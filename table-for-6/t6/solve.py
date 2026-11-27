"""Solvers for Table for 6: random, greedy, Model A (compact MILP), Model B (column generation)."""
import time
from dataclasses import dataclass
import numpy as np
import pulp
import highspy

EPS = 1e-6


# ---------------------------------------------------------------- table evaluation
def prob_at_least(probs, L):
    """P(at least L of the members show up), Poisson-binomial by dynamic programming."""
    dist = np.zeros(len(probs) + 1); dist[0] = 1.0
    for r in probs:
        dist[1:] = dist[1:] * (1 - r) + dist[:-1] * r
        dist[0] *= (1 - r)
    return dist[L:].sum()


def gender_cap(n):
    """Most guests of one gender allowed at a mixed table of size n: 3 n_g <= 2 n + 2 (3 of 4, 4 of 5, 4 of 6)."""
    return (2 * n + 2) // 3


def gender_ok(inst, S, partial=False):
    """Hard gender rule. A table with a guest who asked for same-gender is all one gender.
    Every other table is mixed: no gender holds more than gender_cap(|S|) seats.
    partial=True checks whether a growing set can still be completed (cap at the largest size U)."""
    S = list(S)
    g = inst.gender[S]
    if inst.same_pref[S].any():
        return bool((g == g[0]).all())
    cap = gender_cap(inst.p.U if partial else len(S))
    return int(np.bincount(g, minlength=3).max()) <= cap


def table_ok(inst, S, v, t):
    p = inst.p
    if not (p.L <= len(S) <= p.U) or inst.R[v, t] == 0:
        return False
    S = list(S)
    if not gender_ok(inst, S):
        return False
    if not np.all(np.isfinite(inst.c[S, v, t])):
        return False
    if p.show_mode == "expected" and inst.show[S].sum() < p.exp_att - EPS:
        return False
    if p.show_mode == "chance" and prob_at_least(inst.show[S], p.L) < p.chance_alpha - EPS:
        return False
    return True


def age_penalty(inst, S):
    a = inst.age[list(S)]
    return inst.p.rho_age * max(0.0, a.max() - a.min() - inst.p.age_span)


def user_values(inst, S, v, t):
    """U_{ig} = c_{ivt} + 1/2 sum_{j in S} q_{ij} for each member i (pair value split evenly)."""
    S = list(S)
    return inst.c[S, v, t] + 0.5 * inst.q[np.ix_(S, S)].sum(1)


def table_value(inst, S, v, t):
    """C_g = sum_i U_{ig} - age penalty."""
    return user_values(inst, S, v, t).sum() - age_penalty(inst, S)


@dataclass
class Solution:
    tables: list          # list of (members tuple, v, t)
    objective: float      # sum C_g - sum M u_i + gamma * theta
    seconds: float
    method: str
    bound: float = np.nan  # valid upper bound when known
    info: dict = None


def evaluate(inst, tables, method="", seconds=0.0, bound=np.nan, info=None):
    seated = set()
    tot = 0.0
    Ui = np.full(inst.N, np.nan)
    for S, v, t in tables:
        assert table_ok(inst, S, v, t), (S, v, t)
        assert not (seated & set(S)), "user seated twice"
        seated |= set(S)
        tot += table_value(inst, S, v, t)
        Ui[list(S)] = user_values(inst, S, v, t)
    unseated = inst.N - len(seated)
    Ui = np.where(np.isnan(Ui), -inst.p.M_unseated, Ui)       # unseated users count as -M
    theta = Ui.min()
    obj = tot - inst.p.M_unseated * unseated + inst.p.gamma * theta
    used = {}
    for S, v, t in tables:
        used[(v, t)] = used.get((v, t), 0) + 1
    assert all(n <= inst.R[v, t] for (v, t), n in used.items())
    return Solution(tables, obj, seconds, method, bound, info or {})


def metrics(inst, sol):
    """Per-user numbers for plots: utility, satisfaction p, minutes, toll, seated flag."""
    Ui = np.full(inst.N, np.nan); sat = np.full(inst.N, np.nan)
    mins = np.full(inst.N, np.nan); toll = np.full(inst.N, np.nan)
    for S, v, t in sol.tables:
        S = list(S)
        Ui[S] = user_values(inst, S, v, t)
        sat[S] = inst.sat[S, v, t]
        mins[S] = inst.d[S, v, t]
        toll[S] = inst.tau[S, v]
    return dict(U=Ui, sat=sat, mins=mins, toll=toll, seated=~np.isnan(Ui))


