"""Table for 6: seat strangers at tables of 4 to 6, and compare four ways of doing it.

Run locally:  streamlit run app.py
"""
import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from t6.data import HOODS, SLOTS, CUISINES, TAG_NAMES, GENDERS, TYPES
from t6.service import (METHODS, MODEL_A_MAX_N, build, run_all, scorecard, describe_table,
                        find_user_table)

st.set_page_config(page_title="Table for 6", page_icon="🍽️", layout="wide",
                   initial_sidebar_state="collapsed")

COLORS = {"Random": "#A79E94", "Greedy": "#E4876A", "Model A": "#233386", "Model B": "#591D2F"}
BLURB = {
    "Random": ("Shuffle the guests into open tables.",
               "What most group events do. Fast, fair in a coin-flip way, and blind to geography."),
    "Greedy": ("Open the best table first, then the next best.",
               "A sensible shortcut. It fills the happiest tables early and can strand the last few guests."),
    "Model A": ("Exact MILP: seat each guest one by one.",
                "Guaranteed best when it finishes, but slow. We only run it for 24 guests or fewer."),
    "Model B": ("Column generation: choose whole tables at once.",
                "Our engine. Uses duals to discover good tables, and is within about 1% of optimal in our tests."),
}
REPORT_URL = "https://github.com/amyyang027/meet-in-the-middle/blob/main/table-for-6/report/main.pdf"

# ------------------------------------------------------------------ styling
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Aboreto&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --cream:#F3EDD2; --paper:#FBF8EE; --wine:#591D2F; --coral:#E4876A; --ink:#2B2124;
  --muted:#6E6266; --cobalt:#233386; --line:#E2D8BC;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--cream) !important; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; max-width: 1180px; }
html, body, p, li, label, .stMarkdown, [data-testid="stWidgetLabel"] p {
  font-family: 'EB Garamond', Georgia, serif !important; color: var(--ink);
}
p, li { font-size: 1.08rem; line-height: 1.55; }
h1, h2, h3 { font-family: 'EB Garamond', Georgia, serif !important; color: var(--wine) !important;
  font-weight: 500 !important; letter-spacing: -0.01em; }
.eyebrow { font-family: 'Aboreto', serif; text-transform: uppercase; letter-spacing: .18em;
  font-size: .78rem; color: var(--coral); margin-bottom: .2rem; }
.nav { display:flex; justify-content:space-between; align-items:center; padding:.4rem 0 1.4rem;
  border-bottom: 1px solid var(--line); margin-bottom: 2.2rem; }
.wordmark { font-family:'Aboreto',serif; letter-spacing:.32em; font-size:1rem; color:var(--wine); }
.nav a { font-family:'Aboreto',serif; letter-spacing:.16em; font-size:.72rem; color:var(--ink);
  text-decoration:none; margin-left:1.8rem; }
.nav a:hover { color: var(--coral); }
.hero { display:grid; grid-template-columns: 1.25fr 1fr; gap: 2rem; align-items:center; margin-bottom: 2.5rem; }
.hero h1 { font-size: clamp(3rem, 7vw, 5.6rem); line-height: .95; margin: .2rem 0 1rem; font-style: italic; }
.hero .lede { font-size: 1.3rem; color: var(--muted); max-width: 32rem; }
.pill { display:inline-block; border:1px solid var(--wine); color:var(--wine); border-radius:999px;
  padding:.45rem 1.1rem; font-family:'Aboreto',serif; letter-spacing:.14em; font-size:.72rem;
  text-decoration:none; margin-right:.6rem; margin-top:.8rem; }
