"""Cycles (CPU) QA renders of a vehicle on a neutral ground under the repo's sky panorama."""
import math, os
import bpy
import numpy as np
from mathutils import Vector
from .common import REPO, get_mat

VIEWS = {  # name: (azimuth deg from the vehicle's front (+Y in Blender), elevation deg, distance factor)
    "front34": (35.0, 12.0, 1.0), "side": (90.0, 6.0, 1.0), "rear34": (145.0, 12.0, 1.0),
    "front": (0.0, 6.0, 0.9), "rear": (180.0, 6.0, 0.9), "top": (90.0, 70.0, 1.05), "low_front34": (25.0, 3.0, 0.9),
    "rear34b": (-150.0, 22.0, 1.0),
}


def setup(res=(1000, 560), samples=48):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 12
    sc.render.threads_mode = "FIXED"; sc.render.threads = 4
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Filmic" if "Filmic" in [i.identifier for i in type(sc.view_settings).bl_rna.properties["view_transform"].enum_items] else "AgX"
    w = sc.world or bpy.data.worlds.new("W"); sc.world = w
    w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    hdri = os.path.join(REPO, "WebPreview", "assets", "hdri", "snowy_park_01.jpg")
    if os.path.exists(hdri):
        env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(hdri, check_existing=True)
        nt.links.new(env.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 1.6
    else:
        bg.inputs[0].default_value = (0.75, 0.8, 0.9, 1); bg.inputs[1].default_value = 1.0
    nt.links.new(bg.outputs[0], out.inputs[0])
    if "QA_Sun" not in bpy.data.objects:
        sun = bpy.data.lights.new("QA_Sun", "SUN"); sun.energy = 3.0; sun.angle = math.radians(6)
        so = bpy.data.objects.new("QA_Sun", sun); sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(50), 0, math.radians(-40))
        me = bpy.data.meshes.new("QA_Ground"); s = 60
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new("QA_Ground", me); sc.collection.objects.link(g)
        m = bpy.data.materials.new("QA_GroundMat"); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.32, 0.33, 0.35, 1); b.inputs["Roughness"].default_value = 0.85
        me.materials.append(m)
        cam = bpy.data.cameras.new("QA_Cam"); co = bpy.data.objects.new("QA_Cam", cam); sc.collection.objects.link(co)
    sc.camera = bpy.data.objects["QA_Cam"]


def apply_tint(m, tint):
    """Multiply a material's base colour (constant or texture) by tint, the way three.js material.color does."""
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    inp = bsdf.inputs["Base Color"]
    if not inp.is_linked:
        inp.default_value = (*tint, 1); return
    src = inp.links[0].from_socket
    mix = nt.nodes.get("QA_Tint")
    if mix is None:
        mix = nt.nodes.new("ShaderNodeMix"); mix.name = "QA_Tint"; mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(src, mix.inputs["A"]); nt.links.new(mix.outputs["Result"], inp)
    mix.inputs["B"].default_value = (*tint, 1)


def bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    bpy.context.view_layer.update()
    for o in objs:
        if o.type != "MESH": continue
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi


def render_views(objs, prefix, tint=None, tint_mat="car_paint", views=("front34", "side", "rear34"), res=(1000, 560), samples=48, lens=70, fmt="PNG"):
    setup(res, samples)
    sc = bpy.context.scene
    if tint is not None:
        for m in bpy.data.materials:
            if m.name.split(".")[0] == tint_mat: apply_tint(m, tint)
    lo, hi = bounds(objs)
    c = (lo + hi) / 2; size = max(hi.x - lo.x, hi.y - lo.y, (hi.z - lo.z) * 2.0)
    cam = sc.camera; cam.data.lens = lens
    paths = []
    for v in views:
        az, el, df = VIEWS[v]
        a, e = math.radians(az), math.radians(el)
        dist = size * 2.25 * df * (lens / 70.0)
        d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
        tgt = Vector((c.x, c.y, c.z * 0.95))
        cam.location = tgt + d * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.image_settings.file_format = fmt
        if fmt == "JPEG": sc.render.image_settings.quality = 88
        sc.render.filepath = f"{prefix}_{v}.{'jpg' if fmt == 'JPEG' else 'png'}"
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    return paths
