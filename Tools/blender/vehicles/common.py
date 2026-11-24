"""Shared helpers for the vehicle build: materials, mesh construction, subdivision, shading, glTF export."""
import math, os
import bpy, bmesh
import numpy as np
from mathutils import Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_DIR = os.path.join(REPO, "WebPreview", "assets", "vehicles")
RENDER_DIR = os.path.join(REPO, "docs", "vehicle_renders")

# name -> (base colour RGB, metallic, roughness, alpha, emissive RGB)
MATERIALS = {
    "car_paint":     ((1.00, 1.00, 1.00), 0.55, 0.26, 1.0, None),
    "car_glass":     ((0.03, 0.04, 0.045), 0.0, 0.06, 0.64, None),
    "car_trim":      ((0.022, 0.023, 0.025), 0.0, 0.55, 1.0, None),
    "car_chrome":    ((0.80, 0.81, 0.83), 1.0, 0.14, 1.0, None),
    "car_tyre":      ((0.028, 0.028, 0.03), 0.0, 0.85, 1.0, None),
    "car_rim":       ((0.64, 0.65, 0.67), 0.70, 0.34, 1.0, None),   # part-metallic so it stays silver under warm skies
    "car_headlight": ((0.85, 0.87, 0.90), 0.2, 0.12, 1.0, (1.0, 0.96, 0.88)),
    "car_taillight": ((0.45, 0.02, 0.02), 0.0, 0.22, 1.0, (0.85, 0.04, 0.02)),
    "car_interior":  ((0.045, 0.045, 0.05), 0.0, 0.8, 1.0, None),
    "car_plate":     ((1.0, 1.0, 1.0), 0.0, 0.5, 1.0, None),
    "bike_frame":    ((1.0, 1.0, 1.0), 0.3, 0.35, 1.0, None),
    "bike_metal":    ((0.74, 0.75, 0.77), 0.75, 0.32, 1.0, None),
    "bike_tyre":     ((0.03, 0.03, 0.032), 0.0, 0.85, 1.0, None),
    "bike_saddle":   ((0.05, 0.04, 0.035), 0.0, 0.7, 1.0, None),
    "rack_steel":    ((0.60, 0.61, 0.63), 0.70, 0.45, 1.0, None),
}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    col, metal, rough, alpha, emis = MATERIALS.get(name, ((0.5, 0.5, 0.5), 0.0, 0.6, 1.0, None))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1.0)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED" if hasattr(m, "surface_render_method") else m.surface_render_method
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
    if emis:
        b.inputs["Emission Color"].default_value = (*emis, 1.0)
        b.inputs["Emission Strength"].default_value = 1.0
    m.use_backface_culling = True
    return m


class Builder:
    """Accumulates polygons (any vertex count) with a material name per face and optional per-corner UVs."""

    def __init__(self):
        self.v, self.f, self.m, self.uv = [], [], [], []

    def vert(self, p):
        self.v.append(tuple(p)); return len(self.v) - 1

    def face(self, idx, mat, uv=None):
        self.f.append(tuple(idx)); self.m.append(mat); self.uv.append(uv)

    def quad(self, a, b, c, d, mat, uv=None):
        i = [self.vert(p) for p in (a, b, c, d)]
        self.face(i, mat, uv)

    def extend(self, other, xf=None):
        base = len(self.v)
        self.v.extend([tuple(xf(p)) if xf else p for p in other.v])
        for f, m, uv in zip(other.f, other.m, other.uv):
            self.face([base + i for i in f], m, uv)

    def box(self, c, size, mat, rot_z=0.0):
        cx, cy, cz = c; sx, sy, sz = (s / 2 for s in size)
        cs, sn = math.cos(rot_z), math.sin(rot_z)
        pts = []
        for dz in (-sz, sz):
            for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
                pts.append((cx + dx * cs - dy * sn, cy + dx * sn + dy * cs, cz + dz))
        i = [self.vert(p) for p in pts]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.face([i[k] for k in q], mat)

    def to_object(self, name, smooth=True):
        mats = []
        for m in self.m:
            if m not in mats:
                mats.append(m)
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in mats:
            me.materials.append(get_mat(m))
        idx = {m: i for i, m in enumerate(mats)}
        me.polygons.foreach_set("material_index", [idx[m] for m in self.m])
        if any(u is not None for u in self.uv):
            uvl = me.uv_layers.new(name="UVMap")
            for poly, fuv in zip(me.polygons, self.uv):
                if fuv is None:
                    continue
                for li, uvc in zip(poly.loop_indices, fuv):
                    uvl.data[li].uv = uvc
        if smooth:
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def lathe(b, profile, mat, segs=24, axis="x", centre=(0, 0, 0), cap_start=False, cap_end=False, flip=False, mats=None):
    """Revolve a (axial, radius) profile about an axis through centre. mats: optional per-profile-segment materials."""
    rings = []
    for a, r in profile:
        ring = []
        for s in range(segs):
            t = 2 * math.pi * s / segs
            c, sn = math.cos(t) * r, math.sin(t) * r
            p = {"x": (a, c, sn), "y": (sn, a, c), "z": (c, sn, a)}[axis]     # cyclic, so winding is kept
            ring.append(b.vert((p[0] + centre[0], p[1] + centre[1], p[2] + centre[2])))
        rings.append(ring)
    for k in range(len(rings) - 1):
        m = mats[k] if mats else mat
        for s in range(segs):
            q = [rings[k][s], rings[k][(s + 1) % segs], rings[k + 1][(s + 1) % segs], rings[k + 1][s]]
            b.face(q[::-1] if flip else q, m)
    if cap_start:
        b.face(rings[0] if flip else rings[0][::-1], mats[0] if mats else mat)
    if cap_end:
        b.face(rings[-1][::-1] if flip else rings[-1], mats[-1] if mats else mat)
    return rings


