"""Tour Manager — route suggestion, revenue projection, and budgeting.

Routes are built from the real venue library in modules.booking_agent
(CURATED_VENUES): each suggested stop names a real venue from that
library in a real market. Distances use approximate city-center
coordinates (rounded, planning-grade — not survey data) and a
haversine leg calculation between consecutive stops.

Money figures are transparent estimates from a small documented model:
expected draw is derived from follower count with a tiered conversion
rate, guarantees are a share of expected door gross, and merch is a
per-head rate by genre. Every response echoes its `assumptions` so the
user can see — and override — the inputs.
"""
import math
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

# Approximate city-center coordinates (lat, lon) for every city present
# in booking_agent.CURATED_VENUES. Planning-grade only.
CITY_COORDS: Dict[str, tuple] = {
    "Abilene": (32.45, -99.73), "Ann Arbor": (42.28, -83.74),
    "Asheville": (35.60, -82.32), "Atlanta": (33.75, -84.39),
    "Austin": (30.27, -97.74), "Baton Rouge": (30.45, -91.15),
    "Bloomington": (39.17, -86.53), "Boston": (42.36, -71.06),
    "Brooklyn": (40.68, -73.94), "Cambridge": (42.37, -71.11),
    "Carrboro": (35.91, -79.08), "Charlotte": (35.23, -80.84),
    "Chicago": (41.88, -87.63), "Cincinnati": (39.10, -84.51),
    "Cleveland": (41.50, -81.69), "Columbus": (39.96, -83.00),
    "Coupland": (30.46, -97.39), "Dallas": (32.78, -96.80),
    "Decatur": (33.77, -84.30), "Denver": (39.74, -104.99),
    "Detroit": (42.33, -83.05), "Fort Worth": (32.76, -97.33),
    "Helotes": (29.58, -98.69), "Houston": (29.76, -95.37),
    "Indianapolis": (39.77, -86.16), "Inglewood": (33.96, -118.35),
    "Kansas City": (39.10, -94.58), "La Grange": (29.91, -96.88),
    "Las Vegas": (36.17, -115.14), "Los Angeles": (34.05, -118.24),
    "Luckenbach": (30.18, -98.75), "Madison": (43.07, -89.40),
    "Memphis": (35.15, -90.05), "Milwaukee": (43.04, -87.91),
    "Minneapolis": (44.98, -93.27), "Morrison": (39.65, -105.19),
    "Nashville": (36.16, -86.78), "New Braunfels": (29.70, -98.12),
    "New Orleans": (29.95, -90.07), "New York": (40.71, -74.01),
    "Orlando": (28.54, -81.38), "Philadelphia": (39.95, -75.17),
    "Phoenix": (33.45, -112.07), "Pittsburgh": (40.44, -79.99),
    "Portland": (45.52, -122.68), "Raleigh": (35.78, -78.64),
    "San Francisco": (37.77, -122.42), "Santa Cruz": (36.97, -122.03),
    "Seattle": (47.61, -122.33), "St. Louis": (38.63, -90.20),
    "St. Paul": (44.95, -93.09), "St. Petersburg": (27.77, -82.64),
    "Tampa": (27.95, -82.46), "Tucson": (32.22, -110.97),
    "Ventura": (34.27, -119.29), "West Hollywood": (34.09, -118.36),
}

STATE_ABBR = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

GENRE_TICKET = {
    "edm": 30.0, "electronic": 30.0, "hip hop": 25.0, "rap": 25.0, "pop": 25.0,
    "jazz": 25.0, "country": 22.0, "metal": 22.0, "rock": 20.0,
    "blues": 20.0, "punk": 18.0, "folk": 18.0, "americana": 18.0,
    "gospel": 15.0, "christian": 15.0,
}
GENRE_MERCH_PER_HEAD = {
    "metal": 6.0, "punk": 5.5, "rock": 5.0, "country": 5.0, "hip hop": 4.5,
    "rap": 4.5, "edm": 4.0, "electronic": 4.0, "pop": 4.0, "jazz": 3.5,
    "folk": 3.5, "americana": 3.5, "gospel": 3.0, "christian": 3.0,
}

