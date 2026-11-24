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


def _strip_layers(bm):
    """Geometry cut out of the body must not inherit its skin weights or morph-delta attributes (stale weight
    indices would bind it to arbitrary bones once meshes are joined)."""
    for lay in list(bm.verts.layers.deform):
        bm.verts.layers.deform.remove(lay)
    for lay in list(bm.verts.layers.float_vector):
        bm.verts.layers.float_vector.remove(lay)
    for lay in list(bm.verts.layers.shape):
        bm.verts.layers.shape.remove(lay)


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
    keys = {}
    rest = dict(cfg.get('neutral_expression', []))        # expression units baked into the resting face
    for unit, w in rest.items():
        keys[unit] = TS.load_target(basemesh, os.path.join(udir, unit + '.target.gz'), weight=w, name='ex_' + unit)
    for r, (o, _) in proxies.items():
        CS.fit_clothes_to_human(o, basemesh, mh[r], set_parent=False)
    neutral = mix()
    pn = {r: M.coords(o).copy() for r, (o, _) in proxies.items()}
    for name, units in cfg['morphs'].items():
        for unit, w in units:
            if unit not in keys:
                keys[unit] = TS.load_target(basemesh, os.path.join(udir, unit + '.target.gz'), weight=0.0, name='ex_' + unit)
        for u_, k in keys.items():
            k.value = rest.get(u_, 0.0)
        for unit, w in units:
            keys[unit].value = max(w, rest.get(unit, 0.0))
        d = mix() - neutral
        set_attr(basemesh, 'mt_' + name, d)
        print('morph', name, 'body verts moved', int((np.abs(d).max(1) > 1e-5).sum()), 'max', float(np.abs(d).max()))
        for r, (o, _) in proxies.items():
            CS.fit_clothes_to_human(o, basemesh, mh[r], set_parent=False)
            set_attr(o, 'mt_' + name, M.coords(o) - pn[r])
    for u_, k in keys.items():
        k.value = rest.get(u_, 0.0)
    for r, (o, _) in proxies.items():
        CS.fit_clothes_to_human(o, basemesh, mh[r], set_parent=False)
    for u_, k in list(keys.items()):
        if u_ not in rest:                                 # rest-expression keys stay and are baked with the body
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
def skin_tone(gain=(1.72, 1.60, 1.55), keep_dark=0.10, full=0.24, sat=1.14):
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
    brown = np.concatenate([lum * 1.55, lum * 0.95, lum * 0.55], -1)
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
    # mid-line profile y(z): most forward surface point near x = 0 in 1.5 mm slices
    mid = head & (np.abs(co[:, 0]) < 0.006) & (co[:, 1] < L['eye_y'] + 0.04)
    zs = np.arange(co[mid, 2].min(), L['eye_z'], 0.0015); prof = np.full(len(zs), np.nan)
    for k, z in enumerate(zs):
        m = mid & (np.abs(co[:, 2] - z) < 0.003)
        if m.any(): prof[k] = co[m, 1].min()
    ok = ~np.isnan(prof); prof = np.interp(zs, zs[ok], prof[ok])
    prof = np.convolve(np.pad(prof, 2, mode='edge'), np.ones(5) / 5, mode='valid')
    L['prof_z'] = zs; L['prof_y'] = prof
    def ext(z0, z1, kind):
        m = (zs >= z0) & (zs <= z1)
        if not m.any():
            return float((z0 + z1) / 2), float(np.interp((z0 + z1) / 2, zs, prof))
        idx = np.nonzero(m)[0]
        k = idx[np.argmin(prof[idx])] if kind == 'fwd' else idx[np.argmax(prof[idx])]
        return float(zs[k]), float(prof[k])
    ez = L['eye_z']
    L['nose_z'], L['nose_y'] = ext(ez - 0.065, ez - 0.02, 'fwd')
    sm = get_attr(body, 'mt_Smile')
    if sm is not None:                                   # mouth corners travel furthest in the smile
        zone = head & (np.abs(co[:, 2] - (L['nose_z'] - 0.028)) < 0.026) & (np.abs(co[:, 0]) > 0.012) & (co[:, 1] < L['eye_y'] + 0.03)
        mag = np.linalg.norm(sm, axis=1) * zone * (co[:, 0] > 0)
        i = int(np.argmax(mag)); L['corner_x'] = float(abs(co[i, 0])); L['corner_z'] = float(co[i, 2]); L['corner_y'] = float(co[i, 1])
    cz0 = L.get('corner_z', L['nose_z'] - 0.03)
    L['stomion_z'], L['stomion_y'] = ext(cz0 - 0.006, cz0 + 0.010, 'back')
    st = L['stomion_z']
    L['subnasale_z'], L['subnasale_y'] = ext(st + 0.010, L['nose_z'] - 0.003, 'back')
    L['pogonion_z'], L['pogonion_y'] = ext(st - 0.055, st - 0.020, 'fwd')
    L['sulcus_z'], L['sulcus_y'] = ext(L['pogonion_z'], st - 0.008, 'back')
    below = (zs < L['pogonion_z']) & (prof < L['pogonion_y'] + 0.012)
    L['menton_z'] = float(zs[below].min()) if below.any() else L['pogonion_z'] - 0.012
    L['head_top'] = float(co[head, 2].max())
    L['head_halfw'] = float(np.abs(co[head & (np.abs(co[:, 2] - L['eye_z']) < 0.02), 0]).max())
    return L


