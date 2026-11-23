#!/usr/bin/env python3
"""Builds bare winter street trees (lime-like, as on Sveavägen) as GLB.

Each tree is a branching skeleton grown with a seeded random walk, then every branch is swept into a tube with
proper UVs (u around, v along) so the scanned bark texture tiles correctly. Snow lies as thin strips on the upper
side of the thicker branches. Materials are named `tree_bark` and `tree_snow`; the game assigns the textures.

Usage: python3 Tools/blender/build_winter_tree.py [--render]
Output: WebPreview/assets/props/winter_tree_{a,b,c}.glb  (Y-up, metres, origin at the trunk base)
"""
import math, os, random, sys
import bpy
from mathutils import Vector

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, 'WebPreview', 'assets', 'props')
UP = Vector((0, 0, 1))


def grow(seed, height=9.5):
    """Returns a list of branches; each is a list of (point, radius)."""
    rnd = random.Random(seed); branches = []

    def branch(p, d, length, r0, depth):
        n = max(2, int(length / 0.5)); pts = [(p.copy(), r0)]; seg = length / n; r_end = max(0.004, r0 * 0.78)
        for i in range(1, n + 1):
            t = i / n
            wob = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.5, 0.5))) * (0.06 + 0.035 * depth)
            lift = UP * (0.07 if depth > 0 else 0.0)           # young wood bends back up towards the light
            d = (d + wob + lift).normalized()
            p = p + d * seg
            pts.append((p.copy(), r0 + (r_end - r0) * t))
        branches.append(pts)
        if depth >= 6:
            return
        # The first child continues the limb; the others are laterals leaving from its outer two thirds.
        kids = rnd.choice((3, 4)) if depth == 0 else rnd.choice((2, 3, 3))
        base_ang = rnd.uniform(0, math.tau)
        for k in range(kids):
            lead = k == 0 and depth > 0
            at = n if (lead or depth == 0) else rnd.randint(max(1, n // 3), n)
            bp, br = pts[at]
            side = d.cross(UP); side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
            ang = base_ang + math.tau * k / kids + rnd.uniform(-0.4, 0.4)
            spread = math.radians(rnd.uniform(8, 20) if lead else rnd.uniform(30, 44) if depth == 0 else rnd.uniform(32, 58))
            off = (side * math.cos(ang) + d.cross(side) * math.sin(ang)).normalized()
            cd = (d * math.cos(spread) + off * math.sin(spread)).normalized()
            cl = length * (rnd.uniform(0.70, 0.82) if (lead or depth == 0) else rnd.uniform(0.52, 0.72))
            cr = br * (0.84 if lead else rnd.uniform(0.62, 0.74) if depth == 0 else rnd.uniform(0.50, 0.66))
            branch(bp, cd, cl, max(0.004, cr), depth + 1)

    trunk_h = height * rnd.uniform(0.27, 0.31)
    branch(Vector((0, 0, 0)), Vector((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 1)).normalized(), trunk_h, 0.20, 0)
    return branches


def sweep(branches):
    """Tubes with UVs. Returns verts, faces, uvs-per-face-corner, and snow strips."""
    V, F, UV, SV, SF = [], [], [], [], []
    for pts in branches:
        r_max = pts[0][1]; sides = 10 if r_max > 0.09 else 6 if r_max > 0.035 else 4 if r_max > 0.015 else 3
        # parallel-transported frame
        t0 = (pts[1][0] - pts[0][0]).normalized(); a = t0.cross(UP)
        a = a.normalized() if a.length > 1e-3 else Vector((1, 0, 0)); b = t0.cross(a)
        rings = []; v_len = 0.0; prev = pts[0][0]
        for i, (p, r) in enumerate(pts):
            t = ((pts[min(i + 1, len(pts) - 1)][0] - pts[max(i - 1, 0)][0])).normalized()
            a = (a - t * a.dot(t)).normalized(); b = t.cross(a)
            flare = 1.0 + (0.55 * max(0.0, 1 - p.z / 0.5) if r_max > 0.15 else 0.0)   # root flare on the trunk
            v_len += (p - prev).length; prev = p
            base = len(V)
            for k in range(sides + 1):
                th = math.tau * k / sides
                V.append(p + (a * math.cos(th) + b * math.sin(th)) * r * flare)
            rings.append((base, v_len, r))
            # snow lies on top of thicker, not-too-steep branches
            if 0.022 < r < 0.16 and abs(t.z) < 0.82 and p.z > 2.2:
                u = (UP - t * UP.dot(t)).normalized(); s = t.cross(u)
                sb = len(SV)
                for ang, lift in ((-0.95, 0.004), (0.0, 0.012 + r * 0.35), (0.95, 0.004)):
                    SV.append(p + (u * math.cos(ang) + s * math.sin(ang)) * (r + lift))
                if i > 0 and prev_snow is not None:
                    for k in range(2):
                        SF.append((prev_snow + k, prev_snow + k + 1, sb + k + 1, sb + k))
                prev_snow = sb
            else:
                prev_snow = None
        for (b0, v0, r0), (b1, v1, r1) in zip(rings, rings[1:]):
            for k in range(sides):
                F.append((b0 + k, b0 + k + 1, b1 + k + 1, b1 + k))
                u0, u1 = k / sides, (k + 1) / sides; us = max(1.0, round(r_max * 2 * math.pi / 0.5))   # ~0.5 m of bark per tile around
                UV.append([(u0 * us, v0 / 0.9), (u1 * us, v0 / 0.9), (u1 * us, v1 / 0.9), (u0 * us, v1 / 0.9)])
    return V, F, UV, SV, SF


def build(name, seed, height):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    V, F, UV, SV, SF = sweep(grow(seed, height))
    bark = bpy.data.materials.new('tree_bark'); bark.use_nodes = True
    bsdf = bark.node_tree.nodes['Principled BSDF']; bsdf.inputs['Base Color'].default_value = (0.16, 0.13, 0.11, 1); bsdf.inputs['Roughness'].default_value = 0.95
    snow = bpy.data.materials.new('tree_snow'); snow.use_nodes = True
    sb = snow.node_tree.nodes['Principled BSDF']; sb.inputs['Base Color'].default_value = (0.92, 0.94, 0.97, 1); sb.inputs['Roughness'].default_value = 0.8
    objs = []
    for nm, verts, faces, mat, uvs in (('bark', V, F, bark, UV), ('snow', SV, SF, snow, None)):
        me = bpy.data.meshes.new(f'{name}_{nm}'); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
        if uvs:
            layer = me.uv_layers.new(name='UVMap')
            for poly, quad in zip(me.polygons, uvs):
                for li, uv in zip(poly.loop_indices, quad):
                    layer.data[li].uv = uv
        for poly in me.polygons: poly.use_smooth = True
        me.materials.append(mat)
        ob = bpy.data.objects.new(f'{name}_{nm}', me); bpy.context.collection.objects.link(ob); objs.append(ob)
    os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, f'{name}.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=True, export_normals=True, export_texcoords=True, export_materials='EXPORT')
    tris = sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons)
    hi = max(v.z for v in V); wide = max(max(abs(v.x), abs(v.y)) for v in V)
    print(f'BUILT {name}: {tris} triangles, height {hi:.1f} m, crown radius {wide:.1f} m, {os.path.getsize(path) // 1024} KB')
    return objs


def render(name, path):
    """Quick Cycles look at the tree that is currently in the scene."""
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.render.resolution_x = 700; sc.render.resolution_y = 900
    world = bpy.data.worlds.new('w'); world.use_nodes = True; world.node_tree.nodes['Background'].inputs[0].default_value = (0.72, 0.78, 0.86, 1); world.node_tree.nodes['Background'].inputs[1].default_value = 1.1; sc.world = world
    bpy.ops.mesh.primitive_plane_add(size=60); bpy.context.object.data.materials.append(bpy.data.materials['tree_snow'])
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(62), 0, math.radians(35))); bpy.context.object.data.energy = 2.5
    cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (13.5, -10.5, 3.2); tgt = Vector((0, 0, 4.9)); co.rotation_euler = (tgt - co.location).to_track_quat('-Z', 'Y').to_euler(); cam.lens = 40
    sc.render.filepath = path; sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 85
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    for name, seed, h in (('winter_tree_a', 11, 9.5), ('winter_tree_b', 29, 10.5), ('winter_tree_c', 47, 8.5)):
        build(name, seed, h)
        if '--render' in sys.argv:
            render(name, os.path.join(REPO, 'docs', 'prop_renders', f'{name}.jpg'))
