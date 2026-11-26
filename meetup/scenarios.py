"""Traffic scenarios: turn free-flow drive times into random travel times by time slot.

The free routing data (OSRM) has no live traffic. We model traffic as a random
multiplier on each trip leg, plus rare incidents:

    time = free_flow * (1 + c_t * G_s * E_leg,s)  +  incident_delay

* c_t   peak intensity of time slot t (0 = empty roads; 1 = weekday rush hour)
* G_s   a "bad traffic day" shock, shared by every trip in scenario s
* E     a per-trip shock (lognormal, mean 1)
* incident: with a small probability that grows with trip length and peak
  intensity, a trip loses 10-30 extra minutes (a crash or a backup).
* bridges: legs that cross the bay (Bay, San Mateo, Dumbarton, Richmond bridges)
  get a toll-plaza queue, double the random swing, and about 4x the incident rate.

The incidents give the heavy right tail that makes a robust (CVaR) objective
behave differently from the average. If a Google API key is available,
``calibrate_intensity`` fits c_t to Google's traffic-aware times.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Default slot intensities are modelling assumptions, loosely based on typical Bay
# Area congestion (weekday evening peak much worse than weekend mornings).
DEFAULT_SLOTS = {
    "Sat 10:00 AM": 0.20,
    "Sat 2:00 PM": 0.35,
    "Sat 6:00 PM": 0.40,
    "Sun 11:00 AM": 0.15,
    "Sun 4:00 PM": 0.35,
    "Fri 7:00 PM": 0.75,
    "Weeknight 7:30 PM": 0.50,
    "Weeknight 6:00 PM": 1.00,
}


@dataclass
class Instance:
    """Everything an optimizer needs.

    C[i, o, s] = minutes member i spends travelling under option o in scenario s
    (full trip: home -> studio -> [restaurant ->] home).
    """
    C: np.ndarray
    options: list[dict]          # each: {"venue": j, "restaurant": k|None, "slot": t}
    members: list[str]
    venues: list[str]
    restaurants: list[str]
    slots: list[str]
    host_of_venue: dict           # venue index -> member index (host homes only)


def _leg(ff: np.ndarray, c: float, G: np.ndarray, rng: np.random.Generator,
         bridge: np.ndarray | None = None, sigma: float = 0.25) -> np.ndarray:
    """Random travel minutes for free-flow array ff (..., 1) across scenarios G (S,).

    bridge (same shape as ff, bool) marks legs that cross the bay. They get a fixed
    bridge-queue delay, larger random swings, and about 4x the incident rate.
    """
    shape = ff.shape[:-1] + (G.shape[0],)
    br = np.zeros_like(ff, dtype=bool) if bridge is None else bridge
    sig = np.where(br, 2.0 * sigma, sigma)
    E = np.exp(sig * rng.standard_normal(shape) - sig ** 2 / 2)
    t = ff * (1.0 + c * G * E) + br * (6.0 * c * G)            # toll plaza / metering queue
    p_inc = np.clip((0.02 + 0.05 * c) * ff / 20.0 * np.where(br, 4.0, 1.0), 0.0, 0.6)
    inc = rng.random(shape) < p_inc
    t = t + inc * rng.uniform(10.0, 30.0, size=shape) * np.where(br, 1.5, 1.0)
    return np.where(ff > 0, t, 0.0)


def build_instance(ff: np.ndarray, homes: list[int], venues: list[int], members: list[str],
                   venue_names: list[str], slots: dict[str, float], n_scenarios: int = 200,
                   restaurants: list[int] | None = None, restaurant_names: list[str] | None = None,
                   host_of_venue: dict | None = None, seed: int = 0,
                   bridge: np.ndarray | None = None) -> Instance:
    """ff is a full free-flow minutes matrix over all points; homes/venues/restaurants index into it.

    bridge (optional, bool, same shape as ff) marks pairs whose drive crosses the bay.
    """
    rng = np.random.default_rng(seed)
    S = n_scenarios
    X = np.zeros_like(ff, dtype=bool) if bridge is None else bridge
    A_go = ff[np.ix_(homes, venues)][..., None]                  # (I, J, 1)
    A_back = ff[np.ix_(venues, homes)].T[..., None]              # (I, J, 1)
    X_go = X[np.ix_(homes, venues)][..., None]
    X_back = X[np.ix_(venues, homes)].T[..., None]
    food = restaurants is not None and len(restaurants) > 0
    if food:
        B = ff[np.ix_(venues, restaurants)][..., None]           # (J, K, 1)
        R = ff[np.ix_(restaurants, homes)].T[..., None]          # (I, K, 1)
        X_B = X[np.ix_(venues, restaurants)][..., None]
        X_R = X[np.ix_(restaurants, homes)].T[..., None]
    day = rng.lognormal(-0.3 ** 2 / 2, 0.3, size=S)              # bad-day shock
    blocks, options = [], []
    slot_names = list(slots)
    for t, name in enumerate(slot_names):
        c = slots[name]
        G = day * rng.lognormal(-0.35 ** 2 / 2, 0.35, size=S)
        go = _leg(A_go, c, G, rng, X_go)                                # (I, J, S)
        if not food:
            back = _leg(A_back, c * 0.8, G, rng, X_back)                  # return trip, a bit lighter
            blocks.append(go + back)
            options += [{"venue": j, "restaurant": None, "slot": t} for j in range(len(venues))]
        else:
            mid = _leg(B, c * 0.8, G, rng, X_B)                        # (J, K, S)
            home = _leg(R, c * 0.6, G, rng, X_R)                       # (I, K, S)
            cost = go[:, :, None, :] + mid[None, :, :, :] + home[:, None, :, :]
            I, J, K, _ = cost.shape
            blocks.append(cost.reshape(I, J * K, S))
            options += [{"venue": j, "restaurant": k, "slot": t}
                        for j in range(J) for k in range(K)]
    C = np.concatenate(blocks, axis=1)
    return Instance(C, options, members, venue_names, restaurant_names or [], slot_names,
                    host_of_venue or {})


def calibrate_intensity(free_flow: np.ndarray, traffic: np.ndarray) -> float:
    """Fit a slot's peak intensity c_t from traffic-aware times (e.g. Google BEST_GUESS)."""
    ok = (free_flow > 5) & np.isfinite(traffic)
    if not ok.any():
        return float("nan")
    # E[1 + c*G*E] = 1 + c, so the median traffic/free-flow ratio minus 1 estimates c.
    return float(max(0.0, np.median(traffic[ok] / free_flow[ok]) - 1.0))
