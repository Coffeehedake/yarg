# -*- coding: utf-8 -*-
"""Find WHERE a collider capsule has to be, not just how big. Then say if no single one works.

    python fit_body_capsule.py <file.yargchar> <chain-prefix> \n           [--garment PREFIX] [--host BONE] [--near MM]

e.g.  python fit_body_capsule.py "Jessica Rabbit.yargchar" ClothSpring_1_

WHY THIS EXISTS. `tie_collider_fit.py` and `garment_collider_fit.py` both answer "what RADIUS",
taking the axis as given by whichever bone already carries a collider. For Miku's necktie that is
enough: her spine capsule is already in the right place and only its radius was wrong. For
Jessica Rabbit's four-panel skirt it is not, and the reason is recorded in `garment_collider_fit`
-- her `spine` collider runs up her BACK, 250 mm behind her front panel, so a radius that reaches
her front protrudes the same distance out of her back. Three of her four panels came back
"arithmetic only": a number that satisfies the rest-pose inequalities about an axis that is in
the wrong place.

So this tool solves for the axis. The inequalities are the same ones, and they are worth writing
down because the whole fit is two lines of arithmetic per joint:

    the solver holds a joint CENTRE at  r + j  from the axis, where j is the joint radius.
    it must not be pulled nearer the axis than the SKIN is        ->  r + j >= s
    it must not START inside the capsule and be shoved on frame 1 ->  r + j <= d

  s   the median distance from the axis to the skin beside that joint, garment excluded
  d   that joint's own distance to the axis at rest

A capsule exists iff `max(s) <= min(d)` over the joints, so **the axis is whatever position
makes that true**, and the quantity to maximise is `min(d) - max(s)`. Positive is a feasible
interval whose width it reports; negative means no vertical capsule in that position works, and
the tool prints the best position anyway together with how far short it falls, because "how
close" is the thing that decides whether to try two capsules or give up.

WHAT IT SEARCHES, and the first version of this got it wrong in a way only the control could
show. Four parameters: the horizontal position of each END of a segment spanning the garment's
height band, by coordinate descent. **Not a vertical axis.** The first version searched vertical
position only, on the stated grounds that "every body axis in this roster is vertical", and
Miku's tie refuted it immediately: her verified capsule runs from (0, 0.8885, **+0.0651**) to
(0, 1.3220, **-0.0026**), leaning forward at the bottom by 65 mm as her torso does. At her real
axis the slack is **+2.3 mm**; the best VERTICAL axis anywhere scores **-33.8 mm**, and the
search ran 280 mm out to the side chasing a shallow maximum rather than report failure. A
restriction asserted from the roster, contradicted by the one character whose answer was known.

So the tilt is not a refinement, it is the difference between an answer and a false negative.

WHAT IT CANNOT FIX, stated here so a negative result is not mistaken for a bug. A cape's top
joints are AUTHORED under the skin -- Batman's sit at 141.7 mm with his surface at 149.4 -- so
for those joints `s > d` whatever the axis is, and no capsule anywhere satisfies both bounds.
That is not a placement problem. It needs those joints excluded from collision, and a VRM
collider group attaches to a SPRING and not to a joint, so excluding them means splitting the
chain. This tool reports which joints are individually impossible, because that is the
difference between "move the capsule" and "change the rig".

Nothing is written. Feed the result to `place_collider.py`.
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


def read_all(path, prefix, near_m, garment_prefix=None):
    """`prefix` selects the chains to FIT. `garment_prefix` selects what counts as cloth.

    They are separate because a four-panel skirt is fitted one panel at a time -- each panel
    gets its own collider group, so each is its own problem -- while all four panels must
    still be excluded from "skin". Fitting one chain with only that chain excluded would let
    a neighbouring panel stand in for her body and set the lower bound from cloth.
    """
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    chains = [s for s in springs if s[0].startswith(prefix)]
    if not chains:
        raise SystemExit("no chain whose name starts with %r; this file has %s"
                         % (prefix, sorted(s[0] for s in springs)))
    gp = garment_prefix or prefix
    garment = set()
    for nm, jps, _g in springs:
        if not nm.startswith(gp):
            continue
        for jp in jps:
            rec = joints.get(jp)
            tp = go_tf.get(rec[0]) if rec else None
            if tp is not None:
                garment.add(tf.get(tp, {}).get("name") or "?")
    jrows = []
    for nm, jps, _g in chains:
        for jp in jps:
            rec = joints.get(jp)
            tp = go_tf.get(rec[0]) if rec else None
            if rec is None or tp is None:
                raise SystemExit("a joint of %s has no transform -- unmeasured" % nm)
            wp, _wq, ws = world(tp)
            jrows.append([nm, tf.get(tp, {}).get("name") or "?", wp, rec[4] * ws[0], None])

    env = UnityPy.load(path)
    tt, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())
    skin = []
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
            for kk in range(len(W[vi])):
                wgt, bi = W[vi][kk], I[vi][kk]
                if wgt > bw and wgt > 0 and bi < len(mats):
                    bw, best = wgt, bi
            if best is None:
                continue
            bn = tf.get(bones[best], {}).get("name") or "?"
            if bn in garment:
                continue
            skin.append((bn, ps.xform(mats[best], V[vi])))
    if not skin:
        raise SystemExit("NO SKIN decoded -- there is no lower bound and nothing to fit.")

    # The skin beside each joint, chosen by proximity to the JOINT and then measured to
    # whatever axis is under test. Selection is joint-relative so it does not move with the
    # candidate; that is deliberate -- it is the surface that joint could sink into.
    for row in jrows:
        wp = row[2]
        row[4] = [p for _bn, p in skin
                  if sum((p[i] - wp[i]) ** 2 for i in range(3)) < near_m * near_m] or None
    return tf, go_tf, world, skin, jrows, garment, chains


def body_slices(skin, y0, y1, n=12):
    """Per-height (centroid, median horizontal radius) of the skin, for the inside test.

    WHY THE SEARCH NEEDS THIS. The inequalities alone do not say where the axis may be, and
    an unconstrained optimiser exploits that: fitting Jessica's front panel it put the axis
    bottom at x = -0.313, which is 313 mm out to her LEFT, in mid-air. That satisfies both
    bounds and is not a stand-in for her body -- the same "arithmetic only" failure that
    `garment_collider_fit.py` has a gate for, arrived at from the other direction. A collider
    meant to approximate a body has to be INSIDE it, so that is a constraint and not a
    post-hoc check.
    """
    out = []
    for i in range(n):
        y = y0 + (y1 - y0) * (i + 0.5) / n
        h = (y1 - y0) / n
        band = [p for _b, p in skin if abs(p[1] - y) <= h]
        if len(band) < 20:
            out.append(None)
            continue
        cx = sum(p[0] for p in band) / len(band)
        cz = sum(p[2] for p in band) / len(band)
        rs = sorted(math.sqrt((p[0] - cx) ** 2 + (p[2] - cz) ** 2) for p in band)
        out.append((y, cx, cz, rs[len(rs) // 2]))
    return [s for s in out if s]


def inside(slices, x, y, z):
    """Is (x, y, z) within the body's own horizontal spread at its height?"""
    if not slices:
        return True
    s = min(slices, key=lambda t: abs(t[0] - y))
    return math.sqrt((x - s[1]) ** 2 + (z - s[2]) ** 2) <= s[3]


