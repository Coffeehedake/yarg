import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
low = SRC.lower()
bpy.ops.wm.read_homefile(use_empty=True)
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
elif low.endswith((".usd",".usdc",".usda",".usdz")): bpy.ops.wm.usd_import(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
deps = bpy.context.evaluated_depsgraph_get()
rows = []
for o in [x for x in bpy.data.objects if x.type=="MESH" and len(x.data.vertices)]:
    ev = o.evaluated_get(deps)
    ws = [ev.matrix_world @ v.co for v in ev.data.vertices]
    rows.append((o.name, min(w.z for w in ws), max(w.z for w in ws)))
lo = min(r[1] for r in rows); hi = max(r[2] for r in rows); span = hi - lo
for n, a, b in sorted(rows, key=lambda r: -r[2]):
    print("  %-26s %.4f .. %.4f" % (n, (a-lo)/span, (b-lo)/span))
print("DONE")
