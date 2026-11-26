"""Glue between the solvers and the website: build an instance, run every method, summarize."""
import time
import numpy as np
from .data import generate, set_user, Params, HOODS, SLOTS, TYPES, CUISINES, TAG_NAMES, GENDERS
from .solve import (solve_random, solve_greedy, solve_model_a, solve_model_b, metrics, user_values,
                    table_value, age_penalty, prob_at_least)

METHODS = ["Random", "Greedy", "Model A", "Model B"]
MODEL_A_MAX_N = 24


def build(N, seed, lam_d, gamma, show_mode, profile=None):
    p = Params(lam_d=lam_d, gamma=gamma, show_mode=show_mode)
    inst = generate(N, seed, params=p)
    if profile is not None:
        set_user(inst, 0, profile)
    return inst


def run_all(inst, run_a=True, a_time=20.0, seed=0):
    out = {}
    t = time.time(); s = solve_random(inst, seed); out["Random"] = s
    s = solve_greedy(inst); out["Greedy"] = s
    if run_a and inst.N <= MODEL_A_MAX_N:
        s = solve_model_a(inst, time_limit=a_time)
        s.info["stopped"] = s.seconds >= a_time - 0.5
        out["Model A"] = s
    s = solve_model_b(inst, certify=False, ip_time=20, max_iter=60, seed=seed)
    out["Model B"] = s
    return out


def scorecard(inst, sols):
    rows = []
    for name in METHODS:
        if name not in sols:
            continue
        s = sols[name]
        m = metrics(inst, s)
        U = np.where(m["seated"], m["U"], -inst.p.M_unseated)
        rows.append({
            "Method": name,
            "Total score": s.objective,
            "Avg satisfaction (0-10)": np.nanmean(m["sat"]),
            "Avg trip (min)": np.nanmean(m["mins"]),
            "Guests paying a toll": int(np.nansum(m["toll"] > 0)),
            "Worst-off guest": float(U.min()),
            "Seated": f"{int(m['seated'].sum())}/{inst.N}",
            "Seated_n": int(m["seated"].sum()),
            "Tables": len(s.tables),
            "Solve time (s)": s.seconds,
        })
    return rows


def describe_table(inst, S, v, t):
    """Plain facts about one table for the explorer cards."""
    S = list(S)
    U = user_values(inst, S, v, t)
    tags = inst.interests[S].sum(0)
    shared = [(TAG_NAMES[k], int(tags[k])) for k in np.argsort(-tags) if tags[k] >= 2][:4]
    ages = inst.age[S]
    genders = [GENDERS[g] for g in inst.gender[S]]
    vt = TYPES[inst.v_type[v]]
    cuisine = CUISINES[inst.v_cuis[v]] if inst.v_cuis[v] >= 0 else None
    pr = prob_at_least(inst.show[S], inst.p.L)
    guests = []
    for k, i in enumerate(S):
        guests.append(dict(
            id=int(i), age=int(inst.age[i]), gender=GENDERS[inst.gender[i]],
            hood=nearest_hood(inst.home[i]),
            interests=[TAG_NAMES[j] for j in np.flatnonzero(inst.interests[i])],
            minutes=float(inst.d[i, v, t]), toll=float(inst.tau[i, v]),
            satisfaction=float(inst.sat[i, v, t]), value=float(U[k]),
            transit="car" if inst.car[i] else "transit",
        ))
    pair = inst.q[np.ix_(S, S)]
    n = len(S)
    return dict(
        venue=inst.v_name[v], venue_type=vt, cuisine=cuisine, price="$" * int(inst.v_price[v]),
        slot=SLOTS[t], size=n, guests=guests, shared=shared,
        age_range=(int(ages.min()), int(ages.max())), genders=genders,
        avg_trip=float(np.mean([g["minutes"] for g in guests])),
        avg_pair=float(pair.sum() / (n * (n - 1))) if n > 1 else 0.0,
        value=float(table_value(inst, S, v, t)), show_prob=float(pr),
        lat=float(inst.v_loc[v, 0]), lon=float(inst.v_loc[v, 1]),
    )


def nearest_hood(latlon):
    d = [(latlon[0] - h[1]) ** 2 + (latlon[1] - h[2]) ** 2 for h in HOODS]
    return HOODS[int(np.argmin(d))][0]


def find_user_table(sol, i=0):
    for S, v, t in sol.tables:
        if i in S:
            return S, v, t
    return None
