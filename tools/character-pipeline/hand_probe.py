import sys, bpy
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
me = max((o for o in bpy.data.objects if o.type=="MESH"), key=lambda o: len(o.data.vertices))
idx = {g.index: g.name for g in me.vertex_groups}
for hand in ("Bip01 L Hand", "Bip01 R Hand"):
    hb = arm.data.bones.get(hand)
    if hb is None:
        cand = [b.name for b in arm.data.bones if "hand" in b.name.lower()]
        print("hand bone not found; candidates:", cand); continue
    n = 0; beyond = 0
    hw = arm.matrix_world @ hb.head_local
    tw = arm.matrix_world @ hb.tail_local
    axis = (tw - hw).normalized()
    for v in me.data.vertices:
        for g in v.groups:
            if idx.get(g.group) == hand and g.weight > 0.4:
                n += 1
                p = me.matrix_world @ v.co
                if (p - hw).dot(axis) > (tw - hw).length * 0.6:
                    beyond += 1
                break
    print("%-14s verts weighted>0.4: %-4d  beyond 60%% of bone: %d  bone_len=%.4f"
          % (hand, n, beyond, hb.length))
print("total mesh verts", len(me.data.vertices))
print("DONE")
