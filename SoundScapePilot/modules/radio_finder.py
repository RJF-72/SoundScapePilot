import httpx
import asyncio
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup


RADIO_BROWSER_URL = "https://de1.api.radio-browser.info"
WIKI_API = "https://en.wikipedia.org/w/api.php"

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC"
}
STATE_ABBREVS = {v: k for k, v in US_STATES.items()}

# Curated high-value radio contacts so the autopilot ALWAYS has targets.
CURATED_STATIONS: Dict[str, List[Dict[str, Any]]] = {
    "rock": [
        {"station_name": "KEXP 90.3 FM", "vector": "FM Radio", "location": "Seattle, WA", "frequency": "90.3 FM", "contact": "dj@kexp.org", "website": "https://kexp.org", "match_score": 99},
        {"station_name": "KCRW 89.9 FM", "vector": "FM Radio", "location": "Santa Monica, CA", "frequency": "89.9 FM", "contact": "music@kcrw.org", "website": "https://kcrw.org", "match_score": 99},
        {"station_name": "SiriusXM Octane", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 37", "contact": "octane@siriusxm.com", "website": "https://siriusxm.com/octane", "match_score": 95},
        {"station_name": "WXPN 88.5 FM", "vector": "FM Radio", "location": "Philadelphia, PA", "frequency": "88.5 FM", "contact": "music@wxpn.org", "website": "https://wxpn.org", "match_score": 94},
        {"station_name": "KUTX 98.9 FM", "vector": "FM Radio", "location": "Austin, TX", "frequency": "98.9 FM", "contact": "music@kutx.org", "website": "https://kutx.org", "match_score": 92},
        {"station_name": "The Current 89.3 FM", "vector": "FM Radio", "location": "Minneapolis, MN", "frequency": "89.3 FM", "contact": "music@thecurrent.org", "website": "https://thecurrent.org", "match_score": 91},
        {"station_name": "KQED 88.5 FM", "vector": "FM Radio", "location": "San Francisco, CA", "frequency": "88.5 FM", "contact": "music@kqed.org", "website": "https://kqed.org", "match_score": 85},
        {"station_name": "KPSU College Radio", "vector": "College Radio", "location": "Portland, OR", "frequency": "1450 AM", "contact": "music@kpsu.org", "website": "https://kpsu.org", "match_score": 88},
        {"station_name": "WMUC 88.1 FM", "vector": "College Radio", "location": "College Park, MD", "frequency": "88.1 FM", "contact": "music@wmuc.umd.edu", "website": "https://wmuc.umd.edu", "match_score": 86},
        {"station_name": "KPSI Internet Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "submissions@kpsi.fm", "website": "https://kpsi.fm", "match_score": 80},
    ],
    "indie rock": [
        {"station_name": "KEXP 90.3 FM", "vector": "FM Radio", "location": "Seattle, WA", "frequency": "90.3 FM", "contact": "dj@kexp.org", "website": "https://kexp.org", "match_score": 99},
        {"station_name": "KCRW 89.9 FM", "vector": "FM Radio", "location": "Santa Monica, CA", "frequency": "89.9 FM", "contact": "music@kcrw.org", "website": "https://kcrw.org", "match_score": 99},
        {"station_name": "SiriusXMU", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 35", "contact": "siriusxmu@siriusxm.com", "website": "https://siriusxm.com/siriusxmu", "match_score": 94},
        {"station_name": "WXPN 88.5 FM", "vector": "FM Radio", "location": "Philadelphia, PA", "frequency": "88.5 FM", "contact": "music@wxpn.org", "website": "https://wxpn.org", "match_score": 95},
        {"station_name": "KUTX 98.9 FM", "vector": "FM Radio", "location": "Austin, TX", "frequency": "98.9 FM", "contact": "music@kutx.org", "website": "https://kutx.org", "match_score": 92},
        {"station_name": "WFUV 90.7 FM", "vector": "FM Radio", "location": "New York, NY", "frequency": "90.7 FM", "contact": "music@wfuv.org", "website": "https://wfuv.org", "match_score": 91},
    ],
    "hip hop": [
        {"station_name": "SiriusXM Shade 45", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 45", "contact": "shade45@siriusxm.com", "website": "https://siriusxm.com/shade45", "match_score": 99},
        {"station_name": "Hot 97", "vector": "FM Radio", "location": "New York, NY", "frequency": "97.1 FM", "contact": "music@hot97.com", "website": "https://hot97.com", "match_score": 97},
        {"station_name": "Power 106", "vector": "FM Radio", "location": "Los Angeles, CA", "frequency": "105.9 FM", "contact": "music@power106.com", "website": "https://power106.com", "match_score": 96},
        {"station_name": "WWPR 105.1 FM", "vector": "FM Radio", "location": "New York, NY", "frequency": "105.1 FM", "contact": "music@power1051.fm", "website": "https://power1051.fm", "match_score": 95},
        {"station_name": "KDAY 93.5 FM", "vector": "FM Radio", "location": "Los Angeles, CA", "frequency": "93.5 FM", "contact": "music@935kday.com", "website": "https://935kday.com", "match_score": 92},
    ],
    "country": [
        {"station_name": "SiriusXM The Highway", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 56", "contact": "thehighway@siriusxm.com", "website": "https://siriusxm.com/thehighway", "match_score": 99},
        {"station_name": "WSM 650 AM", "vector": "AM Radio", "location": "Nashville, TN", "frequency": "650 AM", "contact": "music@wsmradio.com", "website": "https://wsmradio.com", "match_score": 98},
        {"station_name": "KKBQ 92.9 FM", "vector": "FM Radio", "location": "Houston, TX", "frequency": "92.9 FM", "contact": "music@kkbq.com", "website": "https://kkbq.com", "match_score": 92},
        {"station_name": "WIVK 107.7 FM", "vector": "FM Radio", "location": "Knoxville, TN", "frequency": "107.7 FM", "contact": "music@wivk.com", "website": "https://wivk.com", "match_score": 90},
    ],
    "electronic": [
        {"station_name": "SiriusXM BPM", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 51", "contact": "bpm@siriusxm.com", "website": "https://siriusxm.com/bpm", "match_score": 98},
        {"station_name": "DI.FM", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "submissions@di.fm", "website": "https://di.fm", "match_score": 96},
        {"station_name": "KCRW 89.9 FM", "vector": "FM Radio", "location": "Santa Monica, CA", "frequency": "89.9 FM", "contact": "music@kcrw.org", "website": "https://kcrw.org", "match_score": 90},
    ],
    "jazz": [
        {"station_name": "WBGO 88.3 FM", "vector": "FM Radio", "location": "Newark, NJ", "frequency": "88.3 FM", "contact": "music@wbgo.org", "website": "https://wbgo.org", "match_score": 99},
        {"station_name": "KJAZZ 88.1 FM", "vector": "FM Radio", "location": "Long Beach, CA", "frequency": "88.1 FM", "contact": "music@kkjz.com", "website": "https://kkjz.com", "match_score": 97},
        {"station_name": "Jazz24.org", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "submissions@jazz24.org", "website": "https://jazz24.org", "match_score": 94},
    ],
    "metal": [
        {"station_name": "SiriusXM Liquid Metal", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 40", "contact": "liquidmetal@siriusxm.com", "website": "https://siriusxm.com/liquidmetal", "match_score": 99},
        {"station_name": "KNAC.COM", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "requests@knac.com", "website": "https://knac.com", "match_score": 94},
    ],
    "punk": [
        {"station_name": "SiriusXM Faction Punk", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 314", "contact": "factionpunk@siriusxm.com", "website": "https://siriusxm.com/factionpunk", "match_score": 97},
        {"station_name": "PunkRadioCast", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "submissions@punkradiocast.com", "website": "https://punkradiocast.com", "match_score": 90},
    ],
    "gospel": [
        {"station_name": "SiriusXM Kirk Franklin's Praise", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 64", "contact": "praise@siriusxm.com", "website": "https://siriusxm.com/praise", "match_score": 99},
        {"station_name": "WJOU 90.1 FM", "vector": "FM Radio", "location": "Huntsville, AL", "frequency": "90.1 FM", "contact": "music@wjou.org", "website": "https://wjou.org", "match_score": 94},
        {"station_name": "Joy 1580 AM", "vector": "AM Radio", "location": "Philadelphia, PA", "frequency": "1580 AM", "contact": "joy@wjam.com", "website": "https://wjam.com", "match_score": 90},
        {"station_name": "WGRP 101.9 FM", "vector": "FM Radio", "location": "Greenville, SC", "frequency": "101.9 FM", "contact": "gospel@wgrp.com", "website": "https://wgrp.com", "match_score": 88},
    ],
    "christian": [
        {"station_name": "SiriusXM The Message", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 63", "contact": "themessage@siriusxm.com", "website": "https://siriusxm.com/themessage", "match_score": 99},
        {"station_name": "K-LOVE Radio", "vector": "FM Radio", "location": "National", "frequency": "Multiple", "contact": "submissions@klove.com", "website": "https://klove.com", "match_score": 99},
        {"station_name": "Air1 Radio", "vector": "FM Radio", "location": "National", "frequency": "Multiple", "contact": "submissions@air1.com", "website": "https://air1.com", "match_score": 98},
        {"station_name": "Life 96.5 FM", "vector": "FM Radio", "location": "Fort Wayne, IN", "frequency": "96.5 FM", "contact": "music@life965.com", "website": "https://life965.com", "match_score": 95},
        {"station_name": "Fellowship Church Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "radio@fellowshipchurch.com", "website": "https://fellowshipchurch.com/radio", "match_score": 94},
        {"station_name": "Hillsong Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "radio@hillsong.com", "website": "https://hillsong.com/radio", "match_score": 96},
        {"station_name": "Bethel Music Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "radio@bethelmusic.com", "website": "https://bethelmusic.com/radio", "match_score": 96},
        {"station_name": "Elevation Worship Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "radio@elevationworship.com", "website": "https://elevationworship.com/radio", "match_score": 95},
        {"station_name": "WCIC 91.5 FM", "vector": "FM Radio", "location": "Peoria, IL", "frequency": "91.5 FM", "contact": "music@wcicfm.org", "website": "https://wcicfm.org", "match_score": 93},
        {"station_name": "WAY-FM 88.7 FM", "vector": "FM Radio", "location": "Nashville, TN", "frequency": "88.7 FM", "contact": "promo@wayfm.com", "website": "https://wayfm.com", "match_score": 94},
        {"station_name": "The Promise 99.5 FM", "vector": "FM Radio", "location": "Kansas City, MO", "frequency": "99.5 FM", "contact": "music@thepromise.org", "website": "https://thepromise.org", "match_score": 92},
        {"station_name": "Christian Talk 1160 AM", "vector": "AM Radio", "location": "Dallas, TX", "frequency": "1160 AM", "contact": "talk@1160am.com", "website": "https://1160am.com", "match_score": 90},
        {"station_name": "Plumbline Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "info@plumblinechurch.com", "website": "https://plumblinechurch.com/radio", "match_score": 85},
    ],
    "pop": [
        {"station_name": "SiriusXM Hits 1", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 2", "contact": "hits1@siriusxm.com", "website": "https://siriusxm.com/hits1", "match_score": 99},
        {"station_name": "Z100 New York", "vector": "FM Radio", "location": "New York, NY", "frequency": "100.3 FM", "contact": "music@z100.com", "website": "https://z100.com", "match_score": 97},
        {"station_name": "KIIS-FM 102.7", "vector": "FM Radio", "location": "Los Angeles, CA", "frequency": "102.7 FM", "contact": "music@kiisfm.com", "website": "https://kiisfm.com", "match_score": 96},
    ],
    "rnb": [
        {"station_name": "SiriusXM Heart & Soul", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 48", "contact": "heartandsoul@siriusxm.com", "website": "https://siriusxm.com/heartandsoul", "match_score": 98},
        {"station_name": "WBLS 107.5 FM", "vector": "FM Radio", "location": "New York, NY", "frequency": "107.5 FM", "contact": "music@wbls.com", "website": "https://wbls.com", "match_score": 95},
    ],
    "soul": [
        {"station_name": "SiriusXM Soul Town", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 49", "contact": "soultown@siriusxm.com", "website": "https://siriusxm.com/soultown", "match_score": 98},
        {"station_name": "KBLX 102.9 FM", "vector": "FM Radio", "location": "San Francisco, CA", "frequency": "102.9 FM", "contact": "music@kblx.com", "website": "https://kblx.com", "match_score": 92},
    ],
    "folk": [
        {"station_name": "Folk Alley", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "submissions@folkalley.com", "website": "https://folkalley.com", "match_score": 96},
        {"station_name": "KGSR 93.3 FM", "vector": "FM Radio", "location": "Austin, TX", "frequency": "93.3 FM", "contact": "music@kgsr.com", "website": "https://kgsr.com", "match_score": 90},
    ],
    "industrial": [
        {"station_name": "SiriusXM Turbo", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 41", "contact": "turbo@siriusxm.com", "website": "https://siriusxm.com/turbo", "match_score": 95},
        {"station_name": "Industrial Radio", "vector": "Internet Radio", "location": "Global", "frequency": "Stream", "contact": "submissions@industrialradio.com", "website": "https://industrialradio.com", "match_score": 88},
    ],
    "alternative": [
        {"station_name": "SiriusXM Alt Nation", "vector": "Satellite Radio", "location": "National", "frequency": "Ch 36", "contact": "altnation@siriusxm.com", "website": "https://siriusxm.com/altnation", "match_score": 99},
        {"station_name": "KROQ 106.7 FM", "vector": "FM Radio", "location": "Los Angeles, CA", "frequency": "106.7 FM", "contact": "music@kroq.com", "website": "https://kroq.com", "match_score": 97},
        {"station_name": "101X", "vector": "FM Radio", "location": "Austin, TX", "frequency": "101.5 FM", "contact": "music@101x.com", "website": "https://101x.com", "match_score": 92},
    ],
}

class RadioFinder:
    def __init__(self):
        self.headers = {"User-Agent": "SoundScapePilot-RadioBot/1.0 (Music Industry Research)"}

    def search(self, genre: str, state: str = "", skip_names: set = None) -> List[Dict[str, Any]]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.search_async(genre, state, skip_names or set()))
        finally:
            loop.close()

    async def search_async(self, genre: str, state: str = "", skip_names: set = None) -> List[Dict[str, Any]]:
        results = []
        state_norm = (state or "").strip().lower()
        skip = skip_names or set()

        # 1. Always include curated data.
        curated = self._curated_for_genre(genre)
        for c in curated:
            if state_norm and not self._state_matches(c.get("location", ""), self._state_targets(state_norm)):
                continue
            cname = (c.get("station_name", "") or "").strip().lower()
            if cname in skip:
                continue
            results.append(dict(c))

        # 2. Online discovery — skip already-known stations.
        if state_norm:
            try:
                wiki_results = await asyncio.wait_for(
                    self._search_wikipedia_all(state, skip), timeout=20.0
                )
                results.extend(wiki_results)
            except Exception:
                pass
        try:
            rb_results = await asyncio.wait_for(
                self._search_radio_browser(genre, state, skip), timeout=15.0
            )
            results.extend(rb_results)
        except Exception:
            pass

        # 3. Dedup — keep LAST so online overrides curated.
        seen = {}
        for r in results:
            name = r.get("station_name", "").strip()
            if not name:
                continue
            seen[name] = r

        # 4. Normalize: add name, call_letters, genre, state aliases for frontend
        genre_lower = (genre or "").lower()
        for r in seen.values():
            if "station_name" in r:
                r["name"] = r["station_name"]
            if not r.get("call_letters"):
                r["call_letters"] = r["station_name"]
            r["genre"] = genre_lower
            loc = (r.get("location") or "")
            parts = loc.split(",")
            if len(parts) >= 2:
                st = parts[-1].strip().upper()
                r["state"] = st if len(st) <= 2 else parts[-1].strip()
            else:
                r["state"] = loc.strip()

        return list(seen.values())

    def _curated_for_genre(self, genre: str) -> List[Dict[str, Any]]:
        genre_l = genre.lower()
        # Direct match
        if genre_l in CURATED_STATIONS:
            return CURATED_STATIONS[genre_l]
        # Partial match on key words
        for key, stations in CURATED_STATIONS.items():
            if key in genre_l or genre_l in key:
                return stations
        # Default to rock if nothing matches
        return CURATED_STATIONS.get("rock", [])

    def _resolve_state(self, state: str) -> tuple:
        sn = (state or "").strip().lower()
        if sn in US_STATES:
            abbr = US_STATES[sn]
            return (sn, abbr)
        if len(sn) == 2:
            abbr = sn.upper()
            fn = STATE_ABBREVS.get(abbr, "")
            return (fn, abbr) if fn else ("", abbr)
        return ("", sn)

    async def _search_wikipedia_all(self, state: str, skip_names: set = None) -> List[Dict[str, Any]]:
        """Parse ALL wikitables from a state's radio station list page — no genre filter."""
        full_name, _ = self._resolve_state(state)
        if not full_name:
            return []
        page_title = f"List of radio stations in {full_name.title()}"
        try:
            r = await asyncio.to_thread(
                lambda: httpx.get(f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}",
                    headers=self.headers, follow_redirects=True, timeout=15.0)
            )
        except Exception:
            return []
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        tables = soup.find_all("table", class_="wikitable")
        if not tables:
            return []
        out = []
        seen = set()
        skip = skip_names or set()
        for table in tables:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue
                callsign = cols[0].get_text(strip=True)
                freq = cols[1].get_text(strip=True)
                city = cols[2].get_text(strip=True)
                fmt = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                key = callsign + freq
                if key in seen:
                    continue
                seen.add(key)
                station_name = f"{callsign} {freq}"
                if station_name.lower() in skip:
                    continue
                vector = "FM Radio" if "FM" in freq else "AM Radio" if "AM" in freq else "Radio"
                location = f"{city}, {full_name.title()}"
                contact = f"{callsign.lower()}@{callsign.lower()}.com" if callsign else ""
                out.append({
                    "station_name": station_name,
                    "vector": vector,
                    "location": location,
                    "frequency": freq,
                    "format": fmt,
                    "contact": contact,
                    "website": f"https://en.wikipedia.org/wiki/{callsign}",
                    "match_score": 50
                })
        return out

    async def _search_wikipedia(self, genre: str, state: str) -> List[Dict[str, Any]]:
        full_name, _ = self._resolve_state(state)
        if not full_name:
            return []
        page_title = f"List of radio stations in {full_name.title()}"
        try:
            r = await asyncio.to_thread(
                lambda: httpx.get(f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}",
                    headers=self.headers, follow_redirects=True, timeout=10.0)
            )
        except Exception:
            return []
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table", class_="wikitable")
        if not table:
            return []
        rows = table.find_all("tr")[1:]
        genre_l = genre.lower()
        out = []
        seen = set()
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
            callsign = cols[0].get_text(strip=True)
            freq = cols[1].get_text(strip=True)
            city = cols[2].get_text(strip=True)
            fmt = cols[4].get_text(strip=True) if len(cols) > 4 else ""
            key = callsign + freq
            if key in seen:
                continue
            seen.add(key)
            fmt_l = fmt.lower()
            if genre_l not in fmt_l and not any(w in fmt_l for w in genre_l.split() if len(w) > 2):
                continue
            vector = "FM Radio" if "FM" in freq else "AM Radio" if "AM" in freq else "Radio"
            location = f"{city}, {full_name.title()}"
            contact = f"{callsign.lower()}@{callsign.lower()}.com" if callsign else ""
            score = self._score(f"{callsign} {freq} {fmt}", genre)
            out.append({
                "station_name": f"{callsign} {freq}",
                "vector": vector,
                "location": location,
                "frequency": freq,
                "contact": contact,
                "website": f"https://en.wikipedia.org/wiki/{callsign}",
                "match_score": score
            })
        out.sort(key=lambda x: x["match_score"], reverse=True)
        return out

    async def _search_radio_browser(self, genre: str, state: str, skip_names: set = None) -> List[Dict[str, Any]]:
        if not genre:
            return []
        seen_names = set()
        all_stations = []
        skip = skip_names or set()

        async def fetch(params: dict) -> list:
            try:
                async with httpx.AsyncClient(timeout=8.0, headers=self.headers, follow_redirects=True) as c:
                    r = await c.get(f"{RADIO_BROWSER_URL}/json/stations/search", params=params)
                    return r.json() if r.status_code == 200 else []
            except Exception:
                return []

        searches = [{"tag": genre, "countrycode": "US", "limit": 500, "order": "votes", "reverse": "true"}]
        if state.strip():
            searches.append({"tag": genre, "state": state, "limit": 500, "order": "votes", "reverse": "true"})

        for params in searches:
            for s in await fetch(params):
                name = (s.get("name") or "").strip()
                if name and name not in seen_names and name.lower() not in skip:
                    seen_names.add(name)
                    all_stations.append(s)

        if not all_stations:
            return []

        state_norm = (state or "").strip().lower()
        targets = self._state_targets(state) if state_norm else set()
        matched = all_stations if not state_norm else [s for s in all_stations if self._state_matches(s.get("state",""), targets)]
        if not matched and state_norm:
            matched = all_stations[:20]

        seen = set()
        out = []
        for s in matched:
            name = (s.get("name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            freq = s.get("url_resolved") or s.get("url") or ""
            contact = s.get("homepage") or ""
            if not contact and freq:
                contact = freq[:60]
            vector = "Internet Radio"
            codec = (s.get("codec") or "").upper()
            if codec in ("MP3", "AAC", "OGG", "FLAC"):
                vector = f"{codec} Stream"
            # Heuristic classification
            tags = (s.get("tags") or "").lower()
            if "college" in tags or "university" in tags or "campus" in tags:
                vector = "College Radio"
            if "military" in tags or "afn" in tags or "armed forces" in tags:
                vector = "Military Radio"
            out.append({
                "station_name": name,
                "vector": vector,
                "location": f"{s.get('state','') or s.get('country','') or 'Global'}".strip(", "),
                "frequency": freq[:40] if freq else "Stream",
                "contact": contact[:80] if contact else "",
                "website": (s.get("homepage") or "")[:120],
                "match_score": self._score(f"{name} {s.get('tags','')} {s.get('country','')}", genre)
            })
        out.sort(key=lambda x: x["match_score"], reverse=True)
        return out[:20]

    def _state_targets(self, state: str) -> set:
        t = set()
        sn = (state or "").strip().lower()
        if not sn:
            return t
        full = US_STATES.get(sn)
        if full:
            t.update([full.lower(), full, sn])
        elif len(sn) == 2:
            t.add(sn.upper()); t.add(sn)
            fn = STATE_ABBREVS.get(sn.upper(), "")
            if fn:
                t.update([fn.lower(), fn])
        return t

    def _state_matches(self, station_state: str, targets: set) -> bool:
        ss = (station_state or "").lower().strip()
        if not ss:
            return False
        if ss in targets:
            return True
        for t in targets:
            if f" {t}" in ss or ss.startswith(t) or ss.endswith(t):
                return True
        return False

    def _score(self, text: str, genre: str) -> float:
        text_l = text.lower()
        genre_l = genre.lower()
        score = 0.0
        if genre_l in text_l:
            score += 50.0
        for word in genre_l.split():
            if word in text_l and len(word) > 2:
                score += 15.0
        return min(score, 99.0)
