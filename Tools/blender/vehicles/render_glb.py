#!/usr/bin/env python3
"""QA: re-import an exported GLB into a fresh scene and render it with Cycles the way the game shows it
(single-sided materials have their back faces made invisible, so flipped or missing faces show up as holes).

    python3 Tools/blender/vehicles/render_glb.py <file.glb> <out dir> <name> [--tint r,g,b] [--views a,b,c] [--res 1000] [--spp 48]
"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import bpy  # noqa: E402
from vehicles import export as EX, render_qa  # noqa: E402


def cull_backfaces():
    for m in bpy.data.materials:
        if not m.use_nodes or not m.use_backface_culling: continue
        nt = m.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None or not out.inputs["Surface"].is_linked: continue
        src = out.inputs["Surface"].links[0].from_socket
        geo = nt.nodes.new("ShaderNodeNewGeometry"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(geo.outputs["Backfacing"], mix.inputs[0]); nt.links.new(src, mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])


def main(argv):
    glb, out_dir, name = argv[:3]
    opt = dict(zip(argv[3::2], argv[4::2]))
    objs = EX.reimport(glb)
    cull_backfaces()
    tint = tuple(float(v) for v in opt["--tint"].split(",")) if "--tint" in opt else None
    tint_mat = "bike_frame" if any(m.name.startswith("bike_frame") for m in bpy.data.materials) else "car_paint"
    views = opt.get("--views", "front34,side,rear34").split(",")
    res = int(opt.get("--res", 1000))
    fmt = opt.get("--fmt", "JPEG")
    render_qa.render_views(objs, os.path.join(out_dir, name), tint=tint, tint_mat=tint_mat, views=views, res=(res, int(res * 0.56)),
                           samples=int(opt.get("--spp", 48)), fmt=fmt)


if __name__ == "__main__":
    main(sys.argv[1:])
