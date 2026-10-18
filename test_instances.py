"""Try all known Overpass instances to find one that works."""
import urllib.request, urllib.parse, json, time, socket

instances = [
    ("gall.openstreetmap.de", "gall (main backend)"),
    ("lambert.openstreetmap.de", "lambert (main backend)"),
    ("overpass-api.de", "main round-robin"),
    ("z.overpass-api.de", "old server"),
    ("lz4.overpass-api.de", "old server"),
    ("overpass.kumi.systems", "kumi systems"),
    ("overpass.openstreetmap.fr", "france"),
    ("overpass-swi.openstreetmap.org", "swiss"),
    ("overpass-maprva.openstreetmap.org", "maprva (US)"),
    ("private.coffee.overpass.openstreetmap.org", "private.coffee"),
]

q = '[out:json][timeout:10];node(29.5,-96,30,-95)["amenity"="place_of_worship"]["religion"="christian"][name];out center 3;'
data = f"data={urllib.parse.quote(q)}".encode()

for host, name in instances:
    for proto in ["https", "http"]:
        url = f"{proto}://{host}/api/interpreter"
        try:
            req = urllib.request.Request(url, data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SoundScapePilot/1.0"})
            r = urllib.request.urlopen(req, timeout=15)
            if r.status == 200:
                els = json.loads(r.read()).get("elements", [])
                print(f"OK {name} ({host}): {len(els)} elements")
                found = True
                break
            else:
                print(f"XX {name} ({host}): status {r.status}")
        except Exception as e:
            print(f"XX {name} ({host} [{proto}]): {type(e).__name__}")
    else:
        continue
    break
else:
    print("No working instance found")
