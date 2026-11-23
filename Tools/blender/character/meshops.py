"""Mesh helpers: helper-geometry removal, hidden-face culling, weight transfer, push-out."""
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import common as C


def bvh_of(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.transform(obj.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    t = BVHTree.FromBMesh(bm, epsilon=0.0)
    return t, bm


def delete_verts(obj, mask):
    """Delete vertices where mask[i] is True."""
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if mask[v.index]], context='VERTS')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()


def delete_faces(obj, fmask):
    bm = bmesh.new(); bm.from_mesh(obj.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if fmask[f.index]], context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(obj.data); bm.free(); obj.data.update()


def group_mask(obj, name):
    m = np.zeros(len(obj.data.vertices), bool)
    vg = obj.vertex_groups.get(name)
    if vg is None:
        return m
    gi = vg.index
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0.0:
                m[v.index] = True
    return m


def group_weights(obj, names):
    """Sum of weights of the named groups per vertex."""
    idx = {obj.vertex_groups[n].index for n in names if n in obj.vertex_groups}
    w = np.zeros(len(obj.data.vertices), np.float32)
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group in idx:
                w[v.index] += g.weight
    return w


def strip_body_helpers(body):
    """Keep only real skin: drop MakeHuman helper geometry and joint cubes, and delete-group faces."""
    for m in list(body.modifiers):
        if m.type == 'MASK':
            body.modifiers.remove(m)
    keep = group_mask(body, 'body')
    delete_verts(body, ~keep)
    # MakeHuman delete groups (authored per clothing item): remove faces fully inside
    for vg in [g for g in body.vertex_groups if g.name.startswith('Delete.')]:
        dm = group_mask(body, vg.name)
        fm = np.array([all(dm[v] for v in p.vertices) for p in body.data.polygons], bool)
        if fm.any():
            delete_faces(body, fm)


def keep_only_bone_groups(obj, rig):
    bones = {b.name for b in rig.data.bones}
    for vg in list(obj.vertex_groups):
        if vg.name not in bones:
            obj.vertex_groups.remove(vg)


def covered_mask(obj, cover_objs, max_dist=0.10, start=0.0015):
    """Per-vertex: a ray along the outward normal hits one of cover_objs within max_dist."""
    trees = [bvh_of(c) for c in cover_objs]
    mw = obj.matrix_world; n3 = mw.to_3x3()
    out = np.zeros(len(obj.data.vertices), bool)
    for v in obj.data.vertices:
        p = mw @ v.co; n = (n3 @ v.normal).normalized()
        o = p + n * start
        for t, _ in trees:
            hit = t.ray_cast(o, n, max_dist)
            if hit[0] is not None:
                out[v.index] = True; break
    for _, b in trees:
        b.free()
    return out


def cull_hidden(obj, cover_objs, protect=None, max_dist=0.10, rings=1):
    """Delete faces of obj that are hidden under cover_objs (all verts covered, with a safety ring)."""
    cov = covered_mask(obj, cover_objs, max_dist)
    if protect is not None:
        cov &= ~protect
    me = obj.data
    # erode: a vertex stays 'covered' only if all its edge-neighbours are covered
    for _ in range(rings):
        nb = cov.copy()
        for e in me.edges:
            a, b = e.vertices
            if not cov[a]: nb[b] = False
            if not cov[b]: nb[a] = False
        cov = nb
    fm = np.array([all(cov[v] for v in p.vertices) for p in me.polygons], bool)
    n = int(fm.sum())
    if n:
        delete_faces(obj, fm)
    return n


def transfer_weights(src, dst, rig):
    """Re-derive dst skin weights from src (nearest-face interpolated)."""
    for vg in list(dst.vertex_groups):
        dst.vertex_groups.remove(vg)
    C.activate(dst)
    m = dst.modifiers.new('wt', 'DATA_TRANSFER')
    m.object = src; m.use_vert_data = True; m.data_types_verts = {'VGROUP_WEIGHTS'}
    m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'; m.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.datalayout_transfer(modifier=m.name)
    while dst.modifiers[0].name != m.name:
        bpy.ops.object.modifier_move_up(modifier=m.name)
    bpy.ops.object.modifier_apply(modifier=m.name)
    keep_only_bone_groups(dst, rig)
    if not any(md.type == 'ARMATURE' for md in dst.modifiers):
        am = dst.modifiers.new('Armature', 'ARMATURE'); am.object = rig
    dst.parent = rig


def smooth_weights(obj, iters=2, factor=0.5):
    C.activate(obj)
    bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
    try:
        bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=factor, repeat=iters)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')


def limit_normalize(obj, limit=4):
    C.activate(obj)
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=limit)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)


def push_outside(obj, inner, margin=0.006, reach=0.04, vmask=None):
    """Move verts of obj that are inside / too close to `inner` out to `margin` above its surface."""
    t, b = bvh_of(inner)
    mwi = obj.matrix_world.inverted(); mw = obj.matrix_world
    n = 0
    for v in obj.data.vertices:
        if vmask is not None and not vmask[v.index]:
            continue
        p = mw @ v.co
        loc, nor, idx, dist = t.find_nearest(p, reach)
        if loc is None:
            continue
        sd = (p - loc).dot(nor)
        if sd < margin:
            v.co = mwi @ (p + nor * (margin - sd)); n += 1
    b.free(); obj.data.update()
    return n


def laplacian_smooth(obj, vmask, iters=5, lam=0.5):
    me = obj.data
    co = np.array([v.co[:] for v in me.vertices], np.float64)
    ed = np.array([e.vertices[:] for e in me.edges], np.int64)
    deg = np.zeros(len(co)); np.add.at(deg, ed[:, 0], 1); np.add.at(deg, ed[:, 1], 1)
    w = np.asarray(vmask, np.float64)[:, None] * lam
    for _ in range(iters):
        acc = np.zeros_like(co)
        np.add.at(acc, ed[:, 0], co[ed[:, 1]]); np.add.at(acc, ed[:, 1], co[ed[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        co = co + w * (avg - co)
    me.vertices.foreach_set('co', co.ravel()); me.update()


def coords(obj):
    a = np.empty(len(obj.data.vertices) * 3, np.float64)
    obj.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3)


def set_coords(obj, co):
    obj.data.vertices.foreach_set('co', np.asarray(co, np.float64).ravel()); obj.data.update()
