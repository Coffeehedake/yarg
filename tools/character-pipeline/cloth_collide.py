# -*- coding: utf-8 -*-
"""Which body part can push each spring chain -- and which chains nothing can.

A VRM spring joint is deflected by exactly one thing: a collider attached to
its own chain. The body's geometry is invisible to the simulation. So a skirt
hanging around the thighs, on a character whose only colliders are a head
sphere and a torso capsule, is not "too reactive" -- it is unguarded, and the
legs pass straight through it because nothing represents them.

`vrm_colliders.fit` places a head sphere and a torso capsule and nothing else,
so every character built here has unguarded legs. That is invisible at rest,
invisible in a podium render, and invisible to the pose check -- the skirt
moves, it just moves through the leg.

What this measures, per spring chain:

  * the humanoid bone each joint sits nearest to (point-to-segment, against the
    rest skeleton read out of the file itself, so a rig whose bones are called
    `n47` is handled the same as a Mixamo one)
  * whether that part carries a collider, directly or above it in the chain
  * the smallest distance from any joint to any collider SURFACE

A chain is UNGUARDED when the part it hugs carries no collider. That is a
statement about the rig, not a prediction about an animation, and it is what
can be checked without running the game.

The control is built in: run with CLOTH_CONTROL=1 and the collider list is
emptied, so every chain must come back unguarded. A sweep in which nothing is
flagged, by an instrument that has never flagged anything, says nothing.

    python cloth_collide.py <file.vrm | dir> [...]
"""
import json
import os
import re
import struct
import sys

import numpy as np

# Chest springs sit ON the torso and are deliberately given no collider --
# handing them the torso capsule would push them out of the body they belong
# to. Same regex as vrm_colliders.CHEST. Without it the sweep reports Alcina
# Dimitrescu's `breast.L` and `breast.R` as unguarded, which is true and is not
# a defect; a check that flags a decision as a fault teaches the reader to skim
# its output.
CHEST = r"(breast|bust|pectoral|boob)"

# The humanoid chains, parent -> child, that make up a body. A segment is built
# only where BOTH ends are mapped, so a rig missing its toes or its chest
# contributes fewer segments rather than failing.
CHAINS = [
    ("torso", ["hips", "spine", "chest", "upperChest", "neck", "head"]),
    ("leftLeg", ["leftUpperLeg", "leftLowerLeg", "leftFoot", "leftToes"]),
    ("rightLeg", ["rightUpperLeg", "rightLowerLeg", "rightFoot", "rightToes"]),
    ("leftArm", ["leftShoulder", "leftUpperArm", "leftLowerArm", "leftHand"]),
    ("rightArm", ["rightShoulder", "rightUpperArm", "rightLowerArm",
                  "rightHand"]),
]


def load(path):
    d = open(path, "rb").read()
    off, g = 12, None
    while off < len(d):
        ln, ty = struct.unpack_from("<II", d, off)
        if ty == 0x4E4F534A:
            g = json.loads(d[off + 8:off + 8 + ln].decode("utf-8"))
        off += 8 + ln + ((4 - ln % 4) % 4)
    return g


def world_matrices(g):
    """Rest-pose world matrix per node, from the glTF node tree."""
    nodes = g["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i

    def local(n):
        if "matrix" in n:
            return np.array(n["matrix"], dtype=float).reshape(4, 4).T
        m = np.eye(4)
        if "scale" in n:
            m[:3, :3] = np.diag(n["scale"])
        if "rotation" in n:
            x, y, z, w = n["rotation"]
            r = np.array([
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),
                 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z),
                 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w),
                 1 - 2 * (x * x + y * y)],
            ])
            m[:3, :3] = r @ m[:3, :3]
        if "translation" in n:
            m[:3, 3] = n["translation"]
        return m

    cache = {}

    def wm(i):
        if i in cache:
            return cache[i]
        m = local(nodes[i])
        p = parent.get(i)
        if p is not None:
            m = wm(p) @ m
        cache[i] = m
        return m

    return [wm(i) for i in range(len(nodes))], parent


def seg_dist(p, a, b):
    ab = b - a
    L2 = float(ab @ ab)
    if L2 < 1e-12:
        return float(np.linalg.norm(p - a))
    t = max(0.0, min(1.0, float((p - a) @ ab) / L2))
    return float(np.linalg.norm(p - (a + ab * t)))


