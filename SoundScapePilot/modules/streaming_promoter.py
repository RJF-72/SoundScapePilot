"""Streaming Promoter — per-platform pitching strategy for the major
streaming services. Each platform entry reflects the real submission
mechanism that platform offers independent artists (in-app pitching,
creator dashboards, editorial routes via distributors). Strategies and
success estimates are planning guidance computed from the artist's
supplied profile signals — not measured placement data."""
from typing import List, Dict, Any


PLATFORMS: List[Dict[str, Any]] = [
    {
        "key": "spotify",
        "platform_name": "Spotify",
        "focus": "Editorial playlists + algorithmic (Release Radar, Discover Weekly)",
        "pitch_url": "https://artists.spotify.com",
        "pitch_method": "Pitch in Spotify for Artists (Music → Upcoming), at least 7 days before release",
        "base_rate": 35,
        "strategy": ("Spotify's editors read the 500-character pitch note, not the press kit. "
                     "Describe the song's story, genre lane, and comparable artists in plain words, "
                     "then give the algorithm a head start: get the track on user playlists and "
                     "pre-saves before release day. Editorial decisions typically land in release "
                     "week; keep pitching new singles rather than re-pitching old ones."),
        "pro_tip": ("Claim and verify the Spotify for Artists profile now — canvas, artist pick, "
                    "and profile header photos all feed the algorithm's confidence."),
        "timing": "Pitch 7-28 days before release; never after release day for editorial",
    },
    {
        "key": "apple_music",
        "platform_name": "Apple Music",
        "focus": "Editorial playlists (via distributor) + Shazam discovery",
        "pitch_url": "https://artists.apple.com",
        "pitch_method": "Editorial pitching runs through your label/distributor; keep the Apple Music for Artists profile current",
        "base_rate": 30,
        "strategy": ("Apple Music's editorial is pitched through your distributor, so the "
                     "operational work is: deliver early, attach clean metadata and artwork, "
                     "and make sure the Apple Music for Artists profile is claimed with a bio "
                     "and photos. Shazam counts feed discovery — play the song live and tell "
                     "the room to Shazam it."),
        "pro_tip": ("Apple Music prioritizes high-resolution audio; deliver lossless masters "
                    "with proper mastering credits for the best placement shot."),
        "timing": "Deliver to distributor 4+ weeks before release so the editorial window opens",
    },
    {
        "key": "amazon_music",
        "platform_name": "Amazon Music",
        "focus": "Editorial playlists + Alexa voice discovery",
        "pitch_url": "https://artists.amazonmusic.com",
        "pitch_method": "Pitch through Amazon Music for Artists; Alexa-enabled releases get extra surface",
        "base_rate": 30,
        "strategy": ("Amazon's angle is voice: name your artist name and track titles so Alexa "
                     "hears them correctly, and use the Amazon Music for Artists pitch form for "
                     "playlist consideration. The platform over-indexes on Prime-bundled "
                     "listeners, so lean into genre playlists with broad, household-friendly "
                     "hooks."),
        "pro_tip": "Test your artist and song names with an Alexa device before release day.",
        "timing": "Pitch 2-4 weeks before release; refresh the artist profile the same week",
    },
    {
        "key": "youtube_music",
        "platform_name": "YouTube Music",
        "focus": "Official Artist Channel + music-video and premiere shelf",
        "pitch_url": "https://studio.youtube.com",
        "pitch_method": "Claim the Official Artist Channel in YouTube Studio; premieres and Shorts drive first-week velocity",
        "base_rate": 40,
        "strategy": ("YouTube is half distribution, half search engine. The highest-leverage "
                     "moves: an Official Artist Channel, a premiere with a live chat, and "
                     "Shorts cut from the music video feeding the full-length upload. The "
                     "algorithm reads watch time, so give viewers a reason to stay past 30 "
                     "seconds — lyrics, a story intro, anything with a face."),
        "pro_tip": "Upload the audio track to Content ID through your distributor and manually claim fan uploads early.",
        "timing": "Schedule premieres 7-14 days out; post Shorts daily in release week",
    },
    {
        "key": "tidal",
        "platform_name": "TIDAL",
        "focus": "TIDAL Rising program + high-fidelity editorial",
        "pitch_url": "https://tidal.com",
        "pitch_method": "Editorial via distributor; TIDAL Rising applications run through artist support",
        "base_rate": 28,
        "strategy": ("TIDAL courts audiophiles and its editorial team favors quality "
                     "presentation: lossless delivery, complete credits, and strong visual "
                     "identity. TIDAL Rising spotlights one emerging artist at a time — the "
                     "realistic entry is a distributor-relayed editorial pitch with a clean, "
                     "finished package."),
        "pro_tip": "Deliver MQA/master-quality audio; TIDs of half-finished demos die in review.",
        "timing": "Submit to distributor 4+ weeks before release; TIDAL Rising cycles monthly",
    },
    {
        "key": "deezer",
        "platform_name": "Deezer",
        "focus": "Flow algorithm + territorial editorial playlists",
        "pitch_url": "https://www.deezer.com",
        "pitch_method": "Editorial pitching via distributor; keep the artist page current through Deezer for Creators",
        "base_rate": 30,
        "strategy": ("Deezer's Flow algorithm rewards favorites and replays, so seed the track "
                     "with your existing fans first — ask them to heart it, not just play it. "
                     "Territorial editors (FR, BR, DE, US) operate independently, so pitch each "
                     "market's story separately through your distributor."),
        "pro_tip": "Translated metadata matters on Deezer — localize the artist bio for the markets you pitch.",
        "timing": "Distributor pitch 3-4 weeks before release; fan seeding in release week",
    },
    {
        "key": "soundcloud",
        "platform_name": "SoundCloud",
        "focus": "Direct upload + First on SoundCloud + fan-powered charts",
        "pitch_url": "https://soundcloud.com",
        "pitch_method": "Upload directly; pitch editorial via Repost by SoundCloud or the creator dashboard",
        "base_rate": 55,
        "strategy": ("SoundCloud is the one platform where you control everything. Post the "
                     "track with pinned comments, a full description with buy/pre-save links, "
                     "and repost trades with artists in your lane. First on SoundCloud and "
                     "scene charts are reachable for genuinely active accounts — comment on "
                     "other people's tracks like a community member, not a spammer."),
        "pro_tip": "Waveform comments and repost chains still move the needle here — treat it like social, not a locker.",
        "timing": "Post any time; momentum compounds, so release singles on a steady cadence",
    },
    {
        "key": "audiomack",
        "platform_name": "Audiomack",
        "focus": "Trending charts + creator dashboard pitching",
        "pitch_url": "https://audiomack.com",
        "pitch_method": "Upload via the creator dashboard; pitch trending/editorial from the dashboard",
        "base_rate": 50,
        "strategy": ("Audiomack punches above its weight for hip-hop, R&B, Afrobeats, and "
                     "dancehall, and its trending charts are genuinely earnable. Upload in the "
                     "creator dashboard, tag precisely, and pitch for editorial placement from "
                     "the dashboard the same day. Verified account status helps — apply for it."),
        "pro_tip": "Premieres on Audiomack are a real unlock for urban-leaning genres; ask for one once you have engagement.",
        "timing": "Upload and pitch the same week; trending charts refresh daily",
    },
    {
        "key": "bandcamp",
        "platform_name": "BandCamp",
        "focus": "Direct-to-fan sales + Bandcamp editorial (Weekly/Daily)",
        "pitch_url": "https://bandcamp.com",
        "pitch_method": "Editorial via the artist account submission form; sales through your own page",
        "base_rate": 45,
        "strategy": ("Bandcamp is the platform that actually pays independent artists. The "
                     "editorial desk covers a narrow slice of releases weekly, so give them a "
                     "story: why this record, why now, why it matters to their readers. "
                     "Meanwhile your own page is a store — price the album fairly, offer the "
                     "merch bundle, and rally fans on Bandcamp Fridays."),
        "pro_tip": "Set a pay-what-you-want single with a fair minimum; the average paid often beats the minimum by multiples.",
        "timing": "Editorial submissions 3-6 weeks before release; announce Bandcamp Friday drops in advance",
    },
]


