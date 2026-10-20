"""Radio Promoter — station classification, per-format pitch strategy,
campaign summaries, and follow-up copy for the Radio Autopilot.

Companion to modules/radio_finder.py (which discovers stations). This
module decides *how* to pitch each station: it classifies the station's
format from its name/vector, picks a format-appropriate strategy, and
builds the actual pitch text from the artist's real EPK fields.

Success rates are planning estimates computed from observable signals
(format receptiveness, whether the artist supplied streaming links and
press quotes, genre/format fit) — they are not measured response data.
"""
import re
from typing import List, Dict, Any


# Programming-emphasis tags detectable from a station name / vector.
# Order matters: the first matching tag wins.
EMPHASIS_TAGS = [
    ("christian", ["christian", "gospel", "praise", "worship", "k-love", "klove",
                   "air1", "air 1", "ministry", "faith", "inspir"]),
    ("classical", ["classical", "symphony", "opera"]),
    ("jazz", ["jazz"]),
    ("hip_hop", ["hip hop", "hip-hop", "rap", "shade 45", "urban"]),
    ("country", ["country", "americana", "red dirt", "texas country"]),
    ("metal", ["metal", "hardcore"]),
    ("punk", ["punk"]),
    ("electronic", ["electronic", "edm", "dance", "bpm", "di.fm"]),
    ("news_talk", ["news", "talk", "npr", "public affairs"]),
    ("rock", ["rock", "alternative", "indie", "aaa", "triple a"]),
]

# How receptive each delivery format tends to be to an independent
# submission, on a 0-100 scale. Used only as the starting point for
# the per-pitch estimate; per-station signals adjust it.
FORMAT_BASE_RATE = {
    "college_radio": 55,
    "internet_radio": 50,
    "public_radio": 35,
    "fm_radio": 30,
    "am_radio": 28,
    "military_radio": 25,
    "satellite_radio": 10,
    "radio": 30,
}

STRATEGIES = {
    "college_radio": {
        "strategy": ("College music directors program for discovery, not familiarity. Lead with the "
                     "story and the single, keep the email short, and service a clean streaming "
                     "link plus a downloadable WAV/MP3. Offer a station ID or a short interview "
                     "segment — college MDs love exclusive content they can air."),
        "tips": ("MD office hours are usually posted on the station site; send Tue-Thu mornings. "
                 "Follow up once after 10 days, then move on."),
        "lead_time_days": 14,
    },
    "internet_radio": {
        "strategy": ("Internet programmers add tracks fast and judge on the first 15 seconds. "
                     "Send the stream link up top, name the exact track, and give them the "
                     "genre tags they can slot you under. Ask about rotation tiers and any "
                     "featured-artist or premiere slots."),
        "tips": ("Many internet stations accept submissions through their site form as well as "
                 "email — use the form if one exists, it routes to the actual playlist queue."),
        "lead_time_days": 7,
    },
    "public_radio": {
        "strategy": ("Public radio music shows are curated by hosts, not committees. Pitch the "
                     "specific program/host whose playlist your sound fits, reference a recent "
                     "show segment, and emphasize songwriting and story. One track, no hype."),
        "tips": ("Hosts plan specialty shows weeks out. Offer a live in-studio session if you "
                 "will be touring through their market."),
        "lead_time_days": 28,
    },
    "satellite_radio": {
        "strategy": ("Satellite channels are programmed centrally and rarely add unsigned music "
                     "from cold email. The realistic path is heat first: charting college/internet "
                     "spins, streaming numbers, and press. Frame the pitch as a status update "
                     "with proof, not a first introduction."),
        "tips": ("If you have a label services team or radio promoter, satellite is their call to "
                 "make — a direct co-signed pitch lands far better than a cold one."),
        "lead_time_days": 42,
    },
    "military_radio": {
        "strategy": ("Armed Forces Network-style outlets program familiar, broadly appealing "
                     "material for deployed audiences. Pitch your most accessible track, note "
                     "any military/first-responder connection in the artist's story if genuine, "
                     "and keep metadata perfectly clean."),
        "tips": ("Clean edits matter — service the radio edit, not the album version, if lyrics "
                 "are explicit."),
        "lead_time_days": 21,
    },
    "fm_radio": {
        "strategy": ("Commercial FM adds are decided in weekly music meetings and favor tracks "
                     "with existing momentum. Pitch the music director with your strongest "
                     "30 seconds, current spin/streaming proof points, and a local angle "
                     "(tour date, hometown, regional press). Keep it to one track."),
        "tips": ("Music meetings are typically early week — land the email Monday so it is in "
                 "the pile when the MD builds the meeting packet."),
        "lead_time_days": 21,
    },
    "am_radio": {
        "strategy": ("AM music outlets skew older and local. Emphasize local ties, live "
                     "performance history in their market, and standards-friendly material. "
                     "Offer an on-air interview — AM hosts fill a lot of talk segments."),
        "tips": ("A short phone interview offer converts better than a second track link."),
        "lead_time_days": 14,
    },
    "radio": {
        "strategy": ("Identify the music director, send one track with streaming and download "
                     "links, a two-line pitch on why their listeners fit, and a clear local "
                     "angle if you have one. Follow up once, politely, after 10-14 days."),
        "tips": "Short beats clever — five sentences and the links is the whole email.",
        "lead_time_days": 14,
    },
}


