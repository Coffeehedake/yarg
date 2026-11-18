# -*- coding: utf-8 -*-
"""Rank a whole roster's ANIMATION frames and flag the outliers.

    python anim_sweep.py <frames-dir> <manifest.csv> [<top-n>]

`anim_sheet.py` answers "what does this one character do". This answers "which of the
sixty-five is worth looking at", because looking at sixty-five contact sheets by eye is
how a sweep turns into a skim and a skim finds nothing.

WHAT IT CAN AND CANNOT SEE -- say this out loud rather than letting the output imply
otherwise. Every metric here is taken from the SILHOUETTE, so:

  CAN see   hair or cloth flung outward, a limb or prop swinging free of the body, geometry
            that pops or explodes between adjacent frames, a character that drifts off its
            podium.
  CANNOT see anything INTERIOR: hair across a face, a hand passing through a skirt, an arm
            inside a torso. The outline is identical whether or not the hair is in front of
            her eyes.

That second line matters here, because the open fault on Aiko is "her hair goes over her
face" -- which is exactly the class this sweep is blind to. A clean sweep is therefore NOT a
clean roster, and the summary says so.

NO THRESHOLD IS INVENTED. There is no prior for what a normal amount of idle motion looks
like, so a fixed cutoff would be a guess dressed as a standard. Instead the POPULATION sets
the scale: each metric is scored by its robust z (median and MAD, not mean and sd, so a
handful of genuinely broken characters cannot inflate the yardstick that is supposed to
catch them). The tail is what gets looked at.

CHARACTERS WITH NO ANIMATOR ARE HELD OUT, NOT RANKED. Their frames are identical by
construction, which would otherwise make them the most "stable" characters on the roster --
a perfect score for a character nothing can animate. They are counted and named separately.
"""
import csv
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim_sheet import silhouette, podium_cut, measure  # noqa: E402


def robust_z(vals):
    """Median/MAD, so a few broken characters cannot inflate the scale that should catch them."""
    v = np.asarray(vals, dtype=float)
    med = np.median(v)
    mad = np.median(np.abs(v - med))
    if mad == 0:
        return np.zeros_like(v), med, 0.0
    return 0.6745 * (v - med) / mad, med, mad


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    d, manifest = sys.argv[1], sys.argv[2]
    topn = int(sys.argv[3]) if len(sys.argv) > 3 else 8

    real = {}
    with open(manifest, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            real[row["Label"]] = row["Real"]

    groups = defaultdict(list)
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(".png") and "_f" in f:
            groups[f.rsplit("_f", 1)[0]].append(f)

    print("%d character(s) with frames, %d in the manifest" % (len(groups), len(real)))
    missing = [lab for lab in real if lab not in groups]
    if missing:
        # A character with no frames was NOT measured and is not "clean". Name every one.
        print("NOT RENDERED (%d) -- these were not measured at all: %s"
              % (len(missing), ", ".join(real[m] for m in sorted(missing))))

    rows, dead = [], []
    for lab in sorted(groups):
        files = sorted(groups[lab])
        if len(files) < 3:
            dead.append((lab, "only %d frame(s)" % len(files)))
            continue
        ims, masks = [], []
        for f in files:
            im, m = silhouette(os.path.join(d, f))
            ims.append(im)
            masks.append(m)
        cut = podium_cut(masks, ims)
        ms = [measure(m, cut) for m in masks]
        ms = [m for m in ms if m]
        if len(ms) < 3:
            dead.append((lab, "empty frames"))
            continue

        area = np.array([m["area"] for m in ms], float)
        span = np.array([m["span"] for m in ms], float)
        w = np.array([m["w"] for m in ms], float)
        h = np.array([m["h"] for m in ms], float)
        cx = np.array([m["cx"] for m in ms], float)

        # Identical frames across the whole sequence: either no Animator (a fact about the
        # character) or an Animator that did not advance (a fact about the harness). This
        # cannot tell them apart from the images alone -- the Unity log can, and does.
        if np.ptp(area) == 0 and np.ptp(span) == 0 and np.ptp(cx) == 0:
            dead.append((lab, "no motion at all"))
            continue

        scale = max(float(np.median(h)), 1.0)
        rows.append({
            "lab": lab,
            "name": real.get(lab, lab),
            # hair/cloth flung out: the widest the outline ever gets, against its usual width
            "span_grow": float(span.max() / max(np.median(span), 1.0)),
            # overall billow: how much the silhouette breathes
            "area_cv": float(area.std() / max(area.mean(), 1.0)),
            # a pop: the worst SINGLE-frame jump in either box dimension, as a % of height
            "jump": float(max(np.abs(np.diff(w)).max(), np.abs(np.diff(h)).max()) / scale),
            # drift: how far the centroid wanders, as a % of height
            "drift": float(np.ptp(cx) / scale),
            "frames": len(ms),
        })

    if not rows:
        print("nothing measurable")
        return 1

    keys = ["span_grow", "area_cv", "jump", "drift"]
    zs = {}
    for k in keys:
        z, med, mad = robust_z([r[k] for r in rows])
        zs[k] = z
        print("  %-10s median %8.4f  MAD %8.4f" % (k, med, mad))
    for i, r in enumerate(rows):
        # Worst single metric, not the sum: a character broken in ONE way should rank as
        # broken, and averaging four scores would dilute exactly that case.
        r["z"] = max(float(zs[k][i]) for k in keys)
        r["why"] = max(keys, key=lambda k: zs[k][i])

    rows.sort(key=lambda r: -r["z"])
    print("")
    print("%-34s %6s %9s %8s %7s %7s  %s" % ("character", "z", "span_grow", "area_cv", "jump", "drift", "worst"))
    for r in rows[:topn]:
        print("%-34s %6.2f %9.3f %8.4f %7.3f %7.3f  %s"
              % (r["name"][:34], r["z"], r["span_grow"], r["area_cv"], r["jump"], r["drift"], r["why"]))

    print("")
    print("%d ranked, %d held out" % (len(rows), len(dead)))
    for lab, why in dead:
        print("   HELD OUT %-30s %s" % (real.get(lab, lab)[:30], why))
    print("")
    print("LOOK AT the top of that list, and read the Unity log for every HELD OUT row: "
          "'no motion at all' is a NO ANIMATOR fact about the character or a CONTROL FAILURE "
          "of the harness, and the images cannot tell you which.")
    print("REMEMBER this sweep is silhouette-only: hair across a face, or a hand through a "
          "skirt, leaves the outline unchanged and will NOT appear here at any rank.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
