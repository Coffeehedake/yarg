# -*- coding: utf-8 -*-
"""WHAT does a spring collider actually contain? Named by skin bone, counted.

    python capsule_contains.py <file.yargchar> [--garment-match SUBSTRING]

WHY THIS EXISTS. Jay looked at Batman after three fitted capsules went in: "It's clipping
through batman's arms now." The cape was splayed sideways through both forearms. The three
capsules I had placed were 145, 216 and 232 mm wide and ran from ankle height to his chest, and
between them they held a quarter to nearly half of his entire skin. They were not torso
capsules. They were tubes containing his arms, and a cape kept outside one is a cape held out
past his arms.

Every fit tool here reasons in DISTANCES -- a lower bound from the skin near each joint, an
upper bound from where the joints already are. Both were satisfied at 232 mm. Neither can see
what the resulting VOLUME swallows, because neither ever asks. That is what this asks.

THE DEFECT IT NAMES. The lower bound is "do not hold the cloth nearer the axis than the body
surface is", measured as the median axis distance of the skin NEAR each joint. For a cape joint
at shoulder height the nearest skin is the ARM, 200+ mm from a central vertical axis, so the
rule silently became "do not hold the cape nearer the axis than his arms are". The fitter obeyed
it exactly. "Skin" is not a body part -- the third time that has cost a wrong answer in one day.

THE STANDARD IS THE CHARACTER'S OWN AUTHORING, not a number I would have to invent. Every one of
these characters ships a Body collider group whose author knew which part each capsule stood
for. On Batman the fattest authored collider holds 10.8% of his skin; mine held 41.8%. On Miku
the fattest authored one holds 28.1% and the fitted tie capsule holds 10.6% -- head, spine and
spine1, no limb at all. So `share_gate` refuses a fitted capsule that swallows more skin than
anything the character's own author drew, which fires on all three of Batman's and passes
Miku's. `place_collider.py` calls it; `test_share_gate.py` shows it failing before it is
trusted.

Nothing here writes.
"""
import math
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


def cloth_bones(tf, go_tf, springs, joints, match=None):
    """Every bone a spring chain drives, plus anything whose name carries `match`.

    The second half is not optional padding: Batman's cape is 157 `*cape*` bones and his eleven
    chains own only a handful of them, so a set built from chain membership alone leaves most of
    the garment in "skin" -- which is how a 4% rest penetration was once reported as 63.5%.
    """
    out = set()
    for _nm, jps, _g in springs:
        for jp in jps:
            rec = joints.get(jp)
            tp = go_tf.get(rec[0]) if rec else None
            if tp is not None:
                out.add(tf.get(tp, {}).get("name") or "?")
    if match:
        for _pid, rec in tf.items():
            nm = rec.get("name") or ""
            if match.lower() in nm.lower():
                out.add(nm)
    return out


def skin_vertices(path, tf, world, exclude, env=None):
    """Every skinned vertex in world space, tagged with the bone that weights it most."""
    env = env or UnityPy.load(path)
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
            for k in range(len(W[vi])):
                wgt, bi = W[vi][k], I[vi][k]
                if wgt > bw and wgt > 0 and bi < len(mats):
                    bw, best = wgt, bi
            if best is None:
                continue
            bn = tf.get(bones[best], {}).get("name") or "?"
            if bn in exclude:
                continue
            skin.append((bn, ps.xform(mats[best], V[vi])))
    return skin


def collider_shapes(tf, go_tf, colliders, world):
    """Every collider in the file as (host bone, world radius, world A, world B, type)."""
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
        b = to_world(t.get("Tail") or {}) if int(t.get("ColliderType", 0)) == 1 else a
        shapes[cp] = (tf.get(tp, {}).get("name") or "?",
                      float(t.get("Radius", 0.0)) * ws[0], a, b,
                      int(t.get("ColliderType", 0)))
    return shapes


def contains(skin, a, b, r):
    """(share of `skin` inside the capsule, Counter of bone -> count inside)."""
    inside = Counter()
    for bn, q in skin:
        if seg_dist(q, a, b) < r:
            inside[bn] += 1
    n = sum(inside.values())
    return (0.0 if not skin else float(n) / len(skin)), inside


def share_gate(skin, shapes, a, b, r, allow=0.0):
    """Refuse a capsule that swallows more skin than the character's own fattest collider.

    Returns (ok, message). `allow` is an EXTRA fraction the caller is willing to state out loud,
    so the gate can be overridden deliberately rather than deleted.
    """
    mine, inside = contains(skin, a, b, r)
    best, best_bone = 0.0, None
    for _cp, (bn, cr, ca, cb, _ct) in shapes.items():
        s, _ = contains(skin, ca, cb, cr)
        if s > best:
            best, best_bone = s, bn
    if best_bone is None:
        return True, ("this file has no existing collider to compare against, so the share gate "
                      "stood down; the new capsule holds %.1f%% of the skin." % (mine * 100))
    if mine <= best + allow:
        return True, ("holds %.1f%% of the skin, against %.1f%% for the fattest collider this "
                      "character already ships (%s)." % (mine * 100, best * 100, best_bone))
    return False, (
        "this capsule holds %.1f%% of the skin -- MORE than the %.1f%% of the fattest collider "
        "the character's own author drew (%s), and --allow-contain permits %.1f%% more. It is "
        "not a capsule around a body part, it is a tube around several. The skin inside it is: "
        "%s. This is what put a cape around Batman's arms on 2026-11-21: the fit's lower bound "
        "came from whatever skin was NEAREST each joint, and at shoulder height that is the arm."
        % (mine * 100, best * 100, best_bone, allow * 100,
           ", ".join("%s x%d" % (k, v) for k, v in inside.most_common(6)) or "none"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    gm = (sys.argv[sys.argv.index("--garment-match") + 1]
          if "--garment-match" in sys.argv else None)

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    garment = cloth_bones(tf, go_tf, springs, joints, gm)
    skin = skin_vertices(path, tf, world, garment)
    shapes = collider_shapes(tf, go_tf, colliders, world)
    if not skin:
        print("NO skin decoded -- unmeasured, not clean.")
        return 1

    step = max(1, len(skin) // 12000)
    sk = skin[::step]
    print("%d collider(s), %d skin vertices (%d garment bone(s) excluded), %d sampled"
          % (len(shapes), len(skin), len(garment), len(sk)))
    print()
    for _cp, (bn, cr, a, b, ct) in sorted(shapes.items(), key=lambda kv: -kv[1][1]):
        share, inside = contains(sk, a, b, cr)
        print("%-24s r=%6.1f mm  %s  y %.3f-%.3f"
              % (bn[:24], cr * 1000, "capsule" if ct == 1 else "sphere ", a[1], b[1]))
        print("    %5d of %d sampled skin vertices inside (%.1f%%)"
              % (sum(inside.values()), len(sk), share * 100))
        print("    %s"
              % (", ".join("%s x%d" % (k, v) for k, v in inside.most_common(6)) or "none"))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