# Tour cost model (shared by projection + budget).
FUEL_PRICE_PER_GAL = 3.50
VEHICLE_MPG = 16.0
LODGING_PER_ROOM_NIGHT = 115.0
ROOMS_PER_NIGHT = 2
PER_DIEM_PER_PERSON_DAY = 45.0
TOURING_PARTY = 5
VEHICLE_PER_DAY = 85.0
GEAR_PER_SHOW = 35.0


def ticket_price(genre: str) -> float:
    g = (genre or "").lower()
    for key, price in GENRE_TICKET.items():
        if key in g:
            return price
    return 20.0


def merch_per_head(genre: str) -> float:
    g = (genre or "").lower()
    for key, rate in GENRE_MERCH_PER_HEAD.items():
        if key in g:
            return rate
    return 4.0


def estimate_draw(followers: int) -> int:
    """Expected in-person draw per show from social followers. Tiered
    conversion: small followings convert at a higher rate (friends,
    family, local scene) than large ones."""
    f = max(0, int(followers or 0))
    if f < 1000:
        draw = max(25, f * 0.15)
    elif f < 10000:
        draw = f * 0.06
    elif f < 100000:
        draw = f * 0.035
    else:
        draw = f * 0.02
    return int(round(draw))


def _haversine_mi(a: tuple, b: tuple) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def _venues_index() -> Dict[str, Dict[str, Any]]:
    """city -> {state, venues[]} from the booking agent's curated library."""
    from modules.booking_agent import CURATED_VENUES
    index: Dict[str, Dict[str, Any]] = {}
    for state, venues in CURATED_VENUES.items():
        for v in venues:
            city = v.get("city", "")
            if not city:
                continue
            entry = index.setdefault(city, {"state": state, "venues": []})
            entry["venues"].append(v)
    return index


def _resolve_anchor(home_city: str, index: Dict[str, Dict[str, Any]]) -> tuple:
    """Resolve a free-form home_city ('Austin, TX' / 'Austin') to
    (city, state, note). Falls back to the state in the string, then to
    the market with the largest curated venue library."""
    raw = (home_city or "").strip()
    name = raw.split(",")[0].strip()
    for city in index:
        if city.lower() == name.lower():
            return city, index[city]["state"], ""
    # State fallback: "Somewhere, TX" or "Texas" → biggest city in that state.
    state_guess = ""
    tail = raw.rsplit(",", 1)[-1].strip() if "," in raw else raw
    if len(tail) == 2 and tail.upper() in STATE_ABBR:
        state_guess = STATE_ABBR[tail.upper()]
    elif tail.title() in {index[c]["state"] for c in index}:
        state_guess = tail.title()
    if state_guess:
        in_state = [c for c in index if index[c]["state"] == state_guess]
        if in_state:
            best = max(in_state, key=lambda c: sum(v.get("capacity", 0) or 0 for v in index[c]["venues"]))
            return best, state_guess, f"Home city '{raw}' not in the venue library; anchored on {best}, {state_guess}."
    best = max(index.keys(), key=lambda c: len(index[c]["venues"]))
    return best, index[best]["state"], f"Home city '{raw}' not recognized; anchored on {best}, {index[best]['state']} (largest venue library)."


def _pick_venue(city_entry: Dict[str, Any], target_draw: int) -> Dict[str, Any]:
    """Pick the room closest to ~1.5x expected draw (a full-feeling room
    with headroom), preferring venues with a known capacity."""
    venues = city_entry["venues"]
    known = [v for v in venues if (v.get("capacity") or 0) > 0]
    pool = known or venues
    target = max(150, target_draw * 1.5)
    return min(pool, key=lambda v: abs((v.get("capacity") or 0) - target))


