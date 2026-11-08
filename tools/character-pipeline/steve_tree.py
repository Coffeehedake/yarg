import sys, bpy
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[sys.argv.index("--") + 1])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mw = arm.matrix_world
def show(b, d=0):
    h = mw @ b.head_local; t = mw @ b.tail_local
    print("%s%-14s head=(%+7.2f,%+7.2f,%+7.2f) tail=(%+7.2f,%+7.2f,%+7.2f) len=%.2f"
          % ("  " * d, b.name, h.x, h.y, h.z, t.x, t.y, t.z, b.length))
    for c in b.children: show(c, d + 1)
for b in arm.data.bones:
    if b.parent is None: show(b)
print("DONE")
