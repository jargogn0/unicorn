"""Everything on a car that is not the subdivided shell: wheels, arch lips and liners, interior, mirrors,
lights detail, trim strips, plates. Parts are authored in the design frame (see car_body) unless noted."""
import math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from .common import Builder, lathe, tube, get_mat, shade, subdivide
from .car_body import to_bl, Cage, GLASS_NAME

TYRE_R, TYRE_W, RIM_R = 0.33, 0.225, 0.236


# ----------------------------------------------------------------------------------------- wheels
def wheel_builder(side=1, spokes=5, tyre_r=TYRE_R, tyre_w=TYRE_W, rim_r=RIM_R, segs=28):
    """Wheel centred on the origin, axle along Blender X, outer face towards side * X."""
    b = Builder()
    w, R, r = tyre_w / 2, tyre_r, rim_r
    sw = R - r
    prof = [(-w * 0.93, r), (-w * 0.995, r + sw * 0.28), (-w, r + sw * 0.62), (-w * 0.94, R - sw * 0.14), (-w * 0.78, R - 0.004), (-w * 0.3, R),
            (w * 0.3, R), (w * 0.78, R - 0.004), (w * 0.94, R - sw * 0.14), (w, r + sw * 0.62), (w * 0.995, r + sw * 0.28), (w * 0.93, r)]
    lathe(b, prof, "car_tyre", segs)
    # rim: outer lip, dropped barrel (seen from outside through the spokes), inner lip
    ao = w * 0.93
    rim = [(ao, r), (ao + 0.004, r - 0.012), (ao - 0.012, r - 0.02), (ao - 0.05, r - 0.026), (-ao + 0.01, r - 0.026), (-ao, r)]
    lathe(b, rim, "car_rim", segs)
    # dark brake disc / hub carrier behind the spokes so the wheel is not see-through
    b_disc = [(ao - 0.075, r - 0.026), (ao - 0.075, 0.0001)]
    lathe(b, b_disc, "car_trim", segs)
    lathe(b, [(ao - 0.062, 0.168), (ao - 0.062, 0.075)], "car_rim", segs)     # brake disc face
    lathe(b, [(ao - 0.075, 0.172), (ao - 0.062, 0.168)], "car_rim", segs)
    # hub
    hub = [(ao - 0.07, 0.075), (ao - 0.022, 0.07), (ao - 0.014, 0.058), (ao - 0.012, 0.03), (ao - 0.012, 0.0001)]
    lathe(b, hub, "car_rim", 14)
    # spokes: pairs splaying from the hub to the rim
    def P(a, rad, ang):
        return (a, rad * math.cos(ang), rad * math.sin(ang))
    for k in range(spokes):
        base = 2 * math.pi * k / spokes + math.pi / 2
        for s in (-1, 1):
            a0, a1 = base + s * math.radians(9), base + s * math.radians(24)
            stn = []
            for t in (0.0, 0.5, 1.0):
                rad = 0.062 + (r - 0.022 - 0.062) * t
                ang = a0 + (a1 - a0) * t
                wd = math.radians(7.5 - 3.6 * t) * 0.062 / rad * 3.0 if t == 0 else 0.019 / rad
                af = ao - 0.02 - 0.012 * math.sin(math.pi * t) + 0.012 * t
                stn.append((P(af, rad, ang - wd), P(af, rad, ang + wd), P(af - 0.035, rad, ang + wd * 1.5), P(af - 0.035, rad, ang - wd * 1.5)))
            for u, v in zip(stn, stn[1:]):
                b.quad(u[0], v[0], v[1], u[1], "car_rim")       # face
                b.quad(u[1], v[1], v[2], u[2], "car_rim")       # sides
                b.quad(u[3], v[3], v[0], u[0], "car_rim")
    if side < 0:
        b.v = [(-x, y, z) for x, y, z in b.v]
        b.f = [f[::-1] for f in b.f]
    return b


