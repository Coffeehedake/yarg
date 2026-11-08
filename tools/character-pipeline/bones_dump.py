import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
low = SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
for a in [o for o in bpy.data.objects if o.type=="ARMATURE"]:
    print("ARM", a.name, "mw_scale", tuple(round(v,4) for v in a.matrix_world.to_scale()))
    def walk(b, d=0):
        h = a.matrix_world @ b.head_local
        print("  "*d + "%s  head=(%.3f,%.3f,%.3f)" % (b.name, h.x, h.y, h.z))
        for c in b.children: walk(c, d+1)
    for b in a.data.bones:
        if b.parent is None: walk(b)
for o in [o for o in bpy.data.objects if o.type=="MESH"]:
    print("MESH", o.name, len(o.data.vertices), [m.name for m in o.data.materials])
print("DONE")
