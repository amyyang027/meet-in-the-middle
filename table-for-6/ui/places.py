"""Look up a guest's own favorite spot on a real map.

Uses Google Places (Text Search) when a GOOGLE_MAPS_API_KEY is set in Streamlit secrets,
otherwise OpenStreetMap's free Nominatim geocoder. Only places inside the map area
(San Francisco and the inner East Bay) that are restaurants, cafes or bars count.
"""
import requests
import streamlit as st
from t6.data import CUISINES

BOX = dict(west=-122.53, south=37.70, east=-122.22, north=37.90)
UA = {"User-Agent": "TableFor6-class-project/1.0 (educational demo)"}
OSM_TYPE = {"restaurant": 0, "fast_food": 0, "food_court": 0, "cafe": 1, "ice_cream": 1,
            "bar": 2, "pub": 2, "biergarten": 2, "nightclub": 2}
CUIS_WORDS = {"mexican": 0, "taco": 0, "burrito": 0, "chinese": 1, "dim_sum": 1, "italian": 2, "pizza": 2,
              "japanese": 3, "sushi": 3, "ramen": 3, "indian": 4, "thai": 5, "ethiopian": 6,
              "american": 7, "burger": 7, "barbecue": 7}


def _cuisine(text):
    text = (text or "").lower()
    for w, k in CUIS_WORDS.items():
        if w in text:
            return k
    return -1


def _in_box(lat, lon):
    return BOX["south"] <= lat <= BOX["north"] and BOX["west"] <= lon <= BOX["east"]


def _google(q, key):
    r = requests.post(
        "https://places.googleapis.com/v1/places:searchText", timeout=8,
        headers={"X-Goog-Api-Key": key,
                 "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types"},
        json={"textQuery": q, "maxResultCount": 5,
              "locationRestriction": {"rectangle": {"low": {"latitude": BOX["south"], "longitude": BOX["west"]},
                                                    "high": {"latitude": BOX["north"], "longitude": BOX["east"]}}}})
    r.raise_for_status()
    for p in r.json().get("places", []):
        types = p.get("types", [])
        vt = 2 if ("bar" in types or "night_club" in types) else 1 if ("cafe" in types or "coffee_shop" in types) \
            else 0 if ("restaurant" in types or any(t.endswith("_restaurant") for t in types)) else None
        lat, lon = p["location"]["latitude"], p["location"]["longitude"]
        if vt is None or not _in_box(lat, lon):
            continue
        return dict(name=p["displayName"]["text"], lat=lat, lon=lon, type=vt,
                    cuisine=_cuisine(" ".join(types)) if vt == 0 else -1,
                    addr=p.get("formattedAddress", ""), source="Google Maps")
    return None


def _osm(q):
    r = requests.get(
        "https://nominatim.openstreetmap.org/search", timeout=8, headers=UA,
        params=dict(q=q, format="jsonv2", limit=8, extratags=1, addressdetails=1, countrycodes="us", bounded=1,
                    viewbox=f'{BOX["west"]},{BOX["north"]},{BOX["east"]},{BOX["south"]}'))
    r.raise_for_status()
    for p in r.json():
        vt = OSM_TYPE.get(p.get("type")) if p.get("category") == "amenity" else None
        if vt is None:
            continue
        lat, lon = float(p["lat"]), float(p["lon"])
        a = p.get("address", {})
        street = " ".join(x for x in [a.get("house_number", ""), a.get("road", "")] if x)
        city = a.get("city") or a.get("town") or ""
        return dict(name=p.get("name") or q, lat=lat, lon=lon, type=vt,
                    cuisine=_cuisine((p.get("extratags") or {}).get("cuisine")) if vt == 0 else -1,
                    addr=", ".join(x for x in [street, city] if x), source="OpenStreetMap")
    return None


def _photon(q):
    r = requests.get("https://photon.komoot.io/api/", timeout=8, headers=UA,
                     params=dict(q=q, limit=8, bbox=f'{BOX["west"]},{BOX["south"]},{BOX["east"]},{BOX["north"]}'))
    r.raise_for_status()
    for f in r.json().get("features", []):
        pr = f.get("properties", {})
        vt = OSM_TYPE.get(pr.get("osm_value")) if pr.get("osm_key") == "amenity" else None
        if vt is None:
            continue
        lon, lat = f["geometry"]["coordinates"]
        if not _in_box(lat, lon):
            continue
        street = " ".join(x for x in [pr.get("housenumber", ""), pr.get("street", "")] if x)
        return dict(name=pr.get("name") or q, lat=lat, lon=lon, type=vt, cuisine=-1,
                    addr=", ".join(x for x in [street, pr.get("city", "")] if x), source="OpenStreetMap")
    return None


def _catalog(q):
    """Our own list of real venues, matched by name (works even if the map services are unreachable)."""
    import difflib
    import unicodedata
    from t6.venues import REAL_VENUES
    norm = lambda x: unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().strip()
    names = {norm(r[0]): r for r in REAL_VENUES}
    hit = difflib.get_close_matches(norm(q), list(names), n=1, cutoff=0.85)
    if not hit:
        return None
    r = names[hit[0]]
    return dict(name=r[0], lat=r[1], lon=r[2], type=r[3], cuisine=r[4], addr=r[6], source="OpenStreetMap")


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def find_place(q):
    """Return a dict for the best matching restaurant/cafe/bar in the map area, or None."""
    q = (q or "").strip()
    if len(q) < 2:
        return None
    try:
        key = st.secrets.get("GOOGLE_MAPS_API_KEY", None)
    except Exception:
        key = None
    try:
        if key:
            hit = _google(q, key)
            if hit:
                return hit
    except Exception:
        pass
    hit = _catalog(q)
    if hit:
        return hit
    for fn in (_photon, _osm):
        try:
            hit = fn(q)
            if hit:
                return hit
        except Exception as e:  # service down or blocking this server: try the next one
            print(f"place lookup via {fn.__name__} failed: {e!r}")
    return None


def maps_link(name, addr=""):
    from urllib.parse import quote_plus
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{name} {addr}".strip())