def tube(b, pts, radius, mat, segs=8, caps=True):
    """Sweep a circle of the given radius (float or per-point list) along a 3D polyline."""
    pts = [Vector(p) for p in pts]
    rad = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    rings = []
    prev_n = None
    for i, p in enumerate(pts):
        if i == 0: t = pts[1] - pts[0]
        elif i == len(pts) - 1: t = pts[-1] - pts[-2]
        else: t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        if prev_n is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n = t.cross(ref).normalized()
        else:
            n = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = n
        bn = t.cross(n)
        rings.append([b.vert(p + (n * math.cos(2 * math.pi * s / segs) + bn * math.sin(2 * math.pi * s / segs)) * rad[i]) for s in range(segs)])
    for k in range(len(rings) - 1):
        for s in range(segs):
            b.face([rings[k][s], rings[k][(s + 1) % segs], rings[k + 1][(s + 1) % segs], rings[k + 1][s]], mat)
    if caps:
        b.face(rings[0][::-1], mat); b.face(rings[-1], mat)
    return rings


def subdivide(ob, levels):
    """Apply Catmull-Clark subdivision (honours edge creases) and return the object with the new mesh."""
    mod = ob.modifiers.new("subd", "SUBSURF")
    mod.levels = levels; mod.render_levels = levels
    mod.subdivision_type = "CATMULL_CLARK"
    mod.boundary_smooth = "ALL"
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.remove(mod)
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob


def shade(ob, angle_deg=40.0, sharp_material_borders=()):
    """Smooth shading with edges sharper than angle_deg split (the exporter writes split normals)."""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    lim = math.radians(angle_deg)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = True
        if len(e.link_faces) == 2:
            if e.calc_face_angle(0.0) > lim:
                e.smooth = False
    bm.to_mesh(me); bm.free(); me.update()


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name; ob.data.name = name
    return ob


def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == "MESH")


def recalc_outside(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()


def pchip(knots):
    """Monotone cubic interpolant through (x, v) knots; clamps outside the range."""
    xs = np.array([k[0] for k in knots], float); vs = np.array([k[1] for k in knots], float)
    n = len(xs)
    if n == 1:
        return lambda x: float(vs[0])
    h = np.diff(xs); d = np.diff(vs) / h
    m = np.zeros(n)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]: return float(vs[0])
        if x >= xs[-1]: return float(vs[-1])
        i = int(np.searchsorted(xs, x) - 1)
        t = (x - xs[i]) / h[i]
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1; h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2; h11 = t ** 3 - t ** 2
        return float(h00 * vs[i] + h10 * h[i] * m[i] + h01 * vs[i + 1] + h11 * h[i] * m[i + 1])
    return f