def _base_format(name: str, vector: str) -> str:
    text = f"{name} {vector}".lower()
    if "college" in text or "university" in text or "campus" in text:
        return "college_radio"
    if "military" in text or "armed forces" in text or "afn" in text:
        return "military_radio"
    if "satellite" in text or "sirius" in text:
        return "satellite_radio"
    if "public" in text or "npr" in text:
        return "public_radio"
    if re.search(r"\bam\b", text) or " am " in f" {text} ":
        return "am_radio"
    if re.search(r"\bfm\b", text):
        return "fm_radio"
    if "internet" in text or "stream" in text or "online" in text:
        return "internet_radio"
    return "radio"


def classify_station(name: str, vector: str, location: str = "") -> str:
    """Classify a station into a format id like 'college_radio' or
    'fm_country'. Derived only from the station name and vector strings
    the finder already collected."""
    base = _base_format(name or "", vector or "")
    text = f"{name} {vector}".lower()
    for tag, keywords in EMPHASIS_TAGS:
        if any(k in text for k in keywords):
            if base in ("fm_radio", "am_radio", "internet_radio", "radio"):
                return f"{base.split('_')[0]}_{tag}" if base != "radio" else tag + "_radio"
            return base
    return base


def _base_of(fmt: str) -> str:
    for base in FORMAT_BASE_RATE:
        if fmt == base or fmt.startswith(base.split("_")[0] + "_") or fmt.endswith("_" + base.split("_")[0]):
            return base
    if fmt.startswith("fm_"):
        return "fm_radio"
    if fmt.startswith("am_"):
        return "am_radio"
    if fmt.startswith("internet_"):
        return "internet_radio"
    return "radio"


def _strategy_for(fmt: str) -> Dict[str, Any]:
    base = _base_of(fmt)
    return STRATEGIES.get(base, STRATEGIES["radio"])


def _success_estimate(fmt: str, genre: str, spotify: str, soundcloud: str,
                      press_quotes: str, station_vector: str) -> str:
    base = _base_of(fmt)
    score = FORMAT_BASE_RATE.get(base, 30)
    if spotify:
        score += 10
    if soundcloud:
        score += 5
    if press_quotes:
        score += 10
    genre_l = (genre or "").lower()
    fmt_l = fmt.lower()
    if genre_l and any(w in fmt_l for w in genre_l.split() if len(w) > 2):
        score += 12
    if station_vector and "curated" in station_vector.lower():
        score += 3
    score = max(5, min(90, score))
    return f"{score}%"


def get_pitch_strategy(station_name: str = "", station_format: str = "",
                       artist: str = "Artist", genre: str = "", bio: str = "",
                       spotify: str = "", soundcloud: str = "",
                       press_quotes: str = "", station_location: str = "",
                       station_vector: str = "") -> Dict[str, Any]:
    """Build the full pitch package for one station: strategy, tips, an
    estimated response rate, and the finished pitch email body built
    from the artist's supplied EPK fields."""
    fmt = station_format or classify_station(station_name, station_vector, location=station_location)
    strat = _strategy_for(fmt)
    success = _success_estimate(fmt, genre, spotify, soundcloud, press_quotes, station_vector)

    fmt_label = fmt.replace("_", " ").title()
    lines = [f"Dear {station_name} Music Director,", ""]
    intro = f"I'm writing to submit new music from {artist}"
    if genre:
        intro += f", a {genre} artist"
    if station_location:
        intro += f", for consideration at your station in {station_location}"
    intro += "."
    lines.append(intro)
    if bio:
        lines.append("")
        lines.append(bio.strip()[:600])
    lines.append("")
    lines.append("Listen here:")
    if spotify:
        lines.append(f"Spotify: {spotify}")
    if soundcloud:
        lines.append(f"SoundCloud: {soundcloud}")
    if not spotify and not soundcloud:
        lines.append("(Streaming links available on request — see our EPK.)")
    if press_quotes:
        lines.append("")
        lines.append("What the press is saying:")
        lines.append(press_quotes.strip()[:400])
    lines.append("")
    lines.append("We'd be grateful for a spin in your new-music rotation and are happy to "
                 "record a station ID or join for a short interview if useful.")
    lines.append("")
    lines.append("Thank you for supporting independent music,")
    lines.append(artist)

    return {
        "station_name": station_name,
        "format": fmt,
        "format_label": fmt_label,
        "pitch_strategy": strat["strategy"],
        "tips": strat["tips"],
        "lead_time_days": strat["lead_time_days"],
        "success_rate": success,
        "pitch_body": "\n".join(lines),
    }


