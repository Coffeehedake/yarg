# -*- coding: utf-8 -*-
"""How much fatter is each collision capsule than the body it stands for?

THE HYPOTHESIS UNDER THE NEW INSTRUMENT. The capsule probe reports `fml_un_L_clav` as 21.7% of
all cape-into-body contact. If the clavicle capsule is much wider than the actual shoulder, then
a yoke resting CORRECTLY on the collarbone sits inside that capsule and is counted as
penetration -- and the fix is to test against the body surface instead. If the capsules hug the
surface, that explanation is wrong and the new design loses its main justification.

So, per collider, in the REST pose: take the body vertices near its sphere, and compare the
capsule RADIUS against how far those vertices actually are from the capsule centre.

    overclaim = radius - (distance from centre to the body surface around it)

Positive means the capsule stands proud of the skin by that many millimetres, and anything
within that shell reads as penetration without touching the body at all.

TWO CONTROLS, because a number like this is easy to produce and hard to trust:

  * BODY vertices are selected by the Avatar's humanoid map, not by name -- the same trap that
    would otherwise collect `fml_un_L_capeClav_a` as a clavicle.
  * the per-collider body-vertex COUNT is printed. A capsule with no body vertices near it
    produces a confident number from nothing, and that is reported as SKIPPED rather than as 0.
"""
import collections
import math
import sys

sys.path.insert(0, r"C:\dev\YARG - Open Source Contributions\yarg\tools\character-pipeline")

import chain_weight_installed as cwi                                     # noqa: E402
import cloth_collide_installed as cci                                    # noqa: E402
import patch_springs as ps                                               # noqa: E402
import UnityPy                                                           # noqa: E402

P = (r"C:\Users\ENG2\AppData\LocalLow\FatalException\YARG-FE\release\custom"
     r"\characters\Batman.yargchar")

human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(P)
env = UnityPy.load(P)
nm = lambda t: (tf.get(t, {}).get("name") or "?")
gname = cwi.gameobject_names(env)

# ---- every vertex in the rest pose, with its dominant bone -------------------------------
tt_mesh, smrs = {}, []
for o in env.objects:
    if o.type.name == "Mesh":
        tt_mesh[o.path_id] = o.read_typetree()
    elif o.type.name == "SkinnedMeshRenderer":
        smrs.append(o.read_typetree())

pts = []          # (world position, dominant bone transform id)
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
        if best is None:
            continue
        pts.append((ps.xform(skin[best], V[vi]), bones[best]))

print("rest-pose vertices with a dominant bone: %d" % len(pts))
if not pts:
    raise SystemExit("REFUSED: no vertices read, so nothing below is a measurement")

# ---- which bones are BODY, from the humanoid map and its descendants ----------------------
hbones = {b for b in (human or {}).values() if b}
kids = collections.defaultdict(list)
for pid, rec in tf.items():
    kids[rec.get("f") or 0].append(pid)
body_bones = set()
stack = [pid for pid in tf if nm(pid) in hbones]
seen = set()
while stack:
    q = stack.pop()
    if q in seen:
        continue
    seen.add(q)
    n = nm(q)
    if "cape" in n.lower():
        continue                     # a cape bone under a clavicle is still cloth
    body_bones.add(q)
    stack.extend(kids.get(q, []))
print("humanoid-mapped bones %d, body bones incl. descendants %d" % (len(hbones), len(body_bones)))

body_pts = [p for p, b in pts if b in body_bones]
cloth_pts = [p for p, b in pts if b not in body_bones]
print("body vertices %d, non-body (cloth) vertices %d" % (len(body_pts), len(cloth_pts)))
if not body_pts or not cloth_pts:
    raise SystemExit("REFUSED: one side of the body/cloth split is empty")

# ---- per collider: radius vs where the skin actually is ----------------------------------
rows = []
for cid, t in colliders.items():
    gid = (t.get("m_GameObject") or {}).get("m_PathID")
    tid = go_tf.get(gid)
    if tid is None:
        continue
    wp, wq, ws = world(tid)
    off = t.get("Offset") or {}
    o = (off.get("x", 0.0), off.get("y", 0.0), off.get("z", 0.0))
    o = cci.qrot(wq, (o[0] * ws[0], o[1] * ws[1], o[2] * ws[2]))
    centre = (wp[0] + o[0], wp[1] + o[1], wp[2] + o[2])
    radius = float(t.get("Radius") or 0.0) * max(ws)

    near = [math.dist(centre, b) for b in body_pts if abs(b[1] - centre[1]) < 0.25]
    near = sorted(d for d in near if d < radius * 4.0 + 0.10)
    if len(near) < 20:
        rows.append((nm(tid), radius, None, None, len(near)))
        continue
    # the skin around this capsule: the closest decile is the surface it sits under
    k = min(5, len(near))          # the NEAREST few, not a decile: a decile over a dense mesh
                                   # region reaches further than one over a sparse one, which is
                                   # how two sides of one collarbone read 69 mm apart
    surface = sum(near[:k]) / k
    rows.append((nm(tid), radius, surface, (radius - surface) * 1000.0, len(near)))

rows.sort(key=lambda r: -(r[3] if r[3] is not None else -1e9))
print()
print("%-30s %8s %9s %11s %7s" % ("collider on bone", "radius", "skin at", "OVERCLAIM", "n"))
done = set()
for n, rad, surf, over, cnt in rows:
    if surf is None:
        continue
    if n in done:
        continue
    done.add(n)
    print("%-30s %7.1fmm %8.1fmm %10.1fmm %7d" % (n[:30], rad * 1000, surf * 1000, over, cnt))
skipped = [r for r in rows if r[2] is None]
if skipped:
    print("SKIPPED (fewer than 20 body vertices nearby, so no honest number): %d collider(s)"
          % len(skipped))

print()
clav = [r for r in rows if "clav" in r[0].lower() and r[3] is not None]
if clav:
    print("THE ONE THAT MATTERS -- the clavicle capsules the probe blames for 21.7%% of contact:")
    for n, rad, surf, over, cnt in clav:
        print("   %-26s radius %.1f mm, skin at %.1f mm -> stands %.1f mm proud"
              % (n, rad * 1000, surf * 1000, over))
    print()
    print("Any cloth within that shell is counted as penetration while resting ON the skin.")
