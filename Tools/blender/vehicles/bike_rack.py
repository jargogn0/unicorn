"""Bicycle rack: a row of galvanised steel hoops on two ground rails. Bikes park along Y (glTF Z), hoops repeat along X."""
import math
from mathutils import Vector
from .common import Builder, tube, shade

HOOPS, PITCH, HEIGHT, LENGTH, RADIUS = 5, 0.62, 0.80, 0.78, 0.024


def build(work=None):
    b = Builder()
    x0 = -PITCH * (HOOPS - 1) / 2
    cr = 0.14                                               # corner radius of the hoop
    for k in range(HOOPS):
        x = x0 + k * PITCH
        pts = [Vector((x, -LENGTH / 2, 0.0)), Vector((x, -LENGTH / 2, HEIGHT - cr))]
        for s in range(1, 6):
            a = math.pi / 2 * s / 5
            pts.append(Vector((x, -LENGTH / 2 + cr - cr * math.cos(a), HEIGHT - cr + cr * math.sin(a))))
        for s in range(0, 6):
            a = math.pi / 2 * s / 5
            pts.append(Vector((x, LENGTH / 2 - cr + cr * math.sin(a), HEIGHT - cr + cr * math.cos(a))))
        pts.append(Vector((x, LENGTH / 2, 0.0)))
        tube(b, pts, RADIUS, "rack_steel", segs=8)
        tube(b, [Vector((x, -LENGTH / 2 + 0.02, 0.42)), Vector((x, LENGTH / 2 - 0.02, 0.42))], 0.014, "rack_steel", segs=6, caps=False)   # mid rail
    for y in (-LENGTH / 2, LENGTH / 2):                     # flat ground rails
        b.box((0, y, 0.006), (PITCH * (HOOPS - 1) + 0.24, 0.08, 0.012), "rack_steel")
    ob = b.to_object("bike_rack")
    shade(ob, 45)
    return [ob]
