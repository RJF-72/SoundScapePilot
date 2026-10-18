from typing import Dict, Any, List


# ===== SERVICE TIERS =====

TIERS = {
    "distribution_only": {
        "name": "Distribution Only",
        "price_monthly": 9.99,
        "price_yearly": 99.99,
        "price_per_release": 49.99,
        "description": "Get your music on all major platforms fast.",
        "tagline": "Just deliver.",
        "features": [
            "Distribution to 15+ DSPs (Spotify, Apple, Amazon, etc.)",
            "ISRC & UPC assignment",
            "Metadata formatting & validation",
            "Release within 24-48 hours",
            "Royalty collection (100% artist keeps)",
            "Basic sales reporting",
            "AI Song catalog (up to 1,000 songs)",
        ],
        "limits": {
            "ai_songs": 1000,
            "human_singles_per_year": 12,
            "human_albums_per_year": 2,
            "radio_promotion": False,
            "streaming_promotion": False,
            "sync_pitching": False,
            "tour_tools": False,
            "marketing_campaigns": False,
        },
        "target": "Independent artists, AI music creators, beatmakers",
    },
    "artist_pro": {
        "name": "Artist Pro",
        "price_monthly": 29.99,
        "price_yearly": 299.99,
        "price_per_release": 0,
        "description": "Full promotional pipeline for serious independent artists.",
        "tagline": "Get heard.",
        "features": [
            "Everything in Distribution Only",
            "Unlimited AI Song catalog",
            "Radio promotion campaign (50+ stations per release)",
            "Streaming platform pitching (9 platforms)",
            "EPK generation & hosting",
            "Press release distribution",
            "AI Marketing campaign generation",
            "Priority metadata handling (DDEX-ready)",
            "Redemption Road Chart eligibility",
        ],
        "limits": {
            "ai_songs": -1,
            "human_singles_per_year": 24,
            "human_albums_per_year": 4,
            "radio_promotion": True,
            "streaming_promotion": True,
            "sync_pitching": False,
            "tour_tools": False,
            "marketing_campaigns": True,
        },
        "target": "Active touring artists, serious indie musicians, AI music labels",
    },
    "label_launchpad": {
        "name": "Label Launchpad",
        "price_monthly": 79.99,
        "price_yearly": 799.99,
        "price_per_release": 0,
        "description": "Everything a growing label needs to operate at major-label level.",
        "tagline": "Run your label.",
        "features": [
            "Everything in Artist Pro",
            "Up to 5 artist roster slots",
            "Full tour routing engine (60+ markets)",
            "Booking manager with contract generation",
            "Venue & church booking database",
            "Sync licensing pitches (15 music supervisors)",
            "Cue sheet generation for TV/film placements",
            "Royalty split management (artist/producer/publisher)",
            "Quarterly royalty statements",
            "Catalog management (stems, masters, versions)",
            "Release calendar coordination",
            "Redemption Road Radio spins eligibility",
            "Priority Symphonic distribution pipeline",
            "Dedicated account manager",
        ],
        "limits": {
            "ai_songs": -1,
            "human_singles_per_year": -1,
            "human_albums_per_year": -1,
            "radio_promotion": True,
            "streaming_promotion": True,
            "sync_pitching": True,
            "tour_tools": True,
            "marketing_campaigns": True,
            "roster_slots": 5,
        },
        "target": "Independent labels, management companies, artist collectives",
    },
    "enterprise": {
        "name": "Redemption Road Enterprise",
        "price_monthly": 299.99,
        "price_yearly": 2999.99,
        "price_per_release": 0,
        "description": "Unlimited everything. White-label distribution. Full OS access.",
        "tagline": "Build your empire.",
        "features": [
            "Everything in Label Launchpad",
            "Unlimited artist roster slots",
            "White-label distribution (your brand on DSPs)",
            "Custom metadata pipeline integration",
            "Private API access to all OS modules",
            "Redemption Road Radio station sponsorship",
            "Sync licensing priority placement program",
            "Weekly strategy calls",
            "Custom development requests",
            "Bulk AI song ingestion (unlimited)",
            "Revenue share negotiation support",
            "Investor-ready reporting dashboard",
        ],
        "limits": {
            "ai_songs": -1,
            "human_singles_per_year": -1,
            "human_albums_per_year": -1,
            "radio_promotion": True,
            "streaming_promotion": True,
            "sync_pitching": True,
            "tour_tools": True,
            "marketing_campaigns": True,
            "roster_slots": -1,
        },
        "target": "Established labels, music publishers, media companies, investors",
    },
}

