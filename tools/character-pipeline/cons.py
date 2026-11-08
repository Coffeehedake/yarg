import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    ws=[o.matrix_world @ v.co for v in o.data.vertices] if len(o.data.vertices) else []
    bb = ("z %.2f..%.2f" % (min(w.z for w in ws), max(w.z for w in ws))) if ws else "EMPTY"
    cs = [(c.type, c.target.name if c.target else None, getattr(c,'subtarget','')) for c in o.constraints]
    print("%-24s verts=%-7d %s  cons=%s" % (o.name, len(o.data.vertices), bb, cs))
print("DONE")
