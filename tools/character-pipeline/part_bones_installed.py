# -*- coding: utf-8 -*-
"""What drives each mesh in an installed bundle, and where that mesh sits.

    python part_bones_installed.py <file.yargchar> [name-regex]

"A part is not centred on the body" has two very different causes and the
same appearance, so the first measurement has to tell them apart:

  * the part is its OWN rigid island riding one bone, and that bone is in the
    wrong place or is not the bone it should be on -- Joker's pistol, Judy's
    belt, Gadget Hackwrench's head;
  * the part shares a mesh with the body and its WEIGHTS are wrong, so it
    deforms away from where it was authored -- Jessica Rabbit's bodice.

For each skinned mesh this reports the bones that dominate it, how much of it
each one takes, and the world box and centroid of the skinned result. The
centroid's X against the driving bone's X is what says "off-centre", and the
SPREAD of dominant bones is what says which of the two causes it is: one bone
at 100% is a rigid island, nine bones is a skinned garment.

Everything is measured in the REST pose of the file that ships, which is the
only pose this can speak for. Nothing is written.
"""
import os
import re
import sys

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    want = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None

    human, tf, go_tf, springs, joints, colliders, groups, world = \
        cci.read(path)
    env = UnityPy.load(path)

    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    print("%s -- %d skinned mesh(es), %d bone transform(s)"
          % (os.path.basename(path), len(smrs), len(tf)))

    for r in smrs:
        mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        mname = mt.get("m_Name") or "?"
        if want is not None and not want.search(mname):
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
        if got is None or len(bind) != len(bones) or not bones:
            print("  %-26s COULD NOT DECODE (bones %d, bindposes %d)"
                  % (mname[:26], len(bones), len(bind)))
            continue
        V, W, I = got
        skin = [ps.mul(ps.trs(*world(b)), bind[i])
                for i, b in enumerate(bones)]

        # Dominant bone per vertex, and the skinned world position. The
        # skinned position is what the game draws; the raw V is in the mesh's
        # own space and says nothing about where the part ends up.
        cnt = {}
        # Centroid of the flesh each bone DOMINATES, against that bone's own
        # position. For a correctly bound mesh the two sit within the limb's
        # own thickness of each other; a part that is welded to a bone it was
        # not authored around shows up here as a lateral offset, which is the
        # measurement "the armour is not centred on his chest" actually needs.
        # A whole-mesh centroid cannot answer it -- it is dragged about by the
        # arms and legs, and Mando is authored asymmetric anyway (one
        # pauldron), so absolute symmetry is not evidence of anything.
        per = {}
        lo = [1e9] * 3
        hi = [-1e9] * 3
        sx = sy = sz = 0.0
        n = 0
        for vi in range(len(V)):
            best, bw, p = None, -1.0, None
            for k in range(len(W[vi])):
                w = W[vi][k]
                bi = I[vi][k]
                if w <= 0 or bi >= len(skin):
                    continue
                if w > bw:
                    bw, best = w, bi
                    p = ps.xform(skin[bi], V[vi])
            if best is None or p is None:
                continue
            # m_Bones holds TRANSFORM PPtrs, not GameObject ones -- which is
            # why patch_springs calls world(b) on them directly. Routing them
            # through go_tf returns None for every bone, every name collapses
            # to "?", and the mesh reads as having exactly ONE dominant bone:
            # the precise shape of the finding this probe exists to make.
            nm = tf.get(bones[best], {}).get("name") or "?"
            a = per.setdefault(nm, [0.0, 0.0, 0.0, 0])
            a[0] += p[0]
            a[1] += p[1]
            a[2] += p[2]
            a[3] += 1
            cnt[nm] = cnt.get(nm, 0) + 1
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
            sx += p[0]
            sy += p[1]
            sz += p[2]
            n += 1
        if not n:
            print("  %-26s %6d verts, NONE weighted" % (mname[:26], len(V)))
            continue
        top = sorted(cnt.items(), key=lambda kv: -kv[1])
        print("  %-26s %6d verts, %d bone(s) dominate; box x %+.3f..%+.3f "
              "y %+.3f..%+.3f z %+.3f..%+.3f"
              % (mname[:26], len(V), len(cnt), lo[0], hi[0], lo[1], hi[1],
                 lo[2], hi[2]))
        print("        centroid (%+.4f %+.4f %+.4f), x-centre of box %+.4f"
              % (sx / n, sy / n, sz / n, (lo[0] + hi[0]) / 2.0))
        for nm, c in top[:8]:
            a = per[nm]
            bp = world(next(b for b in bones
                            if (tf.get(b, {}).get("name") or "?") == nm))[0]
            fx, fy, fz = a[0] / a[3], a[1] / a[3], a[2] / a[3]
            print("        %-22s %6d (%5.1f%%)  bone (%+.4f %+.4f) its flesh "
                  "(%+.4f %+.4f)  offset x %+6.1f mm y %+6.1f mm"
                  % (nm[:22], c, 100.0 * c / n, bp[0], bp[1], fx, fy,
                     (fx - bp[0]) * 1000, (fy - bp[1]) * 1000))
        if len(top) > 8:
            print("        ... and %d more bone(s)" % (len(top) - 8))
    return 0


if __name__ == "__main__":
    sys.exit(main())
