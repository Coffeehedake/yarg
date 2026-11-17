# -*- coding: utf-8 -*-
"""Connected islands of an installed bundle's meshes, each with its own world
box, its box centre in X, and the bone that drives most of it.

    python islands_installed.py <file.yargchar> [min-verts]

"The armour is not centred on his chest" is a statement about ONE piece, and
every other measurement is about the whole character. A chest plate is a
connected island; so is a pauldron, a vambrace, a belt and each half of a
helmet. Split the mesh and each piece can be put beside the bone that carries
it. This is how The Mandalorian's chest plate was found: 280 vertices,
y 1.173..1.493, carried by `Chest`.

**The box centre is NOT a centreline.** That plate reads +22.9 mm here and its
own plane of symmetry is -8.0 mm, because it genuinely extends further on one
side than the other: the box measures EXTENT and says nothing about where a
part is centred. Reading the box alone gives a confident "the plate is 23 mm
off" and sends the fix to the wrong place. Use this to FIND an island, then
`mesh_mirror_installed.py` on that island to ask where it is centred.

Equal vertex counts across a pair of islands are worth noticing -- the two
helmet ears are 190 and 190, the two hands 889 and 889 -- but an equal count
is weak evidence on its own, and a pair whose counts match while their widths
do not is a part that has been TURNED rather than displaced.

Everything is measured in the REST pose of the file that ships. Nothing is
written.
"""
import os
import sys

import numpy as np

import cloth_collide_installed as cci
import mesh_mirror_installed as mm


def islands(P, lo, hi, tri, floor):
    """(indices,) per connected island of at least `floor` vertices."""
    parent = np.arange(hi)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in tri:
        ra, rb, rc = find(a), find(b), find(c)
        if ra != rb:
            parent[rb] = ra
        if ra != rc:
            parent[rc] = ra
    roots = np.array([find(i) for i in range(lo, hi)])
    out = []
    for r in np.unique(roots):
        sel = np.nonzero(roots == r)[0] + lo
        if len(sel) >= floor:
            out.append(sel)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    floor = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    got = mm.skinned_cloud(path)
    if got is None:
        print("nothing skinned could be decoded")
        return 2
    P, dom, T, parts, human, tf, world = got

    name_of = {pid: n["name"] for pid, n in tf.items() if n.get("name")}
    hum_of = {}
    for hn, bn in human.items():
        for pid, n in tf.items():
            if n.get("name") == bn:
                hum_of[pid] = hn
                break

    print("%s -- islands of at least %d vertices"
          % (os.path.basename(path), floor))
    for mname, lo, hi, tri in parts:
        if tri is None or not len(tri):
            continue
        sels = islands(P, lo, hi, tri, floor)
        print("")
        print("  %s -- %d verts, %d island(s) at or above the floor"
              % (mname, hi - lo, len(sels)))
        rows = []
        for sel in sels:
            Q = P[sel]
            Q = Q[~np.isnan(Q[:, 0])]
            if not len(Q):
                continue
            bones, counts = np.unique(dom[sel], return_counts=True)
            top = int(bones[int(np.argmax(counts))])
            rows.append((Q[:, 1].max(), len(sel), Q, top,
                         counts.max() / float(counts.sum())))
        for ymax, nv, Q, top, share in sorted(rows, reverse=True):
            label = hum_of.get(top) or name_of.get(top) or "?"
            bx = world(top)[0][0]
            cx = 0.5 * (Q[:, 0].min() + Q[:, 0].max())
            print("    %5d verts  y %6.3f..%6.3f  x %+7.1f..%+7.1f  "
                  "box centre %+7.1f mm   %-14s at %+7.1f mm   "
                  "offset %+7.1f mm   %3.0f%% on it"
                  % (nv, Q[:, 1].min(), Q[:, 1].max(),
                     Q[:, 0].min() * 1000, Q[:, 0].max() * 1000, cx * 1000,
                     label[:14], bx * 1000, (cx - bx) * 1000, share * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main())