# ---------------------------------------------------------------- pricing / table builder
def build_tables(inst, v, t, w, wpair, pool, n_seeds=8, rng=None, want=3):
    """Heuristic best tables at (v, t).

    Score of a set S: sum_i w_i + sum_{i<j in S} wpair_ij - age penalty, where
    w_i and wpair_ij already contain duals. Greedy growth from several seeds, then
    1-swap local search. Returns up to `want` distinct (score, S) sorted best first.
    """
    p = inst.p
    pool = [i for i in pool if np.isfinite(inst.c[i, v, t])]
    if len(pool) < p.L:
        return []
    pool = np.array(pool)
    rng = rng or np.random.default_rng(0)

    def score(S):
        S = list(S)
        return w[S].sum() + 0.5 * wpair[np.ix_(S, S)].sum() - age_penalty(inst, S)

    order = pool[np.argsort(-w[pool])]
    seeds = [int(s) for s in order[:n_seeds]]
    if len(pool) > n_seeds:
        seeds += [int(s) for s in rng.choice(pool, min(3, len(pool)), replace=False)]
    found = {}
    for s in seeds:
        S = [s]
        while len(S) < p.U:
            cand = np.setdiff1d(pool, S)
            cand = np.array([c for c in cand if gender_ok(inst, S + [int(c)], partial=True)], dtype=int)
            if len(cand) == 0:
                break
            gain = w[cand] + wpair[np.ix_(cand, S)].sum(1)
            S.append(int(cand[np.argmax(gain)]))
        # best feasible prefix of size L..U
        best = None
        for k in range(p.L, len(S) + 1):
            T = tuple(sorted(S[:k]))
            if table_ok(inst, T, v, t):
                sc = score(T)
                if best is None or sc > best[0]:
                    best = (sc, T)
        if best is None:
            continue
        # local search (best improvement): swap one member, add one, or drop one
        sc, T = best
        for _ in range(50):
            Tl = np.array(T)
            out = np.setdiff1d(pool, Tl)
            pen0 = age_penalty(inst, T)
            in_sum = wpair[np.ix_(Tl, Tl)].sum(1)            # each member's pair sum with T
            loss = w[Tl] + in_sum                            # what member a brings
            cand_moves = []
            if len(out):
                to_T = wpair[np.ix_(out, Tl)]                # (|out|,|T|)
                gain_add = w[out] + to_T.sum(1)
                if len(Tl) < p.U:
                    for bi, b in enumerate(out):
                        cand_moves.append((gain_add[bi], tuple(sorted(Tl.tolist() + [int(b)]))))
                # swap a -> b: gain_add[b] - wpair[b,a] - loss[a]
                D = gain_add[:, None] - to_T - loss[None, :]
                flat = np.argsort(-D, axis=None)[:40]
                for f in flat:
                    bi, ai = np.unravel_index(f, D.shape)
                    Tn = tuple(sorted([int(x) for x in Tl if x != Tl[ai]] + [int(out[bi])]))
                    cand_moves.append((D[bi, ai], Tn))
            if len(Tl) > p.L:
                for ai in range(len(Tl)):
                    cand_moves.append((-loss[ai], tuple(int(x) for x in Tl if x != Tl[ai])))
            cand_moves.sort(key=lambda m: -m[0])
            moved = False
            for dlt, Tn in cand_moves:
                if dlt + pen0 <= EPS:           # even with the best age change, no improvement
                    break
                if table_ok(inst, Tn, v, t):
                    s2 = score(Tn)
                    if s2 > sc + EPS:
                        sc, T, moved = s2, Tn, True
                        break
            if not moved:
                break
        found[T] = sc
    out = sorted(((s, T) for T, s in found.items()), reverse=True)
    return out[:want]


