"""Stage B: turn the MPFB assembly into a clean game mesh (culled, textured, scaled, bones renamed)."""
import os, math
import numpy as np
import bpy, bmesh
from mathutils import Vector
from PIL import Image
from . import common as C, meshops as M, materials as MT

PROTECT_BONES_PREFIX = ('mixamorig:Head', 'mixamorig:Neck', 'mixamorig:LeftHand', 'mixamorig:RightHand')


def roles():
    return {o['stk_role']: o for o in bpy.data.objects if o.type == 'MESH' and 'stk_role' in o}


def build_materials(cfg):
    R = roles(); name = cfg['name']; recipes = cfg.get('mat', {})
    for role, o in R.items():
        if o.get('stk_custom_mat'):
            continue
        rc = dict(recipes.get(role, {}))
        mh = MT.parse_mhmat(o.get('stk_mhmat', ''))
        base = mh.get('diffuseTexture'); nrm = mh.get('normalmapTexture')
        size = rc.get('size', 1024)
        alpha = rc.get('alpha')
        if role in ('eyebrows', 'eyelashes') and alpha is None:
            alpha = 'BLEND'
        if role == 'hair' and alpha is None:
            alpha = 'MASK'
        bp = npth = None
        if base and os.path.isfile(base):
            im = MT.load_fit(base, size)
            if rc.get('drop_alpha'):
                im = im.convert('RGB')
            if 'tint' in rc:
                rgb = MT.tint_by_luma(im, rc['tint'][0], rc['tint'][1], gamma=rc.get('gamma', 1.0),
                                      lo=rc.get('lo'), hi=rc.get('hi'))
                if alpha:
                    rgb.putalpha(im.convert('RGBA').getchannel('A'))
                im = rgb
            if 'mul' in rc:
                a = np.asarray(im.convert('RGBA'), np.float32); a[..., :3] *= np.array(rc['mul'], np.float32)
                im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
            if 'post' in rc:
                im = rc['post'](im, o)
            if not alpha and im.mode == 'RGBA':
                bg = Image.new('RGB', im.size, rc.get('bg', (255, 255, 255))); bg.paste(im, mask=im.getchannel('A')); im = bg
            bp = MT.save_tex(im, f'{name}_{role}', alpha=bool(alpha), quality=rc.get('quality', 86))
        if nrm and os.path.isfile(nrm) and rc.get('normal', True):
            ni = MT.load_fit(nrm, rc.get('normal_size', 1024)).convert('RGB')
            npth = MT.save_tex(ni, f'{name}_{role}_n', quality=88)
        col = rc.get('color', mh.get('diffuseColor', (0.8, 0.8, 0.8)) if not bp else (1, 1, 1))
        m = MT.make_material(f'{name}_{role}', base=bp, color=col, roughness=rc.get('rough', 0.8), normal=npth,
                             normal_strength=rc.get('normal_strength', 1.0), alpha=alpha, emissive=rc.get('emissive', 0.0),
                             rough_tex=o.get('stk_rough_tex'),
                             double_sided=rc.get('double_sided', role not in ('body', 'eyes')))
        MT.assign(o, m)


