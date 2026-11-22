# -*- coding: utf-8 -*-
"""Fit ONE capsule per body bone, from the skin that bone itself owns.

    python fit_body_capsules.py <file.yargchar> [--garment-match SUB] [--min-verts N]
                                [--percentile P] [--emit]

WHY THIS EXISTS, and it is a correction to three failed fixes in one afternoon. Jay, after the
third: *"We need the entirety of the character's body to deflect any of the cape that IS
attached to a spring bone."* He is right, and the measurement is blunt: **69.1% of Batman's body
skin is outside every one of his ten authored colliders.** His whole belt and waist are at 100%
uncovered, his chest 98.7%, his feet 93-100%, his hips 72%. The cape is not being deflected
because across two thirds of him there is nothing to deflect it off. No radius on the few
capsules that do exist can fix that; the body is simply not represented.

WHY THIS ONE IS NOT POSE-DEPENDENT, which is what killed the earlier attempts. The bundle's rest
pose is a T-POSE and the game poses the character, so anything measured against a GLOBAL axis or
against "whatever skin is nearest this joint" describes a pose the player never sees -- that is
how a fitted lower bound came to demand a capsule containing his arms. A capsule fitted to the
vertices a BONE OWNS, expressed in that bone's own local frame, has no such problem: the skin is
weighted to the bone and travels with it, so the fit is correct in every pose the animator can
produce. The T-pose is irrelevant here, and saying otherwise was over-correcting.

HOW IT FITS, per bone:

  * take the vertices whose largest skin weight is that bone -- its OWN skin, never "nearby"
    skin, which is the contamination that produced the arm-swallowing tubes;
  * move them into the bone's local frame;
  * principal axis by covariance, which handles a limb (long) and a pelvis (blobby) alike;
  * ends at the 2nd and 98th percentile along that axis, so one stray vertex cannot stretch it;
  * radius at `--percentile` (default 90) of the perpendicular distance. Not the max: a single
    spike would inflate the capsule, and this project has already had a min()-based gate refuse
    a verified fix over one vertex 6.7 mm from an axis end.

It prints the coverage the proposed set would reach, beside the coverage the file has now, which
is the only number that says whether it is worth writing. With `--emit` it prints a
`place_collider.py` command line per bone. It writes nothing itself.
"""
import math
import sys
from collections import defaultdict

import capsule_contains as cc
import cloth_collide_installed as cci


def eig3(M):
    """Largest-eigenvalue eigenvector of a symmetric 3x3, by power iteration.

    Good enough and dependency-free: the fit only needs the principal direction, and 200
    iterations on a 3x3 is exact to far more digits than a millimetre needs.
    """
    v = [1.0, 0.3, 0.7]
    for _ in range(200):
        w = [sum(M[i][j] * v[j] for j in range(3)) for i in range(3)]
        n = math.sqrt(sum(x * x for x in w))
        if n < 1e-18:
            return (0.0, 1.0, 0.0)
        v = [x / n for x in w]
    return tuple(v)


def fit_capsules(tf, world, skin, minv=40, pct=90.0, excl=()):
    """[(bone, r_local, A_local, B_local, ws, wp, wq)], one per bone with enough own skin.

    Everything is in the BONE'S OWN local frame, which is what makes the result pose-invariant
    and what `place_body_capsules.py` needs in order to write it.
    """
    byname = {}
    for pid, rec in tf.items():
        byname.setdefault(rec.get("name") or "", pid)
    owned = defaultdict(list)
    for bn, q in skin:
        owned[bn].append(q)

    out = []
    for bn in sorted(owned, key=lambda b: -len(owned[b])):
        pts = owned[bn]
        if len(pts) < minv or any(s in bn.lower() for s in excl):
            continue
        pid = byname.get(bn)
        if pid is None:
            continue
        wp, wq, ws = world(pid)
        iq = (wq[0], -wq[1], -wq[2], -wq[3])     # conjugate negates the LAST three

        def to_local(P, wp=wp, iq=iq, ws=ws):
            v = (P[0] - wp[0], P[1] - wp[1], P[2] - wp[2])
            r3 = cci.qrot(iq, v)
            return (r3[0] / ws[0], r3[1] / ws[1], r3[2] / ws[2])

        L = [to_local(P) for P in pts]
        cx = [sum(p[i] for p in L) / len(L) for i in range(3)]
        M = [[sum((p[i] - cx[i]) * (p[j] - cx[j]) for p in L) / len(L)
              for j in range(3)] for i in range(3)]
        ax = eig3(M)
        ts = sorted(sum((p[i] - cx[i]) * ax[i] for i in range(3)) for p in L)
        t0, t1 = ts[int(len(ts) * 0.02)], ts[int(len(ts) * 0.98)]
        A = tuple(cx[i] + ax[i] * t0 for i in range(3))
        B = tuple(cx[i] + ax[i] * t1 for i in range(3))
        ds = []
        for p in L:
            t = max(t0, min(t1, sum((p[i] - cx[i]) * ax[i] for i in range(3))))
            c = tuple(cx[i] + ax[i] * t for i in range(3))
            ds.append(math.sqrt(sum((p[i] - c[i]) ** 2 for i in range(3))))
        ds.sort()
        r = ds[min(len(ds) - 1, int(len(ds) * pct / 100.0))]
        if r <= 0.002:
            continue
        out.append((bn, r, A, B, ws, wp, wq))
    return out