def build_campaign_summary(selected: List[Dict[str, Any]], artist: str = "Artist",
                           genre: str = "") -> Dict[str, Any]:
    """Summarize a selected-station campaign: counts by format, contact
    coverage, markets, and a recommended send order."""
    breakdown: Dict[str, int] = {}
    with_contacts = 0
    states = set()
    markets = set()
    for s in selected or []:
        fmt = classify_station(s.get("station_name", "") or s.get("name", ""),
                               s.get("vector", ""), location=s.get("location", ""))
        breakdown[fmt] = breakdown.get(fmt, 0) + 1
        if s.get("submission_email") or s.get("contact"):
            with_contacts += 1
        loc = (s.get("location") or "").strip()
        if loc:
            markets.add(loc)
            tail = loc.rsplit(",", 1)[-1].strip()
            if len(tail) == 2:
                states.add(tail.upper())

    # Recommend leading with the most receptive formats present.
    ordered = sorted(breakdown.items(),
                     key=lambda kv: -FORMAT_BASE_RATE.get(_base_of(kv[0]), 30))
    if ordered:
        lead_fmt, lead_n = ordered[0]
        recommendation = (
            f"Lead with your {lead_n} {lead_fmt.replace('_', ' ')} station(s) — that format "
            f"historically answers independent submissions fastest — then work down the list. "
            f"{with_contacts} of {len(selected or [])} selected stations have a contact on file; "
            f"find contacts for the rest before dispatch or they will be skipped."
        )
    else:
        recommendation = "No stations selected yet — run a radio search and select stations first."

    return {
        "artist": artist,
        "genre": genre,
        "total_stations": len(selected or []),
        "format_breakdown": breakdown,
        "stations_with_contacts": with_contacts,
        "states_covered": sorted(states),
        "markets": sorted(markets),
        "send_order": [fmt for fmt, _ in ordered],
        "recommendation": recommendation,
    }


def generate_follow_up(station_name: str, artist: str, attempt: int = 1,
                       max_attempts: int = 3) -> str:
    """Follow-up email copy that escalates politely across attempts and
    closes the loop on the final attempt. Contains no invented stats —
    it is a send-ready draft the artist can edit."""
    attempt = max(1, int(attempt))
    max_attempts = max(attempt, int(max_attempts))
    if attempt >= max_attempts:
        return (
            f"Hi {station_name} team,\n\n"
            f"Closing the loop on my submission for {artist}. I know your inbox is deep and "
            f"your playlist is tight, so I'll leave it here — the music stays up at our usual "
            f"links whenever it fits a future opening.\n\n"
            f"Thanks for everything you play for independent artists. We'll send the next "
            f"single your way when it's ready.\n\n"
            f"Best,\n{artist}"
        )
    if attempt == 1:
        return (
            f"Hi {station_name} team,\n\n"
            f"Floating my submission for {artist} back to the top of your inbox. The track "
            f"is still the one I sent over — happy to resend the stream/download links or "
            f"service a clean radio edit if that's easier on your end.\n\n"
            f"If there's a better contact for new-music submissions at the station, pointing "
            f"me their way is help enough.\n\n"
            f"Thanks for listening,\n{artist}"
        )
    return (
        f"Hi {station_name} team,\n\n"
        f"Second note on {artist}'s submission. Since the first email we've kept building "
        f"the campaign around this record, and your station is still one of the rooms we "
        f"most want it heard in.\n\n"
        f"If a spin isn't in the cards, a sentence of feedback travels a long way with an "
        f"independent artist — and if it is, we can offer a station ID or a quick interview "
        f"to go with it.\n\n"
        f"Gratefully,\n{artist}"
    )
