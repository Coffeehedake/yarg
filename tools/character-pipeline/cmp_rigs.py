import sys, bpy
from mathutils import Vector
A, B = sys.argv[sys.argv.index("--")+1:][:2]
def load(path):
    low=path.lower()
    if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=path)
    elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=path)
    elif low.endswith((".usd",".usdc",".usda",".usdz")): bpy.ops.wm.usd_import(filepath=path)
    else: bpy.ops.import_scene.fbx(filepath=path)
for tag, path in (("TGT", A), ("DONOR", B)):
    bpy.ops.wm.read_homefile(use_empty=True)
    load(path)
    arm = next(o for o in bpy.data.objects if o.type=="ARMATURE")
    pts = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
    zs=[p.z for p in pts.values()]; xs=[p.x for p in pts.values()]
    print("%s %s: %d bones  z %.3f..%.3f  x %.3f..%.3f  mw_scale=%s" % (
        tag, arm.name, len(pts), min(zs), max(zs), min(xs), max(xs),
        tuple(round(v,4) for v in arm.matrix_world.to_scale())))
    root = [b for b in arm.data.bones if b.parent is None]
    def depth_counts(b, d=0, acc=None):
        acc = acc if acc is not None else {}
        acc[d] = acc.get(d,0)+1
        for c in b.children: depth_counts(c, d+1, acc)
        return acc
    acc={}
    for r in root: depth_counts(r, 0, acc)
    print("   roots=%s depth histogram=%s" % ([r.name for r in root], sorted(acc.items())))
    # tallest 3 bones
    top = sorted(pts.items(), key=lambda kv: -kv[1].z)[:3]
    print("   highest: %s" % [(n, tuple(round(v,3) for v in p)) for n,p in top])
print("DONE")
