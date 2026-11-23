#!/usr/bin/env python3
"""STOCKHOLM character build: MakeHuman (MPFB2) body + clothes -> game rig -> retargeted clips -> GLB.

    python3 Tools/blender/character/fetch_assets.py          # once: MPFB2 add-on + asset packs + Xbot.glb
    python3 Tools/blender/build_character.py                 # builds every character
    python3 Tools/blender/build_character.py --only doudou   # or a subset (comma separated)
    python3 Tools/blender/build_character.py --verify        # also run verify.py (measure + Cycles renders)

Needs the `bpy` Python module (Blender >= 4.2; developed on 5.3, headless, CPU only), numpy and Pillow.
Outputs: WebPreview/assets/characters/<name>.glb  (+ renders in docs_character_renders/ with --verify)
Pipeline stages live in Tools/blender/character/:  assemble -> finalize(+garments) -> animate(retarget) -> export.
"""
import sys, os, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from character import common as C, assemble as A, finalize as F, garments as G, animate as AN, export as EX  # noqa: E402
from character.configs import CONFIGS  # noqa: E402

XBOT = C.asset('threejs_r160', 'Xbot.glb')


def build(name, keep_blend=True):
    cfg = CONFIGS[name]
    os.makedirs(C.WORK, exist_ok=True)
    A.assemble(cfg)
    rig = F.finalize(cfg)
    report = AN.build_clips(rig, XBOT, extra=cfg.get('extra_clips', True))
    mesh = EX.join_meshes(rig, cfg['name'])
    if keep_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(C.WORK, name + '.blend'))
    stats = EX.export_glb(rig, mesh, os.path.join(C.OUT_DIR, name + '.glb'))
    stats['clips'] = report
    stats['bones'] = [b.name for b in rig.data.bones]
    with open(os.path.join(C.WORK, name + '_build.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    print('BUILT', name, stats['bytes'], 'bytes', stats['triangles'], 'tris', stats['animations'])
    return stats


def main(argv):
    names = list(CONFIGS)
    if '--only' in argv:
        names = argv[argv.index('--only') + 1].split(',')
    for n in names:
        build(n)
    if '--verify' in argv:
        os.makedirs(C.RENDER_DIR, exist_ok=True)
        for n in names:
            cmd = [sys.executable, os.path.join(HERE, 'character', 'verify.py'),
                   os.path.join(C.OUT_DIR, n + '.glb'), C.RENDER_DIR, n]
            if n != 'doudou':
                cmd.append('--quick')
            subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main(sys.argv[1:])