# ----------------------------------------------------------------------------------------- body post-processing
def arch_fix(ob, spec, lip=0.03):
    """Snap the subdivided arch openings to true circles and fold a lip inwards."""
    L, R, zw = spec["L"], spec["arch_r"], spec["wheel_z"]
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    paint = [i for i, m in enumerate(me.materials) if m.name == "car_paint"][0]
    for ax in (spec["axle_f"], spec["axle_r"]):
        cy = L / 2 - ax
        ring = set()
        for e in bm.edges:
            if not e.is_boundary: continue
            ok = True
            for v in e.verts:
                d = math.hypot(v.co.y - cy, v.co.z - zw)
                if abs(d - R) > 0.045 or v.co.z < zw - R * 0.5: ok = False
            if ok: ring.add(e)
        verts = {v for e in ring for v in e.verts}
        moved = {}
        for v in verts:
            d = math.hypot(v.co.y - cy, v.co.z - zw)
            k = R / d
            new = Vector((v.co.x, cy + (v.co.y - cy) * k, zw + (v.co.z - zw) * k))
            moved[v] = new - v.co
        for v in verts:                                   # relax the next ring by half the correction
            for e in v.link_edges:
                o = e.other_vert(v)
                if o not in moved and not o.is_boundary: o.co += moved[v] * 0.5
        for v, d in moved.items(): v.co += d
        new_v = {}
        for v in verts:
            sx = 1.0 if v.co.x > 0 else -1.0
            k = (R - 0.006) / R
            new_v[v] = bm.verts.new((v.co.x - sx * lip, cy + (v.co.y - cy) * k, zw + (v.co.z - zw) * k))
        for e in ring:
            a, c = e.verts
            f = bm.faces.new((a, c, new_v[c], new_v[a]))
            f.material_index = paint; f.smooth = True
            f.normal_update()
            fc = f.calc_center_median()
            if f.normal.dot(Vector((0, cy - fc.y, zw - fc.z))) < 0: f.normal_flip()
    bm.to_mesh(me); bm.free(); me.update()


def recess(ob, test, depth):
    """Push vertices whose every face passes test(face, material name) inwards along their normals."""
    me = ob.data
    names = [m.name for m in me.materials]
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    sel = [v for v in bm.verts if v.link_faces and all(test(f, names[f.material_index]) for f in v.link_faces)]
    for v in sel:
        v.co -= v.normal * depth
    bm.to_mesh(me); bm.free(); me.update()
    return len(sel)


def push_region(ob, inside, depth_vec):
    me = ob.data
    for v in me.vertices:
        if inside(v.co): v.co += Vector(depth_vec)
    me.update()


class Surface:
    """Ray-cast queries on the finished shell, in design-frame coordinates."""

    def __init__(self, ob, L):
        self.L = L
        dg = bpy.context.evaluated_depsgraph_get()
        self.bvh = BVHTree.FromObject(ob, dg)

    def _cast(self, o, d):
        hit = self.bvh.ray_cast(Vector(to_bl(o, self.L)), Vector((d[1], -d[0], d[2])))
        if hit[0] is None: return None, None
        p, n = hit[0], hit[1]
        return (self.L / 2 - p.y, p.x, p.z), (-n.y, n.x, n.z)

    def side(self, x, z, sgn=1.0):
        return self._cast((x, sgn * 3.0, z), (0, -sgn, 0))

    def top(self, x, y):
        return self._cast((x, y, 3.0), (0, 0, -1))

    def front(self, y, z):
        return self._cast((-2.0, y, z), (1, 0, 0))

    def rear(self, y, z):
        return self._cast((self.L + 2.0, y, z), (-1, 0, 0))


def border_ribbon(ob, is_a, is_b, mat, width=0.014, lift=0.004, name="ribbon"):
    """Thin strip along every edge that separates a face passing is_a from one passing is_b."""
    me = ob.data
    names = [m.name for m in me.materials]
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    edges = []
    for e in bm.edges:
        if len(e.link_faces) != 2: continue
        f0, f1 = e.link_faces
        for fa, fb in ((f0, f1), (f1, f0)):
            if is_a(fa, names[fa.material_index]) and is_b(fb, names[fb.material_index]):
                edges.append((e, fa)); break
    dirs = {}
    for e, fa in edges:
        ev = (e.verts[1].co - e.verts[0].co).normalized()
        n = (e.link_faces[0].normal + e.link_faces[1].normal).normalized()
        d = n.cross(ev).normalized()
        if d.dot(fa.calc_center_median() - (e.verts[0].co + e.verts[1].co) / 2) < 0: d = -d
        for v in e.verts:
            acc = dirs.setdefault(v.index, [Vector(), Vector(), v.co.copy()])
            acc[0] += d; acc[1] += n
    b = Builder()
    for e, fa in edges:
        pts = []
        for v in e.verts:
            d, n, co = dirs[v.index]
            d = d.normalized(); n = n.normalized()
            pts.append((co + n * lift + d * width * 0.5, co + n * lift - d * width * 0.5))
        (a0, a1), (c0, c1) = pts
        q = [a0, c0, c1, a1]
        nn = (c0 - a0).cross(a1 - a0)
        if nn.dot(dirs[e.verts[0].index][1]) < 0: q = q[::-1]
        b.quad(*q, mat)
    bm.free()
    return b.to_object(name) if b.f else None


