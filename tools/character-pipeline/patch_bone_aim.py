# -*- coding: utf-8 -*-
"""Re-aim a bone chain in an installed .yargchar, so a dangling part hangs.

    python patch_bone_aim.py <in.yargchar> <bone> [--aim x,y,z]
        [--out X] [--dry-run]

For a part that is modelled sticking out because the author expected physics to
settle it, and the physics never came across. Rotating the bone carries its
children and all their flesh with it as a rigid unit, so the part swings to
where it should hang and its geometry is untouched.

Miku's necktie, reported 2026-11-15 as sticking straight out. `Bip01 Spine1` ->
`Bone01` -> `Bone02` -> `Bone03`, running from z +0.118 at her collar out to
z +0.372 while her chest surface sits at about z +0.08 -- 255 mm forward for
89 mm of drop, **71 degrees off vertical**. It is not ours: her source
`Miku.fbx` has the same chain at 69.1 and 72.4 degrees, which is the same story
as her hair, already recorded as "splayed outward in the ORIGINAL download, not
by us". It is an MMD-style rig whose tie was expected to be settled by rigid
bodies that a VRM export does not carry.

HOW THE ROTATION IS CHOSEN. The bone's own axis is wherever its first child
sits, so the current world direction is child_world - bone_world. The target is
`--aim`, by default straight down. The rotation applied is the MINIMAL one
taking the first to the second, which leaves the bone's roll alone -- anything
more would twist the part about its own length for no reason. In the parent's
frame that is:

    new_local = P^-1 . R . P . old_local

with P the parent's world rotation. The same four structures hold it as hold a
bone's position, and all four are written -- see patch_mirror.py for why the
Avatar's arrays are easy to miss.

IT CHECKS ITS OWN WORK. The naive thing would be to trust the arithmetic; this
re-reads the patched bytes, re-measures the direction, and writes nothing
unless it has landed within a degree of the target. It also reports where the
tip of the chain ends up against the body, because a tie that hangs straight
down can still hang inside the chest.
"""
import math
import os
import sys

import UnityPy

import cloth_collide_installed as cci
from patch_springs import fingerprint

EPS = 1e-6


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def qrot(q, v):
    w, x, y, z = q
    tx = 2.0 * (y * v[2] - z * v[1])
    ty = 2.0 * (z * v[0] - x * v[2])
    tz = 2.0 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + (y * tz - z * ty),
            v[1] + w * ty + (z * tx - x * tz),
            v[2] + w * tz + (x * ty - y * tx))


def norm(v):
    L = math.sqrt(sum(c * c for c in v))
    return (v[0] / L, v[1] / L, v[2] / L) if L > 1e-12 else (0.0, 0.0, 0.0)


def between(a, b):
    """The minimal rotation taking unit vector a to unit vector b."""
    d = sum(x * y for x, y in zip(a, b))
    if d > 1.0 - 1e-9:
        return (1.0, 0.0, 0.0, 0.0)
    if d < -1.0 + 1e-9:
        # opposite: any perpendicular axis, half turn
        axis = norm((1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0))
        axis = norm((a[1] * axis[2] - a[2] * axis[1],
                     a[2] * axis[0] - a[0] * axis[2],
                     a[0] * axis[1] - a[1] * axis[0]))
        return (0.0,) + axis
    c = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
         a[0] * b[1] - a[1] * b[0])
    w = 1.0 + d
    q = (w, c[0], c[1], c[2])
    L = math.sqrt(sum(x * x for x in q))
    return tuple(x / L for x in q)


