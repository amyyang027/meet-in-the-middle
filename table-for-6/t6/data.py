"""Synthetic Bay Area instance generator for Table for 6.

Every symbol here matches the report: users i in I, venues v in V, slots t in T,
user-table value c_{ivt}, pairwise compatibility q_{ij}, capacities R_{vt}.
"""
from dataclasses import dataclass, field
import numpy as np

SLOTS = ["Fri 7pm", "Sat 11am", "Sat 7pm"]
CONGESTION = np.array([15.0, 5.0, 8.0])          # extra minutes on the Bay Bridge, by slot
TYPES = ["restaurant", "cafe", "bar"]
OPEN = {"restaurant": [0, 1, 2], "cafe": [1], "bar": [0, 2]}
CUISINES = ["Mexican", "Chinese", "Italian", "Japanese", "Indian", "Thai", "Ethiopian", "American"]
N_TAGS = 15                                       # interest tags (hiking, board games, jazz, ...)

# (name, lat, lon, side, weight for users, weight for venues); side 0 = SF, 1 = East Bay
HOODS = [
    ("Mission", 37.7599, -122.4148, 0, 1.2, 1.6),
    ("SoMa", 37.7785, -122.4056, 0, 1.0, 1.2),
    ("North Beach", 37.8061, -122.4103, 0, 0.6, 1.2),
    ("Sunset", 37.7531, -122.4950, 0, 1.0, 0.6),
    ("Richmond", 37.7803, -122.4647, 0, 0.8, 0.7),
    ("Downtown Oakland", 37.8044, -122.2712, 1, 1.0, 1.0),
    ("Temescal", 37.8337, -122.2617, 1, 0.7, 0.8),
    ("Berkeley", 37.8716, -122.2727, 1, 1.2, 0.9),
]
BRIDGE = {0: (37.7880, -122.3900), 1: (37.8250, -122.3150)}   # SF and Oakland touchdowns
TOLL = 8.0                                         # $ westbound (East Bay -> SF), approximate


@dataclass
class Params:
    w: tuple = (3.5, 3.5, 1.5, 1.5)     # weights on venue type, cuisine, price, slot preference
    beta: tuple = (3.0, 1.5)            # interests, age gap (gender is a rule, not a score)
    lam_d: float = 0.08                 # utility per minute of travel
    lam_tau: float = 0.20               # utility per dollar of toll
    M_unseated: float = 8.0             # penalty M_i for leaving user i without a table
    L: int = 4
    U: int = 6
    age_span: float = 12.0              # years before the age-spread penalty starts
    rho_age: float = 0.5                # penalty per year of spread above age_span
    gamma: float = 0.0                  # weight on the fairness floor theta
    show_mode: str = "none"             # none | expected | chance
    exp_att: float = 4.25               # E[attendance] >= exp_att (linear proxy)
    chance_alpha: float = 0.90          # P(at least L show) >= chance_alpha (exact, Model B only)


@dataclass
class Instance:
    N: int
    V: int
    home: np.ndarray        # (N,2) lat/lon
    side: np.ndarray        # (N,)
    car: np.ndarray         # (N,) bool
    age: np.ndarray
    gender: np.ndarray      # 0 = woman, 1 = man, 2 = nonbinary
    same_pref: np.ndarray   # (N,) bool, asked for same-gender tables
    interests: np.ndarray   # (N,N_TAGS) 0/1
    pref_type: np.ndarray   # (N,3) 1..5
    pref_cuis: np.ndarray   # (N,8) 1..5
    budget: np.ndarray      # (N,) 1..3
    avail: np.ndarray       # (N,3) a_{it}
    slot_pref: np.ndarray   # (N,3) in [0,1]
    show: np.ndarray        # (N,) show-up probability rho_i
    v_loc: np.ndarray
    v_side: np.ndarray
    v_type: np.ndarray
    v_cuis: np.ndarray      # -1 for cafes and bars
    v_price: np.ndarray
    v_name: list
    R: np.ndarray           # (V,3) tables venue v can host in slot t (0 = closed)
    p: Params = field(default_factory=Params)
    # derived
    d: np.ndarray = None     # (N,V,3) minutes
    tau: np.ndarray = None   # (N,V) dollars
    sat: np.ndarray = None   # (N,V,3) p_{ivt}
    c: np.ndarray = None     # (N,V,3) c_{ivt} (= -inf where infeasible)
    q: np.ndarray = None     # (N,N)
    v_addr: list = None      # street addresses (real venues only)
    bonus: dict = None       # {(i, v): extra satisfaction}, e.g. a guest's own favorite spot


