"""Custom geometry + garment edits: curly hair cap, pullover-style hoodie fix, kangaroo pocket, chest logo."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Vector
from . import common as C, meshops as M, materials as MT

BP = 'mixamorig:'


def _bone(rig, n):
    return rig.data.bones.get(BP + n) or rig.data.bones.get(n)


def _new_obj(name, role, rig):
    me = bpy.data.meshes.new(name); o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o['stk_role'] = role; o.parent = rig
    return o


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------- hair
def hair_cap(cfg, R, ref, rig):
    """Short tightly-curled hair as an opaque shell grown from the scalp of the CC0 base mesh."""
    return scalp_shell(cfg, R, ref, rig, cfg.get('hair_cap', {}), 'hair')


def beanie(cfg, R, ref, rig):
    """Knitted beanie: the same scalp shell, thicker, lower on the forehead, rib-knit material."""
    bc = dict(line_h=[0.775, 0.77, 0.73, 0.66, 0.635, 0.635, 0.54, 0.44, 0.40], edge=0.007, side=0.011, top=0.020,
              noise=0.0, subdiv=1, taper_rings=2, knit=True, color=(190, 150, 50))
    bc.update(cfg.get('beanie', {}))
    return scalp_shell(cfg, R, ref, rig, bc, 'hat')


def scalp_shell(cfg, R, ref, rig, hc, role):
    co = M.coords(ref)
    wH = M.group_weights(ref, [BP + 'Head'])
    head = wH > 0.5
    z_top = co[head, 2].max()
    upper = head & (co[:, 2] > z_top - 0.10)
    y_front, y_back = co[upper, 1].min(), co[upper, 1].max()
    chin = co[head & (co[:, 1] < y_front + 0.05), 2].min()
    H = z_top - chin
    t = np.clip((co[:, 1] - y_front) / (y_back - y_front), 0, 1)
    # hairline height (fraction of head height above chin) along the fore-aft axis
    tp = hc.get('line_t', [0.00, 0.10, 0.22, 0.33, 0.43, 0.62, 0.72, 0.85, 1.00])
    hp = hc.get('line_h', [0.815, 0.80, 0.74, 0.63, 0.60, 0.60, 0.46, 0.34, 0.30])
    line = chin + H * np.interp(t, tp, hp)
    scalp = head & (co[:, 2] > line)
    # ears stick out sideways: never grow hair from them
    half_w = np.abs(co[upper & (np.abs(t - 0.5) < 0.2), 0]).max()
    bm = bmesh.new(); bm.from_mesh(ref.data); bm.verts.ensure_lookup_table()
    keepf = [f for f in bm.faces if all(scalp[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in set(keepf)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # keep the largest connected piece only
    bm.verts.ensure_lookup_table()
    seen = set(); comps = []
    for v in bm.verts:
        if v in seen: continue
        st = [v]; seen.add(v); c = []
        while st:
            x = st.pop(); c.append(x)
            for e in x.link_edges:
                o2 = e.other_vert(x)
                if o2 not in seen: seen.add(o2); st.append(o2)
        comps.append(c)
    comps.sort(key=len, reverse=True)
    for c in comps[1:]:
        bmesh.ops.delete(bm, geom=c, context='VERTS')
    # relax the jagged hairline (boundary verts slide towards their boundary neighbours)
    for _ in range(hc.get('line_relax', 6)):
        newco = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
                if len(nb) == 2:
                    newco[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
        for v, c in newco.items(): v.co = c
    for _ in range(hc.get('subdiv', 2)):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True, smooth=1.0)
    bm.normal_update(); bm.verts.ensure_lookup_table()
    # ring distance from the boundary (for tapering the thickness at the hairline)
    dist = {v: (0 if v.is_boundary else None) for v in bm.verts}
    frontier = [v for v in bm.verts if v.is_boundary]; d = 0
    while frontier:
        d += 1; nxt = []
        for v in frontier:
            for e in v.link_edges:
                o2 = e.other_vert(v)
                if dist[o2] is None: dist[o2] = d; nxt.append(o2)
        frontier = nxt
    rng = np.random.default_rng(hc.get('seed', 3))
    th_edge = hc.get('edge', 0.004); th_side = hc.get('side', 0.014); th_top = hc.get('top', 0.030)
    zc = z_top - 0.33 * H
    for v in bm.verts:
        k = min(dist[v] or 0, hc.get('taper_rings', 7)) / hc.get('taper_rings', 7)
        k = k * k * (3 - 2 * k)
        up = float(np.clip((v.co.z - zc) / (z_top - zc), 0, 1))
        th = th_edge + (th_side - th_edge) * k + (th_top - th_side) * k * up ** 1.5
        th += (rng.uniform(-1, 1) * hc.get('noise', 0.0022)) * k
        v.co += v.normal * th
    o = _new_obj('stk_' + role, role, rig)
    # azimuthal UVs from the crown (no pinch on top); ~1 tile per 17 cm of scalp
    uvl = bm.loops.layers.uv.new('UVMap')
    cx, cy, cz = 0.0, (y_front + y_back) / 2, z_top - 0.5 * (y_back - y_front)
    rad = 0.5 * (y_back - y_front)
    for f in bm.faces:
        f.smooth = True
        for l in f.loops:
            p = l.vert.co; dv = Vector((p.x - cx, p.y - cy, p.z - cz))
            th = dv.angle(Vector((0, 0, 1))) if dv.length > 1e-6 else 0.0
            ph = math.atan2(dv.y, dv.x); r = th * rad / hc.get('tile', 0.15)
            l[uvl].uv = (0.5 + r * math.cos(ph), 0.5 + r * math.sin(ph))
    bm.to_mesh(o.data); bm.free()
    M.transfer_weights(ref, o, rig)
    from PIL import Image
    if hc.get('knit'):
        col = np.array(hc.get('color', (190, 150, 50)), np.float32)
        g = MT.fabric_noise(256, seed=31)
        rib = (np.sin(np.arange(256) / 256 * 2 * np.pi * 16) * 0.5 + 0.5)[None, :] * np.ones((256, 1), np.float32)
        img = col[None, None] * (0.84 + 0.16 * rib[..., None] + 0.05 * g[..., None])
        bp = MT.save_tex(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_' + role, quality=88)
        npth = MT.save_tex(MT.height_to_normal(rib * 0.6 + g * 0.2, 3.0), cfg['name'] + '_' + role + '_n', quality=88)
        m = MT.make_material(cfg['name'] + '_' + role, base=bp, roughness=0.95, normal=npth, normal_strength=0.8)
    else:
        # near-black, rough, with a tight-curl normal map
        h = MT.curls_height(512, seed=7, cell=hc.get('cell', 12))
        npth = MT.save_tex(MT.height_to_normal(h, 5.0), cfg['name'] + '_hair_n', quality=90)
        base = (np.array(hc.get('color', (26, 22, 21)), np.float32)[None, None] * (0.55 + 0.75 * h[..., None]))
        bp = MT.save_tex(Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_hair', quality=88)
        m = MT.make_material(cfg['name'] + '_hair', base=bp, roughness=0.92, normal=npth, normal_strength=1.5,
                             double_sided=False)
    MT.assign(o, m); o['stk_custom_mat'] = True
    # remove the scalp skin under the cap
    body = R['body']
    cov = M.covered_mask(body, [o], max_dist=0.05)
    for _ in range(2):
        nb = cov.copy()
        for e in body.data.edges:
            a, b = e.vertices
            if not cov[a]: nb[b] = False
            if not cov[b]: nb[a] = False
        cov = nb
    fm = np.array([all(cov[v] for v in p.vertices) for p in body.data.polygons], bool)
    M.delete_faces(body, fm)
    return o


# ----------------------------------------------------------------------------- hoodie
def hoodie_pullover(cfg, R, ref, rig):
    """Turn the zip 'hooded sweat jacket' into an oversized pullover: zip closed up to the collarbone,
    bust flattened to the male chest, body loosened and hem lengthened to hip level."""
    hp = cfg.get('hoodie', {}); o = R[hp.get('role', 'hoodie')]
    do_close = hp.get('close', True)          # False: keep it as an open zip jacket (only fit / loosen / lengthen)
    # drop the small zip-puller pieces (everything but the largest connected component)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen = set(); comps = []
    for v in bm.verts:
        if v in seen: continue
        st = [v]; seen.add(v); c = []
        while st:
            x = st.pop(); c.append(x)
            for e in x.link_edges:
                o2 = e.other_vert(x)
                if o2 not in seen: seen.add(o2); st.append(o2)
        comps.append(c)
    comps.sort(key=len, reverse=True)
    for c in comps[1:]:
        bmesh.ops.delete(bm, geom=c, context='VERTS')
    bm.verts.ensure_lookup_table()
    bm.to_mesh(o.data); bm.free(); o.data.update()

    # The front opening is formed by folded lapels (no mesh boundary), so measure it by ray casting
    # from the front: at each height, the x-interval around the centre line where chest/neck skin shows.
    htree, hb = M.bvh_of(o); btree, bb = M.bvh_of(ref)
    z_neck = _bone(rig, 'Neck').head_local.z
    z_close = z_neck - hp.get('close_below_neck', 0.085)       # zip closed up to here (collarbone)
    zs = np.linspace(z_neck - 0.40, z_neck + 0.02, 64)
    xs = np.linspace(0.0, 0.22, 89)
    def covered(x, z):
        hb_ = btree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
        hh = htree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 3.0)
        if hh[0] is None: return False
        if hb_[0] is None: return True
        return hh[0].y < hb_[0].y + 0.004
    gl = np.zeros(len(zs)); gr = np.zeros(len(zs))
    for k, z in enumerate(zs):
        if covered(0.0, z): continue
        for sign, g in ((-1, gl), (1, gr)):
            e = xs[-1]
            for x in xs[1:]:
                if covered(sign * x, z): e = x; break
            g[k] = e
    hb.free(); bb.free()
    open_z = zs[(gl + gr) > 0]
    z_v = open_z.min() if len(open_z) else z_close
    print('hoodie V bottom', round(float(z_v), 3), 'close to', round(float(z_close), 3), 'neck', round(z_neck, 3))
    if do_close:
        co = M.coords(o)
        front = co[:, 1] < hp.get('front_y', 0.0)
        wsum = np.zeros(len(co))
        for sign, g in ((-1, gl), (1, gr)):
            side = (co[:, 0] * sign >= 0) & front & (co[:, 2] > z_v - 0.04) & (co[:, 2] < z_close + 0.06)
            hg = np.interp(co[:, 2], zs, np.minimum(g, 0.12))
            blend = 1 - _smoothstep(z_close - 0.01, z_close + 0.05, co[:, 2])
            d = np.maximum(np.abs(co[:, 0]) - hg, 0)
            w = np.exp(-(d / hp.get('close_falloff', 0.06)) ** 2) * blend
            shift = np.minimum(hg + 0.003, np.abs(co[:, 0]) + 0.003) * w
            co[side, 0] -= sign * shift[side]
            co[side, 1] -= sign * 0.0015 * w[side]            # tiny overlap so the seam is not coplanar
            wsum = np.maximum(wsum, np.where(side, w, 0.0))
        M.set_coords(o, co)
        M.laplacian_smooth(o, np.clip(wsum * 6, 0, 1), iters=hp.get('close_smooth', 8), lam=0.5)
        # seal the inner collar lining (its free boundary loop) against the skin so no gap opens behind the lapels
        bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
        rim = [v for v in bm.verts if v.is_boundary and abs(v.co.x) < 0.14 and z_v - 0.06 < v.co.z < z_neck + 0.03]
        ring1 = {e.other_vert(v) for v in rim for e in v.link_edges} - set(rim)
        btree2, bb2 = M.bvh_of(ref)
        for vs, k in ((rim, 1.0), (ring1, 0.5)):
            for v in vs:
                loc, nor, _, dist = btree2.find_nearest(v.co)
                if loc is not None and dist < 0.06:
                    v.co = v.co.lerp(loc + nor * 0.0025, k)
        bb2.free(); bm.to_mesh(o.data); bm.free(); o.data.update()
    co = M.coords(o)

    # torso mask (not sleeves / hood): by transferred weights of the garment itself
    wt = M.group_weights(o, [BP + n for n in ('Hips', 'Spine', 'Spine1', 'Spine2', 'LeftUpLeg', 'RightUpLeg')])
    warm = M.group_weights(o, [BP + s + n for s in ('Left', 'Right') for n in ('Arm', 'ForeArm', 'Hand')])
    z_collar = z_close
    torso = (wt > 0.5) & (co[:, 2] < z_collar + 0.02)

    # flatten the bust: clamp distance to the body on the front of the chest, then relax
    tree, tb = M.bvh_of(ref)
    co = M.coords(o)
    chest = torso & (co[:, 1] < 0.02) & (co[:, 2] > z_v - 0.28)
    dmax = hp.get('chest_clear', 0.014)
    for i in np.nonzero(chest)[0]:
        p = Vector(co[i]); loc, nor, _, dist = tree.find_nearest(p)
        if loc is None: continue
        sd = (p - loc).dot(nor)
        if sd > dmax:
            wy = float(_smoothstep(0.0, -0.07, co[i, 1]))          # fade out towards the side seam
            co[i] = np.array(p) * (1 - wy) + np.array(loc + nor * (dmax + 0.1 * (sd - dmax))) * wy
    M.set_coords(o, co)
    M.laplacian_smooth(o, chest.astype(float), iters=hp.get('chest_smooth', 8), lam=0.5)

    # drape: below the chest apex the cloth hangs from the forward-most chest line instead of hugging
    co = M.coords(o)
    z_a = _bone(rig, 'Spine2').head_local.z + hp.get('apex_dz', 0.0)
    fr = torso & (co[:, 1] < _bone(rig, 'Spine2').head_local.y - 0.03)
    band = fr & (np.abs(co[:, 2] - z_a) < 0.035)
    xb = np.linspace(-0.26, 0.26, 27); ya = np.full(len(xb), np.nan)
    for k, x in enumerate(xb):
        m = band & (np.abs(co[:, 0] - x) < 0.015)
        if m.any(): ya[k] = co[m, 1].min()
    ok = ~np.isnan(ya)
    if ok.sum() > 4:
        ya = np.interp(xb, xb[ok], ya[ok])
        env = np.array([ya[max(0, k - 3):k + 4].min() for k in range(len(ya))])     # bridge the pec valley
        env = np.convolve(np.pad(env, 2, mode='edge'), np.ones(5) / 5, mode='valid')
        hem_z = co[torso, 2].min()
        m = fr & (co[:, 2] < z_a + 0.03) & (co[:, 2] > hem_z + 0.01)
        yd = np.interp(co[:, 0], xb, env) + hp.get('drape_slope', 0.05) * np.maximum(z_a - co[:, 2], 0)
        w = (1 - _smoothstep(0.13, 0.22, np.abs(co[:, 0]))) * _smoothstep(z_a + 0.03, z_a - 0.02, co[:, 2])
        newy = co[:, 1] + w * (np.minimum(co[:, 1], yd) - co[:, 1])
        co[m, 1] = newy[m]
        M.set_coords(o, co)
        M.laplacian_smooth(o, m.astype(float), iters=2, lam=0.4)

    # fill recesses (the asset's welt side pockets): pull any lower-torso vertex that lies beneath the
    # outer surface up to just under it, so no dark slits remain once the body below is culled
    co = M.coords(o)
    tmask = wt > 0.5
    bmt = bmesh.new(); bmt.from_mesh(o.data); bmt.faces.ensure_lookup_table()
    bmesh.ops.delete(bmt, geom=[f for f in bmt.faces if not all(tmask[v.index] for v in f.verts)], context='FACES')
    bmesh.ops.triangulate(bmt, faces=bmt.faces)
    from mathutils.bvhtree import BVHTree
    ttree = BVHTree.FromBMesh(bmt)
    yc = _bone(rig, 'Spine').head_local.y
    z_hi = _bone(rig, 'Spine2').head_local.z
    nfix = 0
    for i in np.nonzero(tmask & (co[:, 2] < z_hi))[0]:
        x, y, z = co[i]
        r = math.hypot(x, y - yc)
        if r < 0.03: continue
        d = Vector((x / r, (y - yc) / r, 0.0))
        org = Vector((0.0, yc, z)) + d * 1.0
        hit = ttree.ray_cast(org, -d, 1.0)
        if hit[0] is None: continue
        rh = 1.0 - hit[3]
        if rh - r > 0.004:
            rn = rh - 0.002
            co[i, 0] = d.x * rn; co[i, 1] = yc + d.y * rn; nfix += 1
    bmt.free()
    M.set_coords(o, co)
    print('hoodie recess verts filled', nfix)
    M.laplacian_smooth(o, (tmask & (co[:, 2] < z_hi + 0.05)).astype(float), iters=hp.get('torso_smooth', 5), lam=0.5)

    # loosen (oversized) + lengthen the hem
    co = M.coords(o)
    nrm = np.array([v.normal[:] for v in o.data.vertices])
    loosen = hp.get('loosen', 0.004)
    body_w = np.clip(wt + warm, 0, 1) * (1 - _smoothstep(z_collar - 0.02, z_collar + 0.04, co[:, 2]))
    # keep the cuffs snug
    cuff = _smoothstep(0.0, 0.08, np.abs(co[:, 0]) - (np.abs(co[:, 0]).max() - 0.10))
    co += nrm * (loosen * body_w * (1 - 0.8 * cuff))[:, None]
    z_w = _bone(rig, 'Spine1').head_local.z
    hem_now = co[torso, 2].min()
    hem_to = _bone(rig, 'LeftUpLeg').head_local.z - hp.get('hem_below_hip', 0.05)
    if hp.get('keep_hem'):
        hem_to = hem_now
    k = max(1.0, (z_w - hem_to) / (z_w - hem_now))
    low = co[:, 2] < z_w
    co[low & torso, 2] = z_w - (z_w - co[low & torso, 2]) * k
    M.set_coords(o, co)
    # the stretched hem must clear the trousers and the body
    for inner in [R.get('jeans'), R.get('trousers'), R.get('pants'), ref]:
        if inner is not None:
            M.push_outside(o, inner, margin=hp.get('hem_clear', 0.012), reach=0.05, vmask=low & torso)
    M.push_outside(o, ref, margin=0.006, reach=0.05)
    M.laplacian_smooth(o, (low & torso).astype(float), iters=3, lam=0.4)
    tb.free()
    M.transfer_weights(ref, o, rig)
    M.smooth_weights(o, 2, 0.5)
    o['stk_zv'] = float(z_close)
    if do_close:
        o['stk_protect'] = [0.10, float(z_close) - 0.05]      # keep neck-root / sternum skin under the collar
    o['stk_hem'] = float(hem_to)


def _project_patch(target_tree, xs, zs, y_from, offset, edge_offset=None, mask_fn=None):
    """Grid in the XZ plane projected (ray along +Y) onto the garment front. Returns bmesh."""
    bm = bmesh.new(); grid = {}
    nx, nz = len(xs), len(zs)
    for i, x in enumerate(xs):
        for j, z in enumerate(zs):
            if mask_fn and not mask_fn(i, j, x, z): continue
            hit = target_tree.ray_cast(Vector((x, y_from, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is None: continue
            edge = i in (0, nx - 1) or j in (0, nz - 1)
            off = edge_offset if (edge and edge_offset is not None) else offset
            grid[(i, j)] = bm.verts.new(hit[0] + hit[1] * off)
    for i in range(nx - 1):
        for j in range(nz - 1):
            q = [grid.get((i, j)), grid.get((i + 1, j)), grid.get((i + 1, j + 1)), grid.get((i, j + 1))]
            if all(v is not None for v in q):
                f = bm.faces.new(q); f.smooth = True
    return bm, grid


def kangaroo_pocket(cfg, R, ref, rig):
    o = R['hoodie']; hp = cfg.get('hoodie', {})
    tree, tb = M.bvh_of(o)
    co = M.coords(o)
    wt = M.group_weights(o, [BP + n for n in ('Hips', 'Spine', 'Spine1', 'Spine2')])
    hem = co[wt > 0.5, 2].min()
    z0 = hem + hp.get('pocket_bottom', 0.055); z1 = z0 + hp.get('pocket_h', 0.17)
    wb = hp.get('pocket_w', 0.30); wtp = wb * 0.62
    nxs, nzs = 21, 11
    zs = np.linspace(z0, z1, nzs)
    bm = bmesh.new(); grid = {}
    uvl = bm.loops.layers.uv.new('UVMap')
    for j, z in enumerate(zs):
        tz = j / (nzs - 1)
        # trapezoid with slanted hand openings in the upper 60 %
        half = 0.5 * (wb if tz < 0.38 else wb + (wtp - wb) * (tz - 0.38) / 0.62)
        for i in range(nxs):
            x = -half + 2 * half * i / (nxs - 1)
            hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is None: continue
            edge = (j in (0, nzs - 1)) or (i in (0, nxs - 1) and tz < 0.38)
            opening = (i in (0, nxs - 1)) and tz >= 0.38
            off = 0.0015 if edge else (0.011 if opening else 0.008)
            n = hit[1] if hit[1].y < 0 else -hit[1]
            grid[(i, j)] = bm.verts.new(hit[0] + n * off)
    for i in range(nxs - 1):
        for j in range(nzs - 1):
            q = [grid.get((i, j)), grid.get((i + 1, j)), grid.get((i + 1, j + 1)), grid.get((i, j + 1))]
            if all(v is not None for v in q):
                f = bm.faces.new(q); f.smooth = True
                for l in f.loops:
                    l[uvl].uv = (l.vert.co.x * 2.2 + 0.5, l.vert.co.z * 2.2)
    bm.normal_update()
    # make sure the front faces outwards (-Y)
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    p = _new_obj('stk_pocket', 'pocket', rig)
    bm.to_mesh(p.data); bm.free(); tb.free()
    M.transfer_weights(o, p, rig)
    p['stk_share_mat'] = 'hoodie'
    return p


def chest_logo(cfg, R, ref, rig):
    """Small original octopus mark as an alpha-cutout decal hugging the chest."""
    o = R['hoodie']; hp = cfg.get('hoodie', {})
    tree, tb = M.bvh_of(o)
    size = hp.get('logo_size', 0.085)
    zc = o.get('stk_zv', _bone(rig, 'Spine2').tail_local.z) - hp.get('logo_drop', 0.15)
    xc = hp.get('logo_x', 0.0)
    n = 9
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); grid = {}
    for i in range(n):
        for j in range(n):
            x = xc + (i / (n - 1) - 0.5) * size; z = zc + (j / (n - 1) - 0.5) * size
            hit = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 2.0)
            if hit[0] is None: continue
            nn = hit[1] if hit[1].y < 0 else -hit[1]
            grid[(i, j)] = bm.verts.new(hit[0] + nn * 0.0028)
    for i in range(n - 1):
        for j in range(n - 1):
            q = [grid.get((i, j)), grid.get((i + 1, j)), grid.get((i + 1, j + 1)), grid.get((i, j + 1))]
            if all(v is not None for v in q):
                f = bm.faces.new(q); f.smooth = True
                uv = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                for l, (a, b) in zip(f.loops, uv):
                    l[uvl].uv = (a / (n - 1), b / (n - 1))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    d = _new_obj('stk_logo', 'logo', rig)
    bm.to_mesh(d.data); bm.free(); tb.free()
    # smooth the decal so it does not inherit every wrinkle of the cloth
    M.laplacian_smooth(d, np.ones(len(d.data.vertices)), iters=2, lam=0.4)
    M.transfer_weights(o, d, rig)
    lp = MT.save_tex(MT.octopus_logo(512, color=tuple(hp.get('logo_color', (104, 72, 160)))), cfg['name'] + '_logo', alpha=True)
    m = MT.make_material(cfg['name'] + '_logo', base=lp, roughness=0.8, alpha='MASK', double_sided=False)
    MT.assign(d, m); d['stk_custom_mat'] = True
    return d


def fleece_material(cfg, R, ref, rig):
    """Uniform tileable heavy-fleece texture for the hoodie (+pocket), replacing the asset's zip texture."""
    from PIL import Image
    hp = cfg.get('hoodie', {})
    col = np.array(hp.get('color', (155, 135, 184)), np.float32)
    g = MT.fabric_noise(512, seed=11)
    img = col[None, None] * (1.0 + hp.get('grain', 0.05) * g[..., None])
    bp = MT.save_tex(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_hoodie', quality=90)
    npth = MT.save_tex(MT.height_to_normal(g, 1.6), cfg['name'] + '_hoodie_n', quality=90)
    m = MT.make_material(cfg['name'] + '_hoodie', base=bp, roughness=0.93, normal=npth, normal_strength=0.4,
                         double_sided=True)
    for role in ('hoodie', 'pocket'):
        o = R.get(role) or next((x for x in bpy.data.objects if x.get('stk_role') == role), None)
        if o is None: continue
        if role == 'hoodie':
            # re-tile the asset UVs so the grain is ~constant density
            uv = o.data.uv_layers.active
            a = np.empty(len(uv.data) * 2, np.float32); uv.data.foreach_get('uv', a)
            uv.data.foreach_set('uv', a * hp.get('uv_tile', 4.0))
        MT.assign(o, m); o['stk_custom_mat'] = True


def dark_brown_eyes(im, obj=None):
    """Darken the red-brown MakeHuman iris to a deep brown, keep the sclera."""
    from PIL import Image
    a = np.asarray(im.convert('RGB'), np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    iris = np.clip((r - 1.25 * g) / 40.0, 0, 1)[..., None]
    dark = a * np.array([0.42, 0.50, 0.45], np.float32)
    out = a * (1 - iris) + dark * iris
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def washed_denim(dark=(52, 78, 120), light=(112, 142, 184), stitch=(196, 160, 104)):
    """Recolour a dark jeans texture to washed mid-blue; keep stitching (as tan thread) and leather/metal trims."""
    def post(im, obj=None):
        from PIL import Image
        a = np.asarray(im.convert('RGB'), np.float32)
        lum = (a @ np.array([0.299, 0.587, 0.114], np.float32)) / 255.0
        sat = (a.max(-1) - a.min(-1)) / 255.0
        h, w = lum.shape
        g = MT.fabric_noise(max(h, w), seed=5)[:h, :w]
        lo = Image.fromarray(((MT.fabric_noise(256, seed=9) * 0.5 + 0.5) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        wash = np.asarray(lo, np.float32) / 255.0
        t = np.clip(0.38 + 0.9 * (lum - 0.12) / 0.1 * 0.25 + 0.32 * (wash - 0.5) + 0.10 * g, 0, 1)[..., None]
        den = np.array(dark, np.float32) + (np.array(light, np.float32) - np.array(dark, np.float32)) * t
        is_denim = (np.clip((0.26 - lum) / 0.05, 0, 1) * np.clip((0.22 - sat) / 0.05, 0, 1))[..., None]
        is_stitch = (np.clip((lum - 0.30) / 0.1, 0, 1) * np.clip((0.12 - sat) / 0.04, 0, 1))[..., None]
        out = a * (1 - is_denim) + den * is_denim
        out = out * (1 - is_stitch) + np.array(stitch, np.float32) * is_stitch
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')
    return post


# ----------------------------------------------------------------------------- pedestrians
def scarf(cfg, R, ref, rig):
    """Loop scarf: a thick, slightly irregular ring around the neck (original geometry)."""
    sp = cfg.get('scarf', {})
    neck = _bone(rig, 'Neck'); head = _bone(rig, 'Head')
    co = M.coords(ref)
    zc = neck.head_local.z + sp.get('dz', 0.012)
    ring = np.abs(co[:, 2] - zc) < 0.02
    ring &= np.abs(co[:, 0]) < 0.12
    cx = 0.0; cy = (co[ring, 1].min() + co[ring, 1].max()) / 2
    rx = np.abs(co[ring, 0]).max() + sp.get('gap', 0.004); ry = (co[ring, 1].max() - co[ring, 1].min()) / 2 + sp.get('gap', 0.004)
    tube = sp.get('tube', 0.024)
    nu, nv = 28, 10
    rng = np.random.default_rng(sp.get('seed', 4))
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); vs = {}
    for i in range(nu):
        a = 2 * math.pi * i / nu
        ca, sa = math.cos(a), math.sin(a)
        # centre line: lower at the front (-Y), tube fatter at the front
        front = max(0.0, -sa)
        c = Vector((cx + (rx + tube * 0.55) * ca, cy + (ry + tube * 0.55) * sa - 0.010 * front, zc - 0.035 * front + 0.012 * max(0.0, sa)))
        tr = tube * (1.0 + 0.25 * front) * (1 + 0.08 * rng.uniform(-1, 1))
        radial = Vector((ca, sa, 0))
        for j in range(nv):
            b = 2 * math.pi * j / nv
            p = c + radial * (tr * 0.85 * math.cos(b)) + Vector((0, 0, 1)) * (tr * 1.3 * math.sin(b))
            vs[(i, j)] = bm.verts.new(p)
    for i in range(nu):
        for j in range(nv):
            q = [vs[(i, j)], vs[((i + 1) % nu, j)], vs[((i + 1) % nu, (j + 1) % nv)], vs[(i, (j + 1) % nv)]]
            f = bm.faces.new(q); f.smooth = True
            uv = [(i / nu, j / nv), ((i + 1) / nu, j / nv), ((i + 1) / nu, (j + 1) / nv), (i / nu, (j + 1) / nv)]
            for l, (u, v) in zip(f.loops, uv):
                l[uvl].uv = (u * 6, v * 2)
    bm.normal_update()
    if sum(f.normal.dot(f.calc_center_median() - Vector((cx, cy, zc))) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    o = _new_obj('stk_scarf', 'scarf', rig)
    bm.to_mesh(o.data); bm.free()
    M.transfer_weights(ref, o, rig)
    # a scarf sits on the shoulders: damp head influence
    from PIL import Image
    col = np.array(sp.get('color', (140, 40, 44)), np.float32)
    g = MT.fabric_noise(256, seed=21)
    rib = (np.sin(np.arange(256) / 256 * 2 * np.pi * 24) * 0.5 + 0.5)[None, :] * np.ones((256, 1))
    img = col[None, None] * (0.86 + 0.14 * rib[..., None] + 0.06 * g[..., None])
    bp = MT.save_tex(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB'), cfg['name'] + '_scarf', quality=88)
    npth = MT.save_tex(MT.height_to_normal(rib.astype(np.float32) * 0.6 + g * 0.2, 3.0), cfg['name'] + '_scarf_n', quality=88)
    m = MT.make_material(cfg['name'] + '_scarf', base=bp, roughness=0.95, normal=npth, normal_strength=0.8)
    MT.assign(o, m); o['stk_custom_mat'] = True
    return o


def tint(dark, light, gamma=1.0):
    """Material post-process: luminance remap onto a colour ramp, keeping alpha."""
    def post(im, obj=None):
        rgb = MT.tint_by_luma(im, dark, light, gamma=gamma)
        if im.mode == 'RGBA':
            rgb.putalpha(im.getchannel('A'))
        return rgb
    return post


def grey_hair(amount=0.8, value=1.25):
    def post(im, obj=None):
        from PIL import Image
        a = np.asarray(im.convert('RGBA'), np.float32)
        lum = a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
        g = np.clip(lum * value + 40, 0, 255)[..., None]
        a[..., :3] = a[..., :3] * (1 - amount) + g * amount
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    return post


def reweight(*role_names):
    """Hook factory: replace a garment's interpolated skin weights by weights copied from the body surface."""
    def hook(cfg, R, ref, rig):
        for r in role_names:
            if r in R:
                M.transfer_weights(ref, R[r], rig)
    return hook


# ----------------------------------------------------------------------------- colour-region tools
def _hsv(a):
    """a: float RGB 0..1 (H,W,3) -> h,s,v arrays."""
    mx = a.max(-1); mn = a.min(-1); d = mx - mn
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-6
    hr = ((g - b) / np.where(m, d, 1)) % 6; hg = (b - r) / np.where(m, d, 1) + 2; hb = (r - g) / np.where(m, d, 1) + 4
    h = np.where(mx == r, hr, np.where(mx == g, hg, hb)) / 6.0
    h = np.where(m, h % 1.0, 0.0)
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


SELECT = {
    'blue': lambda h, s, v: (h > 0.50) & (h < 0.74) & (s > 0.22) & (v > 0.08),
    'red': lambda h, s, v: ((h > 0.88) | (h < 0.06)) & (s > 0.30) & (v > 0.10),
    'magenta': lambda h, s, v: (h > 0.74) & (h < 0.96) & (s > 0.22) & (v > 0.10),
    'green_grey': lambda h, s, v: (h > 0.15) & (h < 0.50) & (s > 0.03) & (s < 0.55) & (v > 0.06),
    'dark': lambda h, s, v: (v < 0.55) & (s < 0.45) & (v > 0.02),
    'denim': lambda h, s, v: (h > 0.50) & (h < 0.74) & (s > 0.04) & (v > 0.08),      # incl. faded, pale-blue wear
    'all': lambda h, s, v: v >= 0.0,
}


def recolor(*rules):
    """Material post-process: each rule (selector, dark_rgb, light_rgb) remaps the luminance of the selected
    texture region (by hue / saturation) onto a new colour ramp. Unselected pixels are untouched."""
    def post(im, obj=None):
        from PIL import Image, ImageFilter
        src = im.convert('RGBA')
        a = np.asarray(src, np.float32)[..., :3] / 255.0
        h, s, v = _hsv(a)
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        out = a.copy()
        for sel, dark, light in rules:
            m = SELECT[sel](h, s, v)
            if not m.any():
                continue
            lo, hi = np.percentile(lum[m], 3), np.percentile(lum[m], 97)
            t = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)[..., None]
            ramp = np.array(dark, np.float32) / 255 + (np.array(light, np.float32) - np.array(dark, np.float32)) / 255 * t
            mf = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., None] / 255
            out = out * (1 - mf) + ramp * mf
        res = Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), 'RGB')
        if im.mode == 'RGBA':
            res.putalpha(src.getchannel('A'))
        return res
    return post


def trim_fringe(cfg, R, ref, rig):
    """Hair assets with a long side-swept fringe hide an eye: pull any hair hanging in front of the face up to
    just above the brow line (the fringe becomes a short one)."""
    if 'hair' not in R or 'eyes' not in R:
        return
    ec = M.coords(R['eyes']); o = R['hair']; co = M.coords(o)
    z_lim = ec[:, 2].max() + cfg.get('fringe_above_eye', 0.022)
    y_front = ec[:, 1].min()
    half = np.abs(ec[:, 0]).max() + 0.02
    m = (np.abs(co[:, 0]) < half) & (co[:, 1] < y_front + 0.035) & (co[:, 2] < z_lim)
    co[m, 2] = z_lim - 0.08 * (z_lim - co[m, 2])
    M.set_coords(o, co)
    print('fringe verts lifted', int(m.sum()))
