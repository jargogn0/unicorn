"""Headless Blender: build the STOCKHOLM modular facade kit.

Grid from the owner's building spec: 4.0 m wide panels, 3.5 m floor-to-floor, 4.5 m ground floor.
Module space: X along the facade (0..W), Z up, Y depth (0 = facade plane, +Y into the building,
-Y projecting towards the street). UVs are world-scale (metres / 2) so PBR materials tile consistently.

Each module is exported as one object per material, named `<module>__<material>`; the game and the
Unreal PCG graph instance modules per bay and tint the `wall` part per building.

Usage: python3 Tools/blender/build_facade_kit.py --out WebPreview/assets/kit [--fbx Stockholm/Content/Import/FacadeKit]
"""
import argparse, json, math, pathlib, sys
import bpy

W, H, HG = 4.0, 3.5, 4.5
UVS = 0.5  # uv per metre


class Module:
    def __init__(self, name, width=W, height=H):
        self.name, self.width, self.height = name, width, height
        self.parts = {}  # material -> (verts, faces, uvs)

    def _part(self, mat):
        return self.parts.setdefault(mat, ([], [], []))

    def quad(self, mat, p0, p1, p2, p3, uv=None):
        """Quad with vertices in CCW order seen from the visible side."""
        v, f, u = self._part(mat)
        base = len(v)
        v.extend([p0, p1, p2, p3])
        f.append((base, base + 1, base + 2, base + 3))
        if uv is None:
            # world-scale planar projection chosen from the dominant normal axis
            ax = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]); bx = (p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2])
            n = (ax[1] * bx[2] - ax[2] * bx[1], ax[2] * bx[0] - ax[0] * bx[2], ax[0] * bx[1] - ax[1] * bx[0])
            k = max(range(3), key=lambda i: abs(n[i]))
            proj = {0: lambda p: (p[1], p[2]), 1: lambda p: (p[0], p[2]), 2: lambda p: (p[0], p[1])}[k]
            uv = [tuple(c * UVS for c in proj(p)) for p in (p0, p1, p2, p3)]
        u.append(uv)

    def box(self, mat, x0, x1, y0, y1, z0, z1, faces="fblrtk"):
        """Axis-aligned box. faces: f=front(-Y) b=back(+Y) l=left r=right t=top k=bottom."""
        if "f" in faces: self.quad(mat, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
        if "b" in faces: self.quad(mat, (x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1))
        if "l" in faces: self.quad(mat, (x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1))
        if "r" in faces: self.quad(mat, (x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))
        if "t" in faces: self.quad(mat, (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
        if "k" in faces: self.quad(mat, (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0))

    def wall_with_opening(self, mat, x0, x1, z0, z1, ox0, ox1, oz0, oz1, depth=0.22, reveal_mat=None):
        """Wall panel in the facade plane with a rectangular opening and reveals of the given depth."""
        self.box(mat, x0, ox0, 0, 0, z0, z1, "f"); self.box(mat, ox1, x1, 0, 0, z0, z1, "f")
        self.box(mat, ox0, ox1, 0, 0, z0, oz0, "f"); self.box(mat, ox0, ox1, 0, 0, oz1, z1, "f")
        rm = reveal_mat or mat
        self.quad(rm, (ox0, 0, oz0), (ox0, depth, oz0), (ox0, depth, oz1), (ox0, 0, oz1))        # left reveal
        self.quad(rm, (ox1, depth, oz0), (ox1, 0, oz0), (ox1, 0, oz1), (ox1, depth, oz1))        # right reveal
        self.quad(rm, (ox0, 0, oz1), (ox0, depth, oz1), (ox1, depth, oz1), (ox1, 0, oz1))        # head
        self.quad(rm, (ox0, depth, oz0), (ox0, 0, oz0), (ox1, 0, oz0), (ox1, depth, oz0))        # sill bed

    def profile(self, mat, x0, x1, pts, caps=True):
        """Extrude a (y, z) polyline profile along X. pts go from bottom to top on the visible side."""
        for (ya, za), (yb, zb) in zip(pts, pts[1:]):
            self.quad(mat, (x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb))
        if caps and len(pts) >= 3:
            v, f, u = self._part(mat)
            for x, rev in ((x0, False), (x1, True)):
                ring = [(x, y, z) for y, z in pts] + [(x, 0.0, pts[-1][1]), (x, 0.0, pts[0][1])]
                if rev: ring.reverse()
                base = len(v); v.extend(ring); f.append(tuple(range(base, base + len(ring))))
                u.append([(p[1] * UVS, p[2] * UVS) for p in ring])

    def window(self, ox0, ox1, oz0, oz1, depth=0.22, frame="frame", style="cross", glass="glass", t=0.07):
        """Timber window set into an opening: outer frame, mullion/transom, glass pane."""
        y = depth - 0.07
        self.box(frame, ox0, ox0 + t, y, depth, oz0, oz1, "fr"); self.box(frame, ox1 - t, ox1, y, depth, oz0, oz1, "fl")
        self.box(frame, ox0 + t, ox1 - t, y, depth, oz0, oz0 + t, "ft"); self.box(frame, ox0 + t, ox1 - t, y, depth, oz1 - t, oz1, "fk")
        xm = (ox0 + ox1) / 2
        if style in ("cross", "mullion", "door"):
            self.box(frame, xm - t / 2, xm + t / 2, y, depth, oz0 + t, oz1 - t, "flr")
        if style == "cross":
            zt = oz0 + (oz1 - oz0) * 0.68
            self.box(frame, ox0 + t, ox1 - t, y - 0.01, depth, zt - t / 2, zt + t / 2, "ftk")
        if style == "door":
            zt = oz0 + (oz1 - oz0) * 0.8
            self.box(frame, ox0 + t, ox1 - t, y - 0.01, depth, zt - t / 2, zt + t / 2, "ftk")
            self.box(frame, ox0 + t, ox1 - t, y, depth, oz0 + t, oz0 + 0.35, "ft")
        if style == "grid":
            for i in range(1, 3):
                x = ox0 + (ox1 - ox0) * i / 3
                self.box(frame, x - t / 3, x + t / 3, y, depth, oz0 + t, oz1 - t, "flr")
            zt = (oz0 + oz1) / 2
            self.box(frame, ox0 + t, ox1 - t, y, depth, zt - t / 3, zt + t / 3, "ftk")
        self.quad(glass, (ox0 + t, depth - 0.02, oz0 + t), (ox1 - t, depth - 0.02, oz0 + t), (ox1 - t, depth - 0.02, oz1 - t), (ox0 + t, depth - 0.02, oz1 - t),
                  uv=[(0, 0), (1, 0), (1, 1), (0, 1)])

    def sill(self, ox0, ox1, oz0, mat="trim", snow=True):
        self.profile(mat, ox0 - 0.08, ox1 + 0.08, [(0.0, oz0 - 0.09), (-0.1, oz0 - 0.07), (-0.1, oz0 - 0.02), (0.0, oz0 + 0.01)])
        if snow:
            self.profile("snow", ox0 - 0.06, ox1 + 0.06, [(-0.1, oz0 - 0.02), (-0.09, oz0 + 0.05), (0.02, oz0 + 0.07), (0.1, oz0 + 0.02)], caps=False)

    def snow_ledge(self, x0, x1, y_front, z, depth=0.3, h=0.09):
        self.profile("snow", x0, x1, [(y_front, z), (y_front + 0.02, z + h * 0.8), (y_front + depth * 0.6, z + h), (y_front + depth, z + h * 0.3)], caps=False)


# ---------------------------------------------------------------------------------- upper floors

def win_plain(name="win_plain", wall="wall"):
    m = Module(name); ox0, ox1, oz0, oz1 = 1.375, 2.625, 0.95, 2.85
    m.wall_with_opening(wall, 0, W, 0, H, ox0, ox1, oz0, oz1)
    m.window(ox0, ox1, oz0, oz1); m.sill(ox0, ox1, oz0)
    return m

def win_surround():
    m = Module("win_surround"); ox0, ox1, oz0, oz1 = 1.375, 2.625, 0.95, 2.95
    m.wall_with_opening("wall", 0, W, 0, H, ox0, ox1, oz0, oz1)
    m.window(ox0, ox1, oz0, oz1); m.sill(ox0, ox1, oz0)
    a = 0.16  # architrave
    m.box("trim", ox0 - a, ox0, -0.05, 0, oz0, oz1 + a, "flrt"); m.box("trim", ox1, ox1 + a, -0.05, 0, oz0, oz1 + a, "flrt")
    m.box("trim", ox0, ox1, -0.05, 0, oz1, oz1 + a, "fk")
    m.profile("trim", ox0 - a - 0.1, ox1 + a + 0.1, [(-0.05, oz1 + a), (-0.09, oz1 + a + 0.03), (-0.2, oz1 + a + 0.1), (-0.2, oz1 + a + 0.16), (0, oz1 + a + 0.2)])
    m.snow_ledge(ox0 - a - 0.08, ox1 + a + 0.08, -0.2, oz1 + a + 0.16, 0.2, 0.06)
    for x in (ox0 - a + 0.02, ox1 + 0.02):  # corbels under the sill
        m.box("trim", x, x + 0.12, -0.08, 0, oz0 - 0.3, oz0 - 0.09, "flrk")
    return m

def win_pair(name="win_pair", wall="wall"):
    m = Module(name); z0, z1 = 0.95, 2.85
    xa = (0.75, 1.7, 2.3, 3.25)
    m.box(wall, 0, xa[0], 0, 0, 0, H, "f"); m.box(wall, xa[1], xa[2], 0, 0, 0, H, "f"); m.box(wall, xa[3], W, 0, 0, 0, H, "f")
    for a, b in ((xa[0], xa[1]), (xa[2], xa[3])):
        m.box(wall, a, b, 0, 0, 0, z0, "f"); m.box(wall, a, b, 0, 0, z1, H, "f")
        d = 0.22
        m.quad(wall, (a, 0, z0), (a, d, z0), (a, d, z1), (a, 0, z1)); m.quad(wall, (b, d, z0), (b, 0, z0), (b, 0, z1), (b, d, z1))
        m.quad(wall, (a, 0, z1), (a, d, z1), (b, d, z1), (b, 0, z1)); m.quad(wall, (a, d, z0), (a, 0, z0), (b, 0, z0), (b, d, z0))
        m.window(a, b, z0, z1, style="cross"); m.sill(a, b, z0)
    return m

def win_balcony():
    m = Module("win_balcony"); ox0, ox1, oz0, oz1 = 1.35, 2.65, 0.12, 2.75
    m.wall_with_opening("wall", 0, W, 0, H, ox0, ox1, oz0, oz1)
    m.window(ox0, ox1, oz0, oz1, style="door")
    m.box("trim", ox0 - 0.14, ox0, -0.04, 0, oz0, oz1 + 0.14, "flrt"); m.box("trim", ox1, ox1 + 0.14, -0.04, 0, oz0, oz1 + 0.14, "flrt")
    m.box("trim", ox0, ox1, -0.04, 0, oz1, oz1 + 0.14, "fk")
    bx0, bx1, by = 0.75, 3.25, -0.85
    m.box("trim", bx0, bx1, by, 0, -0.05, 0.12, "flrtk")                      # slab
    for x in (bx0 + 0.2, bx1 - 0.45):                                           # consoles
        m.profile("trim", x, x + 0.25, [(0.0, -0.55), (-0.25, -0.3), (-0.7, -0.08), (-0.7, -0.05)])
    rail = "metal"; top = 1.12
    m.box(rail, bx0 + 0.03, bx1 - 0.03, by + 0.02, by + 0.07, top - 0.05, top, "fbtk")
    m.box(rail, bx0 + 0.03, bx0 + 0.08, by + 0.02, 0, top - 0.05, top, "lrtk"); m.box(rail, bx1 - 0.08, bx1 - 0.03, by + 0.02, 0, top - 0.05, top, "lrtk")
    m.box(rail, bx0 + 0.03, bx1 - 0.03, by + 0.03, by + 0.06, 0.2, 0.24, "fbtk")
    n = 17
    for i in range(n + 1):
        x = bx0 + 0.04 + (bx1 - bx0 - 0.1) * i / n
        m.box(rail, x, x + 0.022, by + 0.035, by + 0.057, 0.12, top - 0.05, "fblr")
    for side_x in (bx0 + 0.04, bx1 - 0.06):
        for j in range(1, 5):
            y = by + 0.05 + (0 - by - 0.05) * j / 5
            m.box(rail, side_x, side_x + 0.022, y, y + 0.022, 0.12, top - 0.05, "fblr")
    m.snow_ledge(bx0 + 0.02, bx1 - 0.02, by, 0.12, 0.6, 0.07)
    return m

def win_brick(name="win_brick"):
    m = Module(name); ox0, ox1, oz0, oz1 = 1.4, 2.6, 0.95, 2.8
    m.wall_with_opening("brick", 0, W, 0, H, ox0, ox1, oz0, oz1, depth=0.26)
    m.window(ox0, ox1, oz0, oz1, depth=0.26, frame="frame_dark", style="grid")
    m.box("stone", ox0 - 0.12, ox1 + 0.12, -0.03, 0, oz1, oz1 + 0.22, "flrtk")       # stone lintel
    m.box("stone", ox0 + 0.4, ox1 - 0.4, -0.05, 0, oz1 + 0.02, oz1 + 0.3, "flrt")     # keystone
    m.sill(ox0, ox1, oz0, mat="stone")
    return m

def win_modern():
    m = Module("win_modern"); ox0, ox1, oz0, oz1 = 0.6, 3.4, 1.0, 2.6
    m.wall_with_opening("wall", 0, W, 0, H, ox0, ox1, oz0, oz1, depth=0.14)
    y, t = 0.08, 0.05
    m.box("frame_dark", ox0, ox1, y, 0.14, oz0, oz0 + t, "ft"); m.box("frame_dark", ox0, ox1, y, 0.14, oz1 - t, oz1, "fk")
    for i in range(4):
        x = ox0 + (ox1 - ox0 - t) * i / 3
        m.box("frame_dark", x, x + t, y, 0.14, oz0, oz1, "flr")
    m.quad("glass", (ox0, 0.12, oz0), (ox1, 0.12, oz0), (ox1, 0.12, oz1), (ox0, 0.12, oz1), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.profile("metal", ox0 - 0.03, ox1 + 0.03, [(0.0, oz0 - 0.04), (-0.07, oz0 - 0.03), (-0.07, oz0), (0.0, oz0 + 0.01)])
    m.snow_ledge(ox0, ox1, -0.07, oz0, 0.1, 0.05)
    return m

def win_tower():
    """Vertical-emphasis bay for the 1920s towers: stone pilasters, slim paired windows, spandrel."""
    m = Module("win_tower")
    p = 0.55
    m.box("stone", 0, p, -0.18, 0, 0, H, "flr"); m.box("stone", W - p, W, -0.18, 0, 0, H, "flr")
    z0, z1 = 0.9, 3.0
    xa = (p + 0.25, 1.85, 2.15, W - p - 0.25)
    m.box("wall", p, xa[0], 0, 0, 0, H, "f"); m.box("wall", xa[1], xa[2], 0, 0, 0, H, "f"); m.box("wall", xa[3], W - p, 0, 0, 0, H, "f")
    for a, b in ((xa[0], xa[1]), (xa[2], xa[3])):
        m.box("wall", a, b, 0, 0, 0, z0, "f"); m.box("wall", a, b, 0, 0, z1, H, "f")
        d = 0.2
        m.quad("wall", (a, 0, z0), (a, d, z0), (a, d, z1), (a, 0, z1)); m.quad("wall", (b, d, z0), (b, 0, z0), (b, 0, z1), (b, d, z1))
        m.quad("wall", (a, 0, z1), (a, d, z1), (b, d, z1), (b, 0, z1)); m.quad("wall", (a, d, z0), (a, 0, z0), (b, 0, z0), (b, d, z0))
        m.window(a, b, z0, z1, depth=d, frame="frame_dark", style="cross")
    m.box("stone", p, W - p, -0.04, 0, 0.3, 0.75, "ftk")  # spandrel panel
    return m

def blank(name="blank", wall="wall"):
    m = Module(name); m.box(wall, 0, W, 0, 0, 0, H, "f"); return m

# ---------------------------------------------------------------------------------- ground floor

def _plinth(m, x0, x1, h=0.55):
    m.box("stone", x0, x1, -0.06, 0, 0, h, "ft")

def shop_glass(name="shop_glass", pier="stone"):
    m = Module(name, height=HG)
    pw = 0.38
    m.box(pier, 0, pw, -0.08, 0.3, 0, 3.55, "frl"); m.box(pier, W - pw, W, -0.08, 0.3, 0, 3.55, "frl")   # piers
    _plinth(m, pw, W - pw, 0.45)
    ox0, ox1, oz0, oz1 = pw, W - pw, 0.45, 3.05
    d = 0.3
    m.quad("frame_dark", (ox0, 0, oz0), (ox1, 0, oz0), (ox1, d, oz0), (ox0, d, oz0))  # stall riser top
    t = 0.06
    m.box("frame_dark", ox0, ox0 + t, d - 0.06, d, oz0, oz1, "fr"); m.box("frame_dark", ox1 - t, ox1, d - 0.06, d, oz0, oz1, "fl")
    m.box("frame_dark", ox0, ox1, d - 0.06, d, oz1 - t, oz1, "fk"); m.box("frame_dark", ox0, ox1, d - 0.06, d, oz0, oz0 + t, "ft")
    m.box("frame_dark", ox0, ox1, d - 0.06, d, 2.45, 2.45 + t, "ftk")
    xm = (ox0 + ox1) / 2
    m.box("frame_dark", xm - t / 2, xm + t / 2, d - 0.06, d, 2.45, oz1, "flr")
    m.quad("shop_glass", (ox0, d - 0.03, oz0), (ox1, d - 0.03, oz0), (ox1, d - 0.03, oz1), (ox0, d - 0.03, oz1), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.quad("shop_interior", (ox0, 1.6, oz0), (ox1, 1.6, oz0), (ox1, 1.6, oz1), (ox0, 1.6, oz1), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.quad("shop_floor", (ox0, d, oz0), (ox1, d, oz0), (ox1, 1.6, oz0), (ox0, 1.6, oz0))
    m.quad("shop_side", (ox0, d, oz0), (ox0, 1.6, oz0), (ox0, 1.6, oz1), (ox0, d, oz1)); m.quad("shop_side", (ox1, 1.6, oz0), (ox1, d, oz0), (ox1, d, oz1), (ox1, 1.6, oz1))
    m.quad("shop_side", (ox0, d, oz1), (ox0, 1.6, oz1), (ox1, 1.6, oz1), (ox1, d, oz1))
    # fascia with sign zone and cornice
    m.box("sign", pw, W - pw, -0.05, 0, 3.12, 3.62, "f"); m.box("frame_dark", pw, W - pw, -0.03, 0, 3.05, 3.12, "fk")
    m.profile("trim", 0, W, [(-0.08, 3.62), (-0.12, 3.66), (-0.3, 3.78), (-0.3, 3.86), (0, 3.92)])
    m.snow_ledge(0, W, -0.3, 3.86, 0.28, 0.08)
    m.box("wall", 0, W, 0, 0, 3.92, HG, "f")
    return m

def shop_door():
    m = Module("shop_door", height=HG)
    pw = 0.38
    m.box("stone", 0, pw, -0.08, 0.3, 0, 3.55, "frl"); m.box("stone", W - pw, W, -0.08, 0.3, 0, 3.55, "frl")
    d0, d1 = 1.3, 2.7  # door recess
    for a, b in ((pw, d0), (d1, W - pw)):
        _plinth(m, a, b, 0.45)
        m.box("frame_dark", a, b, 0.24, 0.3, 0.45, 3.05, "f")
        m.quad("shop_glass", (a + 0.05, 0.27, 0.5), (b - 0.05, 0.27, 0.5), (b - 0.05, 0.27, 3.0), (a + 0.05, 0.27, 3.0), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.quad("stone", (d0, 0, 0), (d1, 0, 0), (d1, 0.9, 0), (d0, 0.9, 0))                      # threshold
    m.quad("frame_dark", (d0, 0.3, 0), (d0, 0.9, 0), (d0, 0.9, 3.05), (d0, 0.3, 3.05)); m.quad("frame_dark", (d1, 0.9, 0), (d1, 0.3, 0), (d1, 0.3, 3.05), (d1, 0.9, 3.05))
    m.quad("frame_dark", (d0, 0.3, 3.05), (d0, 0.9, 3.05), (d1, 0.9, 3.05), (d1, 0.3, 3.05))
    m.window(d0, d1, 0.02, 3.05, depth=0.9, frame="frame_dark", style="door", glass="shop_glass")
    m.box("metal", d0 + 0.55, d0 + 0.59, 0.78, 0.82, 0.95, 1.35, "fblr")                       # door pull
    m.quad("shop_interior", (pw, 1.6, 0.45), (W - pw, 1.6, 0.45), (W - pw, 1.6, 3.05), (pw, 1.6, 3.05), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.box("sign", pw, W - pw, -0.05, 0, 3.12, 3.62, "f"); m.box("frame_dark", pw, W - pw, -0.03, 0, 3.05, 3.12, "fk")
    m.profile("trim", 0, W, [(-0.08, 3.62), (-0.12, 3.66), (-0.3, 3.78), (-0.3, 3.86), (0, 3.92)])
    m.snow_ledge(0, W, -0.3, 3.86, 0.28, 0.08)
    m.box("wall", 0, W, 0, 0, 3.92, HG, "f")
    return m

def portal():
    """Residential entrance (port): stone surround, panelled timber double door, glazed transom."""
    m = Module("portal", height=HG)
    ox0, ox1, oz1 = 1.1, 2.9, 3.35
    m.wall_with_opening("stone", 0, W, 0, 3.92, ox0, ox1, 0.0, oz1, depth=0.45)
    m.box("trim", ox0 - 0.22, ox0, -0.1, 0, 0, oz1 + 0.22, "flrt"); m.box("trim", ox1, ox1 + 0.22, -0.1, 0, 0, oz1 + 0.22, "flrt")
    m.box("trim", ox0, ox1, -0.1, 0, oz1, oz1 + 0.22, "fk")
    m.profile("trim", ox0 - 0.35, ox1 + 0.35, [(-0.1, oz1 + 0.22), (-0.16, oz1 + 0.26), (-0.32, oz1 + 0.36), (-0.32, oz1 + 0.44), (0, oz1 + 0.5)])
    m.snow_ledge(ox0 - 0.33, ox1 + 0.33, -0.32, oz1 + 0.44, 0.3, 0.07)
    d = 0.45
    xm = (ox0 + ox1) / 2
    for a, b in ((ox0, xm - 0.01), (xm + 0.01, ox1)):
        m.box("door_wood", a, b, d - 0.07, d, 0.0, 2.5, "f")
        for z0, z1 in ((0.2, 1.1), (1.25, 2.3)):  # raised panels
            m.box("door_wood", a + 0.14, b - 0.14, d - 0.1, d - 0.07, z0, z1, "flrtk")
    m.box("door_wood", ox0, ox1, d - 0.08, d, 2.5, 2.6, "ftk")
    m.window(ox0, ox1, 2.6, oz1, depth=d, frame="door_wood", style="mullion")
    m.box("metal", xm - 0.12, xm - 0.08, d - 0.14, d - 0.1, 1.0, 1.3, "fblr"); m.box("metal", xm + 0.08, xm + 0.12, d - 0.14, d - 0.1, 1.0, 1.3, "fblr")
    m.quad("stone", (ox0, 0, 0), (ox1, 0, 0), (ox1, d, 0.0), (ox0, d, 0.0))
    # wall lantern
    m.box("metal", ox1 + 0.5, ox1 + 0.56, -0.25, 0, 2.6, 2.66, "flrtk"); m.box("lamp_glow", ox1 + 0.44, ox1 + 0.62, -0.36, -0.18, 2.3, 2.6, "fblrtk")
    m.box("wall", 0, W, 0, 0, 3.92, HG, "f")
    m.profile("trim", 0, W, [(0, 3.78), (-0.1, 3.8), (-0.1, 3.9), (0, 3.92)])
    return m

def ground_brick():
    """Brick ground floor with a large stone-framed shop opening (national-romantic blocks)."""
    m = Module("ground_brick", height=HG)
    ox0, ox1, oz0, oz1 = 0.5, 3.5, 0.5, 3.3
    m.wall_with_opening("brick", 0, W, 0, HG, ox0, ox1, oz0, oz1, depth=0.34, reveal_mat="stone")
    _plinth(m, 0, W, 0.5)
    m.box("stone", ox0 - 0.14, ox0, -0.04, 0, 0.5, oz1 + 0.2, "flrt"); m.box("stone", ox1, ox1 + 0.14, -0.04, 0, 0.5, oz1 + 0.2, "flrt")
    m.box("stone", ox0, ox1, -0.04, 0, oz1, oz1 + 0.2, "fk")
    d, t = 0.34, 0.06
    m.box("frame_dark", ox0, ox1, d - 0.06, d, 2.6, 2.6 + t, "ftk")
    for i in range(1, 3):
        x = ox0 + (ox1 - ox0) * i / 3
        m.box("frame_dark", x - t / 2, x + t / 2, d - 0.06, d, oz0, oz1, "flr")
    m.quad("shop_glass", (ox0, d - 0.03, oz0), (ox1, d - 0.03, oz0), (ox1, d - 0.03, oz1), (ox0, d - 0.03, oz1), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.quad("shop_interior", (ox0, 1.6, oz0), (ox1, 1.6, oz0), (ox1, 1.6, oz1), (ox0, 1.6, oz1), uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.quad("shop_floor", (ox0, d, oz0), (ox1, d, oz0), (ox1, 1.6, oz0), (ox0, 1.6, oz0))
    m.box("sign", ox0 + 0.2, ox1 - 0.2, -0.06, -0.02, 3.6, 4.05, "flrtk")
    return m

# ---------------------------------------------------------------------------------- tops and bands

def cornice():
    m = Module("cornice", height=0.9)
    m.profile("trim", 0, W, [(0, 0), (-0.06, 0.02), (-0.06, 0.22), (-0.14, 0.3), (-0.14, 0.4), (-0.42, 0.62), (-0.55, 0.66), (-0.55, 0.8), (-0.5, 0.86), (0, 0.9)], caps=False)
    for i in range(10):  # dentils
        x = 0.1 + i * 0.4
        m.box("trim", x, x + 0.2, -0.26, -0.14, 0.3, 0.44, "flrk")
    m.snow_ledge(0, W, -0.55, 0.8, 0.5, 0.1)
    return m

def band():
    m = Module("band", height=0.3)
    m.profile("trim", 0, W, [(0, 0), (-0.05, 0.03), (-0.12, 0.1), (-0.12, 0.22), (0, 0.3)], caps=False)
    m.snow_ledge(0, W, -0.12, 0.22, 0.12, 0.05)
    return m

def parapet():
    m = Module("parapet", height=1.0)
    m.box("wall", 0, W, 0, 0.3, 0, 0.9, "fb")
    m.box("metal", 0, W, -0.04, 0.34, 0.9, 0.96, "fbtk")
    m.snow_ledge(0, W, -0.04, 0.96, 0.36, 0.08)
    return m

def mansard(dormer=False):
    m = Module("mansard_dormer" if dormer else "mansard", height=3.2)
    run, rise = 1.25, 2.9
    m.quad("roof", (0, 0, 0), (W, 0, 0), (W, run, rise), (0, run, rise), uv=[(0, 0), (W * UVS, 0), (W * UVS, 3.2 * UVS), (0, 3.2 * UVS)])
    m.quad("roof", (0, run, rise), (W, run, rise), (W, run + 1.2, 3.2), (0, run + 1.2, 3.2))
    m.profile("metal", 0, W, [(-0.02, 0), (-0.1, 0.02), (-0.1, 0.1), (0.04, 0.12)], caps=False)   # gutter
    if dormer:
        x0, x1, z0, z1 = 1.3, 2.7, 0.55, 2.2
        # dormer front stands in the facade plane, ahead of the sloping roof
        m.wall_with_opening("trim", x0, x1, z0, z1, x0 + 0.2, x1 - 0.2, z0 + 0.2, z1 - 0.25, depth=0.12)
        m.window(x0 + 0.2, x1 - 0.2, z0 + 0.2, z1 - 0.25, depth=0.12, style="cross")
        ytop = run * (z1 / rise)
        m.quad("trim", (x0, 0.0, z0), (x0, run * (z0 / rise), z0), (x0, ytop, z1), (x0, 0.0, z1))   # cheeks
        m.quad("trim", (x1, run * (z0 / rise), z0), (x1, 0.0, z0), (x1, 0.0, z1), (x1, ytop, z1))
        m.quad("roof", (x0 - 0.08, -0.08, z1), (x1 + 0.08, -0.08, z1), (x1 + 0.08, ytop + 0.1, z1 + 0.12), (x0 - 0.08, ytop + 0.1, z1 + 0.12))
        m.snow_ledge(x0 - 0.06, x1 + 0.06, -0.08, z1 + 0.02, 0.5, 0.09)
    return m

def awning():
    m = Module("awning", width=3.2, height=1.0)
    m.quad("awning", (0, 0, 0.9), (3.2, 0, 0.9), (3.2, -1.3, 0.25), (0, -1.3, 0.25), uv=[(0, 0), (4, 0), (4, 1), (0, 1)])
    m.quad("awning", (0, -1.3, 0.25), (3.2, -1.3, 0.25), (3.2, -1.3, 0.02), (0, -1.3, 0.02), uv=[(0, 0), (4, 0), (4, 0.2), (0, 0.2)])
    m.quad("awning", (3.2, 0, 0.9), (0, 0, 0.9), (0, -1.3, 0.25), (3.2, -1.3, 0.25), uv=[(0, 0), (4, 0), (4, 1), (0, 1)])  # underside
    m.profile("snow", 0.05, 3.15, [(-1.28, 0.27), (-1.2, 0.36), (-0.4, 0.76), (-0.1, 0.87)], caps=False)
    return m

def blade_sign():
    m = Module("blade_sign", width=0.9, height=0.9)
    m.box("metal", 0.0, 0.04, -0.95, 0, 0.82, 0.86, "fblrtk")
    m.box("sign_blade", 0.01, 0.05, -0.9, -0.15, 0.05, 0.75, "lr"); m.box("metal", 0.0, 0.06, -0.92, -0.13, 0.03, 0.77, "fbtk")
    return m


MATERIAL_COLORS = {
    "wall": (0.85, 0.82, 0.76), "brick": (0.35, 0.2, 0.15), "stone": (0.5, 0.5, 0.5), "trim": (0.88, 0.86, 0.8), "frame": (0.9, 0.9, 0.88),
    "frame_dark": (0.08, 0.1, 0.1), "glass": (0.1, 0.14, 0.18), "shop_glass": (0.1, 0.14, 0.18), "shop_interior": (1.0, 0.8, 0.55),
    "shop_floor": (0.3, 0.25, 0.2), "shop_side": (0.6, 0.55, 0.5), "sign": (0.1, 0.1, 0.1), "sign_blade": (0.1, 0.1, 0.1), "roof": (0.12, 0.13, 0.14),
    "metal": (0.06, 0.07, 0.08), "door_wood": (0.2, 0.12, 0.07), "snow": (0.95, 0.96, 0.98), "awning": (0.5, 0.1, 0.1), "lamp_glow": (1.0, 0.8, 0.5),
}


def build_all():
    mods = [win_plain(), win_surround(), win_pair(), win_balcony(), win_brick(), win_pair("win_brick_pair", "brick"), win_modern(), win_tower(),
            blank(), blank("blank_brick", "brick"), shop_glass(), shop_glass("shop_glass_plaster", "wall"), shop_door(), portal(), ground_brick(),
            cornice(), band(), parapet(), mansard(False), mansard(True), awning(), blade_sign()]
    return mods


def main(argv):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--fbx")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {}
    for name, col in MATERIAL_COLORS.items():
        mt = bpy.data.materials.new(name); mt.use_nodes = True
        bsdf = mt.node_tree.nodes.get("Principled BSDF")
        if bsdf: bsdf.inputs["Base Color"].default_value = (*col, 1.0)
        mats[name] = mt
    manifest = {"grid": {"panel_width_m": W, "floor_height_m": H, "ground_height_m": HG}, "modules": {}}
    tris_total = 0
    for i, mod in enumerate(build_all()):
        manifest["modules"][mod.name] = {"width": mod.width, "height": mod.height, "parts": []}
        for mat, (verts, faces, uvs) in mod.parts.items():
            if not faces: continue
            me = bpy.data.meshes.new(f"{mod.name}__{mat}")
            me.from_pydata(verts, [], faces); me.update()
            uvl = me.uv_layers.new(name="UVMap")
            k = 0
            for poly, fuv in zip(me.polygons, uvs):
                for li, uvc in zip(poly.loop_indices, fuv):
                    uvl.data[li].uv = uvc
            me.materials.append(mats[mat])
            ob = bpy.data.objects.new(f"{mod.name}__{mat}", me)
            bpy.context.scene.collection.objects.link(ob)
            tris = sum(len(p.vertices) - 2 for p in me.polygons); tris_total += tris
            manifest["modules"][mod.name]["parts"].append({"material": mat, "triangles": tris})
    # Blender is Z-up; the glTF exporter converts to Y-up (module X stays X, depth +Y becomes -Z, height becomes Y).
    bpy.ops.export_scene.gltf(filepath=str(out / "stockholm_facade_kit.glb"), export_format="GLB", export_yup=True, export_apply=True,
                              export_materials="EXPORT", export_normals=True, export_texcoords=True)
    (out / "stockholm_facade_kit.json").write_text(json.dumps(manifest, indent=1))
    if a.fbx:
        fb = pathlib.Path(a.fbx); fb.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=str(fb / "SM_StockholmFacadeKit.fbx"), apply_unit_scale=True, object_types={"MESH"}, mesh_smooth_type="FACE")
    print(f"kit: {len(manifest['modules'])} modules, {tris_total} triangles, {len(MATERIAL_COLORS)} material slots")
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    sys.exit(main(argv))