def slats(ob, inside, zs, mat, height=0.012, lift=0.012, name="slats"):
    """Horizontal bars across a region of the shell: cut the faces passing inside() at each z."""
    me = ob.data
    names = [m.name for m in me.materials]
    b = Builder()
    for zc in zs:
        bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
        drop = [f for f in bm.faces if not inside(f, names[f.material_index])]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, zc), plane_no=(0, 0, 1))
        cut = [g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMEdge)]
        for e in cut:
            a, c = sorted(e.verts, key=lambda v: v.co.x)
            n = Vector((0, 1, 0)) if a.co.y > 0 else Vector((0, -1, 0))
            pa, pc = a.co + n * lift, c.co + n * lift
            up = Vector((0, 0, height / 2))
            q = [pa - up, pc - up, pc + up, pa + up]
            if (q[1] - q[0]).cross(q[3] - q[0]).dot(n) < 0: q = q[::-1]
            b.quad(*q, mat)
        bm.free()
    return b.to_object(name, smooth=False) if b.f else None


# ----------------------------------------------------------------------------------------- simple solids
def obox(b, c, size, mat, pitch=0.0, xf=None):
    """Box centred at c (design frame), pitched about the lateral axis (positive leans the top rearwards)."""
    sx, sy, sz = (s / 2 for s in size)
    cs, sn = math.cos(pitch), math.sin(pitch)
    pts = []
    for dz in (-sz, sz):
        for dx, dy in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
            pts.append((c[0] + dx * cs + dz * sn, c[1] + dy, c[2] - dx * sn + dz * cs))
    if xf: pts = [xf(p) for p in pts]
    i = [b.vert(p) for p in pts]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        b.face([i[k] for k in q], mat)


def blob(b, c, radii, mat, power=2.6, nu=10, nv=6, xf=None):
    """Superellipsoid (rounded box) centred at c with the given semi-axes."""
    e = 2.0 / power
    def sp(v): return math.copysign(abs(v) ** e, v)
    grid = []
    for iv in range(nv + 1):
        ph = -math.pi / 2 + math.pi * iv / nv
        row = []
        for iu in range(nu):
            th = 2 * math.pi * iu / nu
            p = (c[0] + radii[0] * sp(math.cos(ph)) * sp(math.cos(th)), c[1] + radii[1] * sp(math.cos(ph)) * sp(math.sin(th)), c[2] + radii[2] * sp(math.sin(ph)))
            row.append(b.vert(xf(p) if xf else p))
        grid.append(row)
    for iv in range(nv):
        for iu in range(nu):
            q = [grid[iv][iu], grid[iv][(iu + 1) % nu], grid[iv + 1][(iu + 1) % nu], grid[iv + 1][iu]]
            if iv == 0: q = [q[0], q[2], q[3]]
            elif iv == nv - 1: q = [q[0], q[1], q[2]]
            b.face(q, mat)


