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

# Calibrated against the installed set rather than guessed, and ON THE p10 that
# gap() returns -- the thresholds were first set against the MINIMUM and had to
# be redone, because the minima and the p10s are different populations.
#
#   Spartan Mark V, displaced   p10 11.6 against 39.8   28.1 mm at 3.4x
#   Spartan Mark V, fixed       p10 11.6 against 12.2    0.6 mm at 1.0x
#   Scott Hall, sound           p10 17.8 against 20.7    2.9 mm at 1.2x
#   Yui Suzukaze, sound         p10 37.1 against 27.4    9.6 mm at 1.4x
#   Kronk, sound                p10 48.8 against 41.3    7.4 mm at 1.2x
#
# Both conditions must hold, so a character all of whose limbs sit a little
# clear of the body does not flag. Scott Hall and Yui Suzukaze are in that table
# because the first version of this check REPORTED them, on minima of 1.1
# against 14.0 and 22.2 against 7.4.
GAP_MM = float(os.environ.get("SOCKET_GAP_MM", "10.0"))
GAP_RATIO = float(os.environ.get("SOCKET_GAP_RATIO", "2.0"))
# Two sides whose flesh differs by more than this IN THEIR OWN BONES' FRAMES
# are not the same geometry, whatever their vertex counts say, and comparing
# their joins means nothing. The count gate below is not enough on its own:
# Vegeta's two upper arms carry 818 and 827 vertices -- within 5% -- and differ
# by 45.20 mm in frame, and he was the one character the previous version still
# reported. Every limb he has differs in frame, by 4.9 to 45.2 mm, and so does
# every limb Kronk has. Both are hand-modelled characters whose meshes were
# never mirrored.
INFRAME_MM = float(os.environ.get("SOCKET_INFRAME_MM", "10.0"))
# Two sides whose vertex counts differ by more than this are not the same
# geometry and are not compared.
COUNT_TOL = float(os.environ.get("SOCKET_COUNT_TOL", "0.05"))
TORSO_SAMPLE = 3000


def flesh(path):
    """(humanoid map, transforms, {bone: [world positions]}, skipped,
    world()). `world` comes back because inframe() needs each bone's own
    frame and re-reading the bundle to get it would double the sweep."""
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
    return human, tf, per, skipped, world


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


def inframe(tf, by_name, world, ln, rn, pa, pb):
    """How far the two sides' flesh differs IN THEIR OWN BONES' FRAMES.

    Each side's points are taken into its own bone's frame and the right side
    is mirrored in X; a sound mirrored pair then agrees closely (Spartan Mark
    V's thighs to 0.0 mm, Scott Hall's to 2.7). This is the question of whether
    the two limbs are the same object at all, and it has to be answered before
    any comparison between them is worth making.
    """
    def inv(p, q):
        w, x, y, z = q

        def rot_inv(v):
            tx = 2.0 * (-y * v[2] + z * v[1])
            ty = 2.0 * (-z * v[0] + x * v[2])
            tz = 2.0 * (-x * v[1] + y * v[0])
            return (v[0] + w * tx + (-y * tz + z * ty),
                    v[1] + w * ty + (-z * tx + x * tz),
                    v[2] + w * tz + (-x * ty + y * tx))
        return lambda v: rot_inv((v[0] - p[0], v[1] - p[1], v[2] - p[2]))

    out = []
    for nm, ps, flip in ((ln, pa, 1.0), (rn, pb, -1.0)):
        wp, wq, _s = world(by_name[nm])
        to_local = inv(wp, wq)
        lp = [to_local(p) for p in ps]
        lp = [(flip * p[0], p[1], p[2]) for p in lp]
        out.append((tuple(min(p[i] for p in lp) for i in range(3)),
                    tuple(max(p[i] for p in lp) for i in range(3))))
    return max(abs(out[0][j][i] - out[1][j][i])
               for j in (0, 1) for i in range(3))


def nearest(ps, torso):
    """Sorted distances from each point to the nearest torso vertex."""
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


