# Venue Finder Overhaul — SoundScape Pilot

## Objective
Expand the venue finder to equally surface small/medium/large venues and churches, add new data sources, church keyword handling, relevance ranking, Size/Type filters, richer result fields (address, type, capacity, inclusion reason), a Select All + checkbox flow for EPK dispatch, and verify with three live test queries. Large-venue coverage is preserved, not replaced.

## Audit summary (current behavior)
- There is NO Ticketmaster/SeatGeek/event API anywhere. Actual sources today: (1) Wikipedia MediaWiki category crawl (state-level only), (2) OpenStreetMap Overpass — churches ONLY, and ONLY when the genre string contains christian/church/gospel/worship/faith/spiritual/religious, (3) ~100 curated venues (mostly large/medium rooms).
- Gaps causing the reported symptoms:
  - No small/medium sources: no bars, pubs, lounges, cafes, listening rooms, honky-tonks, civic centers, outdoor stages, fairgrounds anywhere in the pipeline.
  - Churches gated behind genre keyword match; OSM church query is state-wide capped at 300 elements, often returning nothing useful for a city search; UI "Churches" checkbox appends " church" to genre but city targeting does not exist.
  - Dead branch in `_search_wikipedia_venues` (booking_agent.py:491-492): genre-specific categories are collected but never crawled (`md = 0`).
  - No capacity extraction from Wikipedia; OSM results hardcode `capacity: 0`.
  - No free-text query — UI only has State + Genre, so "near Abilene TX" style searches are impossible.
  - `/api/booking/search` never persists results; `/api/booking/dispatch` reads an always-empty `venues` table → dispatch always fails.
  - No Size/Type filters, no per-result selection, no address/type/reason fields returned.

## Decisions (confirmed with user)
- Google Places: OPTIONAL provider — auto-activates when `GOOGLE_PLACES_API_KEY` is set in `backend.env`; gracefully skipped when absent. Keyless path (OSM + Nominatim + Wikipedia + curated) is the default and must fully work on its own.
- Facebook Events: SKIPPED (no public API; scraping is brittle/ToS-risky). Gap covered by OSM/Nominatim/Google Places.
- Select All: per-result checkboxes + "Select All / Clear" + selected count; "Send EPKs" dispatches ONLY to selected venues (dispatch endpoint accepts an explicit venue list; also persists search results so the old flow stops being a dead end).

## Design

### 1. Query model (booking_agent.py)
`search_venues(state=None, genre=None, include_churches=False, query=None, size_filter="all", type_filter="all", lat=None, lon=None)`

Free-text `query` parsing (all new logic, existing params kept working):
- Location extraction: patterns "near <City> [ST]", "in <City>, [ST]", "<City>, [ST]", "<City> [ST]" at end; state via existing `US_STATES`/`_STATE_ABBR` maps. Extracted city+state override the State field for provider targeting.
- Geocoding: new `_geocode_location(city, state)` → (lat, lon, bbox) via Nominatim (`nominatim.openstreetmap.org`, 1 req, in-process cache, proper User-Agent, 1s courtesy). "near me" → use `lat`/`lon` passed from browser geolocation; if absent, fall back to state-level.
- Intent keywords:
  - CHURCH_KEYWORDS = church, churches, worship, gospel, christian, catholic, baptist, methodist, lutheran, presbyterian, episcopal, pentecostal, "assembly of god", "non-denominational", cathedral, chapel, ministry, sanctuary, revival → sets `church_intent` (runs church providers AND boosts/sorts churches to top).
  - Genre keywords (country, rock, jazz, ...) keep feeding existing Wikipedia GENRE_CATEGORIES/LIST_PAGES matching; add "honky-tonk"/"honky tonk" and "listening room" handling.
  - Size words ("small", "intimate", "dive") vs ("large", "arena") only bias ranking — NEVER filter results out.
- `include_churches` checkbox remains and forces church_intent on.

