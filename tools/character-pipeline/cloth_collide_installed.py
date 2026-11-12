# -*- coding: utf-8 -*-
"""cloth_collide, run against the INSTALLED .yargchar instead of a .vrm.

Only 30 of the 65 installed characters still have a .vrm on this machine, so a
sweep that reads .vrm files covers less than half the set and would report the
other half as clean by never looking at them. The spring-bone configuration is
in the bundle and is fully readable:

    Vrm10Instance.SpringBone.Springs[]   name, joints, collider groups
    VRM10SpringBoneJoint                 per-bone stiffness/drag/radius
    VRM10SpringBoneCollider              ColliderType, Offset, Radius, Tail

so the chain structure, the collider shapes and the rest skeleton all come out
of the file that the game actually loads -- which is the only thing a claim
about an installed character may rest on.

Same measurement as cloth_collide.py: for each spring chain, which humanoid
part its joints hug, and whether that part carries any collider. A chain whose
part has no collider is UNGUARDED -- the limb passes through the cloth, because
nothing in the simulation represents the limb.

    python cloth_collide_installed.py <dir-of-yargchar | file.yargchar ...>

CLOTH_CONTROL=1 empties the collider list, so every chain must flag.
"""
import math
import os
import re
import sys

import UnityPy

# Chest springs sit ON the torso and are deliberately given no collider --
# handing them the torso capsule would push them out of the body they belong
# to. Same regex as vrm_colliders.CHEST, and it has to be here too: without it
# the sweep reports Alcina Dimitrescu's `breast.L` and `breast.R` as unguarded,
# which is true and is not a defect. A check that flags a decision as a fault
# teaches the reader to skim its output.
CHEST = r"(breast|bust|pectoral|boob)"

