# -*- coding: utf-8 -*-
"""Whose geometry is the "body surface" beside a chain's joints? Name it, do not assume it.

    python chain_surface_owners.py <file.yargchar> <chain-name> [<chain-name> ...]

WHY THIS EXISTS. `tie_collider_fit.py` derives a capsule radius from two bounds, and the lower
one is "where the body surface sits beside each joint". It finds that surface by taking every
vertex within 60 mm of a joint, **excluding the vertices weighted to the measured chain's own
bones** -- because a tie that clears itself is not a measurement.

That exclusion is exactly right for a necktie, which is the only garment this project has one
of. It is WRONG FOR A SKIRT, and silently:

  * Miku's tie is ONE chain. Everything else near it is her body, so "not my bones" and "her
    skin" are the same set.
  * Jessica's dress is FOUR chains. Measuring one of them leaves the other three in the
    "body" set, so a panel hanging beside its neighbour reads as a panel resting on SKIN, and
    the lower bound comes back describing cloth.

Nothing in the output says which happened. The number has the same shape either way, which is
the whole problem: a bound derived from the wrong surface still prints, still looks tight, and
still crosses or clears with no indication that the thing it was measured against was another
piece of the same dress.

So this tool answers only the question the other one assumes: **for each joint, which BONES own
the nearby geometry, and how much of it.** It derives nothing and recommends nothing. Read it
before believing a surface bound on any character with more than one cloth chain.

A second trap it also exposes, because the same listing shows it: the surface vertices are
selected by distance to the JOINT, and then reported as a distance to the CAPSULE AXIS. Those
are different frames. A vertex 40 mm from a hem joint can be 190 mm from the thigh axis that
joint's chain is pinned to -- so a "minimum radius" taken from it asks for a thigh capsule wider
than her pelvis. The `axis d` column here is printed beside `joint d` on purpose, so a bound
that was derived across her body instead of along it is visible rather than inferred.
"""
import math
import os
import sys
from collections import Counter

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

NEAR = 0.060          # the same 60 mm window tie_collider_fit.py uses, on purpose


