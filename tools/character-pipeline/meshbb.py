import sys, bpy
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
for o in sorted((x for x in bpy.data.objects if x.type == "MESH"), key=lambda x: x.name):
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    if not ws: continue
    lo = [min(p[i] for p in ws) for i in range(3)]
    hi = [max(p[i] for p in ws) for i in range(3)]
    print("%-36s verts=%6d  size=(%.3f %.3f %.3f)  z=%.3f..%.3f  mats=%s"
          % (o.name, len(ws), hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2], lo[2], hi[2],
             [m.name for m in o.data.materials]))
