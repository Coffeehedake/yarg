import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
a = next(o for o in bpy.data.objects if o.type=="ARMATURE")
bpy.context.view_layer.update()
print("arm.matrix_world scale:", tuple(round(v,5) for v in a.matrix_world.to_scale()))
for n in ("spine", "spine.004", "spine.005", "hand.L"):
    pb = a.pose.bones.get(n); rb = a.data.bones.get(n)
    if not pb or not rb: continue
    D = pb.matrix @ rb.matrix_local.inverted()
    l, r, sc = D.decompose()
    bl, br, bs = pb.matrix_basis.decompose()
    print("  %-10s deform scale=%s  loc=%s | basis scale=%s len=%.4f"
          % (n, tuple(round(v,4) for v in sc), tuple(round(v,3) for v in l),
             tuple(round(v,4) for v in bs), rb.length))
print("DONE")
