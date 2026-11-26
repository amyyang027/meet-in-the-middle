"""Experiments for the report. Run:  python -m experiments.run_experiments

Writes CSV tables to experiments/results/ and figures to experiments/figures/.
All instances are synthetic Bay Area groups (see meetup/sample.py), so results
are reproducible offline. Every pick is evaluated out of sample: it is chosen on
200 simulated traffic days and scored on 2,000 new ones.
"""

from __future__ import annotations

import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from meetup.optimize import (OBJECTIVES, cvar, member_costs, plan_season, plan_season_greedy,
                             scores, season_lp_bound, solve_enumeration, solve_milp)
from meetup.sample import host_option_map, random_instance

ROOT = Path(__file__).parent
RES, FIG = ROOT / "results", ROOT / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
LABEL = {"total": "Min total", "longest": "Min longest", "robust": "Robust CVaR", "fair": "Fair OWA"}
ALPHA = 0.9
N_INST = 60


def metrics(C, o, alpha=ALPHA, late=120):
    c = C[:, o, :]
    worst = c.max(0)
    return {"avg_total": c.sum(0).mean(), "avg_longest": c.mean(1).max(),
            "cvar_worst": cvar(worst, alpha), "p95_worst": np.percentile(worst, 95),
            "p_late": (worst > late).mean(), "gap_longest_shortest": c.mean(1).max() - c.mean(1).min()}


def exp1_objectives():
    """Price of fairness and robustness: what does each objective give up?"""
    rows = []
    for seed in range(N_INST):
        train = random_instance(n_members=6, n_studios=15, n_slots=4, n_scenarios=200, seed=seed)
        test = random_instance(n_members=6, n_studios=15, n_slots=4, n_scenarios=2000, seed=seed,
                               scenario_seed=10_000 + seed)
        for name in OBJECTIVES:
            o = solve_enumeration(train.C, name, ALPHA)
            rows.append({"instance": seed, "objective": name, "option": o, **metrics(test.C, o)})
    df = pd.DataFrame(rows)
    # When does the robust pick differ from the classic min-max pick, and by how much?
    wide = df.pivot(index="instance", columns="objective")
    differ = wide["option"]["robust"] != wide["option"]["longest"]
    d = wide[differ]
    pd.DataFrame([{
        "share_of_groups_where_robust_differs_from_minmax_%": 100 * differ.mean(),
        "cvar_saved_min (when different)": (d["cvar_worst"]["longest"] - d["cvar_worst"]["robust"]).mean(),
        "p95_saved_min (when different)": (d["p95_worst"]["longest"] - d["p95_worst"]["robust"]).mean(),
        "typical_avg_longest_cost_min (when different)": (d["avg_longest"]["robust"] - d["avg_longest"]["longest"]).mean(),
        "share_of_differing_groups_where_robust_better_out_of_sample_%":
            100 * (d["cvar_worst"]["robust"] < d["cvar_worst"]["longest"]).mean(),
    }]).round(2).T.to_csv(RES / "exp1_robust_vs_minmax.csv", header=["value"])
    print(pd.read_csv(RES / "exp1_robust_vs_minmax.csv", index_col=0))
    df.to_csv(RES / "exp1_objectives_raw.csv", index=False)
    # % worse than the best objective on each metric, averaged over instances
    cols = ["avg_total", "avg_longest", "cvar_worst", "p95_worst"]
    best = df.groupby("instance")[cols].transform("min")
    rel = (df[cols] / best - 1) * 100
    rel["objective"] = df["objective"]
    summary = rel.groupby("objective")[cols].mean().loc[list(OBJECTIVES)]
    summary["p_late"] = df.groupby("objective")["p_late"].mean().loc[list(OBJECTIVES)] * 100
    summary.round(2).to_csv(RES / "exp1_objectives_summary.csv")

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(cols))
    w = 0.2
    for k, name in enumerate(OBJECTIVES):
        ax.bar(x + (k - 1.5) * w, summary.loc[name, cols], w, label=LABEL[name])
    ax.set_xticks(x, ["Avg total time", "Avg longest trip", "Bad-day worst trip\n(CVaR 90%)",
                      "95th pct worst trip"])
    ax.set_ylabel("% worse than best objective\n(avg over 60 groups)")
    ax.set_title("Each objective wins on its own metric; what does it cost on the others?")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "exp1_objectives.png", dpi=200)
    plt.close(fig)
    return summary