# ===== À LA CARTE ADD-ONS =====

ADDONS = [
    {
        "name": "Sync Licensing Pitch Pack",
        "price": 199.99,
        "description": "Pitch your song to 15 music supervisors with custom cue sheet + follow-ups",
        "includes": ["Custom cue sheet", "Supervisor database access", "3 follow-up rounds", "Sync contract template"],
    },
    {
        "name": "Radio Campaign Boost",
        "price": 149.99,
        "description": "Add 100+ targeted radio stations to your campaign with personalized pitches",
        "includes": ["100+ station research", "Format-specific pitch", "Station strategy doc", "Follow-up scheduling"],
    },
    {
        "name": "Streaming Platform Blitz",
        "price": 99.99,
        "description": "9-platform streaming promotion campaign with platform-specific strategies",
        "includes": ["Spotify editorial pitching", "Apple Music iConnect", "YouTube Topic channel", "All 9 platforms"],
    },
    {
        "name": "Tour Route Planning",
        "price": 249.99,
        "description": "Full 12-show tour route with budget, P&L, venue recommendations, and contracts",
        "includes": ["Route optimization", "P&L projection", "Venue recommendations", "Performance contracts"],
    },
    {
        "name": "AI Song Catalog Ingestion",
        "price": 0.01,
        "description": "Per-song fee for AI-generated music catalog upload (min 100 songs)",
        "includes": ["ISRC assignment", "UPC generation", "Metadata formatting", "Distribution ready"],
        "unit": "per song, min 100",
    },
    {
        "name": "Catalog Buyout",
        "price": 0,
        "description": "We acquire your existing catalog for an upfront payment + ongoing royalty split",
        "includes": ["Upfront payment (negotiated)", "Royalty split (negotiated)", "Active promotion", "Sync pitching"],
        "negotiable": True,
    },
]


# ===== REVENUE PROJECTION ENGINE =====

def estimate_annual_revenue(
    distro_only_count: int = 0,
    artist_pro_count: int = 0,
    label_launchpad_count: int = 0,
    enterprise_count: int = 0,
    ai_songs_uploaded: int = 0,
    sync_packs_sold: int = 0,
    radio_boosts_sold: int = 0,
    streaming_blitzes_sold: int = 0,
    tour_plans_sold: int = 0,
) -> Dict[str, Any]:
    recurring = (
        distro_only_count * TIERS["distribution_only"]["price_monthly"]
        + artist_pro_count * TIERS["artist_pro"]["price_monthly"]
        + label_launchpad_count * TIERS["label_launchpad"]["price_monthly"]
        + enterprise_count * TIERS["enterprise"]["price_monthly"]
    ) * 12

    one_time = (
        sync_packs_sold * 199.99
        + radio_boosts_sold * 149.99
        + streaming_blitzes_sold * 99.99
        + tour_plans_sold * 249.99
        + ai_songs_uploaded * 0.01
    )

    # Per-release fees (distribution only tier)
    distro_fees = distro_only_count * 49.99 * 6  # assume 6 releases/year average

    annual = recurring + one_time + distro_fees
    monthly_avg = annual / 12

    return {
        "annual_recurring_subscriptions": round(recurring, 2),
        "annual_one_time_services": round(one_time, 2),
        "annual_per_release_fees": round(distro_fees, 2),
        "total_annual_revenue": round(annual, 2),
        "monthly_average": round(monthly_avg, 2),
        "breakdown": {
            "distribution_only": distro_only_count,
            "artist_pro": artist_pro_count,
            "label_launchpad": label_launchpad_count,
            "enterprise": enterprise_count,
            "ai_songs_uploaded": ai_songs_uploaded,
        },
    }


# ===== COMPARISON MARKETING COPY =====

