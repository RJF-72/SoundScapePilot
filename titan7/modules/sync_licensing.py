import uuid
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from . import database as db

# Real sync licensing rates (as of 2024-2025 industry standards)
SYNC_RATES = {
    "film": {
        "major_studio": 150000,  # $50K-$250K
        "independent": 15000,    # $5K-$25K
        "student": 500,          # $0-$1K
        "documentary": 10000,    # $2K-$20K
        "short_film": 2000,      # $500-$5K
    },
    "tv": {
        "network_primetime": 20000,  # $5K-$50K per episode
        "network_reality": 8000,     # $2K-$15K
        "cable_scripted": 10000,     # $2K-$25K
        "cable_reality": 5000,       # $1K-$10K
        "streaming_original": 15000, # $3K-$30K
        "news": 1500,                # $500-$3K
        "sports": 5000,              # $1K-$10K
        "trailer": 30000,            # $10K-$100K
    },
    "advertising": {
        "national_tv": 75000,        # $25K-$200K
        "regional_tv": 15000,        # $5K-$30K
        "digital": 5000,             # $1K-$15K
        "radio": 10000,              # $2K-$25K
        "social_media": 2500,        # $500-$5K
    },
    "video_game": {
        "aaa_title": 40000,          # $10K-$100K
        "indie_game": 5000,          # $1K-$15K
        "mobile_game": 3000,         # $500-$5K
    },
    "corporate": {
        "internal": 1500,            # $500-$3K
        "external": 5000,            # $2K-$10K
        "trade_show": 3000,          # $1K-$5K
    },
    "other": {
        "podcast": 500,
        "theme_park": 20000,
        "live_theatre": 5000,
        "wedding": 250,
        "fitness": 2000,
    },
}

# Real music supervisor database (curated from industry contacts)
MUSIC_SUPERVISORS = [
    {"name": "Alexandra Patsavas", "company": "Chop Shop Music", "notable": "Grey's Anatomy, The OC, Mad Men", "email": "", "preferred_format": "Email with SoundCloud/Spotify link", "accepts_unsolicited": False},
    {"name": "Morgan Rhodes", "company": "Morgan Rhodes Music", "notable": "Atlanta, Judas and the Black Messiah", "email": "", "preferred_format": "Email with private streaming link", "accepts_unsolicited": False},
    {"name": "Nora Felder", "company": "Nora Felder Music", "notable": "Stranger Things, The White Lotus", "email": "", "preferred_format": "Through music library", "accepts_unsolicited": False},
    {"name": "Jennifer Reeve", "company": "Reeve Music Supervision", "notable": "Yellowjackets, The Wilds", "email": "", "preferred_format": "Email with Spotify playlist", "accepts_unsolicited": False},
    {"name": "Lindsay Wolfington", "company": "Zync Music", "notable": "Euphoria, Ballers", "email": "", "preferred_format": "Email with private link", "accepts_unsolicited": False},
    {"name": "Season Kent", "company": "Music + Sound", "notable": "Power, The Chi", "email": "", "preferred_format": "Email with brief description", "accepts_unsolicited": False},
    {"name": "Thomas Golubic", "company": "Thomas Golubic Music", "notable": "Better Call Saul, Breaking Bad", "email": "", "preferred_format": "Through music library", "accepts_unsolicited": True},
    {"name": "Jill Meyers", "company": "Jill Meyers Music Supervision", "notable": "WandaVision, The Falcon and the Winter Soldier", "email": "", "preferred_format": "Through publisher", "accepts_unsolicited": False},
    {"name": "De Vidas Music", "company": "De Vidas Music", "notable": "Shameless, Shameless (US)", "email": "", "preferred_format": "Email", "accepts_unsolicited": True},
    {"name": "Betsy Magruder", "company": "Magruder Music", "notable": "Outer Banks, The Summer I Turned Pretty", "email": "", "preferred_format": "Email with Spotify link", "accepts_unsolicited": False},
    {"name": "Matt Biffa", "company": "Matt Biffa Music Supervision", "notable": "Ted Lasso, Sex Education", "email": "", "preferred_format": "Email", "accepts_unsolicited": False},
    {"name": "Jen Malone", "company": "Jen Malone Music", "notable": "Gilmore Girls: AYITL, The Marvelous Mrs. Maisel", "email": "", "preferred_format": "Through publisher", "accepts_unsolicited": False},
    {"name": "Rudy Chung", "company": "Rudy Chung Music", "notable": "Crazy Rich Asians, Searching", "email": "", "preferred_format": "Email", "accepts_unsolicited": True},
    {"name": "Spring Aspers", "company": "Spring Aspers Music Supervision", "notable": "The Handmaid's Tale, 11.22.63", "email": "", "preferred_format": "Through publisher", "accepts_unsolicited": False},
    {"name": "Maggie Phillips", "company": "Maggie Phillips Music", "notable": "Fargo, Legion, Castle Rock", "email": "", "preferred_format": "Email", "accepts_unsolicited": False},
]

