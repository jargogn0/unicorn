#!/usr/bin/env python3
"""Convert an Overpass JSON dump into the STOCKHOLM city document consumed by
stockholm::sim::CityModel (Unreal world builder, GPS, minimap, Founder Map).

Coordinates use the same local tangent projection as GeoProjection (origin
59.3275 N, 18.0680 E): x = metres east, y = metres north.

Output is an ODbL "derivative database": keep the attribution and licence
fields, and publish the processing code (this file) alongside it.

Usage:
  python3 Tools/geodata/process_osm.py Tools/geodata/cache/milestone_a.overpass.json \
      Stockholm/Content/Data/Geo/milestone_a_city.json [--locations Stockholm/Content/Data/World/locations.json]
"""
import argparse, json, math, re, sys

ORIGIN_LAT, ORIGIN_LON = 59.3275, 18.0680
PHI = math.radians(ORIGIN_LAT)
M_LAT = 111132.92 - 559.82 * math.cos(2 * PHI) + 1.175 * math.cos(4 * PHI) - 0.0023 * math.cos(6 * PHI)
M_LON = 111412.84 * math.cos(PHI) - 93.5 * math.cos(3 * PHI) + 0.118 * math.cos(5 * PHI)

ROAD_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary",
                "secondary_link", "tertiary", "tertiary_link", "residential", "living_street", "unclassified",
                "service", "pedestrian", "footway", "path", "cycleway", "steps"}
LANDMARK_KINDS = {"church", "cathedral", "palace", "castle", "government", "public", "civic", "museum"}
LEVEL_HEIGHT, GROUND_EXTRA = 3.2, 1.3
DEFAULT_HEIGHT = 18.0  # typical 5–6 storey inner-city block when OSM has no height/levels


def to_local(lat, lon):
    return [round((lon - ORIGIN_LON) * M_LON, 2), round((lat - ORIGIN_LAT) * M_LAT, 2)]


def parse_length(v):
    if v is None:
        return None
    m = re.match(r"\s*([0-9]+(?:[.,][0-9]+)?)\s*(m|ft)?", str(v))
    if not m:
        return None
    x = float(m.group(1).replace(",", "."))
    return x * 0.3048 if m.group(2) == "ft" else x


def ring_of(geom):
    pts = [to_local(p["lat"], p["lon"]) for p in geom if p]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def signed_area(r):
    return 0.5 * sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))


def assemble_rings(member_geoms):
    """Join open way segments of a multipolygon role into closed rings."""
    segs = [ring_of(g) + ([to_local(g[-1]["lat"], g[-1]["lon"])] if g and g[0] != g[-1] else []) for g in member_geoms]
    segs = [s for s in segs if len(s) >= 2]
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]; segs.pop(i); changed = True; break
                if s[-1] == cur[-1]:
                    cur += list(reversed(s))[1:]; segs.pop(i); changed = True; break
        if cur[0] == cur[-1]:
            cur = cur[:-1]
        if len(cur) >= 3:
            rings.append(cur)
    return rings