.pill.solid { background: var(--wine); color: var(--cream); }
.section { margin: 3.2rem 0 1.2rem; }
.section h2 { font-size: 2.6rem; margin: 0 0 .4rem; }
.section .sub { color: var(--muted); font-size: 1.15rem; max-width: 46rem; }
.steps { display:grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem; margin-top: 1rem; }
.step { border-top: 1px solid var(--wine); padding-top: .8rem; }
.step .num { font-family:'Aboreto',serif; color: var(--coral); letter-spacing:.2em; font-size:.8rem; }
.step h3 { font-size: 1.5rem; margin: .2rem 0 .3rem; }
.card { background: var(--paper); border: 1px solid var(--line); border-radius: 14px; padding: 1.1rem 1.2rem; }
.yourtable { background: var(--wine); color: var(--cream); border-radius: 18px; padding: 1.6rem 1.8rem; }
.yourtable h3, .yourtable p, .yourtable li, .yourtable span { color: var(--cream) !important; }
.yourtable .eyebrow { color: var(--coral); }
.yourtable h3 { font-size: 2.1rem; font-style: italic; margin: .1rem 0 .2rem; }
.guest { display:flex; justify-content:space-between; border-bottom: 1px solid rgba(243,237,210,.25); padding:.35rem 0; font-size:1rem; }
.chips span { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:.1rem .6rem;
  margin:.15rem .25rem 0 0; font-size:.86rem; font-family:'Inter',sans-serif; color: var(--ink); background: var(--cream); }
.yourtable .chips span { background: transparent; border-color: rgba(243,237,210,.5); color: var(--cream) !important; }
table.score { width:100%; border-collapse: collapse; font-family:'Inter',sans-serif; font-size:.92rem; background: var(--paper);
  border-radius: 14px; overflow:hidden; }
table.score th { text-align:right; font-weight:500; color: var(--muted); padding:.7rem .8rem; border-bottom:1px solid var(--line);
  font-size:.76rem; text-transform: uppercase; letter-spacing:.06em; }
table.score th:first-child, table.score td:first-child { text-align:left; }
table.score td { text-align:right; padding:.65rem .8rem; border-bottom:1px solid var(--line); color: var(--ink); }
table.score tr:last-child td { border-bottom: none; }
table.score td.best { color: var(--wine); font-weight: 600; }
table.score td.best::after { content:' ●'; color: var(--coral); font-size:.7rem; }
.dot { display:inline-block; width:.7rem; height:.7rem; border-radius:50%; margin-right:.5rem; vertical-align: middle; }
.tcard { background: var(--paper); border:1px solid var(--line); border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: 1rem; min-height: 100%; }
.tcard h4 { font-family:'EB Garamond',serif; font-size:1.3rem; color: var(--wine); margin:.1rem 0; font-weight:500; }
.tcard .meta { font-family:'Inter',sans-serif; font-size:.8rem; color: var(--muted); }
.tcard ul { padding-left: 1rem; margin: .4rem 0; }
.tcard li { font-size: .95rem; line-height: 1.35; }
.method { border-top: 3px solid; padding-top: .6rem; }
.method h4 { font-family:'EB Garamond',serif; font-size:1.35rem; margin:.1rem 0; font-weight:500; }
.method p { font-size: .98rem; color: var(--muted); margin: .2rem 0; }
.foot { margin-top: 4rem; padding: 1.6rem 0 2rem; border-top:1px solid var(--line); display:flex; justify-content:space-between;
  font-family:'Aboreto',serif; letter-spacing:.14em; font-size:.7rem; color: var(--muted); }
.stButton > button, .stFormSubmitButton > button { background: var(--wine) !important; color: var(--cream) !important;
  border: none !important; border-radius: 999px !important; padding: .55rem 1.6rem !important;
  font-family: 'Aboreto', serif !important; letter-spacing: .14em; font-size: .78rem !important; }
