"""Delete the vertices a named set of bones controls, so what is underneath can
be looked at. Used to check whether a figure hidden by a spread cape is intact."""
import re
import sys

import bmesh
import bpy

SRC, PATTERN, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
bpy.ops.wm.open_mainfile(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
hit = {b.name for b in arm.data.bones if re.search(PATTERN, b.name, re.I)}
print("bones matching %r: %d" % (PATTERN, len(hit)))

for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    gi = {g.index for g in o.vertex_groups if g.name in hit}
    if not gi:
        continue
    doomed = [v.index for v in o.data.vertices
              if sum(g.weight for g in v.groups if g.group in gi) > 0.5]
    print("  %s: removing %d of %d verts" % (o.name, len(doomed), len(o.data.vertices)))
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in doomed], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()

bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