def seg_dist(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    L = sum(x * x for x in ab)
    t = 0.0 if L <= 0 else max(0.0, min(1.0, sum(ap[i] * ab[i] for i in range(3)) / L))
    c = [a[i] + ab[i] * t for i in range(3)]
    return math.sqrt(sum((p[i] - c[i]) ** 2 for i in range(3)))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path, want = sys.argv[1], sys.argv[2:]

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    by_name = {s[0]: s for s in springs}
    missing = [w for w in want if w not in by_name]
    if missing:
        print("no such chain(s): %s; this file has %s"
              % (", ".join(missing), sorted(by_name)))
        return 2

    # Every joint of every REQUESTED chain, plus the set of bones they occupy. The union is
    # what a multi-chain garment's exclusion set should have been.
    jrows, garment_bones = {}, set()
    for w in want:
        rows = []
        for jp in by_name[w][1]:
            rec = joints.get(jp)
            if rec is None:
                print("joint %s of %s is not in the joint table -- unmeasured" % (jp, w))
                return 2
            tp = go_tf.get(rec[0])
            if tp is None:
                print("joint %s of %s has no transform -- unmeasured" % (jp, w))
                return 2
            wp, _wq, ws = world(tp)
            nm = tf.get(tp, {}).get("name") or "?"
            rows.append((nm, wp, rec[4] * ws[0]))
            garment_bones.add(nm)
        jrows[w] = rows

    # The capsule each chain is deepest inside -- the one tie_collider_fit.py would pick as
    # standing in for the body, and therefore the axis its bounds are measured against.
    shapes = {}
    for cp, t in colliders.items():
        tp = go_tf.get((t.get("m_GameObject") or {}).get("m_PathID"))
        if tp is None:
            continue
        wp, wq, ws = world(tp)

        def to_world(v, wq=wq, ws=ws, wp=wp):
            sc = (v.get("x", 0.0) * ws[0], v.get("y", 0.0) * ws[1], v.get("z", 0.0) * ws[2])
            r = cci.qrot(wq, sc)
            return (wp[0] + r[0], wp[1] + r[1], wp[2] + r[2])

        a = to_world(t.get("Offset") or {})
        b = to_world(t.get("Tail") or {}) if t.get("ColliderType", 0) == 1 else a
        shapes[cp] = (tf.get(tp, {}).get("name") or "?",
                      float(t.get("Radius", 0.0)) * ws[0], a, b)

    axis_of = {}
    for w in want:
        best, bcp = None, None
        for cp, (cname, cr, a, b) in shapes.items():
            worst = min(seg_dist(wp, a, b) - cr - jr for _n, wp, jr in jrows[w])
            if best is None or worst < best:
                best, bcp = worst, cp
        axis_of[w] = shapes[bcp] if bcp is not None else None

    # ---- decode every skinned vertex once, keeping its dominant bone's NAME
    env = UnityPy.load(path)
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())
    verts = []
    for r in smrs:
        mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        got = ps.decode(mt)
        bones = [x["m_PathID"] for x in (r.get("m_Bones") or [])]
        bind = [ps.mat4(x) for x in (mt.get("m_BindPose") or [])]
        if got is None or not bones or len(bind) != len(bones):
            continue
        V, W, I = got
        skin = [ps.mul(ps.trs(*world(x)), bind[i]) for i, x in enumerate(bones)]
        for vi in range(len(V)):
            best, bw = None, -1.0
            for k in range(len(W[vi])):
                wgt, bi = W[vi][k], I[vi][k]
                if wgt > bw and wgt > 0 and bi < len(skin):
                    bw, best = wgt, bi
            if best is None:
                continue
            verts.append((tf.get(bones[best], {}).get("name") or "?",
                          ps.xform(skin[best], V[vi])))
    if not verts:
        print("NO GEOMETRY decoded -- nothing is named here, which is not the same as 'clean'.")
        return 1
    print("%d skinned vertices decoded; %d joint(s) across %d chain(s); garment bones: %s"
          % (len(verts), sum(len(v) for v in jrows.values()), len(want),
             ", ".join(sorted(garment_bones))))
    print()

    for w in want:
        cname, cr, a, b = axis_of[w] if axis_of[w] else ("(none)", 0.0, (0, 0, 0), (0, 0, 0))
        print("=" * 78)
        print("chain %s   bounds would be measured against the capsule on %r (r %.1f mm)"
              % (w, cname, cr * 1000))
        print("=" * 78)
        for jn, jp, jr in jrows[w]:
            near = [(bn, p) for bn, p in verts
                    if math.sqrt(sum((p[i] - jp[i]) ** 2 for i in range(3))) <= NEAR]
            own = [x for x in near if x[0] == jn]
            sib = [x for x in near if x[0] in garment_bones and x[0] != jn]
            skin = [x for x in near if x[0] not in garment_bones]
            print("  %-22s %4d vert(s) within %d mm: %d own, %d SIBLING PANEL, %d other"
                  % (jn[:22], len(near), NEAR * 1000, len(own), len(sib), len(skin)))
            if not near:
                print("      nothing within the window -- UNMEASURED, not clear")
                continue
            # What tie_collider_fit.py would have used: everything but `own`.
            used = sib + skin
            if used:
                ad = sorted(seg_dist(p, a, b) for _bn, p in used)
                jd = sorted(math.sqrt(sum((p[i] - jp[i]) ** 2 for i in range(3)))
                            for _bn, p in used)
                print("      as used by the fit tool: axis d min %6.1f med %6.1f max %6.1f mm"
                      % (ad[0] * 1000, ad[len(ad) // 2] * 1000, ad[-1] * 1000))
                print("                               joint d min %6.1f med %6.1f max %6.1f mm"
                      % (jd[0] * 1000, jd[len(jd) // 2] * 1000, jd[-1] * 1000))
            if skin:
                ad = sorted(seg_dist(p, a, b) for _bn, p in skin)
                print("      SKIN ONLY             : axis d min %6.1f med %6.1f max %6.1f mm"
                      % (ad[0] * 1000, ad[len(ad) // 2] * 1000, ad[-1] * 1000))
            else:
                print("      SKIN ONLY             : NONE -- every nearby vertex is garment")
            top = Counter(bn for bn, _p in near).most_common(6)
            print("      owners: %s"
                  % ", ".join("%s x%d%s" % (bn, n, " [GARMENT]" if bn in garment_bones else "")
                              for bn, n in top))
        print()

    print("Read the SIBLING PANEL column first. Where it is non-zero, the fit tool's lower")
    print("bound was derived partly from another piece of the same garment, and the two")
    print("`axis d` rows show how far apart that makes the answer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
