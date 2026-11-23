"""Stage C driver: build all clips on a finished character rig.

Retargeted mocap (Mixamo animations shipped with the three.js r160 examples, Xbot.glb):
    Idle, Walk, Run, Agree, HeadShake
Hand-keyed (procedural IK keyed on top of the mocap idle, authored here):
    Talk, Interact
All clips are in place, 30 fps, first frame == last frame.
"""
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector, Quaternion
from . import retarget as RT

MOCAP = [  # (clip name, source action, grounding mode)
    ('Idle', 'idle', 'frame'), ('Walk', 'walk', 'frame'), ('Run', 'run', 'const'),
    ('Agree', 'agree', 'frame'), ('HeadShake', 'headShake', 'frame'),
]


def _copy(frames):
    return [[{b: m.copy() for b, m in W.items()}, p.copy()] for W, p in frames]


def _descendants(tgt, bone):
    out = [bone]
    for b in tgt.bones:
        p = tgt.parent[b]
        if p in out and b not in out:
            out.append(b)
    return out


def rotate_branch(tgt, W, bone, rot3):
    for b in _descendants(tgt, bone):
        W[b] = rot3 @ W[b]


def _bone_dir(tgt, W, bone, child):
    return (W[bone] @ tgt.R[bone].inverted() @ (tgt.head[child] - tgt.head[bone])).normalized()


def arm_ik(tgt, W, hips, side, target, pole, weight=1.0, twist=0.0):
    """Analytic two-bone IK for one arm, blended by weight. Fingers follow the hand."""
    if weight <= 1e-4:
        return
    A, F, H = side + 'Arm', side + 'ForeArm', side + 'Hand'
    pos = tgt.fk(W, hips)
    S = pos[A]
    a = (tgt.head[F] - tgt.head[A]).length; b = (tgt.head[H] - tgt.head[F]).length
    v = Vector(target) - S
    d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, v.length)); dr = v.normalized()
    ca = (a * a + d * d - b * b) / (2 * a * d); sa = math.sqrt(max(0.0, 1 - ca * ca))
    pl = Vector(pole); perp = (pl - dr * pl.dot(dr)).normalized()
    elbow = S + dr * (a * ca) + perp * (a * sa)
    u = (elbow - S).normalized(); l = (S + dr * d - elbow).normalized()
    rA = _bone_dir(tgt, W, A, F).rotation_difference(u).to_matrix()
    rF = _bone_dir(tgt, W, F, H).rotation_difference(l).to_matrix()
    if twist:
        rF = Matrix.Rotation(twist, 3, l) @ rF
    new = {A: rA @ W[A], F: rF @ W[F]}
    for bn in _descendants(tgt, H):
        new[bn] = rF @ W[bn]
    for bn, m in new.items():
        q = W[bn].to_quaternion().slerp(m.to_quaternion(), weight)
        W[bn] = q.to_matrix()


def _ease(t):
    t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)


def _bump(t, a, b, c, d):
    """0 before a, ramps to 1 at b, holds to c, back to 0 at d."""
    if t <= a or t >= d: return 0.0
    if t < b: return _ease((t - a) / (b - a))
    if t <= c: return 1.0
    return 1.0 - _ease((t - c) / (d - c))


def make_interact(tgt, idle, n=40):
    """Reach forward with the right hand (press / pick up at chest height), then return to idle frame 0."""
    s = tgt.scale
    frames = _copy([idle[0]] * n)
    for i, (W, hp) in enumerate(frames):
        t = i / (n - 1)
        w = _bump(t, 0.0, 0.34, 0.56, 1.0)
        lean = math.radians(9) * w
        rotate_branch(tgt, W, 'Spine1', Matrix.Rotation(-lean * 0.6, 3, 'X') @ Matrix.Rotation(math.radians(7) * w, 3, 'Z'))
        rotate_branch(tgt, W, 'Spine2', Matrix.Rotation(-lean * 0.4, 3, 'X'))
        rotate_branch(tgt, W, 'Head', Matrix.Rotation(-math.radians(8) * w, 3, 'X'))
        tgtp = Vector((-0.12 * s, -0.50 * s, 1.20 * s))
        arm_ik(tgt, W, hp, 'Right', tgtp, pole=(-0.6, 0.5, -0.8), weight=w, twist=math.radians(-35) * w)
        # index finger slightly extended, others relaxed-curled, by curling the 3 other fingers
        for f in ('Middle', 'Ring', 'Pinky'):
            for k in (1, 2):
                bn = f'RightHand{f}{k}'
                ax = (W[bn] @ tgt.R[bn].inverted() @ Vector((1, 0, 0))).normalized()
                rotate_branch(tgt, W, bn, Matrix.Rotation(math.radians(18) * w, 3, ax))
    return frames


