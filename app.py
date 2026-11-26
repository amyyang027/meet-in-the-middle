"""Meet in the Middle: find the fairest dance-practice spot (and a place to eat after).

Run locally:   streamlit run app.py
Deploy free:   push to GitHub -> share.streamlit.io -> "New app" -> pick app.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from meetup import geo
from meetup.optimize import (OBJECTIVES, compare_objectives, member_costs, plan_season,
                             plan_season_greedy)
from meetup.sample import SAMPLE_MEMBERS, SAMPLE_STUDIOS, host_option_map
from meetup.scenarios import DEFAULT_SLOTS, build_instance

st.set_page_config(page_title="Meet in the Middle", page_icon="💃", layout="wide")
st.title("💃 Meet in the Middle")
st.caption("Find the practice spot and time that is fair for everyone's commute, with traffic risk "
           "included. Free map data from OpenStreetMap and OSRM. Nothing you type is saved.")

# ------------------------------------------------------------------ sidebar settings
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Venue data", ["Live (OpenStreetMap)", "Demo (offline sample)"],
                    help="Demo mode uses made-up venues and straight-line travel times.")
    focus = st.selectbox("What matters most?", list(OBJECTIVES), index=2,
                         format_func=lambda k: OBJECTIVES[k])
    alpha = st.slider("How bad a day should we plan for? (CVaR level)", 0.5, 0.99, 0.9, 0.01,
                      help="0.9 means: average over the worst 10% of traffic days.")
    slots = st.multiselect("Possible practice times", list(DEFAULT_SLOTS),
                           default=["Sat 10:00 AM", "Sat 2:00 PM", "Sun 4:00 PM",
                                    "Weeknight 7:30 PM"])
    n_cand = st.slider("Studios to consider", 5, 30, 15)
    food = st.toggle("Also pick a place to eat after practice")
    cuisine = st.selectbox("Cuisine", geo.CUISINES, disabled=not food)
    late = st.number_input("A round trip is 'too long' after (minutes)", 20, 300, 90, 5)

st.subheader("1. Who's coming?")
st.write("A city or neighborhood is enough (for example *Berkeley* or *SF Mission*). "
         "You can also type a full address or `lat, lon`. Tick **Can host** if practice can be at "
         "your place.")
default_df = pd.DataFrame([{"Name": n, "Location": loc.title(), "Can host": h}
                           for n, loc, h in SAMPLE_MEMBERS])
members_df = st.data_editor(default_df, num_rows="dynamic", width="stretch",
                            key="members")


def _google_key() -> str | None:
    try:
        return st.secrets.get("GOOGLE_MAPS_KEY")
    except Exception:
        return None


# ------------------------------------------------------------------ build + solve
def run():
    df = members_df.dropna(subset=["Name", "Location"])
    df = df[df["Location"].astype(str).str.strip() != ""]
    if len(df) < 2:
        st.error("Add at least two people.")
        return None
    if not slots:
        st.error("Pick at least one practice time.")
        return None
    names = df["Name"].astype(str).tolist()
    hosts = df["Can host"].fillna(False).astype(bool).tolist()
    status = st.status("Working it out…", expanded=True)
    homes = []
    for name, loc in zip(names, df["Location"].astype(str)):
        try:
            lat, lon, src = geo.geocode(loc)
        except ValueError as e:
            status.update(label="Couldn't find a location", state="error")
            st.error(str(e))
            return None
        homes.append((lat, lon))
    status.write(f"Found {len(homes)} locations.")
    center = geo.geometric_median(homes)
    spread = max(geo.haversine_km(center, h) for h in homes)
    radius = float(np.clip(0.8 * spread + 5, 5, 40))

    studios: list[geo.Place] = []
    if mode.startswith("Live"):
        try:
            studios = geo.nearest_to(geo.find_studios(center, radius), center, n_cand)
            status.write(f"Found {len(studios)} dance studios on OpenStreetMap within {radius:.0f} km.")
        except Exception as e:
            status.write(f"Studio search failed ({type(e).__name__}); using sample venues.")
    if not studios:
        studios = [geo.Place(f"Sample studio ({c.title()})", *geo.BAY_AREA_PLACES[c])
                   for c in SAMPLE_STUDIOS][:n_cand]
    host_places = [geo.Place(f"{n}'s place", *homes[i], kind="home", owner=i)
                   for i, n in enumerate(names) if hosts[i]]
    venues = studios + host_places

    rests: list[geo.Place] = []
    if food:
        if mode.startswith("Live"):
            try:
                rests = geo.nearest_to(geo.find_restaurants(center, radius, cuisine), center, 10)
                status.write(f"Found {len(rests)} {cuisine} places.")
            except Exception as e:
                status.write(f"Restaurant search failed ({type(e).__name__}).")
        if not rests:
            rests = [geo.Place(f"Sample {cuisine} spot ({c.title()})", *geo.BAY_AREA_PLACES[c],
                               kind="restaurant") for c in ["oakland", "san mateo", "fremont"]]

    points = homes + [(v.lat, v.lon) for v in venues] + [(r.lat, r.lon) for r in rests]
    if mode.startswith("Live"):
        ff, source = geo.drive_matrix(points)
    else:
        ff, source = geo.fallback_minutes(points), "straight-line estimate (demo mode)"
    I, J = len(homes), len(venues)
    host_of_venue = {}
    for j, v in enumerate(venues):
        if v.owner is not None:
            host_of_venue[j] = v.owner
            ff[v.owner, I + j] = ff[I + j, v.owner] = 0.0
    status.write(f"Drive times from: {source}.")

    chosen_slots = {s: DEFAULT_SLOTS[s] for s in slots}
    key = _google_key()
    if key and mode.startswith("Live"):
        status.write("Google key found: calibrating traffic for each time slot.")
        chosen_slots = _calibrate_with_google(key, homes, venues, ff, chosen_slots, status)

    inst = build_instance(ff, homes=list(range(I)), venues=list(range(I, I + J)),
                          members=names, venue_names=[v.name for v in venues],
                          slots=chosen_slots, n_scenarios=100 if food else 300,
                          restaurants=list(range(I + J, I + J + len(rests))) or None,
                          restaurant_names=[r.name for r in rests],
                          host_of_venue=host_of_venue, seed=42,
                          bridge=geo.bridge_crossings(points))
    status.write(f"Simulated {inst.C.shape[2]} traffic days for {inst.C.shape[1]} options.")
    results = compare_objectives(inst.C, alpha)
    status.update(label="Done!", state="complete", expanded=False)
    return dict(inst=inst, results=results, homes=homes, venues=venues, rests=rests,
                source=source, names=names)


def _calibrate_with_google(key, homes, venues, ff, slots, status):
    """Use Google traffic-aware times (one small matrix per slot) to set slot intensities."""
    import datetime as dt
    from meetup.scenarios import calibrate_intensity
    sample_v = venues[: max(1, 100 // len(homes))]
    I = len(homes)
    out = {}
    today = dt.date.today()
    targets = {"Sat": 5, "Sun": 6, "Fri": 4, "Weeknight": 2}
    for name, c in slots.items():
        day, clock = name.split(" ", 1)
        hh, rest = clock.split(":")
        mm, ampm = rest.split(" ")
        hour = int(hh) % 12 + (12 if ampm == "PM" else 0)
        days_ahead = (targets[day] - today.weekday()) % 7 or 7
        when = dt.datetime.combine(today + dt.timedelta(days=days_ahead), dt.time(hour, int(mm)))
        try:
            G = geo.google_traffic_matrix(homes, [(v.lat, v.lon) for v in sample_v], key,
                                          when.strftime("%Y-%m-%dT%H:%M:00-08:00"))
            c_hat = calibrate_intensity(ff[:I, I:I + len(sample_v)], G)
            out[name] = c_hat if np.isfinite(c_hat) else c
            status.write(f"{name}: traffic intensity {out[name]:.2f} (default {c:.2f})")
        except Exception as e:
            status.write(f"{name}: Google call failed ({type(e).__name__}); using default.")
            out[name] = c
    return out


if st.button("Find our spot", type="primary"):
    st.session_state["res"] = run()

res = st.session_state.get("res")
if not res:
    st.stop()

inst, results = res["inst"], res["results"]


def describe(o: int) -> dict:
    opt = inst.options[o]
    d = {"Where": inst.venues[opt["venue"]], "When": inst.slots[opt["slot"]]}
    if opt["restaurant"] is not None:
        d["Eat at"] = inst.restaurants[opt["restaurant"]]
    return d


# ------------------------------------------------------------------ results
best = results[focus]
st.subheader("2. Our pick")
pick = describe(best["option"])
cols = st.columns(4)
cols[0].metric("Practice at", pick["Where"])
cols[1].metric("When", pick["When"])
cols[2].metric("Longest average trip", f"{best['avg longest trip (min)']:.0f} min")
cols[3].metric(f"Chance someone takes > {late} min",
               f"{(inst.C[:, best['option'], :].max(0) > late).mean():.0%}")
if "Eat at" in pick:
    st.write(f"🍜 After practice: **{pick['Eat at']}**")

left, right = st.columns([3, 2])
with left:
    try:
        import folium
        from streamlit_folium import st_folium
        homes = res["homes"]
        m = folium.Map(location=geo.geometric_median(homes), zoom_start=10, tiles="cartodbpositron")
        for n, (lat, lon) in zip(res["names"], homes):
            folium.CircleMarker((round(lat, 2), round(lon, 2)), radius=8, color="#2563eb",
                                fill=True, tooltip=f"{n} (approx.)").add_to(m)
        chosen_v = inst.options[best["option"]]["venue"]
        for j, v in enumerate(res["venues"]):
            if v.kind == "home" and j != chosen_v:
                continue
            folium.Marker((v.lat if v.kind != "home" else round(v.lat, 2),
                           v.lon if v.kind != "home" else round(v.lon, 2)), tooltip=v.name,
                          icon=folium.Icon(color="red" if j == chosen_v else "lightgray",
                                           icon="star" if j == chosen_v else "music")).add_to(m)
        r = inst.options[best["option"]]["restaurant"]
        if r is not None:
            rp = res["rests"][r]
            folium.Marker((rp.lat, rp.lon), tooltip=rp.name,
                          icon=folium.Icon(color="green", icon="cutlery")).add_to(m)
        st_folium(m, height=430, use_container_width=True, returned_objects=[])  # noqa
    except ImportError:
        st.map(pd.DataFrame([{"lat": v.lat, "lon": v.lon} for v in res["venues"]]))
with right:
    st.write("**Each person's round trip** (average, and on a bad day)")
    c = inst.C[:, best["option"], :]
    st.bar_chart(pd.DataFrame({"Typical": c.mean(1), "Bad day (90th pct)": np.percentile(c, 90, 1)},
                              index=inst.members), stack=False)

st.subheader("3. How the objectives compare")
st.write("Each row picks the spot that is best for one definition of *best*. "
         "The trade-off between them is the point: lowest total time is not always fair.")
rows = []
for k, r in results.items():
    rows.append({"Objective": OBJECTIVES[k], **describe(r["option"]),
                 "Avg total (min)": round(r["avg total (min)"]),
                 "Avg longest trip": round(r["avg longest trip (min)"]),
                 "Bad-day worst trip (CVaR)": round(r["bad-day worst trip, CVaR (min)"]),
                 f"P(someone > {late} min)": f"{(inst.C[:, r['option'], :].max(0) > late).mean():.0%}"})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
st.caption(f"Drive times: {res['source']}. Traffic is simulated over {inst.C.shape[2]} days "
           "from typical Bay Area congestion by time slot, plus random incidents.")

st.subheader("4. Plan a whole season (rotate spots fairly)")
st.write("Practicing at one spot every week means the same person always drives the farthest. "
         "This plans several weeks so the **season total** of the person who travels most is as "
         "small as possible. Each host's place can be used a limited number of times.")
c1, c2, c3 = st.columns(3)
weeks = c1.number_input("Weeks", 2, 20, 8)
host_cap = c2.number_input("Max times at each host's place", 0, 20, 2)
risk = c3.selectbox("Plan using", ["mean", "cvar"],
                    format_func=lambda r: "typical traffic" if r == "mean" else "bad-day traffic")
if st.button("Plan the season"):
    D = member_costs(inst.C, risk, alpha)
    hosts = host_option_map(inst)
    milp = plan_season(D, int(weeks), hosts, int(host_cap))
    greedy = plan_season_greedy(D, int(weeks), hosts, int(host_cap))
    same = int(np.argmin(D.max(0))) if not hosts else None
    sched = pd.DataFrame([{"Week": w + 1, **describe(o)} for w, o in enumerate(milp["schedule"])])
    st.dataframe(sched, hide_index=True, width="stretch")
    comp = pd.DataFrame({"Optimized rotation": milp["member_totals"],
                         "Greedy week-by-week": greedy["member_totals"]}, index=inst.members)
    if same is not None:
        comp["Same spot every week"] = D[:, same] * int(weeks)
    st.write("**Season total travel per person (minutes)**")
    st.bar_chart(comp, stack=False)
    st.caption(f"Integer program solved in {milp['seconds']:.2f}s ({milp['status']}). Most-travelled "
               f"person: {milp['max_total']:.0f} min optimized vs {greedy['max_total']:.0f} min greedy.")

with st.expander("How this works"):
    st.markdown("""
**Inputs.** Each person's location (only a city or neighborhood is needed), who can host, and the
possible practice times. Studios and restaurants come from OpenStreetMap. Road drive times come from
the free OSRM routing engine.

**Traffic.** Free routing has no live traffic, so each time slot gets a congestion level.
We simulate hundreds of possible traffic days: a shared "bad day" shock, a per-trip shock, and
occasional incidents that add 10 to 30 minutes. Trips that cross a bay bridge are riskier:
they get a toll-plaza queue, bigger swings, and more incidents.

**Objectives.**
* *Total travel* (min-sum): the classic median problem.
* *Longest trip* (min-max): the classic center problem.
* *Robust CVaR* (not covered in class): averages the worst member's trip over the worst
  (1 − α) share of traffic days, so a spot that is usually fine but sometimes awful loses.
  It is solved as a linear program with the Rockafellar–Uryasev formulation.
* *Fair blend, OWA* (not covered in class): ranks people from longest to shortest trip and puts more
  weight on the longer trips.

**Season planning** is an integer program. It sets how many weeks each spot is used, with
limits on how often hosts host, and minimizes the largest season total.
""")
