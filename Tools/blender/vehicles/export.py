"""glTF export and verification of the exported file (re-import into a fresh scene + raw GLB header checks)."""
import json, os, struct
import bpy
from mathutils import Vector


def export_glb(objs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
                              export_materials="EXPORT", export_normals=True, export_texcoords=True, export_tangents=False,
                              export_image_format="AUTO", export_animations=False, export_skins=False, export_morph=False,
                              export_cameras=False, export_lights=False, export_extras=False)
    return os.path.getsize(path)


def read_glb_json(path):
    with open(path, "rb") as f:
        magic, ver, length = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF"
        clen, ctype = struct.unpack("<II", f.read(8))
        return json.loads(f.read(clen))


def inspect(path):
    """Facts taken straight from the GLB container (glTF space: Y up)."""
    g = read_glb_json(path)
    acc = g["accessors"]
    out = {"bytes": os.path.getsize(path), "extensionsUsed": g.get("extensionsUsed", []), "nodes": {}, "materials": [m["name"] for m in g.get("materials", [])],
           "images": [{"name": i.get("name"), "mime": i.get("mimeType")} for i in g.get("images", [])], "triangles": 0}
    lo = [1e9] * 3; hi = [-1e9] * 3
    centroid = {}
    for n in g["nodes"]:
        t = n.get("translation", [0, 0, 0])
        info = {"translation": [round(v, 4) for v in t], "rotation": n.get("rotation"), "scale": n.get("scale")}
        if "mesh" in n:
            tris = 0
            for p in g["meshes"][n["mesh"]]["primitives"]:
                tris += acc[p["indices"]]["count"] // 3
                a = acc[p["attributes"]["POSITION"]]
                mn = [a["min"][i] + t[i] for i in range(3)]; mx = [a["max"][i] + t[i] for i in range(3)]
                lo = [min(lo[i], mn[i]) for i in range(3)]; hi = [max(hi[i], mx[i]) for i in range(3)]
                mat = g["materials"][p["material"]]["name"]
                c = centroid.setdefault(mat, [[1e9] * 3, [-1e9] * 3])
                c[0] = [min(c[0][i], mn[i]) for i in range(3)]; c[1] = [max(c[1][i], mx[i]) for i in range(3)]
            info["triangles"] = tris; out["triangles"] += tris
        out["nodes"][n["name"]] = info
    out["bbox_min"] = [round(v, 3) for v in lo]; out["bbox_max"] = [round(v, 3) for v in hi]
    out["size_xyz"] = [round(hi[i] - lo[i], 3) for i in range(3)]
    out["material_bounds"] = {k: [[round(x, 3) for x in v[0]], [round(x, 3) for x in v[1]]] for k, v in centroid.items()}
    out["material_details"] = {m["name"]: {"alphaMode": m.get("alphaMode", "OPAQUE"), "doubleSided": m.get("doubleSided", False),
                                           "baseColorFactor": m.get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1]),
                                           "metallic": m.get("pbrMetallicRoughness", {}).get("metallicFactor", 1.0),
                                           "roughness": m.get("pbrMetallicRoughness", {}).get("roughnessFactor", 1.0),
                                           "baseColorTexture": "baseColorTexture" in m.get("pbrMetallicRoughness", {}),
                                           "emissiveFactor": m.get("emissiveFactor"), "extensions": list(m.get("extensions", {}).keys())}
                               for m in g.get("materials", [])}
    return out


def reimport(path):
    """Fresh scene with the GLB imported; returns the mesh objects."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def mesh_health(objs):
    """Degenerate faces, loose geometry and inward-facing shell faces in the re-imported scene."""
    import bmesh
    rep = {"degenerate_faces": 0, "zero_normals": 0, "max_image_px": 0, "closed_parts": 0, "inside_out_closed_parts": 0}
    for o in objs:
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)       # undo the exporter's vertex splits
        rep["degenerate_faces"] += sum(1 for f in bm.faces if f.calc_area() < 1e-10)
        seen = set()
        for f0 in bm.faces:                                          # signed volume of every watertight island
            if f0.index in seen: continue
            stack, isl = [f0], []
            seen.add(f0.index)
            while stack:
                f = stack.pop(); isl.append(f)
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index not in seen: seen.add(g.index); stack.append(g)
            if all(len(e.link_faces) == 2 for f in isl for e in f.edges):
                vol = 0.0
                for f in isl:
                    v = [l.vert.co for l in f.loops]
                    for k in range(1, len(v) - 1): vol += v[0].dot(v[k].cross(v[k + 1])) / 6.0
                rep["closed_parts"] += 1
                if vol < 0: rep["inside_out_closed_parts"] += 1
        bm.free()
        o.data.calc_loop_triangles() if hasattr(o.data, "calc_loop_triangles") else None
        for cn in o.data.corner_normals:
            if cn.vector.length < 0.5: rep["zero_normals"] += 1
    for im in bpy.data.images:
        rep["max_image_px"] = max(rep["max_image_px"], *im.size)
    return rep