COMPETITOR_COMPARISON = {
    "vs_distrokid": {
        "competitor": "DistroKid",
        "their_price": "$22.99/year",
        "their_limit": "Unlimited uploads, 0% royalty",
        "their_missing": ["No radio promotion", "No streaming pitching", "No sync licensing",
                          "No tour tools", "No catalog management", "No royalty splitting",
                          "No EPK generation", "No AI song support"],
        "our_equivalent": "Artist Pro ($29.99/mo = $299.99/yr)",
        "why_better": "DistroKid delivers to DSPs. We deliver to DSPs + radio stations + streaming curators + TV/film supervisors + venues.",
    },
    "vs_cdbaby": {
        "competitor": "CD Baby Pro",
        "their_price": "$39.99 + $29.99/release",
        "their_limit": "Sync licensing included, 15% royalty cut",
        "their_missing": ["No automated radio campaigns", "No tour routing engine",
                          "No AI song catalog support", "No real-time dashboard"],
        "our_equivalent": "Label Launchpad ($79.99/mo)",
        "why_better": "CD Baby offers basic sync. We offer sync + radio + streaming + tour + booking + catalog management in one platform.",
    },
    "vs_tunecore": {
        "competitor": "TuneCore",
        "their_price": "$14.99/year per single, $49.99/year per album",
        "their_limit": "Publishing admin extra ($75/year)",
        "their_missing": ["No AI song support", "No automated promotion campaigns",
                          "No tour tools", "No royalty split management"],
        "our_equivalent": "Label Launchpad ($79.99/mo)",
        "why_better": "TuneCore charges per release per year. We charge one flat fee for unlimited releases + promotion + tools.",
    },
    "vs_symphonic": {
        "competitor": "Symphonic Distribution",
        "their_price": "15% commission or ~$50/release",
        "their_limit": "Label services included, requires application",
        "their_missing": ["No AI song catalog pipeline", "No integrated tour/booking engine",
                          "No radio promoter", "No streaming promoter"],
        "our_value_add": "We layer our OS on top of their distribution. You get Symphonic's reach + our promotion engines.",
    },
}

MARKETING_MESSAGES = [
    {
        "headline": "From Abilene to the World.",
        "body": "Redemption Road Music Group runs on TITAN 7 — the only label OS that goes from song registration to sync placement in one pipeline.",
        "audience": "General",
    },
    {
        "headline": "12,000 Songs. One Pipeline.",
        "body": "AI music catalog? We handle it at scale. ISRC, UPC, metadata, distribution — per-song cost of one penny.",
        "audience": "AI Music Creators",
    },
    {
        "headline": "We Don't Just Distribute. We Promote.",
        "body": "Most distributors stop at delivery. We pitch your music to 500+ radio stations, 9 streaming platforms, and 15 music supervisors — automatically.",
        "audience": "Independent Artists",
    },
    {
        "headline": "Major-Label Tools. Independent Price.",
        "body": "Everything Sony, Universal, and Warner use — radio promotion, tour routing, sync licensing, royalty accounting — for $79.99/month.",
        "audience": "Independent Labels",
    },
    {
        "headline": "Your Music. Our Pipeline. Their Playlist.",
        "body": "Artist Pro: $29.99/month gets you on every DSP, every radio station, and every streaming platform that matters.",
        "audience": "Artists",
    },
    {
        "headline": "The Label OS That Works While You Sleep.",
        "body": "AI-powered radio promotion. Automated streaming pitching. Self-driving tour routing. Redemption Road never stops working for your music.",
        "audience": "Labels & Managers",
    },
    {
        "headline": "Not Just Distribution. Domination.",
        "body": "DistroKid delivers files. We deliver fans. Radio spins. Playlist adds. Sync placements. Tour dates. Real results.",
        "audience": "Artists",
    },
    {
        "headline": "Built in Texas. Ready for the World.",
        "body": "Redemption Road Music Group — the independent label with infrastructure that competes with the majors.",
        "audience": "General",
    },
    {
        "headline": "AI Songs Welcome Here.",
        "body": "We don't gatekeep. We distribute. AI music, human music, hybrid — if it's good, we put it everywhere.",
        "audience": "AI Music Producers",
    },
    {
        "headline": "From Demo to DSP in 24 Hours.",
        "body": "Upload your track. We assign ISRC/UPC, format metadata, deliver to 15+ platforms, and start pitching to radio — same day.",
        "audience": "Artists",
    },
]
