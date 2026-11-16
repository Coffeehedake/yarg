# -*- coding: utf-8 -*-
"""body_yaw_check_installed.py <bundle> [...] -- is the character FACING front?

A character can have every bone and every vertex perfectly mirrored about its
own midline and still look wrong on a podium, because a stance symmetric about
that midline projects asymmetrically when the midline is not facing the camera.
The hip rotated toward the viewer reads as sticking out, and no symmetry check
will ever flag it: Spartan Mark V passed every one of them while standing 20
degrees off, and was reported twice for a leg.

So this measures the yaw of lines that are left-right BY CONSTRUCTION -- hips,
shoulders, knees, feet, hands -- in WORLD space.

READ THE SPREAD, NOT THE MEAN. The two faults this can see are told apart by
whether the lines agree:

  * every line agreeing (spread near 0) is the whole character TURNED
  * one line arguing with the others is a LIMB out of place, and turning the
    body would bury it rather than fix it

Across the installed 65 that separates cleanly: Aiko -29.95 at spread 0.15,
Spartan Mark V +20.00 at 0.00 and Kronk -6.97 at 0.00 are turned, while Steve
(+7.47 at spread 18.27), Jessica Rabbit, The Mandalorian, Alastor, Peacemaker,
Vigilante and Alcina Dimitrescu have one line disagreeing and are not.

The hands are included here and excluded from patch_body_yaw.py's decision on
purpose: they are the end of the longest chain and carry the model's own pose,
so they disagree even on a square character. Printed because that is
informative; not voted on.
"""
import math
import os
import sys

sys.path.insert(0, r"C:\dev\YARG - Open Source Contributions\yarg\tools\character-pipeline")
from cloth_collide_installed import read

LINES = [("hips", ("thigh.L", "thigh.R"), ("LeftUpperLeg", "RightUpperLeg")),
         ("shoulders", ("upper_arm.L", "upper_arm.R"),
          ("LeftUpperArm", "RightUpperArm")),
         ("feet", ("foot.L", "foot.R"), ("LeftFoot", "RightFoot")),
         ("knees", ("shin.L", "shin.R"), ("LeftLowerLeg", "RightLowerLeg")),
         ("hands", ("hand.L", "hand.R"), ("LeftHand", "RightHand"))]

for path in sys.argv[1:]:
    human, tf, go_tf, springs, joints, colliders, groups, world = read(path)
    by = {}
    for pid, n in tf.items():
        if n["name"]:
            by.setdefault(n["name"], pid)
    print("\n######## %s" % os.path.basename(path))
    got = []
    for label, names, hum in LINES:
        a = by.get(names[0]) or by.get(human.get(hum[0], ""))
        b = by.get(names[1]) or by.get(human.get(hum[1], ""))
        if a is None or b is None:
            print("    %-10s  bones not found" % label)
            continue
        pa, pb = world(a)[0], world(b)[0]
        dx, dz = pb[0] - pa[0], pb[2] - pa[2]
        if math.hypot(dx, dz) < 1e-4:
            print("    %-10s  the two bones coincide" % label)
            continue
        yaw = math.degrees(math.atan2(dz, dx))
        got.append(yaw)
        print("    %-10s left (%+.4f %+.4f) right (%+.4f %+.4f)  "
              "yaw %+7.2f deg   width %.4f"
              % (label, pa[0], pa[2], pb[0], pb[2], yaw,
                 math.hypot(dx, dz)))
    if got:
        m = sum(got) / len(got)
        spread = max(got) - min(got)
        print("    ---> mean yaw %+.2f deg over %d line(s), spread %.2f deg"
              % (m, len(got), spread))
        if abs(m) > 3.0 and spread < 5.0:
            print("         EVERY left-right line agrees, so this is the "
                  "whole character turned, not one limb displaced.")
