"""Figures for the report. Run after experiments.run has written results/."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from t6.data import generate, HOODS
from t6.solve import solve_random, metrics

R = Path(__file__).resolve().parent / "results"
F = Path(__file__).resolve().parents[1] / "report" / "fig"
F.mkdir(parents=True, exist_ok=True)

INK, INK2, GRID = "#191919", "#666666", "#e6e6e6"
C = {"Random": "#9a9a9a", "Greedy": "#f47230", "Model A (MILP)": "#6a4ce2", "Model B (col. gen.)": "#257de0"}
SHORT = {"Random": "Random", "Greedy": "Greedy", "Model A (MILP)": "Model A (MILP)",
         "Model B (col. gen.)": "Model B (col. gen.)"}
plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "lines.linewidth": 2, "savefig.dpi": 300,
})


def fig_map():
    d = json.loads((R / "demo_map.json").read_text())
    inst = generate(60, 0)
    rnd = solve_random(inst, 0)
    home, vloc = np.array(d["home"]), np.array(d["v_loc"])
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1), sharey=True)
    for ax, (title, tables) in zip(axes, [("Random seating", [(list(S), v, t) for S, v, t in rnd.tables]),
                                          ("Table for 6 (Model B)", d["tables"])]):
        ax.axvspan(-122.385, -122.31, color="#eaf2fb", zorder=0, lw=0)
        ax.text(-122.348, 37.735, "the Bay\n(\\$8 to cross west)", ha="center", va="bottom", fontsize=7.5,
                color="#3a6ea5", style="italic")
        mins = []
        for S, v, t in tables:
            for i in S:
                ax.plot([home[i, 1], vloc[v, 1]], [home[i, 0], vloc[v, 0]], color="#9fbbe0" if title.startswith("Table") else "#c4c4c4",
                        lw=0.7, zorder=1)
                mins.append(inst.d[i, v, t])
        ax.scatter(home[:, 1], home[:, 0], s=9, color=INK, zorder=3, label="user (home)", lw=0)
        used = sorted({v for _, v, _ in tables})
        mk = {0: ("o", "restaurant"), 1: ("s", "cafe"), 2: ("^", "bar")}
        for typ, (m, lab) in mk.items():
            vs = [v for v in used if d["v_type"][v] == typ]
            ax.scatter(vloc[vs, 1], vloc[vs, 0], s=46, marker=m, facecolor="#257de0" if title.startswith("Table") else "#9a9a9a",
                       edgecolor="white", lw=1.2, zorder=4, label=lab)
        for name, lat, lon, *_ in HOODS:
            ax.text(lon, lat + 0.013, name, fontsize=6.5, color=INK2, ha="center", zorder=5,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        ax.set_title(f"{title}: average trip {np.mean(mins):.0f} min")
        ax.set_xlim(-122.53, -122.23); ax.set_ylim(37.73, 37.9)
        ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
    axes[1].legend(loc="lower right", fontsize=7, handletextpad=0.3, borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(F / "map.pdf")
    plt.close(fig)


def fig_quality_scale_cg():
    e1 = pd.read_csv(R / "e1_small.csv")
    e1["ub"] = e1[["ub_b"]].min(axis=1)
    e1["pct"] = 100 * e1["obj"] / e1["ub"]
    e2 = pd.concat([pd.read_csv(f) for f in sorted(R.glob("e2_scale*.csv"))])
    h = pd.read_csv(R / "demo_cg_history.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5))
    # (a) quality
    ax = axes[0]
    Ns = sorted(e1.N.unique())
    meths = ["Random", "Greedy", "Model A (MILP)", "Model B (col. gen.)"]
    wbar = 0.2
    for k, m in enumerate(meths):
        g = e1[e1.method == m].groupby("N")["pct"].mean().reindex(Ns)
        ax.bar(np.arange(len(Ns)) + (k - 1.5) * wbar, np.clip(g.values, 0, None), wbar * 0.9, color=C[m],
               label=SHORT[m])
    ax.set_xticks(range(len(Ns))); ax.set_xticklabels([f"N={n}" for n in Ns])
    ax.set_ylabel("% of certified upper bound"); ax.set_ylim(0, 128); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title("(a) Quality, small N")
    ax.legend(fontsize=5.8, loc="upper center", ncol=2, columnspacing=0.8, handlelength=1.2)
    # (b) time
    ax = axes[1]
    for m in ["Greedy", "Model A (MILP)", "Model B (col. gen.)"]:
        g = e2[e2.method == m].groupby("N")["sec"].mean()
        ax.plot(g.index, g.values, marker="o", ms=4, color=C[m], label=SHORT[m])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([30, 60, 120, 240]); ax.set_xticklabels(["30", "60", "120", "240"])
    ax.set_xlabel("users N"); ax.set_ylabel("seconds")
    ax.set_title("(b) Solve time")
    ax.minorticks_off()
    ax.legend(fontsize=6.5)
    # (c) column generation convergence
    ax = axes[2]
    ax.plot(h["it"], h["lp"], color=C["Model B (col. gen.)"], label="restricted master LP")
    ub = h["ub"].replace(np.inf, np.nan).dropna()
    if len(ub):
        ax.axhline(ub.iloc[-1], color=INK2, lw=1, ls="--", label="certified upper bound")
    ax.axhline(h["ip"].iloc[0], color="#00b894", lw=1.5, label="final integer solution")
    ax.set_xlabel("iteration"); ax.set_ylabel("objective")
    lo = h["lp"].iloc[0]
    ax.set_ylim(lo - 25, (ub.iloc[-1] if len(ub) else h["lp"].max()) + 6)
    ax.set_title("(c) Convergence, N=30")
    ax.legend(fontsize=6.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(F / "quality_scale_cg.pdf")
    plt.close(fig)


def fig_tradeoffs():
    e3 = pd.read_csv(R / "e3_travel.csv").groupby("lam_d")[["mean_sat", "mean_min", "toll_share"]].mean()
    e4u = pd.read_csv(R / "e4_users.csv")
    e4 = pd.read_csv(R / "e4_fair.csv").groupby("gamma")["total_no_theta"].sum()
    e5 = pd.read_csv(R / "e5_robust.csv").groupby("mode")[["collapse", "plan_value", "mean_size", "seated"]].mean()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5))
    ax = axes[0]
    ax.plot(e3.mean_min, e3.mean_sat, marker="o", ms=5, color=C["Model B (col. gen.)"])
    offs = {0.0: (-14, -12), 0.04: (2, -11), 0.08: (2, -11), 0.16: (-6, 6), 0.32: (5, 0)}
    for lam, r in e3.iterrows():
        ax.annotate(f"$\\lambda_d$={lam:g}", (r.mean_min, r.mean_sat), textcoords="offset points",
                    xytext=offs.get(lam, (4, 4)), fontsize=6.5, color=INK2)
    ax.set_xlabel("average trip (minutes)"); ax.set_ylabel("average satisfaction $p$ (0 to 10)")
    ax.set_title("(a) Travel vs. satisfaction")
    ax = axes[1]
    cols = {0.0: "#9a9a9a", 10.0: "#9fbbe0", 30.0: "#257de0", 60.0: "#0b3d91"}
    for gmm, g in e4u.groupby("gamma"):
        x = np.sort(g.U.values)
        ax.step(x, np.arange(1, len(x) + 1) / len(x), where="post", color=cols.get(gmm, INK), lw=1.6,
                label=f"$\\gamma$={gmm:g}" + ("" if gmm == 0 else f" ({100 * (e4[gmm] / e4[0.0] - 1):+.1f}% total)"))
    ax.set_xlabel("user value $U_i$"); ax.set_ylabel("share of users at or below")
    ax.set_title("(b) Fairness: lower tail")
    ax.set_xlim(-2, 7.5); ax.set_ylim(0, 0.4)
    ax.legend(fontsize=6, loc="upper left")
    ax = axes[2]
    order = ["none", "expected", "chance"]
    lab = {"none": "no rule", "expected": "expected\nattendance", "chance": "chance\nconstraint"}
    vals = 100 * e5.loc[order, "collapse"].values
    bars = ax.bar(range(3), vals, 0.6, color=["#9a9a9a", "#9fbbe0", "#257de0"])
    for b, val, (m, r) in zip(bars, vals, e5.loc[order].iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, val + 0.4, f"{val:.1f}%\nsize {r.mean_size:.1f}",
                ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(range(3)); ax.set_xticklabels([lab[o] for o in order], fontsize=7)
    ax.set_ylabel("tables below 4 people (%)")
    ax.set_ylim(0, max(vals) * 1.35)
    ax.set_title("(c) No-shows")
    fig.tight_layout()
    fig.savefig(F / "tradeoffs.pdf")
    plt.close(fig)


if __name__ == "__main__":
    import sys
    for name in (sys.argv[1:] or ["map", "quality_scale_cg", "tradeoffs"]):
        globals()["fig_" + name]()
        print("wrote", name)