def shift(da, db):
    """(mm the right side is further at the WEAKEST of q0..q50, the profile).

    A limb genuinely out of its socket is further from the body across its
    whole near region, because the displacement is rigid. A difference in
    topology between the two sides moves some quantiles and not others, and
    three earlier versions of this check were each fooled by one statistic
    that happened to move. So the criterion is the WEAKEST decile of the near
    half, which is a statement of distributional dominance and is what "this
    limb is further from the body" actually means.

        Spartan Mark V, displaced   +25.1 +28.1 +26.7 +27.8 +26.8 +24.8
        Peacemaker, sound            +0.1 +21.7 +26.8  +0.7  -2.8  -0.8

    Peacemaker differs at two deciles out of eleven and agrees or reverses at
    the rest. He was the last finding of the p10 version, and he is sound.
    """
    prof = []
    for q in (0, 10, 20, 30, 40, 50):
        ia = min(len(da) - 1, q * (len(da) - 1) // 100)
        ib = min(len(db) - 1, q * (len(db) - 1) // 100)
        prof.append((db[ib] - da[ia]) * 1000)
    worst = min(prof, key=abs) if all(v > 0 for v in prof) \
        or all(v < 0 for v in prof) else 0.0
    return worst, prof


def decide(da, db):
    """(is one side out of its socket, +1 right / -1 left, text).

    THE ONE PLACE THIS DECISION IS MADE. It lived in two -- here and in
    patch_mirror.py's guard -- and the duplication bit twice: each time the
    criterion was sharpened, the check got it and the patcher kept the old one,
    so the tool that MOVES A BONE was briefly willing to accept characters the
    tool that only reports had already cleared. Both call this now.
    """
    la, lb = gap(da) * 1000, gap(db) * 1000
    lo, hi = min(la, lb), max(la, lb)
    worst, prof = shift(da, db)
    bad = abs(worst) >= GAP_MM and hi >= GAP_RATIO * max(lo, 0.01)
    txt = ("left %6.1f mm   right %6.1f mm   q0..q50 right-left %s  "
           "weakest %+6.1f" % (la, lb, " ".join("%+.0f" % v for v in prof),
                               worst))
    return bad, (1 if worst > 0 else -1), txt


def gap(ds):
    """The limb's distance from the body, as a ROBUST statistic.

    NOT the minimum. A minimum over hundreds of vertices is the most
    noise-sensitive number available: one vertex that happens to land near one
    torso vertex sets it. Scott Hall was reported as a limb out of its socket
    on exactly that -- his left thigh's closest vertex is 1.1 mm from the
    torso and his right's is 14.0, a 13x reading, while the two distributions
    are the same to 3 mm:

        LeftUpLeg    min  1.1   p10 17.8   median 49.1
        RightUpLeg   min 14.0   p10 20.7   median 46.0

    His thighs carry 1,326 and 1,325 vertices and sit 2.69 mm apart in their
    own frames. Nothing is wrong with him. The tenth percentile of the near
    region says the same thing about a real displacement -- Spartan Mark V
    reads p10 10.4 against 39.8 -- without being hostage to one vertex.
    """
    return ds[len(ds) // 10] if ds else 0.0


def report(path):
    name = os.path.basename(path).replace(".yargchar", "")
    try:
        human, tf, per, skipped, world = flesh(path)
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
        inf = inframe(tf, by_name, world, ln, rn, pa, pb)
        if inf is not None and inf > INFRAME_MM / 1000.0:
            lines.append("    %-10s differs %5.1f mm IN ITS OWN FRAME -- the "
                         "two sides are not the same geometry (counts %d / "
                         "%d), so not compared"
                         % (slot, inf * 1000, len(pa), len(pb)))
            continue
        # the fifth of each limb nearest the body is the part that joins it
        da = nearest(sorted(pa, key=lambda p: -p[1])[:max(8, len(pa) // 5)],
                     torso)
        db = nearest(sorted(pb, key=lambda p: -p[1])[:max(8, len(pb) // 5)],
                     torso)
        bad, side, txt = decide(da, db)
        lines.append("    %-10s %s%s"
                     % (slot, txt,
                        "   <-- %s SIDE IS OUT OF ITS SOCKET"
                        % ("RIGHT" if side > 0 else "LEFT") if bad else ""))
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
