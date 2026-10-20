"""Booking Manager — the deal side of venue booking, companion to
modules.booking_agent (which finds venues). Suggests deal structures
from real draw math, compares competing offers on projected totals,
keeps per-phase booking checklists, scores venue/artist fit, and
generates a draft performance-agreement outline.

Figures are planning estimates from transparent, documented inputs —
not quotes from venues and not legal advice. The contract output is a
draft template: it must be reviewed by a licensed entertainment
attorney before signing."""
import re
from datetime import datetime
from typing import List, Dict, Any

from modules.tour_manager import estimate_draw, ticket_price, merch_per_head


WEEKDAY_MULTIPLIER = {
    "monday": 0.55, "tuesday": 0.60, "wednesday": 0.70, "thursday": 0.85,
    "friday": 1.00, "saturday": 1.05, "sunday": 0.75,
}


def _weekday_factor(day_of_week: str) -> float:
    return WEEKDAY_MULTIPLIER.get((day_of_week or "").strip().lower(), 1.0)


def suggest_deal_type(artist_followers: int = 5000, venue_capacity: int = 300,
                      genre: str = "", day_of_week: str = "Friday") -> Dict[str, Any]:
    """Recommend a deal structure (flat guarantee, plus deal, versus
    deal, or door split) from expected draw vs. room size and the night
    of the week, with a computed target guarantee."""
    draw = estimate_draw(artist_followers)
    capacity = max(1, int(venue_capacity or 1))
    effective_draw = min(draw, capacity)
    fill = effective_draw / capacity
    price = ticket_price(genre)
    weekday = _weekday_factor(day_of_week)
    door_gross = effective_draw * price * weekday
    target_guarantee = int(round(door_gross * 0.50 / 25.0) * 25)

    if fill >= 0.75:
        deal = "Guarantee vs. Door (Versus Deal)"
        door_split = 80
        rationale = [
            f"Expected draw ({effective_draw}) fills ~{int(fill*100)}% of this {capacity}-cap room — you have leverage.",
            "A versus deal means the artist takes the higher of the guarantee or a percentage of door revenue after agreed house expenses.",
            f"At {day_of_week} pricing, the projected door gross is ~${door_gross:,.0f}; the guarantee floor should sit at ~50% of that.",
        ]
    elif fill >= 0.45:
        deal = "Guarantee + Door Split (Plus Deal)"
        door_split = 70
        rationale = [
            f"Expected draw ({effective_draw}) is a solid ~{int(fill*100)}% of a {capacity}-cap room — enough to justify a guarantee with upside.",
            "A plus deal pays the guarantee and adds a share of door revenue beyond an agreed threshold (commonly after the first tier of house expenses).",
            f"Target guarantee: ~${target_guarantee:,} ({day_of_week} factor applied).",
        ]
    elif fill >= 0.20:
        deal = "Flat Guarantee"
        door_split = 0
        rationale = [
            f"Expected draw ({effective_draw}) is a moderate ~{int(fill*100)}% of a {capacity}-cap room — take the guaranteed money.",
            "Keep the guarantee modest and negotiate merch at 100% to the artist plus a drink tab; walk-away value is capped but certain.",
            f"Target guarantee: ~${target_guarantee:,}. Ask for it; settle no lower than 75% of it.",
        ]
    else:
        deal = "Door Split / Co-Bill"
        door_split = 80
        target_guarantee = 0
        rationale = [
            f"Expected draw ({effective_draw}) is only ~{int(fill*100)}% of a {capacity}-cap room — a guarantee is unlikely and a flat fee would look bad to the buyer.",
            "Take a door split (80/20 artist-favored is standard for developing acts) or co-bill with a stronger local act to pool draws.",
            "Push hard on non-door value: 100% of merch, content rights, and a future-date hold at better terms.",
        ]

    risks = [
        "Confirm what counts as house expenses before agreeing to any percentage deal — expenses are negotiated, not facts.",
        "Get the offer in writing before advancing: date, load-in, curfew, payment method, and cancellation terms.",
        "If a guarantee is promised, confirm WHEN it pays (day of show vs. after) and by what method.",
    ]
    return {
        "deal_type": deal,
        "suggested_guarantee": target_guarantee,
        "suggested_door_split_pct": door_split,
        "suggested_merch_split_pct": 100,
        "expected_draw": effective_draw,
        "fill_ratio": round(fill, 2),
        "projected_door_gross": round(door_gross, 2),
        "weekday_factor": weekday,
        "rationale": rationale,
        "risks": risks,
        "assumptions": {
            "draw_model": "tiered follower conversion (see tour_manager.estimate_draw)",
            "ticket_price": price,
            "guarantee_target": "50% of projected door gross, rounded to $25",
        },
    }


