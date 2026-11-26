# Meet in the Middle: Fair and Traffic-Robust Meeting Spots for a Bay Area Dance Group

IEOR 240, Fall 2026, final project (product option). **Video link: <paste share link here>**

> Draft written with AI help. The numbers come from `experiments/run_experiments.py`
> (60 synthetic groups, seeds fixed). Rewrite the prose in your own words before you
> submit. The course says writing quality is graded.

---

## 1. Motivation and use case (~0.5 page)

Our dance cover team has four members living in different parts of the Bay Area. Every week
someone asks "where do we practice?", and the answer usually defaults to whoever complains least.
Bay Area driving makes this harder in two ways:

1. **Distances are lopsided.** The bay sits in the middle, so a spot that is 15 minutes for two
   people can be 50 minutes and a bridge toll for the third.
2. **Travel time is uncertain.** A Saturday 10 AM drive and a weeknight 6 PM drive over the
   Bay Bridge are different problems. A crash on the San Mateo Bridge can add half an hour.

We built a free web app. Each member enters a rough location and whether they can host. The app
recommends **where** (a dance studio from OpenStreetMap, or a member's home) and **when**
(a time slot) to practice. It can also pick **a restaurant** for after practice, and plan a **multi-week
rotation** so the long drives are shared fairly. The same tool works for any group that meets
regularly, such as study groups, clubs, or friends picking a dinner spot.

## 2. Problem setup and formulation (~1 page)

**Sets.** Members i ∈ I. Candidate venues j ∈ J (studios, plus homes of members who opted in
to host). Time slots t ∈ T. Restaurants k ∈ K (optional). Traffic scenarios s ∈ S, which are
equally likely simulated days. An *option* o = (j, t) or (j, k, t).

**Data.** C_ios is member i's round-trip minutes under option o in scenario s:
home → studio → home, or home → studio → restaurant → home.

**Decision.** x_o ∈ {0,1}, with Σ_o x_o = 1.

**Course objectives.**

* Min-sum (1-median): min Σ_o x_o Σ_i E_s[C_ios]
* Min-max (1-center): min z subject to z ≥ Σ_o x_o E_s[C_ios] for all i

**Robust objective (not covered in class): CVaR.** Let W_s(x) = max_i Σ_o x_o C_ios be the
worst member's trip on day s. We minimize CVaR_α(W): the average of W over the worst (1−α)
share of days. Using the Rockafellar–Uryasev (2000) linearization:

  min η + 1/((1−α)|S|) Σ_s u_s
  s.t. u_s ≥ w_s − η, u_s ≥ 0, w_s ≥ Σ_o x_o C_ios for all i, s, Σ_o x_o = 1, x binary

**Fairness objective (not covered in class): OWA / generalized Gini.** Sort members' expected
trips from longest to shortest, y_(1) ≥ … ≥ y_(n). Then minimize Σ_r w_r y_(r) with decreasing
weights w. We linearize it with Ogryczak's k-sum identity: sum of the k largest y equals
min_t { k·t + Σ_i (y_i − t)^+ }. OWA sits between min-sum (equal weights) and min-max
(all weight on the worst member).

**Season rotation (integer program).** For W weeks, n_o ∈ ℤ₊ is the number of weeks option o
is used. D_io is member i's per-session cost (expected trip, or its CVaR).

  min M + ε Σ_i T_i
  s.t. T_i = Σ_o D_io n_o ≤ M for all i;  Σ_o n_o = W;  Σ_{o at h's home} n_o ≤ cap_h for each host h

Modeling note: weeks are interchangeable, so we use counts n_o instead of x_{o,w}. That removes
W! symmetric copies of each solution. A round-robin then turns the counts into a calendar.

## 3. Data (~0.5 page)

All sources are free, and none needs an API key or a credit card:

| Need | Source | Notes |
|---|---|---|
| Member locations | OpenStreetMap Nominatim geocoder | A city or neighborhood is enough. Nothing is stored. |
| Studios / restaurants | OpenStreetMap Overpass API | Tags `leisure=dance`, `amenity=dancing_school`, `cuisine=*` |
| Road drive times | OSRM public routing server | Free-flow times on the real road network |
| Traffic | Our scenario model (optional Google calibration) | See below |

**Traffic model.** time = free-flow × (1 + c_t · G_s · E) + incident delay. Here c_t is the slot's
congestion level (weekend morning 0.15–0.2, weeknight 6 PM 1.0), G_s is a shared "bad day"
shock, and E is a per-trip shock. An incident adds 10–30 minutes, and its probability grows with trip
length and congestion. **Bridge legs** (crossing the bay north of Dumbarton) get a toll-plaza
queue, twice the volatility, and four times the incident rate. If the group adds a Google Routes API key,
the app recalibrates c_t from Google's traffic-aware times.

The venue search is centered at the members' **geometric median**, computed with Weiszfeld's
algorithm (the continuous Weber problem). Then we keep the nearest 15 studios.

## 4. Results (~1–1.5 pages)

Setup: 60 synthetic groups of 6 members, placed around real Bay Area city centers within one
region. Each group has 15 studios, 2 host homes, and 4 time slots. Every pick is chosen on 200
simulated days and **scored on 2,000 new days (out of sample)**.

**Figure 1 (`exp1_objectives.png`): the cost of each objective.**

| Objective | Avg total time | Avg longest trip | Bad-day worst trip (CVaR) | P(someone's round trip > 2 h) |
|---|---|---|---|---|
| Min total | best | +20.3% | +16.7% | 40% of days |
| Min longest | +11.5% | +0.1% | +0.9% | 22% |
| Robust CVaR | +10.0% | +2.6% | +0.5% | 23% |
| Fair OWA | +3.2% | +9.2% | +6.8% | 29% |

Talking points:
* **Minimizing total travel is unfair.** It makes the farthest member travel about 20% longer and
  nearly doubles how often someone faces a round trip over 2 hours (40% of days vs 22%).
* **OWA is a good compromise.** It costs only 3% in total time and recovers about half of the fairness gap.
* **CVaR vs min-max:** the robust pick differs from the min-max pick in **1 in 3 groups**.
  When it differs, it lowers the bad-day worst trip by about 1.4 minutes and costs about 6 minutes on a
  typical day. Out of sample it wins in 65% of those groups. Honest takeaway: in our traffic
  model, *where people live* matters much more than *traffic risk*. Robustness changes the
  decision only when two spots are close on average and one of them needs a bridge.

**Figure 2 (`exp2_alpha.png`): the α trade-off.** Raising α from 0.5 to 0.99 moves the typical-day
worst trip from 99.8 to 101.5 minutes, with almost no change in the tail. The flat curve supports the
point above. Possible extension: rerun with heavier-tailed bridge incidents.

**Figure 3 (`exp3_season.png`): season rotation is where optimization pays off.**

| Group | Options | Weeks | Same spot every week | Greedy week-by-week | IP solve time |
|---|---|---|---|---|---|
| 4 people | 52 | 4 | +23.0% | +12.0% | 0.01 s |
| 6 people | 72 | 8 | +19.4% | +5.9% | 0.02 s |
| 8 people | 112 | 12 | +14.6% | +3.4% | 0.09 s |
| 10 people | 172 | 16 | +11.0% | +3.3% | 0.11 s |
| 12 people | 252 | 20 | +11.7% | +3.3% | 0.13 s |

Each percentage is how much more the most-travelled member drives over the season, compared
with the integer program. The LP relaxation is within 0.2–5.5% of the integer optimum, and the
gap shrinks as instances grow.

**Solve-time note (`exp4_solve_time.csv`).** For a single session the choice is one option, so
enumeration is exact and takes under 1 ms. The CVaR MILP gives the same answer but takes 0.8–10 s
because it has |I|·|S| constraints. So the app enumerates single sessions and uses the MILP
for the season problem, where enumeration is impossible (C(O+W−1, W) count vectors).

## 5. Practicality, limitations, next steps (~0.5 page)

* **Practical:** the app is free, runs in a browser, and gives an answer in a few seconds.
  Privacy: members only need to share a neighborhood.
* **Limitations:** the traffic model is assumed, not fitted. OSM coverage of dance studios is
  incomplete. We ignore studio rental prices and availability. Everyone is assumed to drive
  (no BART or Caltrain).
* **Next:** calibrate traffic with real Google or Caltrans PeMS data; add transit mode; add
  studio prices with a cost-vs-travel trade-off; let members mark slots they are unavailable.

## Appendix (does not count toward the page limit)

* A. Code: GitHub repo link; `meetup/optimize.py` holds every formulation.
* B. Screenshots of the app.
* C. Full experiment tables (`experiments/results/*.csv`).
* D. Test showing the MILPs and enumeration agree (`tests/test_optimize.py`).
* References: Rockafellar & Uryasev (2000), *Optimization of conditional value-at-risk*, J. Risk.
  Yager (1988), *On ordered weighted averaging aggregation operators*, IEEE SMC. Ogryczak & Tamir (2003),
  *Minimizing the sum of the k largest functions in linear time*, IPL. Weiszfeld (1937).