def get_all_platforms() -> List[Dict[str, Any]]:
    """All supported platforms, as a JSON-serializable list. Each entry
    carries its `key`, display name, and pitch mechanics so the UI and
    API can consume them directly."""
    return [
        {
            "key": p["key"],
            "platform": p["key"],
            "platform_name": p["platform_name"],
            "focus": p["focus"],
            "pitch_url": p["pitch_url"],
            "pitch_method": p["pitch_method"],
        }
        for p in PLATFORMS
    ]


def _find(key: str) -> Dict[str, Any]:
    kl = (key or "").strip().lower().replace(" ", "_")
    for p in PLATFORMS:
        if p["key"] == kl or p["platform_name"].lower() == kl:
            return p
    return PLATFORMS[0]


def get_platform_strategy(platform: str = "spotify", artist: str = "Artist",
                          genre: str = "", bio: str = "", spotify: str = "",
                          soundcloud: str = "") -> Dict[str, Any]:
    """Personalized per-platform strategy built from the artist's
    supplied EPK fields. Success rates are planning estimates from
    profile completeness, not measured placement data."""
    p = _find(platform)
    rate = p["base_rate"]
    if spotify and p["key"] in ("spotify", "apple_music", "amazon_music"):
        rate += 8
    if soundcloud and p["key"] in ("soundcloud", "audiomack"):
        rate += 8
    if bio:
        rate += 5
    if genre:
        rate += 4
    rate = max(5, min(92, rate))

    genre_part = f" ({genre})" if genre else ""
    pitch_body = (
        f"Artist: {artist}{genre_part}\n"
        f"Platform: {p['platform_name']}\n\n"
        f"Pitch: {artist}{genre_part} is releasing new music built for your listeners. "
        f"{p['pitch_method']}. {bio.strip()[:300] if bio else 'Independent release, serviced directly by the artist.'}\n\n"
        f"Listen: {spotify or soundcloud or '(links in EPK)'}\n"
        f"Action: {p['timing']}"
    )

    return {
        "platform": p["key"],
        "platform_name": p["platform_name"],
        "focus": p["focus"],
        "strategy": p["strategy"],
        "pro_tip": p["pro_tip"],
        "timing": p["timing"],
        "pitch_url": p["pitch_url"],
        "pitch_method": p["pitch_method"],
        "success_rate": f"{rate}%",
        "pitch_body": pitch_body,
        "action_items": [
            f"Complete the platform-side setup: {p['pitch_method']}.",
            f"Prepare profile assets (bio, photos, links) before pitching — profiles with bios convert better.",
            f"Seed first-week engagement: pre-saves, fan shares, and {p['platform_name']}-native features in release week.",
            f"Follow the timing window: {p['timing']}.",
        ],
    }
