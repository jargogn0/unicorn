"""Cycles-CPU verification render helpers (headless, no GPU)."""
import bpy, math
from mathutils import Vector


def setup_render(res=(800, 800), samples=32):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get('Background')
    if bg is None:
        nt = sc.world.node_tree
        bg = nt.nodes.new('ShaderNodeBackground')
        out = nt.nodes.new('ShaderNodeOutputWorld')
        nt.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[0].default_value = (0.78, 0.80, 0.84, 1)
    bg.inputs[1].default_value = 0.9
    if 'VR_Sun' not in bpy.data.objects:
        sun = bpy.data.lights.new('VR_Sun', 'SUN'); sun.energy = 2.6; sun.angle = math.radians(12)
        so = bpy.data.objects.new('VR_Sun', sun); sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(52), 0, math.radians(35))
        fill = bpy.data.lights.new('VR_Fill', 'SUN'); fill.energy = 0.9; fill.angle = math.radians(40)
        fo = bpy.data.objects.new('VR_Fill', fill); sc.collection.objects.link(fo)
        fo.rotation_euler = (math.radians(60), 0, math.radians(-140))
        bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
        fl = bpy.context.active_object; fl.name = 'VR_Floor'
        m = bpy.data.materials.new('VR_FloorMat'); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.62, 0.63, 0.65, 1)
        m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
        fl.data.materials.append(m)
    if 'VR_Cam' not in bpy.data.objects:
        cam = bpy.data.cameras.new('VR_Cam'); co = bpy.data.objects.new('VR_Cam', cam)
        sc.collection.objects.link(co)
    sc.camera = bpy.data.objects['VR_Cam']


def shot(path, azim_deg=0.0, target=(0, 0, 0.95), dist=4.2, elev_deg=5.0, lens=50, front_axis='-Y'):
    """azim 0 = camera in front of the character. front_axis is the direction the character faces."""
    sc = bpy.context.scene
    cam = sc.camera
    cam.data.lens = lens
    a = math.radians(azim_deg); e = math.radians(elev_deg)
    base = Vector((0, -1, 0)) if front_axis == '-Y' else Vector((0, 1, 0))
    # rotate base around Z by azim
    d = Vector((base.x * math.cos(a) - base.y * math.sin(a), base.x * math.sin(a) + base.y * math.cos(a), 0))
    pos = Vector(target) + d * dist * math.cos(e) + Vector((0, 0, dist * math.sin(e)))
    cam.location = pos
    look = (Vector(target) - pos)
    cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def montage(paths, out, cols=None):
    """Stitch PNGs side by side using Blender's image API (no PIL dependency)."""
    import numpy as np
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p)
        w, h = im.size
        a = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(a)
        imgs.append(a.reshape(h, w, 4)); bpy.data.images.remove(im)
    cols = cols or len(imgs)
    rows = [np.concatenate(imgs[i:i + cols], axis=1) for i in range(0, len(imgs), cols)]
    wmax = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, wmax - r.shape[1]), (0, 0)), constant_values=1.0) for r in rows]
    full = np.concatenate(rows[::-1], axis=0)
    h, w, _ = full.shape
    o = bpy.data.images.new('montage', w, h, alpha=False)
    o.pixels.foreach_set(full.ravel()); o.filepath_raw = out; o.file_format = 'PNG'; o.save()
    bpy.data.images.remove(o)