# ---------------------------------------------------------------- baselines
def solve_random(inst, seed=0):
    """Random seating: shuffle people, fill open tables first-come first-served."""
    t0 = time.time()
    rng = np.random.default_rng(seed)
    K = [(v, t) for v in range(inst.V) for t in range(3) for _ in range(inst.R[v, t])]
    rng.shuffle(K)
    free = set(range(inst.N))
    tables = []
    for v, t in K:
        cand = [i for i in rng.permutation(list(free)) if np.isfinite(inst.c[i, v, t])]
        size = int(rng.integers(inst.p.L, inst.p.U + 1))
        S = None
        for k in (size, inst.p.U, inst.p.L + 1, inst.p.L):
            if len(cand) >= k:
                for _ in range(20):
                    T = tuple(sorted(int(a) for a in rng.choice(cand, k, replace=False)))
                    if table_ok(inst, T, v, t):
                        S = T; break
            if S:
                break
        if S:
            tables.append((S, v, t)); free -= set(S)
    return evaluate(inst, tables, "Random", time.time() - t0)


def solve_greedy(inst):
    """Greedy set packing: repeatedly open the best table per seat among all (v, t)."""
    t0 = time.time()
    free = set(range(inst.N))
    cap = inst.R.copy()
    tables = []
    w_pair = inst.q
    while True:
        best = None
        for v in range(inst.V):
            for t in range(3):
                if cap[v, t] == 0:
                    continue
                w = inst.c[:, v, t] + inst.p.M_unseated          # seating someone avoids M_i
                res = build_tables(inst, v, t, w, w_pair, sorted(free), n_seeds=3, want=1)
                if res:
                    sc, S = res[0]
                    if sc > 0 and (best is None or sc / len(S) > best[0]):
                        best = (sc / len(S), S, v, t)
        if best is None:
            break
        _, S, v, t = best
        tables.append((S, v, t)); free -= set(S); cap[v, t] -= 1
    return evaluate(inst, tables, "Greedy", time.time() - t0)


