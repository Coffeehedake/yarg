import sys, bpy
from mathutils import Vector, Matrix
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
me  = next(o for o in bpy.data.objects if o.type=="MESH")
V = [me.matrix_world @ v.co for v in me.data.vertices]
lo = Vector((min(p.x for p in V), min(p.y for p in V), min(p.z for p in V)))
hi = Vector((max(p.x for p in V), max(p.y for p in V), max(p.z for p in V)))
print("mesh bbox lo=(%.3f,%.3f,%.3f) hi=(%.3f,%.3f,%.3f)" % (tuple(lo)+tuple(hi)))
S = me.matrix_world.to_scale().x
A = arm.matrix_world.copy()
heads = {b.name: A @ b.head_local for b in arm.data.bones}
blo = min(h.z for h in heads.values())
bhi = max(h.z for h in heads.values())
print("bone world z span %.3f .. %.3f (S=%.5f -> %.3f m)" % (blo, bhi, 0.0254, (bhi-blo)*0.0254))

for label, M in (
        ("scale-only", Matrix.Diagonal((S,S,S,1.0))),
        ("floor-aligned", Matrix.Translation((0,0,lo.z - blo*S)) @ Matrix.Diagonal((S,S,S,1.0))),
        ("fit-height", Matrix.Translation((0,0,lo.z - blo*((hi.z-lo.z)/(bhi-blo)))) @ Matrix.Diagonal(((hi.z-lo.z)/(bhi-blo),)*3 + (1.0,))),
    ):
    print("--", label)
    for n in ("Hips","Head","Hand_L","Hand_R","Foot_L","Toe_L","Nose"):
        if n not in heads: continue
        p = M @ heads[n]
        d = min((p - q).length for q in V)
        print("   %-8s at (%.3f,%.3f,%.3f)  nearest vertex %.3f m" % (n, p.x, p.y, p.z, d))
print("DONE")