.stButton > button:hover, .stFormSubmitButton > button:hover { background: var(--coral) !important; }
.stButton > button p, .stFormSubmitButton > button p { color: var(--cream) !important; font-family: 'Aboreto', serif !important; }
a.pill, a.pill:visited { text-decoration: none !important; color: var(--wine) !important; }
a.pill.solid, a.pill.solid:visited { color: var(--cream) !important; }
.nav a, .nav a:visited { text-decoration: none !important; }
table.score td:first-child { white-space: nowrap; }
[data-testid="stForm"] { background: var(--paper); border: 1px solid var(--line) !important; border-radius: 18px; padding: 1.4rem 1.6rem; }
div[data-baseweb="select"] > div, .stNumberInput input, .stTextInput input { background: var(--paper) !important; }
[data-testid="stExpander"] { background: var(--paper); border-radius: 14px; border-color: var(--line) !important; }
@media (max-width: 800px) { .hero, .steps { grid-template-columns: 1fr; } .nav a { margin-left: .8rem; } }
</style>
""", unsafe_allow_html=True)


def H(text):
    return html.escape(str(text))


def table_svg():
    """Six seats around a round table, the brand mark."""
    seats = []
    for k in range(6):
        a = np.pi / 2 + k * np.pi / 3
        x, y = 160 + 118 * np.cos(a), 160 - 118 * np.sin(a)
        fill = "#E4876A" if k % 2 else "#591D2F"
        seats.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{fill}"/>')
    return f'''<svg viewBox="0 0 320 320" width="100%" style="max-width:360px;display:block;margin:auto">
      <circle cx="160" cy="160" r="78" fill="#FBF8EE" stroke="#591D2F" stroke-width="1.5"/>
      <circle cx="160" cy="160" r="60" fill="none" stroke="#E2D8BC" stroke-width="1" stroke-dasharray="3 5"/>
      <text x="160" y="152" text-anchor="middle" font-family="EB Garamond, serif" font-style="italic" font-size="30" fill="#591D2F">for six</text>
      <text x="160" y="176" text-anchor="middle" font-family="Aboreto, serif" font-size="8" letter-spacing="1.6" fill="#6E6266">STRANGERS WELCOME</text>
      {"".join(seats)}
    </svg>'''


# ------------------------------------------------------------------ header and hero
st.markdown("""
<div class="nav"><div class="wordmark">TABLE FOR 6</div>
<div><a href="#how">How it works</a><a href="#find">Find your table</a><a href="#lab">The lab</a><a href="#methods">Methods</a></div></div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="hero">
  <div>
    <div class="eyebrow">Dinner, coffee or drinks with five strangers</div>
    <h1>Six strangers.<br>One table.</h1>
    <p class="lede">Tell us roughly where you live, when you're free and what you love.
    We find the five people you'd get along with, the place you'd all enjoy, and a time that doesn't
    send anyone across the Bay Bridge at rush hour.</p>
    <a class="pill solid" href="#find">Find my table</a><a class="pill" href="#lab">Compare the methods</a>
  </div>
  <div>{table_svg()}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="section" id="how"><div class="eyebrow">How it works</div><h2>Three answers in, one table out.</h2>
<p class="sub">Nothing you tell us is a filter. Every answer nudges a score, and an optimizer seats everyone at once
so that the whole city's evening is as good as it can be.</p></div>
<div class="steps">
 <div class="step"><div class="num">I</div><h3>You tell us a little</h3>
 <p>Neighborhood, free evenings, favorite cuisines, a few interests, and whether you'd like a mixed table.</p></div>
 <div class="step"><div class="num">II</div><h3>We solve for everyone</h3>
 <p>An integer program weighs taste, compatibility, travel time and bridge tolls, then picks every table, venue and time together.</p></div>
 <div class="step"><div class="num">III</div><h3>You show up</h3>
 <p>One message: where, when, and a hint about what you have in common. The rest is conversation.</p></div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ find your table
st.markdown("""<div class="section" id="find"><div class="eyebrow">Find your table</div>
<h2>Join tonight's crowd.</h2><p class="sub">Answer a few questions and we'll add you to a crowd of
simulated Bay Area guests. Then we seat everyone and show you where you'd be.</p></div>""",
            unsafe_allow_html=True)