# ---------------------------------------------------------------- Model A
def solve_model_a(inst, time_limit=120, msg=False):
    """Compact MILP with x_ik, z_k, y_ijk, u_i, s_k (+ age-span and fairness variables).

    Gender rule: s_k = 1 marks a same-gender table (allowed only if a guest who asked for one sits there);
    a guest who asked for same-gender excludes every other gender from the table; otherwise
    3 n_gk <= 2 n_k + 2 for every gender g."""
    t0 = time.time()
    p, N = inst.p, inst.N
    K = [(v, t, r) for v in range(inst.V) for t in range(3) for r in range(inst.R[v, t])]
    m = pulp.LpProblem("TableFor6_A", pulp.LpMaximize)
    elig = {(i, k): True for i in range(N) for k, (v, t, r) in enumerate(K) if np.isfinite(inst.c[i, v, t])}
    x = {ik: pulp.LpVariable(f"x_{ik[0]}_{ik[1]}", cat="Binary") for ik in elig}
    z = {k: pulp.LpVariable(f"z_{k}", cat="Binary") for k in range(len(K))}
    u = {i: pulp.LpVariable(f"u_{i}", cat="Binary") for i in range(N)}
    y = {}
    for k in range(len(K)):
        mem = [i for i in range(N) if (i, k) in elig]
        for a in range(len(mem)):
            for b in range(a + 1, len(mem)):
                i, j = mem[a], mem[b]
                y[i, j, k] = pulp.LpVariable(f"y_{i}_{j}_{k}", 0, 1)
    amax = {k: pulp.LpVariable(f"amax_{k}", 0) for k in range(len(K))}
    amin = {k: pulp.LpVariable(f"amin_{k}", 0) for k in range(len(K))}
    e = {k: pulp.LpVariable(f"e_{k}", 0) for k in range(len(K))}
    theta = pulp.LpVariable("theta") if p.gamma > 0 else None

    obj = pulp.lpSum(inst.c[i, K[k][0], K[k][1]] * x[i, k] for (i, k) in x)
    obj += pulp.lpSum(inst.q[i, j] * y[i, j, k] for (i, j, k) in y)
    obj -= pulp.lpSum(p.M_unseated * u[i] for i in u)
    obj -= pulp.lpSum(p.rho_age * e[k] for k in e)
    if theta is not None:
        obj += p.gamma * theta
    m += obj

    by_user = {i: [] for i in range(N)}
    by_tab = {k: [] for k in range(len(K))}
    for (i, k) in x:
        by_user[i].append(k); by_tab[k].append(i)
    for i in range(N):
        m += pulp.lpSum(x[i, k] for k in by_user[i]) + u[i] == 1
    Amax = float(inst.age.max())
    for k, (v, t, r) in enumerate(K):
        s = pulp.lpSum(x[i, k] for i in by_tab[k])
        m += s >= p.L * z[k]
        m += s <= p.U * z[k]
        if p.show_mode in ("expected", "chance"):          # Model A can only carry the linear proxy
            m += pulp.lpSum(inst.show[i] * x[i, k] for i in by_tab[k]) >= p.exp_att * z[k]
        for i in by_tab[k]:
            m += amax[k] >= inst.age[i] * x[i, k]
            m += amin[k] <= inst.age[i] + Amax * (1 - x[i, k])
        m += e[k] >= amax[k] - amin[k] - p.age_span - Amax * (1 - z[k])
        req = [i for i in by_tab[k] if inst.same_pref[i]]
        sk = pulp.LpVariable(f"s_{k}", cat="Binary") if req else 0
        if req:
            m += sk <= pulp.lpSum(x[i, k] for i in req)
            for i in req:
                m += pulp.lpSum(x[j, k] for j in by_tab[k] if inst.gender[j] != inst.gender[i]) <= p.U * (1 - x[i, k])
        for g in range(3):
            ng = pulp.lpSum(x[i, k] for i in by_tab[k] if inst.gender[i] == g)
            m += 3 * ng - 2 * s <= 2 + p.U * sk
        if r > 0:
            m += z[k] <= z[k - 1]                           # symmetry breaking between copies
    for (i, j, k), var in y.items():
        m += var <= x[i, k]
        m += var <= x[j, k]
        if inst.q[i, j] < 0:
            m += var >= x[i, k] + x[j, k] - 1
    if theta is not None:
        for i in range(N):
            Ui = pulp.lpSum(inst.c[i, K[k][0], K[k][1]] * x[i, k] for k in by_user[i])
            Ui += pulp.lpSum(0.5 * inst.q[a, b] * var for (a, b, k), var in y.items() if a == i or b == i)
            m += theta <= Ui - p.M_unseated * u[i]
    solver = pulp.HiGHS(msg=msg, timeLimit=time_limit, threads=1)
    m.solve(solver)
    tables = []
    for k, (v, t, r) in enumerate(K):
        S = tuple(sorted(i for i in by_tab[k] if x[i, k].value() is not None and x[i, k].value() > 0.5))
        if S:
            tables.append((S, v, t))
    secs = time.time() - t0
    bound = np.nan
    try:
        bound = m.solverModel.getInfo().mip_dual_bound
    except Exception:
        pass
    status = pulp.LpStatus[m.status]
    info = dict(n_vars=len(m.variables()), n_cons=len(m.constraints), status=status)
    return evaluate(inst, tables, "Model A (MILP)", secs, bound, info)



