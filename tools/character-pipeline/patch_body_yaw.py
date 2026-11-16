# -*- coding: utf-8 -*-
"""patch_body_yaw.py <yargchar> [--yaw D] [--out X] [--dry-run]

Turn a character who was built standing at an angle to face front.

THE FAULT THIS IS FOR IS NOT A LIMB. Spartan Mark V was reported twice for a
leg sticking out at one hip, and both of his legs are exact mirrors of each
other -- bones to 0.00 mm in their shared parent's frame, flesh to a median of
0.0 mm in the spine's frame. Both statements are true together because the
whole character is TURNED: a stance symmetric about the body's own midline
projects asymmetrically when that midline is not facing the camera, and the hip
rotated toward the viewer is the one that looks like it sticks out.

His source says where it came from. `MkVSKETCHFAB.blend` is a perfect mirror
about a plane 20.00 degrees off the world x axis -- the model was simply built
at an angle -- and nothing in the pipeline ever straightened him. He ships
standing 20 degrees off, every left-right line agreeing to two decimals.

MEASURING IT, AND WHY SEVERAL LINES. The yaw is read from lines that are
left-right by construction: hips, shoulders, knees, feet. If the body is
turned, all of them agree. If one LIMB is displaced instead, they disagree --
and then turning the character is the wrong operation and this refuses to do
it. That disagreement is the whole guard, which is why one line is not enough
and why a spread is reported rather than an average alone. The hands are left
out: they are the end of the longest chain and carry the model's own pose, so
they disagree on a character who is perfectly square (Spartan reads +6.30 on
the hands against +20.00 on everything else, because his arms are posed).

WHAT IT WRITES. The humanoid root bone's rest rotation, in the four structures
that hold it -- Transform.m_LocalRotation, the Avatar's m_AvatarSkeletonPose
and m_DefaultPose, and m_HumanDescription.m_Skeleton -- exactly as
patch_bone_aim.py does. Every other bone descends from that one and follows,
and the meshes are skinned, so they follow the bones. Nothing else is touched.
Then the written BYTES are re-measured and the file is kept only if the yaw
has actually gone to zero.
"""
import math
import os
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloth_collide_installed import read                         # noqa: E402

# Lines that are left-right by construction. Hands are deliberately absent:
# see the note above.
LINES = [("hips", ("thigh.L", "thigh.R"), ("LeftUpperLeg", "RightUpperLeg")),
         ("shoulders", ("upper_arm.L", "upper_arm.R"),
          ("LeftUpperArm", "RightUpperArm")),
         ("knees", ("shin.L", "shin.R"), ("LeftLowerLeg", "RightLowerLeg")),
         ("feet", ("foot.L", "foot.R"), ("LeftFoot", "RightFoot"))]

SPREAD_MAX = 5.0        # degrees; above this the lines disagree
YAW_MIN = 2.0           # degrees; below this there is nothing to fix
RESIDUAL_MAX = 0.5      # degrees; the check on the written file


def die(msg):
    raise SystemExit("ABORT: %s" % msg)


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def measure(path_or_bytes):
    """(yaw per line, bone lookup, humanoid map, world fn, tf)."""
    human, tf, go_tf, springs, joints, colliders, groups, world = \
        read(path_or_bytes)
    by = {}
    for pid, n in tf.items():
        if n["name"]:
            by.setdefault(n["name"], pid)
    out = []
    for label, names, hum in LINES:
        a = by.get(names[0]) or by.get(human.get(hum[0], ""))
        b = by.get(names[1]) or by.get(human.get(hum[1], ""))
        if a is None or b is None:
            continue
        pa, pb = world(a)[0], world(b)[0]
        dx, dz = pb[0] - pa[0], pb[2] - pa[2]
        if math.hypot(dx, dz) < 1e-4:
            continue
        out.append((label, math.degrees(math.atan2(dz, dx))))
    return out, by, human, world, tf


