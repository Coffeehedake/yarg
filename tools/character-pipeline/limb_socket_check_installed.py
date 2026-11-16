# -*- coding: utf-8 -*-
"""Is a LIMB out of its socket? Measured on the flesh, not on bone offsets.

    python limb_socket_check_installed.py <dir-of-yargchar | file.yargchar ...>

THIS REPLACES mirror_check_installed.py, WHICH WAS UNSOUND. That tool compared
each limb bone's LOCAL offset from its parent with X negated, and the comparison
is only the mirror when the parent's own axes put X along the body's left-right
line. Nothing can be assumed about that, and it is not a property of the pose --
it is the rig's own axis convention, which cannot be read back out of the file.

Sayuri is the proof. It called her thighs 220.59 mm out of mirror; their WORLD
positions agree to 0.05 mm, as does every other limb pair she has. Her
`CC_Base_Pelvis` is rolled 90 degrees and both thighs hang off it, so negating X
in its frame is not a mirror. Kronk was the same artefact: 226.04 mm by that
measure, 30.48 mm in world. **Every one of that tool's nine findings was a
shared-parent slot** -- UpperLeg, Shoulder or UpperArm, the three whose left and
right hang off ONE bone -- because that is exactly the case a rotated parent
corrupts. Where the parents are each other's mirror the local offsets carry the
mirror themselves and read 0.00 correctly, which is why nothing else flagged.

And the world comparison is no use either, for the opposite reason: a rest
skeleton that is an authored stance is not mirror-symmetric in world and should
not be. Spartan Mark V's arms are 198 mm apart in world by design.

So this measures neither. It measures THE JOIN, which needs no reference to the
other side and no axis convention:

    for each limb that attaches to the torso, how far is the nearest part of
    its flesh from the nearest torso vertex?

A limb in its socket touches. The other side is then a CONTROL rather than the
measurement, and the comparison is between two numbers about the same model.
Spartan Mark V's right thigh sat 29.7 mm clear of a socket his left thigh sat
4.6 mm inside; after the fix it reads 4.6, his left leg's own figure. Kronk
reads 25.2 against 29.0 and is simply a chunky low-poly character whose legs
both attach.

IT DECLINES TO JUDGE a pair whose two sides are not the same geometry, because
then nothing about them is comparable. Kronk's thighs carry 54 and 45 vertices;
his mesh was never mirrored, and all eight of his limbs differ in their own
frames by 18 to 80 mm.
"""
import glob
import math
import os
import sys

import UnityPy

import cloth_collide_installed as cci
from patch_springs import decode, mat4, mul, trs, xform

# The limbs that hang off the torso. A LowerLeg or a Hand joins its own parent
# limb, not the body, so a gap there is a different fault and not this one.
JOINS = [("UpperLeg", "LeftUpperLeg", "RightUpperLeg"),
         ("Shoulder", "LeftShoulder", "RightShoulder"),
         ("UpperArm", "LeftUpperArm", "RightUpperArm")]
TORSO = ("Hips", "Spine", "Chest", "UpperChest", "Neck")

# Calibrated against the installed set rather than guessed: Spartan Mark V's
# displaced leg read 29.7 against 4.6 -- a 25.1 mm difference at a ratio of
# 6.5 -- while Kronk, the worst honest case, reads 29.0 against 25.2, a 3.8 mm
# difference at 1.15. Both conditions must hold, so a character whose limbs are
# simply all a little clear of the body does not flag.
GAP_MM = float(os.environ.get("SOCKET_GAP_MM", "10.0"))
GAP_RATIO = float(os.environ.get("SOCKET_GAP_RATIO", "2.0"))
# Two sides whose vertex counts differ by more than this are not the same
# geometry and are not compared.
COUNT_TOL = float(os.environ.get("SOCKET_COUNT_TOL", "0.05"))
TORSO_SAMPLE = 3000


