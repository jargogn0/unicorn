#!/usr/bin/env python3
"""Convert an OSM API 0.6 XML extract (api.openstreetmap.org/api/0.6/map?bbox=…) into the
Overpass-style JSON that process_osm.py consumes (ways/relations with inline geometry).
Data © OpenStreetMap contributors, ODbL 1.0.

Usage: python3 Tools/geodata/osm_xml_to_overpass.py in.osm out.overpass.json S W N E
"""
import json, sys, xml.etree.ElementTree as ET

def main(src, dst, s, w, n, e):
    root = ET.parse(src).getroot()
    nodes = {nd.get("id"): (float(nd.get("lat")), float(nd.get("lon"))) for nd in root.findall("node")}
    ways = {}
    elements = []
    for nd in root.findall("node"):
        tags = {t.get("k"): t.get("v") for t in nd.findall("tag")}
        if tags:
            elements.append({"type": "node", "id": int(nd.get("id")), "lat": float(nd.get("lat")), "lon": float(nd.get("lon")), "tags": tags})
    for wy in root.findall("way"):
        refs = [r.get("ref") for r in wy.findall("nd")]
        geom = [{"lat": nodes[r][0], "lon": nodes[r][1]} for r in refs if r in nodes]
        ids = [int(r) for r in refs if r in nodes]
        tags = {t.get("k"): t.get("v") for t in wy.findall("tag")}
        ways[wy.get("id")] = geom
        if tags and len(geom) >= 2:
            elements.append({"type": "way", "id": int(wy.get("id")), "nodes": ids, "geometry": geom, "tags": tags})
    for rel in root.findall("relation"):
        tags = {t.get("k"): t.get("v") for t in rel.findall("tag")}
        members = [{"type": m.get("type"), "ref": int(m.get("ref")), "role": m.get("role"), "geometry": ways[m.get("ref")]}
                   for m in rel.findall("member") if m.get("type") == "way" and m.get("ref") in ways]
        if tags and members:
            elements.append({"type": "relation", "id": int(rel.get("id")), "members": members, "tags": tags})
    out = {"version": 0.6, "osm3s": {"timestamp_osm_base": root.get("generator", "osm api 0.6")},
           "_stockholm": {"bbox": [s, w, n, e], "endpoint": "https://api.openstreetmap.org/api/0.6/map", "license": "ODbL-1.0",
                          "attribution": "© OpenStreetMap contributors"}, "elements": elements}
    json.dump(out, open(dst, "w", encoding="utf-8"))
    print(f"{len(elements)} tagged elements")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7]))
