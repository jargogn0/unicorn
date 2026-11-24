"""Car body shell: a coarse quad control cage generated from feature-line tables, then Catmull-Clark subdivided.

Design frame (metres): x runs from the nose (0) to the tail (L), y is the lateral half-width (the cage is the
y >= 0 half and is mirrored), z is up. Blender frame: X = y, Y = L/2 - x (front towards +Y, i.e. glTF -Z), Z = z.

Topology ("cube" layout): stations run nose to tail, rows run from the roof centreline (0) over the rail (3),
down the side (4 = top of side glass / wing crown, 5 = belt line, 6 = shoulder, 7..10 = flank, 11 = under tuck).
The front and rear faces are separate patches whose columns continue top rows 0..2 and whose rows continue
side rows 4..11 around the corner, so row 3 ends in a three-way pole at each corner, like the corner of a cube.
Wheel arches are grid columns whose lower rows are placed on the arch circle (faces below are simply left out).
"""
import math
import bpy, bmesh
from .common import Builder, pchip, subdivide, get_mat

GLASS_NAME = "car_glass"
TOP_F = (0.0, 0.40, 0.74, 1.0)      # lateral fraction of top rows 0..3 between centreline and rail
ARCH_ANGLE = {"B": (140.0, 180.0), "C1": (115.0,), "C2": (90.0,), "C3": (65.0,), "D": (40.0, 0.0)}


def to_bl(p, L):
    return (p[1], L / 2 - p[0], p[2])


