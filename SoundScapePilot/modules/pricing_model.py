from typing import Dict, Any, List


# ===== SERVICE TIERS =====
# NOTE: SoundScape Pilot does NOT provide music distribution and does NOT
# issue ISRC/UPC codes. We are a promotion, press, sync, booking, and label
# operations platform. Artists deliver to DSPs through their own distributor;
# we prepare metadata handoff packages and run every promotional pipeline.

TIERS = {
    "artist_starter": {
        "name": "Artist Starter",
        "price_monthly": 9.99,
        "price_yearly": 99.99,
        "price_per_release": 0,
        "description": "Self-serve tools: catalog, EPKs, royalties, and sync estimates.",
        "tagline": "Get organized.",
        "features": [
            "AI Song catalog (up to 1,000 songs)",
            "EPK generator",
            "Sales reporting",
            "Sync fee estimator & cue sheet tools",
            "Release metadata QC & delivery-ready data sheet",
            "Contract templates",
        ],
        "limits": {
            "ai_songs": 1000,
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
            "Everything in Artist Starter",
            "Unlimited song catalog",
            "Radio promotion campaign (50+ stations per release)",
            "Streaming platform pitching (9 platforms)",
            "EPK generation & hosting",
            "Press release wire (tiered media database)",
            "AI marketing campaign generation",
            "Priority metadata handling",
            "Redemption Road Chart eligibility",
        ],
        "limits": {
            "ai_songs": -1,
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
            "Catalog management (stems, masters, versions)",
            "Release calendar coordination",
            "Redemption Road Radio spins eligibility",
            "Dedicated account manager",
        ],
        "limits": {
            "ai_songs": -1,
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
        "description": "Unlimited everything. White-label branding. Full OS access.",
        "tagline": "Build your empire.",
        "features": [
            "Everything in Label Launchpad",
            "Unlimited artist roster slots",
            "White-label branding (your logo, your domain)",
            "Custom metadata pipeline integration",
            "Private API access to all OS modules",
            "Redemption Road Radio station sponsorship",
            "Sync licensing priority placement program",
            "Weekly strategy calls",
            "Custom development requests",
            "Bulk catalog ingestion (unlimited)",
            "Revenue share negotiation support",
            "Investor-ready reporting dashboard",
        ],
        "limits": {
            "ai_songs": -1,
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
        "name": "Streaming Pitching Blitz",
        "price": 99.99,
        "description": "9-platform promotional pitching campaign with platform-specific strategies",
        "includes": ["Spotify editorial pitching", "Apple Music iConnect", "YouTube Topic channels", "All 9 platforms"],
    },
    {
        "name": "Tour Route Planning",
        "price": 249.99,
        "description": "Full 12-show tour route with budget, P&L, venue recommendations, and contracts",
        "includes": ["Route optimization", "P&L projection", "Venue recommendations", "Performance contracts"],
    },
    {
        "name": "Catalog Ingestion & Metadata QC",
        "price": 0.01,
        "description": "Per-song catalog upload with metadata formatting and a delivery-ready data sheet (min 100 songs)",
        "includes": ["Metadata formatting & QC", "Delivery-ready data sheet", "Cue sheet setup"],
        "unit": "per song, min 100",
    },
    {
        "name": "Catalog Buyout",
        "price": 0,
        "description": "We acquire your existing catalog for an upfront payment + ongoing revenue share",
        "includes": ["Upfront payment (negotiated)", "Ongoing revenue share (negotiated)", "Active promotion", "Sync pitching"],
        "negotiable": True,
    },
]


# ===== REVENUE PROJECTION ENGINE =====

def estimate_annual_revenue(
    artist_starter_count: int = 0,
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
        artist_starter_count * TIERS["artist_starter"]["price_monthly"]
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

    annual = recurring + one_time
    monthly_avg = annual / 12

    return {
        "annual_recurring_subscriptions": round(recurring, 2),
        "annual_one_time_services": round(one_time, 2),
        "annual_per_release_fees": 0,
        "total_annual_revenue": round(annual, 2),
        "monthly_average": round(monthly_avg, 2),
        "breakdown": {
            "artist_starter": artist_starter_count,
            "artist_pro": artist_pro_count,
            "label_launchpad": label_launchpad_count,
            "enterprise": enterprise_count,
            "ai_songs_uploaded": ai_songs_uploaded,
        },
    }


# ===== COMPARISON MARKETING COPY =====

COMPETITOR_COMPARISON = {
    "vs_radio_promoter": {
        "competitor": "Traditional Radio Promoter",
        "their_price": "$500–$1,500 per campaign",
        "their_limit": "One promoter, one format, manual reporting",
        "their_missing": ["No streaming pitching", "No sync licensing pipeline",
                          "No tour routing", "No EPK generation",
                          "No AI song catalog support"],
        "our_equivalent": "Artist Pro ($29.99/mo = $299.99/yr)",
        "why_better": "One flat fee runs radio, streaming, sync, and press pipelines in parallel with real-time reporting.",
    },
    "vs_sync_agency": {
        "competitor": "Sync Licensing Agency",
        "their_price": "25–50% of every placement",
        "their_limit": "They own the relationship and the upside",
        "their_missing": ["No radio promotion", "No tour/booking tools",
                          "No catalog control"],
        "our_equivalent": "Label Launchpad ($79.99/mo)",
        "why_better": "Flat-fee sync pitching to 15 supervisors. You keep your masters, your relationships, and 100% of placement fees.",
    },
    "vs_diy_stack": {
        "competitor": "DIY SaaS Stack",
        "their_price": "$80–$200/mo across 4–5 tools",
        "their_limit": "Chart trackers, mailing lists, and spreadsheets that don't talk to each other",
        "their_missing": ["No integrated promotion engine", "No booking database",
                          "No press wire"],
        "our_equivalent": "Artist Pro ($29.99/mo) or Label Launchpad ($79.99/mo)",
        "why_better": "One OS: promotion, press, sync, booking, royalties, and catalog in a single database with one dashboard.",
    },
    "vs_tour_software": {
        "competitor": "Tour Routing Software",
        "their_price": "$30–$50/mo per seat",
        "their_limit": "Routing only — no promotion, no booking outreach",
        "their_missing": ["No radio campaigns", "No sync pitching",
                          "No EPK generation", "No contract drafting"],
        "our_equivalent": "Label Launchpad ($79.99/mo)",
        "why_better": "Routing engine plus 60+ markets of venue/church targets, contract generation, and the promo engines that fill the rooms.",
    },
}

MARKETING_MESSAGES = [
    {
        "headline": "From Abilene to the World.",
        "body": "Redemption Road Music Group runs on SoundScape Pilot — the label OS that goes from song registration to sync placement in one pipeline.",
        "audience": "General",
    },
    {
        "headline": "12,000 Songs. One Pipeline.",
        "body": "AI music catalog? We handle it at scale. Catalog management, metadata QC, release coordination — per-song cost of one penny.",
        "audience": "AI Music Creators",
    },
    {
        "headline": "Radio. Playlists. Sync. Venues.",
        "body": "Most tools stop at storage. We pitch your music to 500+ radio stations, 9 streaming platforms, and 15 music supervisors — automatically.",
        "audience": "Independent Artists",
    },
    {
        "headline": "Major-Label Tools. Independent Price.",
        "body": "Everything Sony, Universal, and Warner use — radio promotion, tour routing, sync licensing, press, and booking — for $79.99/month.",
        "audience": "Independent Labels",
    },
    {
        "headline": "Your Music. Our Pipeline. Their Playlists.",
        "body": "Artist Pro: $29.99/month runs radio campaigns, streaming pitching, press, and EPKs while you stay focused on the music.",
        "audience": "Artists",
    },
    {
        "headline": "The Label OS That Works While You Sleep.",
        "body": "AI-powered radio promotion. Automated streaming pitching. Self-driving tour routing. Redemption Road never stops working for your music.",
        "audience": "Labels & Managers",
    },
    {
        "headline": "Not Just Storage. Amplification.",
        "body": "Cloud folders hold files. We deliver radio spins, playlist adds, sync placements, and tour dates. Real results.",
        "audience": "Artists",
    },
    {
        "headline": "Built in Texas. Ready for the World.",
        "body": "Redemption Road Music Group — the independent label with infrastructure that competes with the majors.",
        "audience": "General",
    },
    {
        "headline": "AI Songs Welcome Here.",
        "body": "We don't gatekeep. AI music, human music, hybrid — if it's good, it gets promoted, pitched, and booked like anything else.",
        "audience": "AI Music Producers",
    },
    {
        "headline": "From Demo to Campaign in an Hour.",
        "body": "Load your track and metadata, and the OS formats your release package, builds the press kit, and starts pitching radio — same day.",
        "audience": "Artists",
    },
]
