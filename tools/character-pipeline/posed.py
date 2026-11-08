import sys, bpy
from mathutils import Matrix
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
a = next(o for o in bpy.data.objects if o.type=="ARMATURE")
n = 0
for pb in a.pose.bones:
    if (pb.matrix_basis - Matrix.Identity(4)).median_scale if False else any(
            abs(pb.matrix_basis[i][j] - (1.0 if i==j else 0.0)) > 1e-5
            for i in range(4) for j in range(4)):
        n += 1
        if n <= 8:
            l,r,s = pb.matrix_basis.decompose()
            print("  posed %-14s loc=%s rotW=%.4f" % (pb.name, tuple(round(v,4) for v in l), r.w))
print("POSED BONES:", n, "of", len(a.pose.bones))
print("DONE")
