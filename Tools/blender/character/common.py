"""Shared paths + MPFB bootstrap for the STOCKHOLM character pipeline.

Runs inside the `bpy` Python module (Blender 5.x, headless).  MPFB2 (MakeHuman
for Blender, GPL-3 code, CC0 base mesh/targets) must be installed as an
extension: see fetch_assets.py.
"""
import os, sys, tempfile
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ASSET_ROOT = os.environ.get('STK_MH_ASSETS', os.path.join(REPO, 'Assets', 'ThirdParty', 'makehuman'))
WORK = os.environ.get('STK_CHAR_WORK', os.path.join(tempfile.gettempdir(), 'stk_char_work'))   # scratch: .blend + textures
OUT_DIR = os.path.join(REPO, 'WebPreview', 'assets', 'characters')
RENDER_DIR = os.path.join(REPO, 'docs', 'character_renders')
MPFB_MOD = 'bl_ext.user_default.mpfb'


def asset(*parts):
    return os.path.join(ASSET_ROOT, *parts)


def reset_scene():
    """Empty scene but keep the MPFB add-on registered."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    enable_mpfb()


def enable_mpfb():
    import addon_utils
    if MPFB_MOD not in bpy.context.preferences.addons:
        addon_utils.enable(MPFB_MOD, default_set=True)
    import importlib
    return importlib.import_module(MPFB_MOD)


def quiet_mpfb():
    try:
        import importlib
        ls = importlib.import_module(MPFB_MOD + '.services.logservice').LogService
        ls.set_default_log_level(ls.ERROR if hasattr(ls, 'ERROR') else 1)
    except Exception:
        pass


def services():
    import importlib
    m = lambda n: importlib.import_module(MPFB_MOD + '.services.' + n)
    return (m('humanservice').HumanService, m('targetservice').TargetService,
            m('objectservice').ObjectService, m('rigservice').RigService)


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
