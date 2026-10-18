import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from . import database as db

PLATFORMS = {
    "distrokid": {
        "name": "DistroKid",
        "description": "Best for independent artists. $22.99/year unlimited uploads. Fastest delivery (24-48hrs). Keeps 0% royalty.",
        "pricing": "Subscription: $22.99-$89.99/year",
        "royalty_share": "Artist keeps 100%",
        "features": ["Unlimited uploads", "Spotify pre-save", "YouTube Content ID", "TikTok integration", "Shazam"],
        "pros": ["Fast delivery", "Low cost", "Instant splits"],
        "cons": ["No free tier", "No distribution to Facebook/Instagram directly"],
    },
    "cdbaby": {
        "name": "CD Baby",
        "description": "Pro distributor with sync licensing. One-time fee per release. Strong sync licensing team.",
        "pricing": "Single: $9.99, Album: $29.99, Pro: $39.99 (includes YouTube Content ID)",
        "royalty_share": "Artist keeps 90% (Pro: 85%)",
        "features": ["Sync licensing", "Physical distribution", "CD Baby Pro", "Publishing administration"],
        "pros": ["Sync licensing team", "Physical retail", "Publishing admin"],
        "cons": ["Slower delivery (3-5 days)", "Higher fees for pro features"],
    },
    "tunecore": {
        "name": "TuneCore",
        "description": "Industry standard. Annual fee per release. Social media monetization included.",
        "pricing": "Single: $14.99/year, Album: $49.99/year",
        "royalty_share": "Artist keeps 100%",
        "features": ["Social Media monetization", "Publishing administration ($75/year)", "Sync licensing"],
        "pros": ["Transparent accounting", "Social media monetization", "Publishing admin available"],
        "cons": ["Annual fees per release", "Cost adds up with large catalog"],
    },
    "symphonic": {
        "name": "Symphonic Distribution",
        "description": "Full-service distributor for labels. 15% commission. Label services including marketing.",
        "pricing": "15% commission or $50/release (label plans available)",
        "royalty_share": "Artist keeps 85% (or 100% with fee-based plan)",
        "features": ["Label services", "Marketing support", "Playlist pitching", "Data analytics"],
        "pros": ["Label-friendly", "Marketing included", "Great analytics"],
        "cons": ["Requires minimum release volume", "More expensive for small artists"],
    },
    "vydia": {
        "name": "Vydia",
        "description": "Technology-first distributor. Used by major labels for backend infrastructure. Best for catalog management.",
        "pricing": "Custom pricing for labels",
        "royalty_share": "Negotiable (typically 80-95% artist)",
        "features": ["Catalog management API", "Royalty accounting", "Rights management", "Analytics dashboard"],
        "pros": ["Enterprise infrastructure", "Full API access", "White-label options"],
        "cons": ["Enterprise-only pricing", "Minimum volume requirements"],
    },
    "united_masters": {
        "name": "UnitedMasters",
        "description": "Artist-first distributor. Has partnerships with Apple Music and Spotify. Selective — curates artists.",
        "pricing": "Free (Starter), $49.99/year (Select)",
        "royalty_share": "Artist keeps 90% (Starter) or 100% (Select)",
        "features": ["Brand partnerships", "Data analytics", "Playlist pitching", "Select program"],
        "pros": ["Brand partnership opportunities", "No fees on Starter plan"],
        "cons": ["Selective curation", "Limited features on free plan"],
    },
}

RECOMMENDED_PLATFORMS_BY_GOAL = {
    "speed": "distrokid",
    "sync_licensing": "cdbaby",
    "publishing_admin": "tunecore",
    "label_services": "symphonic",
    "enterprise": "vydia",
    "brand_partnerships": "united_masters",
    "low_cost": "distrokid",
}


class DistributionPipeline:
    def __init__(self):
        pass

    def get_platforms(self, goal: str = "") -> List[Dict[str, Any]]:
        if goal:
            key = RECOMMENDED_PLATFORMS_BY_GOAL.get(goal.lower())
            if key and key in PLATFORMS:
                return [{**PLATFORMS[key], "key": key}]
        return [{**v, "key": k} for k, v in PLATFORMS.items()]

    def prepare_metadata(self, title: str, artist: str, isrc: str, upc: str,
                          genre: str, release_date: str, label: str,
                          tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "release_title": title,
            "artist_name": artist,
            "label_name": label or "Redemption Road Music Group",
            "upc": upc,
            "primary_genre": genre,
            "release_date": release_date,
            "tracks": [
                {
                    "track_title": t.get("title", ""),
                    "isrc": t.get("isrc", ""),
                    "artists": t.get("artists", [artist]),
                    "writers": t.get("writers", []),
                    "producers": t.get("producers", []),
                    "duration_sec": t.get("duration_sec", 0),
                    "explicit": t.get("explicit", False),
                    "genre": t.get("genre", genre),
                }
                for t in tracks
            ],
            "metadata_complete": True,
            "missing_fields": [],
        }

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        required = ["release_title", "artist_name", "upc", "primary_genre",
                     "release_date", "tracks"]
        missing = [f for f in required if not metadata.get(f)]
        track_issues = []
        for i, t in enumerate(metadata.get("tracks", [])):
            if not t.get("isrc"):
                track_issues.append(f"Track {i+1} ({t.get('title', 'Untitled')}): missing ISRC")
            if not t.get("duration_sec"):
                track_issues.append(f"Track {i+1}: missing duration")
        return {
            "valid": len(missing) == 0 and len(track_issues) == 0,
            "missing_fields": missing,
            "track_issues": track_issues,
            "metadata": metadata,
        }

    def create_delivery(self, platform: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        delivery_id = str(uuid.uuid4())[:12]
        delivery = {
            "id": delivery_id,
            "platform": platform,
            "platform_name": PLATFORMS.get(platform, {}).get("name", platform),
            "status": "preparing",
            "metadata": metadata,
            "created": datetime.now().isoformat(),
            "estimated_delivery": "",
            "errors": [],
        }

        # Validate
        validation = self.validate_metadata(metadata)
        if not validation["valid"]:
            delivery["status"] = "validation_failed"
            delivery["errors"] = validation["missing_fields"] + validation["track_issues"]
        else:
            delivery["status"] = "ready"
            # Estimated delivery time per platform
            eta_map = {
                "distrokid": "24-48 hours",
                "cdbaby": "3-5 business days",
                "tunecore": "3-5 business days",
                "symphonic": "5-7 business days",
                "vydia": "2-3 business days",
                "united_masters": "2-4 weeks (curation review)",
            }
            delivery["estimated_delivery"] = eta_map.get(platform, "3-5 business days")

        db.save_distro_delivery(delivery)
        return delivery

    def get_delivery(self, delivery_id: str) -> Optional[Dict[str, Any]]:
        return db.get_distro_delivery(delivery_id)

    def get_all_deliveries(self) -> List[Dict[str, Any]]:
        return db.get_distro_deliveries()

    def generate_delivery_report(self) -> Dict[str, Any]:
        all_d = db.get_distro_deliveries()
        return {
            "total": len(all_d),
            "preparing": sum(1 for d in all_d if d["status"] == "preparing"),
            "ready": sum(1 for d in all_d if d["status"] == "ready"),
            "delivered": sum(1 for d in all_d if d["status"] == "delivered"),
            "failed": sum(1 for d in all_d if d["status"] == "validation_failed"),
            "by_platform": {p: sum(1 for d in all_d if d["platform"] == p) for p in set(d["platform"] for d in all_d)},
        }
