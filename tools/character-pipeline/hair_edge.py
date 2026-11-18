# -*- coding: utf-8 -*-
"""Measure the HAIR EDGE -- the thing MASK and OPAQUE actually differ on.

    python hair_edge.py <frames-dir> <prefixA> <prefixB>

WHY MEASURE AND NOT LOOK. Earlier today I judged a cape "rigid" from a contact sheet and was
wrong, because the quantity in the claim had never been measured. The claim here is about
hair-card EDGES, so this measures edges.

WHAT THE BRANCHES DO. Her hair texture carries 13.09% of its pixels below full alpha: a real
cutout mask on the card edges.

  OPAQUE  ignores the mask -- each card renders as a full quad, so the outline is SMOOTHER and
          blockier and encloses more area.
  MASK    alpha-tests and writes depth -- card edges are cut away, so the outline is WISPIER,
          with strands and gaps.

WHAT CHANGED AFTER THE FIRST ATTEMPT, which is the useful part. v1 segmented hair by DARKNESS
inside the head region and its own cutoff sweep came back UNSTABLE: the ordering flipped at
three of five cutoffs and hair area swung 371 -> 12,527 px across the range. Looking at the
crop showed why -- her hair carries a lit sheen and her face carries shadow, so brightness does
not separate them at any cutoff. The guard caught it; the measurement was discarded rather than
reported.

So this version segments NOTHING by colour. It measures the OUTER SILHOUETTE of the head
region against the background, using only the background cutoff every other tool here uses.
That boundary IS the hair-card edge wherever hair meets background, which is exactly where the
two branches differ, and it removes the unstable threshold completely rather than tuning it.

Reported as the isoperimetric ratio P^2 / (4*pi*A): 1.0 for a perfect disc, growing with
raggedness, and scale-free so two renders of different size stay comparable.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BG = 2


def head_silhouette(path, frac=0.22):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    body = im.max(axis=2) > BG
    lab, n = ndimage.label(body)
    if n:
        sz = ndimage.sum(body, lab, range(1, n + 1))
        body = lab == (int(np.argmax(sz)) + 1)
    ys, _ = np.nonzero(body)
    top, bot = ys.min(), ys.max()
    cut = top + int(frac * (bot - top))
    return body[top:cut, :]


def measure(path, frac):
    m = head_silhouette(path, frac)
    area = int(m.sum())
    if area < 50:
        return None
    er = ndimage.binary_erosion(m, np.ones((3, 3), bool))
    per = int((m & ~er).sum())
    return {"area": area, "per": per, "iso": (per * per) / (4.0 * np.pi * area)}


def main():
    d, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
    fa = sorted(f for f in os.listdir(d) if f.startswith(a) and "_f" in f)
    fb = sorted(f for f in os.listdir(d) if f.startswith(b) and "_f" in f)
    if not fa or not fb:
        print("missing frames: %s=%d %s=%d" % (a, len(fa), b, len(fb)))
        return 2
    print("%-12s %-6s %9s %8s %9s" % ("subject", "frac", "area", "perim", "iso"))
    diffs = []
    # The head-region fraction is the one remaining free choice, so SWEEP IT TOO.
    for frac in (0.16, 0.20, 0.24, 0.28):
        row = {}
        for tag, files in ((a, fa), (b, fb)):
            ms = [measure(os.path.join(d, f), frac) for f in files]
            ms = [m for m in ms if m]
            if not ms:
                continue
            row[tag] = {k: float(np.mean([m[k] for m in ms])) for k in ("area", "per", "iso")}
            print("%-12s %-6.2f %9.0f %8.0f %9.3f"
                  % (tag[:12], frac, row[tag]["area"], row[tag]["per"], row[tag]["iso"]))
        if a in row and b in row:
            diffs.append((frac, row[a]["iso"] - row[b]["iso"]))
        print("")
    print("=== does the ordering survive the sweep? ===")
    for frac, d_iso in diffs:
        print("  frac %.2f  iso higher (wispier) for %-12s by %+.3f"
              % (frac, a[:12] if d_iso > 0 else b[:12], abs(d_iso)))
    if diffs and len({np.sign(x[1]) for x in diffs}) == 1:
        print("  STABLE: same ordering at every head fraction. Safe to read.")
    else:
        print("  UNSTABLE: the ordering FLIPS -- this is the cutoff's finding, not the "
              "subject's. Do not conclude from it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