def exact_pricing(inst, v, t, w, wpair, time_limit=20.0):
    """Exact pricing MILP at (v, t), including the age-spread penalty; the chance rule is relaxed.

    max sum_i w_i b_i + sum_{i<j} wpair_ij y_ij  s.t. L <= sum b_i <= U, AND-linearization.
    Returns (best primal table or None, its relaxed score, valid upper bound on the score).
    """
    p = inst.p
    pool = [i for i in range(inst.N) if np.isfinite(inst.c[i, v, t])]
    n = len(pool)
    if n < p.L:
        return None, -np.inf, -np.inf
    h = highspy.Highs(); h.setOptionValue("output_flag", False); h.setOptionValue("threads", 1)
    h.setOptionValue("time_limit", float(time_limit)); h.setOptionValue("mip_rel_gap", 1e-4)
    h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    inf = highspy.kHighsInf
    E = np.array([], dtype=np.int32); F = np.array([], dtype=np.float64)
    for a in range(n):
        h.addCol(float(w[pool[a]]), 0.0, 1.0, 0, E, F)
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * n))
    # size row
    h.addRow(float(p.L), float(p.U), n, np.arange(n, dtype=np.int32), np.ones(n))
    if p.show_mode in ("expected", "chance"):
        h.addRow(float(p.exp_att) if p.show_mode == "expected" else -inf, inf, n,
                 np.arange(n, dtype=np.int32), inst.show[pool].astype(float))
    col = n
    for a in range(n):
        for b in range(a + 1, n):
            qq = wpair[pool[a], pool[b]]
            if abs(qq) < 1e-9:
                continue
            h.addCol(float(qq), 0.0, 1.0, 0, E, F)
            if qq > 0:
                h.addRow(-inf, 0.0, 2, np.array([col, a], dtype=np.int32), np.array([1.0, -1.0]))
                h.addRow(-inf, 0.0, 2, np.array([col, b], dtype=np.int32), np.array([1.0, -1.0]))
            else:
                h.addRow(-1.0, inf, 3, np.array([col, a, b], dtype=np.int32), np.array([1.0, -1.0, -1.0]))
            col += 1
    # gender rule (see solve_model_a): same-gender flag sg, requester exclusion, mixed-table cap
    gen = inst.gender[pool]; req = [a for a in range(n) if inst.same_pref[pool[a]]]
    cs = col; h.addCol(0.0, 0.0, 1.0 if req else 0.0, 0, E, F); col += 1
    h.changeColsIntegrality(1, np.array([cs], dtype=np.int32), np.array([highspy.HighsVarType.kInteger]))
    if req:
        h.addRow(-inf, 0.0, len(req) + 1, np.array([cs] + req, dtype=np.int32), np.array([1.0] + [-1.0] * len(req)))
        for a in req:
            other = [b for b in range(n) if gen[b] != gen[a]]
            if other:
                h.addRow(-inf, float(p.U), len(other) + 1, np.array(other + [a], dtype=np.int32),
                         np.array([1.0] * len(other) + [float(p.U)]))
    for g in range(3):
        coef = np.where(gen == g, 1.0, -2.0)                # 3 n_g - 2 n = sum (3[g_i=g] - 2) b_i
        h.addRow(-inf, 2.0, n + 1, np.array(list(range(n)) + [cs], dtype=np.int32),
                 np.array(list(coef) + [-float(p.U)]))
    # age spread: e >= amax - amin - span, objective -rho_age * e
    ages = inst.age[pool].astype(float)
    A = float(inst.age.max())
    ca = col; h.addCol(0.0, 0.0, A, 0, E, F)          # amax
    ci = col + 1; h.addCol(0.0, 0.0, A, 0, E, F)      # amin
    ce = col + 2; h.addCol(-float(p.rho_age), 0.0, inf, 0, E, F)
    for a in range(n):
        h.addRow(0.0, inf, 2, np.array([ca, a], dtype=np.int32), np.array([1.0, -ages[a]]))
        h.addRow(-inf, ages[a] + A, 2, np.array([ci, a], dtype=np.int32), np.array([1.0, A]))
    h.addRow(-float(p.age_span), inf, 3, np.array([ce, ca, ci], dtype=np.int32), np.array([1.0, -1.0, 1.0]))
    h.run()
    info = h.getInfo()
    x = np.array(h.getSolution().col_value)[:n]
    S = tuple(sorted(int(pool[a]) for a in range(n) if x[a] > 0.5))
    ub = info.mip_dual_bound if np.isfinite(info.mip_dual_bound) else np.inf
    return (S if S else None), info.objective_function_value, max(ub, info.objective_function_value)

