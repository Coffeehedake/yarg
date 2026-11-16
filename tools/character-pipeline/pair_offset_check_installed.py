# -*- coding: utf-8 -*-
"""Left/right asymmetry that needs NO centreline and NO mirror assumption.

    python pair_offset_check_installed.py <dir-of-yargchar | file.yargchar ...>

A pair's X positions cannot be compared without knowing where the middle is,
and the middle is often exactly what cannot be established. On Jessica Rabbit
every attempt failed: the midpoint of a slice's extremes is a measurement of
her outliers, a median over a two-legged band lands on whichever leg carries
more vertices, and her band medians spread 169.6 mm. `half_body_check` can
still compare one half against the other, but it cannot say which half is
wrong.

HEIGHT and DEPTH need no middle. For a pair the rig itself calls left and
right, dy and dz should both be zero, and any difference is measured against
nothing but the pair. That is the whole idea, and it is why this check has a
true zero where the X-based ones do not.

**Spartan Mark V reads 0.0 mm on every pair and every axis.** That control is
what makes a reading here mean something -- it is a correct symmetric rig, so
the instrument demonstrably CAN return zero, and a non-zero is the subject
rather than the method. Run him alongside anything new.

Jessica Rabbit, 2026-11-16:

    UpperLeg   dy  +92.4  dz   +3.0     thigh.L / thigh.R
    LowerLeg   dy  +92.4  dz   +3.0     shin.L  / shin.R
    Foot       dy  +92.4  dz   +3.0     foot.L  / foot.R
    Shoulder   dy   +0.1  dz   -2.7     shoulder.L / shoulder.R
    UpperArm   dy  +29.0  dz  -74.1     upper_arm.L / upper_arm.R
    LowerArm   dy  +29.0  dz  -74.1     forearm.L / forearm.R
    Hand       dy  +29.0  dz  -74.1     hand.L / hand.R

Her whole right leg is 92.4 mm HIGHER than her left and her whole right arm
29.0 mm higher and 74.1 mm further back, while her SHOULDER bones are
symmetric to a tenth of a millimetre. Each limb is internally consistent --
all three joints displaced by the identical amount -- so whole limbs are
displaced rather than deformed, the same signature as the half-skeleton step.
Identical in all four of her snapshots from that day, so it predates every
patch and comes from her source rig.

WHAT THIS CANNOT TELL YOU is whether the displacement was AUTHORED. A raised
leg is also what a glamour pose looks like, and this project has been bitten
twice by reading a deliberate choice as a defect. Two things argue against a
pose here and they are worth checking on any new finding: her legs are
straight vertical columns (hip, knee and foot share one x, and dz is 3 mm), and
a posed leg bends. Settle it by LOOKING at the character before changing
anything.

PAIR_MM sets the reporting threshold in millimetres, default 5.0.
"""
import math
import os
import sys

import cloth_collide_installed as cci

PAIR_MM = float(os.environ.get("PAIR_MM", "5.0"))

PAIRS = [("UpperLeg", "LeftUpperLeg", "RightUpperLeg"),
         ("LowerLeg", "LeftLowerLeg", "RightLowerLeg"),
         ("Foot", "LeftFoot", "RightFoot"),
         ("Shoulder", "LeftShoulder", "RightShoulder"),
         ("UpperArm", "LeftUpperArm", "RightUpperArm"),
         ("LowerArm", "LeftLowerArm", "RightLowerArm"),
         ("Hand", "LeftHand", "RightHand")]


def measure(path):
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
    for label, ln, rn in PAIRS:
        a, b = wp(ln), wp(rn)
        if a is None or b is None:
            continue
        rows.append((label, (b[1] - a[1]) * 1000, (b[2] - a[2]) * 1000,
                     human.get(ln) or "?", human.get(rn) or "?",
                     abs(b[0] - a[0])))
    return rows


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

    print("reporting a left/right height or depth difference of %.1f mm or "
          "more. Spartan Mark V is the control and reads 0.0 on every pair.\n"
          % PAIR_MM)
    walked = flagged = 0
    worst_of = []
    for f in files:
        name = os.path.basename(f)[:-9]
        try:
            rows = measure(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-30s UNREADABLE: %s" % (name, e))
            continue
        walked += 1
        if not rows:
            continue
        worst = max(max(abs(r[1]), abs(r[2])) for r in rows)
        worst_of.append((worst, name))
        if worst < PAIR_MM:
            continue
        flagged += 1
        # dy and dz are NOT the same finding, and lumping them together
        # reports a fault this project has already measured. A pure dz
        # difference with dy at zero is the body being TURNED -- Aiko reads
        # dz -100.2 mm on her legs with dy -0.0, and 190 mm of leg separation
        # rotated by the 29.95 deg `body_yaw_check_installed` already records
        # for her gives 94.9 mm. Same fault, second instrument. A dy
        # difference cannot come from a yaw at all: that is a limb at the
        # wrong HEIGHT, which is new.
        mdy = max(abs(r[1]) for r in rows)
        mdz = max(abs(r[2]) for r in rows)
        if mdy < 2.0 <= mdz:
            kind = "a TURN (yaw) -- cross-check body_yaw_check_installed"
        elif mdy >= PAIR_MM and mdz < PAIR_MM:
            kind = "a limb at the wrong HEIGHT"
        else:
            kind = "MIXED -- height and depth both"
        print("%s -- worst %.1f mm (dy %.1f, dz %.1f): %s"
              % (name, worst, mdy, mdz, kind))
        for label, dy, dz, ln, rn, sep in rows:
            if max(abs(dy), abs(dz)) < PAIR_MM:
                continue
            yaw = ""
            if sep > 1e-6 and abs(dz) >= PAIR_MM:
                r = max(-1.0, min(1.0, (dz / 1000.0) / sep))
                yaw = "  implies %+5.1f deg of yaw" % math.degrees(
                    math.asin(r))
            print("    %-10s dy %+8.1f mm  dz %+8.1f mm   %-16s %s"
                  % (label, dy, dz, (ln[:16] + " / " + rn[:16])[:34], yaw))

    print("\nwalked %d bundle(s); %d have a pair off by %.1f mm or more"
          % (walked, flagged, PAIR_MM))
    worst_of.sort(reverse=True)
    print("worst ten: %s"
          % ", ".join("%s %.0f" % (n, w) for w, n in worst_of[:10]))
    clean = [n for w, n in worst_of if w < 0.1]
    print("%d bundle(s) are symmetric to within 0.1 mm%s"
          % (len(clean), (": " + ", ".join(clean[:8])) if clean else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
