# -*- coding: utf-8 -*-
"""Is a surface LIT or UNLIT? Luminance variation across curved skin.

    python shade_flat.py <frames-dir> <prefix> [<prefix> ...]

THE PHYSICS, which is why this needs no threshold: a LIT surface shades with curvature, so
luminance falls away from the light across a rounded torso. An UNLIT surface does not -- it
renders its texture flat, whatever the geometry is doing. So luminance STANDARD DEVIATION over
a patch of curved skin separates the two shading models directly.

WHY THE TORSO AND NOT THE FACE. The face is where the seam question lives, but it is also where
the hair is, and hair over skin produces luminance variation that has nothing to do with
shading. The torso is large, curved, unobstructed and entirely one material, so it measures the
shading model and nothing else.

THIS IS A POSITIVE CONTROL FIRST AND A MEASUREMENT SECOND. Run it on a build known lit and a
build known unlit before trusting it on anything ambiguous: if it cannot separate those two, it
cannot detect a shading difference at all, and a clean reading from it means nothing. That is
this repo's rule about an instrument that has never been seen to produce a finding, and
yarg-1 is the one who pointed out I had both extremes available for free.

The band is swept, because its placement is the only free choice here.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BG = 2


def patch_stats(path, lo_f, hi_f):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    v = im.max(axis=2)
    body = v > BG
    lab, n = ndimage.label(body)
    if n:
        sz = ndimage.sum(body, lab, range(1, n + 1))
        body = lab == (int(np.argmax(sz)) + 1)
    ys, xs = np.nonzero(body)
    top, bot = ys.min(), ys.max()
    y0 = top + int(lo_f * (bot - top))
    y1 = top + int(hi_f * (bot - top))
    band = body[y0:y1]
    if band.sum() < 200:
        return None
    bx = np.nonzero(band.any(axis=0))[0]
    cx = int((bx[0] + bx[-1]) / 2)
    half = int(0.25 * (bx[-1] - bx[0]))
    sl = slice(max(cx - half, 0), cx + half)
    lum = 0.2126 * im[y0:y1, sl, 0] + 0.7152 * im[y0:y1, sl, 1] + 0.0722 * im[y0:y1, sl, 2]
    m = body[y0:y1, sl]
    if m.sum() < 200:
        return None
    vals = lum[m]
    # gradient magnitude inside the patch: shading makes a smooth ramp, unlit makes none
    g = np.hypot(*np.gradient(np.where(m, lum, np.nan)))
    g = g[np.isfinite(g)]
    return {"mean": float(vals.mean()), "std": float(vals.std()),
            "grad": float(np.nanmean(g)) if g.size else 0.0, "n": int(m.sum())}


def main():
    d = sys.argv[1]
    tags = sys.argv[2:]
    for lo, hi in ((0.30, 0.50), (0.35, 0.60), (0.40, 0.70)):
        print("=== torso band %.2f-%.2f of height ===" % (lo, hi))
        print("%-12s %9s %9s %9s %9s" % ("build", "mean", "STD", "grad", "px"))
        rows = {}
        for t in tags:
            fs = sorted(f for f in os.listdir(d) if f.startswith(t) and "_f" in f)
            st = [patch_stats(os.path.join(d, f), lo, hi) for f in fs]
            st = [s for s in st if s]
            if not st:
                print("%-12s (no frames)" % t)
                continue
            rows[t] = {k: float(np.mean([s[k] for s in st])) for k in ("mean", "std", "grad", "n")}
            print("%-12s %9.2f %9.3f %9.4f %9.0f"
                  % (t[:12], rows[t]["mean"], rows[t]["std"], rows[t]["grad"], rows[t]["n"]))
        print("")
    print("READ IT AS: UNLIT should give a markedly LOWER std and LOWER grad than LIT on the")
    print("same curved torso. If two builds known to differ in shading model do NOT separate")
    print("here, this instrument is blind and no reading from it may be used.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