def finalize(cfg, in_blend=None, out_blend=None):
    if in_blend:
        bpy.ops.wm.open_mainfile(filepath=in_blend); C.enable_mpfb(); C.quiet_mpfb()
    HumanService, TargetService, ObjectService, RigService = C.services()
    R = roles(); body = R['body']; rig = bpy.data.objects['Armature']

    # 1. bake morph targets, drop modifiers other than the armature
    if body.data.shape_keys:
        TargetService.bake_targets(body)
    for o in R.values():
        for m in list(o.modifiers):
            if m.type in ('SUBSURF',):
                o.modifiers.remove(m)
    M.strip_body_helpers(body)
    height_raw = M.coords(body)[:, 2].max()

    # full-body copy (before any skin is removed) as surface / skin-weight source for edited and authored garments
    C.activate(body); bpy.ops.object.duplicate()
    ref = bpy.context.active_object; ref.name = 'stk_weight_ref'; del ref['stk_role']
    for m in list(ref.modifiers): ref.modifiers.remove(m)
    M.apply_delete_groups(body)

    # 2. garment edits / custom geometry (hair cap, hood, pocket, logo ...)
    for hook in cfg.get('hooks', []):
        hook(cfg, roles(), ref, rig)
    R = roles(); body = R['body']

    # outer garments that sit too tight over an inner layer are pushed out to clear it
    for outer, inner, margin in cfg.get('push', []):
        if outer in R and inner in R:
            print('push', outer, 'over', inner, M.push_outside(R[outer], R[inner], margin=margin, reach=0.035))
    # trousers tucked into tall boots: drop trouser faces below the boot top
    for inner, outer, margin in cfg.get('trim_below', []):
        if inner in R and outer in R:
            lim = M.coords(R[outer])[:, 2].max() - margin; zc = M.coords(R[inner])[:, 2]
            fm = np.array([all(zc[v] < lim for v in p.vertices) for p in R[inner].data.polygons], bool)
            M.delete_faces(R[inner], fm); print('trim', inner, int(fm.sum()))

    # 3. cull geometry hidden under clothes
    order = cfg.get('layers', [])          # outermost first, e.g. ['hoodie','jeans','shoes','tee']
    cloth = [R[r] for r in order if r in R]
    prot = M.group_weights(body, [b.name for b in rig.data.bones if b.name.startswith(PROTECT_BONES_PREFIX)]) > 0.3
    for o in R.values():                      # garments may ask to keep the skin around an opening
        if 'stk_protect' in o:
            xh, zlo = o['stk_protect']; bc = M.coords(body)
            prot |= (np.abs(bc[:, 0]) < xh) & (bc[:, 2] > zlo)
    if cloth:
        n = M.cull_hidden(body, cloth, protect=prot, max_dist=cfg.get('cull_dist', 0.12))
        print('culled body faces', n, 'left', len(body.data.polygons))
    for i, r in enumerate(order):
        if r in R and i > 0 and r not in cfg.get('no_cull', ()):
            outer = [R[x] for x in order[:i] if x in R]
            n = M.cull_hidden(R[r], outer, max_dist=cfg.get('cull_dist_cloth', 0.05), rings=cfg.get('cull_rings', {}).get(r, 2))
            print('culled', r, n)

    # garments tucked under a longer outer layer: drop everything above the outer hem (+margin)
    for inner, outer, margin in cfg.get('tuck', []):
        if inner in R and outer in R and 'stk_hem' in R[outer]:
            zc = M.coords(R[inner])[:, 2]; lim = R[outer]['stk_hem'] + margin
            fm = np.array([all(zc[v] > lim for v in p.vertices) for p in R[inner].data.polygons], bool)
            M.delete_faces(R[inner], fm); print('tuck', inner, int(fm.sum()))

    # optional polygon reduction of dense garments (keeps UVs and skin weights)
    for role, ratio in cfg.get('decimate', {}).items():
        if role in R:
            o = R[role]; before = len(o.data.polygons)
            C.activate(o)
            md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = ratio; md.use_collapse_triangulate = False
            bpy.ops.object.modifier_apply(modifier=md.name)
            print('decimate', role, before, '->', len(o.data.polygons))

    # 4. materials
    build_materials(cfg)

    for r in cfg.get('drop_roles', ()):          # helper proxies only needed while painting textures
        if r in roles():
            bpy.data.objects.remove(roles()[r], do_unlink=True)

    # 5. clean vertex groups, weights
    for o in roles().values():
        M.keep_only_bone_groups(o, rig)
        M.limit_normalize(o, 4)
        if not o.get('stk_keep_flat'):
            for p in o.data.polygons: p.use_smooth = True
    bpy.data.objects.remove(ref, do_unlink=True)

    # 6. scale to target height (top of skull), apply transforms
    s = cfg.get('height', 1.82) / height_raw
    rig.scale = (s, s, s)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig] + list(roles().values()):
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in roles().values():                   # morph-target deltas are plain attributes: scale them too
        for at in o.data.attributes:
            if at.name.startswith('mt_'):
                a = np.empty(len(o.data.vertices) * 3, np.float32); at.data.foreach_get('vector', a)
                at.data.foreach_set('vector', a * s)
    # soles on the ground plane: lift everything so the lowest vertex (shoe sole) sits at z = 0
    zmin = min(M.coords(o)[:, 2].min() for o in roles().values())
    rig.location.z -= zmin                      # meshes are children of the rig and follow it
    bpy.context.view_layer.update()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    zchk = min(M.coords(o)[:, 2].min() for o in roles().values())
    assert abs(zchk) < 1e-4 and abs(rig.location.z) < 1e-6, ('grounding failed', zchk)
    print('height raw', round(height_raw, 4), 'scale', round(s, 4), 'lifted', round(-zmin, 4))

    # 7. bone names: strip the mixamorig: prefix
    for b in rig.data.bones:
        b.name = b.name.replace('mixamorig:', '')
    rig.name = cfg['name'] + '_Armature'; rig.data.name = cfg['name'] + '_Skeleton'
    rig['stk_name'] = cfg['name']
    if out_blend:
        bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    return rig
