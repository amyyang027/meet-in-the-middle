import streamlit as st
from ui.theme import show, img, hero, H, COLORS
from ui.engine import solve_everything, dark_map, profile_key, find_user_table, describe_table
from t6.service import METHODS, MODEL_A_MAX_N, scorecard

BLURB = {
    "Random": ("Shuffle the guests into open tables.",
               "What most group events do. Quick, fair in a coin-flip way, and blind to geography."),
    "Greedy": ("Open the best table, then the next best.",
               "A sensible shortcut. It fills the happiest tables early and can strand the last few guests."),
    "Model A": ("Exact MILP, guest by guest.",
                "Provably best when it finishes, but slow. We only run it for 24 guests or fewer."),
    "Model B": ("Column generation, whole tables at once.",
                "Our engine. Duals point it to good tables, and it matched the proven optimum in 8 of 10 small tests."),
}

hero(img("bar_glow", 2200), "The lab", "Same guests.<br>Four seatings.",
     "Every method seats the exact same crowd. Change the crowd or the priorities and watch the answers move.",
     short=True)

show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">The controls</div>
<h2>Set the <em>evening's priorities</em></h2></div></div>""")
k1, k2, k3, k4, k5 = st.columns([1.1, 1.1, 1.1, 1.3, .9], gap="medium")
with k1:
    N = st.select_slider("Guests", [12, 18, 24, 36, 48, 60], value=24,
                         help="Model A only runs up to 24 guests: past that it takes minutes.")
with k2:
    lam = st.slider("Value of time", 0.0, 0.3, 0.08, 0.02,
                    help="Satisfaction points a guest gives up per minute of travel (λ_d in the report).")
with k3:
    gamma = st.slider("Fairness", 0, 30, 0, 5,
                      help="Weight on the worst-off guest's score (γ in the report). 0 maximizes the total only.")
with k4:
    mode = st.selectbox("No-show rule", ["none", "expected", "chance"],
                        format_func={"none": "None", "expected": "Expected attendance ≥ 4.25",
                                     "chance": "90% chance of 4+ guests"}.get)
with k5:
    seed = st.number_input("Crowd no.", 0, 99, 0, help="Pick a different simulated crowd.")
run_a = N <= MODEL_A_MAX_N
if not run_a:
    st.caption(f"Model A sits out above {MODEL_A_MAX_N} guests: the exact MILP would need minutes. That gap is the point of Model B.")

prof = st.session_state.get("profile")
with st.spinner("Seating everyone four ways… (Model A can take up to 20 seconds)"):
    inst, sols = solve_everything(N, int(seed), float(lam), int(gamma), mode, profile_key(), run_a)
rows = scorecard(inst, sols)
methods = [r["Method"] for r in rows]
b_total = [r for r in rows if r["Method"] == "Model B"][0]["Total score"]

# ---- headline bars
bars = ""
top = max(r["Total score"] for r in rows)
for k, r in enumerate(rows):
    share = max(r["Total score"], 0) / top if top > 0 else 0
    bars += (f'<div class="row"><span><span class="dot" style="background:{COLORS[r["Method"]]}"></span>{r["Method"]}</span>'
             f'<div class="track"><div class="fill" style="width:{100 * share:.1f}%;background:{COLORS[r["Method"]]};animation-delay:{.15 * k:.2f}s"></div></div>'
             f'<div class="pct">{100 * r["Total score"] / b_total:.0f}%</div></div>')
show(f"""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">The verdict</div>
<h2>Total score, <em>as a share of Model B</em></h2></div><div class="bars reveal">{bars}</div></div>""")

# ---- scorecard
cols = [("Total score", max, "{:.1f}"), ("Avg satisfaction (0-10)", max, "{:.2f}"), ("Avg trip (min)", min, "{:.1f}"),
        ("Guests paying a toll", min, "{:d}"), ("Worst-off guest", max, "{:.1f}"), ("Seated", None, "{}"),
        ("Solve time (s)", min, "{:.1f}")]
