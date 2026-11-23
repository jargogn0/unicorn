#!/usr/bin/env python3
"""Fetch OpenStreetMap data for a STOCKHOLM build slice via the Overpass API.

Data © OpenStreetMap contributors, licensed ODbL 1.0. Derived databases
(Content/Data/Geo/*.json) must stay ODbL and carry attribution; see
WORLD_DESIGN.md §4. Respect Overpass usage policy: one request per slice,
cache results in Tools/geodata/cache/ and never hammer the public endpoint.

Usage:
  python3 Tools/geodata/fetch_osm.py --slice milestone_a
  python3 Tools/geodata/fetch_osm.py --bbox 59.3150 18.0480 59.3360 18.0850 --name custom
"""
import argparse, datetime, json, pathlib, sys, urllib.parse, urllib.request

SLICES = {
    # Gamla Stan, Riddarholmen, Helgeandsholmen, southern Norrmalm, northern
    # Södermalm (Slussen–Mariatorget–Hornsgatan) and the eastern tip of Kungsholmen.
    "milestone_a": (59.3150, 18.0480, 59.3360, 18.0850),
}
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]

QUERY = """[out:json][timeout:240][bbox:{s},{w},{n},{e}];
(
  way["highway"];
  way["building"]; relation["building"];
  way["building:part"];
  way["natural"="water"]; relation["natural"="water"];
  way["natural"="coastline"];
  way["place"~"island|islet"]; relation["place"~"island|islet"];
  way["leisure"="park"]; relation["leisure"="park"];
  way["place"="square"]; way["highway"="pedestrian"]["area"="yes"];
  way["bridge"]; way["man_made"="bridge"];
  node["amenity"~"cafe|restaurant|bar"]; node["tourism"~"attraction|museum"];
);
out body geom;
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", default="milestone_a")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("S", "W", "N", "E"))
    ap.add_argument("--name")
    args = ap.parse_args()
    s, w, n, e = args.bbox if args.bbox else SLICES[args.slice]
    name = args.name or args.slice
    cache = pathlib.Path(__file__).parent / "cache"
    cache.mkdir(exist_ok=True)
    out = cache / f"{name}.overpass.json"
    q = QUERY.format(s=s, w=w, n=n, e=e)
    last_err = None
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "stockholm-game-geodata/0.1"})
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.load(r)
            data["_stockholm"] = {"bbox": [s, w, n, e], "endpoint": ep,
                                  "fetched_utc": datetime.datetime.utcnow().isoformat() + "Z",
                                  "license": "ODbL-1.0", "attribution": "© OpenStreetMap contributors"}
            out.write_text(json.dumps(data), encoding="utf-8")
            print(f"wrote {out} ({len(data.get('elements', []))} elements) from {ep}")
            return 0
        except Exception as ex:  # network policy / rate limits: try the next mirror
            last_err = ex
            print(f"{ep}: {ex}", file=sys.stderr)
    print(f"FAILED to fetch OSM data: {last_err}", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
