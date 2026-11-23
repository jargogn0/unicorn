#!/usr/bin/env python3
"""Download CC0 assets from Poly Haven (https://polyhaven.com, licence CC0 1.0) and record a manifest.

Raw downloads go to Assets/ThirdParty/polyhaven/ (git-ignored; re-run this script to restore them).
The manifest (Assets/ThirdParty/polyhaven_manifest.json) is committed and lists every file, URL and licence.

Usage: python3 Tools/assets/fetch_polyhaven.py
"""
import json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "Assets" / "ThirdParty" / "polyhaven"
API = "https://api.polyhaven.com"
UA = {"User-Agent": "stockholm-game-assets/0.1"}

TEXTURES = ["painted_plaster_wall", "white_plaster_02", "brick_wall_10", "brick_wall_006", "granite_wall", "asphalt_02",
            "asphalt_snow", "concrete_pavement", "cobblestone_floor_08", "snow_02", "box_profile_metal_sheet", "grey_roof_01", "bark_willow"]
HDRIS = ["winter_evening", "snowy_park_01"]
MODELS = ["street_lamp_01", "street_lamp_02", "modular_street_seating", "metal_trash_can", "standing_chalkboard_01",
          "outdoor_table_chair_set_01", "planter_box_01", "utility_box_01", "water_manhole_cover"]


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def fetch(url, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.stat().st_size == 0:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
            dst.write_bytes(r.read())
    return dst.stat().st_size


def main():
    manifest = {"source": "Poly Haven", "licence": "CC0 1.0 Universal (public domain dedication)",
                "licence_url": "https://polyhaven.com/license", "assets": []}
    for tid in TEXTURES:
        files = get_json(f"{API}/files/{tid}")
        info = get_json(f"{API}/info/{tid}")
        entry = {"id": tid, "type": "texture", "name": info.get("name"), "authors": list(info.get("authors", {})),
                 "page": f"https://polyhaven.com/a/{tid}", "files": []}
        for key in ("Diffuse", "nor_gl", "arm", "Rough"):
            node = files.get(key, {}).get("1k", {}).get("jpg")
            if not node:
                continue
            dst = OUT / "textures" / tid / pathlib.Path(node["url"]).name
            entry["files"].append({"map": key, "url": node["url"], "bytes": fetch(node["url"], dst), "path": str(dst.relative_to(ROOT))})
        manifest["assets"].append(entry); print("texture", tid, len(entry["files"]), "maps")
    for hid in HDRIS:
        files = get_json(f"{API}/files/{hid}"); info = get_json(f"{API}/info/{hid}")
        node = files["hdri"]["1k"]["hdr"]
        dst = OUT / "hdris" / pathlib.Path(node["url"]).name
        manifest["assets"].append({"id": hid, "type": "hdri", "name": info.get("name"), "authors": list(info.get("authors", {})),
                                   "page": f"https://polyhaven.com/a/{hid}",
                                   "files": [{"url": node["url"], "bytes": fetch(node["url"], dst), "path": str(dst.relative_to(ROOT))}]})
        print("hdri", hid)
    for mid in MODELS:
        files = get_json(f"{API}/files/{mid}"); info = get_json(f"{API}/info/{mid}")
        node = files["gltf"]["1k"]["gltf"]
        base = OUT / "models" / mid
        entry = {"id": mid, "type": "model", "name": info.get("name"), "authors": list(info.get("authors", {})),
                 "page": f"https://polyhaven.com/a/{mid}", "polycount": info.get("polycount"), "files": []}
        dst = base / pathlib.Path(node["url"]).name
        entry["files"].append({"url": node["url"], "bytes": fetch(node["url"], dst), "path": str(dst.relative_to(ROOT))})
        for rel, inc in node.get("include", {}).items():
            d2 = base / rel
            entry["files"].append({"url": inc["url"], "bytes": fetch(inc["url"], d2), "path": str(d2.relative_to(ROOT))})
        manifest["assets"].append(entry); print("model", mid, len(entry["files"]), "files")
    (ROOT / "Assets" / "ThirdParty").mkdir(parents=True, exist_ok=True)
    (ROOT / "Assets" / "ThirdParty" / "polyhaven_manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(f["bytes"] for a in manifest["assets"] for f in a["files"])
    print(f"{len(manifest['assets'])} assets, {total / 1e6:.1f} MB")

if __name__ == "__main__":
    sys.exit(main())
