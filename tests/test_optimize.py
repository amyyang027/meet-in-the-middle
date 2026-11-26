import numpy as np
import pytest

from meetup.optimize import (OBJECTIVES, cvar, plan_season, plan_season_greedy, scores,
                             season_lp_bound, solve_enumeration, solve_milp, member_costs)
from meetup.sample import host_option_map, random_instance


def test_cvar_matches_definition():
    L = np.arange(1, 101, dtype=float)          # 1..100
    assert cvar(L, 0.9) == pytest.approx(np.mean(np.arange(91, 101)))
    assert cvar(L, 0.0) == pytest.approx(L.mean())


@pytest.mark.parametrize("objective", list(OBJECTIVES))
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_milp_equals_enumeration(objective, seed):
    inst = random_instance(n_members=5, n_studios=6, n_slots=2, n_scenarios=40, seed=seed)
    e = solve_enumeration(inst.C, objective)
    m = solve_milp(inst.C, objective)
    s = scores(inst.C)[objective]
    assert s[m] == pytest.approx(s[e], rel=1e-6)


def test_food_instance_shape():
    inst = random_instance(n_members=4, n_studios=3, n_slots=2, n_scenarios=10, n_restaurants=5)
    assert inst.C.shape == (4, (3 + 2) * 5 * 2, 10)


def test_host_travels_zero():
    inst = random_instance(n_members=4, n_studios=3, n_slots=1, n_scenarios=10, hosts=1)
    for o, opt in enumerate(inst.options):
        h = inst.host_of_venue.get(opt["venue"])
        if h is not None:
            assert np.all(inst.C[h, o] == 0)


def test_season_milp_beats_or_ties_greedy_and_respects_caps():
    inst = random_instance(n_members=6, n_studios=8, n_slots=2, n_scenarios=50, hosts=2, seed=3)
    D = member_costs(inst.C)
    hosts = host_option_map(inst)
    milp = plan_season(D, weeks=6, host_options=hosts, host_cap=1)
    greedy = plan_season_greedy(D, weeks=6, host_options=hosts, host_cap=1)
    lb = season_lp_bound(D, weeks=6, host_options=hosts, host_cap=1)
    assert milp["counts"].sum() == 6
    assert lb <= milp["max_total"] + 1e-6 <= greedy["max_total"] + 1e-6
    for opts in hosts.values():
        assert milp["counts"][opts].sum() <= 1
