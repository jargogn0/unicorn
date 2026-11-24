"""Assemble a complete car from a spec: shell, details, interior and four wheel nodes."""
import math, os
import bpy, bmesh
from mathutils import Vector
from . import common as C, car_body, car_parts as P, textures as T


def _design(v, L):          # Blender -> design frame
    return (L / 2 - v.y, v.x, v.z)


def paint_uvs(ob, L):
    """Planar-projected UVs into the paint atlas, the projection chosen per face from its normal."""
    me = ob.data
    uvl = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    lamp = {i for i, m in enumerate(me.materials) if m.name in ("car_headlight", "car_taillight")}
    for poly in me.polygons:
        if poly.material_index in lamp: continue
        n = poly.normal
        if n.z > 0.62: mode = "top"
        elif abs(n.y) > 0.72: mode = "front" if n.y > 0 else "rear"
        else: mode = "side"
        for li in poly.loop_indices:
            x, y, z = _design(me.vertices[me.loops[li].vertex_index].co, L)
            uvl.data[li].uv = {"top": T.uv_top(x, y), "side": T.uv_side(x, z), "front": T.uv_front(y, z), "rear": T.uv_rear(y, z)}[mode]


def build_car(spec, work_dir, plate_text="STH 47K"):
    L = spec["L"]
    body, cage = car_body.build_body(spec, 2)
    P.arch_fix(body, spec)

    def dx(f): return L / 2 - f.calc_center_median().y
    def in_grille(f, name):
        c = f.calc_center_median()
        return name == "car_trim" and dx(f) < 0.35 and abs(c.x) < 0.6 and c.z > spec["grille_z"][0]
    def in_intake(f, name):
        c = f.calc_center_median()
        return name == "car_trim" and dx(f) < 0.35 and c.z <= spec["grille_z"][0] and c.z > spec["under_z"] + 0.06
    P.recess(body, lambda f, n: in_grille(f, n) or in_intake(f, n), 0.028)
    pz = spec["plate_z"][1]
    pd = spec.get("plate_recess", 0.016)
    if pd:
        P.push_region(body, lambda co: co.y < -L / 2 + 0.25 and abs(co.x) < 0.30 and abs(co.z - pz) < 0.075, (0, pd, 0))
    paint_uvs(body, L)
    surf = P.Surface(body, L)

    parts = [body]
    parts.append(P.wheel_liners(spec))
    parts += P.interior(spec, surf)
    parts.append(P.mirrors(spec, surf))
    parts.append(P.door_handles(spec, surf))
    if spec.get("rails"):
        parts.append(P.roof_rails(spec, surf))
    parts.append(P.small_details(spec, surf))
    plate_img = T.load(T.plate(os.path.join(work_dir, "plate.png"), plate_text), "car_plate_tex")
    parts.append(P.plates(spec, surf, plate_img))

    def is_dlo(f, name):
        if abs(f.normal.x) < 0.5: return False
        return name == "car_glass" or (name == "car_trim" and f.calc_center_median().z > 0.9)
    r = P.border_ribbon(body, is_dlo, lambda f, n: n == "car_paint", "car_chrome", width=0.016, lift=0.003, name="dlo_trim")
    if r: parts.append(r)
    r = P.border_ribbon(body, in_grille, lambda f, n: not in_grille(f, n), "car_chrome", width=0.015, lift=0.004, name="grille_frame")
    if r: parts.append(r)
    g0, g1 = spec["grille_z"]
    nb = spec.get("grille_bars", 8)
    r = P.slats(body, in_grille, [g0 + (g1 - g0) * (k + 0.75) / (nb + 0.5) for k in range(nb)], "car_chrome", height=0.0045, lift=0.014, name="grille_bars")
    if r: parts.append(r)

    # paint atlas
    atlas = T.load(T.paint_atlas(spec["lines"], os.path.join(work_dir, f"paint_{spec['name']}.png")), f"car_paint_lines_{spec['name']}")
    pm = C.get_mat("car_paint")
    tn = pm.node_tree.nodes.get("PaintTex") or pm.node_tree.nodes.new("ShaderNodeTexImage")
    tn.name = "PaintTex"; tn.image = atlas
    pm.node_tree.links.new(tn.outputs["Color"], pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])

    T.lamp_materials(work_dir)
    for o in parts:
        if not o.data.uv_layers: o.data.uv_layers.new(name="UVMap"); [setattr(d, "uv", (0.004, 0.004)) for d in o.data.uv_layers[0].data]
    C.shade(body, 42)
    for o in parts[1:]:
        C.shade(o, 38)
    body = C.join(parts, "body")

    wheels = []
    meshes = {}
    for name, sx, ax in (("wheel_fl", -1, spec["axle_f"]), ("wheel_fr", 1, spec["axle_f"]), ("wheel_rl", -1, spec["axle_r"]), ("wheel_rr", 1, spec["axle_r"])):
        if sx not in meshes:
            w = P.wheel_builder(sx).to_object("wheel_L" if sx < 0 else "wheel_R")
            C.shade(w, 35)
            meshes[sx] = w.data
            ob = w
        else:
            ob = bpy.data.objects.new(name, meshes[sx]); bpy.context.scene.collection.objects.link(ob)
        ob.name = name
        ob.location = (sx * spec["track"], L / 2 - ax, P.TYRE_R)
        wheels.append(ob)
    return body, wheels