def interior(spec, surf):
    """Dark inner shell (a coarser copy of the cabin skin, facing inwards) plus floor, dashboard, seats, wheel."""
    L = spec["L"]
    names = {st["name"]: i for i, st in enumerate(spec["stations"])}

    def filt(cage, kind, a, j, k, out):
        if out == GLASS_NAME: return "DEL"
        if kind == "body" and a >= names["cowl"] and j <= 8: return "car_interior"
        if kind == "rear" and j <= 8: return "car_interior"
        return "DEL"
    shell = Cage(spec, filt).to_object("interior_shell")
    subdivide(shell, 1)
    me = shell.data
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    di = [i for i, m in enumerate(me.materials) if m.name == "DEL"]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in di], context="FACES")
    for v in bm.verts: v.co -= v.normal * 0.03
    for f in bm.faces: f.normal_flip(); f.material_index = 0
    bm.to_mesh(me); bm.free()
    me.materials.clear(); me.materials.append(get_mat("car_interior"))
    b = Builder()
    xf = lambda p: to_bl(p, L)
    I = "car_interior"
    cowl = spec["stations"][names["cowl"]]["xs"]
    xr = spec["cabin_end"]
    zf = spec["wheel_z"] + 0.02
    b.quad(*[xf(p) for p in ((cowl - 0.1, -0.86, zf), (cowl - 0.1, 0.86, zf), (xr, 0.86, zf), (xr, -0.86, zf))], I)   # floor
    b.quad(*[xf(p) for p in ((cowl - 0.02, 0.86, zf), (cowl - 0.02, -0.86, zf), (cowl - 0.02, -0.86, 1.0), (cowl - 0.02, 0.86, 1.0))], I)  # firewall
    obox(b, (cowl + 0.19, 0, 0.80), (0.42, 1.66, 0.36), I, xf=xf)                       # dashboard
    obox(b, (cowl + 0.17, 0, 0.965), (0.30, 1.50, 0.05), I, pitch=-0.12, xf=xf)        # dash top roll
    sx = spec["seat_x"]
    for sy in (-0.37, 0.37):
        obox(b, (sx, sy, zf + 0.21), (0.50, 0.50, 0.14), I, pitch=-0.10, xf=xf)
        obox(b, (sx + 0.30, sy, zf + 0.55), (0.13, 0.48, 0.62), I, pitch=0.30, xf=xf)
        obox(b, (sx + 0.42, sy, zf + 0.92), (0.10, 0.27, 0.19), I, pitch=0.18, xf=xf)
    rx = spec["rear_seat_x"]
    obox(b, (rx, 0, zf + 0.22), (0.50, 1.36, 0.14), I, pitch=-0.10, xf=xf)
    obox(b, (rx + 0.30, 0, zf + 0.53), (0.13, 1.36, 0.58), I, pitch=0.36, xf=xf)
    for sy in (-0.42, 0.0, 0.42):
        obox(b, (rx + 0.43, sy, zf + 0.88), (0.09, 0.25, 0.16), I, pitch=0.2, xf=xf)
    if spec.get("parcel_shelf"):
        px0, px1, pz = spec["parcel_shelf"]
        b.quad(*[xf(p) for p in ((px0, -0.7, pz), (px0, 0.7, pz), (px1, 0.7, pz), (px1, -0.7, pz))], I)
    # steering wheel (left-hand drive) and column
    c = Vector((cowl + 0.42, -0.37, 0.985)); tilt = math.radians(24)
    ax = Vector((math.cos(tilt), 0, -math.sin(tilt)))                 # wheel axis points forward-down... towards the dash
    u = Vector((0, 1, 0)); v = ax.cross(u).normalized()
    ring = [c + (u * math.cos(2 * math.pi * s / 14) + v * math.sin(2 * math.pi * s / 14)) * 0.185 for s in range(15)]
    tube(b, [xf(p) for p in ring], 0.017, I, segs=5, caps=False)
    tube(b, [xf(c), xf(c - ax * 0.30)], 0.035, I, segs=6)
    tube(b, [xf(c - u * 0.18), xf(c + u * 0.18)], 0.014, I, segs=4)
    extra = b.to_object("interior_parts", smooth=False)
    return [shell, extra]


def wheel_liners(spec):
    """Dark arch liners, inner wheel-house walls and a flat undertray so nothing is see-through."""
    L, R, zw = spec["L"], spec["arch_r"] + 0.012, spec["wheel_z"]
    b = Builder(); T = "car_trim"
    n = 14
    for ax in (spec["axle_f"], spec["axle_r"]):
        for sgn in (-1, 1):
            y0, y1 = sgn * 0.50, sgn * (spec["W"] / 2 - 0.035)
            ring = []
            for s in range(n + 1):
                t = math.radians(-18 + 216 * s / n)
                ring.append((ax + R * math.cos(t), zw + R * math.sin(t)))
            for (xa, za), (xb, zb) in zip(ring, ring[1:]):
                q = [(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)]
                if sgn < 0: q = q[::-1]                      # faces look at the wheel
                b.quad(*[to_bl(p, L) for p in q], T)
            fan = [to_bl((x, y0, z), L) for x, z in ring]
            idx = [b.vert(p) for p in fan]
            b.face(idx[::-1] if sgn > 0 else idx, T)        # inner wall faces outwards
    zu = spec["under_z"]
    x0, x1, w = 0.22, L - 0.22, spec["W"] / 2 - 0.09
    q = [(x0, -w, zu), (x0, w, zu), (x1, w, zu), (x1, -w, zu)]
    b.quad(*[to_bl(p, L) for p in q], T)
    ob = b.to_object("liners", smooth=False)
    return ob


