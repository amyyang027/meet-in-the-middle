import math
import streamlit as st
from ui.theme import show, img, hero, H, VENUE_PHOTO
from ui.engine import solve_b, profile_form, profile_key, find_user_table, describe_table, TONIGHT_N

hero(img("candle_dinner", 2200), "The invitation", "Request a seat.",
     "Six questions. Then we seat you among tonight's guests and hand you a sealed card.", short=True)

show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">Part one</div>
<h2>Tell us <em>a little</em></h2><p>We add you to a crowd of simulated Bay Area guests and seat everyone with Model B,
our column-generation engine.</p></div></div>""")

profile_form()
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
  <text x="{x:.1f}" y="{y + 7:.1f}" text-anchor="middle" font-family="Cormorant Garamond, serif" font-style="italic"
    font-size="20" fill="{'#0A0D0C' if me else '#E6D2A2'}">{'you' if me else '?'}</text>
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
    show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">Part two</div>
<h2>Your <em>sealed card</em></h2></div></div>""")
    if not found:
        st.info("No table fit you this round: no open venue matched your free evenings. Try adding another evening.")
    else:
        d = describe_table(inst, *found)
        me = [g for g in d["guests"] if g["id"] == 0][0]
        others = [g for g in d["guests"] if g["id"] != 0]
        kind = (d["cuisine"] + " " if d["cuisine"] else "") + d["venue_type"]
        shared = "".join(f"<span>{H(t)} · {n} of you</span>" for t, n in d["shared"]) or "<span>a bit of everything</span>"
        toll = " + $8 toll" if me["toll"] > 0 else ""
        guests = "".join(
            f'<div class="guest"><b>Guest {k + 1}</b><span>{H(g["gender"])}, {g["age"]} · {H(g["hood"])}</span>'
            f'<span>{H(", ".join(g["interests"][:3]) or "open to anything")}</span></div>'
            for k, g in enumerate(others))
        show(f"""{wax()}<div class="letter" key="{st.session_state.get('sealed_at', 0)}">
<div style="display:grid;grid-template-columns:1.2fr 1fr;gap:2.4rem;align-items:center" class="lettergrid">
 <div>
  <div class="when">{H(d["slot"])} &nbsp;·&nbsp; {H(kind)} &nbsp;·&nbsp; {H(d["price"])}</div>
  <h2>{H(d["venue"].split(",")[0])}</h2>
  <p style="color:var(--mist);margin:0">{H(", ".join(d["venue"].split(",")[1:]).strip())}</p>
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
<div class="q reveal"><small>{H(d["slot"])}</small><p>See you at {H(d["venue"].split(",")[0])}.</p></div></div>""")
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Model B chose this seat to make the whole city's evening as good as possible, not any single guest's. "
                   "The Lab shows where the other methods would have put you.")
        with st.container(key="cta", horizontal=True, horizontal_alignment="center", gap="medium"):
            st.page_link("views/tonight.py", label="See every table tonight")
            st.page_link("views/lab.py", label="Compare the methods")
