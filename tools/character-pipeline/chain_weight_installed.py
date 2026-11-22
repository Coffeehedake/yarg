# -*- coding: utf-8 -*-
"""How much skin weight does each spring chain actually carry? Measured, per chain.

    python chain_weight_installed.py <file.yargchar> [<name-regex>]

WHY THIS EXISTS. A spring chain that no vertex is weighted to still costs the solver its full
per-frame work and still appears in every listing, so a roster of chains tells you nothing
about which ones MOVE anything. Dropping a chain is only safe if its bones own no geometry,
and "owns no geometry" is a measurement, not a property of the name.

WHAT IT MEASURES, and the distinction matters. For every bone named by a chain's joints:

  * `sum w`   the total of every weight on that bone, over every skinned mesh. This is the
              honest quantity -- a bone with 0.05 of a vertex is not weightless.
  * `dom v`   vertices where that bone is the DOMINANT influence. A chain can have weight
              and dominate nothing, which means it only ever modulates another bone's pull.

A chain is a drop candidate when `sum w` is 0.0 across every mesh. `dom v` is reported beside
it because the two disagree, and a tool that printed only the second would call a chain dead
while a quarter of a cape partly hung from it.

THE CONTROL IS NOT OPTIONAL AND THIS TOOL REFUSES WITHOUT IT. A zero from a loop that never
ran looks exactly like a zero from a weightless bone, and this project has shipped three such
zeros in one afternoon. So the summary prints:

  * `meshes walked` and `vertices read` -- nonzero, or the measurement did not happen;
  * `bones matched` against `bones named` -- the join between the spring chains (which name
    GameObjects) and the skin (which names TRANSFORMS) is the exact place a silent zero comes
    from, and an unmatched bone is reported as UNMATCHED rather than as 0.0;
  * the LIVE chains beside the dead ones, every time, so a zero has a non-zero next to it.

It REFUSES to call anything a drop candidate if no chain on the character carries weight --
that is an instrument fault, not a roster of dead chains.
"""
import os
import re
import sys

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy


def bone_weights(env):
    """Total weight and dominant-vertex count per bone TRANSFORM path_id.

    Returns (wsum, wdom, meshes_walked, vertices_read). The last two are the control: a caller
    that does not check them cannot tell a weightless bone from a loop that never ran.
    """
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    # bone TRANSFORM path_id -> (sum of weights, dominant vertex count)
    wsum, wdom = {}, {}
    walked = verts = 0
    for r in smrs:
        mt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        if got is None or not bones:
            continue
        V, W, I = got
        walked += 1
        verts += len(V)
        for vi in range(len(V)):
            best, bw = None, -1.0
            for k in range(len(W[vi])):
                w = W[vi][k]
                bi = I[vi][k]
                if w <= 0 or bi >= len(bones):
                    continue
                b = bones[bi]
                wsum[b] = wsum.get(b, 0.0) + w
                if w > bw:
                    bw, best = w, b
            if best is not None:
                wdom[best] = wdom.get(best, 0) + 1
    return wsum, wdom, walked, verts


def per_chain(springs, joints, go_tf, gname, wsum, wdom):
    """One row per chain: (name, joints, sum w, dom v, unmatched, per-bone strings).

    `unmatched` is the GameObject->Transform join failing, and it is NOT the same as a zero:
    a chain with unmatched bones is never a drop candidate, because nothing was measured.
    """
    rows, named, matched = [], 0, 0
    for name, jps, _cgs in springs:
        tot, dom, bones_out, unmatched = 0.0, 0, [], 0
        for jp in jps:
            rec = joints.get(jp)
            if rec is None:
                continue
            gid = rec[0]
            tid = go_tf.get(gid)
            named += 1
            bn = gname.get(gid, "?")
            if tid is None:
                unmatched += 1
                bones_out.append("%s(UNMATCHED)" % bn)
                continue
            matched += 1
            s = wsum.get(tid, 0.0)
            d = wdom.get(tid, 0)
            tot += s
            dom += d
            bones_out.append("%s %.1f/%d" % (bn, s, d))
        rows.append((name, len(jps), tot, dom, unmatched, bones_out))
    return rows, named, matched


def gameobject_names(env):
    out = {}
    for o in env.objects:
        if o.type.name == "GameObject":
            out[o.path_id] = o.read_typetree().get("m_Name", "?")
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    want = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    env = UnityPy.load(path)
    gname = gameobject_names(env)
    wsum, wdom, walked, verts = bone_weights(env)

    print("%s" % os.path.basename(path))
    print("meshes walked %d, vertices read %d, bones with any weight %d"
          % (walked, verts, len(wsum)))
    if not walked or not verts:
        print("REFUSED: no skinned mesh was read, so every zero below would be the "
              "instrument. Nothing here is a measurement.")
        return 1

    rows, named, matched = per_chain(springs, joints, go_tf, gname, wsum, wdom)

    print("bones named %d, matched to a transform %d, UNMATCHED %d"
          % (named, matched, named - matched))
    if named and matched == 0:
        print("REFUSED: not one joint bone joined to the skin. The GameObject->Transform "
              "join is broken, and every 0.0 below is that bug rather than a dead chain.")
        return 1

    live = [r for r in rows if r[2] > 0]
    dead = [r for r in rows if r[2] == 0 and r[4] == 0]
    print()
    print("%-22s %5s %12s %8s" % ("chain", "joint", "sum w", "dom v"))
    for name, n, tot, dom, unm, _b in sorted(rows, key=lambda r: -r[2]):
        if want is not None and not want.search(name):
            continue
        tag = "" if tot > 0 else ("  <- carries NOTHING" if unm == 0
                                  else "  <- has UNMATCHED bones, not a drop candidate")
        print("%-22s %5d %12.2f %8d%s" % (name[:22], n, tot, dom, tag))

    print()
    print("%d chain(s) carry weight, %d carry none." % (len(live), len(dead)))
    if not live:
        print("REFUSED to call anything a drop candidate: NO chain on this character "
              "carries weight, which is an instrument fault and not a finding.")
        return 1
    if live:
        lo = min(r[2] for r in live)
        print("The lightest LIVE chain is %.2f (%s) -- that is the non-zero beside the "
              "zeros, and it is what makes them readable."
              % (lo, next(r[0] for r in live if r[2] == lo)))
    if dead:
        print()
        print("DROP CANDIDATES (sum w == 0.0, every bone matched):")
        for name, n, _t, _d, _u, bones_out in dead:
            print("  %-20s %d joints: %s" % (name, n, ", ".join(bones_out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
