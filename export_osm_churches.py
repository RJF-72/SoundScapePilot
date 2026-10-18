"""Export all churches north of I-10 from OpenStreetMap — async + concurrent.
Output: texas_churches_north_of_i10.csv

Usage:
    python export_osm_churches.py                      # all 230 counties (~5 min)
    python export_osm_churches.py --county Taylor       # single county
    python export_osm_churches.py --dry-run             # list counties only
    python export_osm_churches.py --batch 10             # concurrency level (default 8)
"""
import csv, os, sys, asyncio, time
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "titan7"))

HEADERS = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SoundScapePilot-ChurchExport/2.0"}

NORTH_OF_I10 = [
    "Anderson","Andrews","Angelina","Archer","Armstrong","Atascosa","Bailey","Bastrop","Baylor",
    "Bell","Bexar","Blanco","Borden","Bosque","Bowie","Brazoria","Brazos","Brewster","Briscoe",
    "Brown","Burleson","Burnet","Caldwell","Callahan","Cameron","Camp","Carson","Cass","Castro",
    "Chambers","Cherokee","Childress","Clay","Cochran","Coke","Coleman","Collin","Collingsworth",
    "Colorado","Comal","Comanche","Concho","Cooke","Coryell","Cottle","Crane","Crockett",
    "Crosby","Culberson","Dallam","Dallas","Dawson","Deaf Smith","Delta","Denton","DeWitt",
    "Dickens","Dimmit","Donley","Duval","Eastland","Ector","Edwards","Ellis","El Paso",
    "Erath","Falls","Fannin","Fayette","Fisher","Floyd","Foard","Fort Bend","Franklin",
    "Freestone","Frio","Gaines","Galveston","Garza","Gillespie","Glasscock","Goliad",
    "Gonzales","Gray","Grayson","Gregg","Grimes","Guadalupe","Hale","Hall","Hamilton",
    "Hansford","Hardeman","Hardin","Harris","Harrison","Hartley","Haskell","Hays","Hemphill",
    "Henderson","Hidalgo","Hill","Hockley","Hood","Hopkins","Houston","Howard","Hudspeth",
    "Hunt","Hutchinson","Irion","Jack","Jackson","Jasper","Jeff Davis","Jefferson","Jim Hogg",
    "Jim Wells","Johnson","Jones","Karnes","Kaufman","Kendall","Kenedy","Kent","Kerr",
    "Kimble","King","Kinney","Kleberg","Knox","Lamar","Lamb","Lampasas","La Salle",
    "Lavaca","Lee","Leon","Liberty","Limestone","Lipscomb","Live Oak","Llano","Loving",
    "Lubbock","Lynn","Madison","Marion","Martin","Mason","Matagorda","Maverick","McCulloch",
    "McLennan","McMullen","Medina","Menard","Midland","Milam","Mills","Mitchell","Montague",
    "Montgomery","Moore","Morris","Motley","Nacogdoches","Navarro","Newton","Nolan",
    "Nueces","Ochiltree","Oldham","Orange","Palo Pinto","Panola","Parker","Parmer",
    "Pecos","Polk","Potter","Presidio","Rains","Randall","Reagan","Real","Red River",
    "Reeves","Refugio","Roberts","Robertson","Rockwall","Runnels","Rusk","Sabine",
    "San Augustine","San Jacinto","San Patricio","San Saba","Schleicher","Scurry","Shackelford",
    "Shelby","Sherman","Smith","Somervell","Starr","Stephens","Sterling","Stonewall",
    "Sutton","Swisher","Tarrant","Taylor","Terrell","Terry","Throckmorton","Titus",
    "Tom Green","Travis","Trinity","Tyler","Upshur","Upton","Uvalde","Val Verde",
    "Van Zandt","Victoria","Walker","Waller","Ward","Washington","Webb","Wharton",
    "Wheeler","Wichita","Wilbarger","Willacy","Williamson","Wilson","Winkler","Wise",
    "Wood","Yoakum","Young","Zapata","Zavala",
]
SOUTH_OF_I10 = {
    "Aransas","Bee","Brooks","Calhoun","DeWitt","Goliad","Hidalgo","Jim Hogg",
    "Jim Wells","Kenedy","Kleberg","La Salle","Live Oak","McMullen","Nueces",
    "Refugio","San Patricio","Starr","Victoria","Webb","Willacy","Zapata",
}

FIELD_NAMES = ["name","denomination_category","address","city","county","zip","phone","website","pastor","email","notes"]


