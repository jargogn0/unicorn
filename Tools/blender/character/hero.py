"""Hero-character (Doudou) specific construction: facial morph targets, skin painting, high-top hair,
custom pullover hoodie with rib bands, chunky boots, smartwatch.

Everything in this module is authored geometry / texture work layered on the CC0 MakeHuman base; the only
third-party garments it touches are the jeans and boots named in configs.py.
"""
import math, os
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from . import common as C, meshops as M, materials as MT

BP = 'mixamorig:'
EXPR_DIR = None


def _bone(rig, n):
    return rig.data.bones.get(BP + n) or rig.data.bones.get(n)


def _smooth(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _new_obj(name, role, rig, bm=None):
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o['stk_role'] = role; o.parent = rig
    if bm is not None:
        bm.to_mesh(me); bm.free()
    return o


# ----------------------------------------------------------------------------- morph targets
def set_attr(obj, name, vec):
    at = obj.data.attributes.get(name) or obj.data.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
    at.data.foreach_set('vector', np.asarray(vec, np.float32).ravel())


def get_attr(obj, name):
    at = obj.data.attributes.get(name)
    if at is None:
        return None
    a = np.empty(len(obj.data.vertices) * 3, np.float32); at.data.foreach_get('vector', a)
    return a.reshape(-1, 3)


def capture_morphs(cfg, basemesh, proxies):
    """Store facial morph targets as per-vertex delta attributes ('mt_<Name>') on the base mesh and on the
    fitted proxies (teeth, lashes, brows), so they survive every later mesh edit; export.py turns them into
    shape keys / glTF morph targets.  cfg['morphs'] = {name: [(expression unit, weight), ...]}."""
    import importlib
    TS = importlib.import_module(C.MPFB_MOD + '.services.targetservice').TargetService
    CS = importlib.import_module(C.MPFB_MOD + '.services.clothesservice').ClothesService
    Mhclo = importlib.import_module(C.MPFB_MOD + '.entities.clothes.mhclo').Mhclo
    LS = importlib.import_module(C.MPFB_MOD + '.services.locationservice').LocationService
    race = max(cfg['macro']['race'], key=cfg['macro']['race'].get)
    udir = os.path.join(LS.get_mpfb_data('targets'), 'expression', 'units', race)

    def mix():
        k = basemesh.shape_key_add(name='stk_tmp', from_mix=True)
        co = np.empty(len(basemesh.data.vertices) * 3, np.float32); k.data.foreach_get('co', co)
        basemesh.shape_key_remove(k)
        return co.reshape(-1, 3)

    mh = {}
    for role, (obj, path) in proxies.items():
        m = Mhclo(); m.load(path); m.clothes = obj; mh[role] = m
    neutral = mix()
    pn = {r: M.coords(o).copy() for r, (o, _) in proxies.items()}
    keys = {}
    for name, units in cfg['morphs'].items():
        for unit, w in units:
            if unit not in keys:
                keys[unit] = TS.load_target(basemesh, os.path.join(udir, unit + '.target.gz'), weight=0.0, name='ex_' + unit)
        for k in keys.values():
            k.value = 0.0
        for unit, w in units:
            keys[unit].value = w
        d = mix() - neutral
        set_attr(basemesh, 'mt_' + name, d)
        print('morph', name, 'body verts moved', int((np.abs(d).max(1) > 1e-5).sum()), 'max', float(np.abs(d).max()))
        for r, (o, _) in proxies.items():
            CS.fit_clothes_to_human(o, basemesh, mh[r], set_parent=False)
            set_attr(o, 'mt_' + name, M.coords(o) - pn[r])
    for k in keys.values():
        k.value = 0.0
    for r, (o, _) in proxies.items():
        CS.fit_clothes_to_human(o, basemesh, mh[r], set_parent=False)
    for k in list(keys.values()):
        basemesh.shape_key_remove(k)


def attrs_to_shape_keys(mesh_obj):
    """Convert 'mt_*' delta attributes of the (joined) mesh into shape keys named after the morph."""
    names = [a.name for a in mesh_obj.data.attributes if a.name.startswith('mt_')]
    if not names:
        return []
    base = M.coords(mesh_obj).astype(np.float32)
    deltas = {n: get_attr(mesh_obj, n) for n in names}
    mesh_obj.shape_key_add(name='Basis')
    for n in sorted(names, key=lambda x: (x != 'mt_Smile', x)):
        sk = mesh_obj.shape_key_add(name=n[3:]); sk.value = 0.0
        sk.data.foreach_set('co', (base + deltas[n]).ravel())
    for n in names:
        mesh_obj.data.attributes.remove(mesh_obj.data.attributes[n])
    return [n[3:] for n in names]


# ----------------------------------------------------------------------------- skin
def skin_tone(gain=(1.60, 1.50, 1.46), keep_dark=0.10, full=0.24, sat=1.12):
    """Lift the very dark MakeHuman 'young_african_male' skin to a warm medium-dark brown while leaving the
    painted scalp hair / lash lines dark."""
    def post(im, obj=None):
        a = np.asarray(im.convert('RGB'), np.float32) / 255.0
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        w = _smooth(keep_dark, full, lum)[..., None].astype(np.float32)
        g = 1.0 + (np.array(gain, np.float32) - 1.0) * w
        out = a * g
        m = out.mean(-1, keepdims=True)
        out = m + (out - m) * (1.0 + (sat - 1.0) * w)
        return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')
    return post


def bright_teeth(im, obj=None):
    """The MakeHuman teeth texture has heavy baked occlusion; lift the enamel to a clean off-white."""
    a = np.asarray(im.convert('RGB'), np.float32) / 255.0
    mx = a.max(-1); mn = a.min(-1)
    sat = np.where(mx > 1e-3, (mx - mn) / np.maximum(mx, 1e-3), 0)
    enamel = (_smooth(0.30, 0.12, sat) * _smooth(0.12, 0.3, mx))[..., None].astype(np.float32)
    white = np.clip(0.55 + a * 0.62, 0, 1) * np.array([1.0, 0.98, 0.93], np.float32)
    out = a * (1 - enamel) + white * enamel
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')


def lively_eyes(im, obj=None):
    """Clean bright sclera and a deep-brown iris that still shows its structure (the stock iris is red-brown,
    the stock sclera pinkish grey)."""
    a = np.asarray(im.convert('RGB'), np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    iris = np.clip((r - 1.25 * g) / 0.16, 0, 1)[..., None]
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    brown = np.concatenate([lum * 1.15, lum * 0.72, lum * 0.45], -1)
    sclera = np.clip(0.30 + a * 0.82, 0, 1) * np.array([1.0, 0.985, 0.96], np.float32)
    out = sclera * (1 - iris) + brown * iris
    dark = (lum < 0.12)                      # pupil stays black
    out = np.where(dark, a * 0.6, out)
    return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')


# ----------------------------------------------------------------------------- UV-space baking helpers
def bake_uv_maps(obj, size, face_sel=None):
    """Rasterise the mesh into its UV layout: returns (pos[H,W,3], nrm[H,W,3], valid[H,W]) holding, for every
    texel covered by a face, the 3D position and smooth normal of the surface point it textures."""
    me = obj.data
    me.calc_loop_triangles()
    uv = me.uv_layers.active.data
    co = M.coords(obj)
    vn = np.array([v.normal[:] for v in me.vertices], np.float64)
    pos = np.zeros((size, size, 3), np.float32); nrm = np.zeros((size, size, 3), np.float32)
    valid = np.zeros((size, size), bool)
    for t in me.loop_triangles:
        if face_sel is not None and not face_sel[t.polygon_index]:
            continue
        l = t.loops; v = t.vertices
        u = np.array([[uv[l[k]].uv[0] * size - 0.5, (1.0 - uv[l[k]].uv[1]) * size - 0.5] for k in range(3)])
        x0 = max(int(math.floor(u[:, 0].min())) - 1, 0); x1 = min(int(math.ceil(u[:, 0].max())) + 1, size - 1)
        y0 = max(int(math.floor(u[:, 1].min())) - 1, 0); y1 = min(int(math.ceil(u[:, 1].max())) + 1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        d = (u[1, 1] - u[2, 1]) * (u[0, 0] - u[2, 0]) + (u[2, 0] - u[1, 0]) * (u[0, 1] - u[2, 1])
        if abs(d) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        w0 = ((u[1, 1] - u[2, 1]) * (xs - u[2, 0]) + (u[2, 0] - u[1, 0]) * (ys - u[2, 1])) / d
        w1 = ((u[2, 1] - u[0, 1]) * (xs - u[2, 0]) + (u[0, 0] - u[2, 0]) * (ys - u[2, 1])) / d
        w2 = 1 - w0 - w1
        m = (w0 >= -0.06) & (w1 >= -0.06) & (w2 >= -0.06)          # small bleed over the triangle edge
        if not m.any():
            continue
        W = np.stack([w0[m], w1[m], w2[m]], -1)
        pos[ys[m], xs[m]] = W @ co[list(v)]
        nrm[ys[m], xs[m]] = W @ vn[list(v)]
        valid[ys[m], xs[m]] = True
    return pos, nrm, valid


def face_landmarks(R, rig):
    """Landmarks measured on the finished head (object space, pre-scale): eye centres, mouth corners (from the
    Smile morph), and the mid-line profile points (nose tip, subnasale, lips, chin)."""
    body = R['body']; co = M.coords(body)
    ec = M.coords(R['eyes'])
    L = dict(eye_z=float(ec[:, 2].mean()), eye_x=float(np.abs(ec[:, 0]).mean()), eye_y=float(ec[:, 1].min()))
    head = M.group_weights(body, [b.name for b in rig.data.bones if b.name.endswith('Head')]) > 0.5
    sm = get_attr(body, 'mt_Smile')
    lower = head & (co[:, 2] < L['eye_z'] - 0.02) & (co[:, 1] < L['eye_y'] + 0.03)
    if sm is not None:
        mag = np.linalg.norm(sm, axis=1) * lower
        i = int(np.argmax(mag * (co[:, 0] > 0))); L['corner_x'] = float(abs(co[i, 0])); L['corner_z'] = float(co[i, 2])
        L['corner_y'] = float(co[i, 1])
    # mid-line profile y(z): most forward surface point near x = 0 in 1.5 mm slices
    mid = head & (np.abs(co[:, 0]) < 0.006) & (co[:, 1] < L['eye_y'] + 0.04)
    zs = np.arange(co[mid, 2].min(), L['eye_z'], 0.0015); prof = np.full(len(zs), np.nan)
    for k, z in enumerate(zs):
        m = mid & (np.abs(co[:, 2] - z) < 0.003)
        if m.any(): prof[k] = co[m, 1].min()
    ok = ~np.isnan(prof); prof = np.interp(zs, zs[ok], prof[ok])
    prof = np.convolve(np.pad(prof, 2, mode='edge'), np.ones(5) / 5, mode='valid')
    L['prof_z'] = zs; L['prof_y'] = prof
    k_nose = int(np.argmin(prof)); L['nose_z'] = float(zs[k_nose]); L['nose_y'] = float(prof[k_nose])
    # walk down from the nose tip through the alternating extrema of the profile
    def next_ext(k, kind):
        f = np.argmax if kind == 'max' else np.argmin
        j = k
        while j > 2:
            seg = prof[max(j - 4, 0):j + 1]
            if (kind == 'max' and prof[j - 1] < prof[j] and prof[j] >= seg.max() - 1e-9) or \
               (kind == 'min' and prof[j - 1] > prof[j] and prof[j] <= seg.min() + 1e-9):
                return j
            j -= 1
        return j
    k = k_nose
    names = [('subnasale', 'max'), ('lip_up', 'min'), ('stomion', 'max'), ('lip_low', 'min'), ('sulcus', 'max'), ('pogonion', 'min')]
    for n, kind in names:
        k = next_ext(k - 1, kind); L[n + '_z'] = float(zs[k]); L[n + '_y'] = float(prof[k])
    L['menton_z'] = float(co[mid, 2].min())
    L['head_top'] = float(co[head, 2].max())
    L['head_halfw'] = float(np.abs(co[head & (np.abs(co[:, 2] - L['eye_z']) < 0.02), 0]).max())
    return L


def face_paint(tone=None, hair_rgb=(21, 15, 13)):
    """Skin texture post-process for the hero head: warm tone lift, then crisp facial hair (thin moustache, soul
    patch, goatee, jaw-line stubble), a faded short-hair gradient on the sides / back of the scalp and a slight
    warm flush on ears and nose - all painted by projecting 3D stencils (positioned from measured landmarks)
    into the UV layout."""
    tone = tone or skin_tone()

    def post(im, obj=None):
        from . import finalize as F
        R = F.roles(); rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        im = tone(im)
        size = im.size[0]
        a = np.asarray(im, np.float32) / 255.0
        src_lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        body = R['body']
        head = M.group_weights(body, [b.name for b in rig.data.bones if b.name.endswith(('Head', 'Neck'))]) > 0.3
        fs = np.array([all(head[v] for v in p.vertices) for p in body.data.polygons])
        pos, nrm, valid = bake_uv_maps(body, size, fs)
        L = face_landmarks(R, rig)
        X, Y, Z = pos[..., 0], pos[..., 1], pos[..., 2]
        ax = np.abs(X)
        st = L['stomion_z']; sn = L['subnasale_z']; me = L['menton_z']
        cx = L.get('corner_x', L['eye_x'] * 0.85); cz = L.get('corner_z', st)
        front = valid & (Y < L['eye_y'] + 0.055) & (Z < L['eye_z'] - 0.02)
        rng = np.random.default_rng(5)
        grain = np.asarray(Image.fromarray((rng.random((size, size)) * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(0.7)), np.float32) / 255.0
        grain = np.clip((grain - 0.5) * 3.2 + 0.5, 0, 1)

        def band(d, half, soft=0.0007):
            return 1.0 - _smooth(half - soft, half + soft, d)

        # thin moustache hugging the upper lip, running out to the mouth corners
        t = np.clip(ax / (cx * 1.10), 0, 1)
        z_top = st + (sn - st) * 0.56
        zc = z_top + (cz + 0.0025 - z_top) * t ** 1.7
        half = 0.0030 * (1 - 0.45 * t ** 3)
        mous = band(np.abs(Z - zc), half) * (ax < cx * 1.10) * front
        # soul patch + goatee on the chin, joined to the mouth corners by a light line
        soul = band(ax, 0.0055) * (Z < st - 0.0125) * (Z > st - 0.024) * front
        chin_top = st - 0.0235
        wz = np.clip((chin_top - Z) / max(chin_top - me, 1e-4), 0, 1.5)
        goat = band(ax, 0.017 + 0.011 * np.clip(wz, 0, 1), 0.0012) * (Z < chin_top) * (Z > me - 0.03) * valid * (Y < L['eye_y'] + 0.07)
        p0 = np.array([cx * 1.02, cz - 0.002]); p1 = np.array([0.021, chin_top - 0.006])
        seg = p1 - p0; tt = np.clip(((ax - p0[0]) * seg[0] + (Z - p0[1]) * seg[1]) / (seg @ seg), 0, 1)
        dseg = np.hypot(ax - (p0[0] + tt * seg[0]), Z - (p0[1] + tt * seg[1]))
        conn = band(dseg, 0.0028) * front * 0.55
        # jaw-line stubble: a band following the lower contour of the jaw as seen from the front
        co = M.coords(body)
        hv = head & (co[:, 1] < L['eye_y'] + 0.11) & (co[:, 2] < L['eye_z'] - 0.03)
        xb = np.linspace(0, L['head_halfw'] * 1.02, 24); zj = np.full(len(xb), np.nan)
        for k, x in enumerate(xb):
            m = hv & (np.abs(np.abs(co[:, 0]) - x) < 0.004)
            if m.any(): zj[k] = co[m, 2].min()
        ok = ~np.isnan(zj); zj = np.interp(xb, xb[ok], zj[ok])
        zjx = np.interp(ax, xb, zj)
        fade_ear = 1 - _smooth(L['head_halfw'] * 0.80, L['head_halfw'] * 0.98, ax) * 0.6
        jaw = band(np.abs(Z - (zjx + 0.004)), 0.011, 0.004) * valid * (Y < L['eye_y'] + 0.12) * (Z < st + 0.004) * 0.50 * fade_ear
        under = valid * (nrm[..., 2] < -0.55) * (Z < st) * (Y < L['eye_y'] + 0.07) * (ax < 0.035) * 0.45
        solid = np.clip(np.maximum.reduce([mous, soul, goat * 0.92]), 0, 1)
        light = np.clip(np.maximum.reduce([conn, jaw, under]), 0, 1)
        alpha = np.clip(solid * (0.86 + 0.14 * grain) + (1 - solid) * light * (0.35 + 0.65 * grain), 0, 1)[..., None]
        hair = np.array(hair_rgb, np.float32) / 255.0
        out = a * (1 - alpha) + hair * alpha
        # fade: the painted scalp hair thins out towards the ears / nape so skin shows through
        skin_ref = np.median(a[valid & (Z > L['eye_z'] + 0.025) & (Z < L['eye_z'] + 0.045) & (ax < 0.03) & (src_lum > 0.2)], axis=0)
        scalp = valid & (src_lum < 0.20) & (Z > L['eye_z'] - 0.07) & ~(front & (Z < L['eye_z'] - 0.005))
        z_lo = L['eye_z'] - 0.035; z_hi = L['head_top'] - 0.075
        dens = 0.30 + 0.70 * _smooth(z_lo, z_hi, Z)
        dens = np.clip(dens * (0.88 + 0.12 * grain), 0, 1)[..., None]
        faded = (skin_ref * 0.86)[None, None] * (1 - dens) + np.minimum(out, hair * 1.35) * dens
        sc = np.asarray(Image.fromarray((scalp * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255
        out = out * (1 - sc) + faded * sc
        # warm flush where skin is thin (ears, tip of the nose)
        ear = valid * _smooth(L['head_halfw'] - 0.004, L['head_halfw'] + 0.012, ax) * (np.abs(Z - (L['eye_z'] - 0.01)) < 0.045) * (src_lum > 0.18)
        nose = valid * (1 - _smooth(0.008, 0.02, np.sqrt(X ** 2 + (Z - L['nose_z']) ** 2 + (Y - L['nose_y']) ** 2)))
        flush = np.clip(np.maximum(ear, nose * 0.8), 0, 1)[..., None]
        out = out * (1 + flush * (np.array([1.07, 0.93, 0.90], np.float32) - 1))
        print('face paint: corner', round(cx, 4), round(cz, 4), 'stomion', round(st, 4), 'subnasale', round(sn, 4), 'menton', round(me, 4))
        return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')
    return post


# ----------------------------------------------------------------------------- hair
def hightop_hair(cfg, R, ref, rig):
    """Short curly high-top: a tapered shell over the top / crown of the scalp carrying a few hundred small
    low-poly curl clumps, so the silhouette is knobbly like the sheet; sides and nape stay as the faded
    short hair painted into the skin texture."""
    hc = dict(top=0.030, edge=0.004, clump=0.0115, spacing=0.0135, seed=11, color=(30, 21, 18))
    hc.update(cfg.get('hightop', {}))
    co = M.coords(ref)
    wH = M.group_weights(ref, [BP + 'Head'])
    head = wH > 0.5
    z_top = co[head, 2].max()
    upper = head & (co[:, 2] > z_top - 0.10)
    y_front, y_back = co[upper, 1].min(), co[upper, 1].max()
    chin = co[head & (co[:, 1] < y_front + 0.05), 2].min()
    Hh = z_top - chin
    t = np.clip((co[:, 1] - y_front) / (y_back - y_front), 0, 1)
    tp = hc.get('line_t', [0.00, 0.08, 0.18, 0.30, 0.50, 0.70, 0.85, 1.00])
    hp = hc.get('line_h', [0.800, 0.800, 0.795, 0.790, 0.790, 0.760, 0.660, 0.560])
    line = chin + Hh * np.interp(t, tp, hp)
    scalp = head & (co[:, 2] > line)
    bm = bmesh.new(); bm.from_mesh(ref.data); bm.verts.ensure_lookup_table()
    keep = set(f for f in bm.faces if all(scalp[v.index] for v in f.verts))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    for _ in range(8):                                    # straighten the hairline (clean line-up)
        new = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
                if len(nb) == 2: new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in new.items(): v.co = c
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    bm.normal_update(); bm.verts.ensure_lookup_table()
    dist = {v: (0 if v.is_boundary else None) for v in bm.verts}
    fr = [v for v in bm.verts if v.is_boundary]; d = 0
    while fr:
        d += 1; nx = []
        for v in fr:
            for e in v.link_edges:
                o2 = e.other_vert(v)
                if dist[o2] is None: dist[o2] = d; nx.append(o2)
        fr = nx
    dmax = max(dist.values()) or 1
    cy = (y_front + y_back) / 2
    thick = {}
    for v in bm.verts:
        k = min(dist[v], 5) / 5.0; k = k * k * (3 - 2 * k)
        fwd = float(np.clip((cy - v.co.y) / (cy - y_front), -1, 1))          # +1 front, -1 back
        th = hc['edge'] + (hc['top'] * (0.80 + 0.20 * max(fwd, 0) - 0.30 * max(-fwd, 0)) - hc['edge']) * k
        thick[v.index] = th
        v.co += v.normal * th * 0.62
    bm.normal_update()
    uvl = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        f.smooth = True
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x * 9.0 + 0.5, l.vert.co.y * 9.0 + 0.5)
    # scatter clump centres on the shell (dart throwing), then add a low-poly blob per centre
    rng = np.random.default_rng(hc['seed'])
    cand = []
    for f in bm.faces:
        vs = [v.co for v in f.verts]; ar = f.calc_area()
        n = max(1, int(ar / (hc['spacing'] ** 2) * 6))
        for _ in range(n):
            w = rng.random(len(vs)); w /= w.sum()
            p = sum((vv * float(ww) for vv, ww in zip(vs, w)), Vector())
            th = sum(thick[v.index] * float(ww) for v, ww in zip(f.verts, w))
            cand.append((p, f.normal.copy(), th))
    order = rng.permutation(len(cand)); pts = []
    cell = {}
    for i in order:
        p, n, th = cand[i]
        sp = hc['spacing'] * (0.75 + 0.25 * min(1.0, th / hc['top']))
        key = (int(p.x / sp), int(p.y / sp), int(p.z / sp)); ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in cell.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        if (q - p).length < sp: ok = False; break
        if ok:
            cell.setdefault(key, []).append(p); pts.append((p, n, th))
    ico = bmesh.new(); bmesh.ops.create_icosphere(ico, subdivisions=1, radius=1.0)
    iv = [v.co.copy() for v in ico.verts]; ifc = [[v.index for v in f.verts] for f in ico.faces]; ico.free()
    for p, n, th in pts:
        k = min(1.0, th / hc['top'])
        r = hc['clump'] * (0.55 + 0.45 * k) * rng.uniform(0.85, 1.2)
        rot = Matrix.Rotation(rng.uniform(0, 6.283), 3, n) @ Vector((0, 0, 1)).rotation_difference(n).to_matrix()
        sq = Vector((rng.uniform(0.85, 1.1), rng.uniform(0.85, 1.1), rng.uniform(0.95, 1.35)))
        c = p + n * (th * 0.38 + r * 0.15)
        vs = []
        for q in iv:
            w = Vector((q.x * sq.x, q.y * sq.y, q.z * sq.z)) * r * (1 + 0.10 * rng.uniform(-1, 1))
            vs.append(bm.verts.new(c + rot @ w))
        u0 = rng.random(2)
        for fi in ifc:
            f = bm.faces.new([vs[i] for i in fi]); f.smooth = True
            for l, i in zip(f.loops, fi):
                q = iv[i]
                l[uvl].uv = (u0[0] + 0.5 + math.atan2(q.y, q.x) / 6.283 * 0.5, u0[1] + 0.5 + q.z * 0.25)
    o = _new_obj('stk_hair', 'hair', rig, bm)
    vg = o.vertex_groups.new(name=BP + 'Head'); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    am = o.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    print('hightop: clumps', len(pts), 'tris', sum(len(p.vertices) - 2 for p in o.data.polygons))
    h = MT.curls_height(512, seed=7, cell=hc.get('cell', 14))
    npth = MT.save_tex(MT.height_to_normal(h, 5.0), cfg['name'] + '_hair_n', quality=90)
    base = np.array(hc['color'], np.float32)[None, None] * (0.50 + 0.80 * h[..., None])
    bp = MT.save_tex(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_hair', quality=88)
    m = MT.make_material(cfg['name'] + '_hair', base=bp, roughness=0.80, normal=npth, normal_strength=1.6, double_sided=False)
    MT.assign(o, m); o['stk_custom_mat'] = True
    return o
