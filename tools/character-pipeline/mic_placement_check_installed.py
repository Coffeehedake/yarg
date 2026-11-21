# -*- coding: utf-8 -*-
"""Where does the game actually put the microphone, and is that inside the hand?

    python mic_placement_check_installed.py <dir-of-yargchar>
    python mic_placement_check_installed.py <a.yargchar> [b.yargchar ...]

WHY THIS EXISTS. `hand_grip_check_installed.py` answers whether the AVATAR BINDS the finger
slots. It does not answer whether the bones behind those slots are anywhere sensible, and for
the characters this pipeline patches they are provably not.

`build_vrm.py` (the `VRM_FILL_FINGERS` block) SYNTHESISES missing finger chains, because YARG's
`AddMicrophoneToCharacter` dereferences six hand bones and a null one used to make the whole
character invisible. Those synthesised bones are deliberately **weightless** -- they deform
nothing -- and when the rig has no complete finger anywhere to copy from, they are laid out by
stepping along the FOREARM from the hand's head. Kronk and Judy Hopps are that case: every
finger bone either of them has is one of ours, and the real rig has none.

So the grip cannot close, which is a limitation of the model. But the mic's POSITION is a
separate question and a fixable one, because the game computes it from two of those bones:

    mic.transform.position = Vector3.Lerp(RightThumbDistal.position,
                                          RightIndexProximal.position, 0.25f)

If those two sit along the forearm, the mic is placed along the forearm. This tool computes
that exact point and measures it against the character's own HAND GEOMETRY.

WHAT IS REPORTED, and why each number is there rather than one verdict:

  * `d_hand`  distance from the mic point to the nearest vertex whose dominant bone is the
              right hand or one of its fingers. A mic in the palm reads near zero.
  * `%height` the same distance as a percentage of that character's own mesh height, because
              28 mm means something different on Yoda and on The Rock, and a bare millimetre
              figure across 65 characters of different scales is not a comparison
              ([[centroids-lie-across-topologies]]).
  * `synth`   whether the two bones the mic is interpolated between are ones `build_vrm.py`
              invented (name ends `_fused`). This is the suspected cause, kept in its own
              column so the correlation can be read rather than assumed.

READ IT AS A POPULATION. The 48 characters with a fully mapped real hand are the control group:
whatever `%height` they cluster at is what "the mic is in the hand" looks like for this roster,
and a character far outside that is the finding. If synthesised and real bones give the same
distribution then the fused placement is fine and the grip report is about something else.

Everything is the bundle's REST pose. The Animator re-poses the skeleton on `Rebind()`, and the
mic is placed after `animator.Update(0f)`, so these are not the in-game numbers -- they are a
like-for-like comparison across characters, which is what ranks them. Nothing is written.
"""
import os
import re
import sys

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

THUMB_DISTAL = "Right Thumb Distal"
INDEX_PROXIMAL = "Right Index Proximal"
RIGHT_HAND = "RightHand"
HANDISH = re.compile(r"hand|wrist|thumb|index|middle|ring|little|pinky|finger", re.I)


