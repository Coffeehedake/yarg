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

STATURE IS A BONE MEASUREMENT, AND A LOW HEAD BONE INFLATES EVERY RATIO.

Stature is foot bone to head bone, which is shorter than the character: it
excludes the skull above the head bone and the foot below the ankle. On most
of this set that comes to about 0.87-0.89 of mesh height. The Rock's old build
sat at 1.536 / 1.96 = 0.78, so every ratio of his was inflated by about 12%
before anything else was wrong -- which is part of why his `reach` read 1.268
against a median of 0.938.

So read a single high ratio with that in mind, and prefer the ones where the
two sides of the comparison share a denominator. His SHOULDERS were the real
finding because 0.548 is more than twice the median and no denominator error
of 12% explains that. His `reach` was not: a rebuilt, correct build also reads
1.272, because this mesh's hands genuinely sit far out and fitting the hand
bones to them is what makes the hands WORK.

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


def read_vrm(path):
    """The same humanoid map and world positions, out of a .vrm.

    Worth having because the alternative is finding out after a Unity export,
    and an export costs minutes where this costs nothing. VRM 1.0 keeps the
    map at extensions.VRMC_vrm.humanoid.humanBones as camelCase names; they
    are normalised to Unity's spelling so one set of comparisons serves both.
    """
    import json
    import struct
    d = open(path, "rb").read()
    off, g = 12, None
    while off < len(d):
        ln, ty = struct.unpack_from("<II", d, off)
        if ty == 0x4E4F534A:
            g = json.loads(d[off + 8:off + 8 + ln].decode("utf-8"))
        off += 8 + ln + ((4 - ln % 4) % 4)
    if not g:
        return {}, {}
    nodes = g.get("nodes", [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []) or []:
            parent[c] = i

    def qrot(q, v):
        x, y, z, w = q
        tx = 2.0 * (y * v[2] - z * v[1])
        ty = 2.0 * (z * v[0] - x * v[2])
        tz = 2.0 * (x * v[1] - y * v[0])
        return (v[0] + w * tx + (y * tz - z * ty),
                v[1] + w * ty + (z * tx - x * tz),
                v[2] + w * tz + (x * ty - y * tx))

    def qmul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz)

    # FULL TRS, because the first version skipped rotation on the stated
    # grounds that "a VRM's rest hierarchy is written with identity rotations".
    # That is not true of this exporter's output, and the tool's own numbers
    # said so immediately: The Rock came back with his FEET 0.6 m above his
    # HEAD and his hand directly above his shoulder. An assumption written
    # confidently into a comment, disproved by one run of the thing it was
    # written in.
    def world(i, seen=None):
        seen = seen or set()
        if i in seen:
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0)
        seen.add(i)
        n = nodes[i]
        t = n.get("translation", [0, 0, 0])
        q = n.get("rotation", [0, 0, 0, 1])
        sc = n.get("scale", [1, 1, 1])
        par = parent.get(i)
        if par is None:
            return tuple(t), tuple(q), tuple(sc)
        pp, pq, ps = world(par, seen)
        scaled = (t[0] * ps[0], t[1] * ps[1], t[2] * ps[2])
        r = qrot(pq, scaled)
        return ((pp[0] + r[0], pp[1] + r[1], pp[2] + r[2]),
                qmul(pq, q),
                (ps[0] * sc[0], ps[1] * sc[1], ps[2] * sc[2]))

    hb = (((g.get("extensions") or {}).get("VRMC_vrm") or {})
          .get("humanoid") or {}).get("humanBones") or {}
    human, pos = {}, {}
    for k, v in hb.items():
        idx = v.get("node") if isinstance(v, dict) else None
        if idx is None or idx >= len(nodes):
            continue
        unity = k[0].upper() + k[1:]
        bn = nodes[idx].get("name") or ("node%d" % idx)
        human[unity] = bn
        pos[bn] = world(idx)[0]
    return human, pos


def measure(path):
    if path.lower().endswith(".vrm"):
        human, pos = read_vrm(path)
    else:
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
