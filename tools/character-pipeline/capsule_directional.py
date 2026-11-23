# -*- coding: utf-8 -*-
"""Is my 51-56 mm "capsule stands proud of the skin" an OVER-READ, or an artefact of taking the
NEAREST body vertex to a capsule centre that sits INSIDE the body?

THE DOUBT. capsule_overclaim.py reports radius minus distance-to-the-nearest-five-body-vertices.
For a capsule whose centre is INSIDE the body -- which a clavicle's is -- the nearest surface
point is not the surface the capsule is meant to match: such a capsule is authored to FILL the
body there, so radius > nearest-vertex-distance is expected and is not an over-read at all. The
tell is in my own table: C_head reads radius 83.7 mm with "skin at 6.4 mm", a 77 mm "over-read"
on a capsule whose whole job is to fill a head.

THE DIRECTIONAL VERSION. From the capsule centre, sample directions. Along each, find the body
surface within a narrow cone and compare it against the capsule's extent in THAT direction. The
capsule stands proud only in the directions where its surface lies outside the body's.

TWO CONTROLS:
  * C_head, which is authored to fit a head, must come back mostly NOT proud. If the head reads
    proud in every direction the method is wrong, not the capsules.
  * the per-direction body-vertex count is printed, and a direction with no body vertex in its
    cone is reported as UNSEEN rather than counted as proud -- otherwise every direction pointing
    out of the body reads as a maximal over-read.
"""
import math
import sys

sys.path.insert(0, r"C:\dev\YARG - Open Source Contributions\yarg\tools\character-pipeline")

import cloth_collide_installed as cci                                     # noqa: E402
import patch_springs as ps                                               # noqa: E402
import UnityPy                                                           # noqa: E402

P = (r"C:\Users\ENG2\AppData\LocalLow\FatalException\YARG-FE\release\custom"
     r"\characters\Batman.yargchar")
WANT = ("L_clav", "R_clav", "C_head", "C_spine_b")
COS_CONE = math.cos(math.radians(12.0))

human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(P)
env = UnityPy.load(P)
nm = lambda t: (tf.get(t, {}).get("name") or "?")

tt_mesh, smrs = {}, []
for o in env.objects:
    if o.type.name == "Mesh":
        tt_mesh[o.path_id] = o.read_typetree()
    elif o.type.name == "SkinnedMeshRenderer":
        smrs.append(o.read_typetree())

# body = humanoid-mapped bones and their descendants, minus anything cape-named (same rule as
# capsule_overclaim.py, so this tests the DIRECTION change and nothing else)
hbones = {b for b in (human or {}).values() if b}
kids = {}
for pid, rec in tf.items():
    kids.setdefault(rec.get("f") or 0, []).append(pid)
body_bones, stack, seen = set(), [p for p in tf if nm(p) in hbones], set()
while stack:
    q = stack.pop()
    if q in seen:
        continue
    seen.add(q)
    if "cape" in nm(q).lower():
        continue
    body_bones.add(q)
    stack.extend(kids.get(q, []))

pts = []
for r in smrs:
    mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
    if mt is None:
        continue
    got = ps.decode(mt)
    bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
    bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
    if got is None or not bones or len(bind) != len(bones):
        continue
    V, W, I = got
    skin = [ps.mul(ps.trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
    for vi in range(len(V)):
        best, bw = None, -1.0
        for k in range(len(W[vi])):
            w, bi = W[vi][k], I[vi][k]
            if w > bw and w > 0 and bi < len(bones):
                bw, best = w, bi
        if best is not None and bones[best] in body_bones:
            pts.append(ps.xform(skin[best], V[vi]))
print("body vertices: %d" % len(pts))
if len(pts) < 1000:
    raise SystemExit("REFUSED: %d body vertices is too few for a surface" % len(pts))

# ~200 roughly uniform directions
dirs = []
n = 200
for i in range(n):
    y = 1.0 - 2.0 * (i + 0.5) / n
    r = math.sqrt(max(0.0, 1.0 - y * y))
    th = math.pi * (1.0 + 5.0 ** 0.5) * i
    dirs.append((math.cos(th) * r, y, math.sin(th) * r))

print()
print("%-22s %8s  %5s %5s %5s   %s" % ("collider on bone", "radius", "proud", "in", "unseen",
                                       "median proud / max"))
for cid, t in colliders.items():
    gid = (t.get("m_GameObject") or {}).get("m_PathID")
    tid = go_tf.get(gid)
    if tid is None or not any(w in nm(tid) for w in WANT):
        continue
    wp, wq, ws = world(tid)
    off = t.get("Offset") or {}
    o = cci.qrot(wq, (off.get("x", 0.0) * ws[0], off.get("y", 0.0) * ws[1],
                      off.get("z", 0.0) * ws[2]))
    c = (wp[0] + o[0], wp[1] + o[1], wp[2] + o[2])
    radius = float(t.get("Radius") or 0.0) * max(ws)
    if radius <= 0:
        continue
    near = [p for p in pts if abs(p[0] - c[0]) < 0.45 and abs(p[1] - c[1]) < 0.45
            and abs(p[2] - c[2]) < 0.45]
    proud, inside, unseen, overs = 0, 0, 0, []
    for d in dirs:
        bestd = None
        for p in near:
            vx, vy, vz = p[0] - c[0], p[1] - c[1], p[2] - c[2]
            L = math.sqrt(vx * vx + vy * vy + vz * vz)
            if L < 1e-6:
                continue
            if (vx * d[0] + vy * d[1] + vz * d[2]) / L >= COS_CONE:
                if bestd is None or L > bestd:
                    bestd = L            # the FARTHEST surface point in this cone is the outer wall
        if bestd is None:
            unseen += 1
        elif radius > bestd:
            proud += 1
            overs.append((radius - bestd) * 1000.0)
        else:
            inside += 1
    overs.sort()
    med = overs[len(overs) // 2] if overs else 0.0
    mx = overs[-1] if overs else 0.0
    print("%-22s %7.1fmm  %5d %5d %5d   %7.1fmm / %7.1fmm"
          % (nm(tid)[:22], radius * 1000, proud, inside, unseen, med, mx))

print()
print("READ IT LIKE THIS. C_head is authored to fit a head, so if it reads proud in nearly every")
print("direction the METHOD is wrong rather than the capsules. A clavicle that is proud in only a")
print("minority of directions is not 'standing 51-56 mm off the skin' -- it is a capsule filling a")
print("shoulder, and the nearest-vertex figure was measuring its own centre's depth.")
