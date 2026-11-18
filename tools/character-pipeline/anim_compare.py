# -*- coding: utf-8 -*-
"""Compare the same roster animated at TWO yaws, and find where the views disagree.

    python anim_compare.py <front-frames-dir> <side-frames-dir> <manifest.csv> [<top-n>]

WHY A SECOND VIEW IS NOT JUST MORE OF THE SAME. A single yaw does not under-sample the
problem, it is BLIND along one axis. Head-on, the horizontal extent of the silhouette is the
character's WIDTH and depth is compressed to nothing: a ponytail swinging forward, a cape
billowing back, a hand passing in front of the chest all happen along the axis the camera has
collapsed. Rotate 90 degrees and that same horizontal extent IS the depth. So the side view
does not confirm the front view, it measures a different thing.

That is also why the interesting output here is not the side ranking on its own -- it is the
DISAGREEMENT. A character ordinary in both views is ordinary. A character ordinary head-on and
extreme side-on is doing something in depth, and depth is exactly where the first sweep could
not look. The reverse disagreement is worth as much: extreme head-on and ordinary side-on means
the first sweep's reading was about width alone.

All four metrics are already scale-free -- span_grow is a ratio to the character's own median,
area_cv is a coefficient of variation, jump and drift are normalised by the character's own
height -- so they are comparable BETWEEN views even though a humanoid is narrower side-on than
head-on. Nothing here compares raw pixels across views, which would just be measuring that
people are deeper than they are wide.

A character missing from either view is NAMED, not dropped. "Present in one view only" is a
coverage hole, and a comparison that quietly skips it reports agreement it never tested.
"""
import csv
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim_sheet import silhouette, podium_cut, measure  # noqa: E402
from anim_sweep import robust_z  # noqa: E402

KEYS = ["span_grow", "area_cv", "jump", "drift"]


def metrics_for(d):
    groups = defaultdict(list)
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(".png") and "_f" in f:
            groups[f.rsplit("_f", 1)[0]].append(f)
    out = {}
    for lab, files in groups.items():
        files = sorted(files)
        ims, masks = [], []
        for f in files:
            im, m = silhouette(os.path.join(d, f))
            ims.append(im)
            masks.append(m)
        cut = podium_cut(masks, ims)
        ms = [m for m in (measure(x, cut) for x in masks) if m]
        if len(ms) < 3:
            continue
        area = np.array([m["area"] for m in ms], float)
        span = np.array([m["span"] for m in ms], float)
        w = np.array([m["w"] for m in ms], float)
        h = np.array([m["h"] for m in ms], float)
        cx = np.array([m["cx"] for m in ms], float)
        if np.ptp(area) == 0 and np.ptp(span) == 0 and np.ptp(cx) == 0:
            continue
        scale = max(float(np.median(h)), 1.0)
        out[lab] = {
            "span_grow": float(span.max() / max(np.median(span), 1.0)),
            "area_cv": float(area.std() / max(area.mean(), 1.0)),
            "jump": float(max(np.abs(np.diff(w)).max(), np.abs(np.diff(h)).max()) / scale),
            "drift": float(np.ptp(cx) / scale),
        }
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    front_d, side_d, man = sys.argv[1], sys.argv[2], sys.argv[3]
    topn = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    real = {}
    with open(man, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            real[row["Label"]] = row["Real"]

    front, side = metrics_for(front_d), metrics_for(side_d)
    only_f = sorted(set(front) - set(side))
    only_s = sorted(set(side) - set(front))
    both = sorted(set(front) & set(side))
    print("front %d, side %d, comparable %d" % (len(front), len(side), len(both)))
    for label, group in (("FRONT ONLY", only_f), ("SIDE ONLY", only_s)):
        if group:
            print("%s (%d) -- NOT comparable, coverage hole: %s"
                  % (label, len(group), ", ".join(real.get(g, g) for g in group)))
    if not both:
        print("nothing comparable")
        return 1

    zf = {k: robust_z([front[l][k] for l in both])[0] for k in KEYS}
    zs = {k: robust_z([side[l][k] for l in both])[0] for k in KEYS}

    rows = []
    for i, l in enumerate(both):
        f_worst = max(float(zf[k][i]) for k in KEYS)
        s_worst = max(float(zs[k][i]) for k in KEYS)
        # Which metric disagrees MOST between the views, and by how much. Signed, because
        # "invisible head-on" and "only visible head-on" are different stories.
        gaps = {k: float(zs[k][i] - zf[k][i]) for k in KEYS}
        wk = max(KEYS, key=lambda k: abs(gaps[k]))
        rows.append({"name": real.get(l, l), "zf": f_worst, "zs": s_worst,
                     "gap": gaps[wk], "which": wk})

    print("")
    print("RANKED BY THE SIDE VIEW (depth-axis motion the front view cannot see)")
    print("%-30s %7s %7s" % ("character", "z_side", "z_front"))
    for r in sorted(rows, key=lambda r: -r["zs"])[:topn]:
        print("%-30s %7.2f %7.2f" % (r["name"][:30], r["zs"], r["zf"]))

    print("")
    print("RANKED BY DISAGREEMENT (+ve = far more extreme SIDE-on, which is the blind axis)")
    print("%-30s %7s %7s %7s  %s" % ("character", "gap", "z_side", "z_front", "metric"))
    for r in sorted(rows, key=lambda r: -abs(r["gap"]))[:topn]:
        print("%-30s %+7.2f %7.2f %7.2f  %s"
              % (r["name"][:30], r["gap"], r["zs"], r["zf"], r["which"]))

    print("")
    print("A character ordinary in BOTH columns is ordinary. One ordinary head-on and extreme "
          "side-on is moving in DEPTH, which is what this second view was added to reach.")
    print("STILL UNSEEN at both yaws: anything interior. Hair across a face changes the outline "
          "side-on only if it projects past the profile; a hand inside a skirt never does.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
