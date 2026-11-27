"""Experiments for the Table for 6 report. Usage: python -m experiments.run e1|e2|e3|e4|e5|map"""
import sys, json, time
from dataclasses import replace
from pathlib import Path
import numpy as np
import pandas as pd
from t6.data import generate, Params, derive
from t6.solve import (solve_random, solve_greedy, solve_model_a, solve_model_b, metrics,
                      prob_at_least, table_value, EPS)

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)


def row(inst, sol, **kw):
    m = metrics(inst, sol)
    return dict(method=sol.method, obj=sol.objective, sec=sol.seconds, bound=sol.bound,
                seated=m["seated"].mean(), mean_U=np.nanmean(m["U"]), min_U=np.nanmin(m["U"]),
                mean_sat=np.nanmean(m["sat"]), mean_min=np.nanmean(m["mins"]),
                toll_share=np.nanmean(m["toll"] > 0), n_tables=len(sol.tables), **kw)


def e1():
    """Small instances: every method, certified bounds."""
    rows = []
    for N in (12, 18, 24, 30):
        for seed in range(5):
            inst = generate(N, seed)
            b = solve_model_b(inst, certify=True, exact_time=20.0)
            a = solve_model_a(inst, time_limit=90)
            for s in (solve_random(inst, seed), solve_greedy(inst), a, b):
                rows.append(row(inst, s, N=N, seed=seed, ub_b=b.bound, lp_b=b.info["lp"],
                                a_status=a.info["status"], a_vars=a.info["n_vars"]))
            print(N, seed, [round(r["obj"], 1) for r in rows[-4:]], round(a.seconds, 1), round(b.seconds, 1), flush=True)
            pd.DataFrame(rows).to_csv(OUT / "e1_small.csv", index=False)


def e2():
    """Scaling: greedy vs Model B (and Model A while it fits)."""
    rows = []
    for N in (30, 60, 120, 240):
        for seed in range(2):
            inst = generate(N, seed)
            g = solve_greedy(inst)
            b = solve_model_b(inst, certify=False, ip_time=120)
            sols = [solve_random(inst, seed), g, b]
            if N <= 60:
                sols.append(solve_model_a(inst, time_limit=300))
            for s in sols:
                rows.append(row(inst, s, N=N, seed=seed, lp_b=b.info["lp"], iters=b.info["iters"],
                                cols=b.info["cols"]))
            print(N, seed, [(r["method"], round(r["obj"], 1), round(r["sec"], 1)) for r in rows[-len(sols):]], flush=True)
            pd.DataFrame(rows).to_csv(OUT / "e2_scale.csv", index=False)


def e3():
    """Travel trade-off: vary lambda_d."""
    rows = []
    for lam in (0.0, 0.04, 0.08, 0.16, 0.32):
        for seed in range(2):
            inst = generate(60, seed, params=Params(lam_d=lam))
            b = solve_model_b(inst, certify=False)
            rows.append(row(inst, b, lam_d=lam, seed=seed))
            print(lam, seed, rows[-1]["mean_sat"], rows[-1]["mean_min"], flush=True)
            pd.DataFrame(rows).to_csv(OUT / "e3_travel.csv", index=False)


def e4():
    """Fairness floor: vary gamma, keep per-user utilities."""
    rows, users = [], []
    for gamma in (0.0, 10.0, 30.0, 60.0):
        for seed in range(2):
            inst = generate(60, seed, params=Params(gamma=gamma))
            b = solve_model_b(inst, certify=False)
            r = row(inst, b, gamma=gamma, seed=seed)
            r["total_no_theta"] = b.objective - gamma * (r["min_U"] if gamma > 0 else 0)
            rows.append(r)
            m = metrics(inst, b)
            users += [dict(gamma=gamma, seed=seed, U=u) for u in m["U"] if np.isfinite(u)]
            print(gamma, seed, r["total_no_theta"], r["min_U"], flush=True)
            pd.DataFrame(rows).to_csv(OUT / "e4_fair.csv", index=False)
            pd.DataFrame(users).to_csv(OUT / "e4_users.csv", index=False)


def e5():
    """No-show robustness: plan under three rules, then simulate who actually shows up."""
    rows = []
    sim = np.random.default_rng(42)
    for mode in ("none", "expected", "chance"):
        for seed in range(3):
            inst = generate(60, seed, params=Params(show_mode=mode))
            b = solve_model_b(inst, certify=False)
            # plan value is measured with no show-up rule so the three plans are comparable
            plan_value = sum(table_value(inst, S, v, t) for S, v, t in b.tables) - inst.p.M_unseated * (inst.N - sum(len(S) for S, _, _ in b.tables))
            collapse, sizes = [], []
            for S, v, t in b.tables:
                pr = inst.show[list(S)]
                draws = sim.random((5000, len(S))) < pr
                k = draws.sum(1)
                collapse.append((k < inst.p.L).mean())
                sizes.append(len(S))
            rows.append(dict(mode=mode, seed=seed, plan_value=plan_value, n_tables=len(b.tables),
                             mean_size=np.mean(sizes), collapse=np.mean(collapse),
                             exact_risk=np.mean([1 - prob_at_least(inst.show[list(S)], inst.p.L) for S, _, _ in b.tables]),
                             seated=sum(sizes) / inst.N))
            print(rows[-1], flush=True)
            pd.DataFrame(rows).to_csv(OUT / "e5_robust.csv", index=False)


def demo():
    """One N=60 solution for the map, plus column generation history for N=30."""
    inst = generate(60, 0)
    b = solve_model_b(inst, certify=False)
    g = solve_greedy(inst)
    data = dict(home=inst.home.tolist(), v_loc=inst.v_loc.tolist(), v_type=inst.v_type.tolist(),
                v_name=inst.v_name, tables=[[list(map(int, S)), int(v), int(t)] for S, v, t in b.tables],
                greedy=[[list(map(int, S)), int(v), int(t)] for S, v, t in g.tables])
    (OUT / "demo_map.json").write_text(json.dumps(data))
    inst = generate(30, 0)
    b = solve_model_b(inst, certify=True, exact_time=20.0)
    hist = pd.DataFrame(b.info["hist"]); hist["ip"] = b.objective
    hist.to_csv(OUT / "demo_cg_history.csv", index=False)
    # example table for the report
    S, v, t = max(b.tables, key=lambda x: table_value(inst, *x) / len(x[0]))
    ex = dict(members=[dict(age=int(inst.age[i]), gender=int(inst.gender[i]), mins=float(inst.d[i, v, t]),
                            toll=float(inst.tau[i, v]), tags=np.flatnonzero(inst.interests[i]).tolist()) for i in S],
              venue=inst.v_name[v], slot=int(t))
    (OUT / "demo_table.json").write_text(json.dumps(ex, indent=1))
    print("demo done", flush=True)


if __name__ == "__main__":
    globals()[sys.argv[1]]()
