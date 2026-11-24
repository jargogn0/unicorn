#!/usr/bin/env python3
"""STOCKHOLM vehicle build: procedural cars, city bicycle and bike rack -> game-ready GLB.

    python3 Tools/blender/build_vehicles.py                    # build + export + verify everything
    python3 Tools/blender/build_vehicles.py --only car_estate  # comma-separated subset
    python3 Tools/blender/build_vehicles.py --renders          # also write Cycles QA renders (docs/vehicle_renders)

Needs the `bpy` Python module (developed on Blender 5.3, headless, CPU only), numpy and Pillow.
Outputs: WebPreview/assets/vehicles/<name>.glb and vehicles_report.json next to them, plus Assets/ThirdParty/vehicle_manifest.json.
Contract: glTF Y-up, metres, origin on the ground at the footprint centre, front along -Z, right side +X.
Cars: nodes body, wheel_fl, wheel_fr, wheel_rl, wheel_rr (wheel origins at the wheel centres, axle = local X).
The modelling code lives in Tools/blender/vehicles/ (car_body = shell cage, car_specs = dimension tables,
car_parts = wheels/interior/trim, bicycle, bike_rack, textures, export, render_qa).
"""
import argparse, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from vehicles import common as C, car, car_specs, bicycle, bike_rack, export as EX  # noqa: E402

CARS = {"car_estate": car_specs.estate, "car_sedan": car_specs.sedan, "car_hatch": car_specs.hatch}
OTHERS = {"bicycle": bicycle.build, "bike_rack": bike_rack.build}
TINTS = {"car_estate": (0.03, 0.10, 0.07), "car_sedan": (0.42, 0.44, 0.47), "car_hatch": (0.30, 0.03, 0.03),
         "bicycle": (0.02, 0.09, 0.22), "bike_rack": None}


def build_one(name, work):
    C.reset_scene()
    if name in CARS:
        body, wheels = car.build_car(CARS[name](), work)
        objs = [body] + wheels
    else:
        objs = OTHERS[name](work)
    path = os.path.join(C.OUT_DIR, name + ".glb")
    EX.export_glb(objs, path)
    rep = EX.inspect(path)
    rep.update(EX.mesh_health(EX.reimport(path)))
    return rep