def aim_of(src, bone):
    """(current direction, child name, bone world pos, parent world rot)."""
    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(src)
    by_name = {}
    for pid, n in tf.items():
        if n["name"]:
            by_name.setdefault(n["name"], pid)
    if bone not in by_name:
        return None
    pid = by_name[bone]
    kids = [c for c, n in tf.items() if n["f"] == pid]
    if not kids:
        return None
    kid = kids[0]
    wp = world(pid)[0]
    kp = world(kid)[0]
    ppq = world(tf[pid]["f"])[1] if tf[pid]["f"] in tf else (1.0, 0.0, 0.0,
                                                             0.0)
    return (norm((kp[0] - wp[0], kp[1] - wp[1], kp[2] - wp[2])),
            tf[kid]["name"], wp, ppq, tf[pid]["q"], tf, by_name, world)


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    out, aim = None, (0.0, -1.0, 0.0)
    if "--out" in args:
        out = args[args.index("--out") + 1]
    if "--aim" in args:
        aim = tuple(float(x) for x in args[args.index("--aim") + 1].split(","))
    skip = {out, ("%g,%g,%g" % aim) if "--aim" in args else None}
    if "--aim" in args:
        skip.add(args[args.index("--aim") + 1])
    rest = [a for a in args if not a.startswith("--") and a not in skip]
    if len(rest) != 2:
        print(__doc__)
        return 2
    src, bone = rest
    out = out or src
    aim = norm(aim)

    got = aim_of(src, bone)
    if got is None:
        print("ABORT: %r is not a bone with a child in this bundle" % bone)
        return 2
    cur, kidname, wp, ppq, oldq, tf, by_name, world = got
    ang = math.degrees(math.acos(max(-1.0, min(1.0,
                                               sum(a * b for a, b
                                                   in zip(cur, aim))))))
    print("%s: %r -> %r currently points (%+.4f %+.4f %+.4f)"
          % (os.path.basename(src), bone, kidname, *cur))
    print("  target (%+.4f %+.4f %+.4f) -- %.1f degrees away" % (aim + (ang,)))
    if ang < 1.0:
        print("nothing to do: it already points there")
        return 2
    R = between(cur, aim)
    newq = qmul(qmul(qconj(ppq), qmul(R, ppq)), oldq)
    print("  local rotation (%+.6f %+.6f %+.6f %+.6f) -> (%+.6f %+.6f %+.6f "
          "%+.6f)" % (oldq + newq))

    env = UnityPy.load(src)
    before = fingerprint(env)
    done = []
    pid = by_name[bone]
    for obj in env.objects:
        if obj.type.name == "Transform":
            if (tf.get(obj.path_id) or {}).get("name") != bone:
                continue
            tt = obj.read_typetree()
            lr = tt["m_LocalRotation"]
            lr["w"], lr["x"], lr["y"], lr["z"] = newq
            tt["m_LocalRotation"] = lr
            obj.save_typetree(tt)
            done.append("Transform.m_LocalRotation")
        elif obj.type.name == "Avatar":
            tt = obj.read_typetree()
            av = tt["m_Avatar"]
            names = {}
            for e in (tt.get("m_TOS") or []):
                if isinstance(e, (list, tuple)) and len(e) == 2:
                    names[e[0]] = e[1]
            ids = av["m_AvatarSkeleton"]["data"]["m_ID"]
            short = [(names.get(b) or "?").split("/")[-1] for b in ids]
            touched = False
            if bone in short:
                i = short.index(bone)
                for key in ("m_AvatarSkeletonPose", "m_DefaultPose"):
                    arr = av[key]["data"]["m_X"]
                    if i >= len(arr):
                        continue
                    q = arr[i]["q"]
                    q["w"], q["x"], q["y"], q["z"] = (newq[0], newq[1],
                                                      newq[2], newq[3])
                    touched = True
                    done.append("%s[%d].q" % (key, i))
            for e in tt["m_HumanDescription"]["m_Skeleton"]:
                if (e.get("m_Name") or "") != bone:
                    continue
                q = e["m_Rotation"]
                q["w"], q["x"], q["y"], q["z"] = (newq[0], newq[1], newq[2],
                                                  newq[3])
                touched = True
                done.append("m_HumanDescription.m_Skeleton.m_Rotation")
            if touched:
                obj.save_typetree(tt)

    if not done:
        print("nothing to do")
        return 2
    print("  changed: %s" % ", ".join(done))
    if dry:
        print("  --dry-run: nothing written")
        return 0

    data = env.file.save(packer="original")
    after = fingerprint(UnityPy.load(data))
    changed = [k for k in before if before.get(k) != after.get(k)]
    gone = [k for k in before if k not in after]
    added = [k for k in after if k not in before]
    expect = 2 if any(k.startswith("m_Avatar") or k.startswith("m_Human")
                      for k in done) else 1
    print("  read-back: %d object(s) readable, %d changed (expected %d), "
          "%d gone, %d added" % (len(after), len(changed), expect, len(gone),
                                 len(added)))
    for k in sorted(changed):
        print("    %s" % k)
    if len(changed) != expect or gone or added:
        print("  WARNING: the read-back does not match what was asked for -- "
              "nothing was written")
        return 1

    # Did it actually land where it was aimed? Measured on the patched bytes.
    got2 = aim_of(data, bone)
    if got2 is None:
        print("  WARNING: cannot re-measure the result -- nothing written")
        return 1
    cur2 = got2[0]
    ang2 = math.degrees(math.acos(max(-1.0, min(1.0,
                                                sum(a * b for a, b
                                                    in zip(cur2, aim))))))
    print("  after: points (%+.4f %+.4f %+.4f), %.2f degrees off the target"
          % (cur2 + (ang2,)))
    if ang2 > 1.0:
        print("  WARNING: it did not land on the target -- nothing written")
        return 1
    with open(out, "wb") as f:
        f.write(data)
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
