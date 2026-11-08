"""Which UV layer actually matches the texture?

Wires one image onto a mesh and reports, per UV layer, how much of the 0..1
square the coordinates occupy. A layer whose UVs all sit in one corner samples a
single texel and the surface renders as flat colour."""
import sys

import bpy

SRC, WANT, TEX = sys.argv[sys.argv.index("--") + 1:][:3]
bpy.ops.wm.read_homefile(use_empty=True)
low = SRC.lower()
if low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.usd_import(filepath=SRC)
else:
    bpy.ops.import_scene.fbx(filepath=SRC)

for o in bpy.data.objects:
    if o.type != "MESH" or WANT.lower() not in o.name.lower():
        continue
    me = o.data
    print("MESH %s  verts=%d" % (o.name, len(me.vertices)))
    for layer in me.uv_layers:
        us = [d.uv[0] for d in layer.data]
        vs = [d.uv[1] for d in layer.data]
        if not us:
            continue
        print("   UV %-12s active=%-5s render=%-5s  u=%.3f..%.3f  v=%.3f..%.3f  spread=%.3f"
              % (layer.name, layer.active, layer.active_render,
                 min(us), max(us), min(vs), max(vs),
                 (max(us) - min(us)) * (max(vs) - min(vs))))
print("DONE")