def main():
    argv = sys.argv[1:]
    src, out, dry, want = None, None, False, None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dry-run":
            dry = True
        elif a in ("--out", "--yaw"):
            i += 1
            if i >= len(argv):
                die("%s needs a value" % a)
            if a == "--out":
                out = argv[i]
            else:
                want = float(argv[i])
        elif a.startswith("--"):
            die("unknown flag %r" % a)
        elif src is None:
            src = a
        else:
            die("unexpected argument %r" % a)
        i += 1
    if src is None:
        die("usage: patch_body_yaw.py <yargchar> [--yaw D] [--out X] "
            "[--dry-run]")
    out = out or src

    lines, by, human, world, tf = measure(src)
    if len(lines) < 2:
        die("only %d left-right line(s) could be measured; this check needs "
            "at least two that agree before it will turn anything"
            % len(lines))
    vals = [v for _l, v in lines]
    yaw = sum(vals) / len(vals)
    spread = max(vals) - min(vals)
    print("%s" % os.path.basename(src))
    for label, v in lines:
        print("    %-10s yaw %+7.2f deg" % (label, v))
    print("    mean %+.2f deg, spread %.2f deg over %d line(s)"
          % (yaw, spread, len(lines)))

    if spread > SPREAD_MAX:
        die("the left-right lines disagree by %.2f deg (limit %.1f). That is "
            "not a turned character -- it is a limb out of place, and turning "
            "the body would bury it rather than fix it." % (spread, SPREAD_MAX))
    # HANDEDNESS, and it is not guessable. Unity is left-handed Y-up, so a
    # positive rotation about +Y takes +Z toward +X: a point (x, z) becomes
    # (x cos t + z sin t, -x sin t + z cos t), and the yaw measured here as
    # atan2(z, x) therefore comes out as yaw - t. The correction is +yaw, NOT
    # -yaw. Signing it the other way turns a character who was 20 degrees off
    # into one 40 degrees off, which is what the first run of this did -- and
    # the re-measure below is the only reason that did not ship.
    if want is None:
        want = yaw
    if abs(yaw) < YAW_MIN:
        print("nothing to do: %.2f deg is within %.1f of square"
              % (yaw, YAW_MIN))
        return 2

    hips = human.get("Hips")
    if not hips or hips not in by:
        die("no humanoid Hips bone to turn (map says %r)" % hips)
    # every bone must be in the hips' subtree, or turning it turns only part
    # of the character
    pid = by[hips]
    loose = []
    for p, n in tf.items():
        if not n["name"]:
            continue
        k, seen = p, 0
        while k in tf and seen < 64:
            if k == pid:
                break
            k = tf[k]["f"]
            seen += 1
        else:
            loose.append(n["name"])
            continue
        if k != pid:
            loose.append(n["name"])
    loose = [x for x in loose if x not in (hips,)]
    # the root object and the mesh nodes legitimately sit outside the skeleton
    skel_loose = [x for x in loose if x in
                  {n["name"] for n in tf.values()} and
                  any(x.endswith(s) for s in (".L", ".R")) or
                  x.startswith(("spine", "thigh", "shin", "foot", "upper_",
                                "fore", "hand", "head", "neck"))]
    if skel_loose:
        die("these bones are NOT below %r, so turning it would turn only part "
            "of the character: %s" % (hips, sorted(skel_loose)[:8]))

    rad = math.radians(want)
    R = (math.cos(rad / 2), 0.0, math.sin(rad / 2), 0.0)   # about world +Y
    # parent world rotation, so the turn is about the WORLD axis
    par = tf[pid]["f"]
    pq = (1.0, 0.0, 0.0, 0.0)
    chain = []
    k = par
    while k in tf:
        chain.append(k)
        k = tf[k]["f"]
    for k in reversed(chain):
        pq = qmul(pq, tf[k]["q"])
    oldq = tf[pid]["q"]
    newq = qmul(qmul(qconj(pq), qmul(R, pq)), oldq)
    print("    turning %r by %+.2f deg about world +Y, which takes the "
          "measured yaw to %+.2f" % (hips, want, yaw - want))
    print("    local rotation (%+.6f %+.6f %+.6f %+.6f) -> "
          "(%+.6f %+.6f %+.6f %+.6f)" % (oldq + newq))

    env = UnityPy.load(src)
    done = []
    for obj in env.objects:
        try:
            ty = obj.type.name
        except Exception:                                        # noqa: BLE001
            continue
        if ty == "Transform":
            if (tf.get(obj.path_id) or {}).get("name") != hips:
                continue
            tt = obj.read_typetree()
            lr = tt["m_LocalRotation"]
            lr["w"], lr["x"], lr["y"], lr["z"] = newq
            tt["m_LocalRotation"] = lr
            obj.save_typetree(tt)
            done.append("Transform.m_LocalRotation")
        elif ty == "Avatar":
            tt = obj.read_typetree()
            av = tt["m_Avatar"]
            names = {}
            for e in (tt.get("m_TOS") or []):
                if isinstance(e, (list, tuple)) and len(e) == 2:
                    names[e[0]] = e[1]
            ids = av["m_AvatarSkeleton"]["data"]["m_ID"]
            short = [(names.get(b) or "?").split("/")[-1] for b in ids]
            touched = False
            if hips in short:
                j = short.index(hips)
                for key in ("m_AvatarSkeletonPose", "m_DefaultPose"):
                    arr = av[key]["data"]["m_X"]
                    if j >= len(arr):
                        continue
                    q = arr[j]["q"]
                    q["w"], q["x"], q["y"], q["z"] = newq
                    touched = True
                    done.append("%s[%d].q" % (key, j))
            for e in tt["m_HumanDescription"]["m_Skeleton"]:
                if (e.get("m_Name") or "") != hips:
                    continue
                q = e["m_Rotation"]
                q["w"], q["x"], q["y"], q["z"] = newq
                touched = True
                done.append("m_HumanDescription.m_Skeleton.m_Rotation")
            if touched:
                obj.save_typetree(tt)

    if len(done) < 4:
        die("only %d of the four rest structures were written (%s). A bone's "
            "rest transform lives in all four and a partial write leaves the "
            "avatar disagreeing with the transform."
            % (len(done), ", ".join(done) or "none"))
    print("    changed: %s" % ", ".join(done))
    if dry:
        print("    --dry-run: nothing written")
        return 0

    data = env.file.save(packer="original")

    # re-measure on the bytes, before anything reaches disk
    lines2, _b2, _h2, _w2, _t2 = measure(data)
    vals2 = [v for _l, v in lines2]
    if not vals2:
        die("the written file has no measurable left-right line")
    yaw2 = sum(vals2) / len(vals2)
    spread2 = max(vals2) - min(vals2)
    print("    after:  " + "  ".join("%s %+.2f" % (l, v) for l, v in lines2))
    if abs(yaw2) > RESIDUAL_MAX:
        die("the turn did not take: the written file still reads %+.2f deg "
            "(limit %.1f). Nothing was saved." % (yaw2, RESIDUAL_MAX))
    if spread2 > SPREAD_MAX:
        die("the written file's lines disagree by %.2f deg; the turn has "
            "distorted something. Nothing was saved." % spread2)
    with open(out, "wb") as fh:
        fh.write(data)
    print("    mean yaw %+.2f -> %+.2f deg, spread %.2f -> %.2f"
          % (yaw, yaw2, spread, spread2))
    print("    wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
