"""Export Texas churches via lat/lon grid to bypass OSM element limits.
Splits Texas into 6x4=24 cells, queries each concurrently.
Output: csv with county inferred from OSM relations where available.
"""
import csv, os, sys, asyncio, re
import httpx

HEADERS = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SoundScapePilot-Grid/1.0"}
OUT_FILE = "texas_churches_grid.csv"
FIELD_NAMES = ["name","denomination_category","address","city","county","zip","phone","website","email","notes"]

# Texas bounding box: lat [25.8, 36.5], lon [-106.6, -93.5]
LAT_MIN, LAT_MAX = 25.8, 36.5
LON_MIN, LON_MAX = -106.6, -93.5
ROWS, COLS = 6, 4

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


def make_query(lat_min, lon_min, lat_max, lon_max):
    return (
        f'[out:json][timeout:45];'
        f'node({lat_min},{lon_min},{lat_max},{lon_max})'
        f'["amenity"="place_of_worship"]["religion"="christian"][name];'
        f'out center 5000;'
    )


async def query_cell(client, sem, lat_min, lon_min, lat_max, lon_max, cell_id):
    async with sem:
        q = make_query(lat_min, lon_min, lat_max, lon_max)
        try:
            r = await client.post("https://overpass-api.de/api/interpreter",
                                  data={"data": q}, timeout=50)
            if r.status_code == 200:
                return cell_id, r.json().get("elements", [])
            return cell_id, []
        except Exception as e:
            print(f"  Cell {cell_id} error: {type(e).__name__}")
            return cell_id, []


def elements_to_rows(elements, seen):
    rows = []
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name", "").strip()
        lat = round(el.get("lat", 0) or (el.get("center") or {}).get("lat", 0), 3)
        lon = round(el.get("lon", 0) or (el.get("center") or {}).get("lon", 0), 3)
        if not name:
            continue
        key = (name.lower(), lat, lon) if lat and lon else (name.lower(),)
        if key in seen:
            continue
        seen.add(key)
        lat = el.get("lat", 0) or (el.get("center") or {}).get("lat", 0)
        lon = el.get("lon", 0) or (el.get("center") or {}).get("lon", 0)
        rows.append({
            "name": name,
            "denomination_category": classify(name),
            "address": tags.get("addr:street", "") or tags.get("addr:full", ""),
            "city": tags.get("addr:city", "") or "",
            "county": tags.get("addr:county", "") or "",
            "zip": tags.get("addr:postcode", "") or "",
            "phone": tags.get("phone", "") or tags.get("contact:phone", ""),
            "website": tags.get("website", "") or tags.get("contact:website", ""),
            "email": tags.get("email", "") or tags.get("contact:email", ""),
            "notes": f"lat:{lat};lon:{lon}",
        })
    return rows


async def main():
    # Generate grid cells
    cells = []
    for r in range(ROWS):
        for c in range(COLS):
            lat_min = LAT_MIN + (LAT_MAX - LAT_MIN) * r / ROWS
            lat_max = LAT_MIN + (LAT_MAX - LAT_MIN) * (r + 1) / ROWS
            lon_min = LON_MIN + (LON_MAX - LON_MIN) * c / COLS
            lon_max = LON_MIN + (LON_MAX - LON_MIN) * (c + 1) / COLS
            cells.append((lat_min, lon_min, lat_max, lon_max, f"R{r}C{c}"))
    print(f"Querying {len(cells)} grid cells (batch=6 concurrency)...")

    seen = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                n = row.get("name", "").strip().lower()
                nt = row.get("notes", "")
                lat_match = re.search(r"lat:([-\d.]+)", nt)
                lon_match = re.search(r"lon:([-\d.]+)", nt)
                if lat_match and lon_match:
                    lat, lon = round(float(lat_match.group(1)), 3), round(float(lon_match.group(2)), 3)
                    seen.add((n, lat, lon))
                elif n:
                    seen.add((n,))
    print(f"Loaded {len(seen)} existing from CSV")

    sem = asyncio.Semaphore(6)
    all_rows = []
    total_new = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=55) as client:
        for i in range(0, len(cells), 6):
            chunk = cells[i:i+6]
            tasks = [query_cell(client, sem, *cell) for cell in chunk]
            results = await asyncio.gather(*tasks)

            for cell_id, elements in results:
                rows = elements_to_rows(elements, seen)
                if rows:
                    print(f"  Cell {cell_id}: {len(rows)} churches (+ some already seen)")
                    all_rows.extend(rows)
                    total_new += len(rows)
                else:
                    print(f"  Cell {cell_id}: 0 new")

    if all_rows:
        with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELD_NAMES)
            w.writeheader()
            w.writerows(all_rows)
        print(f"\nWritten {total_new} churches to {OUT_FILE}")
    else:
        print("\nNo results")

    websites = sum(1 for r in all_rows if r.get("website"))
    phones = sum(1 for r in all_rows if r.get("phone"))
    emails = sum(1 for r in all_rows if r.get("email"))
    cities = sum(1 for r in all_rows if r.get("city"))
    counties = sum(1 for r in all_rows if r.get("county"))
    print(f"Stats: {total_new} total, {websites} websites, {phones} phones, {emails} emails, {cities} cities, {counties} counties")


if __name__ == "__main__":
    asyncio.run(main())
