# 💃 Meet in the Middle

Find the fairest place and time for a group to meet, such as a dance practice studio, a member's home,
or a restaurant after practice. It uses real road data and accounts for Bay Area traffic risk.
IEOR 240 (Fall 2026) final project, "product" option.

**What it does**
- Members type a city or neighborhood and tick whether they can host.
- It finds dance studios (and, if you want, restaurants by cuisine) on OpenStreetMap near the group's
  geometric median.
- It simulates hundreds of traffic days per time slot. Bay bridge crossings are riskier.
- It compares four objectives: min total travel, min longest trip, **robust CVaR**, and **fair OWA**.
- It plans a multi-week **rotation** with an integer program so long drives are shared fairly.

**Cost: $0.** OpenStreetMap (Nominatim and Overpass) and the OSRM routing server are free and need no key.
A Google Routes API key is optional (only used for traffic calibration).

## Run it on your laptop
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Put it online for free (Streamlit Community Cloud)
1. Push this folder to a **public** GitHub repo.
2. Go to https://share.streamlit.io, sign in with GitHub, and click **Create app**.
3. Pick the repo, branch `main`, and file `app.py`. Click **Deploy**. You get a shareable `*.streamlit.app` link.

## Reproduce the report results
```bash
python -m pytest -q                         # MILPs agree with enumeration, caps respected
python -m experiments.run_experiments       # tables -> experiments/results, figures -> experiments/figures
```

## Layout
| Path | What |
|---|---|
| `app.py` | Streamlit web app |
| `meetup/geo.py` | Geocoding, venue search, OSRM drive times, bridge detection, Weiszfeld median |
| `meetup/scenarios.py` | Traffic scenario model |
| `meetup/optimize.py` | All formulations: min-sum, min-max, CVaR (Rockafellar–Uryasev), OWA, season IP |
| `meetup/sample.py` | Offline demo data and synthetic instances |
| `experiments/` | Experiments behind the report figures |
| `docs/report.md` | Report draft |
| `docs/video_outline.md` | Video plan |

## Fair-use notes
Nominatim allows at most 1 request per second (the app waits between calls). The OSRM demo server is meant for
light use, which suits a class project. Members' locations are used only in memory and are never saved.
