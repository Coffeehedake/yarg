# -*- coding: utf-8 -*-
"""Every humanoid bone's X against its height -- a lean and a step look alike
   until something samples BETWEEN the two ends.

    python plumb_check_installed.py <dir-of-yargchar | file.yargchar ...>

`half_body_check_installed.py` reports a character as "two half-skeletons" when
its lower pairs share one centre and its upper pairs share another. On The
Mandalorian it read -18.5 mm for hips, knees and feet and +18.7 mm for
shoulders, elbows and hands, and this project wrote that up as a 37.2 mm STEP
with "no gradient between them".

There is no gradient between them in that output because **nothing in that
check lies between them**. Its six pairs are the legs and the arms. On a
standing figure the three leg pairs inherit the hip bone's X rigidly, and on a
T-posed figure the three arm pairs inherit the shoulder's; so the six numbers
are two numbers, measured three times each, and the spine -- the only thing
that could tell a lean from a step -- is not among them. Three decimal places
of agreement between a bone and its own child is not evidence about anything.

So this walks the SPINE and prints X at every height, with the limb roots
beside it. A lean comes out as a gradient, a step as a step, and the
difference decides the fix: a lean is a posture, which the character may have
been authored with, while a step is a rig that was assembled in two pieces.

Read it with a control. Spartan Mark V is square and prints 0.0 at every
height; a character whose spine wanders by millimetres is being read against
an instrument that demonstrably returns zero when there is nothing there.

PLUMB_MM sets the reporting threshold, default 5.0 mm.
"""
import os
import sys

import cloth_collide_installed as cci

PLUMB_MM = float(os.environ.get("PLUMB_MM", "5.0"))

SPINE = ["Hips", "Spine", "Chest", "UpperChest", "Neck", "Head"]
LIMBS = [("LeftUpperLeg", "RightUpperLeg"), ("LeftFoot", "RightFoot"),
         ("LeftShoulder", "RightShoulder"), ("LeftUpperArm", "RightUpperArm"),
         ("LeftHand", "RightHand")]


def measure(path):
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    name_pid = {}
    for pid, n in tf.items():
        if n.get("name"):
            name_pid.setdefault(n["name"], pid)

    def wp(key):
        bn = cci.hname(human, key)
        if not bn or bn not in name_pid:
            return None
        return world(name_pid[bn])[0]

    spine = []
    for k in SPINE:
        p = wp(k)
        if p is not None:
            spine.append((k, p[0], p[1]))
    pairs = []
    for ln, rn in LIMBS:
        a, b = wp(ln), wp(rn)
        if a is not None and b is not None:
            pairs.append((ln.replace("Left", ""), 0.5 * (a[0] + b[0]),
                          0.5 * (a[1] + b[1])))
    return spine, pairs


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

    for f in files:
        name = os.path.basename(f)[:-9]
        try:
            spine, pairs = measure(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-30s UNREADABLE: %s" % (name, e))
            continue
        rows = [(y, "spine  " + k, x) for k, x, y in spine] + \
               [(y, "pair   " + k, x) for k, x, y in pairs]
        rows.sort()
        if not rows:
            print("%s -- no humanoid bones" % name)
            continue
        print("")
        print("%s" % name)
        print("    %-8s %-22s %10s %12s"
              % ("height", "what", "x (mm)", "vs the one below"))
        prev = None
        for y, what, x in rows:
            step = "" if prev is None else "%+8.1f" % ((x - prev) * 1000)
            print("    %-8.4f %-22s %10.1f %12s" % (y, what, x * 1000, step))
            prev = x
        xs = [x for _, _, x in rows]
        rng = (max(xs) - min(xs)) * 1000
        # A LEAN spreads its travel over many steps; a STEP puts most of it in
        # one. Printing the largest single step beside the total range is what
        # separates them, and neither number alone can.
        biggest = max((abs(rows[i][2] - rows[i - 1][2]) * 1000, rows[i][1],
                       rows[i - 1][1]) for i in range(1, len(rows))) \
            if len(rows) > 1 else (0.0, "", "")
        verdict = "FLAT" if rng < PLUMB_MM else (
            "A STEP: %.0f%% of the travel is in one gap"
            % (100.0 * biggest[0] / rng) if biggest[0] > 0.5 * rng
            else "A LEAN: the travel is spread over the chain")
        print("    range %.1f mm over %d bones; largest single gap %.1f mm "
              "(%s -> %s) -- %s"
              % (rng, len(rows), biggest[0], biggest[2], biggest[1], verdict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
