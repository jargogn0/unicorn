"""Headless Blender: turn Poly Haven glTF downloads (CC0) into single, game-ready GLB props.

Some downloads are kits or exploded layouts, so each prop has an assembly rule:
  bench      <- modular_street_seating: seat plank on two leg frames, back rest on supports
  trash_can  <- metal_trash_can: the clean can body with its lid placed on top
  others     <- kept as authored (origin re-centred on the ground footprint)
Textures are reduced to 512 px JPEG. Reports real-world dimensions for validation.

Usage: python3 Tools/blender/pack_props.py Assets/ThirdParty/polyhaven/models WebPreview/assets/props
"""
import bpy, pathlib, sys, json, math
from mathutils import Vector

src, out = pathlib.Path(sys.argv[-2]), pathlib.Path(sys.argv[-1]); out.mkdir(parents=True, exist_ok=True)
report = {}


def load(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(next((src / name).glob("*.gltf"))))
    for img in bpy.data.images:
        if img.size[0] > 512: img.scale(512, 512)
    return {o.name: o for o in bpy.context.scene.objects if o.type == "MESH"}


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def centre_on_ground(objs):
    bpy.context.view_layer.update()
    lo, hi = bounds(objs)
    off = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    for o in objs:
        if o.parent is None or o.parent not in objs: o.location += off
    bpy.context.view_layer.update()


def put(o, loc, rot=(0, 0, 0)):
    """Place an object so its bounding-box centre sits at loc (after rotation)."""
    o.parent = None; o.rotation_mode = "XYZ"; o.rotation_euler = rot; o.location = (0, 0, 0)
    bpy.context.view_layer.update()
    lo, hi = bounds([o]); c = (lo + hi) / 2
    o.location = Vector(loc) - c
    bpy.context.view_layer.update()


def dup(o):
    c = o.copy(); bpy.context.scene.collection.objects.link(c); return c


def export(name, keep):
    for o in list(bpy.context.scene.objects):
        if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
    centre_on_ground(keep)
    lo, hi = bounds(keep)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in keep)
    bpy.ops.export_scene.gltf(filepath=str(out / f"{name}.glb"), export_format="GLB", export_image_format="JPEG", export_jpeg_quality=80)
    report[name] = {"size_xyz_m": [round(hi[i] - lo[i], 2) for i in range(3)], "triangles": tris, "kb": (out / f"{name}.glb").stat().st_size // 1024}
    print(name, report[name])


# --- bench assembled from the modular seating kit -------------------------------------------------
o = load("modular_street_seating")
seat = o["seat_bench"]; back = o["seat_back"]; legs = [o["legs_double"], dup(o["legs_double"])]; sup = [o["back_support_l"], o["back_support_r"]]
put(legs[0], (-0.72, 0, 0.225)); put(legs[1], (0.72, 0, 0.225))
put(seat, (0, 0, 0.46))
put(sup[0], (-0.72, 0.24, 0.69)); put(sup[1], (0.72, 0.24, 0.69))
put(back, (0, 0.27, 0.78), (math.radians(80), 0, 0))
export("bench", [seat, back, *legs, *sup])

# --- trash can with its lid on ----------------------------------------------------------------------
o = load("metal_trash_can")
can = o["metal_trash_can"]; lid = o["metal_trash_can_lid"]
put(can, (0, 0, 0.455)); put(lid, (0, 0, 0.93))
export("trash_can", [can, lid])

# --- props kept as authored ---------------------------------------------------------------------------
for name, dst in (("standing_chalkboard_01", "chalkboard"), ("outdoor_table_chair_set_01", "cafe_table_set"), ("planter_box_01", "planter"),
                  ("utility_box_01", "utility_box"), ("water_manhole_cover", "manhole_cover"), ("street_lamp_01", "street_lamp_post"), ("street_lamp_02", "street_lantern")):
    o = load(name); export(dst, list(o.values()))
(out / "props_report.json").write_text(json.dumps(report, indent=1))