def to_world(v, wp, wq, ws):
    sc = (v[0] * ws[0], v[1] * ws[1], v[2] * ws[2])
    r3 = cci.qrot(wq, sc)
    return (wp[0] + r3[0], wp[1] + r3[1], wp[2] + r3[2])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    gm = (sys.argv[sys.argv.index("--garment-match") + 1]
          if "--garment-match" in sys.argv else None)
    minv = int(sys.argv[sys.argv.index("--min-verts") + 1]) if "--min-verts" in sys.argv else 40
    pct = float(sys.argv[sys.argv.index("--percentile") + 1]) if "--percentile" in sys.argv else 90.0
    emit = "--emit" in sys.argv
    # A cape cannot be deflected by a tongue, and every collider is tested against every joint
    # of every chain each frame. So the set is pruned by PART, not by a vertex-count threshold:
    # a finger owns as much skin as a heel and matters to a garment not at all.
    excl = [s.strip().lower() for s in
            sys.argv[sys.argv.index("--exclude") + 1].split(",")] if "--exclude" in sys.argv else []

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    garment = cc.cloth_bones(tf, go_tf, springs, joints, gm)
    skin = cc.skin_vertices(path, tf, world, garment)
    shapes = cc.collider_shapes(tf, go_tf, colliders, world)
    if not skin:
        print("no skin decoded -- unmeasured, not clean.")
        return 1

    byname = {}
    for pid, rec in tf.items():
        byname.setdefault(rec.get("name") or "", pid)

    owned = defaultdict(list)
    for bn, q in skin:
        owned[bn].append(q)

    step = max(1, len(skin) // 12000)
    sample = skin[::step]

    def uncovered(shapeset):
        n = 0
        for _bn, q in sample:
            if not any(cc.seg_dist(q, a, b) < r for _nm, r, a, b, _c in shapeset):
                n += 1
        return n

    before = uncovered(list(shapes.values()))
    print("%d body skin vertices, %d sampled, %d existing collider(s)"
          % (len(skin), len(sample), len(shapes)))
    print("NOW: %d of %d sampled body vertices (%.1f%%) are outside every collider"
          % (before, len(sample), 100.0 * before / len(sample)))
    print()

    fitted = fit_capsules(tf, world, skin, minv, pct, excl)
    print("%-26s %6s %9s %9s %9s" % ("bone", "verts", "radius", "length", "already"))
    print("-" * 70)
    have = set(v[0] for v in shapes.values())
    for bn, r, A, B, _ws, _wp, _wq in fitted:
        print("%-26s %6d %6.1f mm %6.1f mm %9s"
              % (bn[:26], len(owned[bn]), r * 1000,
                 math.sqrt(sum((B[i] - A[i]) ** 2 for i in range(3))) * 1000,
                 "yes" if bn in have else ""))

    # what the proposed set would cover, in WORLD space so it is comparable with `before`
    proposed = [(bn, r * ws[0], to_world(A, wp, wq, ws), to_world(B, wp, wq, ws), 1)
                for bn, r, A, B, ws, wp, wq in fitted]
    after = uncovered(list(shapes.values()) + proposed)
    print()
    # A capsule fitted to a bone's own skin can still be a tube around several parts: the
    # principal axis of a shoulder-spanning bone runs ACROSS him, and a radius taken from that
    # bone's own spread then reaches well past it. So each one is scored the way the share gate
    # scores it -- what fraction of the WHOLE body it swallows -- and the fat ones are named.
    fat = [(bn, r, cc.contains(sample, a, b, r)[0]) for bn, r, a, b, _c in proposed]
    fat.sort(key=lambda t: -t[2])
    print()
    print("fattest proposed capsules, by share of ALL body skin they contain:")
    for bn, r, s in fat[:6]:
        print("    %-28s r=%6.1f mm  %5.1f%%" % (bn[:28], r * 1000, s * 100))
    print()
    print("%d capsule(s) proposed. Coverage of his body skin:" % len(proposed))
    print("    now        %5.1f%% outside every collider" % (100.0 * before / len(sample)))
    print("    with these %5.1f%% outside every collider" % (100.0 * after / len(sample)))

    # WHAT IS STILL EXPOSED, named. A coverage percentage says how much is left and nothing
    # about whether it matters: 14% spread over a face is fine, 14% on the hands is the thing
    # the cape was seen passing through.
    rest = defaultdict(int)
    tot = defaultdict(int)
    allshapes = list(shapes.values()) + proposed
    for bn, q in sample:
        tot[bn] += 1
        if not any(cc.seg_dist(q, a, b) < r for _nm, r, a, b, _c in allshapes):
            rest[bn] += 1
    if rest:
        print()
        print("    still exposed, by bone:")
        for bn, n in sorted(rest.items(), key=lambda kv: -kv[1])[:10]:
            print("      %-28s %4d of %4d  (%.0f%% of that bone)"
                  % (bn[:28], n, tot[bn], 100.0 * n / tot[bn]))
    if emit:
        print()
        for bn, r, A, B, ws, wp, wq in fitted:
            print("  --host %s --radius %.1f --offset %.9f,%.9f,%.9f --tail %.9f,%.9f,%.9f"
                  % (bn, r * 1000, A[0], A[1], A[2], B[0], B[1], B[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
