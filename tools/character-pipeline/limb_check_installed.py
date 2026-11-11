# limb_check, run against the INSTALLED .yargchar instead of a .vrm.
#
# Most of these characters no longer have a source file, and only 29 of 66
# still have a .vrm anywhere -- so a sweep over .vrm files silently covers
# less than half the set, and covers it with builds that may not be what is
# installed. Both problems go away here: the bundle carries everything needed.
#
#   * every bone's Transform (m_LocalPosition / m_LocalRotation / m_LocalScale)
#     and its parent, which compose into world positions
#   * the Avatar's m_HumanDescription.m_Human, a list of m_BoneName ->
#     m_HumanName, which is the humanoid map
#
# The measurement is the same one limb_check.py settled on and for the same
# reason: JOINT TO JOINT, from bone head positions only. A bone's own axis is
# not used, because the tail that defines it is synthesised wherever the
# hierarchy does not pin one, and reading those produced two confident, wrong
# reports of a Sonic wrist defect that does not exist.
#
# Validated against limb_check.py on the characters where both can run: the
# two must agree, and where they disagree the bundle is the authority, because
# it is the thing the game loads.
#
# Usage:  python limb_check_installed.py <dir-of-yargchar | file.yargchar ...>
import math
import os
import re
import sys

import UnityPy


def qrot(q, v):
    w, x, y, z = q
    vx, vy, vz = v
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def read_rig(path):
    env = UnityPy.load(path)
    tf, human = {}, {}
    objs = {}
    for obj in env.objects:
        try:
            objs[obj.path_id] = (obj.type.name, obj.read())
        except Exception:
            pass
    for _pid, (ty, d) in objs.items():
        if ty != "Avatar":
            continue
        hd = getattr(d, "m_HumanDescription", None)
        for e in (getattr(hd, "m_Human", None) or []):
            bn = getattr(e, "m_BoneName", None)
            hn = getattr(e, "m_HumanName", None)
            if bn and hn:
                human[hn] = bn
        break
    for pid, (ty, d) in objs.items():
        if ty != "Transform":
            continue
        go = getattr(d, "m_GameObject", None)
        nm = None
        if go is not None:
            try:
                nm = go.read().m_Name
            except Exception:
                nm = None
        lp = getattr(d, "m_LocalPosition", None)
        lr = getattr(d, "m_LocalRotation", None)
        ls = getattr(d, "m_LocalScale", None)
        fa = getattr(d, "m_Father", None)
        fid = getattr(fa, "path_id", 0) if fa is not None else 0
        tf[pid] = {
            "name": nm,
            "p": (lp.x, lp.y, lp.z) if lp is not None else (0, 0, 0),
            "q": (lr.w, lr.x, lr.y, lr.z) if lr is not None else (1, 0, 0, 0),
            "s": (ls.x, ls.y, ls.z) if ls is not None else (1, 1, 1),
            "f": fid,
        }
    cache = {}

    def world(pid, seen=None):
        if pid in cache:
            return cache[pid]
        seen = seen or set()
        if pid in seen or pid not in tf:
            return ((0, 0, 0), (1, 0, 0, 0), (1, 1, 1))
        seen.add(pid)
        n = tf[pid]
        if n["f"] and n["f"] in tf:
            pp, pq, ps = world(n["f"], seen)
        else:
            pp, pq, ps = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
        scaled = (n["p"][0] * ps[0], n["p"][1] * ps[1], n["p"][2] * ps[2])
        r = qrot(pq, scaled)
        wp = (pp[0] + r[0], pp[1] + r[1], pp[2] + r[2])
        wq = qmul(pq, n["q"])
        ws = (ps[0] * n["s"][0], ps[1] * n["s"][1], ps[2] * n["s"][2])
        cache[pid] = (wp, wq, ws)
        return cache[pid]

    pos = {}
    for pid, n in tf.items():
        if n["name"]:
            pos[n["name"]] = world(pid)[0]
    return human, pos


