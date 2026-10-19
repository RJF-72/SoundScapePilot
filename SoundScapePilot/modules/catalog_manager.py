import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from . import database as db


class CatalogManager:
    def __init__(self):
        pass

    def add_release(self, title: str, artist: str, upc: str = "",
                     isrc: str = "", genre: str = "", release_date: str = "",
                     label: str = "Redemption Road Music Group",
                     catalog_number: str = "") -> Dict[str, Any]:
        existing = db.get_catalog_releases()
        release_id = str(uuid.uuid4())[:12]
        release = {
            "id": release_id,
            "title": title,
            "artist": artist,
            "upc": upc or self._generate_upc(),
            "isrc": isrc,
            "genre": genre,
            "release_date": release_date or datetime.now().strftime("%Y-%m-%d"),
            "label": label,
            "catalog_number": catalog_number or f"RRM-{datetime.now().strftime('%y')}-{len(existing)+1:04d}",
            "tracks": [],
            "artwork_url": "",
            "lyrics": "",
            "credits": "",
            "status": "draft",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "version_history": [],
        }
        db.save_catalog_release(release)
        return release

    def _generate_upc(self) -> str:
        prefix = "008428"
        unique = str(uuid.uuid4().int)[:5]
        return f"{prefix}{unique}"

    def add_track(self, release_id: str, title: str, isrc: str = "",
                   artists: list = None, writers: list = None,
                   producers: list = None, duration_sec: int = 0,
                   genre: str = "", is_single: bool = False) -> Optional[Dict[str, Any]]:
        release = db.get_catalog_release(release_id)
        if not release:
            return None
        track = {
            "id": str(uuid.uuid4())[:12],
            "title": title,
            "isrc": isrc or f"USRRM{datetime.now().strftime('%y')}{str(uuid.uuid4().int)[:5]}",
            "artists": artists or [release["artist"]],
            "writers": writers or [],
            "producers": producers or [],
            "duration_sec": duration_sec,
            "genre": genre or release["genre"],
            "is_single": is_single,
            "stems": [],
            "masters": [],
            "metadata": {"bpm": 0, "key": "", "mood_tags": [], "lyrical_themes": []},
        }
        release["tracks"].append(track)
        release["updated"] = datetime.now().isoformat()
        db.save_catalog_release(release)
        return track

    def update_track_metadata(self, release_id: str, track_id: str,
                               metadata: Dict[str, Any]) -> bool:
        release = db.get_catalog_release(release_id)
        if not release:
            return False
        for track in release["tracks"]:
            if track["id"] == track_id:
                track["metadata"].update(metadata)
                release["updated"] = datetime.now().isoformat()
                release["version_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "metadata_update",
                    "track": track["title"],
                })
                db.save_catalog_release(release)
                return True
        return False

    def get_catalog(self, artist: str = "", genre: str = "",
                     status: str = "") -> List[Dict[str, Any]]:
        results = db.get_catalog_releases()
        if artist:
            results = [r for r in results if r["artist"].lower() == artist.lower()]
        if genre:
            results = [r for r in results if r["genre"].lower() == genre.lower()]
        if status:
            results = [r for r in results if r["status"].lower() == status.lower()]
        return results

    def get_release(self, release_id: str) -> Optional[Dict[str, Any]]:
        return db.get_catalog_release(release_id)

    def search_by_isrc(self, isrc: str) -> Optional[Dict[str, Any]]:
        for release in db.get_catalog_releases():
            for track in release["tracks"]:
                if track["isrc"] == isrc:
                    return {**release, "matched_track": track}
        return None

    def search_by_upc(self, upc: str) -> Optional[Dict[str, Any]]:
        for release in db.get_catalog_releases():
            if release["upc"] == upc:
                return release
        return None

    def get_catalog_summary(self) -> Dict[str, Any]:
        releases = db.get_catalog_releases()
        total_tracks = sum(len(r["tracks"]) for r in releases)
        singles = sum(1 for r in releases for t in r["tracks"] if t.get("is_single"))
        return {
            "total_releases": len(releases),
            "total_tracks": total_tracks,
            "singles": singles,
            "albums": max(0, len(releases) - singles),
            "artists": len(set(r["artist"] for r in releases)),
        }

    def add_stem(self, release_id: str, track_id: str, stem_type: str,
                  file_url: str, format: str = "wav") -> bool:
        release = db.get_catalog_release(release_id)
        if not release:
            return False
        for track in release["tracks"]:
            if track["id"] == track_id:
                track["stems"].append({
                    "id": str(uuid.uuid4())[:12],
                    "type": stem_type,
                    "file_url": file_url,
                    "format": format,
                    "added": datetime.now().isoformat(),
                })
                db.save_catalog_release(release)
                return True
        return False

    def add_master(self, release_id: str, track_id: str, format: str,
                    file_url: str, sample_rate: str = "44.1kHz",
                    bit_depth: str = "24bit") -> bool:
        release = db.get_catalog_release(release_id)
        if not release:
            return False
        for track in release["tracks"]:
            if track["id"] == track_id:
                track["masters"].append({
                    "id": str(uuid.uuid4())[:12],
                    "format": format,
                    "file_url": file_url,
                    "sample_rate": sample_rate,
                    "bit_depth": bit_depth,
                    "added": datetime.now().isoformat(),
                })
                db.save_catalog_release(release)
                return True
        return False
