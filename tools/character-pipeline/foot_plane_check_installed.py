# -*- coding: utf-8 -*-
"""Does a character's SHOE actually hang below the floor? Measured on geometry, not bones.

    python foot_plane_check_installed.py <file.yargchar> [more.yargchar ...]

WHY THIS EXISTS. This project recorded that Jessica Rabbit's "left shoe hangs 67 mm below her
own hem and 92 mm below the plane her right foot stands on", and re-opened a closed decision on
the strength of it. But the number behind that sentence came from `YargFootProbe`, which reports
**UPPER-LEG bone** heights under the label "foot height difference" -- and a bone is not a shoe.
Measured in a build of her on 2026-11-20, her thigh ROOTS differ by 92.38 mm while her FOOT
BONES differ by 0.82 mm, so the two readings disagree by two orders of magnitude and only one of
them is about the thing anyone can see.

So this reads the VERTICES. For each side it takes the geometry whose dominant bone is that
side's foot or toe, skins it the way the game does, and reports how low it actually goes.

  * `min Y` is the single lowest vertex, which is what "the shoe is through the floor" means.
  * `p1 Y` is the 1st percentile beside it, because one stray vertex is not a shoe and a
    minimum is the statistic most easily made by an outlier.
  * the HEM is the lowest geometry that is NOT foot or toe -- a dress, a coat, a cape. The
    "67 mm below her own hem" claim is a comparison between those two.

CONTROLS. Pass a character known to stand level -- Spartan Mark V reads 0.0 on every left/right
pair in `pair_offset_check_installed.py` and is this project's standing control. A left/right
difference means something only beside a character where it comes out zero, and an asymmetry
that appears on EVERY character is this tool's own bug.

Everything is in the REST pose of the shipped file, which is the only pose a bundle can speak
for. The Animator re-poses every leg bone by 2 to 45 mm on `Rebind()`, on a correct character as
much as a broken one, so a figure from here is not the last word on what the game draws --
`YargFootProbe` is, and it must be read with its own label corrected. Nothing is written.
"""
import os
import re
import sys

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

LEFT = re.compile(r"(^|[._\- ])(l|left)([._\- ]|$)|left", re.I)
RIGHT = re.compile(r"(^|[._\- ])(r|right)([._\- ]|$)|right", re.I)
FOOT = re.compile(r"foot|toe|ankle|ball", re.I)


def side_of(name):
    """L or R from a bone name, tolerating mixamo prefixes and glTF numeric suffixes."""
    n = re.sub(r"_\d+$", "", name or "")
    if RIGHT.search(n):
        return "R"
    if LEFT.search(n):
        return "L"
    return None


def pct(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, int(len(s) * q)))]


def measure(path):
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    env = UnityPy.load(path)
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    ys = {"L": [], "R": []}      # foot/toe geometry, per side
    other = []                   # everything else -- the hem lives in here
    decoded = 0
    for r in smrs:
        mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
        if got is None or not bones or len(bind) != len(bones):
            continue
        decoded += 1
        V, W, I = got
        # m_Bones holds TRANSFORM PPtrs, never GameObject ones. Route them through a
        # GameObject table and every name comes back "?", every mesh reads as one dominant
        # bone, and this tool reports a tidy nothing.
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
            nm = tf.get(bones[best], {}).get("name") or "?"
            if FOOT.search(nm):
                s = side_of(nm)
                if s:
                    ys[s].append(p[1])
                    continue
            other.append(p[1])
    return decoded, ys, other


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    print("%-26s %9s %9s %9s %9s %10s %10s"
          % ("character", "L min", "L p1", "R min", "R p1", "L-R min", "hem min"))
    rows = []
    for path in sys.argv[1:]:
        if not os.path.isfile(path):
            print("%-26s MISSING %s" % (os.path.basename(path)[:26], path))
            continue
        try:
            decoded, ys, other = measure(path)
        except Exception as exc:                                   # noqa: BLE001
            print("%-26s UNREADABLE: %s: %s"
                  % (os.path.basename(path)[:26], type(exc).__name__, exc))
            continue
        name = os.path.basename(path)[:-9]
        if not ys["L"] or not ys["R"]:
            print("%-26s NO FOOT GEOMETRY per side (L %d, R %d verts over %d mesh(es)) -- "
                  "unmeasured, NOT level"
                  % (name[:26], len(ys["L"]), len(ys["R"]), decoded))
            continue
        lmin, rmin = min(ys["L"]), min(ys["R"])
        lp1, rp1 = pct(ys["L"], 0.01), pct(ys["R"], 0.01)
        hem = min(other) if other else None
        print("%-26s %9.4f %9.4f %9.4f %9.4f %9.1fmm %9s"
              % (name[:26], lmin, lp1, rmin, rp1, (lmin - rmin) * 1000.0,
                 "%.4f" % hem if hem is not None else "-"))
        rows.append((name, lmin, rmin, hem, len(ys["L"]), len(ys["R"])))

    print()
    for name, lmin, rmin, hem, nl, nr in rows:
        print("%s: %d left-foot verts, %d right-foot verts" % (name, nl, nr))
        print("   lower shoe sits %+.1f mm against the other foot" % ((lmin - rmin) * 1000.0))
        if hem is not None:
            print("   lowest foot vertex is %+.1f mm against the lowest NON-foot geometry "
                  "(the hem); negative means the shoe is below it"
                  % ((min(lmin, rmin) - hem) * 1000.0))
    print()
    print("A number here means something only beside a character that reads ~0. Nothing is")
    print("written, and this is the bundle's REST pose -- the Animator moves every leg bone on")
    print("Rebind, on a correct character as much as a broken one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