### 2. Providers (all merged; NOTHING is excluded by size/popularity/event-count)
| Provider | Covers | Changes |
|---|---|---|
| Curated (existing) | large+medium anchors | keep as-is; add a modest set of small/medium + church entries for TX (Abilene-area bars/listening rooms/churches) to guarantee offline/city results |
| Wikipedia (existing, expanded) | theaters, halls, churches, genre rooms | (a) crawl genre categories for real (fix dead `md=0` branch, max_depth 2); (b) city-level crawl: `Category:Music venues in {State}` subcats (e.g. "Music venues in Lubbock, Texas") + `Category:Churches in {State} by populated place` when a city is known; (c) denomination categories incl. Baptist/Methodist/Catholic/Episcopal/Lutheran/Presbyterian/Evangelical/Megachurches in {State}; (d) extract capacity from intro extracts via regex (seats/seating/capacity "holds X", "seats X"); (e) church pages get venue_type=church |
| OSM Overpass (existing, expanded) | THE small/medium + church source | from churches-only to full venue taxonomy (see tags below); location-aware: `around:` query at geocoded coords (radius ~15-25km) or bbox, else state area; read `capacity`, `addr:*`, `website`, `phone`, `denomination`; more mirrors + retry/backoff + per-query cache; church query no longer gated on genre string — runs whenever church_intent OR include_churches |
| Nominatim (new) | geocoding "near Abilene TX" / "near me" | 1 request per search, cached |
| Google Places (new, optional) | small/medium venues + churches with addresses/ratings | Text Search + Nearby Search; types: bar, church, cafe, nightclub, concert_hall, event_venue, museum? no — stick to: bar, church, cafe, nightclub, concert_hall, event_venue; searches: "live music venue", "bar with live music", "church", "honky tonk", "listening room" within result radius; requires GOOGLE_PLACES_API_KEY; skipped silently without key |

OSM tags queried (single or two Overpass calls per search):
- Venues: `amenity` in (bar, pub, music_venue, nightclub, theatre, arts_centre, community_centre, event_venue, cafe, amphitheatre, biergarten, casino), `leisure=bandstand`, `shop=music` skipped, `tourism=hostel` skipped.
- Churches: `amenity=place_of_worship` + `religion=christian` (denomination tag captured for reason text).
- Cafe included (user asked for coffee shops) but ranked below bars/music venues on general queries so results stay balanced.

### 3. Classification (every result gets these)
- `venue_type`: church | bar | club | theater | cafe | outdoor | civic | listening_room | other
  - Mapping: OSM amenity bar/pub→bar, nightclub→club, theatre→theater, arts_centre/community_centre→civic, cafe→cafe, amphitheatre/bandstand→outdoor; place_of_worship→church; name/category keywords: "listening room"/"listening hall"→listening_room, "honky"→bar (honky-tonk), "amphitheater/outdoor/stage/pavilion/bandstand/fairground"→outdoor, "cathedral/chapel/ministry/tabernacle"→church, "arena/stadium/coliseum"→theater? NO — arena/stadium/coliseum→other-but-large… keep type "theater" only for performing arts; arena/stadium→`other` with large size_class (curated ones keep working as before).
- `size_class`: small (<500), medium (500–1500), large (>1500), unknown→estimated from type (bar/cafe/listening_room→small; theater/music_venue/civic/church→medium; arena/stadium/amphitheatre→large) and flagged `capacity_estimate: true`.
- `capacity`: int when known (curated, OSM capacity tag, Wikipedia extract), else null with estimated size_class.
- `address`: composed from OSM `addr:housenumber/street/city/postcode`; else "City, ST"; else Nominatim display_name region.
- `reason`: human-readable inclusion string, e.g. "OpenStreetMap: bar in Abilene, TX (small, live-music venue type)", "Wikipedia: Baptist churches in Texas category match (church query)", "Curated country target — capacity 500", "Google Places: church near Abilene".

