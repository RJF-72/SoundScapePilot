import re
import time
import httpx
from typing import List, Dict, Any, Set, Optional

from modules.mailer import DEFAULT_DOMAIN

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_BASE = "https://en.wikipedia.org"

US_STATES_LIST = [
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut","Delaware",
    "Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky",
    "Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota","Mississippi","Missouri",
    "Montana","Nebraska","Nevada","New Hampshire","New Jersey","New Mexico","New York",
    "North Carolina","North Dakota","Ohio","Oklahoma","Oregon","Pennsylvania","Rhode Island",
    "South Carolina","South Dakota","Tennessee","Texas","Utah","Vermont","Virginia",
    "Washington","West Virginia","Wisconsin","Wyoming"
]

# Topic -> list of Wikipedia list-page titles to search/parse
LIST_PAGE_MAP = {
    "christian": [
        "List of Christian radio stations in the United States",
        "List of Christian newspapers",
        "List of Christian magazines",
        "List of gospel musicians",
        "List of Christian music festivals",
    ],
    "gospel": [
        "List of gospel musicians",
        "List of gospel music festivals",
        "Gospel music",
    ],
    "music": [
        "List of music magazines",
        "List of music websites",
        "List of music journalists",
        "List of American music critics",
        "List of music blogs",
        "List of record labels",
    ],
    "album": [
        "List of music magazines",
        "List of music websites",
        "List of music journalists",
        "List of album review websites",
    ],
    "tour": [
        "List of concert tours",
        "List of music venues",
        "List of festival line-ups",
    ],
    "radio": [
        "List of radio stations in the United States",
    ],
    "newspaper": [
        "List of newspapers in the United States",
    ],
    "magazine": [
        "List of magazines in the United States",
    ],
    "television": [
        "List of television stations in the United States",
    ],
}

STATE_LIST_PAGES = [
    "List of newspapers in {state}",
    "List of radio stations in {state}",
    "List of television stations in {state}",
]


