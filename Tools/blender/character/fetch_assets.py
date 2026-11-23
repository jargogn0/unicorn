#!/usr/bin/env python3
"""Fetch third-party inputs for the character build into Assets/ThirdParty/makehuman/ (git-ignored).

    python3 Tools/blender/character/fetch_assets.py [--cache DIR] [--skip-mpfb]

* MakeHuman asset packs (https://files.makehumancommunity.org/asset_packs/): CC0 system assets plus the
  CC0 / CC-BY community packs actually referenced by configs.py.  Every asset's licence is in its .mhclo /
  .mhmat header and is recorded in Assets/ThirdParty/character_manifest.json.
* MPFB2 (MakeHuman Plugin For Blender, GPL-3 code; used only as a build tool) from extensions.blender.org,
  verified against the sha256 published by the extensions API, installed as a Blender user extension.
* Xbot.glb from the three.js r160 examples (Mixamo skeleton + animations) for retargeting.

Archives are treated as untrusted data: each is unpacked into its own directory, member paths are
validated, and nothing inside them is executed (MPFB itself is only installed through Blender's extension
installer).
"""
import hashlib, json, os, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ROOT = os.environ.get('STK_MH_ASSETS', os.path.join(REPO, 'Assets', 'ThirdParty', 'makehuman'))
BASE = 'https://files.makehumancommunity.org/asset_packs'
PACKS = {  # directory name -> url
    'makehuman_system_assets_cc0': f'{BASE}/makehuman_system_assets/makehuman_system_assets_cc0.zip',
    'shirts01_cc0': f'{BASE}/shirts01/shirts01_cc0.zip',
    'shirts02_ccby': f'{BASE}/shirts02/shirts02_ccby.zip',
    'pants01_cc0': f'{BASE}/pants01/pants01_cc0.zip',
    'pants02_ccby': f'{BASE}/pants02/pants02_ccby.zip',
    'shoes01_cc0': f'{BASE}/shoes01/shoes01_cc0.zip',
    'shoes02_ccby': f'{BASE}/shoes02/shoes02_ccby.zip',
    'shoes03_ccby': f'{BASE}/shoes03/shoes03_ccby.zip',
    'gloves01_cc0': f'{BASE}/gloves01/gloves01_cc0.zip',
    'suits01_cc0': f'{BASE}/suits01/suits01_cc0.zip',          # story NPCs
    'hair01_cc0': f'{BASE}/hair01/hair01_cc0.zip',
}
XBOT = 'https://cdn.jsdelivr.net/gh/mrdoob/three.js@r160/examples/models/gltf/Xbot.glb'
EXT_API = 'https://extensions.blender.org/api/v1/extensions/'


def curl(url, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.part'
    subprocess.run(['curl', '-fsSL', '--retry', '3', '-o', tmp, url], check=True)
    os.replace(tmp, dst)


def safe_extract(zpath, dest):
    os.makedirs(dest, exist_ok=True)
    root = os.path.realpath(dest)
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            target = os.path.realpath(os.path.join(dest, info.filename))
            if not (target == root or target.startswith(root + os.sep)):
                raise RuntimeError(f'unsafe path in {zpath}: {info.filename}')
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError(f'symlink in {zpath}: {info.filename}')
        z.extractall(dest)


def fetch_packs(cache):
    for name, url in PACKS.items():
        dest = os.path.join(ROOT, name)
        if os.path.isdir(dest) and os.listdir(dest):
            print('have', name); continue
        zname = os.path.basename(url)
        zpath = os.path.join(cache, zname) if cache and os.path.isfile(os.path.join(cache, zname)) else os.path.join(ROOT, '_zips', zname)
        if cache and name == 'makehuman_system_assets_cc0' and os.path.isfile(os.path.join(cache, 'sys.zip')):
            zpath = os.path.join(cache, 'sys.zip')
        if not os.path.isfile(zpath):
            print('download', url); curl(url, zpath)
        print('extract', name); safe_extract(zpath, dest)
    xb = os.path.join(ROOT, 'threejs_r160', 'Xbot.glb')
    if not os.path.isfile(xb):
        src = os.path.join(cache, 'Xbot.glb') if cache else ''
        if src and os.path.isfile(src):
            os.makedirs(os.path.dirname(xb), exist_ok=True)
            with open(src, 'rb') as a, open(xb, 'wb') as b:
                b.write(a.read())
        else:
            curl(XBOT, xb)
    print('Xbot.glb sha256', hashlib.sha256(open(xb, 'rb').read()).hexdigest())


def install_mpfb(cache):
    import bpy, addon_utils
    if any(m.__name__ == 'bl_ext.user_default.mpfb' for m in addon_utils.modules()):
        print('MPFB already installed'); return
    api = os.path.join(ROOT, '_zips', 'extensions.json'); curl(EXT_API, api)
    with open(api, 'r', encoding='utf-8') as f:
        ext = next(e for e in json.load(f)['data'] if e['id'] == 'mpfb')
    zpath = os.path.join(cache, 'mpfb.zip') if cache and os.path.isfile(os.path.join(cache, 'mpfb.zip')) else os.path.join(ROOT, '_zips', 'mpfb.zip')
    if not os.path.isfile(zpath):
        curl(ext['archive_url'], zpath)
    digest = 'sha256:' + hashlib.sha256(open(zpath, 'rb').read()).hexdigest()
    if digest != ext['archive_hash']:
        raise RuntimeError(f'MPFB archive hash mismatch: {digest} != {ext["archive_hash"]}')
    print('MPFB', ext['version'], digest)
    bpy.ops.extensions.package_install_files(filepath=zpath, repo='user_default', enable_on_install=True)
    bpy.ops.wm.save_userpref()


if __name__ == '__main__':
    cache = sys.argv[sys.argv.index('--cache') + 1] if '--cache' in sys.argv else None
    fetch_packs(cache)
    if '--skip-mpfb' not in sys.argv:
        install_mpfb(cache)
