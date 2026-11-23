"""Stage C: retarget Mixamo-rig mocap (three.js example Xbot.glb) onto the MakeHuman/MPFB mixamo skeleton.

Method (world-space delta transfer):
  * rest poses differ (source = T-pose, target = MakeHuman A-pose with splayed legs), so for limb bones a
    correction C(b) rotates the target rest direction onto the source rest direction (minimal rotation);
    fingers inherit the hand's correction; spine / neck / head / clavicles / feet keep C = I so the target
    keeps its own upright rest posture and flat feet.
  * per frame:  W_T(b) = D_S(b) . C(b) . R_T(b)   with   D_S(b) = W_S(b) . R_S(b)^-1   (armature space 3x3)
  * hips translation: vertical offset from the source rest height scaled by the leg-length ratio, horizontal
    sway scaled likewise with any net travel removed (clips stay in place).
  * feet are re-grounded with a per-clip constant so the lowest sole contact sits on z = 0.
"""
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector, Quaternion

CHAIN_CHILD = {
    'Hips': 'Spine', 'Spine': 'Spine1', 'Spine1': 'Spine2', 'Spine2': 'Neck', 'Neck': 'Head',
}
for s in ('Left', 'Right'):
    CHAIN_CHILD.update({s + 'Shoulder': s + 'Arm', s + 'Arm': s + 'ForeArm', s + 'ForeArm': s + 'Hand',
                        s + 'Hand': s + 'HandMiddle1', s + 'UpLeg': s + 'Leg', s + 'Leg': s + 'Foot',
                        s + 'Foot': s + 'ToeBase'})
ALIGN = [s + n for s in ('Left', 'Right') for n in ('UpLeg', 'Leg', 'Arm', 'ForeArm', 'Hand')]


def _sname(n):
    return n.replace('mixamorig:', '').replace('mixamorig', '')


def import_source(path):
    before = set(bpy.data.objects); acts_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == 'ARMATURE')
    acts = [a for a in bpy.data.actions if a not in acts_before]
    return arm, new, acts


def _set_action(arm, act):
    ad = arm.animation_data or arm.animation_data_create()
    for t in ad.nla_tracks:
        t.mute = True
    ad.action = act
    try:
        if getattr(ad, 'action_slot', None) is None and len(act.slots):
            ad.action_slot = act.slots[0]
    except Exception:
        pass


def sample_source(arm, act):
    """Returns dict: frames, rot[bone] = list of 3x3 world-delta D per frame, hips = Nx3 world positions."""
    sc = bpy.context.scene
    _set_action(arm, act)
    f0, f1 = (int(round(x)) for x in act.frame_range)
    names = {_sname(b.name): b.name for b in arm.data.bones}
    mw = arm.matrix_world; mw3 = mw.to_3x3().normalized()
    rest = {k: (mw3 @ arm.data.bones[v].matrix_local.to_3x3()) for k, v in names.items()}
    D = {k: [] for k in names}; hips = []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        for k, v in names.items():
            W = mw3 @ arm.pose.bones[v].matrix.to_3x3().normalized()
            D[k].append(W @ rest[k].inverted())
        hips.append((mw @ arm.pose.bones[names['Hips']].matrix.translation)[:])
    return dict(n=f1 - f0 + 1, D=D, hips=np.array(hips))


def source_rest(arm):
    names = {_sname(b.name): b for b in arm.data.bones}
    mw = arm.matrix_world
    head = {k: mw @ b.head_local for k, b in names.items()}
    return head


class Target:
    def __init__(self, rig):
        self.rig = rig
        self.bones = [b.name for b in rig.data.bones]          # parents before children
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
        self.R = {b.name: b.matrix_local.to_3x3() for b in rig.data.bones}
        self.head = {b.name: b.head_local.copy() for b in rig.data.bones}
        self.tail = {b.name: b.tail_local.copy() for b in rig.data.bones}
        self.leg_len = sum((self.head[a] - self.head[b]).length for a, b in
                           (('LeftUpLeg', 'LeftLeg'), ('LeftLeg', 'LeftFoot')))
        # sole reference points (armature space, rest): heel, ball, toe tip for each foot
        self.sole = {}
        for s in ('Left', 'Right'):
            a = self.head[s + 'Foot']; t = self.head[s + 'ToeBase']; tt = self.tail[s + 'ToeBase']
            self.sole[s] = [(s + 'Foot', Vector((a.x, a.y + 0.045, 0.0))), (s + 'ToeBase', Vector((t.x, t.y, 0.0))),
                            (s + 'ToeBase', Vector((tt.x, tt.y, 0.0)))]

    def fk(self, W, hips_pos):
        """Armature-space joint positions given world orientations W[b] (3x3) and hips head position."""
        pos = {}
        for b in self.bones:
            p = self.parent[b]
            if p is None:
                pos[b] = Vector(hips_pos)
            else:
                # child's head offset is rigid in the parent's frame
                off = self.R[p].inverted() @ (self.head[b] - self.head[p])
                pos[b] = pos[p] + W[p] @ off
        return pos

    def sole_min(self, W, pos):
        z = []
        for s in ('Left', 'Right'):
            for b, pt in self.sole[s]:
                off = self.R[b].inverted() @ (pt - self.head[b])
                z.append((pos[b] + W[b] @ off).z)
        return z

    def local_quats(self, W):
        q = {}
        for b in self.bones:
            p = self.parent[b]
            if p is None:
                B = self.R[b].inverted() @ W[b]
            else:
                B = (W[p] @ self.R[p].inverted() @ self.R[b]).inverted() @ W[b]
            q[b] = B.to_quaternion()
        return q