def write_manifest(report):
    """Assets/ThirdParty/vehicle_manifest.json: what was authored here and every third-party input."""
    import datetime
    described = {
        "car_estate": "Generic modern estate car (station wagon). Original design, no manufacturer badge or logo.",
        "car_sedan": "Saloon variant of the same base: lower rear roofline, rear screen, boot lid.",
        "car_hatch": "Compact five-door hatchback variant: shorter wheelbase and tail, no quarter glass.",
        "bicycle": "City bicycle: diamond frame, 28 inch wheels, mudguards, chain guard, carrier, kickstand.",
        "bike_rack": "Row of five galvanised steel hoops on ground rails.",
    }
    man = {
        "generated_by": "Tools/blender/build_vehicles.py (modelling code in Tools/blender/vehicles/)",
        "date": datetime.date.today().isoformat(),
        "licence_summary": "All geometry and textures in these files were authored procedurally in this repository; no third-party model, "
                           "texture or logo is contained in any GLB. The only third-party input to the shipped files is a font used to rasterise "
                           "the fictional number plate text.",
        "authored_here": [
            {"file": f"WebPreview/assets/vehicles/{n}.glb", "description": described.get(n, ""), "author": "STOCKHOLM project (generated in Blender by build_vehicles.py)",
             "licence": "Project-owned original work", "triangles": r["triangles"], "bytes": r["bytes"], "size_xyz_m_gltf": r["size_xyz"],
             "nodes": list(r["nodes"]), "materials": r["materials"], "embedded_images": [i["name"] for i in r["images"]]}
            for n, r in report.items()],
        "embedded_textures": "paint_<variant>.png (512 px shut-line atlas), lamp_head_base/emis.png and lamp_tail_base/emis.png (256x128), plate.png (512x112): "
                             "all drawn by Tools/blender/vehicles/textures.py with Pillow.",
        "number_plate": "Fictional registration 'STH 47K' on a plain plate with a blank blue band (no national or EU emblem).",
        "third_party": [
            {"name": "DejaVu Sans Bold (font)", "author": "DejaVu fonts team, based on Bitstream Vera (Bitstream Inc.)", "licence": "Bitstream Vera / DejaVu Fonts License (free, permissive)",
             "url": "https://dejavu-fonts.github.io/License.html", "used_for": "Rasterising the plate text into plate.png (the font file itself is not shipped). "
             "textures.py falls back to Liberation Sans Bold, FreeSans Bold or Pillow's built-in font if it is missing."},
            {"name": "Snowy Park 01 (HDRI)", "author": "Poly Haven (see Assets/ThirdParty/polyhaven_manifest.json)", "licence": "CC0 1.0", "url": "https://polyhaven.com/a/snowy_park_01",
             "used_for": "Lighting of the QA renders in docs/vehicle_renders only (WebPreview/assets/hdri/snowy_park_01.jpg); not part of any vehicle file."},
            {"name": "Blender (bpy) 5.3, Pillow, numpy", "licence": "GPL-2.0-or-later / MIT-CMU / BSD-3-Clause (build tools only, not redistributed)", "url": "https://www.blender.org/",
             "used_for": "Mesh construction, Catmull-Clark subdivision, glTF export, Cycles QA renders, texture drawing."},
        ],
        "sourcing_check": {
            "performed": "2026-11-23", "conclusion": "No realistic, redistributable (CC0 / CC BY) car or bicycle model was downloadable without a login, so everything was modelled here.",
            "checked": [
                {"source": "Poly Haven model list (api.polyhaven.com/assets?t=models, 522 models)", "result": "No car or bicycle. Only 'covered_car' (a car hidden under a tarpaulin), 'old_tyre' and two rusted wheel rims. Not used."},
                {"source": "ambientCG 3D models (API)", "result": "No car, bicycle or vehicle models. Not used."},
                {"source": "Khronos glTF-Sample-Assets", "result": "'CarConcept' (CC BY 4.0, futuristic concept supercar with Khronos trademarks, needs KHR material extensions) and 'ToyCar' (a toy). Neither is a realistic estate car. Not used."},
                {"source": "OpenGameArt (3D art search: car, bicycle)", "result": "Reachable, but results were toon / low-poly kits, a muscle car from a Wii game, a named real make, and an 820-triangle toon bicycle. Rejected as stylised or carrying a real marque. Not used."},
                {"source": "Sketchfab, Fab, Quixel", "result": "Downloads need a login. Not used."},
                {"source": "Wikimedia Commons, free3d", "result": "Requests refused (HTTP 429 / 403) from this environment. Not used."},
            ],
        },
    }
    path = os.path.join(C.REPO, "Assets", "ThirdParty", "vehicle_manifest.json")
    json.dump(man, open(path, "w"), indent=1)
    return path


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only"); ap.add_argument("--renders", action="store_true"); ap.add_argument("--work")
    a = ap.parse_args(argv)
    names = a.only.split(",") if a.only else list(CARS) + list(OTHERS)
    work = a.work or tempfile.mkdtemp(prefix="vehicles_")
    os.makedirs(work, exist_ok=True); os.makedirs(C.OUT_DIR, exist_ok=True)
    report_path = os.path.join(C.OUT_DIR, "vehicles_report.json")
    report = json.load(open(report_path)) if os.path.exists(report_path) else {}
    for n in names:
        report[n] = build_one(n, work)
        r = report[n]
        print(f"BUILT {n}: {r['triangles']} tris, {r['bytes'] / 1024:.0f} KB, size {r['size_xyz']}, nodes {list(r['nodes'])}, ext {r['extensionsUsed']}")
    json.dump(report, open(report_path, "w"), indent=1)
    write_manifest({n: report[n] for n in list(CARS) + list(OTHERS) if n in report})
    if a.renders:
        os.makedirs(C.RENDER_DIR, exist_ok=True)
        for n in names:
            cmd = [sys.executable, os.path.join(HERE, "vehicles", "render_glb.py"), os.path.join(C.OUT_DIR, n + ".glb"), C.RENDER_DIR, n]
            if TINTS.get(n): cmd += ["--tint", ",".join(str(v) for v in TINTS[n])]
            subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]))