class PRWire:
    def __init__(self):
        self._last_req = 0.0
        self.client = httpx.Client(timeout=12.0, headers={
            "User-Agent": "TITAN7-PRWire/1.0 (Music Industry Research)",
            "Accept-Language": "en-US,en;q=0.9"
        }, follow_redirects=True)

    def _rate_limit(self):
        elapsed = time.time() - self._last_req
        if elapsed < 0.25:
            time.sleep(0.25 - elapsed)
        self._last_req = time.time()

    def _wiki_get(self, params: dict) -> dict:
        for attempt in range(2):
            self._rate_limit()
            try:
                r = self.client.get(WIKI_API, params=params, timeout=10.0)
                if r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                return r.json() if r.status_code == 200 else {}
            except Exception:
                return {}
        return {}

    def _extract_state(self, topic: str) -> str:
        tl = topic.lower()
        for s in US_STATES_LIST:
            if s.lower() in tl:
                return s
        abbr_map = {
            "al":"Alabama","ak":"Alaska","az":"Arizona","ar":"Arkansas","ca":"California",
            "co":"Colorado","ct":"Connecticut","de":"Delaware","fl":"Florida","ga":"Georgia",
            "hi":"Hawaii","id":"Idaho","il":"Illinois","in":"Indiana","ia":"Iowa","ks":"Kansas",
            "ky":"Kentucky","la":"Louisiana","me":"Maine","md":"Maryland","ma":"Massachusetts",
            "mi":"Michigan","mn":"Minnesota","ms":"Mississippi","mo":"Missouri","mt":"Montana",
            "ne":"Nebraska","nv":"Nevada","nh":"New Hampshire","nj":"New Jersey","nm":"New Mexico",
            "ny":"New York","nc":"North Carolina","nd":"North Dakota","oh":"Ohio","ok":"Oklahoma",
            "or":"Oregon","pa":"Pennsylvania","ri":"Rhode Island","sc":"South Carolina",
            "sd":"South Dakota","tn":"Tennessee","tx":"Texas","ut":"Utah","vt":"Vermont",
            "va":"Virginia","wa":"Washington","wv":"West Virginia","wi":"Wisconsin","wy":"Wyoming",
        }
        for w in re.findall(r'\b[a-z]{2}\b', tl):
            if w in abbr_map:
                return abbr_map[w]
        return ""

    def _detect_topics(self, topic: str) -> list:
        tl = topic.lower()
        matched = []
        for key in LIST_PAGE_MAP:
            if key in tl:
                matched.append(key)
        return matched

    def _search_general_list(self, topic: str) -> List[str]:
        search_queries = [
            f"List of {topic} magazines",
            f"List of {topic} publications",
            f"List of {topic} websites",
            f"List of {topic} blogs",
            f"List of {topic} outlets",
        ]
        found = []
        seen_q = set()
        for q in search_queries:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": q,
                "srlimit": 3,
                "format": "json",
            }
            data = self._wiki_get(params)
            if data:
                for r in data.get("query", {}).get("search", []):
                    title = r["title"]
                    if title not in seen_q and "List of" in title:
                        seen_q.add(title)
                        found.append(title)
        return found

    def _search_wikipedia_list_pages(self, topic: str) -> List[Dict[str, Any]]:
        state = self._extract_state(topic)
        detected = self._detect_topics(topic)
        seen: Set[str] = set()
        outlets = []
        deadline = time.time() + 30.0

        pages_to_fetch = []

        for d in detected:
            for p in LIST_PAGE_MAP.get(d, []):
                if p not in seen:
                    seen.add(p)
                    pages_to_fetch.append(p)

        for template in STATE_LIST_PAGES:
            target = template.replace("{state}", state) if state else template.replace("{state}", "United States")
            if target not in seen:
                seen.add(target)
                pages_to_fetch.append(target)

        if not detected and not state:
            general_pages = self._search_general_list(topic)
            for p in general_pages:
                if p not in seen:
                    seen.add(p)
                    pages_to_fetch.append(p)

        for page_title in pages_to_fetch:
            if time.time() > deadline:
                break
            try:
                parsed = self._parse_list_page(page_title)
                for o in parsed:
                    if o["name"] not in seen:
                        seen.add(o["name"])
                        outlets.append(o)
            except Exception:
                pass

        return outlets

    def _parse_list_page(self, page_title: str) -> List[Dict[str, Any]]:
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json",
            "redirects": "1",
        }
        data = self._wiki_get(params)
        if not data or "parse" not in data:
            return []

        html = data["parse"].get("text", {}).get("*", "")
        if not html:
            return []

        outlets = []
        tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
        for table in tables:
            rows = re.findall(r'<tr>(.*?)</tr>', table, re.DOTALL)
            for row in rows[1:]:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if not cells:
                    continue
                name_cell = cells[0]
                name_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', name_cell)
                if name_match:
                    name = name_match.group(2).strip()
                    rel_path = name_match.group(1)
                    website = f"{WIKI_BASE}{rel_path}" if rel_path.startswith("/") else rel_path
                    location = ""
                    for cell in cells[1:4]:
                        text = re.sub(r'<[^>]+>', '', cell).strip()
                        if text and len(text) < 100:
                            location = text
                            break
                    outlets.append({
                        "name": name,
                        "tier": "Wikipedia",
                        "contact": self._wiki_page_to_contact(rel_path),
                        "website": website,
                        "location": location,
                        "source": "Wikipedia"
                    })

        if not outlets:
            list_items = re.findall(r'<li>(.*?)</li>', html, re.DOTALL)
            for item in list_items:
                link = re.search(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', item)
                if link:
                    name = link.group(2).strip()
                    if "List of" in name or "Category:" in name:
                        continue
                    rel_path = link.group(1)
                    website = f"{WIKI_BASE}{rel_path}" if rel_path.startswith("/") else rel_path
                    outlets.append({
                        "name": name,
                        "tier": "Wikipedia",
                        "contact": self._wiki_page_to_contact(rel_path),
                        "website": website,
                        "location": "",
                        "source": "Wikipedia"
                    })

        return outlets

    def _wiki_page_to_contact(self, rel_path: str) -> str:
        page_title = rel_path.replace("/wiki/", "").replace("_", " ")
        page_title = re.sub(r'[^a-zA-Z0-9 ]', '', page_title)
        slug = page_title.lower().replace(" ", "")
        if not slug:
            return ""
        domain = re.sub(r'[^a-z0-9]', '', slug)
        if domain:
            return f"newsroom@{domain}.com"
        return ""

    # ----------------------------------------------------------------
    # CURATED MEDIA DATABASE - expanded to be aggressive and self-sufficient
    # ----------------------------------------------------------------
    MEDIA_DB = {
        "debut album": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "Bloomberg", "tier": "Major", "contact": "tips@bloomberg.net", "website": "https://bloomberg.com"},
            {"name": "Pitchfork", "tier": "Major", "contact": "music@pitchfork.com", "website": "https://pitchfork.com"},
            {"name": "Stereogum", "tier": "Major", "contact": "tips@stereogum.com", "website": "https://stereogum.com"},
            {"name": "Consequence of Sound", "tier": "Major", "contact": "tips@consequence.net", "website": "https://consequence.net"},
            {"name": "Brooklyn Vegan", "tier": "Niche", "contact": "tips@brooklynvegan.com", "website": "https://brooklynvegan.com"},
            {"name": "The Fader", "tier": "Major", "contact": "tips@thefader.com", "website": "https://thefader.com"},
            {"name": "Spin", "tier": "Major", "contact": "pitches@spin.com", "website": "https://spin.com"},
            {"name": "NME", "tier": "Major", "contact": "news@nme.com", "website": "https://nme.com"},
            {"name": "Under The Radar", "tier": "Niche", "contact": "press@undertheradar.com", "website": "https://undertheradarmag.com"},
            {"name": "Clash Magazine", "tier": "Major", "contact": "info@clashmusic.com", "website": "https://clashmusic.com"},
            {"name": "The Line of Best Fit", "tier": "Niche", "contact": "tips@thelineofbestfit.com", "website": "https://thelineofbestfit.com"},
            {"name": "Austin Chronicle", "tier": "Local", "contact": "music@austinchronicle.com", "website": "https://austinchronicle.com"},
            {"name": "Nashville Scene", "tier": "Local", "contact": "music@nashvillescene.com", "website": "https://nashvillescene.com"},
            {"name": "Treble", "tier": "Niche", "contact": "contact@treblezine.com", "website": "https://treblezine.com"},
            {"name": "PopMatters", "tier": "Niche", "contact": "editors@popmatters.com", "website": "https://popmatters.com"},
            {"name": "Beats Per Minute", "tier": "Niche", "contact": "tips@beatsperminute.com", "website": "https://beatsperminute.com"},
            {"name": "The Quietus", "tier": "Niche", "contact": "news@thequietus.com", "website": "https://thequietus.com"},
            {"name": "Drowned In Sound", "tier": "Niche", "contact": "tips@drownedinsound.com", "website": "https://drownedinsound.com"},
            {"name": "Gorilla Vs. Bear", "tier": "Niche", "contact": "tips@gorillavsbear.com", "website": "https://gorillavsbear.com"},
            {"name": "Aquarium Drunkard", "tier": "Niche", "contact": "ad@aquariumdrunkard.com", "website": "https://aquariumdrunkard.com"},
            {"name": "Paste Magazine", "tier": "Major", "contact": "editor@pastemagazine.com", "website": "https://pastemagazine.com"},
            {"name": "Uproxx Music", "tier": "Major", "contact": "tips@uproxx.com", "website": "https://uproxx.com/music"},
            {"name": "Alternative Press", "tier": "Major", "contact": "submissions@altpress.com", "website": "https://altpress.com"},
            {"name": "Kerrang!", "tier": "Major", "contact": "news@kerrang.com", "website": "https://kerrang.com"},
            {"name": "Louder Sound", "tier": "Major", "contact": "news@loudersound.com", "website": "https://loudersound.com"},
            {"name": "DIY Magazine", "tier": "Niche", "contact": "news@diymag.com", "website": "https://diymag.com"},
            {"name": "The 405", "tier": "Niche", "contact": "contact@thefourohfive.com", "website": "https://thefourohfive.com"},
            {"name": "GoldFlakePaint", "tier": "Niche", "contact": "contact@goldflakepaint.co.uk", "website": "https://goldflakepaint.co.uk"},
        ],
        "tour": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "Pollstar", "tier": "Industry", "contact": "news@pollstar.com", "website": "https://pollstar.com"},
            {"name": "Rolling Stone", "tier": "Major", "contact": "tips@rollingstone.com", "website": "https://rollingstone.com"},
            {"name": "Billboard", "tier": "Major", "contact": "news@billboard.com", "website": "https://billboard.com"},
            {"name": "JamBase", "tier": "Niche", "contact": "news@jambase.com", "website": "https://jambase.com"},
            {"name": "Live Nation", "tier": "Industry", "contact": "media@livenation.com", "website": "https://livenation.com"},
            {"name": "Songkick", "tier": "Industry", "contact": "press@songkick.com", "website": "https://songkick.com"},
            {"name": "Bandsintown", "tier": "Industry", "contact": "partners@bandsintown.com", "website": "https://bandsintown.com"},
            {"name": "Relix", "tier": "Niche", "contact": "editor@relix.com", "website": "https://relix.com"},
            {"name": "Grateful Web", "tier": "Niche", "contact": "info@gratefulweb.com", "website": "https://gratefulweb.com"},
            {"name": "No Depression", "tier": "Niche", "contact": "info@nodepression.com", "website": "https://nodepression.com"},
            {"name": "JamBands.com", "tier": "Niche", "contact": "news@jambands.com", "website": "https://jambands.com"},
            {"name": "Glide Magazine", "tier": "Niche", "contact": "contact@glidemagazine.com", "website": "https://glidemagazine.com"},
            {"name": "Live For Live Music", "tier": "Niche", "contact": "news@liveforlivemusic.com", "website": "https://liveforlivemusic.com"},
        ],
        "single": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "Spotify Editorial", "tier": "Platform", "contact": "editorial@spotify.com", "website": "https://artists.spotify.com"},
            {"name": "Apple Music Editorial", "tier": "Platform", "contact": "editorial@apple.com", "website": "https://music.apple.com"},
            {"name": "SoundCloud Playlists", "tier": "Platform", "contact": "curation@soundcloud.com", "website": "https://soundcloud.com"},
            {"name": "Hype Machine", "tier": "Niche", "contact": "submit@hypem.com", "website": "https://hypem.com"},
            {"name": "Indie Shuffle", "tier": "Niche", "contact": "contact@indieshuffle.com", "website": "https://indieshuffle.com"},
            {"name": "Earmilk", "tier": "Niche", "contact": "submissions@earmilk.com", "website": "https://earmilk.com"},
            {"name": "This Song Is Sick", "tier": "Niche", "contact": "submissions@thissongissick.com", "website": "https://thissongissick.com"},
            {"name": "Pigeons & Planes", "tier": "Niche", "contact": "tips@pigeonsandplanes.com", "website": "https://pigeonsandplanes.com"},
            {"name": "Complex Music", "tier": "Major", "contact": "tips@complex.com", "website": "https://complex.com/music"},
        ],
        "music video": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "MTV News", "tier": "Major", "contact": "mtvnews@mtv.com", "website": "https://mtv.com"},
            {"name": "YouTube Music", "tier": "Platform", "contact": "music@youtube.com", "website": "https://music.youtube.com"},
            {"name": "Vevo", "tier": "Platform", "contact": "artists@vevo.com", "website": "https://vevo.com"},
            {"name": "Paste Magazine", "tier": "Major", "contact": "editor@pastemagazine.com", "website": "https://pastemagazine.com"},
            {"name": "Audiography", "tier": "Niche", "contact": "submit@audiography.com", "website": "https://audiography.com"},
        ],
        "festival": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "Pollstar", "tier": "Industry", "contact": "news@pollstar.com", "website": "https://pollstar.com"},
            {"name": "Festival Owl", "tier": "Niche", "contact": "info@festivalowl.com", "website": "https://festivalowl.com"},
            {"name": "Festicket", "tier": "Industry", "contact": "partners@festicket.com", "website": "https://festicket.com"},
            {"name": "Billboard", "tier": "Major", "contact": "festivals@billboard.com", "website": "https://billboard.com"},
            {"name": "Consequence of Sound", "tier": "Major", "contact": "festivals@consequence.net", "website": "https://consequence.net"},
            {"name": "Music Festival Wizard", "tier": "Niche", "contact": "tips@musicfestivalwizard.com", "website": "https://musicfestivalwizard.com"},
        ],
        "hip hop": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "XXL", "tier": "Major", "contact": "xxl@xxlmag.com", "website": "https://xxlmag.com"},
            {"name": "Complex", "tier": "Major", "contact": "tips@complex.com", "website": "https://complex.com"},
            {"name": "Hypebeast", "tier": "Major", "contact": "music@hypebeast.com", "website": "https://hypebeast.com"},
            {"name": "HotNewHipHop", "tier": "Major", "contact": "tips@hotnewhiphop.com", "website": "https://hotnewhiphop.com"},
            {"name": "DJ Booth", "tier": "Niche", "contact": "submissions@djbooth.net", "website": "https://djbooth.net"},
            {"name": "Rap Radar", "tier": "Niche", "contact": "tips@rapradar.com", "website": "https://rapradar.com"},
            {"name": "2DOPEBOYZ", "tier": "Niche", "contact": "tips@2dopeboyz.com", "website": "https://2dopeboyz.com"},
            {"name": "Lyrical Lemonade", "tier": "Niche", "contact": "submissions@lyricallemonade.com", "website": "https://lyricallemonade.com"},
        ],
        "country": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Reuters", "tier": "Major", "contact": "newsroom@reuters.com", "website": "https://reuters.com"},
            {"name": "Rolling Stone Country", "tier": "Major", "contact": "country@rollingstone.com", "website": "https://rollingstone.com/country"},
            {"name": "Taste of Country", "tier": "Major", "contact": "tips@tasteofcountry.com", "website": "https://tasteofcountry.com"},
            {"name": "The Boot", "tier": "Niche", "contact": "tips@theboot.com", "website": "https://theboot.com"},
            {"name": "Country Music News", "tier": "Industry", "contact": "editor@countrymusicnews.com", "website": "https://countrymusicnews.com"},
            {"name": "No Depression", "tier": "Niche", "contact": "info@nodepression.com", "website": "https://nodepression.com"},
            {"name": "Texas Music", "tier": "Local", "contact": "editor@texasmusic.com", "website": "https://texasmusic.com"},
            {"name": "CMT News", "tier": "Major", "contact": "news@cmt.com", "website": "https://cmt.com"},
        ],
        "christian": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Gospel Today", "tier": "Major", "contact": "editor@gospeltoday.com", "website": "https://gospeltoday.com"},
            {"name": "CCM Magazine", "tier": "Industry", "contact": "editor@ccmmagazine.com", "website": "https://ccmmagazine.com"},
            {"name": "Christian Music Weekly", "tier": "Industry", "contact": "news@christianmusicweekly.com", "website": "https://christianmusicweekly.com"},
            {"name": "The Christian Beat", "tier": "Niche", "contact": "tips@thechristianbeat.com", "website": "https://thechristianbeat.com"},
            {"name": "Jesus Rock Magazine", "tier": "Niche", "contact": "info@jesusrockmag.com", "website": "https://jesusrockmag.com"},
            {"name": "Gospel Music Association", "tier": "Industry", "contact": "press@gospelmusic.org", "website": "https://gospelmusic.org"},
            {"name": "BreatheCast", "tier": "Niche", "contact": "music@breathecast.com", "website": "https://breathecast.com"},
            {"name": "NewReleaseToday", "tier": "Niche", "contact": "submissions@newreleasetoday.com", "website": "https://newreleasetoday.com"},
        ],
        "general": [
            {"name": "Associated Press", "tier": "Major", "contact": "apnews@ap.org", "website": "https://apnews.com"},
            {"name": "Pitchfork", "tier": "Major", "contact": "music@pitchfork.com", "website": "https://pitchfork.com"},
            {"name": "Stereogum", "tier": "Major", "contact": "tips@stereogum.com", "website": "https://stereogum.com"},
            {"name": "Rolling Stone", "tier": "Major", "contact": "tips@rollingstone.com", "website": "https://rollingstone.com"},
            {"name": "Billboard", "tier": "Major", "contact": "news@billboard.com", "website": "https://billboard.com"},
            {"name": "Spin", "tier": "Major", "contact": "pitches@spin.com", "website": "https://spin.com"},
            {"name": "NME", "tier": "Major", "contact": "news@nme.com", "website": "https://nme.com"},
            {"name": "Consequence of Sound", "tier": "Major", "contact": "tips@consequence.net", "website": "https://consequence.net"},
            {"name": "The Fader", "tier": "Major", "contact": "tips@thefader.com", "website": "https://thefader.com"},
            {"name": "Brooklyn Vegan", "tier": "Niche", "contact": "tips@brooklynvegan.com", "website": "https://brooklynvegan.com"},
            {"name": "PopMatters", "tier": "Niche", "contact": "editors@popmatters.com", "website": "https://popmatters.com"},
            {"name": "Austin Chronicle", "tier": "Local", "contact": "music@austinchronicle.com", "website": "https://austinchronicle.com"},
            {"name": "Treble", "tier": "Niche", "contact": "contact@treblezine.com", "website": "https://treblezine.com"},
            {"name": "Under The Radar", "tier": "Niche", "contact": "press@undertheradar.com", "website": "https://undertheradarmag.com"},
            {"name": "Clash Magazine", "tier": "Major", "contact": "info@clashmusic.com", "website": "https://clashmusic.com"},
            {"name": "The Quietus", "tier": "Niche", "contact": "news@thequietus.com", "website": "https://thequietus.com"},
            {"name": "KEXP Blog", "tier": "Niche", "contact": "blog@kexp.org", "website": "https://kexp.org/blog"},
            {"name": "KCRW Music", "tier": "Niche", "contact": "music@kcrw.org", "website": "https://kcrw.org/music"},
            {"name": "Paste Magazine", "tier": "Major", "contact": "editor@pastemagazine.com", "website": "https://pastemagazine.com"},
            {"name": "Uproxx Music", "tier": "Major", "contact": "tips@uproxx.com", "website": "https://uproxx.com/music"},
            {"name": "DIY Magazine", "tier": "Niche", "contact": "news@diymag.com", "website": "https://diymag.com"},
        ],
        "rock": [
            {"name": "Kerrang!", "tier": "Major", "contact": "news@kerrang.com", "website": "https://kerrang.com"},
            {"name": "Louder Sound", "tier": "Major", "contact": "news@loudersound.com", "website": "https://loudersound.com"},
            {"name": "Revolver", "tier": "Major", "contact": "editor@revolvermag.com", "website": "https://revolvermag.com"},
            {"name": "Metal Hammer", "tier": "Major", "contact": "news@metalhammer.com", "website": "https://metalhammer.com"},
            {"name": "Classic Rock Magazine", "tier": "Major", "contact": "news@classicrockteam.com", "website": "https://classicrockmagazine.com"},
            {"name": "The Rockpit", "tier": "Niche", "contact": "contact@therockpit.net", "website": "https://therockpit.net"},
        ],
        "metal": [
            {"name": "Blabbermouth", "tier": "Major", "contact": "news@blabbermouth.net", "website": "https://blabbermouth.net"},
            {"name": "Metal Injection", "tier": "Major", "contact": "news@metalinjection.net", "website": "https://metalinjection.net"},
            {"name": "MetalSucks", "tier": "Major", "contact": "tips@metalsucks.net", "website": "https://metalsucks.net"},
            {"name": "The PRP", "tier": "Niche", "contact": "news@theprp.com", "website": "https://theprp.com"},
            {"name": "Ghost Cult Magazine", "tier": "Niche", "contact": "editor@ghostcultmag.com", "website": "https://ghostcultmag.com"},
        ],
        "electronic": [
            {"name": "Resident Advisor", "tier": "Major", "contact": "news@residentadvisor.net", "website": "https://ra.co"},
            {"name": "Mixmag", "tier": "Major", "contact": "news@mixmag.net", "website": "https://mixmag.net"},
            {"name": "DJ Mag", "tier": "Major", "contact": "news@djmag.com", "website": "https://djmag.com"},
            {"name": "Beatportal", "tier": "Industry", "contact": "news@beatportal.com", "website": "https://beatportal.com"},
            {"name": "Electronic Groove", "tier": "Niche", "contact": "contact@electronicgroove.com", "website": "https://electronicgroove.com"},
            {"name": "Data Transmission", "tier": "Niche", "contact": "news@datatransmission.co.uk", "website": "https://datatransmission.co.uk"},
        ],
        "jazz": [
            {"name": "DownBeat", "tier": "Major", "contact": "editor@downbeat.com", "website": "https://downbeat.com"},
            {"name": "JazzTimes", "tier": "Major", "contact": "editor@jazztimes.com", "website": "https://jazztimes.com"},
            {"name": "Jazziz", "tier": "Major", "contact": "news@jazziz.com", "website": "https://jazziz.com"},
            {"name": "All About Jazz", "tier": "Niche", "contact": "news@allaboutjazz.com", "website": "https://allaboutjazz.com"},
            {"name": "London Jazz News", "tier": "Niche", "contact": "editor@londonjazznews.com", "website": "https://londonjazznews.com"},
        ],
        "blues": [
            {"name": "Blues Music Magazine", "tier": "Major", "contact": "editor@bluesmusicmag.com", "website": "https://bluesmusicmag.com"},
            {"name": "Living Blues", "tier": "Major", "contact": "editor@livingblues.com", "website": "https://livingblues.com"},
            {"name": "Blues Blast Magazine", "tier": "Niche", "contact": "editor@bluesblastmagazine.com", "website": "https://bluesblastmagazine.com"},
            {"name": "American Blues Scene", "tier": "Niche", "contact": "tips@americanbluesscene.com", "website": "https://americanbluesscene.com"},
        ],
        "rnb": [
            {"name": "Rated R&B", "tier": "Major", "contact": "tips@ratedrnb.com", "website": "https://ratedrnb.com"},
            {"name": "SoulBounce", "tier": "Major", "contact": "tips@soulbounce.com", "website": "https://soulbounce.com"},
            {"name": "ThisisRNB", "tier": "Niche", "contact": "submissions@thisisrnb.com", "website": "https://thisisrnb.com"},
            {"name": "YouKnowIGotSoul", "tier": "Niche", "contact": "contact@youknowigotsoul.com", "website": "https://youknowigotsoul.com"},
        ],
        "soul": [
            {"name": "Rated R&B", "tier": "Major", "contact": "tips@ratedrnb.com", "website": "https://ratedrnb.com"},
            {"name": "SoulBounce", "tier": "Major", "contact": "tips@soulbounce.com", "website": "https://soulbounce.com"},
            {"name": "The Soul of America", "tier": "Niche", "contact": "contact@soulofamerica.net", "website": "https://soulofamerica.net"},
        ],
        "reggae": [
            {"name": "ReggaeVille", "tier": "Major", "contact": "news@reggaeville.com", "website": "https://reggaeville.com"},
            {"name": "DancehallMag", "tier": "Major", "contact": "tips@dancehallmag.com", "website": "https://dancehallmag.com"},
            {"name": "United Reggae", "tier": "Niche", "contact": "contact@unitedreggae.com", "website": "https://unitedreggae.com"},
        ],
        "latin": [
            {"name": "Billboard Latin", "tier": "Major", "contact": "latin@billboard.com", "website": "https://billboard.com/latin"},
            {"name": "Remezcla", "tier": "Major", "contact": "tips@remezcla.com", "website": "https://remezcla.com"},
            {"name": "LatinTimes", "tier": "Niche", "contact": "tips@latintimes.com", "website": "https://latintimes.com"},
        ],
    }

    def get_outlets(self, topic: str) -> List[Dict[str, Any]]:
        tl = topic.lower()

        # 1. Always include curated data in the library.
        curated = []
        for key in self.MEDIA_DB:
            if key in tl:
                curated.extend(self.MEDIA_DB[key])
        if not curated:
            curated = list(self.MEDIA_DB["general"])

        # Deduplicate curated by name while preserving order.
        seen_curated = set()
        deduped = []
        for o in curated:
            if o["name"] not in seen_curated:
                seen_curated.add(o["name"])
                deduped.append(o)
        curated = deduped

        results = list(curated)  # start with curated

        # 2. Always try online discovery too.
        scraped = []
        try:
            scraped = self._search_wikipedia_list_pages(topic)
        except Exception:
            pass

        # 3. Merge — online overrides curated on name collision.
        seen: Set[str] = set()
        merged: List[Dict[str, Any]] = []
        for o in results:
            seen.add(o["name"])
            merged.append(o)
        for o in scraped:
            if o["name"] in seen:
                # Replace curated entry with online version
                merged = [x for x in merged if x["name"] != o["name"]]
            seen.add(o["name"])
            merged.append(o)
        return merged

    def craft_release(self, topic: str, artist_name: str = "TITAN 7 Artist",
                      quote: str = "") -> str:
        headline = f"FOR IMMEDIATE RELEASE: {artist_name} Announces {topic}"
        body = (
            f"{headline}\n\n"
            f"({artist_name}) — Today, {artist_name} announces {topic}, marking a significant milestone for the project.\n\n"
            f'"We are excited to share this with the world," says the artist. {quote if quote else "The release represents months of writing, recording, and collaboration."}\n\n'
            f"{topic} is available now across all major streaming platforms. For press inquiries, interview requests, or promotional assets, please contact the TITAN 7 press office.\n\n"
            f"###\n\n"
            f"Press Contact:\n"
            f"Paige\n"
            f"paige@{DEFAULT_DOMAIN}\n"
            f"TITAN 7 Publicity\n"
        )
        return body

    def distribute(self, topic: str) -> List[Dict[str, Any]]:
        return self.get_outlets(topic)
