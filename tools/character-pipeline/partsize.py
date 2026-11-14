"""How big is each material's geometry, as a fraction of character height?

A centroid says where a part is and nothing about whether it was scaled. Both
of Gadget Hackwrench's faults show up here: a cluster three times too large and
one sitting at the throat have very different numbers, and a size is far less
sensitive to topology than a centroid -- subdivision shrinks a bounding box by
a few percent, not by a factor.

Argv: <file> [material-substring ...]
"""
import sys

import bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
if SRC.lower().endswith(".vrm"):
    bpy.ops.wm.read_homefile(use_empty=True)
    if bpy.ops.import_scene.vrm(filepath=SRC) != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import failed")
else:
    bpy.ops.wm.open_mainfile(filepath=SRC)
for o in bpy.data.objects:
    if o.name.startswith("WGT-") or o.name == "smd_bone_vis":
        o.hide_render = True
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

hz = []
for ob in bpy.data.objects:
    if ob.type == "MESH" and not ob.hide_render:
        hz += [(ob.matrix_world @ Vector(c)).z for c in ob.bound_box]
H = max(hz) - min(hz)
print("character height %.4f" % H)

SUBS = (sys.argv[sys.argv.index("--") + 2:] or ["teeth", "eye", "body"])
for sub in SUBS:
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    n = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.hide_render:
            continue
        idx = [i for i, sl in enumerate(ob.material_slots)
               if sl.material and sub in sl.material.name.lower()]
        if not idx:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        vs = set()
        for p in me.polygons:
            if p.material_index in idx:
                vs.update(p.vertices)
        for i in vs:
            w = ev.matrix_world @ me.vertices[i].co
            lo = Vector((min(lo[k], w[k]) for k in range(3)))
            hi = Vector((max(hi[k], w[k]) for k in range(3)))
            n += 1
        ev.to_mesh_clear()
    if not n:
        print("  %-6s absent" % sub)
        continue
    d = hi - lo
    c = (lo + hi) / 2.0
    print("  %-6s %6d verts  size=(%.4f,%.4f,%.4f)  as %% of height: "
          "(%.2f%%,%.2f%%,%.2f%%)  centre z = %.1f%% of height"
          % (sub, n, d.x, d.y, d.z,
             100 * d.x / H, 100 * d.y / H, 100 * d.z / H,
             100 * (c.z - min(hz)) / H))
