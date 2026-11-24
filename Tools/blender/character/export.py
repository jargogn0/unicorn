"""Stage D: join meshes, export GLB (Y-up, +Z forward), patch alpha modes, report stats."""
import os, json, struct
import bpy
from . import common as C


def join_meshes(rig, name):
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.get('stk_role')]
    order = ['body', 'eyes', 'teeth', 'hoodie', 'hood', 'pocket', 'ribs', 'strings', 'jeans', 'cuffs', 'shoes', 'boots',
             'laces', 'watch', 'hair', 'logo', 'eyebrows', 'eyelashes']
    meshes.sort(key=lambda o: order.index(o['stk_role']) if o['stk_role'] in order else 50)
    for o in meshes:
        for uv in o.data.uv_layers:
            uv.name = 'UVMap'
        for m in list(o.modifiers):
            if m.type != 'ARMATURE':
                o.modifiers.remove(m)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    mesh = bpy.context.active_object
    mesh.name = name + '_Mesh'; mesh.data.name = name + '_Mesh'
    mesh.parent = rig
    for m in mesh.modifiers:
        if m.type == 'ARMATURE':
            m.object = rig
    # merge duplicate material slots (hoodie + pocket share one material)
    bpy.ops.object.material_slot_remove_unused()
    from . import hero
    morphs = hero.attrs_to_shape_keys(mesh)          # 'mt_*' delta attributes -> shape keys -> glTF morph targets
    if morphs:
        print('morph targets:', morphs)
    return mesh


def patch_glb(path, alpha_modes):
    """Set alphaMode/alphaCutoff per material name (the Blender exporter cannot express MASK reliably)."""
    with open(path, 'rb') as f:
        data = f.read()
    magic, ver, total = struct.unpack('<III', data[:12])
    jl, jt = struct.unpack('<II', data[12:20])
    js = json.loads(data[20:20 + jl]); rest = data[20 + jl:]
    for m in js.get('materials', []):
        mode = alpha_modes.get(m['name'])
        if mode == 'MASK':
            m['alphaMode'] = 'MASK'; m['alphaCutoff'] = 0.45
        elif mode == 'BLEND':
            m['alphaMode'] = 'BLEND'
        elif mode == 'OPAQUE':
            m.pop('alphaMode', None); m.pop('alphaCutoff', None)
    # clips: keep rotations for every joint but translation only on the root joint (Hips) and no scale tracks,
    # so clips stay proportion-independent and can be shared / cross-faded freely in three.js
    names = [n.get('name') for n in js['nodes']]
    for a in js.get('animations', []):
        keep = [c for c in a['channels'] if c['target']['path'] == 'rotation' or
                (c['target']['path'] == 'translation' and names[c['target']['node']] == 'Hips')]
        used = sorted({c['sampler'] for c in keep}); remap = {o: i for i, o in enumerate(used)}
        a['samplers'] = [a['samplers'][i] for i in used]
        for c in keep:
            c['sampler'] = remap[c['sampler']]
        a['channels'] = keep
    if 'extensionsUsed' in js and not js['extensionsUsed']:
        del js['extensionsUsed']
    js.setdefault('asset', {})['copyright'] = 'STOCKHOLM character build - see Assets/ThirdParty/character_manifest.json'
    out = json.dumps(js, separators=(',', ':')).encode('utf-8')
    out += b' ' * ((4 - len(out) % 4) % 4)
    blob = struct.pack('<II', len(out), 0x4E4F534A) + out + rest
    with open(path, 'wb') as f:
        f.write(struct.pack('<III', magic, ver, 12 + len(blob)) + blob)
    return js


def export_glb(rig, mesh, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sc = bpy.context.scene
    sc.frame_start = 0; sc.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); mesh.select_set(True)
    bpy.context.view_layer.objects.active = rig
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
              export_skins=True, export_animations=True, export_animation_mode='NLA_TRACKS',
              export_force_sampling=True, export_frame_step=1, export_optimize_animation_size=True,
              export_image_format='AUTO', export_materials='EXPORT', export_texcoords=True, export_normals=True,
              export_tangents=False, export_morph=True, export_morph_normal=False, export_morph_tangent=False, export_cameras=False, export_lights=False,
              export_extras=False, export_def_bones=False, export_all_influences=False,
              export_anim_slide_to_zero=True, export_negative_frame='SLIDE')
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    kw = {k: v for k, v in kw.items() if k in props}
    bpy.ops.export_scene.gltf(**kw)
    alpha = {m.name: m.get('stk_alpha', 'OPAQUE') for m in bpy.data.materials}
    js = patch_glb(path, alpha)
    tris = 0
    for me in js['meshes']:
        for p in me['primitives']:
            tris += js['accessors'][p['indices']]['count'] // 3
    stats = dict(file=path, bytes=os.path.getsize(path), triangles=tris,
                 vertices=sum(js['accessors'][p['attributes']['POSITION']]['count'] for me in js['meshes'] for p in me['primitives']),
                 joints=len(js['skins'][0]['joints']), materials=[m['name'] for m in js['materials']],
                 images=len(js.get('images', [])),
                 morph_targets=(js['meshes'][0].get('extras') or {}).get('targetNames', []),
                 animations={a['name']: max(js['accessors'][s['input']]['count'] for s in a['samplers']) for a in js.get('animations', [])})
    return stats
