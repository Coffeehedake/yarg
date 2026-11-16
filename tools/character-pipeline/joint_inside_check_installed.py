# -*- coding: utf-8 -*-
"""Joints that START INSIDE one of their own chain's colliders.

    python joint_inside_check_installed.py <dir-of-yargchar | file.yargchar ...>

`patch_springs.py --collide` checks this before it HANDS a chain a collider
group. Nothing has ever checked the chains that already have one -- and that
is the direction the damage comes from, because those groups were written by
`vrm_colliders.fit` and by the characters' own authors, not by that guard.

A VRM spring joint inside a collider is not restrained by it, it is EJECTED
by it: the solver's first act is to push the joint out to the collider's
surface. On Gadget Hackwrench three hair joints sat inside a 0.193 sphere, one
of them 44% in, and the ejection threw her hair out by ~10 cm on a head 0.45
wide -- it ballooned into a mass bigger than she was. That was measured across
a batch of 23 characters as 8 with at least one joint inside, "exactly the set
that came back looking wrong", and `vrm_colliders.fit` grew its shrink-to-clear
rule in response. This asks whether the rule held, in the files that shipped.

Two joints are NOT faults and are reported separately:

  * The chain's FIRST joint is the anchor. Its position comes from the
    skeleton rather than from the simulation, so no collider can eject it, and
    guarding against it is actively harmful -- an anchor normally sits on the
    very body part the collider represents. The Xenomorph's tail root sits at
    exactly 0.0000 m from his torso capsule's axis for that reason.

  * A CHEST chain is excluded wholesale, the same way `--cloth`, the `--limbs`
    guard and `--collide` exclude it. A chest chain sits ON the torso and is
    deliberately given no collider group at all; where one has a group anyway
    it is the author's own doing and not ours to grade.

INSIDE_CONTROL=<f> multiplies every collider radius by f. A run at 3.0 must
flag nearly everything: a sweep that reports no findings and a sweep that
never ran look identical, so the control is how this one proves it walked.
"""
import os
import re
import sys

import cloth_collide_installed as cci

CHEST = cci.CHEST
CONTROL = float(os.environ.get("INSIDE_CONTROL", "1") or "1")


def seg_dist(p, a, b):
    """Distance from point p to the segment a..b."""
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    ll = sum(x * x for x in ab)
    if ll <= 0.0:
        t = 0.0
    else:
        t = sum(ap[i] * ab[i] for i in range(3)) / ll
        t = max(0.0, min(1.0, t))
    c = [a[i] + ab[i] * t for i in range(3)]
    return sum((p[i] - c[i]) ** 2 for i in range(3)) ** 0.5


def check(path):
    """(findings, anchors, nchains, ncolliders) for one bundle."""
    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(path)

    # Every collider, resolved to world space once. Offset and Tail are in
    # the collider BONE's own frame, so they go through that bone's matrix --
    # adding them to a world position instead is the mistake that makes a
    # capsule look like it is somewhere it is not.
    cols = {}
    for cp, ct in colliders.items():
        gid = (ct.get("m_GameObject") or {}).get("m_PathID")
        tp = go_tf.get(gid)
        if tp is None:
            continue
        wp, wq, wsv = world(tp)
        ws = wsv[0] if isinstance(wsv, (tuple, list)) else wsv
        off, tail = ct["Offset"], ct["Tail"]
        a = cci.qrot(wq, (off["x"] * ws, off["y"] * ws, off["z"] * ws))
        a = (wp[0] + a[0], wp[1] + a[1], wp[2] + a[2])
        if ct.get("ColliderType") == 1:
            b = cci.qrot(wq, (tail["x"] * ws, tail["y"] * ws, tail["z"] * ws))
            b = (wp[0] + b[0], wp[1] + b[1], wp[2] + b[2])
        else:
            b = a
        cols[cp] = (tf[tp]["name"], ct.get("ColliderType"),
                    ct["Radius"] * ws * CONTROL, a, b)

    findings, anchors, nchains = [], [], 0
    for sname, jids, gids in springs:
        if not gids:
            continue
        if re.search(CHEST, sname or "", re.I):
            continue
        mine = []
        for gp in gids:
            for cp in (groups.get(gp) or []):
                if cp in cols:
                    mine.append(cols[cp])
        if not mine:
            continue
        nchains += 1
        for idx, jid in enumerate(jids):
            j = joints.get(jid)
            if not j:
                continue
            tp = go_tf.get(j[0])
            if tp is None:
                continue
            jp = world(tp)[0]
            jr = j[4]
            worst = None
            for cn, ct, r, a, b in mine:
                clear = seg_dist(jp, a, b) - r - jr
                if worst is None or clear < worst[0]:
                    worst = (clear, cn, r)
            if worst is None or worst[0] >= 0.0:
                continue
            # The signature of our own shrink guard. `vrm_colliders.add()` and
            # `patch_springs.py --limbs` both shrink a collider to 0.95 of the
            # distance to the nearest non-anchor joint's CENTRE -- and the
            # solver needs centre >= collider radius + joint radius. So where
            # the guard is what set the radius, r / centre_dist is exactly
            # 0.95 and the overlap is exactly jr - 0.05 * centre_dist. Printing
            # the ratio is what tells our arithmetic apart from an author's.
            centre = worst[0] + worst[2] + jr
            ratio = (worst[2] / centre) if centre > 1e-9 else 0.0
            row = (sname, tf[tp]["name"], worst[1], worst[0], worst[2], jr,
                   ratio)
            if idx == 0:
                anchors.append(row)
            else:
                findings.append(row)
    return findings, anchors, nchains, len(cols)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            files.append(a)

    if CONTROL != 1.0:
        print("INSIDE_CONTROL=%.2f -- every collider radius multiplied, so "
              "this run is a control and its findings are not real.\n"
              % CONTROL)

    walked = flagged = tot_chains = 0
    sig = notsig = 0
    for f in files:
        name = os.path.basename(f)[:-9]
        try:
            findings, anchors, nchains, ncols = check(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-36s UNREADABLE: %s" % (name, e))
            continue
        walked += 1
        tot_chains += nchains
        if not findings:
            continue
        flagged += 1
        for row in findings:
            if abs(row[6] - 0.95) <= 0.002:
                sig += 1
            else:
                notsig += 1
        print("%s -- %d joint(s) inside, of %d guarded chain(s), %d collider(s)"
              % (name, len(findings), nchains, ncols))
        for sname, bn, cn, clear, r, jr, ratio in sorted(findings,
                                                         key=lambda x: x[3])[:10]:
            print("    chain %-22s joint %-22s %7.1f mm inside %-18s "
                  "(r %.0f mm, joint r %.0f mm, r/centre %.3f%s)"
                  % (sname[:22], (bn or "?")[:22], -clear * 1000,
                     (cn or "?")[:18], r * 1000, jr * 1000, ratio,
                     "  <-- OUR GUARD" if abs(ratio - 0.95) <= 0.002 else ""))
        if anchors:
            print("    (+ %d anchor joint(s) inside, which is expected and "
                  "harmless)" % len(anchors))

    print("\nwalked %d bundle(s), %d guarded non-chest chain(s); "
          "%d bundle(s) have a joint starting inside its own collider"
          % (walked, tot_chains, flagged))
    print("of those joints, %d carry our shrink guard's signature "
          "(r/centre = 0.950) and %d do not" % (sig, notsig))
    return 0


if __name__ == "__main__":
    sys.exit(main())
