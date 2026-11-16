# -*- coding: utf-8 -*-
"""Where is the geometry's own centreline, and do the bones sit on it?

    python centreline_check_installed.py <file.yargchar> [mesh-name]

MEDIAN x, not the midpoint of the extremes. That is the whole point of this
tool. Slicing The Mandalorian by height and taking (min + max) / 2 gave
x-midpoints wandering +-20 mm with no structure, because the extremes are
whichever single vertex happens to stick out furthest -- a measurement of his
outliers, not of his centre. The median of a few hundred vertices does not
care about them, and on a body that is broadly symmetric it IS the centreline.

With a centreline per height band, a bone can finally be asked the only
question that matters: does it sit where the geometry's own middle is? Mando's
chest pivots 18.7 mm off the line his legs define, and until there is a
trustworthy centreline there is no way to say which of the two is wrong, so no
way to correct either.

The vertices are the SKINNED positions -- where the game draws them -- and the
dominant-bone selection means a band of the torso is not contaminated by the
arms that pass through it at the same height, which is what spoiled the first
attempt at this on Mando (a "chest midpoint" of -0.2077 that was his forearm).

Reports the median, the quartiles and the count per band, because a median
over 30 vertices of a narrow strip is not the same claim as one over 900. A
band whose quartiles straddle the median unevenly is skewed geometry rather
than a displaced one, and the two must not be read the same way.
"""
import os
import sys

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

BANDS = 14


def pct(vals, q):
    if not vals:
        return 0.0
    v = sorted(vals)
    i = q * (len(v) - 1)
    lo = int(i)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else None

    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(path)
    env = UnityPy.load(path)

    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    # The humanoid torso and legs only. An arm crossing the band at chest
    # height is the contamination this selection exists to remove.
    keep_bones = set()
    for hn in ("Hips", "Spine", "Chest", "UpperChest", "Neck", "Head",
               "LeftUpperLeg", "RightUpperLeg", "LeftLowerLeg",
               "RightLowerLeg", "LeftFoot", "RightFoot"):
        bn = human.get(hn)
        if bn:
            keep_bones.add(bn)
    if not keep_bones:
        print("no humanoid torso/leg bone is mapped in this file")
        return 2

    pts = []
    for r in smrs:
        mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        if want is not None and (mt.get("m_Name") or "") != want:
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
        if got is None or len(bind) != len(bones) or not bones:
            continue
        V, W, I = got
        skin = [ps.mul(ps.trs(*world(b)), bind[i])
                for i, b in enumerate(bones)]
        for vi in range(len(V)):
            bw, bb, p = -1.0, None, None
            for k in range(len(W[vi])):
                w, bi = W[vi][k], I[vi][k]
                if w <= 0 or bi >= len(skin):
                    continue
                if w > bw:
                    bw, bb, p = w, bi, ps.xform(skin[bi], V[vi])
            if p is None:
                continue
            if (tf.get(bones[bb], {}).get("name") or "") in keep_bones:
                pts.append(p)

    if len(pts) < 200:
        print("only %d vertex/vertices are dominated by a mapped torso or leg "
              "bone -- too few to call a centreline" % len(pts))
        return 1

    lo_y = min(p[1] for p in pts)
    hi_y = max(p[1] for p in pts)
    step = (hi_y - lo_y) / BANDS
    print("%s -- %d torso/leg vertices, y %.3f..%.3f in %d bands\n"
          % (os.path.basename(path), len(pts), lo_y, hi_y, BANDS))
    print("%-16s %6s   %9s %9s %9s   %9s"
          % ("band (y)", "n", "x q25", "x MEDIAN", "x q75", "min..max mid"))
    meds = []
    y = lo_y
    while y < hi_y - 1e-9:
        b = [p[0] for p in pts if y <= p[1] < y + step]
        if len(b) >= 40:
            m = pct(b, 0.5)
            meds.append(m)
            print("%6.3f..%6.3f %6d   %+9.4f %+9.4f %+9.4f   %+9.4f"
                  % (y, y + step, len(b), pct(b, 0.25), m, pct(b, 0.75),
                     (min(b) + max(b)) / 2.0))
        y += step
    if meds:
        print("\ncentreline: median of the band medians %+.4f m, "
              "spread %.1f mm"
              % (pct(meds, 0.5), (max(meds) - min(meds)) * 1000))

    # And the bone pairs against it, which is the comparison the whole tool
    # is for.
    c = pct(meds, 0.5) if meds else 0.0
    name_pid = {}
    for pid, n in tf.items():
        if n.get("name"):
            name_pid.setdefault(n["name"], pid)

    def wp(hn):
        bn = human.get(hn)
        if not bn or bn not in name_pid:
            return None
        return world(name_pid[bn])[0]

    print("\n%-12s %10s %10s %12s %14s"
          % ("pair", "left x", "right x", "pair centre", "off centreline"))
    for label, ln, rn in (("Hips", "LeftUpperLeg", "RightUpperLeg"),
                          ("Knees", "LeftLowerLeg", "RightLowerLeg"),
                          ("Feet", "LeftFoot", "RightFoot"),
                          ("Shoulders", "LeftUpperArm", "RightUpperArm"),
                          ("Hands", "LeftHand", "RightHand")):
        a, b = wp(ln), wp(rn)
        if a is None or b is None:
            continue
        mid = (a[0] + b[0]) / 2.0
        print("%-12s %+10.4f %+10.4f %+12.4f %11.1f mm"
              % (label, a[0], b[0], mid, (mid - c) * 1000))
    for hn in ("Hips", "Spine", "Chest", "UpperChest", "Head"):
        p = wp(hn)
        if p is None:
            continue
        print("%-12s %32s %+12.4f %11.1f mm"
              % (hn, "(single bone)", p[0], (p[0] - c) * 1000))
    return 0


if __name__ == "__main__":
    sys.exit(main())
