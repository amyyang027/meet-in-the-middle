import streamlit as st
from ui.theme import show, img, hero, HERO_LOCAL
from t6.data import HOODS

# the hero photo carries its own oval logo, so the nav seal steps aside on this page
st.markdown('<style>.st-key-topnav .seal{visibility:hidden} .hero .ph{top:5.4rem !important; background-position:center top !important;}</style>', unsafe_allow_html=True)

hero(HERO_LOCAL, "San Francisco &nbsp;·&nbsp; East Bay &nbsp;·&nbsp; By invitation",
     "Six strangers.<br>One table.",
     "Tell us a little. We find the five people you'd get along with, the room you'd all love, "
     "and an hour that doesn't send anyone across the Bay Bridge at rush hour.",
     corner="Scroll for the evening", pos="center top")

show("""<div class="sec"><div class="reveal center"><div class="eyebrow">The house rules</div>
<p class="statement">We don't do small talk with whoever's nearby. We do <em>the right five strangers</em>,
the right room, and the right hour, chosen <em>all at once</em> for everyone in the city.</p>
<hr class="rule"></div></div>""")

names = [h[0] for h in HOODS] * 2
track = "".join(f'<span>{n}</span><span class="dot">✦</span>' for n in names)
show(f'<div class="fullbleed marquee"><div class="track">{track}{track}</div></div>')

show(f"""<div class="sec"><div class="sechead reveal"><div class="eyebrow">The evening, in three acts</div>
<h2>How a table <em>comes together</em></h2><p>Hover over each act.</p></div><br>
<div class="acts">
 <div class="act reveal"><div class="ph" style="background-image:url('{img("glasses_up", 1100)}')"></div>
  <div class="txt"><div class="num">I.</div><h3>The invitation</h3>
  <div class="more">Neighborhood, free evenings, cuisines you love, a few interests, and whether you'd like a mixed table.
  None of it is a filter. Every answer quietly nudges a score.</div><div class="line"></div></div></div>
 <div class="act reveal"><div class="ph" style="background-image:url('{img("lamps", 1100)}')"></div>
  <div class="txt"><div class="num">II.</div><h3>The seating</h3>
  <div class="more">An integer program weighs taste, chemistry between every pair of guests, travel time and bridge tolls,
  then chooses every table, venue and hour together.</div><div class="line"></div></div></div>
 <div class="act reveal"><div class="ph" style="background-image:url('{img("laughing", 1100)}')"></div>
  <div class="txt"><div class="num">III.</div><h3>The table</h3>
  <div class="more">One sealed message: where, when, and a hint about what the six of you share.
  The rest is conversation.</div><div class="line"></div></div></div>
</div></div>""")

show(f"""<div class="fullbleed band"><div class="ph" style="background-image:url('{img("bridge_fog", 2200)}')"></div>
<div class="q reveal"><small>A note on geography</small>
<p>"The city is seven miles wide. Your table should feel a little closer than that."</p></div></div>""")

show(f"""<div class="sec"><div class="split">
 <div class="frame reveal-img reveal"><div class="ph" style="background-image:url('{img("candle_dinner", 1400)}')"></div></div>
 <div class="reveal"><div class="eyebrow">Who's coming</div>
  <h2 style="font-size:clamp(2.4rem,4.6vw,4rem);line-height:1;margin:0 0 1.2rem">Names are revealed <em style="color:var(--gold2)">at the table.</em></h2>
  <p>Until then, you get a hint: their neighborhoods, an age range, and the interests the six of you share.
  We think a little mystery is good for an evening.</p>
  <p style="color:var(--mist)">Behind the curtain, a column-generation engine considers hundreds of thousands of possible
  tables and keeps the few hundred worth seating. In our tests it lands within about one percent of the
  best possible seating plan, in seconds.</p></div>
</div></div>""")

show(f"""<div class="fullbleed spot"><div class="ph" style="background-image:url('{img("toast_white", 2200)}')"></div>
<div class="glow"></div><div class="msg"><p>Someone is already holding your seat.</p>
<small>Move your cursor to find them</small></div></div>""")

show(f"""<div class="sec"><div class="sechead reveal"><div class="eyebrow">Where we seat you</div>
<h2>Three kinds of <em>evening</em></h2><p>A long dinner, a slow weekend coffee, or a round of drinks. We match the room to the table.</p></div><br>
<div class="trio">
 <div class="venue reveal"><div class="ph" style="background-image:url('{img("dark_dining2", 1500)}')"></div>
   <div class="lab"><span>Fri &amp; Sat · 7 pm</span><b>Restaurants</b></div></div>
 <div class="venue reveal"><div class="ph" style="background-image:url('{img("cafe", 900)}')"></div>
   <div class="lab"><span>Sat · 11 am</span><b>Cafés</b></div></div>
 <div class="venue reveal"><div class="ph" style="background-image:url('{img("cocktail", 900)}')"></div>
   <div class="lab"><span>Fri &amp; Sat · 7 pm</span><b>Bars</b></div></div>
</div></div>""")

show("""<div class="sec tight"><div class="eyebrow reveal">By the numbers</div><div class="stats reveal">
 <div class="stat"><b>~1%</b><span>from the best possible seating plan, on cases small enough to prove it</span></div>
 <div class="stat"><b>−54%</b><span>shorter trips once a minute of travel has a price</span></div>
 <div class="stat"><b>4.2%</b><span>of tables fall below four guests after no-shows, down from 15.3%</span></div>
 <div class="stat"><b>240</b><span>guests seated in about three and a half minutes</span></div>
</div></div>""")

show(f"""<div class="fullbleed band" style="height:70vh"><div class="ph" style="background-image:url('{img("candles_row", 2200)}')"></div>
<div class="q reveal"><small>Tonight</small><p>Your seat is waiting.</p></div></div>""")

st.markdown("<br><br>", unsafe_allow_html=True)
with st.container(key="cta", horizontal=True, horizontal_alignment="center", gap="medium"):
    st.page_link("views/invitation.py", label="Request an invitation")
    st.page_link("views/lab.py", label="Compare the methods")
