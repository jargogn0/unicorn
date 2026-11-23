"""Headless Blender: prepare GLB blockouts/models for Unreal Engine 5.

- Optionally fixes assets authored Z-up but saved as Y-up glTF (--zup-authored), which import lying on their side.
- Applies transforms, reports real-world dimensions (metres) for validation against the art specs,
- Exports FBX (UE imports metres→cm correctly from Blender's default unit settings) and a corrected GLB.

Usage (Blender as a Python module, `pip install bpy`, or `blender -b -P`):
  python3 Tools/blender/glb_to_ue_fbx.py --in A.glb --out-dir OUT [--zup-authored]
"""
import argparse, json, math, pathlib, sys
import bpy
from mathutils import Vector


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True, nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--zup-authored", action="store_true")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    report = {}
    for src in a.src:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=src)
        roots = [o for o in bpy.context.scene.objects if o.parent is None]
        if a.zup_authored:
            # glTF import already rotated +90° about X (Y-up → Z-up); undo it for Z-up-authored data.
            # glTF import maps the file's +Z (authored "up") to Blender -Y; rotate -90° about X so it points to +Z.
            # The importer leaves objects in quaternion mode, so switch to Euler before editing.
            for o in roots:
                o.rotation_mode = "XYZ"
                o.rotation_euler[0] -= math.pi / 2
        bpy.ops.object.select_all(action="SELECT")
        bpy.context.view_layer.objects.active = next((o for o in bpy.context.scene.objects if o.type == "MESH"), None)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
        meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        for o in meshes:
            for v in o.bound_box:
                w = o.matrix_world @ Vector(v)
                lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
        dims = [round(hi[i] - lo[i], 3) for i in range(3)]
        name = pathlib.Path(src).stem
        bpy.ops.export_scene.fbx(filepath=str(out / f"{name}.fbx"), use_selection=False, apply_unit_scale=True,
                                 bake_space_transform=False, object_types={"MESH", "EMPTY"}, mesh_smooth_type="FACE",
                                 add_leaf_bones=False, path_mode="COPY", embed_textures=True)
        bpy.ops.export_scene.gltf(filepath=str(out / f"{name}.glb"), export_format="GLB")
        report[name] = {"meshes": len(meshes), "size_xyz_m": dims, "min_z_m": round(lo[2], 3)}
        print(f"{name}: {len(meshes)} meshes, size X×Y×Z = {dims} m (Z up), lowest point z = {lo[2]:.3f} m")
    (out / "conversion_report.json").write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
