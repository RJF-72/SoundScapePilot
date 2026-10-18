"""Quick check if Overpass is responding."""
import httpx, time
q = '[out:json][timeout:15];node(29.5,-96,30,-95)["amenity"="place_of_worship"]["religion"="christian"][name];out center 2000;'
for attempt in range(3):
    try:
        r = httpx.post("https://overpass-api.de/api/interpreter", data={"data": q},
                       headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SoundScapePilot/1.0"},
                       timeout=20)
        print(f"Attempt {attempt+1}: Status {r.status_code}")
        if r.status_code == 200:
            els = r.json().get("elements", [])
            print(f"  Elements: {len(els)}")
            break
    except Exception as e:
        print(f"Attempt {attempt+1}: {type(e).__name__}")
    time.sleep(5)
