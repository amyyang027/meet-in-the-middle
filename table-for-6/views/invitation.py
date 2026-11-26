import math
import streamlit as st
from ui.theme import show, img, hero, H, VENUE_PHOTO
from ui.engine import solve_b, profile_key, find_user_table, describe_table, TONIGHT_N
from ui.places import find_place, maps_link
from t6.data import HOODS, SLOTS, CUISINES, TAG_NAMES, GENDERS, TYPES

hero(img("candle_dinner", 2200), "The invitation", "Request a seat.",
     "Six short questions, one sealed card. Your answers never filter anyone out: they only nudge the score.",
     short=True)

STEPS = ["Where", "Who", "Mood", "Talk", "When", "Seal"]
LIKE = ["Not for me", "Maybe", "Yes please"]
DEFAULTS = dict(hood=None, transport="Transit or walking", age=28, gender="Woman", mix="Mixed is great",
                dinner="Yes please", coffee="Maybe", drinks="Yes please", budget="$$", cuisines=["Japanese", "Italian"],
                interests=["Live music", "Cooking", "Film"], slots=["Fri 7pm", "Sat 7pm"], spot_q="", spot=None)
if "ans" not in st.session_state:
    st.session_state.ans = dict(DEFAULTS)
if "step" not in st.session_state:
    st.session_state.step = 0
A = st.session_state.ans
step = st.session_state.step


def go(k):
    st.session_state.step = k


def keep(name, value):
    A[name] = value
    return value


# ---------------------------------------------------------------- progress rail
rail = "".join(
    f'<div class="st {"done" if k < step else "on" if k == step else ""}"><b>{["I", "II", "III", "IV", "V", "VI"][k]}</b>'
    f'<span>{s}</span></div>' for k, s in enumerate(STEPS))
show(f"""<div class="sec tight" style="padding-bottom:1.2rem"><div class="rail">{rail}
<div class="bar"><i style="width:{100 * step / (len(STEPS) - 1):.0f}%"></i></div></div></div>""")

QUESTIONS = [
    ("Where does your evening <em>begin?</em>", "Pick the neighborhood closest to home. We'll keep your trip short."),
    ("A little about <em>you</em>", "Used only to balance the table. Nobody sees your answers."),
    ("What sets <em>the mood?</em>", "Tell us how you like to spend an evening, and what you like to eat."),
    ("What would you <em>talk about?</em>", "Choose up to five. Shared interests are the strongest pull at the table."),
    ("When are you <em>free?</em>", "Choose every evening that works. You can also name a favorite spot."),
    ("Ready to <em>seal it?</em>", "Check your answers, then seal the card. We'll seat the whole city at once."),
]
q, sub = QUESTIONS[step]