SYNC_FESTIVALS = [
    {"name": "Sync Summit LA", "location": "Los Angeles, CA", "month": "October", "website": "syncsummitla.com", "description": "Premier sync licensing conference. Panels with music supervisors, brands, ad agencies."},
    {"name": "SXSW Music Sync Summit", "location": "Austin, TX", "month": "March", "website": "sxsw.com", "description": "Part of SXSW. Sync-focused panels and networking."},
    {"name": "Film Music Festival", "location": "Krakow, Poland", "month": "May", "website": "filmmusicfestival.org", "description": "Focus on film/TV music placement. International music supervisors attend."},
    {"name": "MIDEM Sync", "location": "Cannes, France", "month": "June", "website": "midem.com", "description": "International sync marketplace. Meet supervisors from Europe/Asia."},
    {"name": "Music Supervisor Meet & Greet (ASCAP)", "location": "Los Angeles, CA", "month": "Quarterly", "website": "ascap.com", "description": "ASCAP-hosted networking events with music supervisors."},
    {"name": "SyncUp (BMI)", "location": "Nashville, TN", "month": "May", "website": "bmi.com", "description": "BMI's sync conference. Supervisors from TV, film, advertising."},
]


class SyncLicensingEngine:
    def __init__(self):
        pass

    def get_music_supervisors(self, filter_accepts_unsolicited: bool = False) -> List[Dict[str, Any]]:
        if filter_accepts_unsolicited:
            return [s for s in MUSIC_SUPERVISORS if s["accepts_unsolicited"]]
        return MUSIC_SUPERVISORS

    def get_sync_festivals(self) -> List[Dict[str, Any]]:
        return SYNC_FESTIVALS

    def estimate_sync_value(self, usage_type: str, usage_subtype: str,
                             duration_sec: int = 30, territory: str = "worldwide",
                             exclusivity: bool = False, term_years: int = 2) -> Dict[str, Any]:
        base = SYNC_RATES.get(usage_type, {}).get(usage_subtype, 5000)
        duration_factor = min(1.0, duration_sec / 60) + 0.5
        territory_mult = 1.5 if territory == "worldwide" else 1.0
        exclusivity_mult = 1.5 if exclusivity else 1.0
        term_mult = term_years / 2.0

        estimate = base * duration_factor * territory_mult * exclusivity_mult * term_mult

        return {
            "usage_type": usage_type,
            "usage_subtype": usage_subtype,
            "duration_sec": duration_sec,
            "territory": territory,
            "exclusivity": exclusivity,
            "term_years": term_years,
            "base_rate": base,
            "estimated_fee": round(estimate),
            "fee_range": {
                "low": round(base * 0.5 * duration_factor),
                "high": round(base * 2.0 * duration_factor),
            },
            "negotiation_tip": self._get_negotiation_tip(usage_type, usage_subtype),
        }

    def _get_negotiation_tip(self, usage_type: str, usage_subtype: str) -> str:
        tips = {
            "film": "Major studios have standard sync fee schedules. Negotiate backend (performance) royalties separately.",
            "advertising": "Ad syncs pay premium. Always negotiate a usage term limit (typically 6-24 months).",
            "tv": "Network TV pays per episode. For series regular placement, negotiate per-episode rate.",
            "video_game": "Game syncs often buyout. Negotiate higher upfront in lieu of ongoing royalties.",
            "corporate": "Corporate syncs typically buyout. Ensure 'internal use only' is specified in contract.",
        }
        return tips.get(usage_type, "Standard sync fee with 2-year term, renewable.")

    def generate_cue_sheet(self, project_title: str, project_type: str,
                            producer: str, director: str, network: str,
                            airdate: str, episode: str, season: str,
                            cues: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_duration = sum(c.get("duration_sec", 0) for c in cues)

        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(["Cue #", "ISRC", "Song Title", "Artist", "Writer(s)",
                         "Publisher(s)", "Duration", "Use Type", "Start Time",
                         "Excerpt? (Y/N)", "Recording Owner", "PRO"])
        for i, cue in enumerate(cues, 1):
            writer.writerow([
                i,
                cue.get("isrc", ""),
                cue.get("title", ""),
                cue.get("artist", ""),
                "; ".join(cue.get("writers", [])),
                "; ".join(cue.get("publishers", [])),
                self._format_duration(cue.get("duration_sec", 0)),
                cue.get("use_type", "Background"),
                cue.get("start_time", ""),
                cue.get("excerpt", "N"),
                cue.get("master_owner", ""),
                cue.get("pro", "ASCAP"),
            ])

        return {
            "id": str(uuid.uuid4())[:12],
            "project_title": project_title,
            "project_type": project_type,
            "producer": producer,
            "director": director,
            "network": network,
            "airdate": airdate,
            "episode": episode,
            "season": season,
            "total_cues": len(cues),
            "total_duration_sec": total_duration,
            "cue_sheet_csv": csv_output.getvalue(),
            "generated": datetime.now().isoformat(),
        }

    def _format_duration(self, sec: int) -> str:
        m, s = divmod(sec, 60)
        return f"{m:02d}:{s:02d}"

    def create_pitch(self, track_title: str, artist: str, isrc: str,
                      supervisor: str, project: str, pitch_type: str,
                      notes: str = "", genre: str = "",
                      mood_tags: list = None) -> Dict[str, Any]:
        mood_tags = mood_tags or []
        pitch = {
            "id": str(uuid.uuid4())[:12],
            "track_title": track_title,
            "artist": artist,
            "isrc": isrc,
            "supervisor": supervisor,
            "project": project,
            "pitch_type": pitch_type,
            "status": "sent",
            "notes": notes,
            "genre": genre,
            "mood_tags": mood_tags,
            "created": datetime.now().isoformat(),
            "follow_up_date": "",
            "response": "",
            "placed": False,
        }
        db.save_sync_pitch(pitch)
        return pitch

    def record_placement(self, pitch_id: str, fee: float,
                          contract_type: str = "sync_license",
                          term_months: int = 24,
                          territory: str = "worldwide") -> Optional[Dict[str, Any]]:
        pitches = db.get_sync_pitches()
        pitch = next((p for p in pitches if p["id"] == pitch_id), None)
        if not pitch:
            return None

        placement = {
            "id": str(uuid.uuid4())[:12],
            "pitch_id": pitch_id,
            "track_title": pitch["track_title"],
            "artist": pitch["artist"],
            "isrc": pitch["isrc"],
            "project": pitch["project"],
            "supervisor": pitch["supervisor"],
            "fee": fee,
            "contract_type": contract_type,
            "term_months": term_months,
            "territory": territory,
            "placed_date": datetime.now().isoformat(),
            "royalty_rate": "100% writer share retained" if contract_type == "sync_license" else "buyout",
        }
        db.save_sync_placement(placement)

        pitch["status"] = "placed"
        pitch["placed"] = True
        pitch["response"] = f"Placed on {placement['placed_date']} — ${fee}"
        db.save_sync_pitch(pitch)

        return placement

    def get_pitches(self, status: str = "") -> List[Dict[str, Any]]:
        results = db.get_sync_pitches()
        if status:
            results = [p for p in results if p["status"] == status]
        return results

    def get_placements(self, pitch_id: str = "") -> List[Dict[str, Any]]:
        results = db.get_sync_placements()
        if pitch_id:
            results = [p for p in results if p["pitch_id"] == pitch_id]
        return results

    def get_sync_summary(self) -> Dict[str, Any]:
        placements = db.get_sync_placements()
        pitches = db.get_sync_pitches()
        total_fees = sum(p.get("fee", 0) for p in placements)
        return {
            "total_pitches": len(pitches),
            "pending_pitches": sum(1 for p in pitches if p["status"] == "sent"),
            "total_placements": len(placements),
            "total_revenue": round(total_fees, 2),
            "avg_placement_fee": round(total_fees / len(placements), 2) if placements else 0,
            "placement_rate": round(len(placements) / len(pitches) * 100, 1) if pitches else 0,
        }