def classify(name):
    l = name.lower()
    if "baptist" in l: return "Baptist"
    if "methodist" in l or "umc" in l: return "Methodist"
    if "pentecostal" in l or "assembly" in l: return "Pentecostal"
    if "catholic" in l: return "Catholic"
    if "lutheran" in l: return "Lutheran"
    if "presbyterian" in l: return "Presbyterian"
    if "episcopal" in l: return "Episcopal"
    if "church of christ" in l or "church of god" in l: return "Christian"
    return "Non-Denominational"


async def query_county(client, county_name, sem, timeout=25):
    """Async query a single county."""
    q = f'[out:json][timeout:{timeout}];area["name"="{county_name} County"]["admin_level"=6]->.a;node(area.a)["amenity"="place_of_worship"]["religion"="christian"];out center 2000;'
    async with sem:
        try:
            r = await client.post("https://overpass-api.de/api/interpreter", data={"data": q}, timeout=timeout+5)
            if r.status_code == 200:
                return county_name, r.json().get("elements", [])
            return county_name, []
        except:
            return county_name, []


def elements_to_rows(county_name, elements, seen):
    """Convert OSM elements to CSV rows, deduping by (name, county)."""
    rows = []
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name", "").strip()
        key = (name.lower(), county_name.lower())
        if not name or key in seen:
            continue
        seen.add(key)
        city = tags.get("addr:city", "") or tags.get("name:city", "")
        lat = el.get("lat", 0) or (el.get("center") or {}).get("lat", 0)
        lon = el.get("lon", 0) or (el.get("center") or {}).get("lon", 0)
        rows.append({
            "name": name,
            "denomination_category": classify(name),
            "address": tags.get("addr:street", "") or tags.get("addr:full", ""),
            "city": city,
            "county": county_name,
            "zip": tags.get("addr:postcode", "") or tags.get("addr:post_code", ""),
            "phone": tags.get("phone", "") or tags.get("contact:phone", ""),
            "website": tags.get("website", "") or tags.get("contact:website", ""),
            "pastor": "",
            "email": tags.get("email", "") or tags.get("contact:email", ""),
            "notes": f"lat:{lat};lon:{lon}",
        })
    return rows


async def main():
    dry_run = "--dry-run" in sys.argv
    single = None
    for a in sys.argv:
        if a.startswith("--county="): single = a.split("=",1)[1]
        elif a == "--county" and len(sys.argv) > sys.argv.index(a)+1: single = sys.argv[sys.argv.index(a)+1]

    counties = [single] if single else [c for c in NORTH_OF_I10 if c not in SOUTH_OF_I10]
    batch_size = 8
    for a in sys.argv:
        if a.startswith("--batch="): batch_size = int(a.split("=",1)[1])

    out_file = "texas_churches_north_of_i10.csv"

    # Load existing names
    seen = set()
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                n = row.get("name", "").strip().lower()
                c = row.get("county", "").strip().lower()
                if n and c: seen.add((n, c))

    if dry_run:
        print(f"{len(counties)} counties, {len(seen)} existing churches")
        for i, c in enumerate(counties, 1): print(f"  [{i}] {c} County")
        return

    print(f"Exporting {len(counties)} counties north of I-10 (batch={batch_size})...")
    print(f"Already have {len(seen)} churches in CSV.\n")

    write_mode = "a" if os.path.exists(out_file) and len(seen) > 0 else "w"
    total_new = 0
    sem = asyncio.Semaphore(batch_size)
    start_clock = time.time()

    # We write in batches to reduce file I/O
    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        for i in range(0, len(counties), batch_size):
            chunk = counties[i:i+batch_size]
            tasks = [query_county(client, c, sem) for c in chunk]
            results = await asyncio.gather(*tasks)

            all_rows = []
            for cname, elements in results:
                rows = elements_to_rows(cname, elements, seen)
                all_rows.extend(rows)
                total_new += len(rows)

            # Write chunk to CSV
            with open(out_file, write_mode, newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=FIELD_NAMES)
                if write_mode == "w": w.writeheader(); write_mode = "a"
                w.writerows(all_rows)

            elapsed = time.time() - start_clock
            pct = min(100, (i + len(chunk)) / len(counties) * 100)
            rate = total_new / elapsed if elapsed > 0 else 0
            print(f"  [{i+1}-{min(i+batch_size, len(counties))}/{len(counties)}] {pct:.0f}% | {total_new} churches | {rate:.1f}/s | {elapsed:.0f}s")

    elapsed = time.time() - start_clock
    print(f"\nDone. {total_new} new churches added to {out_file} in {elapsed:.0f}s ({total_new/elapsed:.1f} churches/s)")
    print(f"Total unique churches in CSV: {len(seen)}")

if __name__ == "__main__":
    asyncio.run(main())
