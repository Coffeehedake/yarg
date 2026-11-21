# -*- coding: utf-8 -*-
"""Which cape panel is IN FRONT of him, and is it inside him at rest?

Jay: "the cape cuts directly through his torso." A capsule cannot answer that. Its upper bound
is "no joint starts inside", so by construction it changes nothing in the rest pose -- and a
panel that has come through to his FRONT is either authored there or put there by something
other than collision.

So, per chain, on the garment's VERTICES and not its joints:

  * how many sit inside the body at rest, measured against the author's own torso capsule axis
    rather than a fitted one;
  * their height, because cape buried at the collar is authored attachment and invisible, while
    cape buried at the waist is the reported fault;
  * which SIDE of him they are on. The axis has a front and a back, and a panel whose vertices
    are at negative depth behind him is draping; one at positive depth in front of him has
    crossed through.

Depth is taken along the torso's own forward direction, derived from the body itself -- the
mean offset of the belt skin from the axis -- rather than from a world axis, because nothing
guarantees the character faces +z.

Nothing written.
"""
import math
import statistics as st
import sys

import capsule_contains as cc
import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

path = sys.argv[1]

human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
garment = cc.cloth_bones(tf, go_tf, springs, joints, "cape")
shapes = cc.collider_shapes(tf, go_tf, colliders, world)
host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "fml_un_C_pelvis_att"
torso = [v for v in shapes.values() if v[0] == host]
if not torso:
    print("no collider on %r to measure against -- unmeasured" % host)
    sys.exit(2)
# A bone can carry more than one, and after 2026-11-21 this one does: the author's full-torso
# capsule and the shortened CapeTorso one added for the cape. The REFERENCE axis is the longest,
# because that is the one drawn to describe the whole part; picking by radius would pick mine.
torso.sort(key=lambda v: -sum((v[3][i] - v[2][i]) ** 2 for i in range(3)))
_bn, r0, A, B, _ct = torso[0]
if len(torso) > 1:
    print("%d colliders on %s; using the longest as the body axis (r=%.1f mm, span %.3f m)"
          % (len(torso), host, r0 * 1000,
             math.sqrt(sum((B[i] - A[i]) ** 2 for i in range(3)))))

env = UnityPy.load(path)
tt, smrs = {}, []
for o in env.objects:
    if o.type.name == "Mesh":
        tt[o.path_id] = o.read_typetree()
    elif o.type.name == "SkinnedMeshRenderer":
        smrs.append(o.read_typetree())
cloth, skin = [], []
for r in smrs:
    mt = tt.get((r.get("m_Mesh") or {}).get("m_PathID"))
    if mt is None:
        continue
    got = ps.decode(mt)
    bones = [x["m_PathID"] for x in (r.get("m_Bones") or [])]
    bind = [ps.mat4(x) for x in (mt.get("m_BindPose") or [])]
    if got is None or not bones or len(bind) != len(bones):
        continue
    V, W, I = got
    mats = [ps.mul(ps.trs(*world(x)), bind[i]) for i, x in enumerate(bones)]
    for vi in range(len(V)):
        best, bw = None, -1.0
        for k in range(len(W[vi])):
            wgt, bi = W[vi][k], I[vi][k]
            if wgt > bw and wgt > 0 and bi < len(mats):
                bw, best = wgt, bi
        if best is None:
            continue
        bn = tf.get(bones[best], {}).get("name") or "?"
        p = ps.xform(mats[best], V[vi])
        (cloth if bn in garment else skin).append((bn, p))


def axis_at(y):
    lo, hi = (A, B) if A[1] < B[1] else (B, A)
    t = 0.0 if hi[1] == lo[1] else max(0.0, min(1.0, (y - lo[1]) / (hi[1] - lo[1])))
    return tuple(lo[i] + (hi[i] - lo[i]) * t for i in range(3))


# the body's OWN forward direction: the belt buckle is on the front, so the mean offset of the
# belt_f skin from the axis points forward. Nothing here assumes +z.
fwd = [0.0, 0.0, 0.0]
n = 0
for bn, q in skin:
    if "belt_f" not in bn:
        continue
    c = axis_at(q[1])
    fwd[0] += q[0] - c[0]
    fwd[2] += q[2] - c[2]
    n += 1
if n < 20:
    print("could not derive a forward direction from belt_f skin (%d vertices) -- unmeasured" % n)
    sys.exit(2)
L = math.sqrt(fwd[0] ** 2 + fwd[2] ** 2)
fwd = (fwd[0] / L, fwd[2] / L)
print("forward derived from %d belt_f vertices: (%.3f, %.3f) in xz" % (n, fwd[0], fwd[1]))


def radial(p):
    c = axis_at(p[1])
    return math.sqrt((p[0] - c[0]) ** 2 + (p[2] - c[2]) ** 2)


def depth(p):
    c = axis_at(p[1])
    return (p[0] - c[0]) * fwd[0] + (p[2] - c[2]) * fwd[1]


# the body surface radius at each height, from torso skin only (near the authored capsule)
bands = {}
for bn, q in skin:
    if radial(q) > 0.30:
        continue
    bands.setdefault(round(q[1], 2), []).append(radial(q))


def surface(y):
    k = round(y, 2)
    for d in (0.0, 0.01, -0.01, 0.02, -0.02, 0.03, -0.03):
        b = bands.get(round(k + d, 2))
        if b and len(b) >= 10:
            return st.median(b)
    return None


bychain = {}
for nm, jps, _g in springs:
    if "cape" not in nm.lower():
        continue
    for jp in jps:
        rec = joints.get(jp)
        tp = go_tf.get(rec[0]) if rec else None
        if tp is not None:
            bychain[tf.get(tp, {}).get("name") or "?"] = nm

print("%d cape vertices, %d skin vertices, torso capsule r=%.1f mm y %.3f-%.3f"
      % (len(cloth), len(skin), r0 * 1000, min(A[1], B[1]), max(A[1], B[1])))
print()
print("%-22s %6s %7s %8s %9s %9s %9s"
      % ("chain (or no chain)", "n", "inside", "worst", "y of worst", "front n", "back n"))
print("-" * 92)
rows = {}
for bn, p in cloth:
    nm = bychain.get(bn, "(no chain)")
    s = surface(p[1])
    if s is None:
        continue
    d = s - radial(p)
    r = rows.setdefault(nm, [0, 0, 0.0, 0.0, 0, 0])
    r[0] += 1
    if d > 0:
        r[1] += 1
        if d > r[2]:
            r[2], r[3] = d, p[1]
        if depth(p) > 0:
            r[4] += 1
        else:
            r[5] += 1
for nm in sorted(rows, key=lambda k: -rows[k][1]):
    n0, ins, worst, wy, fr, bk = rows[nm]
    print("%-22s %6d %6d%% %7.1f mm %9.3f %9d %9d"
          % (nm[:22], n0, int(100.0 * ins / n0) if n0 else 0, worst * 1000, wy, fr, bk))