# ---------------------------------------------------------------- Model B
class Master:
    """Restricted master LP/IP over table columns, built directly in HiGHS.

    Rows: 0..N-1 partition (= 1, dual pi_i); then one capacity row per open (v,t)
    (<= R_vt, dual mu_vt >= 0); then, if gamma > 0, fairness rows
    theta - sum_g U_ig lambda_g + M u_i <= 0 (dual sigma_i >= 0): an unseated user counts as -M.
    """

    def __init__(self, inst):
        self.inst = inst
        p = inst.p
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("threads", 1)
        h.changeObjectiveSense(highspy.ObjSense.kMaximize)
        self.h = h
        N = inst.N
        self.vt = [(v, t) for v in range(inst.V) for t in range(3) if inst.R[v, t] > 0]
        self.vt_row = {vt: N + n for n, vt in enumerate(self.vt)}
        inf = highspy.kHighsInf
        lo = [1.0] * N + [-inf] * len(self.vt)
        up = [1.0] * N + [float(inst.R[v, t]) for v, t in self.vt]
        self.fair = p.gamma > 0
        self.f0 = N + len(self.vt)
        self.BIG = 60.0
        if self.fair:
            lo += [-inf] * N; up += [0.0] * N
        h.addRows(len(lo), np.array(lo), np.array(up), 0, np.array([], dtype=np.int32),
                  np.array([], dtype=np.int32), np.array([], dtype=np.float64))
        self.cols = []       # (S, v, t)
        self.keys = set()
        for i in range(N):   # u_i
            idx = [i] + ([self.f0 + i] if self.fair else [])
            val = [1.0] + ([float(p.M_unseated)] if self.fair else [])
            h.addCol(-p.M_unseated, 0.0, 1.0, len(idx), np.array(idx, dtype=np.int32), np.array(val))
        self.n_u = N
        if self.fair:
            idx = np.arange(self.f0, self.f0 + N, dtype=np.int32)
            h.addCol(p.gamma, -inf, inf, N, idx, np.ones(N))
            self.theta_col = N

    def add(self, S, v, t):
        key = (S, v, t)
        if key in self.keys:
            return False
        self.keys.add(key)
        inst = self.inst
        idx = list(S) + [self.vt_row[(v, t)]]
        val = [1.0] * len(S) + [1.0]
        if self.fair:
            Ui = user_values(inst, S, v, t)
            idx += [self.f0 + i for i in S]
            val += list(-Ui)
        self.h.addCol(table_value(inst, S, v, t), 0.0, 1.0, len(idx), np.array(idx, dtype=np.int32),
                      np.array(val))
        self.cols.append(key)
        return True

    def solve_lp(self):
        h = self.h
        h.run()
        sol = h.getSolution()
        rd = np.array(sol.row_dual)
        N = self.inst.N
        pi = rd[:N]
        mu = {vt: rd[self.vt_row[vt]] for vt in self.vt}
        sigma = rd[self.f0:self.f0 + N] if self.fair else np.zeros(N)
        return h.getInfo().objective_function_value, pi, mu, sigma

    def solve_ip(self, time_limit=60):
        h = self.h
        n = h.getNumCol()
        integ = np.array([highspy.HighsVarType.kInteger] * n)
        if self.fair:
            integ[self.theta_col] = highspy.HighsVarType.kContinuous
        h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), integ)
        h.setOptionValue("time_limit", float(time_limit))
        h.run()
        x = np.array(h.getSolution().col_value)
        first = self.n_u + (1 if self.fair else 0)
        chosen = [self.cols[j - first] for j in range(first, n) if x[j] > 0.5]
        return chosen, h.getInfo().objective_function_value


