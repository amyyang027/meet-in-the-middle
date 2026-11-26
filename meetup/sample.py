"""Offline sample and synthetic instances (for tests, experiments, and the demo mode)."""

from __future__ import annotations

import numpy as np

from .geo import BAY_AREA_PLACES, bridge_crossings, fallback_minutes
from .scenarios import DEFAULT_SLOTS, build_instance

# Demo group: members give only a city or neighborhood, never a home address.
SAMPLE_MEMBERS = [
    ("Member A", "berkeley", True),
    ("Member B", "san jose", False),
    ("Member C", "sf mission", True),
    ("Member D", "fremont", False),
]

# Generic sample venues placed at city centers. They are not real businesses.
SAMPLE_STUDIOS = ["oakland", "san mateo", "hayward", "palo alto", "milpitas",
                  "san francisco", "union city", "sunnyvale", "emeryville", "san leandro"]


def random_instance(n_members: int = 6, n_studios: int = 15, n_slots: int = 4,
                    n_scenarios: int = 200, n_restaurants: int = 0, hosts: int = 2,
                    seed: int = 0, spread_km: float = 3.0,
                    scenario_seed: int | None = None, region_km: float | None = 35.0):
    """Synthetic Bay Area group: members and venues jittered around real city centers.

    Friends usually live in one part of the Bay Area, so by default every member and
    venue is drawn from the cities within region_km of a random anchor city.
    region_km=None draws from the whole Bay Area.
    """
    rng = np.random.default_rng(seed)
    cities = list(BAY_AREA_PLACES.values())
    if region_km is not None:
        from .geo import haversine_km
        anchor = cities[rng.integers(len(cities))]
        cities = [c for c in cities if haversine_km(anchor, c) <= region_km]

    def jitter(p):
        d = rng.normal(0, spread_km / 111.0, size=2)
        return (p[0] + d[0], p[1] + d[1])

    homes = [jitter(cities[rng.integers(len(cities))]) for _ in range(n_members)]
    studios = [jitter(cities[rng.integers(len(cities))]) for _ in range(n_studios)]
    rests = [jitter(cities[rng.integers(len(cities))]) for _ in range(n_restaurants)]
    host_members = list(rng.choice(n_members, size=min(hosts, n_members), replace=False))
    venue_pts = studios + [homes[h] for h in host_members]
    points = homes + venue_pts + rests
    ff = fallback_minutes(points)
    I, J = n_members, len(venue_pts)
    venue_idx = list(range(I, I + J))
    # a host's home is the same point as the venue: zero travel for the host
    for v, h in enumerate(host_members):
        ff[h, I + n_studios + v] = ff[I + n_studios + v, h] = 0.0
    slot_names = list(DEFAULT_SLOTS)
    pick = sorted(rng.choice(len(slot_names), size=min(n_slots, len(slot_names)), replace=False))
    slots = {slot_names[t]: DEFAULT_SLOTS[slot_names[t]] for t in pick}
    inst = build_instance(
        ff, homes=list(range(I)), venues=venue_idx,
        members=[f"M{i + 1}" for i in range(I)],
        venue_names=[f"Studio {j + 1}" for j in range(n_studios)] +
                    [f"M{h + 1}'s place" for h in host_members],
        slots=slots, n_scenarios=n_scenarios,
        restaurants=list(range(I + J, I + J + n_restaurants)) or None,
        restaurant_names=[f"Restaurant {k + 1}" for k in range(n_restaurants)],
        host_of_venue={n_studios + v: int(h) for v, h in enumerate(host_members)},
        seed=seed + 1 if scenario_seed is None else scenario_seed,
        bridge=bridge_crossings(points))
    return inst


def host_option_map(inst) -> dict[int, list[int]]:
    """member index -> option indices held at that member's home."""
    out: dict[int, list[int]] = {}
    for o, opt in enumerate(inst.options):
        h = inst.host_of_venue.get(opt["venue"])
        if h is not None:
            out.setdefault(h, []).append(o)
    return out
