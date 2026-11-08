"""Measure arm straightness in REST and POSE for any rig, by finding the arm
chain from bone names rather than assuming one naming convention."""
import sys, math, bpy

SRC = sys.argv[sys.argv.index("--") + 1]
low = SRC.lower()
bpy.ops.wm.read_homefile(use_empty=True)
if low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.usd_import(filepath=SRC)
elif low.endswith(".vrm"):
    bpy.ops.import_scene.vrm(filepath=SRC)
elif low.endswith((".glb", ".gltf")):
    bpy.ops.import_scene.gltf(filepath=SRC)
else:
    bpy.ops.import_scene.fbx(filepath=SRC)

a = max((o for o in bpy.data.objects if o.type == "ARMATURE"),
        key=lambda o: len(o.data.bones))
bpy.context.view_layer.update()
names = [b.name for b in a.data.bones]
print("armature %r  bones=%d" % (a.name, len(names)))


def pick(*words):
    """The bone whose name carries every word, shortest name first."""
    hits = [n for n in names if all(w in n.lower() for w in words)]
    hits.sort(key=len)
    return hits[0] if hits else None


def ang(v):
    return math.degrees(math.atan2(math.hypot(v.y, v.z), abs(v.x)))


UP = ("upperarm", "upper_arm", "uparm", "arm", "shldr", "shoulder")
LO = ("forearm", "fore_arm", "lowarm", "lower_arm", "elbow")
HD = ("hand", "wrist")
for side, tags in (("L", ("left", "_l", ".l", "l_")), ("R", ("right", "_r", ".r", "r_"))):
    got = {}
    for role, cands in (("up", UP), ("lo", LO), ("hd", HD)):
        for c in cands:
            for t in tags:
                n = pick(c, t)
                if n and n not in got.values():
                    got[role] = n
                    break
            if role in got:
                break
    if len(got) < 3:
        print("  %s: could not find a 3-bone arm chain, got %s" % (side, got))
        continue
    print("  %s chain: %s -> %s -> %s" % (side, got["up"], got["lo"], got["hd"]))
    pb = a.pose.bones
    s, e, w = pb[got["up"]].head, pb[got["lo"]].head, pb[got["hd"]].head
    el, fa = (e - s), (w - e)
    bend = math.degrees(el.angle(fa)) if el.length > 1e-9 and fa.length > 1e-9 else 0.0
    print("    POSE: shoulder->elbow %.1f off X | elbow->wrist %.1f off X | elbow BEND %.1f"
          % (ang(el), ang(fa), bend))
    db = a.data.bones
    rs, re_, rw = db[got["up"]].head_local, db[got["lo"]].head_local, db[got["hd"]].head_local
    rel, rfa = (re_ - rs), (rw - re_)
    rbend = math.degrees(rel.angle(rfa)) if rel.length > 1e-9 and rfa.length > 1e-9 else 0.0
    print("    REST: shoulder->elbow %.1f off X | elbow->wrist %.1f off X | elbow BEND %.1f"
          % (ang(rel), ang(rfa), rbend))
print("DONE")
