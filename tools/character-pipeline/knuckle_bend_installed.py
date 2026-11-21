# -*- coding: utf-8 -*-
"""How much knuckle bend does an INSTALLED character's hand still carry?

    python knuckle_bend_installed.py <dir-of-yargchar>
    python knuckle_bend_installed.py <a.yargchar> [b.yargchar ...]

WHY THIS EXISTS. This file records that the VRM add-on applies a T-pose of its own and
**flattens hands**: of 35 characters rebuilt both ways, *every single `auto` build reads a
knuckle bend of exactly 0.0 degrees* except Pomni, and 25 of them carried authored bend that was
being destroyed -- Vigilante 87.0, Peacemaker 74.5, The Rock 36.2, Scott Hall 34.8, Batman 27.9.

That measurement was made on rebuilds from sources. It has never been made on the bundles that
are actually installed, which is what the game loads and what Jay is looking at when he reports
a hand. Elite Terrorist has no surviving `.vrm`, so a rebuild comparison cannot be made for him
at all -- but the installed file can still be asked what bend it carries.

WHAT IS MEASURED. For each finger, the angle at the MIDDLE joint between the proximal->
intermediate segment and the intermediate->distal segment. 0 degrees is a straight finger; a
relaxed hand carries 20-90. Taken JOINT TO JOINT from the humanoid map, never from bone axes --
a bone's tail is synthesised wherever the rig does not pin one, so an axis-based version of this
measures the importer. `fingerpose.py` got that wrong once by summing bone axes and reported a
32.5 degree curl on a hand that reads 0.0 from the file.

TWO KINDS OF ZERO, AND THEY ARE NOT THE SAME THING:

  * a finger whose three slots are all mapped and which reads 0.0 -- FLATTENED, and in
    principle recoverable by rebuilding with `VRM_EXPORT_POSE=rest`.
  * a finger whose slots are missing -- there is nothing to measure and nothing to recover.
    Printed as `-`, never as 0.0, because a blank and a zero mean opposite things here and
    averaging them together would hide every mitten hand on the roster.

Nothing is written.
"""
import math
import os
import sys

import cloth_collide_installed as cci
import UnityPy

FINGERS = ["Thumb", "Index", "Middle", "Ring", "Little"]


def bend(a, b, c):
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - b[i] for i in range(3)]
    nu = math.sqrt(sum(x * x for x in u))
    nv = math.sqrt(sum(x * x for x in v))
    if nu < 1e-9 or nv < 1e-9:
        return None
    d = sum(u[i] * v[i] for i in range(3)) / (nu * nv)
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def measure(path):
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
    for f in FINGERS:
        pts = [pos("Right %s %s" % (f, j))
               for j in ("Proximal", "Intermediate", "Distal")]
        out[f] = None if any(p is None for p in pts) else bend(*pts)
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
        rows.append((name, vals))

    def best(v):
        got = [x for x in v.values() if x is not None]
        return max(got) if got else -1.0

    rows.sort(key=lambda t: -best(t[1]))
    print("Knuckle bend in degrees, right hand, measured joint to joint in the INSTALLED")
    print("bundle. 0.0 is a straight finger. '-' means the slots are not mapped -- nothing")
    print("to measure, which is NOT the same as a zero.")
    print()
    print("%-26s %s %8s %6s" % ("character", " ".join("%8s" % f for f in FINGERS),
                                "max", "mapped"))
    print("-" * 94)
    flat, bent, mitten = [], [], []
    for name, v in rows:
        cells = " ".join(("%8.1f" % v[f]) if v[f] is not None else "%8s" % "-"
                         for f in FINGERS)
        n = sum(1 for f in FINGERS if v[f] is not None)
        m = best(v)
        print("%-26s %s %8s %4d/5" % (name[:26], cells,
                                      ("%.1f" % m) if m >= 0 else "-", n))
        if n == 0:
            mitten.append(name)
        elif m < 0.05:
            flat.append(name)
        else:
            bent.append(name)

    print()
    print("%d characters: %d carry bend, %d read FLAT (every mapped finger 0.0), %d have no"
          % (len(rows), len(bent), len(flat), len(mitten)))
    print("mapped finger at all.")
    print()
    print("A FLAT row is the add-on's T-pose estimate having replaced authored bend, and is in")
    print("principle recoverable by rebuilding with VRM_EXPORT_POSE=rest -- but only if the")
    print("source and recipe still exist. A row with few mapped fingers is a mitten hand and")
    print("has nothing to recover: no knob reaches a bone the rig does not have.")
    if errs:
        print()
        for name, why in errs:
            print("UNMEASURED  %-26s %s" % (name[:26], why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
