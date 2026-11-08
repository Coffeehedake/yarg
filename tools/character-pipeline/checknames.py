import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
a = next(o for o in bpy.data.objects if o.type=="ARMATURE")
for n in ("mixamorig:Hips","mixamorig:Spine","mixamorig:Head","mixamorig:HeadTop_End",
          "mixamorig:LeftUpLeg","mixamorig:RightUpLeg","mixamorig:LeftHand",
          "mixamorig:RightHand","mixamorig:LeftFoot","mixamorig:LeftHandThumb1"):
    b = a.data.bones.get(n)
    if b is None: print("  %-28s MISSING" % n); continue
    h = a.matrix_world @ b.head_local
    print("  %-28s (%.3f, %.3f, %.3f)" % (n, h.x, h.y, h.z))
print("DONE")