def mirrors(spec, surf):
    L = spec["L"]
    b = Builder(); xf = lambda p: to_bl(p, L)
    mx, mz = spec["mirror"]
    for sgn in (-1, 1):
        p, n = surf.side(mx - 0.02, mz - 0.035, sgn)
        y0 = p[1]
        yc = y0 + sgn * 0.105
        blob(b, (mx, yc, mz), (0.052, 0.085, 0.056), "car_paint", power=3.0, nu=10, nv=6, xf=xf)
        obox(b, (mx - 0.015, y0 + sgn * 0.01, mz - 0.04), (0.06, 0.09, 0.026), "car_trim", xf=xf)
        gx = mx + 0.054
        q = [(gx, yc - 0.068, mz - 0.038), (gx, yc + 0.068, mz - 0.038), (gx, yc + 0.068, mz + 0.038), (gx, yc - 0.068, mz + 0.038)]
        b.quad(*[xf(p) for p in q], "car_chrome")
    return b.to_object("mirrors")


def door_handles(spec, surf):
    L = spec["L"]
    b = Builder(); xf = lambda p: to_bl(p, L)
    for hx in spec["handles"]:
        for sgn in (-1, 1):
            hz = spec["handle_z"]
            p, n = surf.side(hx, hz, sgn)
            blob(b, (hx, p[1] + sgn * 0.004, hz), (0.085, 0.017, 0.015), "car_paint", power=3.5, nu=8, nv=4, xf=xf)
    return b.to_object("handles")


def roof_rails(spec, surf):
    L = spec["L"]
    b = Builder()
    x0, x1, yr = spec["rails"]
    for sgn in (-1, 1):
        pts = []
        n = 9
        for s in range(n + 1):
            x = x0 + (x1 - x0) * s / n
            y = sgn * yr(x)
            p, _ = surf.top(x, y)
            h = 0.026 if 0 < s < n else -0.004
            pts.append(to_bl((x, y, p[2] + h), L))
        tube(b, pts, 0.012, "car_chrome", segs=6)
    return b.to_object("rails")


def plates(spec, surf, tex_img):
    """Number plates on thin dark plinths, front and rear, with a shared texture."""
    L = spec["L"]
    b = Builder(); xf = lambda p: to_bl(p, L)
    w, h = 0.26, 0.056
    for end, zc in (("front", spec["plate_z"][0]), ("rear", spec["plate_z"][1])):
        cast = surf.front if end == "front" else surf.rear
        sg = -1.0 if end == "front" else 1.0
        xs = [cast(y, zc + dz)[0][0] for y in (0.0, w) for dz in (-h, h)]
        xp = (min(xs) if end == "front" else max(xs)) + sg * 0.012
        q = [(xp, -w, zc - h), (xp, w, zc - h), (xp, w, zc + h), (xp, -w, zc + h)]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if end == "front": q = q[::-1]; uv = [(1, 0), (0, 0), (0, 1), (1, 1)][::-1]
        else: uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        b.quad(*[xf(p) for p in q], "car_plate", uv)
        obox(b, (xp - sg * 0.02, 0, zc), (0.036, 2 * w + 0.03, 2 * h + 0.03), "car_trim", xf=xf)
    ob = b.to_object("plates", smooth=False)
    m = get_mat("car_plate")
    if tex_img is not None and not m.node_tree.nodes.get("PlateTex"):
        t = m.node_tree.nodes.new("ShaderNodeTexImage"); t.name = "PlateTex"; t.image = tex_img
        m.node_tree.links.new(t.outputs["Color"], m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    return ob


def small_details(spec, surf):
    """Wipers parked at the base of the windscreen and a roof antenna fin."""
    L = spec["L"]
    b = Builder(); xf = lambda p: to_bl(p, L)
    wx, wz = spec["wiper"]
    for y0, y1 in ((-0.62, -0.06), (0.02, 0.58)):
        pts = []
        for s in range(5):
            y = y0 + (y1 - y0) * s / 4
            x = wx + 0.035 * (abs(y) / 0.7) ** 2 + 0.03 * s / 4
            p, n = surf.top(x, y)
            pts.append(xf((x, y, p[2] + 0.012)))
        tube(b, pts, 0.008, "car_trim", segs=4)
    fx = spec.get("fin_x")
    if fx:
        za = surf.top(fx - 0.10, 0.0)[0][2]; zb = surf.top(fx + 0.08, 0.0)[0][2]
        zm = za + (zb - za) * 0.75
        i = [b.vert(xf(q)) for q in ((fx - 0.10, -0.022, za - 0.006), (fx + 0.08, -0.03, zb - 0.008), (fx + 0.08, 0.03, zb - 0.008), (fx - 0.10, 0.022, za - 0.006),
                                     (fx + 0.03, 0.0, zm + 0.04), (fx + 0.085, 0.0, zb + 0.036))]
        for f in ((0, 4, 3), (0, 1, 5, 4), (3, 4, 5, 2), (1, 2, 5)):
            b.face([i[k] for k in f], "car_paint")
    return b.to_object("details", smooth=False)