def make_talk(tgt, idle):
    """Conversational gesturing: mocap idle (two cycles) + keyed hand gestures and head nods."""
    s = tgt.scale
    base = idle[:-1] + idle[:-1] + [idle[0]]
    frames = _copy(base); n = len(frames)
    for i, (W, hp) in enumerate(frames):
        t = i / (n - 1)
        wr = _bump(t, 0.04, 0.16, 0.40, 0.52) + _bump(t, 0.58, 0.68, 0.84, 0.96) * 0.9
        wl = _bump(t, 0.56, 0.68, 0.82, 0.95)
        beat = math.sin(t * math.pi * 2 * 7)
        nod = math.radians(3.5) * math.sin(t * math.pi * 2 * 5) * (0.3 + 0.7 * max(wr, wl))
        yaw = math.radians(5) * math.sin(t * math.pi * 2 * 2)
        rotate_branch(tgt, W, 'Head', Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(nod, 3, 'X'))
        rotate_branch(tgt, W, 'Spine2', Matrix.Rotation(math.radians(2.0) * math.sin(t * math.pi * 2 * 2), 3, 'Z'))
        w1 = _bump(t, 0.04, 0.16, 0.40, 0.52); w2 = _bump(t, 0.58, 0.68, 0.84, 0.96)
        out = 0.06 * w2                                        # second gesture opens outwards
        tr = Vector(((-0.20 - out) * s, (-0.30 + 0.025 * beat) * s, (1.33 - 0.5 * out + 0.03 * beat) * s))
        arm_ik(tgt, W, hp, 'Right', tr, pole=(-0.3, 0.3, -0.9), weight=wr, twist=math.radians(30) * wr)
        tl = Vector((0.26 * s, (-0.28 - 0.02 * beat) * s, (1.27 - 0.025 * beat) * s))
        arm_ik(tgt, W, hp, 'Left', tl, pole=(0.3, 0.3, -0.9), weight=wl, twist=math.radians(-30) * wl)
    return frames


def build_clips(rig, source_glb, extra=True):
    sc = bpy.context.scene
    sc.render.fps = 30; sc.frame_start = 0
    if rig.animation_data:
        rig.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    src, new, acts = RT.import_source(source_glb)
    acts = {a.name: a for a in acts}
    sh = RT.source_rest(src)
    tgt = RT.Target(rig)
    tgt.scale = (tgt.head['Head'].z) / 1.60          # reach targets are authored for a ~1.82 m figure
    Cc = RT.corrections(tgt, sh)
    sl = (sh['LeftUpLeg'] - sh['LeftLeg']).length + (sh['LeftLeg'] - sh['LeftFoot']).length
    clips = {}; report = {}
    for name, srcname, ground in MOCAP:
        if not extra and name in ('Agree', 'HeadShake'):
            continue
        smp = RT.sample_source(src, acts[srcname])
        fr, info = RT.retarget_clip(tgt, Cc, sh, smp, sl, in_place=True, ground=ground)
        err = RT.close_loop(tgt, fr)
        clips[name] = fr
        report[name] = dict(frames=len(fr), source=f'Xbot.glb:{srcname}', kind='retargeted mocap',
                            loop_residual_fixed_rad=round(err[0], 4), **info)
    # remove the source rig + its actions again
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    for a in acts.values():
        bpy.data.actions.remove(a)
    clips['Talk'] = make_talk(tgt, clips['Idle'])
    report['Talk'] = dict(frames=len(clips['Talk']), kind='hand-keyed IK gestures layered on retargeted Idle')
    clips['Interact'] = make_interact(tgt, clips['Idle'])
    report['Interact'] = dict(frames=len(clips['Interact']), kind='hand-keyed (IK reach, right hand), starts/ends on Idle frame 0')
    order = ['Idle', 'Walk', 'Run', 'Talk', 'Interact', 'Agree', 'HeadShake']
    for name in order:
        if name in clips:
            RT.write_action(tgt, name, clips[name])
    RT.reset_pose(rig)
    sc.frame_set(0)
    return report