with st.container(key="wizard"):
    show(f'<div class="qhead"><div class="eyebrow">Question {step + 1} of {len(STEPS)}</div><h2>{q}</h2><p>{sub}</p></div>')
    hood_names = [h[0] for h in HOODS]

    if step == 0:
        keep("hood", st.pills("Neighborhood", hood_names, default=A["hood"], key="w_hood", label_visibility="collapsed"))
        keep("transport", st.segmented_control("Getting there", ["Transit or walking", "Driving"],
                                               default=A["transport"], key="w_tr") or A["transport"])
        if A["transport"] == "Driving":
            st.caption("Driving west across the Bay Bridge costs about $8. The optimizer knows.")
    elif step == 1:
        keep("age", st.slider("Age", 21, 60, A["age"], key="w_age"))
        c1, c2 = st.columns(2, gap="large")
        with c1:
            keep("gender", st.segmented_control("Gender", GENDERS, default=A["gender"], key="w_g") or A["gender"])
        with c2:
            keep("mix", st.segmented_control("Table mix", ["Mixed is great", "Prefer same gender"], default=A["mix"],
                                             key="w_mix") or A["mix"])
    elif step == 2:
        c1, c2, c3 = st.columns(3, gap="large")
        for col, name, label in [(c1, "dinner", "A long dinner"), (c2, "coffee", "Weekend coffee"), (c3, "drinks", "Drinks at a bar")]:
            with col:
                keep(name, st.segmented_control(label, LIKE, default=A[name], key=f"w_{name}") or A[name])
        keep("budget", st.segmented_control("Budget", ["$", "$$", "$$$"], default=A["budget"], key="w_b") or A["budget"])
        keep("cuisines", st.pills("Cuisines you love", CUISINES, default=A["cuisines"], selection_mode="multi", key="w_c"))
    elif step == 3:
        picked = st.pills("Interests", TAG_NAMES, default=A["interests"], selection_mode="multi", key="w_i",
                          label_visibility="collapsed")
        if len(picked) > 5:
            st.caption("Five is plenty. We'll keep your first five.")
        keep("interests", picked[:5])
    elif step == 4:
        keep("slots", st.pills("Evenings", SLOTS, default=A["slots"], selection_mode="multi", key="w_s"))
        show('<div class="eyebrow" style="margin:1.8rem 0 .2rem">Optional · your own spot</div>'
             '<p style="color:var(--mist);margin:0 0 .6rem">Name a restaurant, café or bar you love. If we find it on the map, '
             'the optimizer counts it as a strong favorite for you. If we can\'t find it, we simply leave it out.</p>')
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            spot_q = st.text_input("Favorite spot", value=A["spot_q"], key="w_spot",
                                   placeholder="e.g. Zuni Cafe, Tartine, Comal…", label_visibility="collapsed")
        with c2:
            look = st.button("Find it", key="w_find", width="stretch")
        if look or (spot_q and spot_q != A["spot_q"]):
            A["spot_q"] = spot_q
            with st.spinner("Searching the map…"):
                A["spot"] = find_place(spot_q) or ("missing" if spot_q.strip() else None)
        sp = A["spot"]
        if isinstance(sp, dict):
            show(f"""<div class="found"><span class="tag">Found on {H(sp["source"])}</span>
<b>{H(sp["name"])}</b><span>{H(TYPES[sp["type"]].capitalize())} · {H(sp["addr"] or "address on the map")}</span>
<a href="{maps_link(sp["name"], sp["addr"])}" target="_blank">Open in Google Maps ↗</a></div>""")
            if st.button("Remove this spot", key="w_rm"):
                A["spot"], A["spot_q"] = None, ""
                st.rerun()
        elif sp == "missing":
            show(f'<div class="found miss"><b>We couldn\'t find “{H(A["spot_q"])}”</b><span>No restaurant, café or bar by that name '
                 'in San Francisco or the inner East Bay. We\'ll disregard it and choose for you.</span></div>')
    else:
        sp = A["spot"] if isinstance(A["spot"], dict) else None
        rows = [("Starting from", f'{A["hood"] or "—"} · {A["transport"].lower()}'),
                ("You", f'{A["age"]} · {A["gender"]} · {A["mix"].lower()}'),
                ("Evenings", ", ".join(A["slots"]) or "—"),
                ("Mood", f'Dinner: {A["dinner"].lower()} · Coffee: {A["coffee"].lower()} · Drinks: {A["drinks"].lower()} · {A["budget"]}'),
                ("Cuisines", ", ".join(A["cuisines"]) or "no strong preference"),
                ("Talk about", ", ".join(A["interests"]) or "anything"),
                ("Favorite spot", sp["name"] if sp else "none, surprise me")]
        show('<div class="review">' + "".join(f'<div><span>{k}</span><b>{H(v)}</b></div>' for k, v in rows) + '</div>')

    # ---- navigation
    problems = []
    if step == 0 and not A["hood"]:
        problems.append("Pick a neighborhood to continue.")
    if step == 4 and not A["slots"]:
        problems.append("Pick at least one evening.")
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    with st.container(key="wiznav", horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
        if step > 0:
            st.button("← Back", key="w_back", on_click=go, args=(step - 1,))
        else:
            st.markdown("&nbsp;")
        if problems:
            st.caption(problems[0])
        if step < len(STEPS) - 1:
            st.button("Continue →", key="w_next", on_click=go, args=(step + 1,), disabled=bool(problems))
        else:
            seal = st.button("Seal my invitation", key="w_seal", disabled=not (A["hood"] and A["slots"]))

LV = {"Not for me": 1, "Maybe": 3, "Yes please": 5}
if step == len(STEPS) - 1 and seal:
    sp = A["spot"] if isinstance(A["spot"], dict) else None
    st.session_state.profile = dict(
        hood=hood_names.index(A["hood"]), car=(A["transport"] == "Driving"), age=A["age"],
        gender=GENDERS.index(A["gender"]), same_gender=(A["mix"] == "Prefer same gender"),
        interests=tuple(TAG_NAMES.index(t) for t in A["interests"]),
        type_pref=(LV[A["dinner"]], LV[A["coffee"]], LV[A["drinks"]]),
        cuisine_pref=tuple(5 if c in A["cuisines"] else 2 for c in CUISINES),
        budget=["$", "$$", "$$$"].index(A["budget"]) + 1,
        avail=tuple(s in A["slots"] for s in SLOTS),
        slot_pref=tuple(1.0 if s in A["slots"] else 0.0 for s in SLOTS),
        spot=(sp["name"], round(sp["lat"], 5), round(sp["lon"], 5), sp["type"], sp["cuisine"], sp["addr"]) if sp else None,
    )
    st.session_state.sealed_at = st.session_state.get("sealed_at", 0) + 1
prof = st.session_state.get("profile")


def wax():
    return """<div class="waxwrap"><svg class="wax" viewBox="0 0 120 120">
<defs><radialGradient id="wg" cx="40%" cy="35%"><stop offset="0" stop-color="#8E3446"/><stop offset="1" stop-color="#4A1522"/></radialGradient></defs>
<path d="M60 6 C78 8 92 4 102 18 C116 30 110 46 114 60 C116 78 112 94 98 104 C84 116 70 110 58 114 C42 116 26 112 16 100 C4 86 10 72 6 58 C4 42 8 26 22 16 C34 6 46 4 60 6Z" fill="url(#wg)"/>
<circle cx="60" cy="60" r="34" fill="none" stroke="#2E0C14" stroke-width="2" opacity=".6"/>
<text x="60" y="74" text-anchor="middle" font-family="Cormorant Garamond, serif" font-style="italic" font-size="42" fill="#C47A86">6</text></svg></div>"""


def round_table(d, me_id=0):
    """Animated round table: seats pop in one by one; hover a seat for a hint about that guest."""
    n = d["size"]
    parts = []
    for k, g in enumerate(d["guests"]):
        a = -math.pi / 2 + 2 * math.pi * k / n
        x, y = 220 + 150 * math.cos(a), 220 + 150 * math.sin(a)
        me = g["id"] == me_id
        tip = "You" if me else f'{g["gender"]}, {g["age"]} · {g["hood"]}'
        sub = ", ".join(g["interests"][:2]) if not me else f'{g["minutes"]:.0f} min away'
        ty = y - 46 if y < 220 else y + 56
        parts.append(f'''<g class="s" style="animation-delay:{2.6 + .25 * k:.2f}s">
<circle class="c" cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{'#C8A96A' if me else '#15221F'}" stroke="#C8A96A" stroke-width="1"/>
<text x="{x:.1f}" y="{y + 7:.1f}" text-anchor="middle" font-family="Cormorant Garamond, serif" font-style="italic" font-size="20" fill="{'#0A0D0C' if me else '#E6D2A2'}">{'you' if me else '?'}</text>
<g class="tip"><rect x="{x - 92:.1f}" y="{ty - 18:.1f}" width="184" height="40" fill="#0A0D0C" stroke="#C8A96A" stroke-width=".6"/>
<text x="{x:.1f}" y="{ty - 1:.1f}" text-anchor="middle" font-family="Jost, sans-serif" font-size="11" fill="#EEE7D8">{H(tip)}</text>
<text x="{x:.1f}" y="{ty + 14:.1f}" text-anchor="middle" font-family="Jost, sans-serif" font-size="9.5" fill="#9C978C">{H(sub)}</text></g>
</g>''')
    return f'''<svg class="roundtable" viewBox="0 0 440 440">
<circle cx="220" cy="220" r="96" fill="#0F1614" stroke="#C8A96A" stroke-width=".8"/>
<circle cx="220" cy="220" r="82" fill="none" stroke="rgba(200,169,106,.3)" stroke-dasharray="2 6"/>
<text x="220" y="214" text-anchor="middle" font-family="Cormorant Garamond, serif" font-style="italic" font-size="30" fill="#EEE7D8">table for {n}</text>
<text x="220" y="240" text-anchor="middle" font-family="Jost, sans-serif" letter-spacing="3" font-size="9" fill="#C8A96A">HOVER A SEAT</text>
{"".join(parts)}</svg>'''


if prof:
    with st.spinner("Seating the city…"):
        inst, sol = solve_b(TONIGHT_N, 0, profile_key())
    found = find_user_table(sol, 0)
    show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">Your card</div>
<h2>Sealed, <em>and delivered</em></h2></div></div>""")
    if not found:
        st.info("No table fit you this round: no open venue matched your free evenings. Try adding another evening.")
    else:
        d = describe_table(inst, *found)
        me = [g for g in d["guests"] if g["id"] == 0][0]
        others = [g for g in d["guests"] if g["id"] != 0]
        kind = (d["cuisine"] + " " if d["cuisine"] else "") + d["venue_type"]
        shared = "".join(f"<span>{H(t)} · {n} of you</span>" for t, n in d["shared"]) or "<span>a bit of everything</span>"
        toll = " + $8 toll" if me["toll"] > 0 else ""
        vname = d["venue"].split(",")[0]
        spot = prof.get("spot")
        is_fav = bool(spot) and d["v"] == inst.V - 1
        fav_note = ""
        if spot and is_fav:
            fav_note = '<div class="favbadge">✦ Your pick. The optimizer seated your table at your favorite spot.</div>'
        elif spot:
            fav_note = (f'<div class="favbadge dim">Your pick, {H(spot[0])}, didn\'t make the final plan this time: '
                        'it was a better evening for the whole table somewhere else.</div>')
        guests = "".join(
            f'<div class="guest"><b>Guest {k + 1}</b><span>{H(g["gender"])}, {g["age"]} · {H(g["hood"])}</span>'
            f'<span>{H(", ".join(g["interests"][:3]) or "open to anything")}</span></div>'
            for k, g in enumerate(others))
        show(f"""{wax()}<div class="letter">
<div class="lettergrid" style="display:grid;grid-template-columns:1.2fr 1fr;gap:2.4rem;align-items:center">
<div>
<div class="when">{H(d["slot"])} &nbsp;·&nbsp; {H(kind)} &nbsp;·&nbsp; {H(d["price"])}</div>
<h2>{H(vname)}</h2>
<p style="color:var(--mist);margin:0">{H(d["addr"] or ", ".join(d["venue"].split(",")[1:]).strip())}</p>
<a class="maplink" href="{maps_link(vname, d['addr'])}" target="_blank">Open in Google Maps ↗</a>
{fav_note}
<div class="facts"><div><b>{d["size"]}</b><span>guests</span></div>
<div><b>{me["minutes"]:.0f}′</b><span>your trip{toll}</span></div>
<div><b>{d["age_range"][0]}–{d["age_range"][1]}</b><span>ages</span></div>
<div><b>{100 * d["show_prob"]:.0f}%</b><span>chance 4+ show</span></div></div>
<div class="eyebrow" style="margin-bottom:.4rem">What you share</div><div class="chips">{shared}</div>
</div>
<div>{round_table(d)}</div>
</div>
<div class="eyebrow" style="margin:2.2rem 0 .8rem">Your five strangers</div><div class="guests">{guests}</div>
</div>""")
        vp = img(VENUE_PHOTO[d["venue_type"]], 2000)
        show(f"""<div class="fullbleed band" style="height:60vh;margin-top:5rem"><div class="ph" style="background-image:url('{vp}')"></div>
<div class="q reveal"><small>{H(d["slot"])}</small><p>See you at {H(vname)}.</p></div></div>""")
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Venues are real places from OpenStreetMap; the other guests are simulated. Model B chose this seat to make "
                   "the whole city's evening as good as possible, not any single guest's.")
        with st.container(key="cta", horizontal=True, horizontal_alignment="center", gap="medium"):
            st.page_link("views/tonight.py", label="See every table tonight")
            st.page_link("views/lab.py", label="Compare the methods")