def suggest_tour_route(artist_genre: str = "", home_city: str = "",
                       followers: int = 5000, num_shows: int = 12) -> Dict[str, Any]:
    """Build a nearest-neighbor tour route through real library venues,
    starting from the artist's home market. One show per city; dates run
    Thu/Fri/Sat clusters starting the Thursday at least 10 days out."""
    index = _venues_index()
    anchor, anchor_state, note = _resolve_anchor(home_city, index)
    draw = estimate_draw(followers)
    price = ticket_price(artist_genre)

    # Nearest-neighbor ordering outward from the anchor.
    remaining = [c for c in index if c in CITY_COORDS]
    route: List[str] = []
    current = anchor if anchor in CITY_COORDS else remaining[0]
    route.append(current)
    remaining.remove(current)
    while remaining and len(route) < max(1, int(num_shows or 12)):
        nxt = min(remaining, key=lambda c: _haversine_mi(CITY_COORDS[current], CITY_COORDS[c]))
        route.append(nxt)
        remaining.remove(nxt)
        current = nxt

    # First show: the Thursday at least 10 days from today.
    start = date.today() + timedelta(days=10)
    while start.weekday() != 3:  # Thursday
        start += timedelta(days=1)
    gaps = [1, 1, 4]  # Thu → Fri → Sat → next Thu

    shows = []
    total_miles = 0.0
    prev: Optional[str] = None
    show_date = start
    for i, city in enumerate(route):
        if i > 0:
            show_date = show_date + timedelta(days=gaps[(i - 1) % 3])
        leg = _haversine_mi(CITY_COORDS[prev], CITY_COORDS[city]) if prev else 0.0
        total_miles += leg
        venue = _pick_venue(index[city], draw)
        capacity = venue.get("capacity") or 0
        local_draw = draw if city != anchor else int(draw * 1.15)
        expected = min(local_draw, capacity) if capacity else local_draw
        guarantee = int(round(expected * price * 0.45 / 25.0) * 25)
        shows.append({
            "show_number": i + 1,
            "date": show_date.isoformat(),
            "day_of_week": show_date.strftime("%A"),
            "city": city,
            "state": index[city]["state"],
            "venue": venue.get("name", ""),
            "venue_capacity": capacity,
            "venue_contact": venue.get("contact", ""),
            "distance_from_prev_mi": int(round(leg)),
            "expected_draw": expected,
            "ticket_price_assumption": price,
            "estimated_guarantee": guarantee,
        })
        prev = city

    return {
        "genre": artist_genre,
        "home_city": f"{anchor}, {anchor_state}",
        "followers": followers,
        "shows": shows,
        "total_shows": len(shows),
        "total_miles": int(round(total_miles)),
        "estimated_gross_guarantees": sum(s["estimated_guarantee"] for s in shows),
        "assumptions": {
            "draw_model": "followers converted at 15% (<1k) / 6% (1k-10k) / 3.5% (10k-100k) / 2% (>100k); +15% in the home market; capped at venue capacity",
            "guarantee_model": "45% of expected door gross (expected draw x assumed ticket price), rounded to $25",
            "distances": "approximate city-center to city-center, planning grade",
            "venue_source": "SoundScape Pilot curated venue library (modules.booking_agent)",
            **({"note": note} if note else {}),
        },
    }


def calculate_tour_projection(shows: int = 12, avg_guarantee: float = 1500.0,
                              followers: int = 5000, genre: str = "rock") -> Dict[str, Any]:
    """Project a tour's economics at a given scale: guarantees, merch,
    and the standard cost model, with a break-even guarantee per show."""
    shows = max(0, int(shows))
    attendance = estimate_draw(followers)
    gross_guarantees = shows * float(avg_guarantee)
    merch = shows * attendance * merch_per_head(genre)
    total_revenue = gross_guarantees + merch

    avg_leg_mi = 275.0
    miles = shows * avg_leg_mi
    tour_days = int(shows * 1.4) + 1
    expenses = {
        "fuel": round(miles / VEHICLE_MPG * FUEL_PRICE_PER_GAL, 2),
        "lodging": round(shows * ROOMS_PER_NIGHT * LODGING_PER_ROOM_NIGHT, 2),
        "per_diem": round(tour_days * TOURING_PARTY * PER_DIEM_PER_PERSON_DAY, 2),
        "vehicle": round(tour_days * VEHICLE_PER_DAY, 2),
        "gear_backline": round(shows * GEAR_PER_SHOW, 2),
    }
    total_expenses = round(sum(expenses.values()), 2)
    net = round(total_revenue - total_expenses, 2)
    return {
        "shows": shows,
        "genre": genre,
        "followers": followers,
        "expected_attendance_per_show": attendance,
        "gross_guarantees": round(gross_guarantees, 2),
        "estimated_merch_revenue": round(merch, 2),
        "total_projected_revenue": round(total_revenue, 2),
        "expenses": expenses,
        "total_expenses": total_expenses,
        "projected_net": net,
        "per_show_net": round(net / shows, 2) if shows else 0.0,
        "break_even_guarantee_per_show": round(total_expenses / shows, 2) if shows else 0.0,
        "assumptions": {
            "merch_per_head": merch_per_head(genre),
            "avg_leg_miles": avg_leg_mi,
            "tour_days": tour_days,
            "cost_model": f"fuel ${FUEL_PRICE_PER_GAL}/gal at {VEHICLE_MPG:.0f} mpg; lodging {ROOMS_PER_NIGHT} rooms x ${LODGING_PER_ROOM_NIGHT:.0f}/night per show; per diem ${PER_DIEM_PER_PERSON_DAY:.0f} x {TOURING_PARTY} people; vehicle ${VEHICLE_PER_DAY:.0f}/day; gear ${GEAR_PER_SHOW:.0f}/show",
        },
    }


