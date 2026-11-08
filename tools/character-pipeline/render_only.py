import sys, bpy, re
SRC, KEEP, OUT = sys.argv[sys.argv.index("--")+1:][:3]
bpy.ops.wm.read_homefile(use_empty=True)
low=SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
elif low.endswith((".usd",".usdc",".usda",".usdz")): bpy.ops.wm.usd_import(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
for o in list(bpy.data.objects):
    if o.type=="MESH" and not re.search(KEEP, o.name, re.I):
        bpy.data.objects.remove(o, do_unlink=True)
print("kept:", [o.name for o in bpy.data.objects if o.type=="MESH"])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
