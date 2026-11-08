import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
a = next(o for o in bpy.data.objects if o.type=="ARMATURE")
bpy.context.view_layer.update()
n = 0
for pb in a.pose.bones:
    s = pb.matrix_basis.to_scale()
    if any(abs(v-1.0) > 1e-4 for v in s):
        n += 1
        if n <= 8: print("  scaled %-14s basis_scale=%s" % (pb.name, tuple(round(v,4) for v in s)))
print("BONES WITH POSE SCALE:", n, "of", len(a.pose.bones))
print("armature object scale:", tuple(round(v,4) for v in a.matrix_world.to_scale()))
print("DONE")