hood_names = [h[0] for h in HOODS]
with st.form("profile_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
        hood = st.selectbox("Your neighborhood", hood_names, index=0)
        transport = st.radio("Getting there", ["Transit or walking", "Driving"], horizontal=True)
        age = st.slider("Age", 21, 60, 28)
        gender = st.selectbox("Gender", GENDERS, index=0)
        table_pref = st.radio("Table mix", ["Mixed is great", "Prefer same gender"], horizontal=True)
    with c2:
        interests = st.multiselect("A few interests (up to 5)", TAG_NAMES, default=["Hiking", "Live music", "Cooking"],
                                   max_selections=5)
        loves = st.multiselect("Cuisines you love", CUISINES, default=["Japanese", "Ethiopian"])
        budget = st.select_slider("Budget", ["$", "$$", "$$$"], value="$$")
    with c3:
        st.markdown("**What sounds fun?** (1 = not for me, 5 = yes please)")
        r_rest = st.slider("Dinner at a restaurant", 1, 5, 5)
        r_cafe = st.slider("Weekend coffee", 1, 5, 3)
        r_bar = st.slider("Drinks at a bar", 1, 5, 3)
        st.markdown("**When are you free?**")
        avail = [st.checkbox(s, value=(k != 1), key=f"slot{k}") for k, s in enumerate(SLOTS)]
    submitted = st.form_submit_button("Set my table")

if submitted:
    st.session_state.profile = dict(
        hood=hood_names.index(hood), car=(transport == "Driving"), age=age, gender=GENDERS.index(gender),
        same_gender=(table_pref == "Prefer same gender"),
        interests=tuple(TAG_NAMES.index(t) for t in interests),
        type_pref=(r_rest, r_cafe, r_bar),
        cuisine_pref=tuple(5 if c in loves else 2 for c in CUISINES),
        budget=["$", "$$", "$$$"].index(budget) + 1,
        avail=tuple(bool(a) for a in avail),
        slot_pref=tuple(1.0 if a else 0.0 for a in avail),
    )
profile = st.session_state.get("profile")

# ------------------------------------------------------------------ the lab controls
st.markdown("""<div class="section" id="lab"><div class="eyebrow">The lab</div>
<h2>Same guests, four ways to seat them.</h2><p class="sub">Every method below seats the exact same crowd.
Change the crowd or the priorities and watch how the answers move. The best value in each column is marked.</p></div>""",
            unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns([1.1, 1.1, 1.1, 1.2, 1])
with k1:
    N = st.select_slider("Guests", [12, 18, 24, 36, 48, 60], value=24,
                         help="Model A only runs up to 24 guests: past that it takes minutes.")
with k2:
    lam = st.slider("Value of time", 0.0, 0.3, 0.08, 0.02,
                    help="Satisfaction points a guest gives up per minute of travel (λ_d in the report).")
with k3:
    gamma = st.slider("Fairness", 0, 30, 0, 5,
                      help="Weight on the worst-off guest's score (γ in the report). 0 = maximize the total only.")
with k4:
    mode = st.selectbox("No-show rule", ["none", "expected", "chance"],
                        format_func={"none": "None", "expected": "Expected attendance ≥ 4.25",
                                     "chance": "90% chance of 4+ guests"}.get)
with k5:
    seed = st.number_input("Crowd", 0, 99, 0, help="Pick a different simulated crowd.")
run_a = N <= MODEL_A_MAX_N
if not run_a:
    st.caption(f"Model A is skipped above {MODEL_A_MAX_N} guests, because the exact MILP would need minutes. "
               "That gap is the point of Model B.")


@st.cache_data(show_spinner=False, max_entries=64)
def solve_everything(N, seed, lam, gamma, mode, profile_items, run_a):
    prof = dict(profile_items) if profile_items else None
    inst = build(N, seed, lam, float(gamma), mode, prof)
    sols = run_all(inst, run_a=run_a, a_time=20.0, seed=seed)
    return inst, sols


with st.spinner("Seating everyone… (Model A can take up to 20 seconds)"):
    pkey = tuple(sorted(profile.items())) if profile else None
    inst, sols = solve_everything(N, int(seed), float(lam), int(gamma), mode, pkey, run_a)

rows = scorecard(inst, sols)
methods = [r["Method"] for r in rows]

# ------------------------------------------------------------------ your table
if profile:
    found = find_user_table(sols["Model B"], 0)
    if found:
        d = describe_table(inst, *found)
        me = [g for g in d["guests"] if g["id"] == 0][0]
        others = [g for g in d["guests"] if g["id"] != 0]
        guests_html = "".join(
            f'<div class="guest"><span>{H(g["gender"])}, {g["age"]} · {H(g["hood"])}</span>'
            f'<span>{H(", ".join(g["interests"][:3]) or "open to anything")}</span></div>' for g in others)
        shared = "".join(f"<span>{H(t)} ×{n}</span>" for t, n in d["shared"]) or "<span>a bit of everything</span>"
        kind = d["cuisine"] + " " + d["venue_type"] if d["cuisine"] else d["venue_type"]
        st.markdown(f"""
<div class="yourtable">
 <div class="eyebrow">Your table, chosen by Model B</div>
 <h3>{H(d["venue"])}</h3>
 <p>{H(d["slot"])} · {H(kind)} · {H(d["price"])} · {d["size"]} guests ·
 your trip {me["minutes"]:.0f} min{" plus a $8 toll" if me["toll"] > 0 else ""}</p>
 <div class="chips" style="margin:.4rem 0 .8rem">{shared}</div>
 {guests_html}
</div>""", unsafe_allow_html=True)
        comp = []
        for m in methods:
            f = find_user_table(sols[m], 0)
            if f:
                dd = describe_table(inst, *f)
                mm = [g for g in dd["guests"] if g["id"] == 0][0]
                comp.append(f'<td>{H(dd["venue"])}<br><span class="meta">{H(dd["slot"])}</span></td>'
                            f'<td>{mm["minutes"]:.0f} min</td><td>{mm["value"]:.1f}</td>')
            else:
                comp.append('<td>No seat this round</td><td>–</td><td>–</td>')
        trs = "".join(f'<tr><td><span class="dot" style="background:{COLORS[m]}"></span>{m}</td>{c}</tr>'
                      for m, c in zip(methods, comp))
        st.markdown(f"""<div style="margin-top:1rem"><table class="score"><tr><th>Method</th><th>Where you'd be</th>
<th>Your trip</th><th>Your score</th></tr>{trs}</table></div>
<p class="sub" style="margin-top:.5rem">Another method can sometimes give <i>you</i> a better seat. Model B maximizes
everyone's evening at once, not any single guest's.</p>""", unsafe_allow_html=True)
    else:
        st.info("Model B couldn't fit you at a table this round (no open venue matched your free slots). "
                "Try adding another free evening.")

# ------------------------------------------------------------------ scorecard
cols = [("Total score", max, "{:.1f}"), ("Avg satisfaction (0-10)", max, "{:.2f}"), ("Avg trip (min)", min, "{:.1f}"),
        ("Guests paying a toll", min, "{:d}"), ("Worst-off guest", max, "{:.1f}"), ("Seated", None, "{}"),
        ("Solve time (s)", min, "{:.1f}")]
best = {}
for c, fn, _ in cols:
    if fn:
        best[c] = fn(r[c] for r in rows)
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
            txt += " (stopped)"
        tds += f'<td class="{"best" if isbest else ""}">{txt}</td>'
    body += f'<tr><td><span class="dot" style="background:{COLORS[r["Method"]]}"></span>{r["Method"]}</td>{tds}</tr>'
st.markdown(f'<div style="margin-top:1.4rem"><table class="score"><tr><th>Method</th>{head}</tr>{body}</table></div>',
            unsafe_allow_html=True)

b_total = [r for r in rows if r["Method"] == "Model B"][0]["Total score"]
notes = []
for r in rows:
    if r["Method"] != "Model B" and b_total > 0:
        notes.append(f'{r["Method"]} reaches <b>{100 * r["Total score"] / b_total:.0f}%</b> of Model B\'s total score')
st.markdown(f'<p class="sub" style="margin-top:.6rem">{"; ".join(notes)}.</p>', unsafe_allow_html=True)


# ------------------------------------------------------------------ maps
def map_fig(name):
    """Tile-free map: homes, venues and the lines between them, with the Bay drawn in."""
    sol = sols[name]
    x, y = [], []
    for S, v, t in sol.tables:
        for i in S:
            x += [inst.home[i, 1], inst.v_loc[v, 1], None]
            y += [inst.home[i, 0], inst.v_loc[v, 0], None]
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-122.385, x1=-122.31, y0=37.70, y1=37.92, fillcolor="#E3E9EE",
                  line=dict(width=0), layer="below")
    fig.add_annotation(x=-122.3475, y=37.725, text="<i>the Bay</i><br>$8 to cross west", showarrow=False,
                       font=dict(family="EB Garamond, serif", size=12, color="#4A6A86"))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(width=1.3, color=COLORS[name]), opacity=0.6,
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=inst.home[:, 1], y=inst.home[:, 0], mode="markers",
                             marker=dict(size=6, color="#2B2124"), hoverinfo="skip"))
    used = sorted({v for _, v, _ in sol.tables})
    fig.add_trace(go.Scatter(x=inst.v_loc[used, 1], y=inst.v_loc[used, 0], mode="markers",
                             marker=dict(size=15, color=COLORS[name], line=dict(color="#FBF8EE", width=2)),
                             text=[inst.v_name[v] for v in used], hovertemplate="%{text}<extra></extra>"))
    for h in HOODS:
        fig.add_annotation(x=h[2], y=h[1] + 0.012, text=h[0], showarrow=False,
                           font=dict(family="Inter, sans-serif", size=10, color="#6E6266"))
    if profile:
        fig.add_trace(go.Scatter(x=[inst.home[0, 1]], y=[inst.home[0, 0]], mode="markers+text",
                                 marker=dict(size=16, color="#E4876A", symbol="star", line=dict(color="#591D2F", width=1)),
                                 text=["you"], textposition="top right", hoverinfo="skip",
                                 textfont=dict(family="EB Garamond, serif", size=14, color="#591D2F")))
    m = [r for r in rows if r["Method"] == name][0]
    fig.update_xaxes(visible=False, range=[-122.53, -122.22])
    fig.update_yaxes(visible=False, range=[37.715, 37.895], scaleanchor="x", scaleratio=1 / np.cos(np.radians(37.8)))
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      paper_bgcolor="#FBF8EE", plot_bgcolor="#FBF8EE", dragmode=False)
    return fig, m


