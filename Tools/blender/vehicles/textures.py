"""Small generated textures: the number plate and the paint 'shut line' atlas (door, bonnet and tailgate gaps)."""
import os
import bpy

FONT_CANDIDATES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                   "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]

# paint atlas layout (uv): side view, top view, front view, rear view
U_LEN, Z_SPAN, Y_SPAN = 5.0, 1.6, 1.0


def uv_side(x, z): return (x / U_LEN, 0.01 + z / Z_SPAN * 0.30)
def uv_top(x, y): return (x / U_LEN, 0.34 + abs(y) / Y_SPAN * 0.22)
def uv_front(y, z): return (0.02 + abs(y) / Y_SPAN * 0.22, 0.60 + z / Z_SPAN * 0.30)
def uv_rear(y, z): return (0.30 + abs(y) / Y_SPAN * 0.22, 0.60 + z / Z_SPAN * 0.30)


def paint_atlas(lines, path, size=512, ss=4, shade=60, width=0.9):
    """lines: {'side': [polyline...], 'top': [...], 'front': [...], 'rear': [...]} in design-frame metres."""
    from PIL import Image, ImageDraw
    S = size * ss
    im = Image.new("L", (S, S), 255)
    d = ImageDraw.Draw(im)
    fn = {"side": uv_side, "top": uv_top, "front": uv_front, "rear": uv_rear}
    for view, polys in lines.items():
        for poly in polys:
            px = [(fn[view](*p)[0] * S, (1.0 - fn[view](*p)[1]) * S) for p in poly]
            d.line(px, fill=shade, width=max(1, int(round(width * ss))), joint="curve")
    im = im.resize((size, size), Image.LANCZOS).convert("RGB")
    im.save(path, optimize=True)
    return path


def plate(path, text="STH 47K", size=(512, 112)):
    from PIL import Image, ImageDraw, ImageFont
    ss = 3
    W, H = size[0] * ss, size[1] * ss
    im = Image.new("RGB", (W, H), (236, 236, 232))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([3 * ss, 3 * ss, W - 3 * ss, H - 3 * ss], radius=10 * ss, outline=(20, 20, 20), width=3 * ss)
    d.rounded_rectangle([6 * ss, 6 * ss, 50 * ss, H - 6 * ss], radius=7 * ss, fill=(28, 58, 150))     # plain blue band, no emblem
    font = None
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            font = ImageFont.truetype(f, int(H * 0.70)); break
    if font is None:
        font = ImageFont.load_default()
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((W + 50 * ss - tw) / 2 - box[0], (H - th) / 2 - box[1]), text, font=font, fill=(18, 18, 18))
    im = im.resize(size, Image.LANCZOS)
    im.save(path, optimize=True)
    return path


def lamp_textures(work_dir):
    """Base-colour and emissive maps for the head and tail lamps (u: inboard -> outboard, v: bottom -> top)."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H, ss = 256, 128, 3
    out = {}

    def canvas(col):
        im = Image.new("RGB", (W * ss, H * ss), col); return im, ImageDraw.Draw(im)

    def R(d, u0, v0, u1, v1, fill, rad=0.0):
        d.rounded_rectangle([u0 * W * ss, (1 - v1) * H * ss, u1 * W * ss, (1 - v0) * H * ss], radius=rad * H * ss, fill=fill)

    def E(d, u, v, r, fill, outline=None, width=0):
        cx, cy, rr = u * W * ss, (1 - v) * H * ss, r * H * ss
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=fill, outline=outline, width=width * ss)

    # head lamp: smoked housing, two projector lenses, light bar along the top that runs out to the tail
    base, d = canvas((34, 36, 40)); emis, e = canvas((0, 0, 0))
    R(d, 0.03, 0.08, 0.97, 0.92, (58, 62, 68), 0.12)
    for u in [0.60 + 0.03 * i for i in range(12)]:
        R(d, u, 0.12, u + 0.012, 0.66, (92, 97, 104))
    for u in (0.20, 0.43):
        E(d, u, 0.40, 0.25, (22, 24, 27), (150, 156, 164), 2)
        E(d, u, 0.40, 0.14, (175, 190, 205)); E(d, u - 0.01, 0.44, 0.05, (245, 248, 252))
        E(e, u, 0.40, 0.13, (150, 146, 132))
    R(d, 0.06, 0.76, 0.95, 0.88, (240, 242, 245), 0.06); R(e, 0.06, 0.76, 0.95, 0.88, (255, 250, 236), 0.06)
    out["head"] = (base, emis)
    # tail lamp: deep red lens, bright band, darker lower section with a clear reversing block inboard
    base, d = canvas((92, 6, 8)); emis, e = canvas((0, 0, 0))
    R(d, 0.02, 0.05, 0.98, 0.95, (120, 8, 10), 0.10)
    R(d, 0.05, 0.10, 0.95, 0.40, (70, 5, 7), 0.05)
    R(d, 0.07, 0.14, 0.26, 0.36, (170, 170, 172), 0.04)
    R(d, 0.05, 0.54, 0.95, 0.80, (235, 40, 28), 0.08); R(e, 0.05, 0.54, 0.95, 0.80, (255, 34, 16), 0.08)
    R(d, 0.80, 0.14, 0.95, 0.80, (235, 40, 28), 0.05); R(e, 0.80, 0.14, 0.95, 0.80, (255, 34, 16), 0.05)
    out["tail"] = (base, emis)
    paths = {}
    for k, (b_, e_) in out.items():
        for tag, im in (("base", b_), ("emis", e_)):
            p = os.path.join(work_dir, f"lamp_{k}_{tag}.png")
            im.resize((W, H), Image.LANCZOS).save(p, optimize=True); paths[(k, tag)] = p
    return paths


def lamp_materials(work_dir):
    from .common import get_mat
    paths = lamp_textures(work_dir)
    for k, name in (("head", "car_headlight"), ("tail", "car_taillight")):
        m = get_mat(name)
        nt = m.node_tree
        if nt.nodes.get("LampBase"): continue
        bsdf = nt.nodes["Principled BSDF"]
        tb = nt.nodes.new("ShaderNodeTexImage"); tb.name = "LampBase"; tb.image = load(paths[(k, "base")], f"{name}_base")
        te = nt.nodes.new("ShaderNodeTexImage"); te.name = "LampEmis"; te.image = load(paths[(k, "emis")], f"{name}_emissive")
        nt.links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0


def load(path, name):
    img = bpy.data.images.load(path, check_existing=False)
    img.name = name
    img.pack()
    return img
