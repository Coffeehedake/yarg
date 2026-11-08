import sys, math, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
a = next(o for o in bpy.data.objects if o.type=="ARMATURE")
bpy.context.view_layer.update()
def ang(v):
    return math.degrees(math.atan2(math.hypot(v.y, v.z), abs(v.x)))
for side in ("L","R"):
    up = a.pose.bones.get("upper_arm.%s"%side)
    lo = a.pose.bones.get("forearm.%s"%side)
    hd = a.pose.bones.get("hand.%s"%side)
    if not (up and lo and hd): print("missing", side); continue
    s, e, w = up.head, lo.head, hd.head
    el = (e-s); fa = (w-e)
    bend = math.degrees((el).angle(fa)) if el.length>1e-9 and fa.length>1e-9 else 0.0
    print("  POSE %s: shoulder->elbow %.1f off X | elbow->wrist %.1f off X | elbow BEND %.1f deg"
          % (side, ang(el), ang(fa), bend))
    rs, re_, rw = a.data.bones["upper_arm.%s"%side].head_local, a.data.bones["forearm.%s"%side].head_local, a.data.bones["hand.%s"%side].head_local
    rel, rfa = (re_-rs), (rw-re_)
    print("  REST %s: shoulder->elbow %.1f off X | elbow->wrist %.1f off X | elbow BEND %.1f deg"
          % (side, ang(rel), ang(rfa),
             math.degrees(rel.angle(rfa)) if rel.length>1e-9 and rfa.length>1e-9 else 0.0))
print("DONE")