def _num(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _norm_split(x) -> float:
    """Normalize an artist door/merch split to a 0-1 fraction. Accepts
    70 or 0.70."""
    v = _num(x)
    if v > 1:
        v = v / 100.0
    return max(0.0, min(1.0, v))


def compare_offers(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare competing venue offers on projected total artist revenue:
    guarantee + share of door (after stated house expenses) + merch
    share. Accepts flexible key names; ranks best first."""
    scored = []
    for i, o in enumerate(offers or []):
        o = o or {}
        attendance = _num(o.get("expected_attendance",
                         o.get("attendance", o.get("expected_draw", 0))))
        if attendance <= 0:
            cap = _num(o.get("capacity", o.get("venue_capacity", 0)))
            attendance = cap * 0.5
        price = _num(o.get("ticket_price", 20.0))
        guarantee = _num(o.get("guarantee", o.get("flat_fee", 0)))
        house = _num(o.get("house_expenses", o.get("expenses", 0)))
        door_split = _norm_split(o.get("door_split", o.get("door_split_pct", 0)))
        merch_split = _norm_split(o.get("merch_split", o.get("merch_split_pct", 100)))
        merch_head = _num(o.get("merch_per_head", 4.0))
        gross_door = attendance * price
        door_share = max(0.0, gross_door - house) * door_split
        merch_share = attendance * merch_head * merch_split
        total = guarantee + door_share + merch_share
        scored.append({
            "index": i,
            "venue": o.get("venue", o.get("venue_name", f"Offer {i+1}")),
            "date": o.get("date", ""),
            "guarantee": guarantee,
            "door_share_estimate": round(door_share, 2),
            "merch_share_estimate": round(merch_share, 2),
            "projected_total": round(total, 2),
            "attendance_assumption": attendance,
            "ticket_price_assumption": price,
        })
    scored.sort(key=lambda s: s["projected_total"], reverse=True)
    for rank, s in enumerate(scored, start=1):
        s["rank"] = rank
    best = scored[0] if scored else None
    if best:
        recommendation = (
            f"Best value: {best['venue']} at ~${best['projected_total']:,.2f} projected "
            f"({len(scored)} offers compared). Confirm house expenses and payment timing in "
            f"writing before committing."
        )
    else:
        recommendation = "No offers to compare."
    return {
        "offers": scored,
        "best_offer_index": best["index"] if best else -1,
        "best_offer": best,
        "recommendation": recommendation,
        "assumptions": {
            "door_share": "attendance x ticket price, minus stated house expenses, at artist's door split",
            "merch_share": "attendance x merch per head ($4 default) at artist's merch split",
            "attendance_default": "50% of stated capacity when no attendance figure is given",
        },
    }


CHECKLISTS: Dict[str, List[str]] = {
    "pre_booking": [
        "Confirm draw expectations in writing (recent ticket counts, market history).",
        "Research the venue's typical deal for acts at your level — ask touring friends.",
        "Check routing: no conflicting radius clauses with nearby dates.",
        "Verify the venue has the right backline/PA or confirm your rider covers it.",
        "Run suggest_deal_type with your follower count, their capacity, and the night.",
    ],
    "negotiation": [
        "Negotiate the money first: guarantee or versus/plus structure, door split, merch split.",
        "Lock the hospitality rider: meals, drinks, green room, guest list count.",
        "Confirm production responsibilities: who provides sound, lights, sound engineer.",
        "Ask about local marketing support (venue email list, social posts, marquee).",
        "Never accept a verbal offer — ask for the deal in an email before you advance.",
    ],
    "contract": [
        "Confirm performance date, load-in, doors, set times, and curfew in writing.",
        "Confirm compensation, payment method, and payment timing (day of show vs after).",
        "Confirm cancellation/kill-fee terms for both sides.",
        "Confirm content rights: who films, who posts, who owns the footage.",
        "Have the draft reviewed before signing — this checklist is not legal advice.",
    ],
    "advancing": [
        "Send the stage plot and input list 2-4 weeks out; confirm receipt.",
        "Confirm hospitality numbers (meals, rooms) 2 weeks out.",
        "Confirm guest list and comp ticket policy.",
        "Share the show on your channels and ask the venue for its promo kit.",
        "Confirm the settlement contact and where/when settlement happens.",
    ],
    "day_of_show": [
        "Arrive for load-in on time; walk the stage and confirm monitor mix.",
        "Settle merch: table location, seller, splits, and float.",
        "Meet the sound engineer and confirm set length and encore policy.",
        "Collect the guarantee and count merch at the end of the night.",
        "Get the settlement sheet signed before you leave the building.",
    ],
    "post_show": [
        "File the settlement sheet with your accounting the same week.",
        "Thank the buyer/booker by email within 48 hours; share any standout photos.",
        "Log the actual draw vs. estimate — it sharpens your next negotiation.",
        "Ask for a return-date hold while the show is fresh.",
        "Follow up with fans from the guest list; they are next tour's presales.",
    ],
}


def get_booking_checklist(phase: str = "pre_booking") -> List[str]:
    """Concrete checklist items for a booking phase. Unknown phases
    fall back to pre-booking."""
    key = re.sub(r"[\s-]+", "_", (phase or "").strip().lower())
    aliases = {
        "show_day": "day_of_show", "showday": "day_of_show",
        "settlement": "day_of_show", "contracting": "contract",
        "talent_buying": "negotiation", "followup": "post_show",
    }
    key = aliases.get(key, key)
    return CHECKLISTS.get(key, CHECKLISTS["pre_booking"])


def analyze_venue_fit(venue_name: str = "Venue", venue_capacity: int = 300,
                      artist_followers: int = 5000,
                      artist_genre: str = "rock") -> Dict[str, Any]:
    """Score how well a room fits the artist: draw vs. capacity, verdict,
    and concrete suggestions. 0 = terrible fit, 100 = ideal."""
    draw = estimate_draw(artist_followers)
    capacity = max(1, int(venue_capacity or 1))
    effective = min(draw, capacity)
    fill = effective / capacity

    if fill > 1.0:
        score, verdict = 88, "Great draw — the room is undersized"
    elif 0.60 <= fill <= 1.0:
        score, verdict = 95, "Excellent fit — full-feeling room"
    elif 0.40 <= fill < 0.60:
        score, verdict = 75, "Good fit — comfortable headroom"
    elif 0.25 <= fill < 0.40:
        score, verdict = 55, "Workable — promote hard to fill it"
    elif fill >= 0.10:
        score, verdict = 30, "Risky — room is oversized for current draw"
    else:
        score, verdict = 12, "Poor fit — room far exceeds current draw"

    pros, suggestions = [], []
    if fill >= 0.40:
        pros.append(f"Expected draw ({effective}) fills ~{int(fill*100)}% of a {capacity}-cap room — a full-feeling show.")
    if fill < 0.40:
        suggestions.append("Co-bill with a stronger local act to pool draws, or route this market next tour.")
    if fill > 1.0:
        suggestions.append("Room is undersized — ask for a weekend slot and negotiate a plus deal; consider a larger room next time.")
    if draw > capacity:
        suggestions.append(f"Your draw ({draw}) exceeds capacity — protect yourself with a sellout bonus clause.")
    suggestions.append(f"Run a deal suggestion for {venue_name} before negotiating to know your target number.")

    return {
        "venue": venue_name,
        "venue_capacity": capacity,
        "artist_genre": artist_genre,
        "expected_draw": effective,
        "fill_ratio": round(fill, 2),
        "fit_score": score,
        "verdict": verdict,
        "pros": pros,
        "suggestions": suggestions,
    }


def generate_contract_terms(artist: str = "Artist", venue: str = "Venue",
                            city: str = "City", state: str = "State",
                            date: str = "TBD", guarantee: float = 0.0,
                            door_split: float = 0.0,
                            merch_split: float = 100.0) -> Dict[str, Any]:
    """Build a draft performance-agreement outline from the negotiated
    terms: structured clauses plus a formatted text version. THIS IS A
    TEMPLATE, not legal advice and not an executed contract."""
    door_split_f = _norm_split(door_split)
    merch_split_f = _norm_split(merch_split)
    g = _num(guarantee)

    terms = [
        {"section": "Engagement",
         "text": f"{venue} engages {artist} to perform on {date} in {city}, {state}. Load-in, doors, set times, and curfew to be confirmed in the advance."},
        {"section": "Compensation",
         "text": f"Artist shall receive a guarantee of ${g:,.2f}, payable {('at settlement on the night of performance' if g else 'as negotiated')}."
                  + (f" Additionally, after agreed house expenses are deducted from the gross door, the Artist shall receive {int(round(door_split_f*100))}% of remaining door revenue." if door_split_f else "")},
        {"section": "Door accounting",
         "text": ("Gross door means ticket sales collected at the door and in advance for this performance, "
                  "less applicable taxes and fees. House expenses must be itemized in writing before the performance "
                  "and agreed by both parties before settlement.") if door_split_f else "Not applicable — flat guarantee deal."},
        {"section": "Merchandise",
         "text": f"Artist retains {int(round(merch_split_f*100))}% of merchandise revenue and shall be provided a visible selling location. Venue provides no inventory."},
        {"section": "Cancellation",
         "text": ("If the Artist cancels within 14 days of the performance date, the guarantee (or agreed kill fee) "
                   "is owed. If the Venue cancels within 14 days, the guarantee is owed to the Artist. "
                   "Neither party is liable for force majeure events beyond reasonable control.")},
        {"section": "Technical & hospitality",
         "text": "Sound, lighting, and hospitality details are governed by the Artist's rider, to be agreed no later than 7 days before the performance."},
        {"section": "Promotion",
         "text": "Both parties agree to promote the performance through their available channels and to use approved artwork and billing."},
        {"section": "Governing law",
         "text": f"This agreement shall be governed by the laws of {state}."},
        {"section": "Entire agreement",
         "text": "This outline, once signed and countersigned, constitutes the parties' agreement. Verbal side agreements are not binding."},
    ]

    text = (
        "PERFORMANCE AGREEMENT (DRAFT — NOT AN EXECUTED CONTRACT)\n"
        f"Generated {datetime.now().strftime('%Y-%m-%d')} by SoundScape Pilot\n\n"
        f"Artist: {artist}\n"
        f"Venue: {venue}\n"
        f"Location: {city}, {state}\n"
        f"Date: {date}\n\n"
        f"1. ENGAGEMENT. {terms[0]['text']}\n\n"
        f"2. COMPENSATION. {terms[1]['text']}\n\n"
        f"3. DOOR ACCOUNTING. {terms[2]['text']}\n\n"
        f"4. MERCHANDISE. {terms[3]['text']}\n\n"
        f"5. CANCELLATION. {terms[4]['text']}\n\n"
        f"6. TECHNICAL & HOSPITALITY. {terms[5]['text']}\n\n"
        f"7. PROMOTION. {terms[6]['text']}\n\n"
        f"8. GOVERNING LAW. {terms[7]['text']}\n\n"
        f"9. ENTIRE AGREEMENT. {terms[8]['text']}\n\n"
        "This draft is a template generated by SoundScape Pilot and is not legal advice. "
        "Both parties should have it reviewed by a licensed entertainment attorney before signing.\n\n"
        "SoundScape Pilot Contract Engine\n"
    )

    return {
        "artist": artist,
        "venue": venue,
        "city": city,
        "state": state,
        "date": date,
        "guarantee": g,
        "door_split": door_split_f,
        "merch_split": merch_split_f,
        "terms": terms,
        "summary": (f"{artist} at {venue} ({city}, {state}) on {date}: "
                    f"${g:,.2f} guarantee"
                    + (f" + {int(round(door_split_f*100))}% of door after expenses" if door_split_f else "")
                    + f", {int(round(merch_split_f*100))}% of merch."),
        "text": text,
        "disclaimer": "Template only — not legal advice and not an executed contract. Have a licensed entertainment attorney review before signing.",
    }
