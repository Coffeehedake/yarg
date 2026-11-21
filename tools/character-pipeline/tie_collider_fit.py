# -*- coding: utf-8 -*-
"""What radius of chest capsule clears a chain's joints AND still stands in for the torso?

    python tie_collider_fit.py <file.yargchar> <chain name> [bone-name-prefix-for-the-chain-mesh]

WHY THIS EXISTS. Miku's necktie chain carries no collider group, on purpose. All three of its
bones start INSIDE the `Body` group's spine capsule, and a spring solver's first act is to push
a joint out to the collider surface -- so attaching that group would displace the knot ~44 mm
forward on frame one, before anything moved, reproducing a "tie sticking straight out" fault
that had been fixed the same morning. The recorded decision was to attach nothing and accept
that the tie "can in principle swing through her chest".

Jay reported on 2026-11-21 that it does so in practice. That does not overturn the clearance
measurement; it changes which of the two faults is worse. And the reason given for not fixing it
-- *shrinking the capsule is not available, because the twintail chains share it* -- only rules
out shrinking the SHARED capsule. A chain may reference a group of its own.

So the question is whether a radius exists that satisfies two opposing constraints:

  BIG ENOUGH   to stand in for the torso, or the tie passes through her chest anyway and the
               collider is decoration. The bound is where her chest SURFACE actually is.
  SMALL ENOUGH that every joint of the chain is outside it at rest, or the solver displaces the
               chain on frame one -- the exact fault that made the shared group unusable.

**If those two bounds cross, there is no such radius and the honest answer is that this fix is
not available.** This tool is written to be able to say that. A tie knot rests ON the chest, so
the two bounds are expected to be close, and a tool that always returns a number would return
one here whether or not it meant anything.

WHAT IT MEASURES, all in the bundle's rest pose and all against the chain's OWN neighbourhood:

  * each joint's clearance to every collider in every group, exactly as `patch_add_springs.py`
    computes it -- `seg_dist(joint, a, b) - collider_radius - joint_radius` -- so the number
    here and the number its guard will check are the same number.
  * the distance from each joint to the spine capsule's AXIS, which is the upper bound on a
    capsule radius that still clears that joint.
  * where the body surface sits beside each joint: the distance from the axis to the nearest
    BODY vertices, excluding the chain's own geometry. Including it would measure the tie and
    report that the tie clears itself.

Nothing is written. The radius it prints is an input to `patch_add_springs.py`, not a patch.
"""
import math
import os
import sys

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy


def seg_dist(p, a, b):
    """Point-to-segment distance. Same function as patch_add_springs.seg_dist, on purpose."""
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
    path, chain_name = sys.argv[1], sys.argv[2]

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)

    chain = None
    for s in springs:
        if s[0] == chain_name:
            chain = s
            break
    if chain is None:
        print("no chain called %r; this file has %s"
              % (chain_name, sorted(s[0] for s in springs)))
        return 2
    _nm, joint_pids, group_refs = chain

    # Joint world positions. cci.read gives joints as
    # (gameObject pathID, stiffness, drag, gravity, jointRadius) -- the radius is the LAST
    # field, not the second. Reading it positionally without checking is how a clearance
    # comes out scaled by a stiffness.
    jrows = []
    for jp in joint_pids:
        rec = joints.get(jp)
        if rec is None:
            print("joint %s is not in the joint table -- unmeasured" % jp)
            return 2
        gid, radius = rec[0], rec[4]
        tp = go_tf.get(gid)
        if tp is None:
            print("joint %s has no transform -- unmeasured" % jp)
            return 2
        wp, _wq, ws = world(tp)
        bone = tf.get(tp, {}).get("name") or "?"
        jrows.append((bone, wp, radius * ws[0]))

    print("chain %r: %d joint(s), %d collider group(s) attached"
          % (chain_name, len(jrows), len(group_refs)))
    print()

    # --- Resolve every collider into world space, the way cloth_collide_installed does:
    # Offset and Tail are in the collider BONE's frame, so they go through that bone's
    # matrix. Read as world offsets they land in the wrong place and every clearance below
    # is wrong in a way that still looks like a number.
    shapes = {}
    for cp, t in colliders.items():
        gid = (t.get("m_GameObject") or {}).get("m_PathID")
        tp = go_tf.get(gid)
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
                      t.get("ColliderType", 0),
                      float(t.get("Radius", 0.0)) * ws[0], a, b)

    # Which group each collider belongs to, so the report says what would be shared.
    owner = {}
    for gp, cps in groups.items():
        for cp in cps:
            owner.setdefault(cp, []).append(gp)

    print("%-20s %-20s %9s %10s %10s" %
          ("joint", "collider on", "col r(mm)", "axis d(mm)", "clear(mm)"))
    print("-" * 76)
    axis_limits = []
    spine = None
    for bone, wp, jr in jrows:
        for cp, (cname, ctype, cr, a, b) in sorted(shapes.items()):
            d = seg_dist(wp, a, b)
            clear = d - cr - jr
            print("%-20s %-20s %9.1f %10.1f %10.1f"
                  % (bone[:20], cname[:20], cr * 1000, d * 1000, clear * 1000))
        print()
    # The capsule standing in for the torso is the one the joints are deepest inside.
    deepest, dcp = None, None
    for cp, (cname, ctype, cr, a, b) in shapes.items():
        worst = min(seg_dist(wp, a, b) - cr - jr for _bn, wp, jr in jrows)
        if deepest is None or worst < deepest:
            deepest, dcp = worst, cp
    if dcp is not None:
        cname, _ct, cr, a, b = shapes[dcp]
        spine = (cname, a, b, cr)
        for bone, wp, jr in jrows:
            axis_limits.append((bone, seg_dist(wp, a, b), jr, cname, a, b))
        print("The capsule the chain is deepest inside is the one on %r (r %.1f mm), "
              "worst clearance %.1f mm. That is the one standing in for the torso."
              % (cname, cr * 1000, deepest * 1000))
    print()

    if spine is None:
        print("NO SPINE OR CHEST COLLIDER in this file -- there is nothing to shrink, and a")
        print("new capsule would have to be placed as well as sized. Unmeasured, not 'fine'.")
        return 1

    cname, a, b, cr = spine
    # UPPER BOUND on a capsule radius that still clears every joint. The joint's own radius
    # counts: the solver pushes the joint SPHERE out, not the joint point.
    upper = min(d - jr for _bn, d, jr, _c, _a, _b in axis_limits)
    print("CLEARANCE BOUND. Capsule on %r must be smaller than %.1f mm, or a joint starts"
          % (cname, upper * 1000))
    print("inside it and the solver displaces the chain on frame one.")
    for bn, d, jr, _c, _a, _b in axis_limits:
        print("    %-22s axis distance %6.1f mm, joint radius %4.1f mm -> bound %6.1f mm"
              % (bn[:22], d * 1000, jr * 1000, (d - jr) * 1000))
    print()

    # --- Where the body surface actually is, beside each joint.
    env = UnityPy.load(path)
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    chain_bones = set(bn for bn, _w, _r in jrows)
    body = []
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
                w, bi = W[vi][k], I[vi][k]
                if w > bw and w > 0 and bi < len(skin):
                    bw, best = w, bi
            if best is None:
                continue
            nm = tf.get(bones[best], {}).get("name") or ""
            # EXCLUDE the chain's own geometry. A tie that clears itself is not a measurement.
            if nm in chain_bones:
                continue
            body.append(ps.xform(skin[best], V[vi]))

    if not body:
        print("NO BODY GEOMETRY decoded -- the surface bound is unmeasured, which is not the")
        print("same as unconstrained. Stopping rather than printing a radius.")
        return 1

    print("SURFACE BOUND. Body vertices within 60 mm of each joint, excluding the chain's own")
    print("geometry (%d body vertices decoded):" % len(body))
    surface = []
    for bn, wp, jr in jrows:
        near = [p for p in body
                if sum((p[i] - wp[i]) ** 2 for i in range(3)) < 0.060 ** 2]
        if not near:
            # Keep the list aligned with axis_limits. Dropping the row instead would shift
            # every later joint's surface onto the wrong joint, silently.
            surface.append(None)
            print("    %-22s no body vertex within 60 mm -- UNMEASURED" % bn[:22])
            continue
        ds = sorted(seg_dist(p, a, b) for p in near)
        med = ds[len(ds) // 2]
        surface.append(med)
        print("    %-22s %4d verts, axis distance min %5.1f  median %5.1f  max %5.1f mm"
              % (bn[:22], len(near), ds[0] * 1000, med * 1000, ds[-1] * 1000))
    print()

    # BOTH BOUNDS ARE ON THE SAME QUANTITY, and that quantity is not the capsule radius.
    # The solver holds the joint CENTRE at `r_capsule + r_joint` from the axis, so every
    # comparison has to be made in standoff, then converted back once. Comparing a capsule
    # radius directly against a surface distance drops the joint radius -- 20 mm here --
    # and on the first run of this tool that made a feasible fix read as impossible.
    print("VERDICT -- all bounds expressed as the capsule radius, after subtracting each")
    print("joint's own radius, because the solver holds the joint CENTRE at r_capsule +")
    print("r_joint and a radius compared against a surface distance is comparing two")
    print("different things.")
    print()
    print("    shared capsule on %-18s %6.1f mm   (what the Body group uses today)"
          % (cname[:18], cr * 1000))
    print()
    lows, highs = [], []
    print("    %-20s %12s %12s %12s" % ("joint", "min r (mm)", "max r (mm)", "width"))
    unmeasured = []
    for (bn, d, jr, _c, _a, _b), surf in zip(axis_limits, surface):
        hi = d - jr             # larger than this and the joint starts inside the capsule
        highs.append(hi)
        if surf is None:
            unmeasured.append(bn)
            print("    %-20s %12s %12.1f %12s"
                  % (bn[:20], "UNMEASURED", hi * 1000, "-"))
            continue
        lo = surf - jr          # smaller than this and the joint sinks inside the body
        lows.append(lo)
        print("    %-20s %12.1f %12.1f %12.1f"
              % (bn[:20], lo * 1000, hi * 1000, (hi - lo) * 1000))
    if not lows:
        print()
        print("    NO joint had measurable body surface beside it, so the lower bound does")
        print("    not exist and any radius printed here would be unconstrained on the side")
        print("    that matters. Stopping.")
        return 1
    if unmeasured:
        print()
        print("    %d joint(s) had no body surface measured (%s). The interval below is"
              % (len(unmeasured), ", ".join(unmeasured)))
        print("    therefore constrained by the others only.")
    need, cap = max(lows), min(highs)
    print()
    print("    FEASIBLE INTERVAL  r in [%.1f, %.1f] mm" % (need * 1000, cap * 1000))
    if need > cap:
        print()
        print("    THE BOUNDS CROSS, by %.1f mm. No single capsule both keeps every joint"
              % ((need - cap) * 1000))
        print("    outside the body and leaves every joint outside itself at rest, so this")
        print("    fix is not available as a single capsule. Say so rather than shipping a")
        print("    number.")
        return 1
    rec = (need + cap) / 2.0
    print("    SUGGESTED          r = %.1f mm (midpoint)" % (rec * 1000))
    print()
    print("    At that radius the solver holds each joint centre %.1f mm from the axis:"
          % ((rec + jrows[0][2]) * 1000))
    for (bn, d, jr, _c, _a, _b), surf in zip(axis_limits, surface):
        if surf is None:
            print("      %-20s stands off %6.1f mm, body surface UNMEASURED; "
                  "rest clearance %+.1f mm"
                  % (bn[:20], (rec + jr) * 1000, (d - rec - jr) * 1000))
            continue
        print("      %-20s stands off %6.1f mm, body surface %6.1f mm -> %+.1f mm outside; "
              "rest clearance %+.1f mm"
              % (bn[:20], (rec + jr) * 1000, surf * 1000,
                 (rec + jr - surf) * 1000, (d - rec - jr) * 1000))
    print()
    print("    The interval is %.1f mm wide. It is narrow whenever the chain RESTS against"
          % ((cap - need) * 1000))
    print("    the body -- a tie knot or a cape attachment has almost no room between")
    print("    'outside the surface' and 'where it already is' -- and wide when the chain")
    print("    hangs clear. A tight interval is an honest answer, not a weak one, but it")
    print("    means the rest clearance will be small, and the guard in the patcher is what")
    print("    confirms it rather than this tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