st.markdown("""<div class="section"><div class="eyebrow">On the map</div><h2>Who travels where.</h2>
<p class="sub">Each line joins a guest's home to their table's venue. Long lines across the water are bridge trips.</p></div>""",
            unsafe_allow_html=True)
grid = st.columns(2)
for k, name in enumerate(methods):
    fig, m = map_fig(name)
    with grid[k % 2]:
        st.markdown(f'<div class="method" style="border-color:{COLORS[name]}"><h4>{name}</h4>'
                    f'<p>Average trip {m["Avg trip (min)"]:.0f} min · {m["Guests paying a toll"]} tolls · '
                    f'{m["Seated"]} seated</p></div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"map_{name}")

# ------------------------------------------------------------------ table explorer
st.markdown("""<div class="section"><div class="eyebrow">Table explorer</div><h2>Pull up a chair.</h2>
<p class="sub">Every table a method set, with who's there and why they were grouped.</p></div>""",
            unsafe_allow_html=True)
pick = st.radio("Method", methods, index=methods.index("Model B"), horizontal=True, label_visibility="collapsed")
tables = [describe_table(inst, *x) for x in sols[pick].tables]
tables.sort(key=lambda d: -d["value"])
cards = st.columns(3)
for k, d in enumerate(tables):
    kind = (d["cuisine"] + " " if d["cuisine"] else "") + d["venue_type"]
    guests = "".join(
        f'<li>{"<b>You</b>" if g["id"] == 0 and profile else H(g["gender"]) + ", " + str(g["age"])} · {H(g["hood"])} · '
        f'{g["minutes"]:.0f} min{" · toll" if g["toll"] > 0 else ""}</li>' for g in d["guests"])
    shared = "".join(f"<span>{H(t)} ×{n}</span>" for t, n in d["shared"]) or "<span>no shared interest</span>"
    with cards[k % 3]:
        st.markdown(f"""<div class="tcard" style="border-top:3px solid {COLORS[pick]}">
<div class="meta">Table {k + 1} · {H(d["slot"])} · {H(kind)} · {H(d["price"])}</div>
<h4>{H(d["venue"])}</h4>
<div class="chips">{shared}</div>
<ul>{guests}</ul>
<div class="meta">Ages {d["age_range"][0]}–{d["age_range"][1]} · avg trip {d["avg_trip"]:.0f} min ·
compatibility {d["avg_pair"]:+.2f} · {100 * d["show_prob"]:.0f}% chance 4+ show up</div>
</div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ methods
st.markdown("""<div class="section" id="methods"><div class="eyebrow">Methods</div><h2>What's under the tablecloth.</h2>
<p class="sub">Every method maximizes the same score: each guest's satisfaction with the venue and time, plus how well
each pair gets along, minus travel time and tolls, minus a penalty for anyone left without a seat.</p></div>""",
            unsafe_allow_html=True)
mc = st.columns(4)
for k, name in enumerate(METHODS):
    one, two = BLURB[name]
    with mc[k]:
        st.markdown(f'<div class="method" style="border-color:{COLORS[name]}"><h4>{name}</h4><p><b>{one}</b></p><p>{two}</p></div>',
                    unsafe_allow_html=True)

with st.expander("The math, in one paragraph"):
    st.markdown(r"""
Model A uses binary variables $x_{ik}$ (guest $i$ sits at table $k$), $z_k$ (table $k$ opens) and
$y_{ijk}$ (guests $i$ and $j$ share table $k$), and maximizes
$\sum_{i,k} c_{ik}x_{ik} + \sum_{k}\sum_{i<j} q_{ij}y_{ijk} - M\sum_i u_i$
subject to $\sum_k x_{ik} + u_i = 1$, $\;L z_k \le \sum_i x_{ik} \le U z_k$, and $y_{ijk}\le x_{ik},\ y_{ijk}\le x_{jk}$.
Model B instead chooses whole tables $g$ with value $C_g$, solving
$\max \sum_g C_g\lambda_g - M\sum_i u_i$ s.t. $\sum_g A_{ig}\lambda_g + u_i = 1$ and $\sum_{g\in\mathcal G_{vt}}\lambda_g \le R_{vt}$.
Column generation adds a table only when its reduced cost $\bar C_g = C_g - \sum_{i\in S_g}\pi_i - \mu_{v_g t_g}$ is positive,
and weak duality gives a certified upper bound. The full write-up is in the report.
""")

st.markdown(f"""<div class="foot"><div>TABLE FOR 6 · IEOR 240 · FALL 2026</div>
<div><a href="{REPORT_URL}" style="color:var(--wine)">READ THE REPORT</a> · SIMULATED GUESTS, REAL MATH</div></div>""",
            unsafe_allow_html=True)
