# -*- coding: utf-8 -*-
"""Does the garment clip AT REST? Because if it does, no collider can ever fix it.

    python garment_rest_penetration.py <file.yargchar> <chain-prefix> \
           [--garment PREFIX] [--garment-match SUBSTRING] [--near MM]

WHY THIS EXISTS, and it is a correction to a day's work. Jay reported Miku's tie and Batman's
cape as clipping, in the character SELECT screen. I answered both with spring-bone colliders --
`patch_chain_collider.py` for her, `place_collider.py` for him -- derived a radius for each, and
verified both in the bundle. He then looked at them in the game: **"none of them are fixed."**

He is right, and the reason is in the construction of the fix. A collider's radius here is
chosen to satisfy two bounds, and **the upper one is "no joint starts inside the capsule at
rest"**, because a joint that starts inside is shoved out on frame one -- the very fault that
made the shared capsule unusable for her tie in the first place. Her chosen radius leaves every
joint 1.2 mm or more clear; Batman's leaves every joint 3.5 mm or more clear.

**So both fixes are, by construction, no-ops in the rest pose.** They change what the cloth may
do while it MOVES. They cannot change where it sits while it stands still, and a static select
screen is exactly where it stands still. I derived a number whose defining property was that it
would not move anything, and then expected to see something move.

So this tool asks the question I never asked: **is the garment inside the body AT REST, before
any simulation?** If it is, the clipping is authored into the geometry, every collider in the
world is irrelevant to it, and the fix is somewhere else entirely -- the mesh, the weights, or
the bones.

HOW IT MEASURES, on the garment's VERTICES and not its joints. That distinction is the whole
point: the fit tools measured JOINTS, which is right for deciding a radius, and a joint is a
point on the chain's spine while the cloth is a surface spread around it. A tie whose joints
clear the chest by 1.2 mm can still have half its width buried in her.

For each garment vertex it takes the skin within `--near` of it, excluding the whole garment,
and compares the two against the local body axis fitted by `fit_body_capsule.body_slices`:

    inside  = median(axis distance of nearby skin) - (axis distance of the garment vertex)

Positive means the vertex is nearer the axis than the surrounding skin is -- i.e. **inside the
body**. The median is used rather than the minimum for the reason recorded under the band gate:
a single stray vertex should not decide an answer.

Nothing is written.
"""
import math
import os
import sys

import cloth_collide_installed as cci
import fit_body_capsule as F
import patch_springs as ps
import UnityPy


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path, prefix = sys.argv[1], sys.argv[2]
    near_m = 0.060
    if "--near" in sys.argv:
        near_m = float(sys.argv[sys.argv.index("--near") + 1]) / 1000.0

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    chains = [s for s in springs if s[0].startswith(prefix)]
    if not chains:
        print("no chain starting %r; this file has %s"
              % (prefix, sorted(s[0] for s in springs)))
        return 2
    # THE GARMENT IS NOT ONLY THE CHAIN'S JOINTS, and getting that wrong inflated this
    # tool's first Batman reading from a real 4% to a reported 63.5%. His cape is eleven
    # chains plus a set of `*_capeEdge_*` bones that are in NO chain at all, so a run with
    # prefix `fml_un_C_cape` left his left and right panels AND every cape edge in the
    # "skin" set -- and counted cape resting against cape as cape buried in body.
    #
    # Pass --garment with a prefix wide enough to cover the whole garment, or give
    # --garment-match a substring that catches the bones no chain owns. Checked for on
    # Jessica, cleared there, and then not re-checked here: her four panels never come
    # within 60 mm of each other, so the trap did not fire and I stopped looking for it.
    gp = sys.argv[sys.argv.index("--garment") + 1] if "--garment" in sys.argv else prefix
    gm = sys.argv[sys.argv.index("--garment-match") + 1] if "--garment-match" in sys.argv         else None
    garment = set()
    for nm, jps, _g in springs:
        if not nm.startswith(gp):
            continue
        for jp in jps:
            rec = joints.get(jp)
            tp = go_tf.get(rec[0]) if rec else None
            if tp is not None:
                garment.add(tf.get(tp, {}).get("name") or "?")
    if gm:
        for _pid, rec in tf.items():
            nm = rec.get("name") or ""
            if gm.lower() in nm.lower():
                garment.add(nm)

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
    if not cloth:
        print("NO geometry is weighted to this garment's bones. That is a finding about the")
        print("rig, not a clean result: the chain moves nothing.")
        return 1
    if not skin:
        print("NO skin decoded -- nothing to be inside of. Unmeasured, not clean.")
        return 1

    ys = [p[1] for _b, p in cloth]
    y0, y1 = min(ys), max(ys)
    slices = F.body_slices(skin, y0, y1)
    if not slices:
        print("could not fit a body axis over the garment's height -- unmeasured.")
        return 1

    def axis_d(p):
        s = min(slices, key=lambda t: abs(t[0] - p[1]))
        return math.sqrt((p[0] - s[1]) ** 2 + (p[2] - s[2]) ** 2)

    print("%d garment vertices on %d bone(s), %d skin vertices, body axis over %.3f-%.3f m"
          % (len(cloth), len(garment), len(skin), y0, y1))
    print()
    rows, buried, unmeasured = [], 0, 0
    step = max(1, len(cloth) // 4000)        # the extremes matter, not every vertex
    for bn, p in cloth[::step]:
        near = [q for _b, q in skin
                if sum((q[i] - p[i]) ** 2 for i in range(3)) < near_m * near_m]
        if len(near) < 5:
            unmeasured += 1
            continue
        ds = sorted(axis_d(q) for q in near)
        depth = ds[len(ds) // 2] - axis_d(p)
        rows.append((depth, bn))
        if depth > 0:
            buried += 1
    if not rows:
        print("no garment vertex has skin within %.0f mm -- it hangs clear of the body"
              % (near_m * 1000))
        print("everywhere, so there is nothing for it to be inside of at rest.")
        return 0
    rows.sort(reverse=True)
    print("%d of %d sampled garment vertices sit INSIDE the body at rest (%.1f%%)"
          % (buried, len(rows), 100.0 * buried / len(rows)))
    print("  deepest %.1f mm, median of the buried %.1f mm"
          % (rows[0][0] * 1000,
             (rows[buried // 2][0] * 1000) if buried else 0.0))
    if unmeasured:
        print("  %d sampled vertices had no skin within %.0f mm and are not counted"
              % (unmeasured, near_m * 1000))
    print()
    for d, bn in rows[:8]:
        print("    %-28s %+7.1f mm" % (bn[:28], d * 1000))
    print()
    if buried:
        print("THE CLIPPING IS AUTHORED AND STATIC. A spring-bone collider is chosen so that")
        print("no joint starts inside it -- that is its upper bound -- so it changes nothing")
        print("in the rest pose by construction. It governs what the cloth may do while it")
        print("MOVES. Geometry that is buried while standing still needs the mesh, the")
        print("weights or the bones changed, and no radius will ever show.")
        return 1
    print("No sampled vertex is inside the body at rest, so what was reported is a fault of")
    print("MOTION and a collider is the right class of fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