def score(jrows, a, b, slices=None):
    """(min d - max s, min d, max s, binding joint, binding skin joint) for an axis a->b.

    Takes the two world endpoints directly, so the same function scores a candidate from the
    search AND an axis read out of an existing bundle. That matters: the control for this
    tool is not "does the search rediscover Miku's capsule" -- it is an optimiser and there
    are many feasible axes -- but "does it read the installed, verified capsule as feasible".
    One function, both jobs, or the control is checking different arithmetic.
    """
    if slices is not None and not (inside(slices, *a) and inside(slices, *b)):
        return None                      # outside the body: not a candidate at all
    dmin, smax, dj, sj = None, None, None, None
    for _cn, bn, wp, jr, near in jrows:
        d = seg_dist(wp, a, b) - jr
        if dmin is None or d < dmin:
            dmin, dj = d, bn
        if near:
            ds = sorted(seg_dist(p, a, b) for p in near)
            s = ds[len(ds) // 2] - jr
            if smax is None or s > smax:
                smax, sj = s, bn
    if smax is None:
        return None
    return (dmin - smax, dmin, smax, dj, sj)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path, prefix = sys.argv[1], sys.argv[2]
    near_m = 0.060
    if "--near" in sys.argv:
        near_m = float(sys.argv[sys.argv.index("--near") + 1]) / 1000.0
    host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else None
    gp = sys.argv[sys.argv.index("--garment") + 1] if "--garment" in sys.argv else None

    tf, go_tf, world, skin, jrows, garment, chains = read_all(path, prefix, near_m, gp)
    ys = [r[2][1] for r in jrows]
    y0, y1 = min(ys), max(ys)
    print("%d chain(s) matching %r, %d joint(s), height band %.3f to %.3f m"
          % (len(chains), prefix, len(jrows), y0, y1))
    print("%d skin vertices (garment excluded)" % len(skin))
    nos = [r[1] for r in jrows if not r[4]]
    if nos:
        print("%d joint(s) have no skin within %.0f mm; they bound the radius from above "
              "only" % (len(nos), near_m * 1000))
    print()

    # ---- search the horizontal position of a vertical axis
    cx = sum(p[0] for _b, p in skin) / len(skin)
    cz = sum(p[2] for _b, p in skin) / len(skin)
    slices = body_slices(skin, y0, y1)
    print("body cross-section, %d height slices: median radius %.1f to %.1f mm"
          % (len(slices), min(s[3] for s in slices) * 1000,
             max(s[3] for s in slices) * 1000))
    print("the axis is CONSTRAINED to stay inside that -- see body_slices()")
    print()
    # START ON THE BODY'S OWN AXIS, which is the per-slice centroid at each end -- NOT the
    # whole-body centroid. For a skirt spanning hip to ankle the global centroid is 150 mm
    # behind her ankles, so it starts OUTSIDE the body at the lower end, the inside
    # constraint rejects it, and the search dies on its first evaluation with a message
    # about there being nothing to fit. The starting point has to satisfy the constraints.
    lo_s = min(slices, key=lambda t: abs(t[0] - y0))
    hi_s = min(slices, key=lambda t: abs(t[0] - y1))
    if "--at" in sys.argv:
        nums = [float(x) for x in sys.argv[sys.argv.index("--at") + 1].split(",")]
        if len(nums) != 6:
            print("--at takes x0,y0,z0,x1,y1,z1 in WORLD metres (6 numbers)")
            return 2
        aa0, bb0 = tuple(nums[:3]), tuple(nums[3:])
        g = score(jrows, aa0, bb0, None)
        if g is None:
            print("that axis has no measurable skin beside any joint.")
            return 1
        print("SCORING A GIVEN AXIS (no search):")
        print("    inside the body at both ends: %s / %s"
              % (inside(slices, *aa0), inside(slices, *bb0)))
        print("    highest skin bound %8.1f mm, set by %s" % (g[2] * 1000, g[4]))
        print("    lowest joint bound %8.1f mm, set by %s" % (g[1] * 1000, g[3]))
        if g[0] <= 0:
            print("    BOUNDS CROSS by %.1f mm" % (-g[0] * 1000))
            return 1
        print("    FEASIBLE r in [%.1f, %.1f] mm, width %.1f -- midpoint %.1f mm"
              % (g[2] * 1000, g[1] * 1000, g[0] * 1000, (g[1] + g[2]) * 500))
        return 0

    axp = [lo_s[1], lo_s[2], hi_s[1], hi_s[2]]
    best = score(jrows, (axp[0], y0, axp[1]), (axp[2], y1, axp[3]), slices)
    if best is None:
        print("even the body's own axis is rejected at one end, or no joint has measurable")
        print("skin beside it. Either way there is nothing to fit against here.")
        return 1
    step = 0.060
    while step > 0.0005:
        moved = False
        for i in range(4):
            for d in (-step, step):
                q = list(axp)
                q[i] += d
                s = score(jrows, (q[0], y0, q[1]), (q[2], y1, q[3]), slices)
                if s is not None and s[0] > best[0]:
                    best, axp, moved = s, q, True
        if not moved:
            step /= 2.0
    slack, dmin, smax, dj, sj = best
    print("BEST AXIS  bottom (%.4f, %.3f, %.4f)  top (%.4f, %.3f, %.4f)"
          % (axp[0], y0, axp[1], axp[2], y1, axp[3]))
    print("           tilt %.1f mm over %.0f mm of height; body centroid x %.4f z %.4f"
          % (math.sqrt((axp[2] - axp[0]) ** 2 + (axp[3] - axp[1]) ** 2) * 1000,
             (y1 - y0) * 1000, cx, cz))
    print("    highest skin bound   %8.1f mm, set by %s" % (smax * 1000, sj))
    print("    lowest joint bound   %8.1f mm, set by %s" % (dmin * 1000, dj))
    print("    slack                %8.1f mm" % (slack * 1000))
    print()

    # ---- which joints block, AT THE BEST AXIS. This is reported here rather than as an
    # axis-independent property because an axis-independent claim is not available cheaply:
    # s and d both move when the axis moves. What the search gives is the best position
    # found, and a joint whose own interval is still empty THERE is the one to look at --
    # for a cape that will be the attachment joints, which are authored under the skin and
    # which no capsule anywhere can hold outside a surface they start inside.
    aa, bb = (axp[0], y0, axp[1]), (axp[2], y1, axp[3])
    print("PER JOINT at that axis -- s is the skin it could sink into, d is where it starts")
    print("%-22s %10s %10s %10s   %s" % ("joint", "s (mm)", "d (mm)", "slack", "verdict"))
    print("-" * 72)
    blockers = []
    for _cn, bn, wp, jr, near in jrows:
        d = seg_dist(wp, aa, bb) - jr
        if not near:
            print("%-22s %10s %10.1f %10s   caps the radius only" % (bn[:22], "-", d * 1000, "-"))
            continue
        ds = sorted(seg_dist(p, aa, bb) for p in near)
        s = ds[len(ds) // 2] - jr
        ok = s <= d
        if not ok:
            blockers.append((bn, (s - d) * 1000))
        print("%-22s %10.1f %10.1f %10.1f   %s"
              % (bn[:22], s * 1000, d * 1000, (d - s) * 1000, "ok" if ok else "BLOCKS"))
    if blockers:
        print()
        print("%d joint(s) block at the best axis found:" % len(blockers))
        for bn, over in blockers:
            print("    %-24s skin is %.1f mm FURTHER from the axis than the joint is,"
                  % (bn[:24], over))
            print("    %-24s i.e. the joint is behind its own surface." % "")
        print("A collider cannot hold a joint outside a surface the joint starts inside, so")
        print("for these the answer is not a radius and not a position. The joints have to")
        print("leave the collided segment, and a VRM collider group attaches to a SPRING and")
        print("not to a joint -- so that means SPLITTING THE CHAIN, which is a rig change.")
    print()
    if slack <= 0:
        print("NO SINGLE CAPSULE WORKS, best position AND tilt included -- it falls %.1f mm"
              % (-slack * 1000))
        print("short. %s wants the capsule at least %.1f mm, and %s would be inside it above"
              % (sj, smax * 1000, dj))
        print("%.1f mm. Two capsules, one per side, is the next thing to try; this tool does"
              % (dmin * 1000))
        print("not fit two, because a two-capsule fit has to decide which joints each one")
        print("guards and that is a choice about the garment rather than arithmetic.")
        return 1
    r = (smax + dmin) / 2.0
    print("FEASIBLE  r in [%.1f, %.1f] mm, width %.1f -- SUGGESTED %.1f mm"
          % (smax * 1000, dmin * 1000, slack * 1000, r * 1000))

    # IS THIS CAPSULE A STAND-IN FOR THE BODY, OR BIGGER THAN IT?
    #
    # The inequalities and the inside-the-body constraint still do not settle this, and the
    # first gate I wrote here got it wrong twice. It took p10-p90 of ALL skin projecting onto
    # the axis, which for a torso-length axis pulls in arms and twintails at 675 mm, so the
    # band came out meaninglessly wide at the top and the CONTROL FAILED -- Miku's 86.6 mm
    # read as "below p10" against a band whose median was 175.8 mm of mostly her arms.
    #
    # The real objection to an over-large capsule is dynamic, not static: the solver holds a
    # joint at a constant r + j from the axis, so the garment is pushed onto a CYLINDER of
    # that radius. Where the cylinder is wider than the body, the cloth is held off the body
    # and hangs as a stiff bell instead of falling. So the test is simply whether the radius
    # exceeds the body's own radius over the garment's height:
    #
    #     Miku's verified tie   86.6 mm vs body 103.0-160.2  -- SMALLER everywhere, safe:
    #                           it under-approximates, which only means it catches less.
    #     Jessica's front panel 206.9 mm vs body  86.4-163.2 -- BIGGER everywhere, so it
    #                           would hold her skirt 40-120 mm off her body all the way
    #                           round. The rest pose is satisfied and the motion is wrong.
    rmax = max(sl[3] for sl in slices)
    print("    body's own radius over this height: %.1f to %.1f mm"
          % (min(sl[3] for sl in slices) * 1000, rmax * 1000))
    if r > rmax:
        print("    ARITHMETIC ONLY: %.1f mm is wider than the body is ANYWHERE over this"
              % (r * 1000))
        print("    height (max %.1f mm). It clears every joint and would hold the cloth off"
              % (rmax * 1000))
        print("    her on a cylinder instead of letting it fall. Do not place it.")
        print("    The lower bound that forces it is %.1f mm, set by %s -- that joint sits"
              % (smax * 1000, sj))
        print("    outside skin which is itself further from the axis than the body's own")
        print("    radius, so this panel needs a collider at the PANEL, not on the body axis.")
        return 1
    print("    the capsule is no wider than the body, so it stands in for it rather than")
    print("    replacing it with a cylinder.")
    print()

    # ---- express the result in a host bone's frame, which is what the writer needs
    owners = Counter()
    for _cn, bn, wp, jr, near in jrows:
        if not near:
            continue
        # nearest skin owner for this joint
        bestd, bestb = None, None
        for sbn, p in skin:
            dd = sum((p[i] - wp[i]) ** 2 for i in range(3))
            if dd < near_m * near_m and (bestd is None or dd < bestd):
                bestd, bestb = dd, sbn
        if bestb:
            owners[bestb] += 1
    hostbone = host or (owners.most_common(1)[0][0] if owners else None)
    if hostbone is None:
        print("no host bone could be chosen -- pass --host")
        return 1
    tp = next((pid for pid, rec in tf.items() if (rec.get("name") or "") == hostbone), None)
    if tp is None:
        print("no bone called %r in this file" % hostbone)
        return 1
    wp, wq, ws = world(tp)
    # invert the bone's world transform for the two axis endpoints: Offset and Tail are in
    # the bone's own frame, which is the whole reason a "placed" collider needs no new
    # GameObject -- the bone already provides the frame.
    # cci.qrot unpacks `w, x, y, z = q`, so the convention is (w, x, y, z) and the conjugate
    # negates the LAST THREE. The first version of this negated the first three -- w, x, y --
    # which is not any quaternion's inverse, and the consequences are worth recording because
    # nothing downstream caught it. place_collider.py faithfully wrote a capsule at the
    # garbled position and its own round-trip check passed, because that check compares what
    # it WROTE against what it was TOLD. It cannot see that what it was told was wrong. The
    # capsule landed at z = -0.65 instead of -0.20, 450 mm behind her, and every clearance
    # printed beside it was a real measurement of the wrong thing.
    iq = (wq[0], -wq[1], -wq[2], -wq[3])

    def to_local(P):
        v = (P[0] - wp[0], P[1] - wp[1], P[2] - wp[2])
        r3 = cci.qrot(iq, v)
        return (r3[0] / ws[0], r3[1] / ws[1], r3[2] / ws[2])

    def back_to_world(v):
        sc = (v[0] * ws[0], v[1] * ws[1], v[2] * ws[2])
        r3 = cci.qrot(wq, sc)
        return (wp[0] + r3[0], wp[1] + r3[1], wp[2] + r3[2])

    A, B = to_local((axp[0], y0, axp[1])), to_local((axp[2], y1, axp[3]))
    # ASSERT THE CONVERSION, HERE, in this tool. A frame change is exactly the kind of step
    # whose output looks like a plausible number whichever way it is wrong.
    for want, got in ((aa, back_to_world(A)), (bb, back_to_world(B))):
        err = math.sqrt(sum((want[i] - got[i]) ** 2 for i in range(3)))
        if err > 1e-6:
            print("THE FRAME CONVERSION IS WRONG: %s came back as %s, %.3f mm out. Not"
                  % (" ".join("%.4f" % x for x in want),
                     " ".join("%.4f" % x for x in got), err * 1000))
            print("printing arguments a writer would apply faithfully.")
            return 1
    print("AS ARGUMENTS TO place_collider.py, in the frame of bone %r:" % hostbone)
    print("    --host %s --radius %.1f \\" % (hostbone, r * 1000))
    print("    --offset %.5f,%.5f,%.5f --tail %.5f,%.5f,%.5f \\"
          % (A[0], A[1], A[2], B[0], B[1], B[2]))
    print("    --expect-world %.5f,%.5f,%.5f,%.5f,%.5f,%.5f"
          % (aa[0], aa[1], aa[2], bb[0], bb[1], bb[2]))
    print()
    print("Bone %r has world scale %.4f, so the writer divides the radius by it and must"
          % (hostbone, ws[0]))
    print("re-read what it wrote in WORLD space before keeping the file -- a local number")
    print("that round-trips to the wrong world radius is the failure to look for here.")
    print("chains to attach: %s" % ", ".join(sorted(c[0] for c in chains)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
