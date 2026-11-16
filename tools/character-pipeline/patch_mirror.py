# -*- coding: utf-8 -*-
"""Move a DISPLACED bone back onto its mirror, in an installed .yargchar.

    python patch_mirror.py <in.yargchar> <bone> [--out X] [--dry-run]

For a limb that is in the wrong PLACE rather than the wrong shape. Spartan
Mark V, reported 2026-11-15 as an asymmetric right leg: his `thigh.R` sits
92.12 mm from the mirror of his `thigh.L`, and every other one of his 29
mirrored pairs matches to 0.00 mm -- rotations to six decimals, and `shin`,
`foot`, `toe` and `heel` to 0.000 mm. His whole right leg hangs off that one
bad offset, 30 mm clear of a hip socket his left leg sits 5 mm inside.

FOUR structures hold that offset, all parent-relative and all in the same
representation, and a patch that misses one leaves the file disagreeing with
itself:

    Transform.m_LocalPosition
    Avatar.m_Avatar.m_AvatarSkeletonPose.data.m_X[i].t
    Avatar.m_Avatar.m_DefaultPose.data.m_X[i].t
    Avatar.m_HumanDescription.m_Skeleton[j].m_Position

The Avatar arrays are nested under a "data" key. Reading them one level too
shallow returns empty lists rather than an error, which reads as "the Avatar
carries no skeleton, so the Transform is the only place" -- it does carry one,
in triplicate, and Unity retargets humanoid animation through it.

NOTHING ELSE IS TOUCHED. The bone's children keep their own offsets and the
mesh keeps its bind pose, so the limb travels rigidly and its geometry is
untouched: measured in each thigh's own frame, his two legs are already
identical to 0.0 mm, which is what says the leg is intact and merely misplaced.

THE CHARACTER IS ITS OWN CONTROL. This refuses to run unless the named bone is
the sole outlier in a rig that otherwise mirrors -- see
mirror_check_installed.py, whose verdict() this calls rather than reimplements.
On a rig whose parent frames are not mirrored, negating X is not that rig's
mirror and this would move a correct bone to a wrong place with great
confidence.

Verification is a full read-back: every object's state is fingerprinted before
and after, and anything differing that was not named is a reason NOT to install
the result.
"""
import os
import sys

import UnityPy

import cloth_collide_installed as cci
import limb_socket_check_installed as sock
from patch_springs import fingerprint

EPS = 1e-6