best = {c: fn(r[c] for r in rows) for c, fn, _ in cols if fn}
best["Seated"] = max(r["Seated_n"] for r in rows)
head = "".join(f"<th>{H(c)}</th>" for c, _, _ in cols)
body = ""
for r in rows:
    tds = ""
    for c, fn, f in cols:
        val = r[c]
        isbest = (r["Seated_n"] == best["Seated"]) if c == "Seated" else abs(val - best[c]) < 1e-9
        txt = f.format(val)
        if r["Method"] == "Model A" and c == "Solve time (s)" and sols["Model A"].info.get("stopped"):
            txt += ' <span class="meta">(stopped)</span>'
        tds += f'<td class="{"best" if isbest else ""}">{txt}</td>'
    body += f'<tr><td><span class="dot" style="background:{COLORS[r["Method"]]}"></span>{r["Method"]}</td>{tds}</tr>'
show(f"""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">The scorecard</div>
<h2>Line by <em>line</em></h2><p>✦ marks the best value in each column.</p></div>
<div class="reveal" style="overflow-x:auto"><table class="score"><tr><th>Method</th>{head}</tr>{body}</table></div></div>""")

# ---- your seat, four ways
if prof:
    trs = ""
    for m in methods:
        f = find_user_table(sols[m], 0)
        if f:
            dd = describe_table(inst, *f)
            mm = [g for g in dd["guests"] if g["id"] == 0][0]
            trs += (f'<tr><td><span class="dot" style="background:{COLORS[m]}"></span>{m}</td>'
                    f'<td>{H(dd["venue"])}<br><span class="meta">{H(dd["slot"])}</span></td>'
                    f'<td>{mm["minutes"]:.0f} min</td><td>{mm["value"]:.1f}</td></tr>')
        else:
            trs += f'<tr><td><span class="dot" style="background:{COLORS[m]}"></span>{m}</td><td>No seat this round</td><td>–</td><td>–</td></tr>'
    show(f"""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">Your seat</div>
<h2>Where each method <em>puts you</em></h2><p>Another method can sometimes give <i>you</i> a better seat.
Model B maximizes everyone's evening at once, not any single guest's.</p></div>
<table class="score"><tr><th>Method</th><th>Where you'd be</th><th>Your trip</th><th>Your score</th></tr>{trs}</table></div>""")

# ---- maps
show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">On the map</div>
<h2>Who travels <em>where</em></h2><p>Long threads across the water are bridge trips. Random seating sends people everywhere.</p></div></div>""")
view = st.segmented_control("Show", ["Side by side", "One at a time"], default="Side by side", key="mapview")
if view == "One at a time":
    one = st.pills("Method", methods, default="Model B", key="mapone") or "Model B"
    m = [r for r in rows if r["Method"] == one][0]
    show(f'<div class="mcard" style="border-color:{COLORS[one]}"><h4>{one}</h4><p>Average trip <b>{m["Avg trip (min)"]:.0f} min</b> · '
         f'<b>{m["Guests paying a toll"]}</b> tolls · <b>{m["Seated"]}</b> seated</p></div>')
    st.plotly_chart(dark_map(inst, sols[one], color=COLORS[one], height=600, you=bool(prof)), width="stretch",
                    config={"displayModeBar": False}, key="map_one")
else:
    grid = st.columns(2, gap="large")
    for k, name in enumerate(methods):
        m = [r for r in rows if r["Method"] == name][0]
        with grid[k % 2]:
            show(f'<div class="mcard" style="border-color:{COLORS[name]}"><h4>{name}</h4><p>Average trip <b>{m["Avg trip (min)"]:.0f} min</b> · '
                 f'<b>{m["Guests paying a toll"]}</b> tolls · <b>{m["Seated"]}</b> seated</p></div>')
            st.plotly_chart(dark_map(inst, sols[name], color=COLORS[name], height=360, you=bool(prof)),
                            width="stretch", config={"displayModeBar": False}, key=f"map_{name}")

# ---- method cards
show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">The contenders</div>
<h2>Four ways to <em>seat a city</em></h2></div></div>""")
mc = st.columns(4, gap="large")
for k, name in enumerate(METHODS):
    one, two = BLURB[name]
    with mc[k]:
        show(f'<div class="mcard reveal" style="border-color:{COLORS[name]}"><h4>{name}</h4><p><b>{one}</b></p><p>{two}</p></div>')
st.markdown("<br>", unsafe_allow_html=True)
with st.container(key="cta", horizontal=True, horizontal_alignment="center"):
    st.page_link("views/method.py", label="Read the method")
