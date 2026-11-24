#!/usr/bin/env python3
"""Refresh the third-party asset list in Assets/ThirdParty/character_manifest.json from configs.py.

    python3 Tools/blender/character/update_manifest.py

For every character in CONFIGS it collects the MakeHuman assets referenced (skin, eyes, brows, lashes, hair,
clothes), reads author + licence from each asset's own .mhclo / .mhmat header, refuses anything that is not
CC0 or CC BY, and rewrites `outputs`, `asset_pack_archives` (urls) and `third_party_assets` (hand-written
notes such as `where_used` are preserved).  The other manifest sections are left untouched.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from character import common as C                      # noqa: E402
from character.configs import CONFIGS                  # noqa: E402
from character.fetch_assets import PACKS               # noqa: E402

MANIFEST = os.path.join(C.REPO, 'Assets', 'ThirdParty', 'character_manifest.json')
MH_TEAM = 'MakeHuman team (Data Collection AB, Joel Palmius, Jonas Hauquier)'
NORM = {'cc0': 'CC0 1.0', 'cc_by': 'CC BY (header says "CC_by"; version not stated in the file)',
        'cc by 3.0': 'CC BY 3.0', 'cc  by 3.0': 'CC BY 3.0', 'cc-by 4.0': 'CC BY 4.0', 'cc by 4.0': 'CC BY 4.0'}
KIND = {'clothes': 'clothing', 'skins': 'skin texture', 'hair': 'hair', 'eyes': 'eyes', 'eyebrows': 'eyebrows',
        'eyelashes': 'eyelashes', 'teeth': 'teeth'}


def header(path):
    author = lic = None
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f):
            if i > 40:
                break
            s = line.strip()
            m = re.match(r'#?\s*author:?\s+(.*)', s, re.I)
            if m: author = author or m.group(1).strip()
            m = re.match(r'#?\s*license:?\s+(.*)', s, re.I)
            if m: lic = lic or m.group(1).strip()
            if 'released as CC0' in s:
                lic = lic or 'CC0'; author = author or MH_TEAM
            m = re.match(r'#\s*(.+?)\s*-\s*CC0\s*$', s)
            if m:
                author = author or m.group(1); lic = lic or 'CC0'
    return author, lic


def assets_of(cfg):
    out = [cfg['skin'], cfg.get('eyes', 'makehuman_system_assets_cc0/eyes/low-poly/low-poly.mhclo'),
           cfg.get('eye_mat', 'makehuman_system_assets_cc0/eyes/materials/brown.mhmat')]
    out += [cfg[k] for k in ('eyebrows', 'eyelashes', 'hair', 'teeth') if cfg.get(k)]
    out += [rel for _, rel in cfg.get('clothes', [])]
    return out


def main():
    with open(MANIFEST, 'r', encoding='utf-8') as f:
        man = json.load(f)
    old = {e['file']: e for e in man.get('third_party_assets', [])}
    used = {}
    for name, cfg in CONFIGS.items():
        for rel in assets_of(cfg):
            used.setdefault(rel, []).append(name)
    entries = []
    for rel in sorted(used):
        full = C.asset(rel)
        author, lic = header(full)
        if rel.endswith('low-poly.mhclo') and not lic:      # the eye mesh file has no header; its materials do
            author, lic = header(C.asset('makehuman_system_assets_cc0/eyes/materials/brown.mhmat'))
        norm = NORM.get((lic or '').lower())
        if not norm or not author:
            raise SystemExit(f'REFUSED: {rel}: author={author!r} licence={lic!r} is not a recognised CC0 / CC BY header')
        pack, kind = rel.split('/')[0], rel.split('/')[1]
        e = dict(old.get(rel, {}))
        e.update(name=('eyes/' + os.path.splitext(os.path.basename(rel))[0]) if kind == 'eyes' else os.path.basename(os.path.dirname(rel)),
                 type='MakeHuman ' + KIND.get(kind, kind), file=rel, author=author, licence=norm,
                 licence_as_written_in_file=lic, pack=pack, source_url=PACKS[pack], used_in=sorted(used[rel]))
        entries.append(e)
    man['third_party_assets'] = entries
    man['outputs'] = [f'WebPreview/assets/characters/{n}.glb' for n in CONFIGS]
    arch = man.setdefault('asset_pack_archives', {})
    for pack in sorted({e['pack'] for e in entries}):
        arch.setdefault(pack, {})['url'] = PACKS[pack]
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(man, f, indent=1, ensure_ascii=False)
    print(len(entries), 'assets,', len(CONFIGS), 'characters')
    for e in entries:
        print(f"  {e['name']:38s} {e['author'][:28]:28s} {e['licence'][:12]:12s} {','.join(n.replace('pedestrian_', 'p').replace('npc_', '') for n in e['used_in'])}")


if __name__ == '__main__':
    main()
