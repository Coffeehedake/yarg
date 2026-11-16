# -*- coding: utf-8 -*-
"""Is one LIMB of an installed character in the wrong place?

    python mirror_check_installed.py <dir-of-yargchar | file.yargchar ...>

`limb_check_installed.py` already measures joint ANGLES and their left/right
asymmetry, and its own calibration says why that is the signal to trust: elbow
and knee asymmetry is exactly 0.0 across all 66 characters. But an angle is
blind to a limb that is RIGIDLY DISPLACED. Spartan Mark V's right leg sits
92 mm out of mirror with its knee and ankle angles identical to his left to
four decimals, so the angle check reported him clean -- "bent or asymmetric
limbs, 0 new, CLOSED" -- while his right leg stood 30 mm clear of the hip
socket his left leg sits 5 mm inside.

What this measures instead is WHERE each limb bone is: its local offset from
its parent, X negated, against its mirror partner's. Three decisions, each of
which a first version got wrong:

LOCAL, not world. World folds in every ancestor's rotation, so it measures the
rest POSE as much as the skeleton. On Spartan Mark V the world comparison flags
29 of 29 pairs, his fingers included, because his authored stance is twisted.
The local comparison flags one.

THE HUMANOID MAP, not bone names. Pairing `.L`/`.R` by pattern works until a
rig calls them something else, and it drags in every finger, hair strand, IK
target and spring helper. A flat 2 mm threshold over all of those "found" 39 of
65 characters -- Adachi Rei's IK leg target at 2,850 mm, Harley Quinn's little
finger at 167 mm -- and reading that list is how you learn to skim. These are
the eight pairs the game actually animates a limb through, and a displacement
in one of them moves a whole arm or leg.

THE CHARACTER IS ITS OWN CONTROL. A local offset is expressed in its PARENT's
frame, so negating X is the true mirror only when the parent frames are
themselves mirrored -- not true of every rig, and where it fails it fails for
nearly every pair at once. So a character is judged only when most of its pairs
mirror, and a rig that fails wholesale is reported as NOT MEASURABLE, by count,
rather than as eight findings.
"""
import glob
import math
import os
import sys

import cloth_collide_installed as cci

# The eight the game animates a limb through. Fingers are deliberately absent:
# they are small, routinely authored asymmetric, and a few millimetres there
# cannot be seen -- while they supply almost all of the noise.
LIMBS = [("Shoulder", "LeftShoulder", "RightShoulder"),
         ("UpperArm", "LeftUpperArm", "RightUpperArm"),
         ("LowerArm", "LeftLowerArm", "RightLowerArm"),
         ("Hand", "LeftHand", "RightHand"),
         ("UpperLeg", "LeftUpperLeg", "RightUpperLeg"),
         ("LowerLeg", "LeftLowerLeg", "RightLowerLeg"),
         ("Foot", "LeftFoot", "RightFoot"),
         ("Toes", "LeftToes", "RightToes")]

TOL = float(os.environ.get("MIRROR_TOL", "0.005"))        # 5 mm
# Two thirds is deliberately loose. The point is to exclude the rigs where the
# comparison is meaningless, not to grade the ones where it works -- those come
# out at 7 of 8 or better.
APPLIES = float(os.environ.get("MIRROR_APPLIES", "0.667"))


def pairs_of(human, tf):
    """[(total m, left bone, right bone, (dx, dy, dz), slot)] per limb."""
    by_name = {}
    for pid, n in tf.items():
        if n["name"]:
            by_name.setdefault(n["name"], pid)
    rows = []
    for slot, lk, rk in LIMBS:
        ln, rn = cci.hname(human, lk), cci.hname(human, rk)
        if not ln or not rn or ln not in by_name or rn not in by_name:
            continue
        a = tf[by_name[ln]]["p"]
        b = tf[by_name[rn]]["p"]
        d = (b[0] + a[0], b[1] - a[1], b[2] - a[2])
        rows.append((math.sqrt(sum(x * x for x in d)), ln, rn, d, slot))
    rows.sort(reverse=True)
    return rows


def verdict(rows):
    """(is the test applicable, [the outliers]) -- judged against itself."""
    if not rows:
        return False, []
    ok = [r for r in rows if r[0] <= TOL]
    if len(ok) < APPLIES * len(rows):
        return False, []
    return True, [r for r in rows if r[0] > TOL]


def report(path):
    name = os.path.basename(path).replace(".yargchar", "")
    try:
        human, tf, _g, _s, _j, _c, _gr, _w = cci.read(path)
    except Exception as e:                                       # noqa: BLE001
        print("%-26s READ FAILED %s" % (name[:26], type(e).__name__))
        return 0
    rows = pairs_of(human, tf)
    if not rows:
        print("%-26s no humanoid limb pairs in the map" % name[:26])
        return 0
    applies, bad = verdict(rows)
    if not applies:
        over = len([r for r in rows if r[0] > TOL])
        print("%-26s NOT MEASURABLE -- %d of %d limb pair(s) over %.0f mm, so "
              "the parent frames are not mirrored and negating X is not this "
              "rig's mirror" % (name[:26], over, len(rows), TOL * 1000))
        return 0
    if not bad:
        print("%-26s %d limb pair(s), all within %.0f mm (worst %s %.2f mm)"
              % (name[:26], len(rows), TOL * 1000, rows[0][4],
                 rows[0][0] * 1000))
        return 0
    print("%-26s %d of %d limb pair(s) mirror, %d DO NOT:"
          % (name[:26], len(rows) - len(bad), len(rows), len(bad)))
    for t, ln, rn, d, slot in bad:
        print("    %-10s %-18s %-18s %8.2f mm  (dx %+.2f dy %+.2f dz %+.2f)"
              % (slot, ln[:18], rn[:18], t * 1000, d[0] * 1000, d[1] * 1000,
                 d[2] * 1000))
    return len(bad)


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
    print("mirror-checking %d bundle(s) on %d humanoid limb pair(s), "
          "tolerance %.0f mm, judged when %.0f%% of a character's pairs mirror"
          % (len(files), len(LIMBS), TOL * 1000, APPLIES * 100))
    n = 0
    for f in files:
        n += report(f)
    print("\n%d displaced limb bone(s) across %d bundle(s)" % (n, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