CHAINS = [
    ("torso", ["Hips", "Spine", "Chest", "UpperChest", "Neck", "Head"]),
    ("leftLeg", ["LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "LeftToes"]),
    ("rightLeg", ["RightUpperLeg", "RightLowerLeg", "RightFoot",
                  "RightToes"]),
    ("leftArm", ["LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand"]),
    ("rightArm", ["RightShoulder", "RightUpperArm", "RightLowerArm",
                  "RightHand"]),
]


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


def seg_dist(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    L2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2
    if L2 < 1e-12:
        return math.dist(p, a)
    t = ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]
         + (p[2] - a[2]) * ab[2]) / L2
    t = max(0.0, min(1.0, t))
    return math.dist(p, (a[0] + ab[0] * t, a[1] + ab[1] * t,
                         a[2] + ab[2] * t))


def hname(human, key):
    """Unity's human-bone name for `key`, in either spelling."""
    spaced = re.sub(r"(?<!^)([A-Z])", lambda m: " " + m.group(1), key)
    for c in (key, spaced):
        if c in human:
            return human[c]
    return None


def read(path):
    """Everything this check needs, straight out of the bundle."""
    env = UnityPy.load(path)
    objs = {}
    for obj in env.objects:
        try:
            objs[obj.path_id] = (obj.type.name, obj)
        except Exception:                                        # noqa: BLE001
            pass

    human = {}
    tf = {}
    go_tf = {}
    springs = []
    joints = {}
    colliders = {}
    groups = {}

    for pid, (ty, obj) in objs.items():
        if ty == "Avatar":
            d = obj.read()
            hd = getattr(d, "m_HumanDescription", None)
            for e in (getattr(hd, "m_Human", None) or []):
                bn = getattr(e, "m_BoneName", None)
                hn = getattr(e, "m_HumanName", None)
                if bn and hn:
                    human[hn] = bn
        elif ty == "Transform":
            d = obj.read()
            go = getattr(d, "m_GameObject", None)
            gid = getattr(go, "path_id", 0) if go is not None else 0
            nm = None
            if go is not None:
                try:
                    nm = go.read().m_Name
                except Exception:                                # noqa: BLE001
                    nm = None
            lp = getattr(d, "m_LocalPosition", None)
            lr = getattr(d, "m_LocalRotation", None)
            ls = getattr(d, "m_LocalScale", None)
            fa = getattr(d, "m_Father", None)
            tf[pid] = {
                "name": nm,
                "p": (lp.x, lp.y, lp.z) if lp is not None else (0, 0, 0),
                "q": ((lr.w, lr.x, lr.y, lr.z) if lr is not None
                      else (1, 0, 0, 0)),
                "s": (ls.x, ls.y, ls.z) if ls is not None else (1, 1, 1),
                "f": getattr(fa, "path_id", 0) if fa is not None else 0,
            }
            if gid:
                go_tf[gid] = pid
        elif ty == "MonoBehaviour":
            try:
                t = obj.read_typetree()
                cn = obj.read().m_Script.read().m_ClassName
            except Exception:                                    # noqa: BLE001
                continue
            if cn == "Vrm10Instance":
                sb = t.get("SpringBone", {}) or {}
                for s in sb.get("Springs", []) or []:
                    springs.append((
                        s.get("Name", "?"),
                        [j["m_PathID"] for j in s.get("Joints", []) or []],
                        [c["m_PathID"]
                         for c in s.get("ColliderGroups", []) or []],
                    ))
            elif cn == "VRM10SpringBoneJoint":
                joints[pid] = (t["m_GameObject"]["m_PathID"],
                               t.get("m_stiffnessForce", 0.0),
                               t.get("m_dragForce", 0.0),
                               t.get("m_gravityPower", 0.0),
                               t.get("m_jointRadius", 0.0))
            elif cn == "VRM10SpringBoneCollider":
                colliders[pid] = t
            elif cn == "VRM10SpringBoneColliderGroup":
                groups[pid] = [c["m_PathID"]
                               for c in (t.get("Colliders", []) or [])]

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

    return human, tf, go_tf, springs, joints, colliders, groups, world


def report(path):
    name = os.path.basename(path).replace(".yargchar", "")
    human, tf, go_tf, springs, joints, colliders, groups, world = read(path)
    if not springs:
        print("%-34s no spring chains" % name[:34])
        return 0, 0

    by_name = {}
    for pid, n in tf.items():
        if n["name"] and n["name"] not in by_name:
            by_name[n["name"]] = pid

    node_part = {}
    segments = []
    for part, keys in CHAINS:
        got = [b for b in (hname(human, k) for k in keys)
               if b and b in by_name]
        for b in got:
            node_part[b] = part
        for a, b in zip(got, got[1:]):
            segments.append((part, world(by_name[a])[0],
                             world(by_name[b])[0]))
    if not segments:
        print("%-34s no humanoid segments" % name[:34])
        return 0, 0

    if os.environ.get("CLOTH_CONTROL"):
        colliders = {}
        print("CONTROL: collider list emptied -- every chain must flag")

    # Where each collider actually sits, and which part it guards.
    cshapes = {}
    guarded = set()
    for pid, t in colliders.items():
        gid = t["m_GameObject"]["m_PathID"]
        tid = go_tf.get(gid)
        if tid is None:
            continue
        wp, wq, ws = world(tid)
        off = t.get("Offset", {}) or {}
        tail = t.get("Tail", {}) or {}

        def to_world(v):
            sc = (v.get("x", 0.0) * ws[0], v.get("y", 0.0) * ws[1],
                  v.get("z", 0.0) * ws[2])
            r = qrot(wq, sc)
            return (wp[0] + r[0], wp[1] + r[1], wp[2] + r[2])

        a = to_world(off)
        b = to_world(tail) if t.get("ColliderType", 0) == 1 else a
        cshapes[pid] = (a, b, float(t.get("Radius", 0.0)))

        # Walk up to the nearest humanoid bone, so a collider on a child bone
        # still counts as guarding the limb it belongs to.
        k, seen = tid, set()
        while k and k in tf and k not in seen:
            seen.add(k)
            nm = tf[k]["name"]
            if nm in node_part:
                guarded.add(node_part[nm])
                break
            k = tf[k]["f"]

    rows = []
    chest = 0
    for sname, jids, gids in springs:
        if re.search(CHEST, sname or "", re.I):
            chest += 1
            continue
        pts = []
        for jid in jids:
            j = joints.get(jid)
            if not j:
                continue
            tid = go_tf.get(j[0])
            if tid is not None:
                pts.append(world(tid)[0])
        if not pts:
            continue
        mine = [c for g in gids for c in groups.get(g, []) if c in cshapes]
        tally = {}
        dcol = 1e9
        for pi, p in enumerate(pts):
            best = min(segments, key=lambda s: seg_dist(p, s[1], s[2]))
            tally[best[0]] = tally.get(best[0], 0) + 1
            # The anchor is excluded from the collider distance; a collider
            # cannot move it. See the note in cloth_collide.py -- UniVRM's
            # simulation collides tails only, and joints[0] is never a tail.
            if pi == 0:
                continue
            for cid in mine:
                a, b, r = cshapes[cid]
                dcol = min(dcol, seg_dist(p, a, b) - r)
        part = max(tally.items(), key=lambda kv: kv[1])[0]
        rows.append((sname, part, part in guarded, len(pts), dcol))

    bad = [r for r in rows if not r[2]]
    print("%-34s %2d chains, %d collider(s) on %s; %d UNGUARDED%s"
          % (name[:34], len(rows), len(cshapes),
             "+".join(sorted(guarded)) or "nothing", len(bad),
             "  (%d chest chain(s) skipped on purpose)" % chest if chest
             else ""))
    for nm, part, ok, nj, dc in rows:
        if ok and not os.environ.get("CLOTH_VERBOSE"):
            continue
        print("    %-30s %-9s %2d joints  nearest collider surface %s"
              % (nm[:30], part, nj,
                 "%.3f m" % dc if dc < 1e8 else "none at all"))
    return len(rows), len(bad)


def main():
    files = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.endswith(".yargchar")]
        else:
            files.append(a)
    nfile = nbad = nchain = nbadchain = 0
    for f in files:
        try:
            tot, bad = report(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-34s ERROR %s" % (os.path.basename(f)[:34], e))
            continue
        nfile += 1
        nchain += tot
        nbadchain += bad
        if bad:
            nbad += 1
    print("")
    print("%d bundle(s) read: %d of %d spring chains unguarded, "
          "across %d character(s)" % (nfile, nbadchain, nchain, nbad))


main()