REST_NAMES = {0: "Casa Nopal", 1: "Jade Lantern", 2: "Osteria Fico", 3: "Kumo", 4: "Saffron Room",
              5: "Basil House", 6: "Injera Table", 7: "The Long Table"}
CAFE_NAMES = ["Morning Fog Coffee", "Little Ritual", "Slow Pour", "Paper Crane Cafe", "Sunday Press"]
BAR_NAMES = ["The Velvet Hour", "Low Tide", "Copper & Rye", "Night Heron", "Last Light"]


def venue_names(vh, v_type, v_cuis):
    names, used = [], {}
    for v in range(len(vh)):
        if v_type[v] == 0:
            base = REST_NAMES[int(v_cuis[v])]
        elif v_type[v] == 1:
            base = CAFE_NAMES[v % len(CAFE_NAMES)]
        else:
            base = BAR_NAMES[v % len(BAR_NAMES)]
        name = f"{base}, {HOODS[vh[v]][0]}"
        used[name] = used.get(name, 0) + 1
        names.append(name if used[name] == 1 else f"{name} ({used[name]})")
    return names


def haversine(a, b):
    a, b = np.radians(a), np.radians(b)
    dlat = b[..., 0] - a[..., 0]
    dlon = b[..., 1] - a[..., 1]
    h = np.sin(dlat / 2) ** 2 + np.cos(a[..., 0]) * np.cos(b[..., 0]) * np.sin(dlon / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))


def generate(N, seed=0, V=None, params=None, real=False):
    rng = np.random.default_rng(seed)
    V = V or max(8, int(np.ceil(N / 6)))
    hw = np.array([h[4] for h in HOODS]); hw /= hw.sum()
    vw = np.array([h[5] for h in HOODS]); vw /= vw.sum()
    centers = np.array([[h[1], h[2]] for h in HOODS])
    hs = rng.choice(len(HOODS), N, p=hw)
    home = centers[hs] + rng.normal(0, 0.008, (N, 2))
    side = np.array([HOODS[h][3] for h in hs])
    car = rng.random(N) < 0.55
    age = np.clip(rng.normal(28, 5, N).round(), 21, 45)
    gender = rng.choice(3, N, p=[0.48, 0.48, 0.04])
    same_pref = rng.random(N) < 0.12
    # interests: a few latent "personas" so compatibility has structure
    personas = rng.random((5, N_TAGS)) < 0.3
    pid = rng.integers(0, 5, N)
    interests = ((rng.random((N, N_TAGS)) < 0.12) | (personas[pid] & (rng.random((N, N_TAGS)) < 0.75))).astype(float)
    pref_type = rng.integers(1, 6, (N, 3)).astype(float)
    pref_cuis = rng.integers(1, 6, (N, 8)).astype(float)
    budget = rng.integers(1, 4, N).astype(float)
    avail = rng.random((N, 3)) < 0.6
    none = ~avail.any(1)
    avail[none, rng.integers(0, 3, none.sum())] = True
    slot_pref = rng.random((N, 3))
    show = np.clip(rng.beta(8.5, 1.5, N), 0.55, 0.99)

    v_addr = None
    if real:
        vh, v_loc, v_type, v_cuis, v_price, v_name, v_addr = pick_real_venues(V, rng, vw)
    else:
        vh = rng.choice(len(HOODS), V, p=vw)
        v_loc = centers[vh] + rng.normal(0, 0.005, (V, 2))
        v_type = rng.choice(3, V, p=[0.5, 0.25, 0.25])
        v_cuis = np.where(v_type == 0, rng.integers(0, 8, V), -1)
        v_price = rng.integers(1, 4, V).astype(float)
        v_name = venue_names(vh, v_type, v_cuis)
    v_side = np.array([HOODS[h][3] for h in vh])
    R = np.zeros((V, 3), dtype=int)
    for v in range(V):
        for t in OPEN[TYPES[v_type[v]]]:
            R[v, t] = rng.integers(1, 3)
    inst = Instance(N, V, home, side, car, age, gender, same_pref, interests, pref_type, pref_cuis,
                    budget, avail, slot_pref, show, v_loc, v_side, v_type, v_cuis, v_price, v_name, R,
                    params or Params(), v_addr=v_addr)
    derive(inst)
    return inst