# Thresholds CALIBRATED against all 66 installed characters rather than
# guessed. The first version used "bent more than 30 degrees" for every joint,
# which is meaningless for the wrist: the index finger naturally starts off to
# one side of the wrist, so the population median there is 16.9 degrees and a
# perfectly healthy character reads 20. It flagged Shaggy Rogers at 35/36 --
# symmetric, and therefore almost certainly just how he is modelled.
#
# Measured over the 66:
#
#   joint   median  p90    max   | asymmetry: median  p90   max
#   elbow      0.0   0.0   15.4  |              0.0   0.0   0.0
#   wrist     16.9  23.6   36.1  |              0.0   2.7  16.0
#   knee       0.0   2.2    8.9  |              0.0   0.0   0.0
#   ankle     62.6  75.4   97.4  |              0.0   1.2  26.4
#
# ASYMMETRY is the signal worth trusting: its median is 0.0 at every joint,
# and elbow and knee asymmetry is exactly 0.0 for all 66. A character compared
# against its own other side needs no population baseline at all. Absolute
# angle is only meaningful where the population says the joint should be
# straight -- the elbow and the knee.
#
# (name, a, b, c, absolute-limit or None)
CHAINS = [("elbow", "UpperArm", "LowerArm", "Hand", 5.0),
          ("wrist", "LowerArm", "Hand", "IndexProximal", None),
          ("knee", "UpperLeg", "LowerLeg", "Foot", 5.0),
          ("ankle", "LowerLeg", "Foot", "Toes", None)]
ASYM_LIMIT = 5.0


def hname(human, side, key):
    """Unity's human-bone name for `key` on `side`, in either spelling."""
    spaced = re.sub(r"(?<!^)([A-Z])", lambda m: " " + m.group(1), key)
    cand = [side + key, side + " " + spaced]
    for c in cand:
        if c in human:
            return human[c]
    return None


def angle(a, b, c):
    if a is None or b is None or c is None:
        return None
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - b[0], c[1] - b[1], c[2] - b[2])
    lu = math.sqrt(sum(x * x for x in u))
    lv = math.sqrt(sum(x * x for x in v))
    if lu < 1e-9 or lv < 1e-9:
        return None
    d = sum(x * y for x, y in zip(u, v)) / (lu * lv)
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def check(path):
    human, pos = read_rig(path)
    name = os.path.basename(path).replace(".yargchar", "")
    if not human:
        print("%-38s no humanoid map in the bundle" % name[:38])
        return
    out, worst, flags = [], 0.0, []
    for label, a, b, c, limit in CHAINS:
        vals = []
        for side in ("Left", "Right"):
            # Unity spells body bones "LeftUpperArm" but FINGER bones
            # "Left Index Proximal", with spaces. Looking up only the first
            # form silently dropped every wrist row -- a missing row reads as
            # "nothing wrong there" exactly like a clean one.
            bn = [hname(human, side, x) for x in (a, b, c)]
            if None in bn:
                vals.append(None)
                continue
            vals.append(angle(*[pos.get(x) for x in bn]))
        l, r = vals
        if l is None or r is None:
            continue
        if limit is not None and max(l, r) > limit:
            flags.append("%s BENT %.1f/%.1f" % (label, l, r))
        if abs(l - r) > ASYM_LIMIT:
            flags.append("%s ASYM %.1f/%.1f (d=%.1f)" % (label, l, r, abs(l - r)))
        worst = max(worst, max(l, r) if limit is not None else abs(l - r))
        out.append("%s %.1f/%.1f" % (label, l, r))
    print("%-38s worst=%6.2f  %s%s"
          % (name[:38], worst, "  ".join(out),
             "   <-- " + "; ".join(flags) if flags else ""))


def main():
    args = sys.argv[1:]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.endswith(".yargchar")]
        else:
            files.append(a)
    for f in files:
        try:
            check(f)
        except Exception as e:
            print("%-38s ERROR %s" % (os.path.basename(f)[:38], e))


if __name__ == "__main__":
    main()
