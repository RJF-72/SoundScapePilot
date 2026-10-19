import json
import uuid
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from . import database as db

# US mechanical royalty rate (2024): 12.4¢ per song per copy
MECHANICAL_RATE = 0.124
# Performance royalty estimate: ~$0.004 per stream (varies by platform)
STREAM_ROYALTY_RATES = {
    "spotify": 0.0035,
    "apple_music": 0.0065,
    "youtube_music": 0.0020,
    "amazon_music": 0.0050,
    "deezer": 0.0050,
    "tidal": 0.0100,
    "pandora": 0.0015,
    "soundcloud": 0.0025,
    "iheartradio": 0.0018,
}
# Neighboring rights: ~25% of performance royalties
NEIGHBORING_RIGHTS_FACTOR = 0.25


class RightsManager:
    def __init__(self):
        pass

    def register_song(self, isrc: str = "", title: str = "", artists: list = None,
                       writers: list = None, producers: list = None,
                       publishers: list = None, upc: str = "",
                       release_date: str = "", genre: str = "",
                       duration_sec: int = 0) -> Dict[str, Any]:
        artists = artists or []
        writers = writers or []
        producers = producers or []
        publishers = publishers or []

        song = {
            "id": str(uuid.uuid4())[:12],
            "isrc": isrc or self._generate_isrc(),
            "upc": upc or "",
            "title": title,
            "artists": artists,
            "writers": writers,
            "producers": producers,
            "publishers": publishers,
            "release_date": release_date or datetime.now().strftime("%Y-%m-%d"),
            "genre": genre,
            "duration_sec": duration_sec,
            "registered": datetime.now().isoformat(),
            "streams": {},
            "sales": 0,
            "sync_income": 0.0,
        }
        db.save_royalty_song(song)
        return song

    def _generate_isrc(self) -> str:
        country = "US"
        registrant = "RRM"  # Redemption Road Music
        year = datetime.now().strftime("%y")
        code = str(uuid.uuid4().int)[:5]
        return f"{country}{registrant}{year}{code}"

    def calculate_mechanical(self, copies: int, songs_per_copy: int = 1) -> Dict[str, Any]:
        total = copies * songs_per_copy * MECHANICAL_RATE
        return {
            "copies": copies,
            "songs_per_copy": songs_per_copy,
            "rate_per_song": MECHANICAL_RATE,
            "total_mechanical": round(total, 2),
        }

    def calculate_performance(self, platform: str, streams: int) -> Dict[str, Any]:
        rate = STREAM_ROYALTY_RATES.get(platform, 0.003)
        gross = streams * rate
        neighboring = gross * NEIGHBORING_RIGHTS_FACTOR
        return {
            "platform": platform,
            "streams": streams,
            "rate": rate,
            "gross_performance": round(gross, 2),
            "neighboring_rights": round(neighboring, 2),
            "total": round(gross + neighboring, 2),
        }

    def calculate_song_royalties(self, isrc: str, streams_by_platform: Dict[str, int] = None,
                                  digital_sales: int = 0, physical_sales: int = 0) -> Dict[str, Any]:
        streams_by_platform = streams_by_platform or {}
        total = 0.0
        breakdown = []

        for platform, count in streams_by_platform.items():
            result = self.calculate_performance(platform, count)
            breakdown.append(result)
            total += result["total"]

        mech = self.calculate_mechanical(digital_sales + physical_sales)
        total += mech["total_mechanical"]
        breakdown.append(mech)

        return {
            "isrc": isrc,
            "total_royalties": round(total, 2),
            "breakdown": breakdown,
        }

    def generate_artist_statement(self, artist: str, songs: List[Dict[str, Any]],
                                   splits: Dict[str, float] = None) -> Dict[str, Any]:
        splits = splits or {"artist": 0.6, "producer": 0.2, "publisher": 0.1, "label": 0.1}
        total_earned = sum(s.get("total_royalties", 0) for s in songs)
        statement = {
            "artist": artist,
            "period": "Q" + str((datetime.now().month - 1) // 3 + 1),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_earned": round(total_earned, 2),
            "splits": {},
        }
        for role, pct in splits.items():
            statement["splits"][role] = {
                "percentage": pct * 100,
                "amount": round(total_earned * pct, 2),
            }
        return statement


class RoyaltySplitEngine:
    def __init__(self):
        pass

    def create_split_agreement(self, title: str, isrc: str, parties: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = sum(p.get("split", 0) for p in parties)
        if abs(total - 100) > 0.01:
            return {"error": f"Splits total {total}%, must equal 100%"}

        agreement = {
            "id": str(uuid.uuid4())[:12],
            "title": title,
            "isrc": isrc,
            "parties": parties,
            "created": datetime.now().isoformat(),
        }
        db.save_royalty_split_agreement(agreement)
        return agreement

    def _load_agreement(self, agreement_id: str) -> Optional[Dict[str, Any]]:
        for a in db.get_royalty_split_agreements():
            if a["id"] == agreement_id:
                return a
        return None

    def calculate_net_royalties(self, agreement_id: str, gross_revenue: float) -> Dict[str, Any]:
        agreement = self._load_agreement(agreement_id)
        if not agreement:
            return {"error": "Agreement not found"}
        breakdown = {}
        for party in agreement["parties"]:
            name = party.get("name", "Unknown")
            role = party.get("role", "artist")
            split = party.get("split", 0) / 100.0
            breakdown[name] = {
                "role": role,
                "split_pct": party["split"],
                "net": round(gross_revenue * split, 2),
            }
        return {
            "agreement_id": agreement_id,
            "gross_revenue": gross_revenue,
            "breakdown": breakdown,
            "total_paid": round(sum(b["net"] for b in breakdown.values()), 2),
        }
