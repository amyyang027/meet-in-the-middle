"""Free map data: geocoding, venue search, and drive-time matrices.

Every function here uses free services that need no API key or credit card:

* Geocoding  -> OpenStreetMap Nominatim (max 1 request/second, needs a User-Agent)
* Venues     -> OpenStreetMap Overpass API (dance studios, restaurants by cuisine)
* Drive time -> OSRM public routing server (free-flow road travel times)

Each one has an offline fallback, so the app and the experiments still run when a
service is down or rate-limits us. Google's Routes API (live traffic) is optional.
See ``google_traffic_matrix``. It needs an API key, and Google needs a card on
file, so it is never required.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field

import numpy as np
import requests

USER_AGENT = "dance-meetup-optimizer/1.0 (IEOR 240 class project)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"
OSRM = "https://router.project-osrm.org/table/v1/driving/"

# Rough centers of Bay Area cities. They are used when a geocoder is unreachable,
# and they let members type only a city or neighborhood (better for privacy).
BAY_AREA_PLACES = {
    "san francisco": (37.7749, -122.4194), "sf mission": (37.7599, -122.4148),
    "sf sunset": (37.7531, -122.4950), "daly city": (37.6879, -122.4702),
    "oakland": (37.8044, -122.2712), "berkeley": (37.8716, -122.2727),
    "albany": (37.8869, -122.2978), "richmond": (37.9358, -122.3477),
    "el cerrito": (37.9161, -122.3108), "emeryville": (37.8313, -122.2852),
    "alameda": (37.7652, -122.2416), "san leandro": (37.7249, -122.1561),
    "hayward": (37.6688, -122.0808), "union city": (37.5934, -122.0439),
    "fremont": (37.5485, -121.9886), "newark": (37.5297, -122.0402),
    "milpitas": (37.4323, -121.8996), "san jose": (37.3382, -121.8863),
    "santa clara": (37.3541, -121.9552), "sunnyvale": (37.3688, -122.0363),
    "cupertino": (37.3230, -122.0322), "mountain view": (37.3861, -122.0839),
    "palo alto": (37.4419, -122.1430), "menlo park": (37.4530, -122.1817),
    "redwood city": (37.4852, -122.2364), "san mateo": (37.5630, -122.3255),
    "foster city": (37.5585, -122.2711), "burlingame": (37.5779, -122.3481),
    "south san francisco": (37.6547, -122.4077), "walnut creek": (37.9101, -122.0652),
    "concord": (37.9780, -122.0311), "dublin": (37.7022, -121.9358),
    "pleasanton": (37.6624, -121.8747), "san ramon": (37.7799, -121.9780),
    "livermore": (37.6819, -121.7680), "danville": (37.8216, -121.9999),
}


@dataclass
class Place:
    name: str
    lat: float
    lon: float
    kind: str = "studio"            # "home" | "studio" | "restaurant"
    owner: int | None = None        # for a host home: index of the member who lives there
    tags: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- geocoding
_last_nominatim_call = 0.0


def geocode(text: str, timeout: float = 10.0) -> tuple[float, float, str]:
    """Return (lat, lon, source). Accepts 'lat, lon', a known city name, or any address."""
    global _last_nominatim_call
    s = text.strip()
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*", s)
    if m:
        return float(m.group(1)), float(m.group(2)), "coordinates"
    key = s.lower().replace(", ca", "").replace(",ca", "").strip()
    try:
        wait = 1.05 - (time.time() - _last_nominatim_call)   # Nominatim policy: 1 req/s
        if wait > 0:
            time.sleep(wait)
        _last_nominatim_call = time.time()
        r = requests.get(NOMINATIM, params={"q": s, "format": "json", "limit": 1,
                                            "countrycodes": "us"},
                         headers={"User-Agent": USER_AGENT}, timeout=timeout)
        r.raise_for_status()
        hits = r.json()
        if hits:
            return float(hits[0]["lat"]), float(hits[0]["lon"]), "nominatim"
    except Exception:
        pass
    if key in BAY_AREA_PLACES:
        lat, lon = BAY_AREA_PLACES[key]
        return lat, lon, "built-in city center"
    raise ValueError(f"Could not find a location for '{text}'. Try a city name or 'lat, lon'.")


# --------------------------------------------------------------------------- distances
def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def fallback_minutes(points: list[tuple[float, float]]) -> np.ndarray:
    """Offline drive-time estimate: straight line x 1.3 road detour at ~60 km/h + 4 min parking."""
    n = len(points)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                M[i, j] = 1.3 * haversine_km(points[i], points[j]) / 60.0 * 60.0 + 4.0
    return M


def _west_of_bay(lat: float, lon: float) -> bool:
    """Crude bay shoreline: a line from Richmond/SF (37.95, -122.40) to Dumbarton (37.45, -122.10)."""
    line_lon = -122.40 + (37.95 - lat) / (37.95 - 37.45) * 0.30
    return lon < line_lon


def bridge_crossings(points: list[tuple[float, float]]) -> np.ndarray:
    """True where a drive between two points must cross the bay on a toll bridge.

    South of the Dumbarton Bridge (lat < 37.45) you can drive around the bay, so no crossing.
    Bridges matter because their delays are larger and less predictable (metering
    lights, crashes, closures). The traffic model gives these legs extra volatility.
    """
    n = len(points)
    side = [_west_of_bay(*p) for p in points]
    X = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(n):
            a, b = points[i], points[j]
            X[i, j] = side[i] != side[j] and min(a[0], b[0]) > 37.45
    return X


def osrm_minutes(points: list[tuple[float, float]], timeout: float = 20.0) -> np.ndarray:
    """Free-flow driving minutes between all points (one OSRM table call, <= 100 points)."""
    if len(points) > 100:
        raise ValueError("OSRM public server allows at most 100 points per table call")
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
    r = requests.get(OSRM + coords, params={"annotations": "duration"},
                     headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "Ok":
        raise RuntimeError(data.get("message", "OSRM error"))
    M = np.array([[np.nan if v is None else v / 60.0 for v in row] for row in data["durations"]])
    # unroutable pairs -> fall back to the straight-line estimate for that pair
    if np.isnan(M).any():
        F = fallback_minutes(points)
        M = np.where(np.isnan(M), F, M)
    return M + 4.0 * (1 - np.eye(len(points)))   # + parking / walking-in time


def drive_matrix(points: list[tuple[float, float]]) -> tuple[np.ndarray, str]:
    try:
        return osrm_minutes(points), "OSRM road network (free-flow)"
    except Exception:
        return fallback_minutes(points), "straight-line estimate (OSRM unreachable)"


def google_traffic_matrix(origins, destinations, api_key: str, departure_rfc3339: str,
                          traffic_model: str = "BEST_GUESS", timeout: float = 30.0) -> np.ndarray:
    """Optional: traffic-aware minutes from Google Routes API computeRouteMatrix.

    departure_rfc3339 must be in the future, e.g. '2026-12-05T18:00:00-08:00'.
    traffic_model is one of BEST_GUESS, PESSIMISTIC, OPTIMISTIC. With traffic-aware
    routing Google allows at most 100 origin x destination elements per request.
    """
    def wp(p):
        return {"waypoint": {"location": {"latLng": {"latitude": p[0], "longitude": p[1]}}}}
    body = {"origins": [wp(p) for p in origins], "destinations": [wp(p) for p in destinations],
            "travelMode": "DRIVE", "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
            "departureTime": departure_rfc3339, "trafficModel": traffic_model}
    r = requests.post("https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix",
                      json=body, timeout=timeout,
                      headers={"X-Goog-Api-Key": api_key,
                               "X-Goog-FieldMask": "originIndex,destinationIndex,duration,condition"})
    r.raise_for_status()
    M = np.full((len(origins), len(destinations)), np.nan)
    for el in r.json():
        if el.get("condition") == "ROUTE_EXISTS" and "duration" in el:
            M[el["originIndex"], el["destinationIndex"]] = float(el["duration"].rstrip("s")) / 60.0
    return M


# --------------------------------------------------------------------------- venues
def _overpass(query: str, timeout: float = 40.0) -> list[dict]:
    r = requests.post(OVERPASS, data={"data": query}, headers={"User-Agent": USER_AGENT},
                      timeout=timeout)
    r.raise_for_status()
    return r.json().get("elements", [])


def _elements_to_places(elements, kind) -> list[Place]:
    out, seen = [], set()
    for e in elements:
        tags = e.get("tags", {})
        name = tags.get("name")
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        if not name or lat is None or name in seen:
            continue
        seen.add(name)
        out.append(Place(name, float(lat), float(lon), kind, tags=tags))
    return out


def find_studios(center, radius_km: float) -> list[Place]:
    lat, lon = center
    r = int(radius_km * 1000)
    q = f"""[out:json][timeout:30];
    (nwr["leisure"="dance"](around:{r},{lat},{lon});
     nwr["amenity"="dancing_school"](around:{r},{lat},{lon});
     nwr["sport"="dance"](around:{r},{lat},{lon});
     nwr["amenity"="studio"]["studio"="dance"](around:{r},{lat},{lon}););
    out center tags;"""
    return _elements_to_places(_overpass(q), "studio")


CUISINES = ["korean", "japanese", "chinese", "italian", "mexican", "thai", "vietnamese",
            "indian", "american", "taiwanese", "ramen", "sushi", "pizza", "burger", "bubble_tea"]


def find_restaurants(center, radius_km: float, cuisine: str) -> list[Place]:
    lat, lon = center
    r = int(radius_km * 1000)
    amenity = "cafe" if cuisine == "bubble_tea" else "restaurant|fast_food"
    q = f"""[out:json][timeout:30];
    nwr["amenity"~"^({amenity})$"]["cuisine"~"{cuisine}",i](around:{r},{lat},{lon});
    out center tags;"""
    return _elements_to_places(_overpass(q), "restaurant")


def nearest_to(places: list[Place], center, k: int) -> list[Place]:
    return sorted(places, key=lambda p: haversine_km(center, (p.lat, p.lon)))[:k]


def geometric_median(points: list[tuple[float, float]], iters: int = 200) -> tuple[float, float]:
    """Weiszfeld's algorithm (the continuous 1-median / Weber point).

    The app uses it to center the venue search on the spot that minimizes total
    straight-line distance to the members.
    """
    P = np.array(points, dtype=float)
    y = P.mean(axis=0)
    for _ in range(iters):
        d = np.linalg.norm(P - y, axis=1)
        if np.any(d < 1e-9):
            return tuple(P[np.argmin(d)])
        w = 1.0 / d
        y_new = (P * w[:, None]).sum(axis=0) / w.sum()
        if np.linalg.norm(y_new - y) < 1e-9:
            break
        y = y_new
    return float(y[0]), float(y[1])
