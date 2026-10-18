"""Test French Overpass with 5000-element output limit."""
import urllib.request, urllib.parse, json, time

host = "overpass.openstreetmap.fr"
q = '[out:json][timeout:60];node(29,-100,33.5,-95)["amenity"="place_of_worship"]["religion"="christian"][name];out center 2000;'
data = f"data={urllib.parse.quote(q)}".encode()
req = urllib.request.Request(
    f"https://{host}/api/interpreter", data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SoundScapePilot/1.0"})

try:
    start = time.time()
    r = urllib.request.urlopen(req, timeout=70)
    elapsed = time.time() - start
    if r.status == 200:
        els = json.loads(r.read()).get("elements", [])
        print(f"OK: {len(els)} elements in {elapsed:.0f}s")
        with_website = sum(1 for e in els if (e.get("tags") or {}).get("website"))
        with_phone = sum(1 for e in els if (e.get("tags") or {}).get("phone"))
        with_city = sum(1 for e in els if (e.get("tags") or {}).get("addr:city"))
        print(f"  Websites: {with_website}, Phones: {with_phone}, Cities: {with_city}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
