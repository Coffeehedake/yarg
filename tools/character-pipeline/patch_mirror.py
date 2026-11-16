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
import mirror_check_installed as mc
from patch_springs import fingerprint

EPS = 1e-6


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

    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(src)
    rows = mc.pairs_of(human, tf)
    applies, bad = mc.verdict(rows)
    if not applies:
        print("ABORT: this rig's limb offsets are not mirrored even "
              "approximately (%d of %d pair(s) over %.0f mm), so negating X "
              "is not its mirror and there is nothing safe to copy"
              % (len([r for r in rows if r[0] > mc.TOL]), len(rows),
                 mc.TOL * 1000))
        return 2
    hit = [r for r in bad if bone in (r[1], r[2])]
    if not hit:
        print("ABORT: %r is not a displaced limb bone in this bundle. "
              "Displaced: %s"
              % (bone, ", ".join("%s/%s" % (r[1], r[2]) for r in bad)
                 or "none -- every limb pair mirrors"))
        return 2
    if len(bad) > 1:
        print("NOTE: %d limb pair(s) are displaced here, and only %r is being "
              "moved: %s" % (len(bad), bone,
                             ", ".join("%s/%s %.1f mm" % (r[1], r[2],
                                                          r[0] * 1000)
                                       for r in bad)))
    total, left, right, _d, slot = hit[0]
    # The partner is whichever of the pair is NOT the bone being moved, and
    # the bone being moved takes the MIRROR of the partner's offset.
    partner = right if bone == left else left
    by_name = {}
    for pid, n in tf.items():
        if n["name"]:
            by_name.setdefault(n["name"], pid)
    ref = tf[by_name[partner]]["p"]
    want = (-ref[0], ref[1], ref[2])
    have = tf[by_name[bone]]["p"]
    print("%s: the %s pair -- %r is %.2f mm off the mirror of %r"
          % (os.path.basename(src), slot, bone, total * 1000, partner))
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
    with open(out, "wb") as f:
        f.write(data)
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
