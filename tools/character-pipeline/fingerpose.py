"""Per-joint bend in every finger chain, REST vs POSE, both hands.

The point is the LEFT/RIGHT comparison: one relaxed hand is the control that
says whether the other is really clenched or whether that is just how the model
holds its hands.
"""
import sys, math, bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
low = SRC.lower()
bpy.ops.wm.read_homefile(use_empty=True)
if low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.usd_import(filepath=SRC)
elif low.endswith(".vrm"):
    bpy.ops.import_scene.vrm(filepath=SRC)
else:
    bpy.ops.import_scene.fbx(filepath=SRC)

arm = max((o for o in bpy.data.objects if o.type == "ARMATURE"),
          key=lambda o: len(o.data.bones))
bpy.context.view_layer.update()
print("armature %r bones=%d" % (arm.name, len(arm.data.bones)))

FING = ("thumb", "index", "middle", "ring", "pinky", "little", "finger")
names = [b.name for b in arm.data.bones]


def side(n):
    l = n.lower()
    if l.endswith(".l") or "_l_" in l or "left" in l or l.endswith("_l"):
        return "L"
    if l.endswith(".r") or "_r_" in l or "right" in l or l.endswith("_r"):
        return "R"
    return "?"


def chains():
    """Root finger bones (a finger bone whose parent is not one), then walk down."""
    out = []
    for b in arm.data.bones:
        if not any(w in b.name.lower() for w in FING):
            continue
        if b.parent is not None and any(w in b.parent.name.lower() for w in FING):
            continue
        ch, cur = [b.name], b
        while True:
            kids = [c for c in cur.children if any(w in c.name.lower() for w in FING)]
            if not kids:
                break
            kids.sort(key=lambda x: -x.length)
            ch.append(kids[0].name)
            cur = kids[0]
        if len(ch) >= 2:
            out.append(ch)
    return out


def dirs(ch, pose):
    out = []
    for n in ch:
        if pose:
            pb = arm.pose.bones[n]
            v = pb.tail - pb.head
        else:
            db = arm.data.bones[n]
            v = db.tail_local - db.head_local
        out.append(v.normalized() if v.length > 1e-9 else Vector((0, 0, 0)))
    return out


def curl(ds):
    """Total bend down the chain, in degrees."""
    t = 0.0
    for a, b in zip(ds, ds[1:]):
        if a.length > 0 and b.length > 0:
            t += math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))
    return t


rows = []
for ch in chains():
    rows.append((side(ch[0]), ch[0], len(ch),
                 curl(dirs(ch, False)), curl(dirs(ch, True))))
rows.sort()
print("%-4s %-28s %5s %10s %10s %10s" % ("side", "chain root", "bones",
                                         "REST curl", "POSE curl", "delta"))
for s, n, k, r, p in rows:
    print("%-4s %-28s %5d %9.1f %9.1f %9.1f" % (s, n, k, r, p, p - r))
for s in ("L", "R"):
    rs = [x for x in rows if x[0] == s]
    if rs:
        print("  %s hand: mean REST curl %.1f, mean POSE curl %.1f over %d chains"
              % (s, sum(x[3] for x in rs) / len(rs),
                 sum(x[4] for x in rs) / len(rs), len(rs)))
print("DONE")
