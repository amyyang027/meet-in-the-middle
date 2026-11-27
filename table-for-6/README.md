# Table for 6

Seat strangers at tables of 4 to 6, and pick each table's venue (restaurant, cafe or bar) and time slot.
Every survey answer (taste, interests, age, gender mix, budget) feeds a satisfaction score. Nothing is a filter.
The optimizer maximizes total satisfaction net of travel time and Bay Bridge tolls.

The website compares four methods on the same simulated crowd:

| Method | What it does |
| --- | --- |
| Random | Shuffles guests into open tables |
| Greedy | Opens the best table first, then the next best |
| Model A | Exact compact MILP (PuLP + HiGHS); only runs for 24 guests or fewer, 20 s limit |
| Model B | Set partitioning solved by column generation (HiGHS); the engine behind "your table" |

## Run locally

```
cd table-for-6
pip install -r requirements.txt
streamlit run app.py
```

## Deploy for free on Streamlit Community Cloud

1. Go to share.streamlit.io and sign in with GitHub.
2. Create an app from `amyyang027/meet-in-the-middle`, branch `main`, main file path `table-for-6/app.py`.
3. Deploy. Streamlit reads `table-for-6/requirements.txt` and `table-for-6/.streamlit/config.toml` automatically.

## Layout

- `app.py`: the website (landing, find your table, the lab, maps, table explorer, methods)
- `t6/data.py`: synthetic Bay Area crowd generator, plus `set_user` to drop a real person into the crowd
- `t6/solve.py`: Random, Greedy, Model A and Model B
- `t6/service.py`: runs all methods and summarizes them for the site
- `experiments/`: the experiments and figures behind the report
- `report/`: LaTeX source and `main.pdf` (the IEOR 240 report)

See `README_models.md` for how to reproduce the experiments.
