# -*- coding: utf-8 -*-
"""Is there a SHADING SEAM on her face? Luminance down the midline, forehead to chest.

    python face_seam.py <frames-dir> <prefix> [<prefix> ...]

WHY. In this builder a cutout is also a shading-model change: enabling MASK turns MToon on and
writes KHR_materials_unlit. On Aiko that puts her HairFace material UNLIT while her Body stays
lit PBR, so two shading models meet on one head. That is the Peach configuration this project
has already shipped once -- a plate of one shading model sitting on a face of another, with a
seam along the join.

WHAT SEPARATES THEM, and it is physics rather than a threshold:

  an UNLIT surface does not shade with curvature -> luminance is FLAT across a curved cheek
  a LIT surface does                              -> luminance falls away from the light

So an unlit face against a lit neck gives BOTH a flatter face AND a step at the join. Two
independent signatures of one cause; if only one shows, something else is going on.

Measured down a central column band so the profile crosses forehead -> cheek -> jaw -> neck ->
chest. Reported per build and compared; a build that is PBR throughout should show a smooth
profile with no step that its neighbours lack.

NO SEGMENTATION BY COLOUR. The one choice is the width of the column band, and it is swept.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BG = 2


def profile(path, halfw):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    v = im.max(axis=2)
    body = v > BG
    lab, n = ndimage.label(body)
    if n:
        sz = ndimage.sum(body, lab, range(1, n + 1))
        body = lab == (int(np.argmax(sz)) + 1)
    ys, xs = np.nonzero(body)
    top, bot = ys.min(), ys.max()
    # midline from the HEAD rows, so shoulders do not drag it sideways
    hrows = body[top:top + int(0.15 * (bot - top)), :]
    hx = np.nonzero(hrows.any(axis=0))[0]
    cx = int((hx[0] + hx[-1]) / 2)
    lo, hi = max(cx - halfw, 0), min(cx + halfw, v.shape[1])
    lum = 0.2126 * im[:, lo:hi, 0] + 0.7152 * im[:, lo:hi, 1] + 0.0722 * im[:, lo:hi, 2]
    mask = body[:, lo:hi]
    prof, rows = [], []
    for y in range(top, min(top + int(0.45 * (bot - top)), v.shape[0])):
        m = mask[y]
        if m.sum() < 4:
            continue
        prof.append(float(lum[y][m].mean()))
        rows.append(y)
    return np.array(prof), np.array(rows), top, bot


def main():
    d = sys.argv[1]
    tags = sys.argv[2:]
    for halfw in (12, 25, 45):
        print("=== column half-width %d px ===" % halfw)
        print("%-12s %8s %8s %9s %9s" % ("build", "mean", "std", "maxstep", "at %H"))
        for t in tags:
            fs = sorted(f for f in os.listdir(d) if f.startswith(t) and "_f" in f)
            if not fs:
                print("%-12s (no frames)" % t)
                continue
            stds, steps, means, ats = [], [], [], []
            for f in fs:
                p, rows, top, bot = profile(os.path.join(d, f), halfw)
                if len(p) < 20:
                    continue
                sm = ndimage.uniform_filter1d(p, 5)
                dif = np.abs(np.diff(sm))
                k = int(np.argmax(dif))
                means.append(p.mean()); stds.append(p.std())
                steps.append(float(dif[k]))
                ats.append(100.0 * (rows[k] - top) / max(bot - top, 1))
            if means:
                print("%-12s %8.1f %8.2f %9.2f %9.1f"
                      % (t[:12], np.mean(means), np.mean(stds), np.mean(steps), np.mean(ats)))
        print("")
    print("READ IT AS: a build whose face is UNLIT should show a LOWER std (flat across a curved")
    print("cheek) AND a LARGER maxstep than the PBR-throughout builds, at a height on the face.")
    print("One signature without the other is not the seam -- say so rather than picking one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