### 4. Ranking (ordering only — zero exclusions)
- church_intent=True → all church results sorted first (score +100), then non-church.
- General query → deterministic interleave (round-robin over size_class buckets small/medium/large/church) so page one is a balanced mix.
- Country intent → boost honky-tonk/country-named venues within their bucket.
- City known → prefer venues with city match / coords nearer to geocoded point.
- Stable sort; no min-capacity, min-followers, or upcoming-event requirements anywhere (there were none in code — keep it that way; spec's 200–2000 filter is explicitly NOT implemented).

### 5. Response schema (per venue)
`{name, address, city, state, venue_type, capacity, size_class, capacity_estimate, contact, website, source, reason, latitude, longitude}`
(`contact` keeps the existing derived-email behavior for compatibility.)

### 6. API changes (server.py:169-185)
- `BookingSearchRequest` += `query: Optional[str]`, `size: Optional[str]` (all|small|medium|large), `type: Optional[str]`, `lat: Optional[float]`, `lon: Optional[float]`.
- Keep include_churches/genre behavior (backward compatible with current UI).
- Server-side Size/Type filtering is applied AFTER ranking (filters narrow display, they are not discovery gates); "All" passes everything.
- Search now persists results via `db.insert_venue` (existing dead code) so `/api/booking/dispatch` stops being a dead end.
- `/api/booking/dispatch` accepts optional `venues: [..]` list (the user's selected rows); falls back to DB rows when absent.

### 7. UI changes (static/index.html:516-541, 1444-1495)
- New "Query" input (placeholder: `e.g. small country venues near Abilene TX`) next to existing State/Genre fields; Churches checkbox kept.
- New selects: Size [All sizes | Small (<500) | Medium (500–1500) | Large (1500+)], Type [All types | Bar | Church | Theater | Outdoor | Club | Cafe | Civic | Listening Room | Other].
- "Use my location" (auto-attempt navigator.geolocation on search; passes lat/lon; silent fallback to state) — powers "near me".
- Results list: per-row checkbox, type badge, size/capacity badge ("~est." when estimated), address line, reason line (muted), source badge.
- Results header: "N venues · M selected" + **Select All** + **Clear** buttons.
- "Send EPKs" button enabled when ≥1 venue selected; posts selected venue objects to /api/booking/dispatch. Log panel shows selection count and dispatch result.

### 8. Files touched
1. `SoundScapePilot/modules/booking_agent.py` — providers, parsing, classification, ranking (main work).
2. `SoundScapePilot/server.py` — request/response/dispatch endpoint changes.
3. `SoundScapePilot/static/index.html` — booking module UI + JS.
4. `SoundScapePilot/backend.env.example` — add optional `GOOGLE_PLACES_API_KEY=`.
5. `SoundScapePilot/modules/database.py` — only if insert_venue needs a tweak (it exists; likely no change).
NOT touched: `T7/` prototypes, `dist/`, `build/`, `T7/msi_src/` (stale copies; source of truth is SoundScapePilot/).

### 9. Verification (live tests, results shown to user)
Run the actual agent (python -c / small runner script against modules.booking_agent) with:
1. `query="small country venues near Abilene TX"` → expect TX country/honky-tonk + small bars/listening rooms in/near Abilene, size mix, each with type/capacity/reason.
2. `query="churches that host concerts near Abilene TX"` → expect churches (OSM place_of_worship near Abilene + Wikipedia TX church categories) ALL tagged venue_type=church, sorted to top.
3. `query="Christian music venues near me"` (simulate near-me with Abilene coords 32.4536,-99.7311) → expect church-first mix + Christian-friendly music venues.
Also verify: general query returns balanced small/medium/large/church; old params (state+genre, include_churches) still return previous large venues (e.g. Billy Bob's, ACL Live); server starts; UI renders filters/Select All. Note: Overpass public mirrors are congested at times (verified from this machine: overpass-api.de timeouts, fr instance 403) — code retries across 5 mirrors and degrades to Wikipedia/Nominatim/curated gracefully; tests will surface whichever sources are live.

### 10. Out of scope (flagged, not fixed)
- Missing `modules/booking_manager.py` / `tour_manager.py` breaking /api/tour/* and /api/booking/venue-fit endpoints (pre-existing; separate task).
- Updating stale copies under T7/, dist/, build/.
- Real contact discovery (emails remain derived placeholders except curated entries).