def exp2_alpha():
    """How the CVaR level alpha trades typical-day time against bad-day time."""
    alphas = [0.0, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
    rows = []
    for seed in range(N_INST):
        train = random_instance(n_members=6, n_studios=15, n_slots=4, n_scenarios=200, seed=seed)
        test = random_instance(n_members=6, n_studios=15, n_slots=4, n_scenarios=2000, seed=seed,
                               scenario_seed=20_000 + seed)
        for a in alphas:
            o = int(np.argmin(cvar(train.C.max(0), a)))
            worst = test.C[:, o, :].max(0)
            rows.append({"alpha": a, "mean_worst": worst.mean(), "p95_worst": np.percentile(worst, 95),
                         "p99_worst": np.percentile(worst, 99)})
    df = pd.DataFrame(rows).groupby("alpha").mean()
    df.round(2).to_csv(RES / "exp2_alpha.csv")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df["mean_worst"], df["p95_worst"], "o-")
    for a, r in df.iterrows():
        ax.annotate(f"α={a:g}", (r["mean_worst"], r["p95_worst"]), textcoords="offset points",
                    xytext=(5, 5), fontsize=8)
    ax.set_xlabel("Typical day: mean worst-member trip (min)")
    ax.set_ylabel("Bad day: 95th pct worst-member trip (min)")
    ax.set_title("Robustness trade-off as α increases")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "exp2_alpha.png", dpi=200)
    plt.close(fig)
    return df


def exp3_season():
    """Season rotation: integer program vs greedy vs same-spot baseline, and solve time."""
    rows = []
    sizes = [(4, 10, 4), (6, 15, 8), (8, 25, 12), (10, 40, 16), (12, 60, 20)]
    for (I, J, W) in sizes:
        for seed in range(10):
            inst = random_instance(n_members=I, n_studios=J, n_slots=4, n_scenarios=100,
                                   hosts=3, seed=100 + seed)
            D = member_costs(inst.C, "cvar", ALPHA)
            hosts = host_option_map(inst)
            milp = plan_season(D, W, hosts, host_cap=2, time_limit=60)
            greedy = plan_season_greedy(D, W, hosts, host_cap=2)
            lb = season_lp_bound(D, W, hosts, host_cap=2)
            non_host = [o for o in range(D.shape[1]) if all(o not in v for v in hosts.values())]
            same = D[:, non_host].max(0).min() * W
            rows.append({"members": I, "studios": J, "weeks": W, "options": D.shape[1],
                         "milp_max": milp["max_total"], "greedy_max": greedy["max_total"],
                         "same_spot_max": same, "lp_bound": lb, "milp_sec": milp["seconds"],
                         "greedy_sec": greedy["seconds"], "status": milp["status"]})
    df = pd.DataFrame(rows)
    df["greedy_gap_%"] = (df["greedy_max"] / df["milp_max"] - 1) * 100
    df["same_spot_gap_%"] = (df["same_spot_max"] / df["milp_max"] - 1) * 100
    df["lp_gap_%"] = (df["milp_max"] / df["lp_bound"] - 1) * 100
    df.to_csv(RES / "exp3_season_raw.csv", index=False)
    summary = df.groupby(["members", "studios", "weeks", "options"])[
        ["greedy_gap_%", "same_spot_gap_%", "lp_gap_%", "milp_sec", "greedy_sec"]].mean()
    summary.round(3).to_csv(RES / "exp3_season_summary.csv")
    fig, ax = plt.subplots(figsize=(6.5, 4))
    lbl = [f"{i}p/{o}opt/{w}wk" for i, _, w, o in summary.index]
    x = np.arange(len(lbl))
    ax.bar(x - 0.2, summary["same_spot_gap_%"], 0.4, label="Same spot every week")
    ax.bar(x + 0.2, summary["greedy_gap_%"], 0.4, label="Greedy week-by-week")
    ax.set_xticks(x, lbl, fontsize=8)
    ax.set_ylabel("% more travel for the most-travelled\nmember than the integer program")
    ax.set_title("Season planning: value of optimizing the rotation")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "exp3_season.png", dpi=200)
    plt.close(fig)
    return summary


def exp4_solve_time():
    """Single session: enumeration vs MILP solve time (why enumeration is used in the app)."""
    rows = []
    for J, S in [(10, 100), (20, 200), (40, 300)]:
        inst = random_instance(n_members=6, n_studios=J, n_slots=4, n_scenarios=S, seed=7)
        for name in OBJECTIVES:
            t0 = time.perf_counter()
            e = solve_enumeration(inst.C, name)
            te = time.perf_counter() - t0
            t0 = time.perf_counter()
            m = solve_milp(inst.C, name)
            tm = time.perf_counter() - t0
            sc = scores(inst.C)[name]
            rows.append({"options": inst.C.shape[1], "scenarios": S, "objective": name,
                         "enum_ms": te * 1000, "milp_ms": tm * 1000,
                         "same_value": bool(np.isclose(sc[e], sc[m]))})
    df = pd.DataFrame(rows)
    df.round(2).to_csv(RES / "exp4_solve_time.csv", index=False)
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    print("Exp 1: objectives (% worse than best; p_late = % of days someone's round trip > 120 min)")
    print(exp1_objectives().round(1))
    print("\nExp 2: CVaR level alpha")
    print(exp2_alpha().round(1))
    print("\nExp 3: season planning")
    print(exp3_season().round(2))
    print("\nExp 4: solve time")
    print(exp4_solve_time().round(1).to_string(index=False))
