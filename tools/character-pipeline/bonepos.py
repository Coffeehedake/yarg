import sys, bpy
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
a = next(x for x in bpy.data.objects if x.type=="ARMATURE")
o = next(x for x in bpy.data.objects if x.type=="MESH")
V=[o.matrix_world @ v.co for v in o.data.vertices]
print("mesh world z %.3f..%.3f  x %.3f..%.3f" % (min(v.z for v in V), max(v.z for v in V), min(v.x for v in V), max(v.x for v in V)))
print("arm mw scale", tuple(round(v,5) for v in a.matrix_world.to_scale()))
for n in ("Hips","Spine","Spine1","Head","UpperArm_L","Hand_L","Thigh_L","Foot_L"):
    b=a.data.bones.get(n)
    if b: 
        h=a.matrix_world @ b.head_local
        print("  %-11s head=(%.3f,%.3f,%.3f) len=%.4f" % (n,h.x,h.y,h.z,b.length))
print("DONE")
