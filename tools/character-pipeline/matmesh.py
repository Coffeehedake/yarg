import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
low=SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    print("%-22s verts=%-7d mats=%s" % (o.name, len(o.data.vertices),
          [ms.material.name if ms.material else None for ms in o.material_slots]))
print("DONE")
