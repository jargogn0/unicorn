"""City bicycle (diamond frame, 28 inch wheels, mudguards, chain guard, carrier, kickstand).

Built directly in the Blender frame: X lateral (+X = right), +Y forward (glTF -Z), Z up, origin on the ground at
the centre of the footprint. Nodes: bicycle (everything fixed), bike_wheel_f / bike_wheel_r (origins at the hubs).
"""
import math
import bpy
from mathutils import Vector
from .common import Builder, lathe, tube, shade, join
from .car_parts import blob

WHEEL_R, WHEELBASE = 0.35, 1.10
FRAME, METAL, TYRE, SADDLE = "bike_frame", "bike_metal", "bike_tyre", "bike_saddle"


def wheel():
    b = Builder()
    t, rc = 0.019, WHEEL_R - 0.019
    n = 8
    prof = [(-t * math.cos(2 * math.pi * k / n), rc + t * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
    lathe(b, prof, TYRE, 36)
    rim = [(-0.011, 0.296), (-0.012, 0.316), (0.012, 0.316), (0.011, 0.296), (-0.011, 0.296)]
    lathe(b, rim, METAL, 36)
    lathe(b, [(-0.05, 0.0001), (-0.05, 0.011), (-0.032, 0.013), (-0.03, 0.024), (-0.026, 0.024), (-0.024, 0.014), (0.024, 0.014), (0.026, 0.024),
              (0.03, 0.024), (0.032, 0.013), (0.05, 0.011), (0.05, 0.0001)], METAL, 10)
    ns = 20
    for k in range(ns):
        side = -1 if k % 2 else 1
        a_rim = 2 * math.pi * k / ns
        a_hub = a_rim + side * math.radians(38) * (1 if (k // 2) % 2 else -1)
        p0 = (side * 0.028, 0.022 * math.cos(a_hub), 0.022 * math.sin(a_hub))
        p1 = (0.0, 0.298 * math.cos(a_rim), 0.298 * math.sin(a_rim))
        tube(b, [p0, p1], 0.0022, METAL, segs=3, caps=False)
    return b


def _arc_strip(b, c, r, a0, a1, half_w, mat, n=14, lip=0.012):
    """Mudguard: a shallow channel following a circle about c in the YZ plane, with an outside and an inside skin."""
    outer, inner = [], []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        cy, cz = math.cos(a), math.sin(a)
        o, i = [], []
        for x, dr in ((-half_w, -lip), (-half_w * 0.6, -lip * 0.25), (0.0, 0.0), (half_w * 0.6, -lip * 0.25), (half_w, -lip)):
            o.append(b.vert((x, c[1] + (r + dr) * cy, c[2] + (r + dr) * cz)))
            i.append(b.vert((x, c[1] + (r + dr - 0.002) * cy, c[2] + (r + dr - 0.002) * cz)))
        outer.append(o); inner.append(i)
    for k in range(n):
        for j in range(4):
            b.face([outer[k][j], outer[k + 1][j], outer[k + 1][j + 1], outer[k][j + 1]], mat)
            b.face([inner[k][j], inner[k][j + 1], inner[k + 1][j + 1], inner[k + 1][j]], mat)


def build(work=None):
    yr, yf, zr = -WHEELBASE / 2, WHEELBASE / 2, WHEEL_R
    bb = Vector((0, -0.09, 0.285))                       # bottom bracket
    seat = Vector((0, -0.265, 0.80))                     # seat cluster
    ht_top, ht_bot = Vector((0, 0.335, 0.925)), Vector((0, 0.385, 0.77))
    rear, front = Vector((0, yr, zr)), Vector((0, yf, zr))
    b = Builder()
    # main triangle
    tube(b, [bb, seat + (seat - bb).normalized() * 0.02], 0.0165, FRAME, 8)
    tube(b, [seat + Vector((0, 0.012, -0.03)), ht_top + Vector((0, -0.005, -0.035))], 0.0155, FRAME, 8)
    tube(b, [bb, ht_bot + Vector((0, -0.004, 0.02))], 0.019, FRAME, 8)
    tube(b, [ht_bot - (ht_top - ht_bot).normalized() * 0.015, ht_top + (ht_top - ht_bot).normalized() * 0.02], 0.021, FRAME, 8)
    lathe(b, [(-0.04, 0.0001), (-0.04, 0.024), (0.04, 0.024), (0.04, 0.0001)], FRAME, 10, centre=tuple(bb))
    for sx in (-1, 1):
        tube(b, [bb + Vector((sx * 0.028, -0.01, 0)), Vector((sx * 0.058, yr + 0.02, zr)), Vector((sx * 0.062, yr - 0.012, zr))], 0.0095, FRAME, 6)   # chain stays
        tube(b, [seat + Vector((sx * 0.014, -0.004, -0.015)), Vector((sx * 0.058, yr + 0.004, zr + 0.012))], 0.0085, FRAME, 6)                        # seat stays
        # fork blades with a little rake
        crown = ht_bot + Vector((sx * 0.05, 0.002, -0.03))
        tube(b, [crown, crown + (Vector((sx * 0.052, yf - 0.045, zr + 0.12)) - crown) * 1.0, Vector((sx * 0.052, yf, zr))], [0.0125, 0.010, 0.008], FRAME, 6)
        tube(b, [Vector((sx * 0.052, yr, zr)), Vector((sx * 0.062, yr, zr))], 0.006, METAL, 5)            # axle nuts
        tube(b, [Vector((sx * 0.052, yf, zr)), Vector((sx * 0.062, yf, zr))], 0.006, METAL, 5)
    tube(b, [ht_bot + Vector((-0.055, 0.002, -0.03)), ht_bot + Vector((0.055, 0.002, -0.03))], 0.014, FRAME, 6)    # fork crown
    # seat post and saddle
    up = (seat - bb).normalized()
    post_top = seat + up * 0.16
    tube(b, [seat, post_top], 0.0125, METAL, 6)
    sc = post_top + Vector((0, -0.02, 0.035))
    def sxf(p):   # saddle: narrow nose forwards, wide at the back
        y = p[1] - sc.y
        w = 0.45 + 0.55 * max(0.0, min(1.0, (0.12 - y) / 0.22))
        return ((p[0]) * w, p[1], p[2] + 0.012 * (y / 0.13) ** 2)
    blob(b, tuple(sc), (0.085, 0.135, 0.028), SADDLE, power=2.6, nu=12, nv=6, xf=sxf)
    # stem and swept-back handlebar with grips
    axis = (ht_top - ht_bot).normalized()
    stem_top = ht_top + axis * 0.13
    tube(b, [ht_top, stem_top], 0.012, METAL, 6)
    bar_c = stem_top + Vector((0, 0.07, 0.01))
    tube(b, [stem_top + Vector((0, -0.005, -0.008)), bar_c], 0.013, METAL, 6)
    for sx in (-1, 1):
        pts = [bar_c, bar_c + Vector((sx * 0.10, 0.012, 0.0)), bar_c + Vector((sx * 0.20, -0.02, 0.022)), bar_c + Vector((sx * 0.262, -0.09, 0.04)), bar_c + Vector((sx * 0.285, -0.17, 0.042))]
        tube(b, pts, 0.011, METAL, 6)
        tube(b, [pts[-1], pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.115], 0.016, SADDLE, 7)
        tube(b, [pts[2] + Vector((0, 0.01, -0.012)), pts[2] + Vector((sx * 0.045, 0.085, -0.03))], 0.0045, METAL, 4)     # brake lever
    # head lamp on the fork crown
    lathe(b, [(0.0, 0.0001), (0.0, 0.02), (0.04, 0.027), (0.046, 0.0001)], METAL, 10, axis="y", centre=(0, ht_bot.y + 0.028, ht_bot.z - 0.002))
    # mudguards and stays
    _arc_strip(b, rear, WHEEL_R + 0.022, -12, 128, 0.027, FRAME)
    _arc_strip(b, front, WHEEL_R + 0.022, 28, 150, 0.027, FRAME)
    for c, ang in ((rear, 8), (front, 140)):
        a = math.radians(ang)
        tip = c + Vector((0, math.cos(a), math.sin(a))) * (WHEEL_R + 0.012)
        for sx in (-1, 1):
            tube(b, [c + Vector((sx * 0.06, 0, 0)), tip + Vector((sx * 0.027, 0, 0))], 0.003, METAL, 3, caps=False)
    # rear carrier
    cz = 2 * WHEEL_R + 0.045
    y0, y1 = yr + 0.20, yr - 0.20
    for sx in (-1, 1):
        tube(b, [Vector((sx * 0.065, y0 + 0.03, cz)), Vector((sx * 0.065, y1, cz))], 0.0055, METAL, 5)
        tube(b, [Vector((sx * 0.062, yr, zr + 0.01)), Vector((sx * 0.065, yr - 0.05, cz))], 0.005, METAL, 4)
        tube(b, [Vector((sx * 0.062, yr, zr + 0.01)), Vector((sx * 0.065, yr - 0.17, cz))], 0.005, METAL, 4)
        tube(b, [Vector((sx * 0.065, y0 + 0.03, cz)), seat + Vector((sx * 0.014, -0.02, -0.07))], 0.005, METAL, 4)
    for y in (y0 + 0.03, (y0 + y1) / 2, y1):
        tube(b, [Vector((-0.065, y, cz)), Vector((0.065, y, cz))], 0.0055, METAL, 5)
    tube(b, [Vector((0, y0 + 0.03, cz)), Vector((0, y1, cz))], 0.0045, METAL, 4)
    # chain guard on the right: a closed plate around chainring and chain
    gx = 0.052
    ca, cb, ra, rb = Vector((0, bb.y, bb.z)), Vector((0, yr + 0.03, zr - 0.005)), 0.118, 0.052
    cloud = [(c.y + r * math.cos(2 * math.pi * k / 20), c.z + r * math.sin(2 * math.pi * k / 20)) for c, r in ((ca, ra), (cb, rb)) for k in range(20)]
    cloud.sort()
    def half(points):                                      # monotone-chain convex hull
        h = []
        for p in points:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0: h.pop()
            h.append(p)
        return h
    lower, upper = half(cloud), half(cloud[::-1])
    out = [Vector((0, y, z)) for y, z in lower[:-1] + upper[:-1]]
    fo = [b.vert((gx + 0.012, p.y, p.z)) for p in out]; fi = [b.vert((gx - 0.006, p.y, p.z)) for p in out]
    area = sum(out[k].y * out[(k + 1) % len(out)].z - out[(k + 1) % len(out)].y * out[k].z for k in range(len(out)))
    ccw = area > 0                                         # counter-clockwise seen from +X
    b.face(fo if ccw else fo[::-1], FRAME); b.face(fi[::-1] if ccw else fi, FRAME)
    for k in range(len(out)):
        k2 = (k + 1) % len(out)
        q = [fo[k], fi[k], fi[k2], fo[k2]]
        b.face(q if ccw else q[::-1], FRAME)
    # cranks and pedals
    for sx, ang in ((1, math.radians(-25)), (-1, math.radians(155))):
        x0 = sx * 0.075
        end = Vector((x0, bb.y + 0.17 * math.cos(ang), bb.z + 0.17 * math.sin(ang)))
        tube(b, [Vector((sx * 0.04, bb.y, bb.z)), Vector((x0, bb.y, bb.z)), end], 0.008, METAL, 5)
        b.box((x0 + sx * 0.055, end.y, end.z), (0.09, 0.065, 0.02), TYRE)
    # kickstand (down, on the left)
    tube(b, [Vector((-0.03, bb.y - 0.06, bb.z - 0.02)), Vector((-0.17, bb.y - 0.16, 0.004))], 0.007, METAL, 5)
    frame = b.to_object("bicycle")
    shade(frame, 45)
    objs = [frame]
    wb = wheel().to_object("bike_wheel_mesh")
    shade(wb, 45)
    for name, y in (("bike_wheel_f", yf), ("bike_wheel_r", yr)):
        if name == "bike_wheel_f":
            ob = wb
        else:
            ob = bpy.data.objects.new(name, wb.data); bpy.context.scene.collection.objects.link(ob)
        ob.name = name; ob.location = (0, y, zr)
        objs.append(ob)
    return objs
