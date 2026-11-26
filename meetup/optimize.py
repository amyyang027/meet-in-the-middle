"""Optimization models for choosing where and when the group meets.

Notation (see docs/report.md for the full write-up)
  i in members, o in options (venue, [restaurant], time slot), s in scenarios
  C[i,o,s] : travel minutes of member i under option o in scenario s
  x_o      : 1 if option o is chosen, sum_o x_o = 1

Single session objectives
  total     (class: min-sum / 1-median)      min sum_o x_o * sum_i E_s[C_ios]
  longest   (class: min-max / 1-center)      min max_i sum_o x_o * E_s[C_ios]
  robust    (non-class: CVaR, Rockafellar-Uryasev 2000)
            min CVaR_alpha over s of the worst member's trip  W_s = max_i C_ios
            LP form: min eta + 1/((1-alpha) S) sum_s u_s
                     u_s >= w_s - eta,  w_s >= sum_o x_o C_ios  (all i, s),  u_s >= 0
  fair      (non-class: OWA / generalized Gini, Yager 1988; Ogryczak 2000)
            min sum_r w_r * (r-th largest expected trip), w decreasing.
            Linearised with Ogryczak's k-sum trick: the sum of the k largest
            values of y is  min_t k t + sum_i max(y_i - t, 0).

Season planning (several practices; this is where integer programming is needed)
  n_o in Z+ = number of weeks option o is used, sum_o n_o = W,
  sum_{o at host h} n_o <= host_cap,  n_o <= max_repeat
  min  M + eps * sum_i T_i  with  T_i = sum_o D_io n_o <= M   (D = risk-adjusted cost)

For one session the choice is a single option, so enumeration is exact and
instant. We still solve the MILPs to check them; ``tests/test_optimize.py``
asserts that both give the same answer.
"""

from __future__ import annotations

import time

import numpy as np
import pulp

OBJECTIVES = {
    "total": "Minimize total travel (class: min-sum)",
    "longest": "Minimize the longest trip (class: min-max)",
    "robust": "Robust: minimize bad-day worst trip (CVaR, non-class)",
    "fair": "Fair blend: OWA / Gini weights (non-class)",
}


def solver(msg: bool = False):
    return pulp.HiGHS(msg=msg) if "HiGHS" in pulp.listSolvers(onlyAvailable=True) \
        else pulp.PULP_CBC_CMD(msg=msg)


# --------------------------------------------------------------------------- helpers
def cvar(losses: np.ndarray, alpha: float, axis: int = -1) -> np.ndarray:
    """Exact CVaR_alpha (mean of the worst (1-alpha) share) of equally likely scenarios."""
    L = -np.sort(-np.moveaxis(losses, axis, -1), axis=-1)       # descending
    S = L.shape[-1]
    k = (1 - alpha) * S
    m = int(np.floor(k + 1e-9))
    out = L[..., :m].sum(-1)
    if k - m > 1e-9:
        out = out + (k - m) * L[..., m]
    return out / k


def owa_weights(n: int) -> np.ndarray:
    """Linearly decreasing weights (generalized Gini): the worst-off member counts n times the best-off."""
    w = np.arange(n, 0, -1, dtype=float)
    return w / w.sum()


def scores(C: np.ndarray, alpha: float = 0.9) -> dict[str, np.ndarray]:
    """Objective value of every option, for every objective. Shape (O,) each."""
    mean = C.mean(-1)                                            # (I, O)
    w = owa_weights(C.shape[0])
    return {
        "total": mean.sum(0),
        "longest": mean.max(0),
        "robust": cvar(C.max(0), alpha),
        "fair": (np.sort(mean, axis=0)[::-1] * w[:, None]).sum(0),
    }


def evaluate(C: np.ndarray, o: int, alpha: float = 0.9, late_minutes: float = 60.0) -> dict:
    c = C[:, o, :]                                               # (I, S)
    worst = c.max(0)
    return {
        "avg total (min)": float(c.sum(0).mean()),
        "avg longest trip (min)": float(c.mean(1).max()),
        "bad-day worst trip, CVaR (min)": float(cvar(worst, alpha)),
        "95th pct worst trip (min)": float(np.percentile(worst, 95)),
        f"P(someone > {late_minutes:.0f} min)": float((worst > late_minutes).mean()),
        "per member avg (min)": c.mean(1).round(1).tolist(),
    }


# --------------------------------------------------------------------------- single session
def solve_enumeration(C: np.ndarray, objective: str, alpha: float = 0.9) -> int:
    return int(np.argmin(scores(C, alpha)[objective]))


def solve_milp(C: np.ndarray, objective: str, alpha: float = 0.9, msg: bool = False) -> int:
    """The same problem written as a MILP (used to verify and to show the formulation)."""
    I, O, S = C.shape
    mean = C.mean(-1)
    p = pulp.LpProblem("meetup", pulp.LpMinimize)
    x = [pulp.LpVariable(f"x{o}", cat="Binary") for o in range(O)]
    p += pulp.lpSum(x) == 1
    trip = [pulp.lpSum(float(mean[i, o]) * x[o] for o in range(O)) for i in range(I)]
    if objective == "total":
        p += pulp.lpSum(trip)
    elif objective == "longest":
        z = pulp.LpVariable("z")
        for i in range(I):
            p += z >= trip[i]
        p += z
    elif objective == "robust":
        eta = pulp.LpVariable("eta")
        u = [pulp.LpVariable(f"u{s}", lowBound=0) for s in range(S)]
        w = [pulp.LpVariable(f"w{s}") for s in range(S)]
        for s in range(S):
            for i in range(I):
                p += w[s] >= pulp.lpSum(float(C[i, o, s]) * x[o] for o in range(O))
            p += u[s] >= w[s] - eta
        p += eta + (1.0 / ((1 - alpha) * S)) * pulp.lpSum(u)
    elif objective == "fair":
        # OWA with decreasing weights = sum_k (w_k - w_{k+1}) * (sum of k largest trips)
        wts = owa_weights(I)
        deltas = np.append(wts[:-1] - wts[1:], wts[-1])
        terms = []
        for k in range(1, I + 1):
            t = pulp.LpVariable(f"t{k}")
            d = [pulp.LpVariable(f"d{k}_{i}", lowBound=0) for i in range(I)]
            for i in range(I):
                p += d[i] >= trip[i] - t
            terms.append(float(deltas[k - 1]) * (k * t + pulp.lpSum(d)))
        p += pulp.lpSum(terms)
    else:
        raise ValueError(objective)
    p.solve(solver(msg))
    return int(np.argmax([v.value() for v in x]))


