# -*- coding: utf-8 -*-
"""Are a character's limb SEGMENTS the right length relative to each other?

Nothing here measured this, and that is why The Rock passed everything and
still looked wrong in game. `limb_check_installed.py` measures joint ANGLES --
is the elbow straight, do the two sides agree -- and he reads `worst=0.38`,
perfectly symmetric. `height_check_installed.py` measures the whole figure and
he reads 1.960 against a documented 1.96. Both are right and neither is
looking at the thing a person notices first, which is that his arms are the
wrong LENGTH for his body.

A rig can be wrong by a different factor in each limb -- that is already
written up in `docs/character-models.md`, and it is exactly The Rock's
history: his source skeleton spans 4.47 m against a 1.96 m mesh, his legs
wanted 0.387 and his arms 0.557, and `fit_joints.py` places each joint at the
boundary of the flesh it separates. If that fit is off, every angle stays
correct and every total stays correct while the segments are wrong.

WHAT IS MEASURED

Each segment's length as a fraction of STATURE, where stature is the vertical
distance from the lower of the two foot bones to the head bone -- rig
intrinsic, so it does not depend on the mesh or on what the character is
wearing:

    upperarm   LeftUpperArm  -> LeftLowerArm
    forearm    LeftLowerArm  -> LeftHand
    thigh      LeftUpperLeg  -> LeftLowerLeg
    shin       LeftLowerLeg  -> LeftFoot
    shoulders  LeftUpperArm  -> RightUpperArm
    reach      LeftHand      -> RightHand

and the same on the right, averaged. Human reference, for orientation only:
upper arm about 0.186 of height, forearm 0.146, thigh 0.245, shin 0.246,
shoulder span 0.259, and a reach roughly equal to height.

THE POPULATION IS THE STANDARD, NOT THE HUMAN FIGURE. Half this set is not
human -- Yoda, Shrek, a Xenomorph, a toilet -- so a deviation from anatomy is
not a defect. What IS a defect is a character that disagrees with the rest of
the set in a way its own species does not explain, which is the same reasoning
`limb_check_installed.py` already uses for its thresholds: calibrate on all 65
and report the outliers.

    python proportion_check_installed.py <dir-of-yargchar | file.yargchar ...>

    PROP_SIGMA=2.5     how far from the population median, in robust sigma,
                       before a segment is called out
"""
import math
import os
import sys

from limb_check_installed import read_rig

SIGMA = float(os.environ.get("PROP_SIGMA", "2.5"))

PAIRS = [
    ("upperarm", "UpperArm", "LowerArm"),
    ("forearm", "LowerArm", "Hand"),
    ("thigh", "UpperLeg", "LowerLeg"),
    ("shin", "LowerLeg", "Foot"),
]
HUMAN = {"upperarm": 0.186, "forearm": 0.146, "thigh": 0.245, "shin": 0.246,
         "shoulders": 0.259, "reach": 1.000}


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def measure(path):
    human, pos = read_rig(path)

    def P(hn):
        bn = human.get(hn)
        return pos.get(bn) if bn else None

    head = P("Head")
    lf, rf = P("LeftFoot"), P("RightFoot")
    if head is None or (lf is None and rf is None):
        return None
    floor = min(p[1] for p in (lf, rf) if p is not None)
    stature = head[1] - floor
    if stature <= 0.01:
        return None

    out = {}
    for key, a, b in PAIRS:
        vals = []
        for side in ("Left", "Right"):
            pa, pb = P(side + a), P(side + b)
            if pa and pb:
                vals.append(dist(pa, pb) / stature)
        if vals:
            out[key] = sum(vals) / len(vals)
    lu, ru = P("LeftUpperArm"), P("RightUpperArm")
    if lu and ru:
        out["shoulders"] = dist(lu, ru) / stature
    lh, rh = P("LeftHand"), P("RightHand")
    if lh and rh:
        out["reach"] = dist(lh, rh) / stature
    out["_stature"] = stature
    return out


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def main():
    args = sys.argv[1:]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            files.append(a)

    rows = {}
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        m = measure(p)
        if m:
            rows[name] = m
        else:
            print("%-34s no usable humanoid map" % name[:34])

    keys = ["upperarm", "forearm", "thigh", "shin", "shoulders", "reach"]
    stats = {}
    for k in keys:
        vals = [r[k] for r in rows.values() if k in r]
        if not vals:
            continue
        med = median(vals)
        # Median absolute deviation, scaled to a normal sigma. Robust, because
        # a set containing Yoda and a Xenomorph has real outliers by design and
        # a standard deviation would be dragged around by them.
        mad = median([abs(v - med) for v in vals]) * 1.4826
        stats[k] = (med, mad if mad > 1e-6 else 1e-6, len(vals))

    print("population of %d, median (robust sigma) -- human reference in []\n"
          % len(rows))
    for k in keys:
        if k in stats:
            med, mad, n = stats[k]
            print("  %-10s %.3f  (sigma %.3f, n=%d)   [%.3f]"
                  % (k, med, mad, n, HUMAN[k]))
    print()

    flagged = []
    for name in sorted(rows):
        r = rows[name]
        bad = []
        for k in keys:
            if k not in r or k not in stats:
                continue
            med, mad, _ = stats[k]
            z = (r[k] - med) / mad
            if abs(z) > SIGMA:
                bad.append("%s %.3f (%+.1f sigma, median %.3f)"
                           % (k, r[k], z, med))
        if bad:
            flagged.append((name, bad))
            print("%-34s %s" % (name[:34], "; ".join(bad)))

    print("\n%d of %d character(s) have a segment more than %.1f sigma from "
          "the population" % (len(flagged), len(rows), SIGMA))
    print("A deviation is not automatically a defect -- half this set is not "
          "human. It is a question to answer with a render.")


if __name__ == "__main__":
    main()
