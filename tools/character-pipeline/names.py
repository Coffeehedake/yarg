import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
low=SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
elif low.endswith((".usd",".usdc",".usda",".usdz")): bpy.ops.wm.usd_import(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
for a in [o for o in bpy.data.objects if o.type=="ARMATURE"]:
    print("ARM", a.name, len(a.data.bones))
    print("  ", sorted(b.name for b in a.data.bones))
print("MESHES", [(o.name, len(o.data.vertices)) for o in bpy.data.objects if o.type=="MESH"])
print("DONE")
