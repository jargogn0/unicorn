"""Side-by-side of the exported hero GLB against the owner's character sheet.

    python3 Tools/blender/character/compare_sheet.py [glb] [reference.webp] [out_dir]

Loads the GLB into a fresh scene (so it shows exactly what ships), poses it with the Idle clip, sets the
`Smile` morph target and renders the same views as the sheet: front, side, back, 3/4 and a face close-up, on a
similar neutral grey ground with soft studio light.  Also renders the face under a dim warm interior light.
Writes  doudou_vs_reference.jpg  (sheet row above, render row below) and  doudou_face_vs_reference.jpg.
"""
import sys, os, math
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from character import common as C, verify as V, render_util as RU   # noqa: E402

BG = (0.098, 0.086, 0.098)          # linear value of the sheet's grey-mauve ground (~ #5A545A)


def _light(name, kind, loc, power, color=(1, 1, 1), size=1.5):
    d = bpy.data.lights.new(name, kind); d.energy = power; d.color = color
    if kind == 'AREA':
        d.size = size
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def lighting(mode):
    sc = bpy.context.scene
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT' or o.name == 'VR_Floor']:
        bpy.data.objects.remove(o, do_unlink=True)
    w = sc.world; nt = w.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld'); mix = nt.nodes.new('ShaderNodeMixShader')
    lp = nt.nodes.new('ShaderNodeLightPath'); amb = nt.nodes.new('ShaderNodeBackground'); cam = nt.nodes.new('ShaderNodeBackground')
    cam.inputs[0].default_value = (*BG, 1) if mode == 'studio' else (0.012, 0.011, 0.014, 1)
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0]); nt.links.new(amb.outputs[0], mix.inputs[1])
    nt.links.new(cam.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0)); fl = bpy.context.active_object; fl.name = 'VR_Floor'
    m = bpy.data.materials.new('floor'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*BG, 1) if mode == 'studio' else (0.03, 0.028, 0.03, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
    fl.data.materials.append(m)
    if mode == 'studio':
        amb.inputs[0].default_value = (0.60, 0.58, 0.64, 1); amb.inputs[1].default_value = 0.38
        _light('key', 'AREA', (-2.2, -3.4, 3.0), 250, (1.0, 0.97, 0.93), 2.5)
        _light('fill', 'AREA', (3.0, -2.6, 1.6), 70, (0.93, 0.93, 1.0), 3.0)
        _light('rim', 'AREA', (1.2, 3.2, 2.8), 170, (0.86, 0.80, 1.0), 2.0)
    else:   # dim warm interior, e.g. the apartment at night: one warm lamp, faint cool spill from a window
        amb.inputs[0].default_value = (0.10, 0.085, 0.075, 1); amb.inputs[1].default_value = 0.12
        _light('lamp', 'AREA', (-1.4, -1.8, 2.5), 34, (1.0, 0.70, 0.42), 0.8)
        _light('window', 'AREA', (2.0, 2.5, 2.2), 14, (0.55, 0.65, 1.0), 2.0)


def set_morph(meshes, name, value):
    for m in meshes:
        kb = m.data.shape_keys.key_blocks if m.data.shape_keys else None
        if kb and name in kb:
            kb[name].value = value


def main(glb, ref_path, out_dir):
    from PIL import Image
    arm, meshes, info = V.measure(glb)
    height = info['bbox_max'][2]
    tmp = os.path.join(C.WORK, 'compare'); os.makedirs(tmp, exist_ok=True)
    V.set_clip(arm, 'Idle', 0)
    set_morph(meshes, 'Smile', 1.0)
    RU.setup_render((440, 1000), 48)
    lighting('studio')
    body = []
    for lab, az in (('front', 0), ('side', 90), ('back', 180), ('threeq', 38)):
        p = os.path.join(tmp, f'b_{lab}.png'); RU.shot(p, az, target=(0, 0, height * 0.495), dist=12.6, lens=200, elev_deg=1.5); body.append(p)
    RU.setup_render((760, 800), 64)
    faces = {}
    # face camera is placed relative to the (animated) head bone, so the close-up is a true front-ish view of the
    # face whatever the Idle pose is doing with the head
    hb = arm.pose.bones['Head']; rest = arm.data.bones['Head']
    Rm = (arm.matrix_world.to_3x3() @ hb.matrix.to_3x3()) @ rest.matrix_local.to_3x3().inverted()
    fwd = (Rm @ Vector((0, -1, 0))).normalized(); up = (Rm @ Vector((0, 0, 1))).normalized()
    head_pos = arm.matrix_world @ hb.head
    centre = head_pos + up * 0.085 + fwd * 0.03
    from mathutils import Matrix
    view = (Matrix.Rotation(math.radians(-14), 3, up) @ fwd).normalized()
    cam = bpy.context.scene.camera; cam.data.lens = 100
    cam.location = centre + view * 1.02
    zc = view; yc = (up - zc * up.dot(zc)).normalized(); xc = yc.cross(zc)
    cam.rotation_euler = Matrix((xc, yc, zc)).transposed().to_euler()
    for lab, mode, smile in (('studio_smile', 'studio', 1.0), ('studio_neutral', 'studio', 0.0),
                             ('interior_smile', 'interior', 1.0), ('interior_neutral', 'interior', 0.0)):
        lighting(mode); set_morph(meshes, 'Smile', smile)
        p = os.path.join(tmp, f'f_{lab}.png')
        bpy.context.scene.render.filepath = p; bpy.ops.render.render(write_still=True); faces[lab] = p
    ref = Image.open(ref_path).convert('RGB')
    ref_body = ref.crop((0, 20, 1010, 1000)); ref_face = ref.crop((1046, 36, 1420, 432))
    # --- sheet 1: reference row above, render row below (four body views + smiling face)
    Wb, Hrow = 1010, 980
    row2 = Image.new('RGB', (Wb, Hrow), (90, 84, 90))
    cells = [(0, 262), (262, 222), (484, 262), (746, 264)]          # same column layout as the sheet
    for (x_, cw), p in zip(cells, body):
        im = Image.open(p).convert('RGB'); im = im.resize((int(im.width * Hrow / im.height), Hrow), Image.LANCZOS)
        x0 = (im.width - cw) // 2
        row2.paste(im.crop((x0, 0, x0 + cw, Hrow)), (x_, 0))
    fw = 420
    def face_tile(im, h=Hrow // 2):
        im = im.resize((fw, int(im.height * fw / im.width)), Image.LANCZOS)
        t = Image.new('RGB', (fw, h), (90, 84, 90)); t.paste(im, (0, (h - im.height) // 2)); return t
    sheet = Image.new('RGB', (Wb + fw, Hrow * 2 + 8), (40, 38, 40))
    sheet.paste(ref_body, (0, 0)); sheet.paste(face_tile(ref_face, Hrow), (Wb, 0))
    sheet.paste(row2, (0, Hrow + 8))
    sheet.paste(face_tile(Image.open(faces['studio_smile']).convert('RGB')), (Wb, Hrow + 8))
    sheet.paste(face_tile(Image.open(faces['interior_smile']).convert('RGB')), (Wb, Hrow + 8 + Hrow // 2))
    sheet = sheet.resize((1180, int(sheet.height * 1180 / sheet.width)), Image.LANCZOS)
    os.makedirs(out_dir, exist_ok=True)
    q = 82
    while True:
        sheet.save(os.path.join(out_dir, 'doudou_vs_reference.jpg'), quality=q, optimize=True)
        if os.path.getsize(os.path.join(out_dir, 'doudou_vs_reference.jpg')) < 395000 or q < 50: break
        q -= 6
    # --- sheet 2: faces - reference crop | studio | dim warm interior, smiling (top) and neutral (bottom)
    T = 440
    tile = lambda im: im.resize((T, int(im.height * T / im.width)), Image.LANCZOS)
    rf = tile(ref_face); th = rf.height
    fs = Image.new('RGB', (T * 3 + 16, th * 2 + 8), (40, 38, 40))
    for r, (a, b) in enumerate((('studio_smile', 'interior_smile'), ('studio_neutral', 'interior_neutral'))):
        fs.paste(rf, (0, r * (th + 8)))
        for c, k in enumerate((a, b)):
            im = tile(Image.open(faces[k]).convert('RGB')); y0 = max(0, (im.height - th) // 2)
            fs.paste(im.crop((0, y0, T, y0 + th)), ((c + 1) * (T + 8), r * (th + 8)))
    fs.save(os.path.join(out_dir, 'doudou_face_vs_reference.jpg'), quality=86, optimize=True)
    print('wrote', os.path.join(out_dir, 'doudou_vs_reference.jpg'), os.path.getsize(os.path.join(out_dir, 'doudou_vs_reference.jpg')),
          os.path.getsize(os.path.join(out_dir, 'doudou_face_vs_reference.jpg')))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0] if len(a) > 0 else os.path.join(C.OUT_DIR, 'doudou.glb'),
         a[1] if len(a) > 1 else os.path.join(C.REPO, 'ArtReference', 'doudou_character_sheet.webp'),
         a[2] if len(a) > 2 else C.RENDER_DIR)
