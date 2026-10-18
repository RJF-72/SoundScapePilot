"""Test OSM query on alternative endpoints."""
import httpx, time

endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

q = '[out:json][timeout:30];area["name"="Taylor County"][admin_level=6]->.a;node(area.a)["amenity"="place_of_worship"]["religion"="christian"][name];out center 2000;'

for ep in endpoints:
    try:
        r = httpx.post(ep, data={'data': q},
                       headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'SoundScapePilot/1.0'},
                       timeout=35)
        print(f'{ep}: Status {r.status_code}')
        if r.status_code == 200:
            els = r.json().get('elements', [])
            print(f'  Elements: {len(els)}')
    except Exception as e:
        print(f'{ep}: Error - {type(e).__name__}')
    time.sleep(2)
