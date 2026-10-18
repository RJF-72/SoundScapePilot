import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from . import database as db

GENRE_TAGS = [
    "Gospel", "Contemporary Christian", "Christian Rock", "Christian Hip Hop",
    "Christian R&B", "Worship", "Southern Gospel", "Christian EDM",
    "Christian Pop", "Praise & Worship", "Christian Metal", "Christian Folk",
    "Inspirational", "Christian Latin", "Christian Country",
]

STAGES = ["submission", "review", "development", "signed", "active", "graduated"]

DEVELOPMENT_MILESTONES = [
    "Single Release", "EP Release", "Album Release",
    "Radio Campaign", "Streaming Campaign", "Tour Support",
    "Sync Placement", "Press Kit Complete", "Website Launch",
    "Social Media Growth (10K+)", "Playlist Placement",
    "Featured on Platform Editorial",
]


class LabelIdentityManager:
    def __init__(self):
        self._label_name = "Redemption Road Music Group"
        self._genres = GENRE_TAGS[:]

    def get_brand(self) -> Dict[str, Any]:
        brand = db.get_label_brand()
        if brand:
            return brand
        return {
            "primary_color": "#1a1a2e",
            "secondary_color": "#e94560",
            "accent_color": "#0f3460",
            "font_primary": "Inter",
            "font_secondary": "JetBrains Mono",
            "logo_url": "",
            "tagline": "Where Faith Meets Sound",
            "mission": "Discover, develop, and distribute world-class Christian music.",
            "values": ["Excellence", "Integrity", "Community", "Innovation", "Faith"],
        }

    def update_brand(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        brand = self.get_brand()
        brand.update(updates)
        db.save_label_brand(brand)
        return {"status": "ok", "brand": brand}

    def add_artist(self, name: str, stage: str = "development",
                   genre: str = "", bio: str = "",
                   social_links: dict = None,
                   metadata: dict = None) -> Dict[str, Any]:
        social_links = social_links or {}
        metadata = metadata or {}
        if stage not in STAGES:
            return {"error": f"Invalid stage: {stage}. Must be one of {STAGES}"}

        artist = {
            "id": str(uuid.uuid4())[:12],
            "name": name,
            "stage": stage,
            "genre": genre,
            "bio": bio,
            "social_links": social_links,
            "metadata": metadata,
            "joined": datetime.now().isoformat(),
            "next_release_date": "",
            "milestones_completed": [],
            "current_milestone": "",
            "notes": "",
            "status": "active",
        }
        db.save_label_artist(artist)
        return artist

    def update_artist(self, artist_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        artist = db.get_label_artist(artist_id)
        if not artist:
            return None
        artist.update(updates)
        artist["updated"] = datetime.now().isoformat()
        db.save_label_artist(artist)
        return artist

    def get_roster(self, stage: str = "", genre: str = "",
                    status: str = "") -> List[Dict[str, Any]]:
        results = db.get_label_roster()
        if stage:
            results = [a for a in results if a["stage"] == stage]
        if genre:
            results = [a for a in results if a["genre"].lower() == genre.lower()]
        if status:
            results = [a for a in results if a["status"] == status]
        return results

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return db.get_label_artist(artist_id)

    def complete_milestone(self, artist_id: str, milestone: str) -> bool:
        artist = db.get_label_artist(artist_id)
        if not artist:
            return False
        if milestone not in artist["milestones_completed"]:
            artist["milestones_completed"].append(milestone)
            completed = artist["milestones_completed"]
            if len(completed) >= 1 and artist["stage"] == "development":
                artist["stage"] = "active"
            if len(completed) >= 3 and artist["stage"] == "active":
                artist["stage"] = "graduated"
            db.save_label_artist(artist)
        return True

    def submit_artist(self, artist_name: str, email: str, genre: str,
                       social_link: str, message: str = "",
                       spotify_link: str = "", youtube_link: str = "") -> Dict[str, Any]:
        submission = {
            "id": str(uuid.uuid4())[:12],
            "artist_name": artist_name,
            "email": email,
            "genre": genre,
            "social_link": social_link,
            "spotify_link": spotify_link,
            "youtube_link": youtube_link,
            "message": message,
            "status": "new",
            "submitted": datetime.now().isoformat(),
            "reviewed_by": "",
            "review_notes": "",
            "decision": "",
        }
        db.save_label_submission(submission)
        return submission

    def review_submission(self, submission_id: str, reviewer: str,
                            decision: str, notes: str = "") -> Optional[Dict[str, Any]]:
        submissions = db.get_label_submissions()
        submission = next((s for s in submissions if s["id"] == submission_id), None)
        if not submission or decision not in ["approved", "rejected", "hold"]:
            return None
        submission["status"] = decision
        submission["reviewed_by"] = reviewer
        submission["review_notes"] = notes
        submission["decision"] = decision
        submission["reviewed_at"] = datetime.now().isoformat()
        db.save_label_submission(submission)

        if decision == "approved":
            self.add_artist(
                name=submission["artist_name"],
                stage="submission",
                genre=submission["genre"],
                bio=f"Sourced from submission on {submission['submitted']}",
            )

        return submission

    def get_submissions(self, status: str = "") -> List[Dict[str, Any]]:
        results = db.get_label_submissions()
        if status:
            results = [s for s in results if s["status"] == status]
        return sorted(results, key=lambda x: x.get("submitted", ""), reverse=True)

    def add_release_calendar(self, title: str, artist: str, release_type: str,
                              release_date: str, upc: str = "",
                              genre: str = "") -> Dict[str, Any]:
        event = {
            "id": str(uuid.uuid4())[:12],
            "title": title,
            "artist": artist,
            "release_type": release_type,
            "release_date": release_date,
            "upc": upc,
            "genre": genre,
            "milestones": [
                {
                    "date": release_date,
                    "task": "Release Day",
                    "completed": False,
                }
            ],
            "created": datetime.now().isoformat(),
        }
        db.save_label_calendar(event)
        return event

    def get_release_calendar(self, artist: str = "", month: str = "") -> List[Dict[str, Any]]:
        results = db.get_label_calendar()
        if artist:
            results = [r for r in results if r.get("artist", "").lower() == artist.lower()]
        if month:
            results = [r for r in results if r.get("release_date", "").startswith(month)]
        return sorted(results, key=lambda x: x.get("release_date", ""))

    def get_summary(self) -> Dict[str, Any]:
        roster = db.get_label_roster()
        submissions = db.get_label_submissions()
        calendar = db.get_label_calendar()
        today = datetime.now().strftime("%Y-%m-%d")
        return {
            "label_name": self._label_name,
            "total_artists": len(roster),
            "submissions_pending": sum(1 for s in submissions if s.get("status") == "new"),
            "artists_by_stage": {s: sum(1 for a in roster if a.get("stage") == s) for s in STAGES},
            "upcoming_releases": len([r for r in calendar if r.get("release_date", "") >= today]),
            "total_submissions": len(submissions),
        }

    def get_development_roadmap(self, artist_id: str) -> Optional[Dict[str, Any]]:
        artist = db.get_label_artist(artist_id)
        if not artist:
            return None
        remaining = [m for m in DEVELOPMENT_MILESTONES if m not in artist.get("milestones_completed", [])]
        return {
            "artist": artist["name"],
            "current_stage": artist.get("stage", "development"),
            "milestones_completed": artist.get("milestones_completed", []),
            "next_milestone": remaining[0] if remaining else None,
            "remaining_milestones": remaining,
            "next_stage": self._get_next_stage(artist.get("stage", "development")),
        }

    def _get_next_stage(self, current: str) -> str:
        idx = STAGES.index(current) if current in STAGES else 0
        return STAGES[idx + 1] if idx + 1 < len(STAGES) else "graduated"
