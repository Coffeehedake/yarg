# -*- coding: utf-8 -*-
"""Per-CAPSULE collider fit for a multi-chain garment: both bounds on the same axis.

    python garment_collider_fit.py <file.yargchar> <chain-prefix> [--near MM]

e.g.  python garment_collider_fit.py "Jessica Rabbit.yargchar" ClothSpring_1_

WHY THIS EXISTS, and it is a correction to `tie_collider_fit.py` rather than an extension.

That tool derives a capsule radius from two bounds and compares them, which is right. It picks
the axis to measure both against by asking **which capsule is the chain deepest inside**, and
that is right for a necktie: Miku's tie hangs on her spine, her spine capsule is the one it is
deepest inside, and the skin beside the knot is spine skin. One axis, one body part, both bounds
in the same frame. Verified -- run `chain_surface_owners.py` on her `Tie` and every nearby skin
vertex is owned by `Bip01 Spine` or `Bip01 Spine1`, the bone the chosen capsule sits on.

**IT IS WRONG FOR A SKIRT, and it fails silently in the direction that looks like bad news.**
Measured on Jessica Rabbit, whose dress is four `ClothSpring_1_*` chains:

    chain              axis it chose      owns the nearby skin?     its verdict
    ClothSpring_1_0_0  thigh.L   r 93.9   NO -- spine x82           feasible [164.9, 186.6]
    ClothSpring_1_1_0  thigh.R   r 67.4   NO -- spine x237          CROSS by 0.3 mm
    ClothSpring_1_2_0  spine     r 41.4   yes -- spine x171         CROSS by 13.8 mm
    ClothSpring_1_3_0  thigh.R   r 67.4   mixed -- spine, shin.R    CROSS by 109.1 mm

Three of the four crossings are measured **from a thigh axis against spine skin**. A hem joint
beside her thigh is deepest inside the thigh capsule, so that is the axis; but the skin it would
clip into is her pelvis, 185 mm from that thigh's axis. The lower bound then asks for a thigh
capsule of 165 mm radius -- wider than her pelvis, and it would swallow her other leg. The
crossing is an artefact of two bounds living on two body parts, not a fact about her dress.

This is the same error this project has recorded twice before in other clothing: *"a number in
local space is not a measurement"*, and *"trace relative, not absolute -- anchor to the part's
OWN neighbours"*. It is also the failure `put-both-bounds-in-the-same-quantity` is about, one
level up: the first time, the two bounds were in different QUANTITIES (a radius against a
surface distance, dropping the joint radius); this time they are the same quantity measured from
different ORIGINS, which the earlier fix cannot catch.

WHAT THIS TOOL DOES INSTEAD. It inverts the question. Not "what radius for this chain", but
**for each capsule, what interval do the garment's joints jointly admit** -- with both bounds as
distances to that one capsule's axis, so a crossing means what it says.

**THE TWO BOUNDS DO NOT HAVE THE SAME MEMBERSHIP, and getting that wrong is what the control
caught here.** The first version of this file let only the skin-owning joints constrain a
capsule, and on Miku's tie -- the one case with a verified answer -- it returned [85.5, 101.7]
against the recorded, applied [85.5, 87.8]. The lower bound reproduced exactly; the upper one
was 13.9 mm too generous, and a radius taken from its midpoint would have displaced the knot on
frame one, reintroducing precisely the fault the fit tool exists to avoid. The asymmetry:

  LOWER, "big enough to reach the skin"   belongs ONLY to joints whose nearby skin is owned by
                                          this capsule's bone. Spine skin cannot tell a thigh
                                          capsule how big to be -- that is the bug above.
  UPPER, "small enough not to swallow a joint"
                                          belongs to EVERY joint of the garment, whoever owns
                                          the skin beside it. A capsule does not consult the
                                          weighting before pushing a joint out, so a joint with
                                          no skin near it -- a hem hanging in free air -- still
                                          caps the radius. Miku's `Bone01` is exactly that case:
                                          its skin is owned by `Bip01 Spine1`, which carries no
                                          collider, yet it sits 107.7 mm from the `Bip01 Spine`
                                          axis and is what holds that capsule to 87.8 mm.

So a joint can constrain a capsule it has nothing to do with, and the control is what shows it.

TWO THINGS IT REPORTS THAT ARE NOT RADII, because on this character they decide the answer:

  * **Skin with no capsule over it.** If the skin beside a joint belongs to a bone no collider
    sits on, no resizing of anything reaches that joint, and the honest answer is a NEW capsule
    rather than a bigger one. Say which bone.
  * **Joints with no skin at all nearby.** They hang clear in the rest pose and constrain
    nothing. `tie_collider_fit.py` prints these as UNMEASURED, correctly, but a reader counting
    rows sees three "unmeasured" of four and distrusts the whole table -- when in fact a hem
    hanging in free air is the expected and harmless case.

It excludes the union of ALL the garment's chain bones from "skin", not just the measured
chain's. `chain_surface_owners.py` shows that makes no difference on Jessica -- her four panels
are never within 60 mm of each other -- but it would on any garment whose panels overlap, and a
measurement that happens to be safe is not the same as one that is.

Nothing is written. A radius printed here is an input to `patch_chain_collider.py`.
"""
import math
import os
import sys
from collections import Counter

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy


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
    path, prefix = sys.argv[1], sys.argv[2]
    near_m = 0.060
    if "--near" in sys.argv:
        near_m = float(sys.argv[sys.argv.index("--near") + 1]) / 1000.0

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    chains = [s for s in springs if s[0].startswith(prefix)]
    if not chains:
        print("no chain whose name starts with %r; this file has %s"
              % (prefix, sorted(s[0] for s in springs)))
        return 2

    # ---- every joint of every matching chain, and the union of their bones
    jrows, garment_bones = [], set()
    for nm, joint_pids, _groups in chains:
        for jp in joint_pids:
            rec = joints.get(jp)
            if rec is None:
                print("joint %s of %s is not in the joint table -- unmeasured" % (jp, nm))
                return 2
            tp = go_tf.get(rec[0])
            if tp is None:
                print("joint %s of %s has no transform -- unmeasured" % (jp, nm))
                return 2
            wp, _wq, ws = world(tp)
            bone = tf.get(tp, {}).get("name") or "?"
            jrows.append((nm, bone, wp, rec[4] * ws[0]))
            garment_bones.add(bone)

    # ---- every collider in world space, with the bone it sits on
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
                      float(t.get("Radius", 0.0)) * ws[0], a, b,
                      int(t.get("ColliderType", 0)))
    bone_caps = {}
    for cp, (bn, cr, a, b, ct) in shapes.items():
        bone_caps.setdefault(bn, []).append(cp)

    print("chains matching %r: %d, %d joint(s) total" % (prefix, len(chains), len(jrows)))
    print("colliders in this file: %d on %d bone(s) -- %s"
          % (len(shapes), len(bone_caps),
             ", ".join("%s(%s)" % (b, "/".join("%.0f" % (shapes[c][1] * 1000) for c in cs))
                       for b, cs in sorted(bone_caps.items()))))
    print()

    # ---- decode skin once, excluding the WHOLE garment
    env = UnityPy.load(path)
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())
    skin = []
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
            if bn in garment_bones:
                continue                      # the garment is not the body
            skin.append((bn, ps.xform(mats[best], V[vi])))
    if not skin:
        print("NO SKIN decoded -- the lower bound does not exist. Stopping rather than")
        print("printing a radius that is unconstrained on the side that matters.")
        return 1
    print("%d skin vertices decoded (garment excluded: %d bone(s))"
          % (len(skin), len(garment_bones)))
    print()

    # ---- IS A SINGLE RADIUS ABOUT THIS AXIS A DESCRIPTION OF THE BODY AT ALL?
    #
    # A capsule is a swept SPHERE: radius r reaches r in EVERY direction at every height along
    # the axis. So one radius can stand in for a body only where that body is roughly one
    # distance from the axis all the way round. A radius chosen to reach the front of a torso
    # from an axis near its back protrudes out of the back by the difference -- the rest-pose
    # arithmetic for the front panel is satisfied and the collider is still the wrong shape in
    # the wrong place.
    #
    # THE STATISTIC IS A PERCENTILE SPREAD, NOT A MINIMUM, and that is not a convenience.
    # The first version of this gate used min(skin distance) and REJECTED MIKU'S VERIFIED
    # FIX: one vertex weighted to `Bip01 Spine` sits 6.7 mm from her spine axis -- near where
    # the segment ends -- so the minimum said her applied, working 86.6 mm capsule protruded
    # 79.9 mm out of her. One vertex, and a control that had already been confirmed in the
    # bundle came back rejected. `a-threshold-discards-data-silently` is about the same shape.
    #
    # Only skin whose projection falls WITHIN the axis segment is counted, because a vertex
    # past the end of a capsule is measured to its cap and is not "around" the axis at all.
    skin_prof = {}
    for cp, (bn, cr, a, b, ct) in shapes.items():
        ab = [b[i] - a[i] for i in range(3)]
        L = sum(x * x for x in ab)
        ds = []
        for vbn, p in skin:
            if vbn != bn:
                continue
            if L > 0:
                t = sum((p[i] - a[i]) * ab[i] for i in range(3)) / L
                if t < 0.0 or t > 1.0:
                    continue            # past an end cap: not around the axis
            ds.append(seg_dist(p, a, b))
        if len(ds) >= 20:
            ds.sort()
            skin_prof[cp] = (ds[int(len(ds) * 0.10)], ds[len(ds) // 2],
                             ds[int(len(ds) * 0.90)], len(ds))

    # ---- per joint: who owns the nearby skin, and which capsule could reach it
    print("=" * 78)
    print("PER JOINT -- the capsule is chosen by WHOSE SKIN IS BESIDE THE JOINT, so that")
    print("both bounds below are distances to one axis on one body part.")
    print("=" * 78)
    print("%-20s %-12s %7s %9s %9s %9s" %
          ("joint", "skin owner", "verts", "min r", "max r", "width"))
    print("-" * 78)
    lows = {}                 # capsule pathID -> [(chain, joint bone, lo)] -- OWNERS ONLY
    free, orphan = [], []
    for cname, bone, wp, jr in jrows:
        nearby = [(bn, p) for bn, p in skin
                  if sum((p[i] - wp[i]) ** 2 for i in range(3)) < near_m * near_m]
        if not nearby:
            free.append((cname, bone))
            print("%-20s %-12s %7s   -- no skin within %.0f mm: constrains nothing"
                  % (bone[:20], "(none)", 0, near_m * 1000))
            continue
        owner = Counter(bn for bn, _p in nearby).most_common(1)[0][0]
        mine = [p for bn, p in nearby if bn == owner]
        caps = bone_caps.get(owner)
        if not caps:
            orphan.append((cname, bone, owner, len(mine)))
            print("%-20s %-12s %7d   -- NO CAPSULE on that bone: unreachable by resizing"
                  % (bone[:20], owner[:12], len(mine)))
            continue
        # the capsule on that bone the joint is nearest to, if the bone carries several
        cp = min(caps, key=lambda c: seg_dist(wp, shapes[c][2], shapes[c][3]))
        _bn, cr, a, b, _ct = shapes[cp]
        ds = sorted(seg_dist(p, a, b) for p in mine)
        lo = ds[len(ds) // 2] - jr               # median skin, as tie_collider_fit.py does
        hi = seg_dist(wp, a, b) - jr
        lows.setdefault(cp, []).append((cname, bone, lo))
        print("%-20s %-12s %7d %9.1f %9.1f %9.1f"
              % (bone[:20], owner[:12], len(mine), lo * 1000, hi * 1000, (hi - lo) * 1000))
    print()
    if free:
        print("%d joint(s) hang clear of all skin at rest and constrain nothing: %s"
              % (len(free), ", ".join(b for _c, b in free)))
        print("That is the expected case for a hem and is not a failed measurement.")
        print()
    if orphan:
        print("%d joint(s) sit beside skin on a bone that carries NO collider:" % len(orphan))
        for _c, b, own, n in orphan:
            print("    %-22s skin owned by %-12s (%d verts) -- needs a NEW capsule there,"
                  % (b[:22], own, n))
            print("    %-22s not a bigger one elsewhere." % "")
        print()

    # ---- per capsule: the interval every joint referencing it jointly admits
    print("=" * 78)
    print("PER CAPSULE -- the LOWER bound comes only from joints whose skin this bone owns;")
    print("the UPPER bound comes from EVERY joint of the garment, because a capsule pushes")
    print("out whatever is inside it without consulting the weighting. Miku's Bone01 is the")
    print("case that proves the difference: its skin belongs to a bone with no collider, and")
    print("it is still what holds her spine capsule to 87.8 mm.")
    print("=" * 78)
    any_fix = False
    for cp, rows in sorted(lows.items(), key=lambda kv: shapes[kv[0]][0]):
        bn, cr, a, b, ct = shapes[cp]
        # UPPER: every joint that will REFERENCE this capsule, which depends on how the fix
        # is wired. Shrinking the shared Body capsule exposes every chain in the garment;
        # cloning it into a group of one chain's own -- what patch_chain_collider.py does,
        # and what Miku got -- exposes only that chain. Both are printed, because the
        # narrower one is only available if the capsule is cloned rather than resized.
        per_chain = {}
        for cn, jb, wp, jr in jrows:
            d = seg_dist(wp, a, b) - jr
            if cn not in per_chain or d < per_chain[cn][1]:
                per_chain[cn] = (jb, d, jr)
        need = max(r[2] for r in rows)
        binder, cap, _jr = min(per_chain.values(), key=lambda t: t[1])
        print()
        print("capsule on %r -- %s, radius now %.1f mm"
              % (bn, "capsule" if ct == 1 else "sphere", cr * 1000))
        prof = skin_prof.get(cp)
        if prof is None:
            print("    too little skin on this bone around the axis to say whether one")
            print("    radius describes it -- the gate below is UNAVAILABLE, not passed.")
        else:
            p10, p50, p90, n = prof
            print("    this bone's skin around the axis (%d verts): p10 %.1f  median %.1f  "
                  "p90 %.1f mm" % (n, p10 * 1000, p50 * 1000, p90 * 1000))
            print("    a usable radius lies inside that band; above p90 the capsule is")
            print("    outside her almost everywhere, below p10 it guards almost nothing.")
        for cn, jb, lo in sorted(rows, key=lambda t: -t[2]):
            print("    needs >= %6.1f mm   to reach the skin beside %s" % (lo * 1000, jb))
        print("    SHARED  (resize in place, every chain sees it):")
        print("        must stay <= %6.1f mm, held by %s" % (cap * 1000, binder))
        if need > cap:
            print("        BOUNDS CROSS by %.1f mm" % ((need - cap) * 1000))
        else:
            any_fix = True
            print("        FEASIBLE r in [%.1f, %.1f] mm, width %.1f -- SUGGESTED %.1f mm "
                  "(%+.1f mm)" % (need * 1000, cap * 1000, (cap - need) * 1000,
                                  (need + cap) * 500, (need + cap) / 2.0 * 1000 - cr * 1000))
        # CLONED: each chain gets its OWN lower bound as well as its own cap. Using the
        # shared `need` here -- the max across all four chains -- was this file's second
        # bug, and it reported two feasible chains as crossing: a capsule cloned for one
        # chain is never asked to reach another chain's skin.
        print("    CLONED into a group of one chain's own (patch_chain_collider.py),")
        print("    each chain against its OWN lower bound:")
        own = {}
        for cn, jb, lo in rows:
            own[cn] = max(lo, own.get(cn, 0.0))
        for cn in sorted(own):
            lo, (jb, d, jr) = own[cn], per_chain[cn]
            if lo > d:
                print("        %-20s [%6.1f, %6.1f] -- CROSSES by %.1f mm (cap held by %s)"
                      % (cn[:20], lo * 1000, d * 1000, (lo - d) * 1000, jb[:18]))
            else:
                rec = (lo + d) / 2.0
                # The radius must sit inside the band the body's own surface occupies around
                # this axis. Outside it, one radius is not a description of this body: it is
                # a sphere swept along a line that happens to touch the panel in the rest
                # pose. The band is the DATA's own spread, not a tolerance picked by me.
                bad = prof is not None and not (prof[0] <= rec <= prof[2])
                if not bad:
                    any_fix = True
                print("        %-20s [%6.1f, %6.1f] -- %s, width %.1f, r = %.1f mm"
                      % (cn[:20], lo * 1000, d * 1000,
                         "ARITHMETIC ONLY" if bad else "FEASIBLE",
                         (d - lo) * 1000, rec * 1000))
                if bad:
                    side = "above p90 %.1f" % (prof[2] * 1000) if rec > prof[2] \
                        else "below p10 %.1f" % (prof[0] * 1000)
                    print("            REJECTED: %.1f mm is %s mm, so one radius about this"
                          % (rec * 1000, side))
                    print("            axis is not a description of this body. The rest-pose")
                    print("            arithmetic is satisfied and the collider would still")
                    print("            be the wrong shape in the wrong place -- it would hold")
                    print("            the panel at a fixed distance from an axis the body is")
                    print("            not at a fixed distance from. Needs a NEW capsule,")
                    print("            placed where the panel hangs, not an existing one")
                    print("            resized. patch_chain_collider.py cannot do that.")
        skipped = [cn for cn in sorted(per_chain) if cn not in own]
        if skipped:
            print("        no skin on this bone beside: %s -- this capsule is not their"
                  % ", ".join(c[:20] for c in skipped))
            print("        reference, and cloning it for them would guard nothing.")
    print()
    if not any_fix and lows:
        print("No capsule admits a radius satisfying every joint that would reference it,")
        print("shared or cloned. That is a finding, not a failure to compute one.")
    return 0 if lows else 1


if __name__ == "__main__":
    sys.exit(main())
