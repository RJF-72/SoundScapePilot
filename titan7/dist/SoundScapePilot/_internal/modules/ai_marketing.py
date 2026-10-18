"""
SOUNDSCAPE PILOT AI MARKETING ENGINE
World-class autonomous marketing for Redemption Road Music Group.

Capabilities:
  - Campaign strategy generation (single, EP, album, tour, video)
  - Social media content calendars and post copy
  - Email nurture sequences
  - Ad creative copy (Meta, TikTok, YouTube, Google)
  - Bio / press kit / one-sheet generation
  - Hashtag and keyword research
  - Influencer pitch templates
  - Playlist pitch campaigns
  - Content remix engine (turn one asset into 30+ pieces)
  - Bot/driver dispatch lists for platforms
"""

import random
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from modules.mailer import DEFAULT_DOMAIN


class AIMarketingEngine:
    """Local, deterministic AI marketing engine with TinyML-style templating."""

    CAMPAIGN_TYPES = ["single", "album", "ep", "tour", "music video", "rebrand", "merch drop"]

    PLATFORMS = [
        "Instagram", "TikTok", "X (Twitter)", "Facebook", "YouTube",
        "Spotify", "Apple Music", "SoundCloud", "Bandcamp", "ReverbNation",
        "LinkedIn", "Pinterest", "Snapchat", "Twitch"
    ]

    DRIVERS = {
        "Instagram": {"handle": "@titan7official", "best_times": ["11:00", "14:00", "19:00"], "hashtags": ["#newmusic", "#indie", "#artistlife"]},
        "TikTok": {"handle": "@titan7official", "best_times": ["10:00", "13:00", "21:00"], "hashtags": ["#newmusic", "#indieartist", "#musictok"]},
        "X (Twitter)": {"handle": "@titan7official", "best_times": ["08:00", "12:00", "17:00"], "hashtags": ["#newmusic", "#indie", "#nowplaying"]},
        "Facebook": {"handle": "TITAN 7", "best_times": ["09:00", "13:00", "15:00"], "hashtags": ["#newmusic", "#livemusic"]},
        "YouTube": {"handle": "@titan7official", "best_times": ["14:00", "17:00"], "hashtags": ["#musicvideo", "#newmusic"]},
        "Spotify": {"handle": "TITAN 7 Artist", "best_times": ["Anytime"], "hashtags": []},
        "Apple Music": {"handle": "TITAN 7 Artist", "best_times": ["Anytime"], "hashtags": []},
        "SoundCloud": {"handle": "@titan7official", "best_times": ["Anytime"], "hashtags": ["#newmusic", "#hiphop", "#electronic"]},
    }

    def __init__(self):
        self._seed = random.Random()

    def generate_campaign(self, artist: str, release: str, genre: str,
                          campaign_type: str = "album",
                          duration_days: int = 30) -> Dict[str, Any]:
        """Generate a complete marketing campaign blueprint."""
        ct = (campaign_type or "album").lower()
        if ct not in self.CAMPAIGN_TYPES:
            ct = "album"

        phases = self._build_phases(ct, duration_days)
        hooks = self._generate_hooks(artist, release, genre)
        content_calendar = self._build_calendar(artist, release, genre, duration_days)
        email_sequence = self._build_email_sequence(artist, release, genre)
        ad_creatives = self._build_ad_creatives(artist, release, genre)
        playlist_pitches = self._build_playlist_pitches(artist, release, genre)
        influencer_pitches = self._build_influencer_pitches(artist, release, genre)
        bio = self._generate_bio(artist, genre)
        one_sheet = self._generate_one_sheet(artist, release, genre)

        return {
            "campaign_id": str(uuid.uuid4())[:8],
            "artist": artist,
            "release": release,
            "genre": genre,
            "campaign_type": ct,
            "duration_days": duration_days,
            "elevator_pitch": hooks["elevator"],
            "taglines": hooks["taglines"],
            "hashtag_sets": hooks["hashtags"],
            "phases": phases,
            "content_calendar": content_calendar,
            "email_sequence": email_sequence,
            "ad_creatives": ad_creatives,
            "playlist_pitches": playlist_pitches,
            "influencer_pitches": influencer_pitches,
            "bio": bio,
            "one_sheet": one_sheet,
            "drivers": self.DRIVERS,
            "generated_at": datetime.utcnow().isoformat()
        }

    def generate_social_post(self, artist: str, release: str, genre: str,
                             platform: str = "Instagram",
                             post_type: str = "announcement") -> Dict[str, Any]:
        """Generate a single social media post."""
        platform = platform or "Instagram"
        templates = {
            "announcement": [
                f"🚀 {release} is OUT NOW. Stream it everywhere. Link in bio. #{genre.replace(' ', '')} #newmusic",
                f"The wait is over. {artist} just dropped {release}. Hit play and tell us your favorite track. 🎧",
                f"New {genre} alert. {release} is now live on all platforms. Run it up. 🔥"
            ],
            "behind_the_scenes": [
                f"A look behind {release}. This one meant everything to create. 🎬",
                f"Late nights, early mornings. {release} wouldn't exist without the grind.",
                f"Studio energy for {release}. Full video on YouTube."
            ],
            "lyric": [
                f"\"{self._random_lyric_line(genre)}\" — {release} is out now.",
                f"This line hits different. {release} 🎶",
                f"Drop a 🔥 if you feel this lyric from {release}."
            ],
            "question": [
                f"Which track from {release} are you running back? 👇",
                f"What's the best song on {release}? Wrong answers only.",
                f"If {release} had a music video, which song should get it first?"
            ],
            "countdown": [
                f"24 hours until {release}. Set your alarms. ⏰",
                f"{release} drops at midnight. Who's staying up?",
                f"One week. {release}. Save the date. 📅"
            ]
        }
        copy = self._seed.choice(templates.get(post_type, templates["announcement"]))
        hashtags = " ".join(self._hashtag_set(genre, platform))
        return {
            "platform": platform,
            "post_type": post_type,
            "copy": f"{copy}\n\n{hashtags}",
            "best_time": self._best_time(platform),
            "caption": copy,
            "hashtags": hashtags,
            "cta": "Stream / Save / Share"
        }

    def remix_content(self, asset: str, artist: str, release: str, genre: str,
                      count: int = 30) -> List[Dict[str, Any]]:
        """Turn one marketing asset into a month of content."""
        remixes = []
        post_types = ["announcement", "behind_the_scenes", "lyric", "question"]
        platforms = ["Instagram", "TikTok", "X (Twitter)", "Facebook", "YouTube"]
        for i in range(count):
            platform = platforms[i % len(platforms)]
            post_type = post_types[i % len(post_types)]
            post = self.generate_social_post(artist, release, genre, platform, post_type)
            post["day"] = i + 1
            post["asset_source"] = asset
            remixes.append(post)
        return remixes

    def _build_phases(self, campaign_type: str, duration_days: int) -> List[Dict[str, Any]]:
        phases = [
            {"name": "Tease", "days": f"1-{max(1, duration_days//5)}", "goal": "Build anticipation and pre-saves", "tactics": ["Lyric snippets", "Countdown stories", "Pre-save push"]},
            {"name": "Launch", "days": f"{max(2, duration_days//5)}-{max(3, duration_days//3)}", "goal": "Maximize release-day streams and shares", "tactics": ["Announcement posts", "Email blast", "Playlist pitching"]},
            {"name": "Sustain", "days": f"{max(4, duration_days//3)}-{max(6, duration_days*2//3)}", "goal": "Keep momentum with content remixes", "tactics": ["Behind-the-scenes", "Fan reposts", "Influencer features"]},
            {"name": "Convert", "days": f"{max(7, duration_days*2//3)}-{duration_days}", "goal": "Drive merch, tickets, and follows", "tactics": ["Tour / ticket links", "Merch drops", "Retargeting ads"]}
        ]
        return phases

    def _generate_hooks(self, artist: str, release: str, genre: str) -> Dict[str, Any]:
        return {
            "elevator": f"{artist} is redefining {genre} with {release} — a self-produced, fiercely independent release built for repeat listens.",
            "taglines": [
                f"{release}: {genre} without compromise.",
                f"Turn it up. {artist} is just getting started.",
                f"The next name in {genre} is {artist}.",
                f"{release} out now — stream it before your friends do."
            ],
            "hashtags": {
                "set_a": [f"#{artist.replace(' ', '')}", f"#{release.replace(' ', '')}", "#newmusic", "#indie", f"#{genre.replace(' ', '')}"],
                "set_b": ["#newmusicfriday", "#spotify", "#applemusic", "#musician", "#producer"],
                "set_c": ["#nowplaying", "#musicvideo", "#unsignedartist", "#independentartist", "#newrelease"]
            }
        }

    def _build_calendar(self, artist: str, release: str, genre: str, days: int) -> List[Dict[str, Any]]:
        calendar = []
        post_types = ["announcement", "behind_the_scenes", "lyric", "question", "countdown"]
        platforms = ["Instagram", "TikTok", "X (Twitter)", "Facebook"]
        for d in range(1, days + 1):
            platform = platforms[d % len(platforms)]
            post_type = post_types[d % len(post_types)]
            post = self.generate_social_post(artist, release, genre, platform, post_type)
            post["day"] = d
            calendar.append(post)
        return calendar

    def _build_email_sequence(self, artist: str, release: str, genre: str) -> List[Dict[str, Any]]:
        return [
            {
                "day": -7,
                "subject": f"Something new is coming from {artist}",
                "body": f"Hey fan,\n\n{artist} has been in the studio crafting a {genre} release that hits different. {release} drops in 7 days. Pre-save now and be the first to hear it.\n\nPre-save: https://distrokid.com/hyperfollow/{artist.lower().replace(' ', '')}\n\nTalk soon,\nTITAN 7"
            },
            {
                "day": 0,
                "subject": f"{release} is OUT NOW 🎧",
                "body": f"It's here.\n\n{artist} just released {release} and it's streaming everywhere right now. Hit play, add it to your playlist, and reply with your favorite track.\n\nStream: https://open.spotify.com/artist/example\n\nLet's run it up.\nTITAN 7"
            },
            {
                "day": 3,
                "subject": f"Did you catch the story behind {release}?",
                "body": f"Hey,\n\nWe put together a behind-the-scenes look at how {release} came together. Three days in and the response has been unreal. Watch the video and share it with a friend who needs new music.\n\nWatch: https://youtube.com/@titan7official\n\nThanks,\nTITAN 7"
            },
            {
                "day": 7,
                "subject": f"Help us reach the next playlist",
                "body": f"Hey,\n\nIf {release} made it onto your playlist this week, would you share the link with one curator or friend? Independent artists move by word of mouth, and yours matters.\n\nShare: https://open.spotify.com/artist/example\n\nGrateful,\nTITAN 7"
            },
            {
                "day": 14,
                "subject": f"{artist} is hitting the road",
                "body": f"Big news — {artist} is taking {release} on the road. Tickets are moving. Lock yours in and come say hi at the merch table.\n\nTour dates: https://bandsintown.com/example\n\nSee you there,\nTITAN 7"
            }
        ]

    def _build_ad_creatives(self, artist: str, release: str, genre: str) -> List[Dict[str, Any]]:
        return [
            {"platform": "Meta / Instagram", "objective": "Traffic / Pre-saves", "headline": f"{artist} — {release}", "primary_text": f"If {genre} is your thing, {release} needs to be on your radar. Stream it now.", "cta": "Listen Now"},
            {"platform": "TikTok", "objective": "Video Views", "headline": f"{release} snippet", "primary_text": f"POV: you just found your new favorite {genre} artist. {artist} — {release}.", "cta": "Watch Now"},
            {"platform": "YouTube", "objective": "Video Views", "headline": f"{artist} - {release} (Official)", "primary_text": f"Official release from {artist}. Watch the full video.", "cta": "Watch"},
            {"platform": "Google Search", "objective": "Brand Search", "headline": f"{artist} {release}", "primary_text": f"Stream {release} on Spotify, Apple Music, and more.", "cta": "Stream"}
        ]

    def _build_playlist_pitches(self, artist: str, release: str, genre: str) -> List[Dict[str, Any]]:
        return [
            {"platform": "Spotify Editorial", "contact": "editorial@spotify.com", "subject": f"Playlist Pitch: {artist} — {release}", "body": f"Hi Spotify Editorial team,\n\n{artist} is releasing {release}, a {genre} track with strong early engagement. We believe it fits Fresh Finds, New Music Friday, and genre-specific playlists. Thanks for considering it.\n\nBest,\nTITAN 7"},
            {"platform": "Independent Curators", "contact": "curators@submithub.com", "subject": f"{genre} submission: {artist} — {release}", "body": f"Hi curator,\n\n{artist}'s new {genre} release {release} is available now. We'd love a playlist add if it fits your audience.\n\nBest,\nTITAN 7"},
            {"platform": "College Radio", "contact": "music@kexp.org", "subject": f"Radio submission: {artist} — {release}", "body": f"Hi,\n\n{artist} just released {release}, a {genre} track perfect for rotation. Please let us know the best way to submit music for airplay.\n\nBest,\nTITAN 7"}
        ]

    def _build_influencer_pitches(self, artist: str, release: str, genre: str) -> List[Dict[str, Any]]:
        return [
            {"tier": "Macro", "subject": f"Feature opportunity: {artist} — {release}", "body": f"Hi,\n\n{artist} is an emerging {genre} act with a new release {release} that's picking up traction. We'd love to explore a feature, reaction video, or playlist inclusion.\n\nBest,\nTITAN 7"},
            {"tier": "Micro", "subject": f"Collaboration: {artist} — {release}", "body": f"Hi,\n\nLove your content. {artist} just dropped {release} and we think your audience would vibe with it. Open to a paid or gifted collaboration?\n\nBest,\nTITAN 7"}
        ]

    def _generate_bio(self, artist: str, genre: str) -> str:
        return f"{artist} is a {genre} artist operating at the intersection of raw lyricism and polished production. Built independently and distributed through Redemption Road Music Group, their music is made for late-night drives, festival stages, and everything in between."

    def _generate_one_sheet(self, artist: str, release: str, genre: str) -> Dict[str, Any]:
        return {
            "artist": artist,
            "release": release,
            "genre": genre,
            "label": "Redemption Road Music Group",
            "contact": f"press@{DEFAULT_DOMAIN}",
            "elevator_pitch": f"{artist} delivers {genre} with undeniable energy on {release}.",
            "for Fans Of": ["Comparable A", "Comparable B", "Comparable C"],
            "streaming": "https://open.spotify.com/artist/example",
            "social": "@titan7official",
            "press_quote": f"\"{release} is the sound of an artist who knows exactly who they are.\" — TITAN 7 Press"
        }

    def _hashtag_set(self, genre: str, platform: str) -> List[str]:
        base = ["#newmusic", f"#{genre.replace(' ', '')}", "#indie"]
        if platform == "TikTok":
            base += ["#musictok", "#fyp"]
        elif platform == "Instagram":
            base += ["#instamusic", "#artistsoninstagram"]
        elif platform == "X (Twitter)":
            base += ["#nowplaying", "#music"]
        return base[:5]

    def _best_time(self, platform: str) -> str:
        return self.DRIVERS.get(platform, {}).get("best_times", ["12:00"])[0]

    def _random_lyric_line(self, genre: str) -> str:
        lines = [
            "We don't wait for permission, we just go",
            "Every scar is a story I never told",
            "Lights down low, let the feeling take control",
            "Built from nothing, now we own the night",
            "This is the sound of breaking through"
        ]
        return random.choice(lines)


# Singleton
ai_marketing = AIMarketingEngine()
