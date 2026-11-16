# -*- coding: utf-8 -*-
"""Is the UPPER half of a skeleton laterally offset from the LOWER half?

    python half_body_check_installed.py <dir-of-yargchar | file.yargchar ...>

The Mandalorian, reported 2026-11-16 as his armour not being centred on his
chest. His pairs come out like this:

    Hips       -0.1576  +0.1206   separation 0.2782   pair centre -18.5 mm
    Knees      -0.1576  +0.1206   separation 0.2782   pair centre -18.5 mm
    Feet       -0.1576  +0.1206   separation 0.2782   pair centre -18.5 mm
    Shoulders  -0.1979  +0.2352   separation 0.4331   pair centre +18.7 mm
    Elbows     -0.4432  +0.4805   separation 0.9237   pair centre +18.7 mm
    Hands      -0.6888  +0.7262   separation 1.4150   pair centre +18.7 mm

Every lower pair centres at -18.5 mm and every upper pair at +18.7 mm, to a
tenth of a millimetre, with NO gradient between them -- and the limbs
themselves are near-perfect (his arm segments measure 0.2453/0.2456 against
0.2453/0.2457). That is not a lean and not a twist. It is a 37.2 mm STEP
between two half-skeletons, which is exactly what his recipe would predict:
his source glTF has two collapsed skeletons and he was re-rigged via Mixamo.

NOTHING IS VISIBLE AT REST, which is why this was never reported as a rig
fault and why slicing the mesh does not find it: the skinned geometry sits
precisely where the bones put it -- raw and skinned vertex positions agree to
four decimal places. The fault is that the bones are in the wrong place INSIDE
the geometry. The chest therefore pivots about an axis 18.7 mm off the
centreline his legs define, and everything the chest carries, his armour
included, swings off-centre the moment he is animated.

This is NOT a mirror check. `mirror_check_installed.py` was deleted for
comparing local bone offsets with X negated, which is unsound wherever a
shared parent is rolled -- all nine of its findings were the one case it got
wrong. This reads WORLD positions of the humanoid-mapped pairs only, and
reports three things that need no axis convention at all: each pair's
SEPARATION, each pair's CENTRE, and the segment lengths down each limb.

A pair centre is the midpoint of two bones that the AVATAR itself calls left
and right, so it needs no reference to x = 0 and no assumption about which
side is which. What it compares is one half of the character against the other
half, which is the only anchor here that cannot itself be wrong.

Read the SPREAD within each half before believing the step between them. Three
lower pairs agreeing to 0.1 mm and three upper pairs agreeing to 0.1 mm is
what makes "two half-skeletons" the reading; if the six centres instead walk
steadily from one value to another, that is a lean distributed through the
spine and a different fault.

HALF_STEP sets the threshold in metres, default 0.008. Segment lengths are
printed for every flagged character because a limb SCALING fault shows there
and a step does not, and the two are easy to confuse from the pair widths
alone.
"""
import os
import sys

import cloth_collide_installed as cci

STEP = float(os.environ.get("HALF_STEP", "0.008"))

PAIRS = [("Hips", "LeftUpperLeg", "RightUpperLeg", "lower"),
         ("Knees", "LeftLowerLeg", "RightLowerLeg", "lower"),
         ("Feet", "LeftFoot", "RightFoot", "lower"),
         ("Shoulders", "LeftUpperArm", "RightUpperArm", "upper"),
         ("Elbows", "LeftLowerArm", "RightLowerArm", "upper"),
         ("Hands", "LeftHand", "RightHand", "upper")]

CHAINS = [("left arm", ["LeftUpperArm", "LeftLowerArm", "LeftHand"]),
          ("right arm", ["RightUpperArm", "RightLowerArm", "RightHand"]),
          ("left leg", ["LeftUpperLeg", "LeftLowerLeg", "LeftFoot"]),
          ("right leg", ["RightUpperLeg", "RightLowerLeg", "RightFoot"])]


def measure(path):
    """(rows, chains) for one bundle, or (None, None) if nothing is mapped."""
    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(path)
    name_pid = {}
    for pid, n in tf.items():
        if n.get("name"):
            name_pid.setdefault(n["name"], pid)

    def wp(hn):
        bn = human.get(hn)
        if not bn or bn not in name_pid:
            return None
        return world(name_pid[bn])[0]

    rows = []
    for label, ln, rn, half in PAIRS:
        a, b = wp(ln), wp(rn)
        if a is None or b is None:
            continue
        rows.append((label, half, a[0], b[0], abs(b[0] - a[0]),
                     (a[0] + b[0]) / 2.0))

    chains = []
    for label, hs in CHAINS:
        pts = [wp(h) for h in hs]
        if any(p is None for p in pts):
            continue
        chains.append((label, [
            sum((pts[i + 1][k] - pts[i][k]) ** 2 for k in range(3)) ** 0.5
            for i in range(len(pts) - 1)]))
    return (rows or None), chains


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            files.append(a)

    print("flagging a step of %.1f mm or more between the upper and lower "
          "halves\n" % (STEP * 1000))
    walked = flagged = unmapped = 0
    for f in files:
        name = os.path.basename(f)[:-9]
        try:
            rows, chains = measure(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-30s UNREADABLE: %s" % (name, e))
            continue
        walked += 1
        if not rows:
            unmapped += 1
            continue
        lo = [r[5] for r in rows if r[1] == "lower"]
        up = [r[5] for r in rows if r[1] == "upper"]
        losep = [r[4] for r in rows if r[1] == "lower"]
        if not lo or not up:
            unmapped += 1
            continue
        step = sum(up) / len(up) - sum(lo) / len(lo)
        # Two spreads, and the SEPARATION one is the load-bearing half of the
        # verdict. The first version of this check used only the centre
        # spread, and on that rule Alcina Dimitrescu read "TWO HALVES" like
        # The Mandalorian -- but her leg pairs separate 0.2806, 0.3824, 0.4683
        # going down, so her legs SPLAY: she is posed, and this project's own
        # note on her says her static pose IS her shape and must never be
        # reset. Her whole skeleton also stands 127.7 mm off the origin by
        # design, so a 26 mm step on top of that means something else again.
        #
        # Legs whose pairs separate IDENTICALLY at hip, knee and foot are
        # vertical and unposed, and only then does an offset upper half have
        # nowhere to come from but the rig.
        sprd = max(max(lo) - min(lo), max(up) - min(up))
        ssprd = max(losep) - min(losep)
        if abs(step) < STEP:
            continue
        flagged += 1
        if sprd < 0.002 and ssprd < 0.002:
            verdict = "TWO HALVES -- legs vertical, so not a pose"
        elif ssprd >= 0.002:
            verdict = "legs SPLAY (%.0f mm) -- posed, read with care" % (
                ssprd * 1000)
        else:
            verdict = "a lean, or mixed"
        print("%-30s step %+7.1f mm   centre spread %4.1f mm   sep spread "
              "%5.1f mm   %s"
              % (name, step * 1000, sprd * 1000, ssprd * 1000, verdict))
        for label, half, lx, rx, sep, mid in rows:
            print("      %-10s %-6s left %+8.4f  right %+8.4f  sep %7.4f  "
                  "centre %+7.1f mm" % (label, half, lx, rx, sep, mid * 1000))
        for label, segs in chains:
            print("      %-12s %s"
                  % (label, "  ".join("%.4f" % s for s in segs)))
    print("\nwalked %d bundle(s); %d flagged, %d had no usable humanoid pair"
          % (walked, flagged, unmapped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