def sockets(src):
    """{slot: (left bone, right bone, left gap m, right gap m)}.

    The same measurement limb_socket_check_installed.py makes, called here so
    that this tool's guard rests on the JOIN rather than on mirror arithmetic.
    It used to call mirror_check_installed.verdict(), and that was withdrawn:
    negating X in a parent's frame is the mirror only when the parent's axes
    happen to be aligned with the body's left-right line, which is the rig's
    own convention and cannot be read back out of the file.
    """
    human, tf, per, _skipped = sock.flesh(src)
    by_name = {}
    for pid, n in tf.items():
        if n["name"]:
            by_name.setdefault(n["name"], pid)
    tor = []
    for k in sock.TORSO:
        bn = cci.hname(human, k)
        if bn and bn in by_name:
            tor += per.get(by_name[bn]) or []
    if len(tor) < 64:
        return {}, tf, by_name, human
    tor = tor[::max(1, len(tor) // sock.TORSO_SAMPLE)]
    out = {}
    for slot, lk, rk in sock.JOINS:
        ln, rn = cci.hname(human, lk), cci.hname(human, rk)
        if not ln or not rn or ln not in by_name or rn not in by_name:
            continue
        g = []
        for nm in (ln, rn):
            ps = [p for b in sock.region(tf, by_name, human, nm)
                  for p in (per.get(b) or [])]
            if len(ps) < 16:
                g.append(None)
                continue
            top = sorted(ps, key=lambda p: -p[1])[:max(8, len(ps) // 5)]
            g.append(sock.nearest(top, tor)[0])
        out[slot] = (ln, rn, g[0], g[1])
    return out, tf, by_name, human


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    out = None
    if "--out" in args:
        out = args[args.index("--out") + 1]
    rest = [a for a in args if not a.startswith("--") and a != out]
    if len(rest) != 2:
        print(__doc__)
        return 2
    src, bone = rest
    out = out or src

    gaps, tf, by_name, human = sockets(src)
    hit = None
    for slot, (ln, rn, gl, gr) in sorted(gaps.items()):
        if bone not in (ln, rn):
            continue
        if gl is None or gr is None:
            print("ABORT: the %s pair carries too little flesh to measure a "
                  "join, so there is no evidence %r is out of place" % (slot,
                                                                        bone))
            return 2
        mine, theirs = (gl, gr) if bone == ln else (gr, gl)
        print("%s: the %s join -- %r sits %.1f mm from the torso, its partner "
              "%r sits %.1f mm" % (os.path.basename(src), slot, bone,
                                   mine * 1000,
                                   rn if bone == ln else ln, theirs * 1000))
        if not ((mine - theirs) * 1000 >= sock.GAP_MM
                and mine >= sock.GAP_RATIO * max(theirs, 1e-5)):
            print("ABORT: that is not a limb out of its socket -- it needs to "
                  "be at least %.0f mm and %.1fx further out than its partner."
                  " Moving a bone that is already attached would detach it."
                  % (sock.GAP_MM, sock.GAP_RATIO))
            return 2
        hit = (slot, ln, rn, gl, gr)
        break
    if hit is None:
        print("ABORT: %r is not one of the limb bones that join the torso "
              "(%s), so this tool has no evidence to act on"
              % (bone, ", ".join(sorted(
                  n for _s, (a, b, _x, _y) in gaps.items() for n in (a, b)))))
        return 2
    slot, left, right, gl, gr = hit
    # The partner is whichever of the pair is NOT the bone being moved, and
    # the bone being moved takes the MIRROR of the partner's offset.
    #
    # THAT NAIVE MIRROR IS AN ASSUMPTION, and the file cannot confirm it:
    # negating X of a local offset is the true mirror only when the shared
    # parent's own axes put X along the body's left-right line. So it is not
    # trusted -- the join is MEASURED AGAIN on the patched bytes below, and if
    # the gap has not closed to its partner's figure nothing is written.
    partner = right if bone == left else left
    ref = tf[by_name[partner]]["p"]
    want = (-ref[0], ref[1], ref[2])
    have = tf[by_name[bone]]["p"]
    print("  moving %r onto the mirror of %r" % (bone, partner))
    print("  have (%+.6f %+.6f %+.6f)" % have)
    print("  want (%+.6f %+.6f %+.6f)   = mirror of %s (%+.6f %+.6f %+.6f)"
          % (want + (partner,) + ref))
    pa = tf.get(tf[by_name[bone]]["f"], {}).get("name")
    pb = tf.get(tf[by_name[partner]]["f"], {}).get("name")
    print("  parents: %s under %r, %s under %r" % (bone, pa, partner, pb))

    env = UnityPy.load(src)
    before = fingerprint(env)
    done = []

    for obj in env.objects:
        if obj.type.name == "Transform":
            # cci.read() keys its transform table by Transform path_id, so
            # the bone's name comes straight out of it.
            if (tf.get(obj.path_id) or {}).get("name") != bone:
                continue
            tt = obj.read_typetree()
            lp = tt["m_LocalPosition"]
            if all(abs(lp[k] - want[i]) < EPS
                   for i, k in enumerate("xyz")):
                print("  Transform already at the target")
            else:
                lp["x"], lp["y"], lp["z"] = want
                tt["m_LocalPosition"] = lp
                obj.save_typetree(tt)
                done.append("Transform.m_LocalPosition")
        elif obj.type.name == "Avatar":
            tt = obj.read_typetree()
            av = tt["m_Avatar"]
            names = {}
            for e in (tt.get("m_TOS") or []):
                if isinstance(e, (list, tuple)) and len(e) == 2:
                    names[e[0]] = e[1]
            ids = av["m_AvatarSkeleton"]["data"]["m_ID"]
            short = [(names.get(b) or "?").split("/")[-1] for b in ids]
            if bone not in short:
                print("  the Avatar's skeleton does not list %r -- NOT "
                      "touched" % bone)
                continue
            i = short.index(bone)
            touched = False
            for key in ("m_AvatarSkeletonPose", "m_DefaultPose"):
                arr = av[key]["data"]["m_X"]
                if i >= len(arr):
                    print("  %s has only %d entries, no [%d] -- NOT touched"
                          % (key, len(arr), i))
                    continue
                t = arr[i]["t"]
                if all(abs(t[k] - want[j]) < EPS
                       for j, k in enumerate("xyz")):
                    continue
                t["x"], t["y"], t["z"] = want
                touched = True
                done.append("%s[%d].t" % (key, i))
            for e in tt["m_HumanDescription"]["m_Skeleton"]:
                if (e.get("m_Name") or "") != bone:
                    continue
                p = e["m_Position"]
                if all(abs(p[k] - want[j]) < EPS
                       for j, k in enumerate("xyz")):
                    continue
                p["x"], p["y"], p["z"] = want
                touched = True
                done.append("m_HumanDescription.m_Skeleton.m_Position")
            if touched:
                obj.save_typetree(tt)

    if not done:
        print("nothing to do")
        return 2
    print("  changed: %s" % ", ".join(done))
    if dry:
        print("  --dry-run: nothing written")
        return 0

    # Verified from the bytes in memory before anything is written, as in
    # patch_springs.py: UnityPy holds a loaded file's handle open, so a
    # temp-file round trip cannot be renamed over the original on Windows.
    data = env.file.save(packer="original")
    after = fingerprint(UnityPy.load(data))
    changed = [k for k in before if before.get(k) != after.get(k)]
    gone = [k for k in before if k not in after]
    added = [k for k in after if k not in before]
    # One Transform and one Avatar, whatever the number of fields inside them.
    expect = 2
    print("  read-back: %d object(s) readable, %d changed (expected %d), "
          "%d gone, %d added" % (len(after), len(changed), expect, len(gone),
                                 len(added)))
    for k in sorted(changed):
        print("    %s" % k)
    if len(changed) != expect or gone or added:
        print("  WARNING: the read-back does not match what was asked for -- "
              "nothing was written")
        return 1

    # DID THE LIMB ACTUALLY LAND IN ITS SOCKET? The naive mirror is an
    # assumption about the parent's axes, so it is not taken on trust: the join
    # is measured again on the patched bytes, and the gap has to have come down
    # to its partner's. On Spartan Mark V it goes 29.7 -> 4.6 against a left
    # leg at 4.7. Without this the tool would write a confident wrong answer on
    # any rig whose parent is rolled, which is the defect that withdrew
    # mirror_check_installed.py.
    after_gaps, _tf2, _bn2, _h2 = sockets(data)
    g = after_gaps.get(slot)
    if not g or g[2] is None or g[3] is None:
        print("  WARNING: the join cannot be re-measured on the result, so "
              "there is no proof it closed -- nothing was written")
        return 1
    mine = g[2] if bone == g[0] else g[3]
    theirs = g[3] if bone == g[0] else g[2]
    print("  the %s join after the move: %r %.1f mm, %r %.1f mm "
          "(was %.1f / %.1f)"
          % (slot, bone, mine * 1000, partner, theirs * 1000,
             (gl if bone == left else gr) * 1000,
             (gr if bone == left else gl) * 1000))
    if (mine - theirs) * 1000 >= sock.GAP_MM:
        print("  WARNING: it is still %.1f mm further out than its partner, so "
              "the mirror of the local offset is NOT this rig's mirror -- "
              "nothing was written" % ((mine - theirs) * 1000))
        return 1
    with open(out, "wb") as f:
        f.write(data)
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