def process(doc, locations=None):
    elements = doc.get("elements", [])
    meta = doc.get("_stockholm", {})
    nodes, ways, buildings, areas, pois = {}, [], [], [], []
    stats = {"roads": 0, "buildings": 0, "buildings_height_from_data": 0, "water": 0, "parks": 0}
    for el in elements:
        tags = el.get("tags", {})
        if el["type"] == "node":
            if "name" in tags:
                pois.append({"id": el["id"], "name": tags["name"], "kind": tags.get("amenity") or tags.get("tourism"),
                             "pos": to_local(el["lat"], el["lon"])})
            continue
        if el["type"] == "way" and tags.get("highway") in ROAD_CLASSES and tags.get("area") != "yes" and "geometry" in el:
            ids = el.get("nodes", [])
            for nid, p in zip(ids, el["geometry"]):
                nodes[nid] = to_local(p["lat"], p["lon"])
            lanes = tags.get("lanes")
            ways.append({
                "id": el["id"], "nodes": ids, "class": tags["highway"],
                "oneway": tags.get("oneway") in ("yes", "1", "true") or tags.get("junction") == "roundabout",
                "lanes": int(lanes) if lanes and lanes.isdigit() else 0,
                "bridge": tags.get("bridge", "no") not in ("no",), "tunnel": tags.get("tunnel", "no") not in ("no",),
                "layer": int(tags["layer"]) if tags.get("layer", "").lstrip("-").isdigit() else 0,
                "name": tags.get("name", ""), "maxspeed": parse_length(tags.get("maxspeed")) or 0,
                "width": parse_length(tags.get("width")) or 0,
            })
            if not ways[-1]["width"]:
                del ways[-1]["width"]
            stats["roads"] += 1
            continue
        is_building = "building" in tags or "building:part" in tags
        if is_building:
            if el["type"] == "way" and "geometry" in el:
                rings = [ring_of(el["geometry"])]
            elif el["type"] == "relation":
                outers = [m["geometry"] for m in el.get("members", []) if m.get("role") == "outer" and "geometry" in m]
                inners = [m["geometry"] for m in el.get("members", []) if m.get("role") == "inner" and "geometry" in m]
                rings = assemble_rings(outers)[:1] + assemble_rings(inners)
            else:
                continue
            if not rings or len(rings[0]) < 3:
                continue
            h = parse_length(tags.get("height"))
            levels = parse_length(tags.get("building:levels"))
            from_data = h is not None or levels is not None
            if h is None:
                h = levels * LEVEL_HEIGHT + GROUND_EXTRA if levels is not None else DEFAULT_HEIGHT
            min_h = parse_length(tags.get("min_height")) or (parse_length(tags.get("building:min_level")) or 0) * LEVEL_HEIGHT
            kind = tags.get("building") or tags.get("building:part") or "yes"
            buildings.append({
                "id": el["id"], "rings": rings, "height": round(h, 2), "min_height": round(min_h, 2),
                "levels": int(levels) if levels else 0, "name": tags.get("name", ""), "kind": kind,
                "roof_shape": tags.get("roof:shape", ""), "colour": tags.get("building:colour", ""),
                "landmark": kind in LANDMARK_KINDS or ("name" in tags and ("wikidata" in tags or "heritage" in tags)),
                "height_from_data": from_data,
            })
            stats["buildings"] += 1
            stats["buildings_height_from_data"] += 1 if from_data else 0
            continue
        kind = None
        if tags.get("natural") == "water":
            kind = "water"
        elif tags.get("leisure") == "park":
            kind = "park"
        elif tags.get("place") == "square" or (tags.get("highway") == "pedestrian" and tags.get("area") == "yes"):
            kind = "plaza"
        elif tags.get("place") in ("island", "islet"):
            kind = "land"
        if kind:
            if el["type"] == "way" and "geometry" in el:
                rings = [ring_of(el["geometry"])]
            elif el["type"] == "relation":
                rings = assemble_rings([m["geometry"] for m in el.get("members", []) if m.get("role") == "outer" and "geometry" in m])
                rings += assemble_rings([m["geometry"] for m in el.get("members", []) if m.get("role") == "inner" and "geometry" in m])
            else:
                continue
            rings = [r for r in rings if len(r) >= 3]
            if rings:
                areas.append({"id": el["id"], "kind": kind, "name": tags.get("name", ""), "rings": rings})
                stats["water" if kind == "water" else "parks"] += 1 if kind in ("water", "park") else 0

    used = {nid for w in ways for nid in w["nodes"]}
    node_rows = [[nid, *nodes[nid]] for nid in sorted(used) if nid in nodes]
    s, w, n, e = meta.get("bbox", [None] * 4)
    if s is not None:
        mn, mx = to_local(s, w), to_local(n, e)
        bounds = [mn[0], mn[1], mx[0], mx[1]]
    else:
        xs = [r[1] for r in node_rows] or [0]; ys = [r[2] for r in node_rows] or [0]
        bounds = [min(xs), min(ys), max(xs), max(ys)]

    report = []
    if locations:
        named = [(b["name"], b["rings"][0]) for b in buildings if b["name"]] + [(p["name"], [p["pos"]]) for p in pois]
        for loc in locations:
            if "lat" not in loc:
                continue
            lx, ly = to_local(loc["lat"], loc["lon"])
            inside_building = any(point_in(lx, ly, b["rings"][0]) for b in buildings)
            nearest = min(((math.dist((lx, ly), centroid(r)), nm) for nm, r in named), default=(None, None))
            report.append({"id": loc["id"], "inside_building": inside_building, "nearest_named": nearest[1],
                           "nearest_named_m": round(nearest[0], 1) if nearest[0] is not None else None})

    out = {
        "kind": "city", "schema_version": 1,
        "origin": {"lat": ORIGIN_LAT, "lon": ORIGIN_LON},
        "bounds_local": [round(v, 1) for v in bounds],
        "attribution": "© OpenStreetMap contributors (ODbL 1.0)", "license": "ODbL-1.0",
        "source_timestamp": doc.get("osm3s", {}).get("timestamp_osm_base", meta.get("fetched_utc", "")),
        "stats": stats,
        "roads": {"nodes": node_rows, "ways": ways},
        "buildings": buildings, "areas": areas, "pois": pois,
    }
    return out, report


def point_in(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def centroid(r):
    return (sum(p[0] for p in r) / len(r), sum(p[1] for p in r) / len(r))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--locations")
    a = ap.parse_args()
    doc = json.load(open(a.src, encoding="utf-8"))
    locs = json.load(open(a.locations, encoding="utf-8"))["locations"] if a.locations else None
    out, report = process(doc, locs)
    json.dump(out, open(a.dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(out["stats"]))
    for r in report:
        flag = "INSIDE BUILDING" if r["inside_building"] else "ok"
        print(f"  location {r['id']}: {flag}; nearest named feature {r['nearest_named']} at {r['nearest_named_m']} m")
    return 0

if __name__ == "__main__":
    sys.exit(main())