def compare_objectives(C: np.ndarray, alpha: float = 0.9) -> dict[str, dict]:
    out = {}
    for name in OBJECTIVES:
        o = solve_enumeration(C, name, alpha)
        out[name] = {"option": o, **evaluate(C, o, alpha)}
    return out


# --------------------------------------------------------------------------- season planning
def member_costs(C: np.ndarray, risk: str = "mean", alpha: float = 0.9) -> np.ndarray:
    """D[i,o]: per-member cost used for season planning (expected trip or its CVaR)."""
    return C.mean(-1) if risk == "mean" else cvar(C, alpha)


def plan_season(D: np.ndarray, weeks: int, host_options: dict[int, list[int]] | None = None,
                host_cap: int = 1, max_repeat: int | None = None, msg: bool = False,
                time_limit: float = 60.0) -> dict:
    """MILP: choose how many weeks to use each option so the member with the most
    total travel over the season travels as little as possible."""
    I, O = D.shape
    host_options = host_options or {}
    ub = weeks if max_repeat is None else max_repeat
    p = pulp.LpProblem("season", pulp.LpMinimize)
    n = [pulp.LpVariable(f"n{o}", lowBound=0, upBound=ub, cat="Integer") for o in range(O)]
    M = pulp.LpVariable("M")
    eps = 1e-3 / I
    T = [pulp.lpSum(float(D[i, o]) * n[o] for o in range(O)) for i in range(I)]
    p += M + eps * pulp.lpSum(T)
    p += pulp.lpSum(n) == weeks
    for i in range(I):
        p += T[i] <= M
    for h, opts in host_options.items():
        p += pulp.lpSum(n[o] for o in opts) <= host_cap
    t0 = time.perf_counter()
    status = p.solve(pulp.HiGHS(msg=msg, timeLimit=time_limit)
                     if "HiGHS" in pulp.listSolvers(onlyAvailable=True) else solver(msg))
    counts = np.array([round(v.value() or 0) for v in n], dtype=int)
    return _season_result(D, counts, time.perf_counter() - t0, pulp.LpStatus[status])


def plan_season_greedy(D: np.ndarray, weeks: int, host_options=None, host_cap: int = 1,
                       max_repeat: int | None = None) -> dict:
    """Baseline heuristic: each week, add the option that keeps the current max total lowest."""
    I, O = D.shape
    host_of = {o: h for h, opts in (host_options or {}).items() for o in opts}
    used_host: dict[int, int] = {}
    counts = np.zeros(O, dtype=int)
    tot = np.zeros(I)
    t0 = time.perf_counter()
    for _ in range(weeks):
        best, best_key = None, None
        for o in range(O):
            if max_repeat is not None and counts[o] >= max_repeat:
                continue
            h = host_of.get(o)
            if h is not None and used_host.get(h, 0) >= host_cap:
                continue
            new = tot + D[:, o]
            key = (new.max(), new.sum())
            if best_key is None or key < best_key:
                best, best_key = o, key
        counts[best] += 1
        tot += D[:, best]
        if best in host_of:
            used_host[host_of[best]] = used_host.get(host_of[best], 0) + 1
    return _season_result(D, counts, time.perf_counter() - t0, "Heuristic")


def season_lp_bound(D: np.ndarray, weeks: int, host_options=None, host_cap: int = 1,
                    max_repeat: int | None = None) -> float:
    """LP relaxation of the season MILP: a lower bound on the best possible max total."""
    I, O = D.shape
    ub = weeks if max_repeat is None else max_repeat
    p = pulp.LpProblem("season_lp", pulp.LpMinimize)
    n = [pulp.LpVariable(f"n{o}", lowBound=0, upBound=ub) for o in range(O)]
    M = pulp.LpVariable("M")
    p += M
    p += pulp.lpSum(n) == weeks
    for i in range(I):
        p += pulp.lpSum(float(D[i, o]) * n[o] for o in range(O)) <= M
    for h, opts in (host_options or {}).items():
        p += pulp.lpSum(n[o] for o in opts) <= host_cap
    p.solve(solver())
    return float(M.value())


def _season_result(D, counts, seconds, status) -> dict:
    totals = D.T[counts > 0].T @ counts[counts > 0] if counts.any() else np.zeros(D.shape[0])
    # spread repeated options out: round-robin over the chosen options
    schedule, left = [], counts.copy()
    while left.sum() > 0:
        for o in np.argsort(-left):
            if left[o] > 0:
                schedule.append(int(o))
                left[o] -= 1
    return {"counts": counts, "schedule": schedule, "member_totals": totals,
            "max_total": float(totals.max()), "sum_total": float(totals.sum()),
            "seconds": seconds, "status": status}