def pick_real_venues(V, rng, vw):
    """Sample V real venues (OpenStreetMap) by neighborhood weight, about half restaurants."""
    from .venues import REAL_VENUES
    rows = list(REAL_VENUES)
    want = rng.choice(3, V, p=[0.5, 0.25, 0.25])
    chosen = []
    for typ in want:
        pool = [r for r in rows if r[3] == typ and r not in chosen] or [r for r in rows if r not in chosen]
        w = np.array([vw[r[5]] for r in pool]); w /= w.sum()
        chosen.append(pool[rng.choice(len(pool), p=w)])
    vh = np.array([r[5] for r in chosen])
    v_loc = np.array([[r[1], r[2]] for r in chosen])
    v_type = np.array([r[3] for r in chosen])
    v_cuis = np.array([r[4] for r in chosen])
    # OpenStreetMap rarely records price, so the level is a rough estimate by kind of place
    v_price = np.array([1.0 if r[3] == 1 or r[4] in (0, 7) else 2.0 for r in chosen])
    v_name = [f"{r[0]}, {HOODS[r[5]][0]}" for r in chosen]
    v_addr = [r[6] for r in chosen]
    return vh, v_loc, v_type, v_cuis, v_price, v_name, v_addr


def add_venue(inst, name, lat, lon, vtype, cuisine=-1, addr="", price=2.0, slots=None):
    """Append one venue (e.g. a guest's favorite spot found on a map search). Returns its index."""
    side = 1 if lon > -122.33 else 0
    inst.v_loc = np.vstack([inst.v_loc, [[lat, lon]]])
    inst.v_side = np.append(inst.v_side, side)
    inst.v_type = np.append(inst.v_type, int(vtype))
    inst.v_cuis = np.append(inst.v_cuis, int(cuisine))
    inst.v_price = np.append(inst.v_price, float(price))
    inst.v_name = list(inst.v_name) + [name]
    inst.v_addr = (list(inst.v_addr) if inst.v_addr else [""] * inst.V) + [addr]
    row = np.zeros((1, 3), dtype=int)
    for t in (slots if slots is not None else OPEN[TYPES[int(vtype)]]):
        row[0, t] = 2
    inst.R = np.vstack([inst.R, row])
    inst.V += 1
    derive(inst)
    return inst.V - 1


