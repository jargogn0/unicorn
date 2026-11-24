"""Texture preparation (Pillow + numpy) and glTF-friendly Principled materials."""
import os
import numpy as np
import bpy
from PIL import Image, ImageFilter, ImageDraw
from . import common as C


def tex_dir():
    d = os.path.join(C.WORK, 'tex'); os.makedirs(d, exist_ok=True); return d


def parse_mhmat(path):
    out = {}
    if not path or not os.path.isfile(path):
        return out
    d = os.path.dirname(path)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            p = line.strip().split(None, 1)
            if len(p) == 2 and p[0] in ('diffuseTexture', 'normalmapTexture'):
                out[p[0]] = os.path.join(d, p[1].strip())
            elif len(p) == 2 and p[0] == 'diffuseColor':
                out['diffuseColor'] = tuple(float(x) for x in p[1].split()[:3])
    return out


def save_tex(img, name, alpha=False, quality=88):
    """Save PIL image under WORK/tex as JPEG (opaque) or PNG (alpha). Returns path."""
    if alpha:
        p = os.path.join(tex_dir(), name + '.png'); img.convert('RGBA').save(p, optimize=True)
    else:
        p = os.path.join(tex_dir(), name + '.jpg'); img.convert('RGB').save(p, quality=quality, optimize=True)
    return p


def load_fit(path, max_size=1024):
    im = Image.open(path); im.load()
    if max(im.size) > max_size:
        s = max_size / max(im.size)
        im = im.resize((max(1, round(im.size[0] * s)), max(1, round(im.size[1] * s))), Image.LANCZOS)
    return im


def tint_by_luma(im, dark, light, lo=None, hi=None, gamma=1.0):
    """Remap luminance of im onto a dark->light colour ramp (sRGB 0-255 tuples)."""
    a = np.asarray(im.convert('RGB'), np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    al = np.asarray(im.convert('RGBA'))[..., 3] > 8
    sel = lum[al] if al.any() else lum.ravel()
    lo = np.percentile(sel, 2) if lo is None else lo
    hi = np.percentile(sel, 98) if hi is None else hi
    t = np.clip((lum - lo) / max(hi - lo, 1e-4), 0, 1) ** gamma
    d = np.array(dark, np.float32); l = np.array(light, np.float32)
    out = d[None, None] + (l - d)[None, None] * t[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def fabric_noise(size, seed=1, scale=1.0):
    """Tileable fine fabric grain in [-1,1] (sum of blurred white noise octaves)."""
    rng = np.random.default_rng(seed)
    acc = np.zeros((size, size), np.float32)
    for rad, amp in ((0.6, 0.55), (1.6, 0.3), (5.0, 0.15)):
        n = rng.standard_normal((size, size)).astype(np.float32)
        im = Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8), 'L')
        # wrap-pad for tileability
        big = Image.new('L', (size * 3, size * 3))
        for i in range(3):
            for j in range(3):
                big.paste(im, (i * size, j * size))
        big = big.filter(ImageFilter.GaussianBlur(rad * scale))
        b = np.asarray(big.crop((size, size, 2 * size, 2 * size)), np.float32)
        b = (b - b.mean()) / (b.std() + 1e-6)
        acc += amp * b
    return np.clip(acc / 2.5, -1, 1)


def height_to_normal(h, strength=2.0):
    """Tileable height (float HxW) -> tangent-space normal map PIL image (OpenGL, +Y up)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), 'RGB')


def curls_height(size=512, seed=7, cell=13):
    """Tight-curl bump pattern: jittered grid of soft domes (tileable)."""
    rng = np.random.default_rng(seed)
    n = size // cell
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    h = np.zeros((size, size), np.float32)
    for i in range(n):
        for j in range(n):
            cx = (i + 0.5 + rng.uniform(-0.35, 0.35)) * cell; cy = (j + 0.5 + rng.uniform(-0.35, 0.35)) * cell
            r = cell * rng.uniform(0.45, 0.72)
            dx = (xx - cx + size / 2) % size - size / 2; dy = (yy - cy + size / 2) % size - size / 2
            d = np.sqrt(dx * dx + dy * dy) / r
            # ring-shaped coil: bright rim, darker centre
            dome = np.clip(1 - d * d, 0, 1) * (0.55 + 0.45 * np.clip(d * 1.6, 0, 1))
            h = np.maximum(h, dome * rng.uniform(0.7, 1.0))
    return h


def octopus_logo(size=256, color=(110, 78, 168), eye=(245, 240, 255)):
    """Original, simple octopus mark (dome head, five tentacles, two eyes) on transparent RGBA."""
    S = size * 4
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = color + (255,)
    cx = S * 0.5
    # head
    d.ellipse([cx - S * 0.30, S * 0.10, cx + S * 0.30, S * 0.66], fill=c)
    d.rectangle([cx - S * 0.30, S * 0.38, cx + S * 0.30, S * 0.58], fill=c)
    # tentacles: 5 rounded legs, outer ones curl outwards
    legs = [(-0.26, -0.10), (-0.13, -0.03), (0.0, 0.0), (0.13, 0.03), (0.26, 0.10)]
    w = S * 0.085
    for ox, curl in legs:
        x0 = cx + ox * S
        pts = []
        for k in range(13):
            t = k / 12
            y = S * (0.55 + 0.33 * t)
            x = x0 + curl * S * (t ** 1.6) * 1.3 + np.sin(t * np.pi * 1.5 + ox * 9) * S * 0.012
            pts.append((x, y))
        for (x, y) in pts:
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=c)
    # eyes
    for sx in (-1, 1):
        ex = cx + sx * S * 0.11; ey = S * 0.40; r = S * 0.045
        d.ellipse([ex - r, ey - r * 1.25, ex + r, ey + r * 1.25], fill=eye + (255,))
    return im.resize((size, size), Image.LANCZOS)


def make_material(name, base=None, color=(0.8, 0.8, 0.8), roughness=0.8, normal=None, normal_strength=1.0,
                  alpha=None, double_sided=False, metallic=0.0, emissive=0.0, rough_tex=None):
    """alpha: None | 'BLEND' | 'MASK'.  base/normal are image file paths."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    # specular / IOR stay at glTF defaults so the export needs no material extensions
    if base:
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(base, check_existing=True)
        tex.location = (-400, 300)
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha:
            nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
        if emissive > 0:          # self-lit floor (core glTF emissiveTexture + factor <= 1, no extension needed)
            nt.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = min(1.0, emissive)
    if rough_tex:            # roughness from the green channel of a (glTF-style occlusion/roughness/metal) map
        rt = nt.nodes.new('ShaderNodeTexImage'); rt.image = bpy.data.images.load(rough_tex, check_existing=True)
        rt.image.colorspace_settings.name = 'Non-Color'; rt.location = (-700, 40)
        sep = nt.nodes.new('ShaderNodeSeparateColor'); sep.location = (-380, 40)
        nt.links.new(rt.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    if normal:
        ntex = nt.nodes.new('ShaderNodeTexImage'); ntex.image = bpy.data.images.load(normal, check_existing=True)
        ntex.image.colorspace_settings.name = 'Non-Color'; ntex.location = (-700, -200)
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
        nm.location = (-300, -200)
        nt.links.new(ntex.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    m.use_backface_culling = not double_sided
    m['stk_alpha'] = alpha or 'OPAQUE'
    if alpha:
        try:
            m.surface_render_method = 'DITHERED' if alpha == 'MASK' else 'BLENDED'
        except Exception:
            pass
    return m


def assign(obj, mat):
    obj.data.materials.clear(); obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.material_index = 0
