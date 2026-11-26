import streamlit as st
from ui.theme import show, img, hero, H, VENUE_PHOTO
from ui.engine import solve_b, tables_of, dark_map, profile_key, TONIGHT_N
from ui.places import maps_link
from t6.data import SLOTS

hero(img("bridge_night", 2200), "Tonight's seating", "Every table, <br>one city.",
     f"{TONIGHT_N} guests, one plan, solved by Model B. Filter the evening, then pick a table to follow its threads across the map.",
     short=True)

prof = st.session_state.get("profile")
with st.spinner("Seating the city…"):
    inst, sol = solve_b(TONIGHT_N, 0, profile_key())
tables = tables_of(inst, sol)
order = sorted(range(len(tables)), key=lambda k: -tables[k]["value"])

show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">The map</div>
<h2>Gold threads, <em>short trips</em></h2><p>Each thread joins a guest's home to their table. Few of them cross the water,
because the bridge costs time and an $8 toll.</p></div></div>""")

f1, f2 = st.columns([1, 1], gap="large")
with f1:
    slot = st.pills("Hour", ["All"] + SLOTS, default="All", key="slot_f")
with f2:
    kind = st.pills("Room", ["All", "restaurant", "cafe", "bar"], default="All", key="kind_f",
                    format_func=lambda s: s.capitalize() if s != "All" else s)
shown = [k for k in order if (slot in (None, "All") or tables[k]["slot"] == slot)
         and (kind in (None, "All") or tables[k]["venue_type"] == kind)]

labels = {k: f'{tables[k]["venue"].split(",")[0]} · {tables[k]["slot"]}' for k in shown}
pick = st.pills("Follow a table", list(labels), format_func=labels.get, key="tbl_pick") if shown else None
st.plotly_chart(dark_map(inst, sol, highlight=pick, you=bool(prof), height=560), width="stretch",
                config={"displayModeBar": False}, key="tonight_map")

show(f"""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">The tables</div>
<h2>Pull up <em>a chair</em></h2><p>{len(shown)} of {len(tables)} tables match. Hover a card to meet the guests.</p></div></div>""")

cols = st.columns(3, gap="medium")
for j, k in enumerate(shown):
    d = tables[k]
    kindtxt = (d["cuisine"] + " " if d["cuisine"] else "") + d["venue_type"]
    shared = "".join(f"<span>{H(t)}</span>" for t, n in d["shared"][:3]) or "<span>a bit of everything</span>"
    guests = "".join(
        f'<li><span>{"<b style=color:var(--gold2)>You</b>" if (g["id"] == 0 and prof) else H(g["gender"]) + ", " + str(g["age"])}</span>'
        f'<i>{H(g["hood"])} · {g["minutes"]:.0f}′{" · toll" if g["toll"] > 0 else ""}</i></li>' for g in d["guests"])
    border = "border-color:var(--gold)" if pick == k else ""
    with cols[j % 3]:
        show(f"""<div class="tcard reveal" style="{border}"><div class="ph" style="background-image:url('{img(VENUE_PHOTO[d["venue_type"]], 900)}')"></div>
<div class="top"><span>No. {order.index(k) + 1:02d}</span><span>{H(d["slot"])}</span></div>
<div class="body"><h4>{H(d["venue"].split(",")[0])}</h4>
<div class="kind">{H(kindtxt.capitalize())} · {H(d["price"])} · {H(", ".join(d["venue"].split(",")[1:]).strip())}</div>
<div class="chips">{shared}</div>
<ul>{guests}</ul>
<div class="kind" style="margin-top:.6rem">Avg trip {d["avg_trip"]:.0f} min · {100 * d["show_prob"]:.0f}% chance 4+ show</div>
<a class="maplink" href="{maps_link(d["venue"].split(",")[0], d["addr"])}" target="_blank">{H(d["addr"] or "Find it")} ↗</a>
</div></div>""")
