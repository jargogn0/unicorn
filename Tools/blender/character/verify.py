"""Verification: load an exported GLB into a fresh scene, measure it, and render check images (Cycles CPU).

Usage: python3 verify.py <file.glb> <out_dir> [prefix] [--quick | --minimal] [--norender]
(--quick: turnaround + walk + run sheets; --minimal: turnaround + walk only; sheets are saved as JPEG)
"""
import sys, os, json, math
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from character import render_util as RU  # noqa: E402


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
    for o in bpy.data.objects:
        if o.type == 'MESH' and o not in meshes:
            o.hide_render = True
    return arm, meshes


def set_clip(arm, name, frame):
    ad = arm.animation_data or arm.animation_data_create()
    for t in ad.nla_tracks:
        t.mute = True
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    if name is None:
        ad.action = None
    else:
        act = next(a for a in bpy.data.actions if a.name == name or a.name.startswith(name + '_'))
        ad.action = act
        try:
            if getattr(ad, 'action_slot', None) is None and len(act.slots):
                ad.action_slot = act.slots[0]
        except Exception:
            pass
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def bbox(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        mw = np.array(ev.matrix_world)
        w = co @ mw[:3, :3].T + mw[:3, 3]
        lo = np.minimum(lo, w.min(0)); hi = np.maximum(hi, w.max(0))
        ev.to_mesh_clear()
    return lo, hi


def measure(path):
    arm, meshes = load(path)
    set_clip(arm, None, 0)
    lo, hi = bbox(meshes)
    info = dict(file=os.path.basename(path), bytes=os.path.getsize(path),
                bbox_min=[round(float(x), 4) for x in lo], bbox_max=[round(float(x), 4) for x in hi],
                height_incl_hair=round(float(hi[2] - lo[2]), 4), bones=len(arm.data.bones),
                bone_names=[b.name for b in arm.data.bones],
                tris=sum(sum(len(p.vertices) - 2 for p in m.data.polygons) for m in meshes),
                clips={})
    for a in bpy.data.actions:
        f0, f1 = a.frame_range
        set_clip(arm, a.name, int(f0)); p0 = [pb.matrix.copy() for pb in arm.pose.bones]
        lo0, _ = bbox(meshes)
        set_clip(arm, a.name, int(f1)); p1 = [pb.matrix.copy() for pb in arm.pose.bones]
        diff = max((m0.to_quaternion().rotation_difference(m1.to_quaternion()).angle for m0, m1 in zip(p0, p1)))
        dpos = max(((m0.translation - m1.translation).length for m0, m1 in zip(p0, p1)))
        zmin = []
        for f in range(int(f0), int(f1) + 1):
            set_clip(arm, a.name, f); l, h = bbox(meshes); zmin.append(float(l[2]))
        info['clips'][a.name] = dict(frames=int(f1 - f0) + 1, seconds=round((f1 - f0) / 30.0, 3),
                                     loop_rot_err_deg=round(math.degrees(diff), 3), loop_pos_err_m=round(dpos, 5),
                                     mesh_min_z_range=[round(min(zmin), 4), round(max(zmin), 4)])
    return arm, meshes, info


def _to_jpeg(png, max_w=1200, quality=80):
    """QA sheets are stored as small JPEGs (docs/character_renders)."""
    from PIL import Image
    im = Image.open(png).convert('RGB')
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(os.path.splitext(png)[0] + '.jpg', quality=quality, optimize=True)
    os.remove(png)


def renders(arm, meshes, out_dir, prefix, quick=False, height=1.82, minimal=False):
    os.makedirs(out_dir, exist_ok=True)
    # glTF importer leaves materials' alpha settings; make hair/brows cut-outs render sensibly in Cycles
    RU.setup_render((560, 860), 24 if quick else 40)
    tgt = (0, 0, height * 0.52)
    ps = []
    set_clip(arm, None, 0)
    for i, (az, lab) in enumerate([(0, 'front'), (90, 'side'), (180, 'back')] + ([] if quick else [(40, 'threequarter')])):
        p = os.path.join(out_dir, f'{prefix}_rest_{lab}.png'); RU.shot(p, az, target=tgt, dist=5.0, lens=70); ps.append(p)
    RU.montage(ps, os.path.join(out_dir, f'{prefix}_turnaround.png'))
    _to_jpeg(os.path.join(out_dir, f'{prefix}_turnaround.png'))
    for p in ps: os.remove(p)
    sheets = [('Walk', [0, 10, 20])] + ([] if minimal else [('Run', [0, 7, 14])])
    if not quick:
        sheets += [('Idle', [0, 38]), ('Talk', [30, 60, 110]), ('Interact', [10, 18, 30])]
    names = {a.name for a in bpy.data.actions}
    for clip, frs in sheets:
        if clip not in names: continue
        ps = []
        for f in frs:
            set_clip(arm, clip, f)
            p = os.path.join(out_dir, f'{prefix}_{clip}_{f:03d}.png')
            RU.shot(p, 38, target=tgt, dist=4.7, lens=60); ps.append(p)
        RU.montage(ps, os.path.join(out_dir, f'{prefix}_{clip.lower()}.png'))
        _to_jpeg(os.path.join(out_dir, f'{prefix}_{clip.lower()}.png'))
        for p in ps: os.remove(p)
    if not quick:
        set_clip(arm, 'Idle' if 'Idle' in names else None, 0)
        RU.setup_render((760, 760), 48)
        ps = []
        for az, lab in [(0, 'f'), (55, 'q')]:
            p = os.path.join(out_dir, f'{prefix}_face_{lab}.png')
            RU.shot(p, az, target=(0, 0, height * 0.915), dist=1.55, lens=85, elev_deg=2); ps.append(p)
        RU.montage(ps, os.path.join(out_dir, f'{prefix}_face.png'))
        _to_jpeg(os.path.join(out_dir, f'{prefix}_face.png'))
        for p in ps: os.remove(p)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    glb, out_dir = args[0], args[1]
    prefix = args[2] if len(args) > 2 else os.path.splitext(os.path.basename(glb))[0]
    arm, meshes, info = measure(glb)
    print(json.dumps(info, indent=1))
    with open(os.path.join(out_dir, prefix + '_verify.json'), 'w') as f:
        json.dump(info, f, indent=1)
    if '--norender' not in sys.argv:
        renders(arm, meshes, out_dir, prefix, quick=('--quick' in sys.argv or '--minimal' in sys.argv),
                minimal='--minimal' in sys.argv, height=info['bbox_max'][2])
