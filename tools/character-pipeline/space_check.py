import sys, bpy
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
def bbox(pts):
    lo = Vector((1e18,)*3); hi = Vector((-1e18,)*3)
    for p in pts:
        for i in range(3): lo[i]=min(lo[i],p[i]); hi[i]=max(hi[i],p[i])
    return lo, hi
for label, mw in (("as-imported", arm.matrix_world.copy()), ("aligned-to-mesh", None)):
    me = next(o for o in bpy.data.objects if o.type=="MESH")
    if mw is None: mw = me.matrix_world.copy()
    pts = []
    for b in arm.data.bones:
        pts.append(mw @ b.head_local); pts.append(mw @ b.tail_local)
    lo,hi = bbox(pts)
    print("%-16s bones  lo=(%.3f,%.3f,%.3f) hi=(%.3f,%.3f,%.3f)" % ((label,)+tuple(lo)+tuple(hi)))
me = next(o for o in bpy.data.objects if o.type=="MESH")
lo,hi = bbox([me.matrix_world @ v.co for v in me.data.vertices])
print("%-16s mesh   lo=(%.3f,%.3f,%.3f) hi=(%.3f,%.3f,%.3f)" % (("world",)+tuple(lo)+tuple(hi)))
print("DONE")