def solve_model_b(inst, max_iter=200, ip_time=60, init=None, log=False, seed=0, certify=True, exact_time=5.0, max_exact_passes=3, dive=True, enrich=True):
    """Column generation: restricted master LP + heuristic pricing, then a final IP over the pool.

    A valid upper bound on the full LP (and so on the IP) comes from weak duality:
    raise each mu_vt by the largest possible reduced cost at (v,t), which makes the dual
    feasible for every column, then take the dual objective sum pi_i + sum R_vt mu'_vt.
    """
    t0 = time.time()
    rng = np.random.default_rng(seed)
    p = inst.p
    mp = Master(inst)
    for S, v, t in (init or solve_greedy(inst).tables):
        mp.add(S, v, t)
    hist = []
    UB = np.inf
    exact_mode = False
    exact_passes = 0
    for it in range(max_iter):
        z, pi, mu, sigma = mp.solve_lp()
        added = 0
        ub_add = 0.0
        for (v, t) in mp.vt:
            # reduced cost of table S at (v,t): sum_i [(1+sigma_i) U_ig - pi_i] - mu_vt
            w = (1 + sigma) * inst.c[:, v, t] - pi
            wpair = 0.5 * ((1 + sigma)[:, None] + (1 + sigma)[None, :]) * inst.q
            if not exact_mode:
                for sc, S in build_tables(inst, v, t, w, wpair, list(range(inst.N)), n_seeds=6, rng=rng, want=2):
                    if sc - mu[(v, t)] > 1e-5:
                        added += mp.add(S, v, t)
            else:
                S, sc, ub = exact_pricing(inst, v, t, w, wpair, time_limit=exact_time)
                ub_add += inst.R[v, t] * max(0.0, ub - mu[(v, t)])
                if S is not None and table_ok(inst, S, v, t):
                    r = (w[list(S)].sum() + 0.5 * wpair[np.ix_(S, S)].sum() - age_penalty(inst, S)
                         - mu[(v, t)])
                    if r > 1e-5:
                        added += mp.add(S, v, t)
        if exact_mode:
            dual_obj = pi.sum() + sum(inst.R[v, t] * mu[(v, t)] for v, t in mp.vt)
            UB = min(UB, dual_obj + ub_add)
        hist.append(dict(it=it, lp=z, ub=UB, cols=len(mp.cols), added=added, exact=exact_mode,
                         sec=time.time() - t0))
        if log:
            print(hist[-1])
        if exact_mode:
            exact_passes += 1
        if added == 0:
            if exact_mode or not certify:
                break
            exact_mode = True
        elif exact_mode:
            if exact_passes >= max_exact_passes:
                break
            exact_mode = False          # new columns found: go back to cheap pricing
    lp_final = z
    t_cg = time.time() - t0
    if enrich:
        # cheap pool enrichment for the integer step: drop-one subsets and the same group elsewhere
        base = list(mp.cols)
        for S, v, t in base:
            if len(S) > p.L:
                for a in S:
                    T = tuple(x for x in S if x != a)
                    if table_ok(inst, T, v, t):
                        mp.add(T, v, t)
            for (v2, t2) in mp.vt:
                if (v2, t2) != (v, t) and table_ok(inst, S, v2, t2):
                    mp.add(S, v2, t2)
    chosen, ipz = mp.solve_ip(ip_time)
    best = evaluate(inst, chosen, "Model B (col. gen.)", 0, UB)
    if dive:
        dv = dive_solution(inst, mp, rng)
        if dv is not None:
            cand = evaluate(inst, dv, "Model B (col. gen.)", 0, UB)
            if cand.objective > best.objective + 1e-9:
                best = cand
    sol = evaluate(inst, best.tables, "Model B (col. gen.)", time.time() - t0, UB,
                   dict(hist=hist, lp=lp_final, cols=len(mp.cols), t_cg=t_cg, iters=len(hist),
                        ip_pool=ipz))
    return sol


def dive_solution(inst, mp, rng, inner_iter=8):
    """Diving heuristic: fix the most-chosen table, re-price around it, repeat until integral."""
    h = mp.h
    n = h.getNumCol()
    integ = np.array([highspy.HighsVarType.kContinuous] * n)
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), integ)
    first = mp.n_u + (1 if mp.fair else 0)
    fixed_users = set()
    fixed_cols = set()
    for _ in range(inst.N):
        for _inner in range(inner_iter):
            z, pi, mu, sigma = mp.solve_lp()
            if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
                return None
            pool = [i for i in range(inst.N) if i not in fixed_users]
            added = 0
            for (v, t) in mp.vt:
                w = (1 + sigma) * inst.c[:, v, t] - pi
                wpair = 0.5 * ((1 + sigma)[:, None] + (1 + sigma)[None, :]) * inst.q
                for sc, S in build_tables(inst, v, t, w, wpair, pool, n_seeds=4, rng=rng, want=1):
                    if sc - mu[(v, t)] > 1e-5:
                        added += mp.add(S, v, t)
            if added == 0:
                break
        x = np.array(h.getSolution().col_value)
        n = h.getNumCol()
        cols = np.arange(first, n)
        frac = [(x[j], j) for j in cols if j not in fixed_cols and x[j] > 1e-6]
        if all(abs(x[j] - round(x[j])) < 1e-6 for j in range(n) if j != getattr(mp, "theta_col", -1)):
            break
        if not frac:
            break
        to_fix = [j for val, j in frac if val > 0.99] or [max(frac)[1]]
        for j in to_fix:
            h.changeColBounds(int(j), 1.0, 1.0)
            fixed_cols.add(j)
            fixed_users |= set(mp.cols[j - first][0])
    x = np.array(h.getSolution().col_value)
    n = h.getNumCol()
    chosen = [mp.cols[j - first] for j in range(first, n) if x[j] > 0.5]
    try:
        evaluate(inst, chosen)
    except AssertionError:
        return None
    return chosen
