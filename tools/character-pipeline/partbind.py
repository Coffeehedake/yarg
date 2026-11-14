"""Which bones actually drive one material's geometry in a finished build?

Separates two faults that look identical in a render: geometry that is in
the wrong place, and geometry that is bound to nothing and therefore cannot
follow the body at all. The exporter invents a 'neutral_bone' for the
second, so it never looks unbound in the file -- it just never moves.

Argv: <file.vrm> [material-substring]
"""
import sys

import bpy

a = sys.argv[sys.argv.index("--") + 1:]
SRC = a[0]
SUB = (a[1] if len(a) > 1 else "teeth").lower()
bpy.ops.wm.read_homefile(use_empty=True)
if bpy.ops.import_scene.vrm(filepath=SRC) != {"FINISHED"}:
    raise SystemExit("ABORT: vrm import failed")
arm = max((o for o in bpy.data.objects if o.type == "ARMATURE"),
          key=lambda o: len(o.data.bones))
print("bones in the build: %d; lip bones: %s"
      % (len(arm.data.bones),
         [b.name for b in arm.data.bones if "lip" in b.name.lower()][:10]))
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    ti = [i for i, sl in enumerate(ob.material_slots)
          if sl.material and SUB in sl.material.name.lower()]
    if not ti:
        continue
    gn = {g.index: g.name for g in ob.vertex_groups}
    tv = set()
    for p in ob.data.polygons:
        if p.material_index in ti:
            tv.update(p.vertices)
    tally, loose = {}, 0
    for i in tv:
        gs = [(g.weight, gn.get(g.group)) for g in ob.data.vertices[i].groups
              if g.weight > 1e-4]
        if not gs:
            loose += 1
            continue
        tally[max(gs)[1]] = tally.get(max(gs)[1], 0) + 1
    print("%s: %d verts, %d carry NO weight" % (ob.name, len(tv), loose))
    for n, c in sorted(tally.items(), key=lambda t: -t[1])[:6]:
        live = n in arm.data.bones
        print("   %-24s %5d verts   bone present in the rig: %s" % (n, c, live))
