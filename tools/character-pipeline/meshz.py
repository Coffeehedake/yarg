import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
low=SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    if not len(o.data.vertices): 
        print("%-28s EMPTY" % o.name); continue
    ws=[o.matrix_world @ v.co for v in o.data.vertices]
    print("%-28s verts=%-7d z %.3f..%.3f  x %.3f..%.3f" % (o.name, len(o.data.vertices),
        min(w.z for w in ws), max(w.z for w in ws), min(w.x for w in ws), max(w.x for w in ws)))
print("DONE")