class Cage:
    def __init__(self, spec, mat_filter=None):
        self.spec = spec
        self.mat_filter = mat_filter
        self.L = spec["L"]
        self.fn = {k: pchip(v) for k, v in spec["rows"].items()}
        self.P = {}       # key -> (x, y, z) design frame, half body
        self.quads = []   # (keys[4], material)
        self.names = {st["name"]: i for i, st in enumerate(spec["stations"])}
        self._stations(); self._fascia("front"); self._fascia("rear"); self._faces()
        self.uv = {}      # (material, key) -> lamp-space uv for cage corners
        for lamp in spec.get("lamps", []):
            for c, u in zip(lamp["cols"], lamp["u"]):
                for r, j in enumerate(lamp["rows"]):
                    key = (self.names[c[1]], j) if c[0] == "st" else (c[0], j, c[1])
                    self.uv[(lamp["mat"], key)] = (u, 1.0 - r / (len(lamp["rows"]) - 1))

    # ------------------------------------------------------------------ points
    def _stations(self):
        sp, fn = self.spec, self.fn
        R, zw = sp["arch_r"], sp["wheel_z"]
        for i, st in enumerate(sp["stations"]):
            pts = st.get("pts", {})
            xs = st.get("xs")
            x0, x3 = st.get("x0", xs), st.get("x3", xs)
            p0 = pts.get(0, (x0, 0.0, fn["z0"](x0)))
            p3 = pts.get(3, (x3, fn["y3"](x3), fn["z3"](x3)))
            crown = st.get("crown", 1.0)
            for j, f in enumerate(st.get("top_f", TOP_F)):
                x = p0[0] + (p3[0] - p0[0]) * f ** 2
                z = p3[2] + (p0[2] - p3[2]) * (1 - f ** 2) ** crown
                self.P[(i, j)] = (x, f * p3[1], z)
            arch = st.get("arch")
            for j in range(4, 12):
                if j in pts:
                    self.P[(i, j)] = pts[j]; continue
                x = st.get(f"x{j}", xs)
                if arch and j >= 8:
                    xa = sp["axle_f"] if arch[0] == "f" else sp["axle_r"]
                    ang = ARCH_ANGLE[arch[1]]
                    if j == 8:
                        t = math.radians(ang[0]); x, z = xa + R * math.cos(t), zw + R * math.sin(t)
                        y = fn["y8"](x) + sp.get("arch_flare", 0.0)
                    elif len(ang) == 1:
                        continue                      # rows below the arch do not exist on C columns
                    else:
                        sgn = -1.0 if arch[1] == "B" else 1.0
                        if j == 9:
                            x, z = xa + sgn * R, zw
                            y = fn["y9"](x) + sp.get("arch_flare", 0.0)
                        else:
                            z10 = fn["z10"](xa + sgn * R)
                            x = xa + sgn * math.sqrt(max(R * R - (zw - z10) ** 2, 0.0))
                            if j == 10: y, z = fn["y10"](x), z10
                            else: y, z = fn["y11"](x), fn["z11"](x)
                    self.P[(i, j)] = (x, y, z); continue
                self.P[(i, j)] = (x, fn[f"y{j}"](x), fn[f"z{j}"](x))

    def _fascia(self, end):
        sp = self.spec
        fs = sp[end]
        i_c = 0 if end == "front" else len(sp["stations"]) - 1
        amp, ref, pw = fs["bow"]
        sgn = 1.0 if end == "front" else -1.0
        for j in range(4, 12):
            xc, z, y1, y2 = fs["rows"][j]
            cx, cy, cz = self.P[(i_c, j)]
            for k, y in enumerate((0.0, y1, y2)):
                t = (y / cy) ** 2
                self.P[(end, j, k)] = (xc + sgn * amp * (y / ref) ** pw, y, z + (cz - z) * t * fs.get("zfollow", 1.0))

    # ------------------------------------------------------------------ faces
    def mat_for(self, kind, a, j, k=None):
        """kind 'body': a = station index of the quad's first station, j = first row. fascia: j = upper row, k = column."""
        out = "car_paint"
        for reg in self.spec["regions"]:
            if reg[1] != kind: continue
            if kind == "body":
                _, _, s0, s1, j0, j1 = reg
                if self.names[s0] <= a < self.names[s1] and j0 <= j < j1: out = reg[0]
            else:
                _, _, j0, j1, k0, k1 = reg
                if j0 <= j < j1 and k0 <= k < k1: out = reg[0]
        if self.mat_filter:
            out = self.mat_filter(self, kind, a, j, k, out)
        return out

    def _faces(self):
        n = len(self.spec["stations"])
        for i in range(n - 1):
            for j in range(11):
                keys = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                if all(k in self.P for k in keys):
                    self.quads.append((keys, self.mat_for("body", i, j)))
        for end, i_c in (("front", 0), ("rear", n - 1)):
            def col(j, k):                       # fascia grid: rows 3 (= lip) .. 11, columns 0..3 (3 = corner line)
                if j == 3: return (i_c, k)
                return (i_c, j) if k == 3 else (end, j, k)
            for j in range(3, 11):
                for k in range(3):
                    keys = [col(j, k), col(j, k + 1), col(j + 1, k + 1), col(j + 1, k)]
                    if end == "rear": keys = keys[::-1]
                    self.quads.append((keys, self.mat_for(end, None, j, k)))

    # ------------------------------------------------------------------ mesh
    def to_object(self, name="body_cage"):
        b = Builder()
        idx, midx = {}, {}
        ys = self.spec.get("y_scale", 1.0)                 # final width trim (subdivision shrinks the cage a little)
        for key, p in self.P.items():
            idx[key] = b.vert(to_bl((p[0], p[1] * ys, p[2]), self.L))
        for key, p in self.P.items():
            midx[key] = idx[key] if abs(p[1]) < 1e-9 else b.vert(to_bl((p[0], -p[1] * ys, p[2]), self.L))
        for keys, mat in self.quads:
            uv = [self.uv.get((mat, k), (0.0, 0.0)) for k in keys]
            b.face([idx[k] for k in keys], mat, uv)
            b.face([midx[k] for k in keys][::-1], mat, uv[::-1])
        ob = b.to_object(name)
        # creases: (row, first station name, last station name, weight) along a row; ('station', name, j0, j1, w) across
        me = ob.data
        bm = bmesh.new(); bm.from_mesh(me)
        cl = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
        bm.verts.ensure_lookup_table()
        emap = {frozenset((e.verts[0].index, e.verts[1].index)): e for e in bm.edges}
        def crease(ka, kb, w):
            for m in (idx, midx):
                if ka in m and kb in m:
                    e = emap.get(frozenset((m[ka], m[kb])))
                    if e is not None: e[cl] = max(e[cl], w)
        for c in self.spec.get("creases", []):
            if c[0] == "row":
                _, j, s0, s1, w = c
                for i in range(self.names[s0], self.names[s1]):
                    crease((i, j), (i + 1, j), w)
            elif c[0] == "station":
                _, s, j0, j1, w = c
                i = self.names[s]
                for j in range(j0, j1):
                    crease((i, j), (i, j + 1), w)
            elif c[0] in ("front", "rear"):          # fascia row crease across columns
                _, j, w = c
                i_c = 0 if c[0] == "front" else len(self.spec["stations"]) - 1
                ks = [(c[0], j, 0), (c[0], j, 1), (c[0], j, 2), (i_c, j)]
                for a, d in zip(ks, ks[1:]): crease(a, d, w)
        bm.to_mesh(me); bm.free()
        return ob


def build_body(spec, levels=2, mat_filter=None, name="body"):
    cage = Cage(spec, mat_filter)
    ob = cage.to_object(name)
    subdivide(ob, levels)
    return ob, cage