def corrections(tgt, src_head):
    """C(b): minimal rotation taking the target rest bone direction onto the source rest direction."""
    C = {b: Matrix.Identity(3) for b in tgt.bones}
    for b in ALIGN:
        ch = CHAIN_CHILD[b]
        if b not in src_head or ch not in src_head:
            continue
        ds = (src_head[ch] - src_head[b]).normalized()
        dt = (tgt.head[ch] - tgt.head[b]).normalized()
        C[b] = dt.rotation_difference(ds).to_matrix()
    for s in ('Left', 'Right'):
        for b in tgt.bones:
            if b.startswith(s + 'Hand') and b != s + 'Hand':
                C[b] = C[s + 'Hand']
    return C


def retarget_clip(tgt, C, src_head, sample, src_leg_len, in_place=True, ground='const'):
    """Returns list of frames: (W dict of 3x3, hips position Vector)."""
    n = sample['n']; ratio = tgt.leg_len / src_leg_len
    hs = sample['hips']; rest_h = np.array(src_head['Hips'][:])
    # target hips height when standing in the *aligned* rest pose (legs brought under the hips)
    Wr = {b: C[b] @ tgt.R[b] for b in tgt.bones}
    pr = tgt.fk(Wr, tgt.head['Hips'])
    base = Vector(tgt.head['Hips']); base.z -= min(tgt.sole_min(Wr, pr))
    rel = (hs - rest_h[None]) * ratio
    if in_place:
        t = np.linspace(0, 1, n)[:, None]
        rel[:, :2] -= (rel[-1:, :2] - rel[0:1, :2]) * t          # net travel
        rel[:, :2] -= rel[:, :2].mean(0, keepdims=True)           # keep only the sway around the origin
    frames = []
    for f in range(n):
        W = {}
        for b in tgt.bones:
            Ds = sample['D'].get(b)
            W[b] = (Ds[f] @ C[b] @ tgt.R[b]) if Ds is not None else None
        for b in tgt.bones:                       # unmapped bones follow their parent rigidly
            if W[b] is None:
                p = tgt.parent[b]
                W[b] = W[p] @ tgt.R[p].inverted() @ tgt.R[b] if p else tgt.R[b].copy()
        frames.append([W, base + Vector(rel[f])])
    # re-ground
    mins = []
    for W, hp in frames:
        mins.append(min(tgt.sole_min(W, tgt.fk(W, hp))))
    mins = np.array(mins)
    if ground == 'const':
        off = np.full(n, mins.min())
    elif ground == 'frame':                    # one foot always planted (idle / walk)
        k = np.ones(5) / 5
        pad = np.concatenate([mins[-3:-1], mins, mins[1:3]])
        off = np.convolve(pad, k, mode='valid')
    else:
        off = np.zeros(n)
    for i, fr in enumerate(frames):
        fr[1].z -= off[i]
    return frames, dict(sole_min_before=(float(mins.min()), float(mins.max())), ratio=ratio)


def close_loop(tgt, frames):
    """Make last frame == first frame by spreading the residual over the clip (rotation + hips)."""
    n = len(frames)
    q0 = tgt.local_quats(frames[0][0]); q1 = tgt.local_quats(frames[-1][0])
    err = max(q0[b].rotation_difference(q1[b]).angle for b in tgt.bones)
    perr = (frames[-1][1] - frames[0][1]).length
    W0, p0 = frames[0]; Wn, pn = frames[-1]
    dW = {b: W0[b] @ Wn[b].inverted() for b in tgt.bones}       # world delta taking last -> first
    dp = p0 - pn
    for i, (W, p) in enumerate(frames):
        t = i / (n - 1)
        t = t * t * (3 - 2 * t) if n > 30 else t
        for b in tgt.bones:
            q = Quaternion().slerp(dW[b].to_quaternion(), t)
            W[b] = q.to_matrix() @ W[b]
        frames[i][1] = p + dp * t
    return err, perr


def write_action(tgt, name, frames, fps=30):
    """Create an action (quaternion rotations on all bones, location on Hips) and stash it on an NLA track."""
    rig = tgt.rig
    ad = rig.animation_data or rig.animation_data_create()
    act = bpy.data.actions.new(name)
    ad.action = act
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    prev = {}
    Rh = tgt.R['Hips']; h0 = tgt.head['Hips']
    for i, (W, hp) in enumerate(frames):
        q = tgt.local_quats(W)
        for b in tgt.bones:
            pb = rig.pose.bones[b]
            qq = q[b]
            if b in prev and prev[b].dot(qq) < 0:
                qq = -qq
            prev[b] = qq
            pb.rotation_quaternion = qq
            pb.keyframe_insert('rotation_quaternion', frame=i)
        pb = rig.pose.bones['Hips']
        pb.location = Rh.inverted() @ (hp - h0)
        pb.keyframe_insert('location', frame=i)
    act.use_fake_user = True
    act['stk_frames'] = len(frames)
    slot = getattr(ad, 'action_slot', None)
    tr = ad.nla_tracks.new(); tr.name = name
    st = tr.strips.new(name, 0, act); st.name = name
    try:
        if slot is not None:
            st.action_slot = slot
    except Exception:
        pass
    ad.action = None
    tr.mute = True
    return act


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)


def play(rig, name, frame):
    """Activate one clip (NLA track solo) and set the frame - used by the verification renders."""
    ad = rig.animation_data
    ad.action = None
    for t in ad.nla_tracks:
        t.mute = (t.name != name)
    reset_pose(rig)
    bpy.context.scene.frame_set(frame)