def avatar_map(path):
    """({humanoid slot: bone name}, {bone name: full hierarchy path}) from the Avatar.

    The second half is what makes this tool work on a rig with no readable bone names.
    Kronk's and Judy's bones are `n6`, `n7`, `n38` -- numbered, not named -- so ANY regex
    looking for "hand" or "thumb" finds nothing and reports a confident zero. `m_TOS` carries
    the full path of every transform, so the hand's descendants can be taken by STRUCTURE
    instead ([[verify-a-zero-with-a-control]]).
    """
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != "Avatar":
            continue
        tt = o.read_typetree()
        hd = tt.get("m_HumanDescription") or {}
        slots = dict((r.get("m_HumanName"), r.get("m_BoneName"))
                     for r in (hd.get("m_Human") or []))
        paths = {}
        for _h, p in (tt.get("m_TOS") or []):
            paths.setdefault(p.split("/")[-1], p)
        return slots, paths
    return None, None


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def measure(path):
    m, tos = avatar_map(path)
    if m is None:
        return {"err": "no Avatar"}
    for slot in (THUMB_DISTAL, INDEX_PROXIMAL):
        if slot not in m:
            return {"err": "no %s -- the mic is never placed (and pre-0d3d4e4f the "
                           "character is invisible)" % slot}

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)

    # tf maps path_id -> {"name": ...}. Find the transform behind each bone NAME.
    by_name = {}
    for pid, rec in tf.items():
        by_name.setdefault(rec.get("name"), pid)

    pids = {}
    for slot in (THUMB_DISTAL, INDEX_PROXIMAL, RIGHT_HAND):
        bone = m.get(slot)
        if bone is None or bone not in by_name:
            return {"err": "slot %r maps to bone %r, which is not a transform in the bundle"
                           % (slot, bone)}
        pids[slot] = by_name[bone]

    def pos(slot):
        """World position of a bone: its own transform applied to its origin."""
        return ps.xform(ps.trs(*world(pids[slot])), (0.0, 0.0, 0.0))

    p_thumb = pos(THUMB_DISTAL)
    p_index = pos(INDEX_PROXIMAL)
    mic = lerp(p_thumb, p_index, 0.25)

    # Skin every mesh the way the game does and keep the hand-side vertices.
    env = UnityPy.load(path)
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    # "The right hand" is the hand bone plus everything parented under it, taken from the
    # hierarchy rather than from bone names -- see avatar_map. A rig whose bones are numbered
    # has no name to match and would otherwise read as a hand with no geometry.
    hand_path = tos.get(m[RIGHT_HAND])
    if not hand_path:
        return {"err": "the right hand bone %r has no path in m_TOS" % m[RIGHT_HAND]}
    hand_names = set(leaf for leaf, p in tos.items()
                     if p == hand_path or p.startswith(hand_path + "/"))

    hand_pts, all_y = [], []
    for r in smrs:
        mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(x) for x in (mt.get("m_BindPose") or [])]
        if got is None or not bones or len(bind) != len(bones):
            continue
        V, W, I = got
        # m_Bones holds TRANSFORM PPtrs, never GameObject ones.
        skin = [ps.mul(ps.trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
        for vi in range(len(V)):
            best, bw = None, -1.0
            for k in range(len(W[vi])):
                w, bi = W[vi][k], I[vi][k]
                if w > bw and w > 0 and bi < len(skin):
                    bw, best = w, bi
            if best is None:
                continue
            p = ps.xform(skin[best], V[vi])
            all_y.append(p[1])
            nm = tf.get(bones[best], {}).get("name") or ""
            if nm in hand_names:
                hand_pts.append(p)

    if not all_y:
        return {"err": "no skinned geometry decoded"}
    height = max(all_y) - min(all_y)
    if not hand_pts:
        return {"err": "no right-hand geometry found (every vertex' dominant bone is "
                       "elsewhere) -- unmeasured, NOT good"}

    d = min(sum((mic[i] - p[i]) ** 2 for i in range(3)) ** 0.5 for p in hand_pts)
    synth = sum(1 for slot in (THUMB_DISTAL, INDEX_PROXIMAL)
                if str(m.get(slot, "")).endswith("_fused"))
    return {"d": d, "height": height, "pct": (d / height * 100.0) if height else None,
            "synth": synth, "nhand": len(hand_pts)}


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            paths.append(a)

    rows, errs = [], []
    for p in paths:
        name = os.path.basename(p)[:-9]
        try:
            r = measure(p)
        except Exception as exc:                                    # noqa: BLE001
            errs.append((name, "%s: %s" % (type(exc).__name__, exc)))
            continue
        if "err" in r:
            errs.append((name, r["err"]))
            continue
        rows.append((name, r))

    rows.sort(key=lambda t: -t[1]["pct"])
    print("%-28s %10s %9s %7s %7s" % ("character", "d_hand(mm)", "%height", "synth", "verts"))
    print("-" * 70)
    for name, r in rows:
        print("%-28s %10.1f %8.2f%% %5d/2 %7d"
              % (name[:28], r["d"] * 1000.0, r["pct"], r["synth"], r["nhand"]))

    real = [r["pct"] for _, r in rows if r["synth"] == 0]
    fake = [r["pct"] for _, r in rows if r["synth"] > 0]
    print()
    if real:
        real.sort()
        print("CONTROL (%d characters whose two mic bones are REAL): median %.2f%%, "
              "worst %.2f%%" % (len(real), real[len(real) // 2], real[-1]))
    if fake:
        fake.sort()
        print("SYNTHESISED (%d whose mic bones this pipeline invented): median %.2f%%, "
              "worst %.2f%%" % (len(fake), fake[len(fake) // 2], fake[-1]))
    if real and fake:
        print()
        print("If those two medians are close, the fused placement is NOT the problem and the")
        print("grip report is about the hand not closing, which no placement change fixes.")
    if errs:
        print()
        for name, why in errs:
            print("UNMEASURED  %-26s %s" % (name[:26], why))
    return 0


if __name__ == "__main__":
    sys.exit(main())