def build_tour_budget(shows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Turn a list of show dicts (e.g. from suggest_tour_route) into a
    line-item budget: guarantee + merch income against the standard
    tour cost model driven by the route's actual leg distances."""
    shows = shows or []
    guarantees = 0.0
    merch = 0.0
    miles = 0.0
    per_show = []
    for s in shows:
        g = float(s.get("estimated_guarantee", s.get("guarantee", 0)) or 0)
        draw = int(s.get("expected_draw", s.get("expected_attendance", 0)) or 0)
        m = float(s.get("merch_estimate", draw * 4.0) or 0)
        leg = float(s.get("distance_from_prev_mi", s.get("distance_miles", 0)) or 0)
        guarantees += g
        merch += m
        miles += leg
        per_show.append({
            "city": s.get("city", ""),
            "venue": s.get("venue", s.get("venue_name", "")),
            "date": s.get("date", ""),
            "guarantee": g,
            "merch_estimate": m,
            "leg_miles": leg,
        })

    n = len(shows)
    tour_days = n + 1
    expense_items = [
        {"item": "Fuel", "amount": round(miles / VEHICLE_MPG * FUEL_PRICE_PER_GAL, 2),
         "basis": f"{int(round(miles))} mi at {VEHICLE_MPG:.0f} mpg, ${FUEL_PRICE_PER_GAL}/gal"},
        {"item": "Lodging", "amount": round(n * ROOMS_PER_NIGHT * LODGING_PER_ROOM_NIGHT, 2),
         "basis": f"{n} nights x {ROOMS_PER_NIGHT} rooms x ${LODGING_PER_ROOM_NIGHT:.0f}"},
        {"item": "Per diem", "amount": round(tour_days * TOURING_PARTY * PER_DIEM_PER_PERSON_DAY, 2),
         "basis": f"{tour_days} days x {TOURING_PARTY} people x ${PER_DIEM_PER_PERSON_DAY:.0f}"},
        {"item": "Vehicle", "amount": round(tour_days * VEHICLE_PER_DAY, 2),
         "basis": f"{tour_days} days x ${VEHICLE_PER_DAY:.0f}"},
        {"item": "Gear / backline", "amount": round(n * GEAR_PER_SHOW, 2),
         "basis": f"{n} shows x ${GEAR_PER_SHOW:.0f}"},
    ]
    subtotal = round(sum(i["amount"] for i in expense_items), 2)
    contingency = round(subtotal * 0.07, 2)
    expense_items.append({"item": "Contingency (7%)", "amount": contingency, "basis": "7% of subtotal"})
    total_expenses = round(subtotal + contingency, 2)
    total_income = round(guarantees + merch, 2)
    net = round(total_income - total_expenses, 2)

    return {
        "shows_count": n,
        "total_miles": int(round(miles)),
        "income": {
            "guarantees": round(guarantees, 2),
            "merch_estimate": round(merch, 2),
            "total": total_income,
        },
        "expenses": expense_items,
        "total_expenses": total_expenses,
        "net": net,
        "margin_pct": round(net / total_income * 100, 1) if total_income else 0.0,
        "per_show": per_show,
        "assumptions": {
            "merch_per_head_default": 4.0,
            "cost_model": f"fuel ${FUEL_PRICE_PER_GAL}/gal at {VEHICLE_MPG:.0f} mpg; lodging {ROOMS_PER_NIGHT} rooms x ${LODGING_PER_ROOM_NIGHT:.0f}/night per show; per diem ${PER_DIEM_PER_PERSON_DAY:.0f} x {TOURING_PARTY} people; vehicle ${VEHICLE_PER_DAY:.0f}/day; gear ${GEAR_PER_SHOW:.0f}/show; contingency 7%",
        },
    }
