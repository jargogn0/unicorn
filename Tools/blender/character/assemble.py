"""Stage A: assemble a MakeHuman character with MPFB2 (body, rig, body parts, clothes)."""
import os, bpy
from . import common as C


def assemble(cfg, save_path=None):
    C.reset_scene(); C.quiet_mpfb()
    HumanService, TargetService, ObjectService, RigService = C.services()

    macro = TargetService.get_default_macro_info_dict()
    macro.update({k: v for k, v in cfg['macro'].items() if k != 'race'})
    macro['race'] = dict(cfg['macro']['race'])
    bm = HumanService.create_human(scale=0.1, macro_detail_dict=macro)
    bm.name = 'Human'
    for tgt, w in cfg.get('targets', []):
        full = TargetService.target_full_path(tgt)
        if full is None:
            print('!! target not found', tgt); continue
        TargetService.load_target(bm, full, weight=w)
    bm['stk_role'] = 'body'
    bm['stk_mhmat'] = C.asset(cfg['skin'])

    rig = HumanService.add_builtin_rig(bm, 'mixamo', import_weights=True)
    rig.name = 'Armature'

    def add(role, rel, typ):
        o = HumanService.add_mhclo_asset(C.asset(rel), bm, asset_type=typ, subdiv_levels=0,
                                         material_type='MAKESKIN')
        o['stk_role'] = role
        o['stk_src'] = rel
        # remember the material file MPFB resolved from the .mhclo
        d = os.path.dirname(C.asset(rel))
        mat = None
        with open(C.asset(rel), 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('material '):
                    mat = os.path.join(d, line.split(None, 1)[1].strip())
        o['stk_mhmat'] = mat or ''
        o.name = 'stk_' + role
        return o

    eyes = add('eyes', cfg.get('eyes', 'makehuman_system_assets_cc0/eyes/low-poly/low-poly.mhclo'), 'Eyes')
    eyes['stk_mhmat'] = C.asset(cfg.get('eye_mat', 'makehuman_system_assets_cc0/eyes/materials/brown.mhmat'))
    if cfg.get('eyebrows'):
        add('eyebrows', cfg['eyebrows'], 'Eyebrows')
    if cfg.get('eyelashes'):
        add('eyelashes', cfg['eyelashes'], 'Eyelashes')
    if cfg.get('hair'):
        add('hair', cfg['hair'], 'Hair')
    for role, rel in cfg.get('clothes', []):
        add(role, rel, 'Clothes')
    if save_path:
        bpy.ops.wm.save_as_mainfile(filepath=save_path)
    return bm, rig
