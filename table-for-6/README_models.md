# Table for 6

Seat strangers at tables of 4 to 6 and choose each table's venue and time slot.
The goal is to maximize satisfaction net of travel time and bridge tolls.
This folder holds the optimization models, the experiments and the IEOR 240 report.

## Layout

- `t6/data.py`: synthetic Bay Area instance generator (users, venues, slots, p, c, q, d, tau)
- `t6/solve.py`: Random, Greedy, Model A (compact MILP, PuLP + HiGHS), Model B (column generation in HiGHS:
  restricted master, heuristic and exact pricing, weak-duality bound, pool enrichment, diving)
- `experiments/run.py`: experiments e1 to e5 and the demo; results go to `experiments/results/`
- `experiments/figures.py`: the report's figures (written to `report/fig/`)
- `report/main.tex`: the report (`pdflatex main.tex` twice)

## Reproduce

```
pip install pulp==2.9.0 highspy numpy pandas matplotlib
python -m experiments.run e1      # also e2, e3, e4, e5, demo
python -m experiments.figures
cd report && pdflatex main.tex && pdflatex main.tex
```

e1 and e2 take the longest (Model A uses 90 and 300 second time limits).