def report(path):
    g = load(path)
    name = os.path.basename(path).replace(".vrm", "")
    sb = g.get("extensions", {}).get("VRMC_springBone", {})
    springs = sb.get("springs", [])
    if not springs:
        print("%-28s no spring chains" % name[:28])
        return []

    W, parent = world_matrices(g)
    pos = [m[:3, 3] for m in W]
    hum = g["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
    hnode = {k: v["node"] for k, v in hum.items()}
    node_of_part = {}
    segments = []
    for part, keys in CHAINS:
        got = [k for k in keys if k in hnode]
        for k in got:
            node_of_part[hnode[k]] = part
        for a, b in zip(got, got[1:]):
            segments.append((part, a, pos[hnode[a]], pos[hnode[b]]))
    if not segments:
        print("%-28s no humanoid segments" % name[:28])
        return []

    colliders = sb.get("colliders", [])
    if os.environ.get("CLOTH_CONTROL"):
        colliders = []
        print("CONTROL: collider list emptied -- every chain must flag")

    # Which PART does each collider sit on? Walk up from its node until a
    # humanoid bone is reached, so a collider on a child bone still counts as
    # guarding the limb it belongs to.
    guarded = set()
    cshapes = []
    for c in colliders:
        n = c["node"]
        m = W[n]
        sh = c.get("shape", {})
        if "sphere" in sh:
            o = np.array(sh["sphere"].get("offset", [0, 0, 0]), dtype=float)
            ctr = (m @ np.append(o, 1.0))[:3]
            cshapes.append(("S", ctr, ctr, float(sh["sphere"]["radius"])))
        elif "capsule" in sh:
            cap = sh["capsule"]
            o = np.array(cap.get("offset", [0, 0, 0]), dtype=float)
            t = np.array(cap.get("tail", [0, 0, 0]), dtype=float)
            a = (m @ np.append(o, 1.0))[:3]
            b = (m @ np.append(t, 1.0))[:3]
            cshapes.append(("C", a, b, float(cap["radius"])))
        k = n
        seen = set()
        while k is not None and k not in seen:
            seen.add(k)
            if k in node_of_part:
                guarded.add(node_of_part[k])
                break
            k = parent.get(k)

    rows = []
    chest = 0
    for sp in springs:
        if re.search(CHEST, sp.get("name", "") or "", re.I):
            chest += 1
            continue
        joints = [j["node"] for j in sp.get("joints", [])]
        if not joints:
            continue
        tally = {}
        dcol = 1e9
        for jn in joints:
            p = pos[jn]
            best = min(segments, key=lambda s: seg_dist(p, s[2], s[3]))
            tally[best[0]] = tally.get(best[0], 0) + 1
            for kind, a, b, r in cshapes:
                d = (float(np.linalg.norm(p - a)) if kind == "S"
                     else seg_dist(p, a, b)) - r
                dcol = min(dcol, d)
        part = max(tally.items(), key=lambda kv: kv[1])[0]
        rows.append((sp.get("name", "?"), part, part in guarded,
                     len(joints), dcol))

    bad = [r for r in rows if not r[2]]
    print("%-28s %2d chains, %d collider(s) on %s; %d UNGUARDED%s"
          % (name[:28], len(rows), len(cshapes),
             "+".join(sorted(guarded)) or "nothing", len(bad),
             "  (%d chest chain(s) skipped on purpose)" % chest if chest
             else ""))
    for nm, part, ok, nj, dc in rows:
        if ok and not os.environ.get("CLOTH_VERBOSE"):
            continue
        print("    %-30s %-9s %2d joints  nearest collider surface %s"
              % (nm[:30], part, nj,
                 "%.3f m" % dc if dc < 1e8 else "none at all"))
    return bad


def main():
    files = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".vrm")]
        else:
            files.append(a)
    tot = hit = 0
    for f in files:
        try:
            b = report(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-28s FAILED: %s" % (os.path.basename(f)[:28], e))
            continue
        tot += 1
        if b:
            hit += 1
    print("")
    print("%d file(s) read, %d with at least one unguarded chain" % (tot, hit))


main()
