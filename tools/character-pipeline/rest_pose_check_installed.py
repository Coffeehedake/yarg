# -*- coding: utf-8 -*-
"""Is an installed character's rest pose actually a T-pose? Measured JOINT TO JOINT.

    python rest_pose_check_installed.py <dir-of-yargchar>
    python rest_pose_check_installed.py <a.yargchar> [b.yargchar ...]

WHY THIS EXISTS. Jay reported on 2026-11-21 that Prix's right arm and hand are "twisted around
and crushed". This file already carries the mechanism that would do that, written up for a
different reason: **Unity builds the humanoid avatar on the bind pose**, so a character shipped
bent has every muscle axis mis-aimed, and every retargeted animation then drives his limbs along
axes that are not his. The entry calls it "the same fault as the hands, applied to the whole
body", and names Prix as the worst case -- a Mixamo rig whose T-pose step *prints nothing*, so
the VRM add-on was the only thing ever T-posing him, with the build-time guard firing on him at
`forearm 21.2 deg`.

That guard runs at BUILD time, on the Blender scene. This one runs on the INSTALLED bundle, so
it can answer the question that actually matters for a character already on disk: whatever the
builder did or did not do, is the file the game loads a T-pose or not?

MEASURE JOINT TO JOINT, NEVER BY BONE AXIS. This is the trap the build-time guard fell into
first, and it is worth restating because the wrong answer looks better than the right one. Its
first version asked which way each BONE POINTS and reported Prix's arms as 90.0 degrees off X
and his legs as 180.0 off vertical -- both sides, upper and lower, to the decimal. **Numbers
that round are not a pose.** A bone's tail is synthesised wherever the rig does not pin one, so
a bone's axis is a fact about the IMPORTER; the head of the next joint down is a fact about the
MODEL. Measuring head-to-head turned those into 21.2 and 77.3, which matched an independent
measurement of the same rigs.

So each segment here is the vector between two humanoid joints' world positions:

    upper arm   RightUpperArm  -> RightLowerArm     expected along  X
    forearm     RightLowerArm  -> RightHand         expected along  X
    thigh       RightUpperLeg  -> RightLowerLeg     expected along -Y
    shin        RightLowerLeg  -> RightFoot         expected along -Y

and the number is the angle between that vector and the axis it should lie on. Unity is Y-up and
X-across, which is why "down" is -Y here; in Blender the same check is -Z, and reading one
convention's answer in the other is its own well-recorded way to be wrong.

READ THE POPULATION. A few degrees is normal -- rigs are not surveyed. What a finding looks like
is a character far outside what the other sixty-four do, so the roster is printed sorted by worst
angle and the quartiles are printed under it. Nothing is written.
"""
import math
import os
import sys

import cloth_collide_installed as cci

SEGMENTS = [
    ("upperarm.R", "RightUpperArm", "RightLowerArm", (1.0, 0.0, 0.0)),
    ("forearm.R", "RightLowerArm", "RightHand", (1.0, 0.0, 0.0)),
    ("upperarm.L", "LeftUpperArm", "LeftLowerArm", (-1.0, 0.0, 0.0)),
    ("forearm.L", "LeftLowerArm", "LeftHand", (-1.0, 0.0, 0.0)),
    ("thigh.R", "RightUpperLeg", "RightLowerLeg", (0.0, -1.0, 0.0)),
    ("shin.R", "RightLowerLeg", "RightFoot", (0.0, -1.0, 0.0)),
    ("thigh.L", "LeftUpperLeg", "LeftLowerLeg", (0.0, -1.0, 0.0)),
    ("shin.L", "LeftLowerLeg", "LeftFoot", (0.0, -1.0, 0.0)),
]


def angle_to(v, axis):
    n = math.sqrt(sum(x * x for x in v))
    if n <= 1e-9:
        return None
    d = sum(v[i] * axis[i] for i in range(3)) / n
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def measure(path):
    import UnityPy
    env = UnityPy.load(path)
    slots = None
    for o in env.objects:
        if o.type.name == "Avatar":
            hd = o.read_typetree().get("m_HumanDescription") or {}
            slots = dict((r.get("m_HumanName"), r.get("m_BoneName"))
                         for r in (hd.get("m_Human") or []))
            break
    if slots is None:
        return None, "no Avatar"

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    by_name = {}
    for pid, rec in tf.items():
        by_name.setdefault(rec.get("name"), pid)

    def pos(slot):
        bone = slots.get(slot)
        if bone is None or bone not in by_name:
            return None
        return world(by_name[bone])[0]

    out = {}
    for label, a_slot, b_slot, axis in SEGMENTS:
        pa, pb = pos(a_slot), pos(b_slot)
        if pa is None or pb is None:
            out[label] = None
            continue
        out[label] = angle_to([pb[i] - pa[i] for i in range(3)], axis)
    return out, None


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            paths.append(a)

    rows, errs = [], []
    for p in paths:
        name = os.path.basename(p)[:-9]
        try:
            vals, err = measure(p)
        except Exception as exc:                                    # noqa: BLE001
            errs.append((name, "%s: %s" % (type(exc).__name__, exc)))
            continue
        if err:
            errs.append((name, err))
            continue
        got = [v for v in vals.values() if v is not None]
        if not got:
            errs.append((name, "no limb segment measurable -- UNMEASURED, not 'straight'"))
            continue
        rows.append((name, vals, max(got)))

    labels = [s[0] for s in SEGMENTS]
    rows.sort(key=lambda t: -t[2])
    print("Angle of each limb segment away from the axis a T-pose puts it on, in degrees.")
    print("Measured JOINT TO JOINT in the installed bundle's rest pose. Unity is Y-up.")
    print()
    print("%-26s %s %8s" % ("character", " ".join("%10s" % l for l in labels), "worst"))
    print("-" * (27 + 11 * len(labels) + 9))
    for name, vals, worst in rows:
        cells = " ".join(("%10.1f" % vals[l]) if vals[l] is not None else "%10s" % "-"
                         for l in labels)
        print("%-26s %s %8.1f" % (name[:26], cells, worst))

    if rows:
        ws = sorted(r[2] for r in rows)
        def q(f):
            return ws[min(len(ws) - 1, int(len(ws) * f))]
        print()
        print("POPULATION of %d: worst-segment angle  median %.1f  p75 %.1f  p90 %.1f  max %.1f"
              % (len(ws), q(0.50), q(0.75), q(0.90), ws[-1]))
        print("A few degrees is normal; rigs are not surveyed. A finding is a character well")
        print("outside what the rest of the roster does, not a character above any round number.")
        if ws[0] == ws[-1]:
            print("EVERY character reads the same worst angle, which is this tool measuring")
            print("itself rather than them.")
    if errs:
        print()
        for name, why in errs:
            print("UNMEASURED  %-26s %s" % (name[:26], why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