def face_paint(tone=None, hair_rgb=(30, 20, 17), cfg_jaw=0.0):
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
        # short-hair streak pattern (fine, mostly vertical strokes) so painted hair reads as hair, not as a fill
        st_img = Image.fromarray((rng.random((size, size // 3)) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC)
        streak = np.asarray(st_img.filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255.0
        streak = np.clip((streak - 0.42) * 4.0, 0, 1)

        def band(d, half, soft=0.0007):
            return 1.0 - _smooth(half - soft, half + soft, d)

        def ell(cx_, cz_, rx, rz, soft=0.18):
            d = np.sqrt(((ax - cx_) / rx) ** 2 + ((Z - cz_) / rz) ** 2)
            return 1.0 - _smooth(1.0 - soft, 1.0 + soft, d)

        pg_y = float(np.interp(st - 0.030, L['prof_z'], L['prof_y']))            # chin front
        chin = valid & (Y < pg_y + 0.030)                                       # chin, not the neck behind it
        # thin moustache hugging the upper lip, running out to (and just past) the mouth corners
        t = np.clip(ax / (cx * 1.08), 0, 1)
        z_top = st + (sn - st) * 0.80
        zc = z_top + (cz + 0.0100 - z_top) * t ** 2.2 - 0.0010 * np.exp(-(ax / 0.004) ** 2)   # slight cupid's-bow dip
        half = 0.0023 * (1 - 0.40 * t ** 3)
        mous = band(np.abs(Z - zc), half, 0.0011) * (1 - _smooth(cx * 0.92, cx * 1.10, ax)) * front
        # soul patch under the lower lip, short goatee on the chin
        soul = ell(0.0, st - 0.0195, 0.0058, 0.0050) * front
        goat = ell(0.0, me + 0.013, 0.0215, 0.0150, 0.30) * chin * (Y < L['eye_y'] + 0.06)
        goat = np.maximum(goat, (nrm[..., 2] < -0.35) * chin * (ax < 0.020) * (Z < me + 0.012) * (Z > me - 0.012) * 0.9)
        # light line from each mouth corner down to the goatee
        p0 = np.array([cx * 1.04, cz - 0.001]); p1 = np.array([0.0185, me + 0.020])
        seg = p1 - p0; tt = np.clip(((ax - p0[0]) * seg[0] + (Z - p0[1]) * seg[1]) / (seg @ seg), 0, 1)
        dseg = np.hypot(ax - (p0[0] + tt * seg[0]), Z - (p0[1] + tt * seg[1]))
        conn = band(dseg, 0.0016, 0.0006) * front * 0.60
        # jaw-line stubble: the strip where the cheek turns under into the jaw (normal tilting downwards)
        nz = nrm[..., 2]
        edge = _smooth(-0.24, -0.40, nz) * (1 - _smooth(-0.66, -0.86, nz))
        jaw = edge * valid * (Z < st - 0.016) * (Z > me - 0.02) * (Y < L['eye_y'] + 0.100) * (Y > pg_y + 0.004) * 0.34
        # eyebrows: soft, arched, relaxed - painted so they move with the skin in every expression.  The fitted
        # eyebrow proxy (dropped afterwards) only supplies where the brow ridge is.
        brow = np.zeros_like(Z)
        if 'eyebrows' in R:
            bc = M.coords(R['eyebrows'])
            bx0, bx1 = np.percentile(np.abs(bc[:, 0]), 2), np.percentile(np.abs(bc[:, 0]), 98)
            xs_ = np.linspace(bx0, bx1, 9); zs_ = []
            for x_ in xs_:
                m_ = np.abs(np.abs(bc[:, 0]) - x_) < (bx1 - bx0) / 8
                zs_.append(bc[m_, 2].mean() if m_.any() else np.nan)
            zs_ = np.array(zs_); okb = ~np.isnan(zs_); zs_ = np.interp(xs_, xs_[okb], zs_[okb])
            u = np.clip((ax - bx0) / (bx1 - bx0), 0, 1)
            zb = np.interp(ax, xs_, zs_) + 0.0026 + 0.0032 * np.sin(np.pi * u ** 0.85) - 0.0015 * u ** 2
            hb_ = 0.0034 * (0.82 + 0.35 * np.sin(np.pi * np.clip(u * 0.9, 0, 1))) * (1 - 0.72 * u ** 2.2)
            ends_ = _smooth(-0.04, 0.12, (ax - bx0) / (bx1 - bx0)) * (1 - _smooth(0.93, 1.04, (ax - bx0) / (bx1 - bx0)))
            brow = band(np.abs(Z - zb), hb_, 0.0016) * ends_ * valid * (Y < L['eye_y'] + 0.04) * (Z > L['eye_z'])
        solid = np.clip(np.maximum.reduce([mous * 0.90, soul * 0.80, goat * 0.88, brow * 0.86]), 0, 1)
        light = np.clip(jaw * cfg_jaw, 0, 1)                  # (mouth-corner lines read as creases: left out)
        alpha = np.clip(solid * (0.62 + 0.30 * streak + 0.08 * grain) + (1 - solid) * light * (0.25 + 0.75 * streak), 0, 1)[..., None]
        hair = np.array(hair_rgb, np.float32) / 255.0
        out = a * (1 - alpha) + hair * alpha
        # fade: the painted scalp hair thins out towards the ears / nape so skin shows through (skin fade)
        skin_ref = np.median(a[valid & (Z > L['eye_z'] + 0.025) & (Z < L['eye_z'] + 0.045) & (ax < 0.03) & (src_lum > 0.2)], axis=0)
        scalp = valid & (src_lum < 0.20) & (Z > L['eye_z'] - 0.07) & ~(front & (Z < L['eye_z'] - 0.005))
        z_lo = L['eye_z'] - 0.030; z_hi = L['head_top'] - 0.040
        dens = 0.50 + 0.47 * _smooth(z_lo, z_hi, Z)
        dens = np.clip(dens * (0.85 + 0.15 * grain), 0, 1)[..., None]
        faded = (skin_ref * 0.90)[None, None] * (1 - dens) + (hair * 1.25) * dens
        sc = np.asarray(Image.fromarray((scalp * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)), np.float32)[..., None] / 255
        out = out * (1 - sc) + faded * sc
        # warm flush where skin is thin (ears, tip of the nose)
        ear = valid * _smooth(L['head_halfw'] - 0.004, L['head_halfw'] + 0.012, ax) * (np.abs(Z - (L['eye_z'] - 0.01)) < 0.045) * (src_lum > 0.18)
        nose = valid * (1 - _smooth(0.008, 0.02, np.sqrt(X ** 2 + (Z - L['nose_z']) ** 2 + (Y - L['nose_y']) ** 2)))
        flush = np.clip(np.maximum(ear, nose * 0.35), 0, 1)[..., None]
        out = out * (1 + flush * (np.array([1.07, 0.93, 0.90], np.float32) - 1))
        print('face paint:', {k: round(v, 4) for k, v in L.items() if not k.startswith('prof')})
        return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')
    return post


# ----------------------------------------------------------------------------- hair
def hightop_hair(cfg, R, ref, rig):
    """Short curly high-top: a tapered shell over the top / crown of the scalp carrying a few hundred small
    low-poly curl clumps, so the silhouette is knobbly like the sheet; sides and nape stay as the faded
    short hair painted into the skin texture."""
    hc = dict(top=0.027, edge=0.003, clump=0.0084, spacing=0.0098, seed=11, color=(34, 23, 19))
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
    hp = hc.get('line_h', [0.835, 0.835, 0.800, 0.745, 0.715, 0.660, 0.540, 0.430])
    line = chin + Hh * np.interp(t, tp, hp)
    scalp = head & (co[:, 2] > line)
    bm = bmesh.new(); bm.from_mesh(ref.data); _strip_layers(bm); bm.verts.ensure_lookup_table()
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
        k = min(dist[v], 7) / 7.0; k = k * k * (3 - 2 * k)
        fwd = float(np.clip((cy - v.co.y) / (cy - y_front), -1, 1))          # +1 front, -1 back
        side = min(1.0, abs(v.co.x) / 0.075)
        low = float(np.clip((z_top - 0.035 - v.co.z) / 0.10, 0, 1))            # shorter down the sides / back
        th = hc['edge'] + (hc['top'] * (0.90 + 0.15 * max(fwd, 0) - 0.20 * max(-fwd, 0)) * (1 - 0.45 * side ** 2)
                           * (1 - 0.60 * low) - hc['edge']) * k
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
    # low-poly clump template: 7 segments x 4 rings (42 triangles)
    seg_n, ring_n = 7, 4
    iv = [Vector((0, 0, 1))]
    for r_ in range(1, ring_n):
        th = math.pi * r_ / ring_n
        for s_ in range(seg_n):
            ph = 2 * math.pi * (s_ + 0.5 * (r_ % 2)) / seg_n
            iv.append(Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))))
    iv.append(Vector((0, 0, -1)))
    ifc = []
    for s_ in range(seg_n):
        ifc.append([0, 1 + s_, 1 + (s_ + 1) % seg_n])
    for r_ in range(ring_n - 2):
        a0 = 1 + r_ * seg_n; b0 = a0 + seg_n
        for s_ in range(seg_n):
            s1 = (s_ + 1) % seg_n
            if r_ % 2 == 0:
                ifc.append([a0 + s_, b0 + s_, a0 + s1]); ifc.append([a0 + s1, b0 + s_, b0 + s1])
            else:
                ifc.append([a0 + s_, b0 + s_, b0 + s1]); ifc.append([a0 + s_, b0 + s1, a0 + s1])
    last = len(iv) - 1; a0 = 1 + (ring_n - 2) * seg_n
    for s_ in range(seg_n):
        ifc.append([last, a0 + (s_ + 1) % seg_n, a0 + s_])
    for p, n, th in pts:
        k = min(1.0, th / hc['top'])
        r = hc['clump'] * (0.50 + 0.50 * k) * rng.uniform(0.70, 1.30)
        tilt = Matrix.Rotation(rng.uniform(-0.6, 0.6), 3, 'X') @ Matrix.Rotation(rng.uniform(-0.6, 0.6), 3, 'Y')
        rot = Vector((0, 0, 1)).rotation_difference(n).to_matrix() @ tilt @ Matrix.Rotation(rng.uniform(0, 6.283), 3, 'Z')
        sq = Vector((rng.uniform(0.85, 1.10), rng.uniform(0.85, 1.10), rng.uniform(1.00, 1.35)))
        c = p + n * (th * 0.38 + r * 0.35 * sq.z * rng.uniform(0.5, 1.3))
        vs = []
        for q in iv:
            w = Vector((q.x * sq.x, q.y * sq.y, q.z * sq.z)) * r * (1 + 0.07 * rng.uniform(-1, 1))
            vs.append(bm.verts.new(c + rot @ w))
        u0 = rng.random(2)
        for fi in ifc:
            f = bm.faces.new([vs[i] for i in fi]); f.smooth = True
            for l, i in zip(f.loops, fi):
                q = iv[i]
                l[uvl].uv = (u0[0] + 0.5 + math.atan2(q.y, q.x) / 6.283 * 0.5, u0[1] + 0.5 + q.z * 0.25)
    bm.normal_update()
    if sum(f.normal.dot(f.calc_center_median() - Vector((0, cy, z_top - 0.08))) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    o = _new_obj('stk_hair', 'hair', rig, bm)
    vg = o.vertex_groups.new(name=BP + 'Head'); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    am = o.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    print('hightop: clumps', len(pts), 'tris', sum(len(p.vertices) - 2 for p in o.data.polygons))
    h = MT.curls_height(512, seed=7, cell=hc.get('cell', 14))
    npth = MT.save_tex(MT.height_to_normal(h, 5.0), cfg['name'] + '_hair_n', quality=90)
    base = np.array(hc['color'], np.float32)[None, None] * (0.70 + 0.45 * h[..., None])
    bp = MT.save_tex(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_hair', quality=88)
    m = MT.make_material(cfg['name'] + '_hair', base=bp, roughness=0.70, normal=npth, normal_strength=1.6, double_sided=False)
    MT.assign(o, m); o['stk_custom_mat'] = True
    return o


# ----------------------------------------------------------------------------- pullover hoodie (authored)
def _loops(bm):
    """Boundary loops of a bmesh as ordered vertex lists."""
    out = []; seen = set()
    for e0 in bm.edges:
        if not e0.is_boundary or e0 in seen:
            continue
        loop = [e0.verts[0]]; v = e0.verts[1]; seen.add(e0); prev_e = e0
        while v is not loop[0]:
            loop.append(v)
            nxt = [e for e in v.link_edges if e.is_boundary and e is not prev_e]
            if not nxt: break
            prev_e = nxt[0]; seen.add(prev_e); v = prev_e.other_vert(v)
        out.append(loop)
    return out


def _box_uv(bm, uvl, scale):
    for f in bm.faces:
        n = f.normal; a = (abs(n.x), abs(n.y), abs(n.z))
        for l in f.loops:
            p = l.vert.co
            if a[1] >= a[0] and a[1] >= a[2]: uv = (p.x, p.z)
            elif a[0] >= a[2]: uv = (p.y, p.z)
            else: uv = (p.x, p.y)
            l[uvl].uv = (uv[0] * scale, uv[1] * scale)


def _band(bm, uvl, loop, direction, length, shrink, ribs_per_m, rows=3, centre=None, bulge=0.004):
    """Rib band continuing a boundary loop: `direction` is the unit vector the band extends along."""
    pts = [v.co.copy() for v in loop]; n = len(pts)
    c = centre or sum(pts, Vector()) / n
    arc = [0.0]
    for i in range(1, n + 1):
        arc.append(arc[-1] + (pts[i % n] - pts[i - 1]).length)
    rings = []
    for r in range(rows + 1):
        t = r / rows
        ring = []
        for i, p in enumerate(pts):
            rad = p - c; rad -= direction * rad.dot(direction)
            k = shrink * (1.0 + 0.15 * t) - bulge * math.sin(math.pi * t)
            q = p - rad.normalized() * k + direction * (length * t)
            ring.append(bm.verts.new(q))
        rings.append(ring)
    faces = []
    for r in range(rows):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new([rings[r][i], rings[r][j], rings[r + 1][j], rings[r + 1][i]]); f.smooth = True
            us = [arc[i], arc[i + 1], arc[i + 1], arc[i]]; vs = [r / rows, r / rows, (r + 1) / rows, (r + 1) / rows]
            for l, u, v in zip(f.loops, us, vs):
                l[uvl].uv = (u * ribs_per_m, v)
            faces.append(f)
    return faces


def build_hoodie(cfg, R, ref, rig):
    """Classic pullover hoodie authored from the CC0 body surface: relaxed torso / sleeve shell with bunching
    above the cuffs, separate rib-knit cuffs and hem band, hood resting behind the neck with crossed front
    edges, two drawstrings, kangaroo pocket, chest logo decal."""
    hp = dict(color=(160, 126, 162), clear=0.013, hem_drop=0.105, sleeve_short=0.105, cuff=0.055, hem_band=0.060)
    hp.update(cfg.get('hoodie', {}))
    B = lambda n: _bone(rig, n)
    co = M.coords(ref)
    z_neck = B('Neck').head_local.z; y_neck = B('Neck').head_local.y
    z_hem = B('LeftUpLeg').head_local.z - hp['hem_drop'] + hp['hem_band']
    # --- 1. torso + sleeves cut out of the body surface
    bm = bmesh.new(); bm.from_mesh(ref.data); _strip_layers(bm)
    def cut(co_, no_, pred):
        geom = [g for g in list(bm.verts) + list(bm.edges) + list(bm.faces)
                if all(pred(v.co) for v in (g.verts if hasattr(g, 'verts') else [g]))]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=co_, plane_no=no_, clear_outer=True)
    cut(Vector((0, 0, z_hem)), Vector((0, 0, -1)), lambda p: True)
    neck_pt = Vector((0, y_neck - 0.03, z_neck - 0.012)); neck_no = Vector((0, -0.50, 0.87)).normalized()
    cut(neck_pt, neck_no, lambda p: abs(p.x) < 0.14 and p.z > z_neck - 0.12)
    ends = {}
    for s_ in ('Left', 'Right'):
        e = B(s_ + 'ForeArm').head_local; w = B(s_ + 'Hand').head_local
        ax = (w - e).normalized(); pt = w - ax * hp['sleeve_short']
        sgn = 1 if s_ == 'Left' else -1
        cut(pt, ax, lambda p, sgn=sgn, e=e: p.x * sgn > e.x * sgn - 0.02)
        ends[s_] = (pt, ax)
    # keep the connected piece containing the chest
    bm.verts.ensure_lookup_table()
    seed = min(bm.verts, key=lambda v: (v.co - Vector((0, -0.2, B('Spine2').head_local.z))).length)
    keep = {seed}; st = [seed]
    while st:
        x = st.pop()
        for e in x.link_edges:
            o2 = e.other_vert(x)
            if o2 not in keep: keep.add(o2); st.append(o2)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in keep], context='VERTS')
    # --- 2. relax into cloth: inflate, smooth away anatomy, keep clear of the body
    tree, tb = M.bvh_of(ref)
    def relax(iters, lam=0.5):
        for _ in range(iters):
            new = {}
            for v in bm.verts:
                if v.is_boundary: continue
                acc = Vector(); nlk = 0
                for e in v.link_edges:
                    acc += e.other_vert(v).co; nlk += 1
                new[v] = v.co.lerp(acc / nlk, lam)
            for v, c in new.items(): v.co = c
    def clearance(p):
        zt = float(np.clip((B('Spine2').head_local.z - p.z) / 0.30, 0, 1))        # looser towards the hem
        arm = float(np.clip((abs(p.x) - 0.20) / 0.10, 0, 1))
        return hp['clear'] + 0.008 * zt * (1 - arm) + 0.006 * arm
    def keep_clear(scale=1.0):
        for v in bm.verts:
            loc, nor, _, d = tree.find_nearest(v.co)
            if loc is None: continue
            sd = (v.co - loc).dot(nor); c = clearance(v.co) * scale
            if sd < c: v.co += nor * (c - sd)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * clearance(v.co)
    relax(10); keep_clear(); relax(6); keep_clear(0.9)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=0.6)
    relax(3); keep_clear(0.85)
    # drape: below the chest the front hangs from the chest line instead of following the belly
    z_a = B('Spine2').head_local.z; y_s = B('Spine2').head_local.y
    fr = [v for v in bm.verts if v.co.y < y_s - 0.03 and abs(v.co.x) < 0.24]
    xb = np.linspace(-0.24, 0.24, 25); ya = np.full(len(xb), np.nan)
    for k, x in enumerate(xb):
        ys = [v.co.y for v in fr if abs(v.co.x - x) < 0.015 and abs(v.co.z - z_a) < 0.04]
        if ys: ya[k] = min(ys)
    ok = ~np.isnan(ya); ya = np.interp(xb, xb[ok], ya[ok])
    env = np.array([ya[max(0, k - 3):k + 4].min() for k in range(len(ya))])
    env = np.convolve(np.pad(env, 2, mode='edge'), np.ones(5) / 5, mode='valid')
    for v in fr:
        if v.co.z < z_a + 0.03 and not v.is_boundary:
            yd = float(np.interp(v.co.x, xb, env)) + 0.04 * max(z_a - v.co.z, 0)
            w = (1 - float(_smooth(0.12, 0.22, abs(v.co.x)))) * float(_smooth(z_a + 0.03, z_a - 0.03, v.co.z))
            v.co.y += w * (min(v.co.y, yd) - v.co.y)
    relax(2, 0.4)
    # relaxed, boxy body: below the chest the sides and back fall straight instead of following the waist
    def is_arm(p):
        for s_ in ('Left', 'Right'):
            a0 = B(s_ + 'Arm').head_local; a1 = B(s_ + 'ForeArm').head_local; a2 = B(s_ + 'Hand').head_local
            for q0, q1 in ((a0, a1), (a1, a2)):
                d = q1 - q0; t_ = max(0.0, min(1.0, (p - q0).dot(d) / d.dot(d)))
                if (p - (q0 + d * t_)).length < 0.075 and abs(p.x) > abs(a0.x) + 0.035:
                    return True
        return False
    z_box = B('Spine2').head_local.z - 0.075
    ctr = Vector((0, B('Spine1').head_local.y, 0))
    nbin = 48; prof = np.zeros(nbin)
    torso_v = [v for v in bm.verts if v.co.z < z_box + 0.03 and not is_arm(v.co)]
    for v in torso_v:
        if abs(v.co.z - z_box) < 0.035:
            k = int((math.atan2(v.co.y - ctr.y, v.co.x) + math.pi) / (2 * math.pi) * nbin) % nbin
            prof[k] = max(prof[k], math.hypot(v.co.x, v.co.y - ctr.y))
    for k in range(nbin):
        if prof[k] == 0: prof[k] = max(prof[(k - 1) % nbin], prof[(k + 1) % nbin])
    prof = np.convolve(np.concatenate([prof[-2:], prof, prof[:2]]), np.ones(5) / 5, mode='valid')
    for v in torso_v:
        if v.is_boundary and v.co.z > z_box: continue
        a_ = math.atan2(v.co.y - ctr.y, v.co.x); k = (a_ + math.pi) / (2 * math.pi) * nbin
        r_t = float(np.interp(k % nbin, np.arange(nbin + 1), np.append(prof, prof[0]))) * hp.get('box', 0.91)
        r = math.hypot(v.co.x, v.co.y - ctr.y)
        w = float(_smooth(z_box + 0.03, z_box - 0.06, v.co.z))
        if r < r_t:
            s_ = 1 + w * (r_t / max(r, 1e-4) - 1)
            v.co.x *= s_; v.co.y = ctr.y + (v.co.y - ctr.y) * s_
    relax(3, 0.4)
    # folds: stacking above the cuffs, blousing over the hem band, a few soft creases
    bm.normal_update()
    rng = np.random.default_rng(3)
    ph = rng.uniform(0, 6.28, 4)
    for v in bm.verts:
        if v.is_boundary: continue
        p = v.co; d = 0.0
        for s_ in ('Left', 'Right'):
            pt, ax = ends[s_]; sgn = 1 if s_ == 'Left' else -1
            if p.x * sgn > 0.2:
                sdist = (pt - p).dot(ax)                                   # distance up the arm from the sleeve end
                if 0 <= sdist < 0.13:
                    ramp = math.sin(math.pi * min(1.0, sdist / 0.13)) ** 0.8
                    around = math.atan2(p.z - pt.z, p.y - pt.y)
                    d += 0.0038 * ramp * math.sin(sdist / 0.048 * 2 * math.pi + 1.6 * math.sin(around + ph[0])) + 0.007 * ramp
        if abs(p.x) < 0.26:
            hz = p.z - z_hem
            if 0 <= hz < 0.12:
                d += 0.008 * math.sin(math.pi * min(1.0, hz / 0.10)) ** 0.7
            d += 0.0035 * math.sin(p.z * 23 + p.x * 9 + ph[1]) * math.sin(p.x * 17 + ph[2]) * float(_smooth(z_a + 0.05, z_a - 0.1, p.z))
        v.co += v.normal * d
    # gather the cloth into the rib bands: pull the last few centimetres in towards the band's (snugger) radius
    hem_c = Vector((0, B('Hips').head_local.y, z_hem))
    for v in bm.verts:
        p = v.co
        if abs(p.x) > 0.25 and p.z < z_neck - 0.15:
            pt, ax = ends['Left' if p.x > 0 else 'Right']
            sdist = (pt - p).dot(ax)
            if 0 <= sdist < 0.035:
                axis_pt = pt - ax * sdist
                core = B(('Left' if p.x > 0 else 'Right') + 'Hand').head_local
                cpt = core + ax * (axis_pt - core).dot(ax)
                rad = p - cpt
                p += -rad.normalized() * 0.010 * (1 - sdist / 0.035) ** 1.5
        elif p.z < z_hem + 0.04 and abs(p.x) < 0.3:
            k = (1 - (p.z - z_hem) / 0.04) ** 1.5
            rad = Vector((p.x - hem_c.x, p.y - hem_c.y, 0))
            p -= rad.normalized() * 0.012 * k
    # put the open edges back exactly on their cutting planes (clean hem / sleeve ends / neckline)
    for v in bm.verts:
        if not v.is_boundary: continue
        p = v.co
        if abs(p.x) > 0.25 and p.z < z_neck - 0.15:
            pt, ax = ends['Left' if p.x > 0 else 'Right']
            v.co = p - ax * (p - pt).dot(ax)
        elif p.z < z_hem + 0.06:
            v.co.z = z_hem
        else:
            v.co = p - neck_no * (p - neck_pt).dot(neck_no)
    bm.normal_update()
    uvl = bm.loops.layers.uv.verify()
    for f in bm.faces: f.smooth = True
    _box_uv(bm, uvl, hp.get('uv_scale', 6.5))
    # --- 3. rib bands (own object / material)
    rb = bmesh.new(); ruv = rb.loops.layers.uv.new('UVMap')
    loops = _loops(bm)
    info = {}
    for lp in loops:
        c = sum((v.co for v in lp), Vector()) / len(lp)
        print('hoodie loop', len(lp), tuple(round(x, 3) for x in c), 'z_hem', round(z_hem, 3))
        if abs(c.x) > 0.25:
            s_ = 'Left' if c.x > 0 else 'Right'
            tmp = [rb.verts.new(v.co) for v in lp]
            _band(rb, ruv, tmp, ends[s_][1], hp['cuff'], 0.002, 260, rows=3, bulge=0.0015)
            bmesh.ops.delete(rb, geom=tmp, context='VERTS')
            info['cuff_' + s_] = c
        elif c.z < z_hem + 0.05:
            tmp = [rb.verts.new(v.co) for v in lp]
            _band(rb, ruv, tmp, Vector((0, 0, -1)), hp['hem_band'], 0.002, 230, rows=3, bulge=0.002)
            bmesh.ops.delete(rb, geom=tmp, context='VERTS')
            info['hem'] = c
        else:
            info['neck'] = lp
    rb.normal_update()
    # --- 4. hood: a band swept around the neck (rim rolled up behind the neck, draped pouch on the back,
    #         the two front ends crossing at the collarbone)
    neck = info['neck']
    nc = sum((v.co for v in neck), Vector()) / len(neck)
    ang = np.array([math.atan2(v.co.x - nc.x, -(v.co.y - nc.y)) for v in neck])          # 0 = front, +-pi = back
    order = np.argsort(ang); angs = ang[order]; npts = np.array([neck[i].co[:] for i in order])
    def base(theta):
        th = (theta + math.pi) % (2 * math.pi) - math.pi
        return Vector([float(np.interp(th, angs, npts[:, k], period=2 * math.pi)) for k in range(3)])
    stree = BVHTree.FromBMesh(bm)
    NU, NV = 60, 13
    over = math.radians(16)                         # each end passes the centre line by this much
    hb = bmesh.new(); huv = hb.loops.layers.uv.new('UVMap'); grid = {}
    for i in range(NU):
        u = i / (NU - 1)
        theta = -over + u * (2 * math.pi + 2 * over)             # from front (right-over-left) round the back to the front
        th = theta
        back = 0.5 - 0.5 * math.cos(th)                           # 0 front .. 1 back
        endk = min(1.0, min(u, 1 - u) / 0.10)                     # taper at the two front ends
        endk = endk * endk * (3 - 2 * endk)
        b = base(th)
        rad = Vector((math.sin(th), -math.cos(th), 0.0))          # horizontal outward direction at this angle
        h = (0.024 + 0.030 * back ** 0.8) * (0.45 + 0.55 * endk)
        w = (0.020 + 0.018 * back) * (0.60 + 0.40 * endk)
        Ld = (0.030 + 0.165 * back ** 1.8) * (0.5 + 0.5 * endk)
        g = 0.007 + 0.016 * back ** 1.2
        layer = 0.006 * (1 if u < 0.5 else -1) * (1 - endk)       # front overlap: one end over the other
        fv = max(0.0, 1.0 - abs((th + math.pi) % (2 * math.pi) - math.pi) / math.radians(62)) ** 1.4
        b = b + Vector((0, -0.012 * fv, -0.085 * fv))             # front ends descend to the crossing point
        for j in range(NV):
            t = j / (NV - 1)
            if t <= 0.36:                                          # roll: inner base -> rim top -> rim outside
                a = t / 0.36
                p = b + rad * (w * (0.5 - 0.5 * math.cos(a * math.pi)) * 1.0 - 0.004) + Vector((0, 0, 1)) * (h * math.sin(a * math.pi * 0.86) + 0.004 * (1 - a))
            else:                                                  # drape down over the shoulders / back
                a = (t - 0.36) / 0.64
                tgt = b + rad * (w + Ld * 0.38 * a) + Vector((0, 0, h * 0.42 - (h * 0.42 + Ld) * a))
                loc, nor, _, d = stree.find_nearest(tgt)
                bulge = math.sin(math.pi * min(1.0, a * 1.02)) ** 0.6
                near = loc + nor * (0.004 + g * bulge)
                blend = float(_smooth(0.0, 0.35, a))
                p = tgt.lerp(near, blend)
            p = p + rad * layer
            grid[(i, j)] = hb.verts.new(p)
    for i in range(NU - 1):
        for j in range(NV - 1):
            f = hb.faces.new([grid[(i, j)], grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]]); f.smooth = True
    hb.normal_update()
    _box_uv(hb, huv, hp.get('uv_scale', 6.5))
    # --- 5. kangaroo pocket: raised panel on the lower front with slanted hand openings
    pk = bmesh.new(); puv = pk.loops.layers.uv.new('UVMap'); pg = {}
    z0 = z_hem + 0.012; z1 = z0 + 0.185; wb = 0.34; wt = 0.20
    nxs, nzs = 23, 12
    for j in range(nzs):
        tz = j / (nzs - 1); z = z0 + (z1 - z0) * tz
        half = 0.5 * (wb if tz < 0.30 else wb + (wt - wb) * ((tz - 0.30) / 0.70) ** 0.85)
        for i in range(nxs):
            x = -half + 2 * half * i / (nxs - 1)
            hit = stree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is None: continue
            edge = j in (0, nzs - 1) or (i in (0, nxs - 1) and tz < 0.30)
            opening = i in (0, nxs - 1) and tz >= 0.30
            n = hit[1] if hit[1].y < 0 else -hit[1]
            pg[(i, j)] = pk.verts.new(hit[0] + n * (0.0015 if edge else (0.013 if opening else 0.009)))
    for i in range(nxs - 1):
        for j in range(nzs - 1):
            q = [pg.get((i, j)), pg.get((i + 1, j)), pg.get((i + 1, j + 1)), pg.get((i, j + 1))]
            if all(v is not None for v in q):
                f = pk.faces.new(q); f.smooth = True
    pk.normal_update()
    if sum(f.normal.y for f in pk.faces) > 0: bmesh.ops.reverse_faces(pk, faces=pk.faces[:])
    _box_uv(pk, puv, hp.get('uv_scale', 6.5))
    # --- 6. drawstrings: two cords from the hood's front edge down the chest
    ds = bmesh.new(); duv = ds.loops.layers.uv.new('UVMap')
    z_cross = base(0.0).z
    for sgn, length in ((1, 0.20), (-1, 0.23)):
        path = []
        for k in range(11):
            t = k / 10
            x = sgn * (0.030 + 0.008 * t + 0.004 * math.sin(t * 5 + sgn))
            z = z_cross + 0.012 - length * t
            hit = stree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is None: continue
            n = hit[1] if hit[1].y < 0 else -hit[1]
            path.append(hit[0] + n * (0.0045 + 0.002 * t))
        r0 = 0.0030; segs = 6; rings = []
        for k, p in enumerate(path):
            tan = (path[min(k + 1, len(path) - 1)] - path[max(k - 1, 0)]).normalized()
            a1 = tan.cross(Vector((0, 1, 0))).normalized(); a2 = tan.cross(a1).normalized()
            r = r0 * (1.9 if k >= len(path) - 2 else 1.0)                       # knotted / tipped end
            rings.append([ds.verts.new(p + (a1 * math.cos(6.283 * q / segs) + a2 * math.sin(6.283 * q / segs)) * r) for q in range(segs)])
        for k in range(len(rings) - 1):
            for q in range(segs):
                f = ds.faces.new([rings[k][q], rings[k][(q + 1) % segs], rings[k + 1][(q + 1) % segs], rings[k + 1][q]]); f.smooth = True
                for l in f.loops: l[duv].uv = (0.5, 0.5)
        ds.faces.new(rings[-1][::-1])
    ds.normal_update()
    # --- objects, weights, materials
    hood_o = _new_obj('stk_hood', 'hood', rig, hb)
    pock_o = _new_obj('stk_pocket', 'pocket', rig, pk)
    rib_o = _new_obj('stk_ribs', 'ribs', rig, rb)
    str_o = _new_obj('stk_strings', 'strings', rig, ds)
    shell = _new_obj('stk_hoodie', 'hoodie', rig, bm)
    tb.free()
    if 'jeans' in R:                                   # the hem band sits over the jeans' waistband
        rc = M.coords(rib_o)
        M.push_outside(rib_o, R['jeans'], margin=0.005, reach=0.04, vmask=np.abs(rc[:, 0]) < 0.25)
    for o in (shell, hood_o, pock_o, rib_o, str_o):
        M.transfer_weights(ref, o, rig)
    M.smooth_weights(shell, 2, 0.5)
    for o in (hood_o, pock_o, str_o):                # ride on the torso cloth, not on the nearest skin
        M.transfer_weights(shell, o, rig)
    shell['stk_hem'] = float(z_hem - hp['hem_band'])
    shell['stk_protect'] = [0.11, float(z_neck - 0.075)]          # keep the skin that shows in the neck opening
    col = np.array(hp['color'], np.float32)
    gz = MT.fabric_noise(512, seed=11)
    bp = MT.save_tex(Image.fromarray(np.clip(col[None, None] * (1.0 + 0.045 * gz[..., None]), 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_hoodie', quality=90)
    npth = MT.save_tex(MT.height_to_normal(gz, 1.6), cfg['name'] + '_hoodie_n', quality=90)
    fleece = MT.make_material(cfg['name'] + '_hoodie', base=bp, roughness=0.92, normal=npth, normal_strength=0.45, double_sided=True)
    rib = (np.sin(np.arange(256) / 256 * 2 * np.pi * 8) * 0.5 + 0.5)[None, :] * np.ones((64, 1), np.float32)
    rimg = col[None, None] * (0.80 + 0.17 * rib[..., None])
    rp = MT.save_tex(Image.fromarray(np.clip(rimg, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_rib', quality=90)
    rn = MT.save_tex(MT.height_to_normal(rib, 6.0), cfg['name'] + '_rib_n', quality=90)
    ribm = MT.make_material(cfg['name'] + '_rib', base=rp, roughness=0.92, normal=rn, normal_strength=1.0, double_sided=True)
    cord = MT.make_material(cfg['name'] + '_cord', color=tuple(float(c) for c in ((col / 255.0) ** 2.2) * 1.12), roughness=0.85)
    for o in (shell, hood_o, pock_o):
        MT.assign(o, fleece); o['stk_custom_mat'] = True
    MT.assign(rib_o, ribm); rib_o['stk_custom_mat'] = True
    MT.assign(str_o, cord); str_o['stk_custom_mat'] = True
    print('hoodie: shell', len(shell.data.polygons), 'hood', len(hood_o.data.polygons), 'ribs', len(rib_o.data.polygons))


def octopus_wordmark(size=1024, body=(124, 96, 201), text_rgb=(60, 42, 132), word='Octopus'):
    """The owner's chest mark as drawn on the character sheet: a round-headed purple octopus with dot eyes and
    curled arms above the word 'Octopus' in a clean sans-serif.  Returns an RGBA image (transparent ground)."""
    S = size * 2
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = body + (255,)
    cx = S * 0.5; hy = S * 0.265; hr = S * 0.185
    d.ellipse([cx - hr, hy - hr, cx + hr, hy + hr * 0.98], fill=c)                       # head
    d.rounded_rectangle([cx - hr * 0.80, hy + hr * 0.25, cx + hr * 0.80, hy + hr * 1.12], radius=hr * 0.3, fill=c)

    def arm(pts, w0, w1):
        n = 40
        P = np.array(pts, np.float64)
        for k in range(n + 1):
            t = k / n                                                                  # quadratic bezier
            p = (1 - t) ** 2 * P[0] + 2 * (1 - t) * t * P[1] + t ** 2 * P[2]
            w = w0 + (w1 - w0) * t
            d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=c)
    by = hy + hr * 0.95; w0 = hr * 0.42
    for sx in (-1, 1):
        arm([(cx + sx * hr * 0.62, by - hr * 0.1), (cx + sx * hr * 1.30, by + hr * 0.25), (cx + sx * hr * 1.22, by + hr * 0.95)], w0, w0 * 0.62)
        arm([(cx + sx * hr * 1.22, by + hr * 0.95), (cx + sx * hr * 1.20, by + hr * 1.18), (cx + sx * hr * 0.98, by + hr * 0.92)], w0 * 0.62, w0 * 0.5)
        arm([(cx + sx * hr * 0.30, by), (cx + sx * hr * 0.50, by + hr * 0.75), (cx + sx * hr * 0.58, by + hr * 1.15)], w0, w0 * 0.60)
        arm([(cx + sx * hr * 0.58, by + hr * 1.15), (cx + sx * hr * 0.62, by + hr * 1.36), (cx + sx * hr * 0.40, by + hr * 1.20)], w0 * 0.60, w0 * 0.48)
    arm([(cx, by), (cx, by + hr * 0.6), (cx, by + hr * 1.02)], w0 * 0.9, w0 * 0.62)
    for sx in (-1, 1):                                                                 # dot eyes
        ex = cx + sx * hr * 0.36; ey = hy + hr * 0.02; r = hr * 0.135
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=(250, 248, 255, 255))
        d.ellipse([ex - r * 0.52 + sx * r * 0.1, ey - r * 0.52, ex + r * 0.52 + sx * r * 0.1, ey + r * 0.52], fill=(28, 22, 40, 255))
    font = None
    for fp in ('/usr/share/fonts/opentype/inter/Inter-Medium.otf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
               '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'):
        if os.path.isfile(fp):
            font = ImageFont.truetype(fp, int(S * 0.165)); break
    if font is None:
        font = ImageFont.load_default()
    tw = d.textlength(word, font=font)
    d.text((cx - tw / 2, S * 0.735), word, font=font, fill=text_rgb + (255,))
    return im.resize((size, size), Image.LANCZOS)


def chest_logo(cfg, R, ref, rig):
    """Octopus + 'Octopus' wordmark as an alpha-cutout decal hugging the chest of the hoodie."""
    o = R['hoodie']; hp = cfg.get('hoodie', {})
    tree, tb = M.bvh_of(o)
    w = hp.get('logo_w', 0.150); h = w
    zc = _bone(rig, 'Neck').head_local.z - hp.get('logo_drop', 0.250)
    n = 11
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = {}
    for i in range(n):
        for j in range(n):
            x = (i / (n - 1) - 0.5) * w; z = zc + (j / (n - 1) - 0.5) * h
            hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is None: continue
            nn = hit[1] if hit[1].y < 0 else -hit[1]
            grid[(i, j)] = bm.verts.new(hit[0] + nn * 0.0030)
    for i in range(n - 1):
        for j in range(n - 1):
            q = [grid.get((i, j)), grid.get((i + 1, j)), grid.get((i + 1, j + 1)), grid.get((i, j + 1))]
            if all(v is not None for v in q):
                f = bm.faces.new(q); f.smooth = True
                for l, (a, b) in zip(f.loops, [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]):
                    l[uvl].uv = (a / (n - 1), b / (n - 1))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    d = _new_obj('stk_logo', 'logo', rig, bm); tb.free()
    M.laplacian_smooth(d, np.ones(len(d.data.vertices)), iters=3, lam=0.4)
    M.transfer_weights(o, d, rig)
    lp = MT.save_tex(octopus_wordmark(1024), cfg['name'] + '_logo', alpha=True)
    m = MT.make_material(cfg['name'] + '_logo', base=lp, roughness=0.8, alpha='MASK', double_sided=False)
    MT.assign(d, m); d['stk_custom_mat'] = True


# ----------------------------------------------------------------------------- boots, jeans, watch
def boots_fit(cfg, R, ref, rig):
    """Turn the biker boots into ankle-high lace-up boots: cut the shaft at ankle height, close the top with a
    padded collar, add crossed laces down the front."""
    o = R['boots']; bp_ = cfg.get('boots', {})
    co = M.coords(o)
    for sgn in (-1, 1):                                  # chunkier last and thicker lug sole
        m = co[:, 0] * sgn > 0
        c = co[m].mean(0); zmin = co[:, 2].min()
        co[m, 0] = c[0] + (co[m, 0] - c[0]) * bp_.get('widen', 1.12)
        co[m, 1] = c[1] + (co[m, 1] - c[1]) * bp_.get('lengthen', 1.06)
        co[m, 2] = zmin + (co[m, 2] - zmin) * bp_.get('heighten', 1.14)
    M.set_coords(o, co)
    z_top = co[:, 2].min() + bp_.get('height', 0.215)
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector((0, 0, z_top)), plane_no=Vector((0, 0, 1)), clear_outer=True)
    uvl = bm.loops.layers.uv.verify()
    lace = bmesh.new(); luv = lace.loops.layers.uv.new('UVMap')
    for lp in _loops(bm):
        c = sum((v.co for v in lp), Vector()) / len(lp)
        if abs(c.z - z_top) > 0.004: continue
        # padded collar: roll the cut edge slightly outwards and back in
        uv_ref = lp[0].link_loops[0][uvl].uv.copy()
        prev = lp
        for k, (dz, dr) in enumerate(((0.006, 0.004), (0.010, 0.0), (0.006, -0.007))):
            ring = []
            for v in lp:
                rad = (v.co - c); rad.z = 0
                ring.append(bm.verts.new(v.co + Vector((0, 0, dz)) + rad.normalized() * dr))
            for i in range(len(lp)):
                j = (i + 1) % len(lp)
                f = bm.faces.new([prev[i], prev[j], ring[j], ring[i]]); f.smooth = True
                for l in f.loops: l[uvl].uv = uv_ref
            prev = ring
        # laces: crossed cords up the front of the shaft (front = -Y), from the instep to the collar
        tree = BVHTree.FromBMesh(bm)
        zs = np.linspace(co[:, 2].min() + 0.075, z_top - 0.012, 7)
        halfw = 0.018

        def onfront(x, z):
            hit = tree.ray_cast(Vector((x, c.y - 0.5, z)), Vector((0, 1, 0)), 1.0)
            if hit[0] is None: return None
            n = hit[1] if hit[1].y < 0 else -hit[1]
            return hit[0] + n * 0.0035

        def cord(a, b, r=0.0030):
            if a is None or b is None: return
            t = (b - a).normalized(); a1 = t.cross(Vector((0, -1, 0))).normalized(); a2 = t.cross(a1).normalized()
            mid = (a + b) / 2 + Vector((0, -0.0015, 0))
            rings = []
            for p in (a, mid, b):
                rings.append([lace.verts.new(p + (a1 * math.cos(6.283 * q / 5) + a2 * math.sin(6.283 * q / 5)) * r) for q in range(5)])
            for k in range(2):
                for q in range(5):
                    f = lace.faces.new([rings[k][q], rings[k][(q + 1) % 5], rings[k + 1][(q + 1) % 5], rings[k + 1][q]]); f.smooth = True
                    for l in f.loops: l[luv].uv = (0.5, 0.5)
        for k in range(len(zs) - 1):
            cord(onfront(c.x - halfw, zs[k]), onfront(c.x + halfw, zs[k + 1]))
            cord(onfront(c.x + halfw, zs[k]), onfront(c.x - halfw, zs[k + 1]))
        cord(onfront(c.x - halfw, zs[-1]), onfront(c.x + halfw, zs[-1]))
    bm.normal_update(); bm.to_mesh(o.data); bm.free(); o.data.update()
    lo = _new_obj('stk_laces', 'laces', rig, lace)
    M.transfer_weights(ref, o, rig)
    M.transfer_weights(o, lo, rig)
    col = bp_.get('lace_color', (150, 116, 84))
    m = MT.make_material(cfg['name'] + '_laces', color=tuple((c_ / 255.0) ** 2.2 for c_ in col), roughness=0.8)
    MT.assign(lo, m); lo['stk_custom_mat'] = True
    o['stk_top'] = float(z_top + 0.01)
    print('boots: top', round(z_top, 3), 'faces', len(o.data.polygons), 'lace faces', len(lo.data.polygons))


def jeans_fit(cfg, R, ref, rig):
    """Jeans end on the boot shaft with a turned-up cuff."""
    o = R['jeans']; boots = R['boots']
    z_cut = boots.get('stk_top', 0.2) - cfg.get('jeans_over_boot', 0.045)
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector((0, 0, z_cut)), plane_no=Vector((0, 0, -1)), clear_outer=True)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    co = M.coords(o)
    slim = cfg.get('jeans_slim', 0.85)                 # slim / straight leg: narrow each leg around its bone axis
    for s_ in ('Left', 'Right'):
        hip = _bone(rig, s_ + 'UpLeg').head_local; knee = _bone(rig, s_ + 'Leg').head_local; ank = _bone(rig, s_ + 'Foot').head_local
        sgn = 1 if s_ == 'Left' else -1
        m = (co[:, 0] * sgn > 0) & (co[:, 2] < hip.z - 0.10)
        zz = co[m, 2]
        axx = np.interp(zz, [ank.z, knee.z, hip.z], [ank.x, knee.x, hip.x]); axy = np.interp(zz, [ank.z, knee.z, hip.z], [ank.y, knee.y, hip.y])
        w = (1 - (1 - slim) * _smooth(hip.z - 0.10, hip.z - 0.22, zz))
        co[m, 0] = axx + (co[m, 0] - axx) * w; co[m, 1] = axy + (co[m, 1] - axy) * w
    M.set_coords(o, co)
    M.push_outside(o, boots, margin=0.006, reach=0.04, vmask=co[:, 2] < z_cut + 0.10)   # legs clear the boot shaft
    cb = bmesh.new(); cuv = cb.loops.layers.uv.new('UVMap')
    co = M.coords(o)
    for sgn in (-1, 1):                 # the jeans mesh has open seams, so build each hem ring by angle instead
        m = (np.abs(co[:, 2] - z_cut) < 0.002) & (co[:, 0] * sgn > 0)
        if m.sum() < 8: continue
        pts = co[m]; c = pts.mean(0)
        ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
        nb = 28; ring = []
        for k in range(nb):
            a0 = -math.pi + 2 * math.pi * k / nb
            d = np.abs((ang - a0 + math.pi) % (2 * math.pi) - math.pi)
            w = np.exp(-(d / 0.18) ** 2)
            r = float((np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1]) * w).sum() / w.sum())
            ring.append(cb.verts.new(Vector((c[0] + r * math.cos(a0), c[1] + r * math.sin(a0), z_cut))))
        _band(cb, cuv, ring, Vector((0, 0, 1)), 0.028, -0.0045, 40, rows=2, bulge=-0.0015)
        bmesh.ops.delete(cb, geom=ring, context='VERTS')
    cb.normal_update()
    cu = _new_obj('stk_cuffs', 'cuffs', rig, cb)
    M.transfer_weights(ref, cu, rig)
    den = MT.fabric_noise(128, seed=4)
    img = np.array(cfg.get('cuff_color', (126, 138, 162)), np.float32)[None, None] * (1 + 0.08 * den[..., None])
    bp = MT.save_tex(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_cuff', quality=88)
    m = MT.make_material(cfg['name'] + '_cuff', base=bp, roughness=0.85, double_sided=True)
    MT.assign(cu, m); cu['stk_custom_mat'] = True


def faded_denim(base_post):
    """Jeans texture: the washed-denim recolour plus lighter wear on the front of the thighs and the knees,
    painted from 3D position so it lands in the right place whatever the UV layout."""
    def post(im, obj=None):
        im = base_post(im, obj)
        size = im.size[0]
        a = np.asarray(im, np.float32) / 255.0
        pos, nrm, valid = bake_uv_maps(obj, size)
        Z = pos[..., 2]; zmax = Z[valid].max(); zmin = Z[valid].min()
        t = (Z - zmin) / max(zmax - zmin, 1e-4)                    # 0 hem .. 1 waist
        front = _smooth(-0.15, -0.75, nrm[..., 1])
        thigh = np.exp(-((t - 0.70) / 0.14) ** 2); knee = np.exp(-((t - 0.44) / 0.07) ** 2)
        seat = _smooth(0.2, 0.8, nrm[..., 1]) * np.exp(-((t - 0.86) / 0.07) ** 2) * 0.5
        wear = np.clip((0.75 * thigh + 0.65 * knee) * front + seat, 0, 1) * valid
        wear = np.asarray(Image.fromarray((wear * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size / 160)), np.float32)[..., None] / 255
        light = np.array([158, 170, 194], np.float32) / 255
        out = a + (light - a) * wear * 0.60
        return Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')
    return post


def smartwatch(cfg, R, ref, rig):
    """Silver smartwatch on the left wrist: light band around the forearm, rounded-square silver case with a
    black glass face on the back of the wrist.  Rigidly skinned to the left forearm."""
    B = lambda n: _bone(rig, n)
    e = B('LeftForeArm').head_local; w = B('LeftHand').head_local
    ax = (w - e).normalized()
    P = w - ax * cfg.get('watch_up', 0.030)
    co = M.coords(ref)
    hw = M.group_weights(ref, [b.name for b in rig.data.bones if b.name.startswith(BP + 'LeftHand')]) > 0.9
    hv = co[hw] - co[hw].mean(0)
    nrm = np.linalg.svd(hv, full_matrices=False)[2][2]                       # palm normal
    up = Vector(nrm); up = (up - ax * up.dot(ax)).normalized()
    if up.z < 0: up = -up                                                    # back of the hand faces up in the rest pose
    side = ax.cross(up).normalized()
    tree, tb = M.bvh_of(ref)

    def surf(d, along=0.0):
        o_ = P + ax * along                              # P lies on the bone axis inside the forearm
        hit = tree.ray_cast(o_, d, 0.08)
        return hit[0] if hit[0] is not None else o_ + d * 0.03
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')

    def quad(vs, mat):
        f = bm.faces.new(vs); f.material_index = mat; f.smooth = (mat == 0)
        for l in f.loops: l[uvl].uv = (0.5, 0.5)
    NS = 20; bw = 0.010; rings = []                                           # band
    for a_ in (-bw, bw):
        ring_i = []; ring_o = []
        for k in range(NS):
            th = 2 * math.pi * k / NS
            d = up * math.cos(th) + side * math.sin(th)
            s0 = surf(d, a_)
            ring_i.append(bm.verts.new(s0 + d * 0.0008)); ring_o.append(bm.verts.new(s0 + d * 0.0034))
        rings.append((ring_i, ring_o))
    for k in range(NS):
        j = (k + 1) % NS
        quad([rings[0][1][k], rings[0][1][j], rings[1][1][j], rings[1][1][k]], 0)
        quad([rings[0][0][k], rings[0][0][j], rings[0][1][j], rings[0][1][k]], 0)
        quad([rings[1][0][j], rings[1][0][k], rings[1][1][k], rings[1][1][j]], 0)
    top0 = surf(up)                                                           # case on the back of the wrist
    L_, W_, H_ = 0.0195, 0.0170, 0.0100

    def outline(scale, h):
        pts = []
        for k in range(16):
            th = 2 * math.pi * (k + 0.5) / 16
            c_, s_ = math.cos(th), math.sin(th)
            x = L_ * scale * (abs(c_) ** 0.42) * (1 if c_ >= 0 else -1)
            y = W_ * scale * (abs(s_) ** 0.42) * (1 if s_ >= 0 else -1)
            pts.append(bm.verts.new(top0 + ax * x + side * y + up * h))
        return pts
    r0 = outline(1.0, 0.0005); r1 = outline(1.0, H_ * 0.8); r2 = outline(0.90, H_); r3 = outline(0.84, H_ + 0.0002)
    for k in range(16):
        j = (k + 1) % 16
        quad([r0[k], r0[j], r1[j], r1[k]], 1); quad([r1[k], r1[j], r2[j], r2[k]], 1); quad([r2[k], r2[j], r3[j], r3[k]], 1)
    f = bm.faces.new(r3); f.material_index = 2
    for l in f.loops: l[uvl].uv = (0.5, 0.5)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median() - P) < 0: f.normal_flip()
    o = _new_obj('stk_watch', 'watch', rig, bm); tb.free()
    vg = o.vertex_groups.new(name=BP + 'LeftForeArm'); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    am = o.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    band = MT.make_material(cfg['name'] + '_watch_band', color=(0.72, 0.72, 0.74), roughness=0.55)
    case = MT.make_material(cfg['name'] + '_watch_case', color=(0.78, 0.78, 0.80), roughness=0.28, metallic=0.9)
    glass = MT.make_material(cfg['name'] + '_watch_glass', color=(0.012, 0.012, 0.016), roughness=0.08)
    o.data.materials.clear()
    for m_ in (band, case, glass): o.data.materials.append(m_)
    o['stk_custom_mat'] = True
    print('watch faces', len(o.data.polygons))