def flesh(path):
    """{bone path_id: [world position per dominated vertex]}, and skips."""
    env = UnityPy.load(path)
    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(path)
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())
    per, skipped = {}, []
    for r in smrs:
        tt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if tt is None:
            continue
        got = decode(tt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [mat4(m) for m in (tt.get("m_BindPose") or [])]
        if got is None or len(bind) != len(bones) or not bones:
            skipped.append(tt.get("m_Name") or "?")
            continue
        V, W, I = got
        skin = [mul(trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
        for vi in range(len(V)):
            px = py = pz = 0.0
            best, bw = None, -1.0
            for k in range(len(W[vi])):
                w, bi = W[vi][k], I[vi][k]
                if w <= 0 or bi >= len(skin):
                    continue
                q = xform(skin[bi], V[vi])
                px += w * q[0]
                py += w * q[1]
                pz += w * q[2]
                if w > bw:
                    best, bw = bones[bi], w
            if best is not None:
                per.setdefault(best, []).append((px, py, pz))
    return human, tf, per, skipped


def region(tf, by_name, human, bone):
    """The bone's own path_id plus its subtree, stopping at other limbs.

    A Character Creator rig deforms through `*_Twist` bones: Sayuri's
    `CC_Base_L_Thigh` dominates ZERO vertices while `CC_Base_L_ThighTwist01`
    and `02` dominate 1,504 and 3,492 of them. Attributing by the mapped bone
    alone made the check decline her entirely, which is honest and useless. A
    twist bone IS part of the thigh, so the thigh's flesh is its whole subtree
    down to the next mapped humanoid bone -- which for Spartan Mark V stops at
    `shin.L` immediately and changes nothing.
    """
    mapped = set(human.values()) - {bone}
    out, stack = set(), [by_name[bone]]
    kids = {}
    for pid, n in tf.items():
        kids.setdefault(n["f"], []).append(pid)
    while stack:
        pid = stack.pop()
        if pid in out:
            continue
        out.add(pid)
        for c in kids.get(pid, []):
            if tf[c]["name"] in mapped:
                continue
            stack.append(c)
    return out


def nearest(ps, torso):
    ds = []
    for p in ps:
        best = 1e9
        for q in torso:
            d = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
                 + (p[2] - q[2]) ** 2)
            if d < best:
                best = d
        ds.append(math.sqrt(best))
    ds.sort()
    return ds


def report(path):
    name = os.path.basename(path).replace(".yargchar", "")
    try:
        human, tf, per, skipped = flesh(path)
    except Exception as e:                                       # noqa: BLE001
        print("%-26s READ FAILED %s" % (name[:26], type(e).__name__))
        return 0
    by_name = {}
    for pid, n in tf.items():
        if n["name"]:
            by_name.setdefault(n["name"], pid)
    # The torso reference is the MAPPED spine chain only, deliberately NOT its
    # subtree. Expanding it was tried and it destroys the measurement: Spartan
    # Mark V's `pelvis.R` is an unmapped child of his hips whose flesh sits
    # right beside his displaced thigh, so counting it as torso closed his
    # 29.7 mm gap to 5.4 mm and the fault vanished. The limb side DOES use the
    # subtree, because a twist bone is part of its limb -- the asymmetry
    # between the two is the point.
    tor_ids = set()
    for k in TORSO:
        bn = cci.hname(human, k)
        if bn and bn in by_name:
            tor_ids.add(by_name[bn])
    torso = [p for b in tor_ids for p in (per.get(b) or [])]
    if len(torso) < 64:
        print("%-26s torso carries %d vertex/vertices -- nothing to measure "
              "a join against%s" % (name[:26], len(torso),
                                    ("; undecodable: " + ", ".join(skipped))
                                    if skipped else ""))
        return 0
    step = max(1, len(torso) // TORSO_SAMPLE)
    torso = torso[::step]
    lines, found = [], 0
    for slot, lk, rk in JOINS:
        ln, rn = cci.hname(human, lk), cci.hname(human, rk)
        if not ln or not rn or ln not in by_name or rn not in by_name:
            continue
        pa = [p for b in region(tf, by_name, human, ln)
              for p in (per.get(b) or [])]
        pb = [p for b in region(tf, by_name, human, rn)
              for p in (per.get(b) or [])]
        if len(pa) < 16 or len(pb) < 16:
            lines.append("    %-10s %5d / %5d vertex/vertices -- too few to "
                         "measure" % (slot, len(pa), len(pb)))
            continue
        if abs(len(pa) - len(pb)) > COUNT_TOL * max(len(pa), len(pb)):
            lines.append("    %-10s %5d / %5d vertices -- the two sides are "
                         "NOT the same geometry, so not compared"
                         % (slot, len(pa), len(pb)))
            continue
        # the fifth of each limb nearest the body is the part that joins it
        da = nearest(sorted(pa, key=lambda p: -p[1])[:max(8, len(pa) // 5)],
                     torso)
        db = nearest(sorted(pb, key=lambda p: -p[1])[:max(8, len(pb) // 5)],
                     torso)
        la, lb = da[0] * 1000, db[0] * 1000
        lo, hi = min(la, lb), max(la, lb)
        bad = (hi - lo) >= GAP_MM and hi >= GAP_RATIO * max(lo, 0.01)
        lines.append("    %-10s left %6.1f mm   right %6.1f mm   "
                     "difference %5.1f, ratio %4.1fx%s"
                     % (slot, la, lb, hi - lo, hi / max(lo, 0.01),
                        "   <-- %s SIDE IS OUT OF ITS SOCKET"
                        % ("RIGHT" if lb > la else "LEFT") if bad else ""))
        if bad:
            found += 1
    print("%-26s %s%s" % (name[:26], "%d limb(s) out of socket" % found
                          if found else "every limb joins the body",
                          ("   (undecodable: %s)" % ", ".join(skipped))
                          if skipped else ""))
    for ln_ in lines:
        print(ln_)
    return found


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    files = []
    for a in args:
        if os.path.isdir(a):
            files += sorted(glob.glob(os.path.join(a, "*.yargchar")))
        else:
            files.append(a)
    print("socket-checking %d bundle(s): a limb flags when the two sides' "
          "gaps differ by >= %.0f mm AND by >= %.1fx"
          % (len(files), GAP_MM, GAP_RATIO))
    n = 0
    for f in files:
        n += report(f)
    print("\n%d limb(s) out of socket across %d bundle(s)" % (n, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