def derive(inst):
    """Compute d_{ivt}, tau_{iv}, p_{ivt}, c_{ivt}, q_{ij} from raw attributes and inst.p."""
    p, N, V = inst.p, inst.N, inst.V
    H, VL = inst.home[:, None, :], inst.v_loc[None, :, :]
    direct = 1.35 * haversine(H, VL)                                   # km, same side of the bay
    b_own = np.array([BRIDGE[s] for s in inst.side])[:, None, :]
    b_far = np.array([BRIDGE[1 - s] for s in inst.side])[:, None, :]
    cross_km = 1.35 * (haversine(H, b_own) + haversine(b_far, VL)) + 7.0
    crosses = inst.side[:, None] != inst.v_side[None, :]
    speed = np.where(inst.car, 24.0, 17.0)[:, None]                    # km/h door to door
    base = np.where(crosses, cross_km, direct) / speed * 60 + 6.0      # + 6 min to walk/park
    cong = np.where(inst.car[:, None, None], CONGESTION[None, None, :], 4.0)   # BART is less traffic sensitive
    inst.d = base[:, :, None] + crosses[:, :, None] * cong
    westbound = crosses & (inst.side[:, None] == 1)
    inst.tau = np.where(westbound & inst.car[:, None], TOLL, 0.0)

    m_type = (inst.pref_type[:, inst.v_type] - 1) / 4                 # (N,V)
    cuis = np.where(inst.v_cuis >= 0, inst.v_cuis, 0)
    m_cuis = np.where(inst.v_cuis[None, :] >= 0, (inst.pref_cuis[:, cuis] - 1) / 4, 0.6)
    m_price = 1 - np.abs(inst.budget[:, None] - inst.v_price[None, :]) / 2
    w = p.w
    inst.sat = (w[0] * m_type + w[1] * m_cuis + w[2] * m_price)[:, :, None] + w[3] * inst.slot_pref[:, None, :]
    for (i, v), b in (inst.bonus or {}).items():
        if v < V:
            inst.sat[i, v, :] += b
    c = inst.sat - p.lam_d * inst.d - p.lam_tau * inst.tau[:, :, None]
    ok = inst.avail[:, None, :] & (inst.R[None, :, :] > 0)
    inst.c = np.where(ok, c, -np.inf)

    X = inst.interests
    nrm = np.linalg.norm(X, axis=1) + 1e-9
    cos = (X @ X.T) / np.outer(nrm, nrm)
    agegap = np.abs(inst.age[:, None] - inst.age[None, :]) / 10
    b = p.beta
    q = b[0] * cos - b[1] * agegap
    np.fill_diagonal(q, 0.0)
    inst.q = q
    return inst


def tables_index(inst):
    """Candidate tables K: R_{vt} copies of every open (v, t)."""
    K = []
    for v in range(inst.V):
        for t in range(3):
            for r in range(inst.R[v, t]):
                K.append((v, t, r))
    return K


TAG_NAMES = ["Hiking", "Board games", "Live music", "Jazz", "Film", "Books", "Running", "Cooking",
             "Art galleries", "Tech", "Startups", "Photography", "Travel", "Yoga", "Comedy"]
GENDERS = ["Woman", "Man", "Nonbinary"]


def set_user(inst, i, profile):
    """Overwrite user i with a real person's answers, then recompute every parameter.

    profile keys: hood (index into HOODS), car (bool), age, gender (0/1/2), same_gender (bool),
    interests (list of tag indices), type_pref (3 ratings 1-5), cuisine_pref (8 ratings 1-5),
    budget (1-3), avail (3 bools), slot_pref (3 numbers in [0,1]).
    """
    h = HOODS[profile["hood"]]
    inst.home[i] = [h[1], h[2]]
    inst.side[i] = h[3]
    inst.car[i] = bool(profile["car"])
    inst.age[i] = float(profile["age"])
    inst.gender[i] = int(profile["gender"])
    inst.same_pref[i] = bool(profile["same_gender"])
    vec = np.zeros(N_TAGS)
    vec[list(profile["interests"])] = 1.0
    inst.interests[i] = vec
    inst.pref_type[i] = np.array(profile["type_pref"], dtype=float)
    inst.pref_cuis[i] = np.array(profile["cuisine_pref"], dtype=float)
    inst.budget[i] = float(profile["budget"])
    av = np.array(profile["avail"], dtype=bool)
    inst.avail[i] = av if av.any() else np.array([True, True, True])
    inst.slot_pref[i] = np.array(profile["slot_pref"], dtype=float)
    inst.show[i] = 0.95
    derive(inst)
    return inst
