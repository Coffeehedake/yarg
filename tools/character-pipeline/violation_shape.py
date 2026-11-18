# -*- coding: utf-8 -*-
"""Is a character's depth-order violation a THIN CURVE or a BROAD REGION?

    python violation_shape.py <painted.png> <plain.png> [<label>] ...

THE QUESTION THIS SETTLES. `YargCharParts` flags pixels where the hair/cloth half is visible
while the body half is geometrically nearer. Its stated mechanism is the Aiko bug: a BLEND
material does not write depth, so geometry behind composites over what is in front. But the
roster's top row, Jessica Rabbit, carries **eleven opaque materials and no blended ones**, so she
cannot produce that mechanism at all -- and she still scores 1.5x the next character.

Two readings, and they are not the same finding:

  (a) THE PROBE SEES MORE THAN ITS STATED MECHANISM. Where two opaque surfaces interpenetrate,
      depths along the intersection are near-coincident and which surface wins is arbitrary.
      That would mark a THIN CURVE tracing where the surfaces cross. The probe would then be a
      geometry-interpenetration detector as well as a draw-order one -- useful, but it means the
      ranking mixes two faults and must be read that way.

  (b) IT IS A FALSE-POSITIVE MODE on opaque geometry -- a split or compositing artefact. That
      would mark a BROAD FILLED REGION, and the ranking needs re-reading from the top.

THE DISCRIMINATOR IS EROSION, and it is blunt on purpose. Strip one pixel from the boundary of
the flagged set: a curve one to three pixels wide very nearly vanishes, while a filled blob keeps
most of its area. `retained = |erode(mask)| / |mask|`.

    retained ~ 0.0 - 0.2   a curve        -> (a)
    retained ~ 0.6 - 0.9   a filled area  -> (b)

THE MASK IS TAKEN BY DIFFERENCE, NOT BY COLOUR. The painted frame marks violations in pure
green, and the obvious thing is to select green pixels -- but Jessica Rabbit's costume HAS green
on it, and "the character is the colour I chose to paint with" is how a probe measures a
costume. Differencing the painted frame against the unpainted one of the same frame is exact and
cannot confuse the two.

A COMPARISON IS REQUIRED, NOT OPTIONAL. A single retained fraction means nothing without a case
whose mechanism is known: pass the synthetic/real BLEND positive alongside, where the violation
IS a genuine draw-order failure over a broad area, and read the suspect against it.
"""
import os
import sys

import numpy as np
from PIL import Image

try:
    from scipy import ndimage
except ImportError:
    ndimage = None


def erode(mask):
    """4-neighbour erosion. Written out so scipy is a convenience, not a dependency."""
    if ndimage is not None:
        return ndimage.binary_erosion(mask, structure=np.array([[0, 1, 0],
                                                                [1, 1, 1],
                                                                [0, 1, 0]], bool))
    m = mask
    out = m.copy()
    out[1:, :] &= m[:-1, :]
    out[:-1, :] &= m[1:, :]
    out[:, 1:] &= m[:, :-1]
    out[:, :-1] &= m[:, 1:]
    out[0, :] = False; out[-1, :] = False; out[:, 0] = False; out[:, -1] = False
    return out


def analyse(painted_path, plain_path, label):
    a = np.asarray(Image.open(painted_path).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(plain_path).convert("RGB"), dtype=np.int16)
    if a.shape != b.shape:
        print("  %-22s SHAPES DIFFER %s vs %s -- not comparable" % (label, a.shape, b.shape))
        return None
    mask = (np.abs(a - b).sum(axis=2) > 24)
    n = int(mask.sum())
    if n == 0:
        print("  %-22s NO FLAGGED PIXELS -- nothing to shape-test, and that is not a thin curve"
              % label)
        return None

    e1 = erode(mask)
    e2 = erode(e1)
    r1, r2 = e1.sum() / float(n), e2.sum() / float(n)

    # How many components, and how big is the largest: a long thin curve is usually one or a few
    # components; scattered single pixels are a different thing again and must not read as a curve.
    comps, ncomp = (ndimage.label(mask) if ndimage is not None else (None, -1))
    biggest = 0
    if ndimage is not None and ncomp > 0:
        sizes = ndimage.sum(mask, comps, range(1, ncomp + 1))
        biggest = int(sizes.max())

    verdict = ("CURVE  -> interpenetration (a)" if r1 <= 0.25 else
               "BROAD  -> filled region (b)" if r1 >= 0.55 else
               "AMBIGUOUS -- neither reading is supported")
    print("  %-22s n=%6d  retained(1px)=%.3f  retained(2px)=%.3f  comps=%s  largest=%d   %s"
          % (label, n, r1, r2, ncomp if ncomp >= 0 else "?", biggest, verdict))
    return r1


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    print("=" * 78)
    print("SHAPE OF THE FLAGGED PIXELS  (erosion: a curve vanishes, a blob survives)")
    print("=" * 78)
    i = 0
    seen = 0
    while i + 1 < len(args):
        painted, plain = args[i], args[i + 1]
        label = args[i + 2] if i + 2 < len(args) and not args[i + 2].lower().endswith(".png") \
            else os.path.basename(painted)[:22]
        step = 3 if (i + 2 < len(args) and not args[i + 2].lower().endswith(".png")) else 2
        if not os.path.isfile(painted) or not os.path.isfile(plain):
            print("  %-22s MISSING FILE -- skipped, which is not a result" % label)
        else:
            analyse(painted, plain, label)
            seen += 1
        i += step
    if seen < 2:
        print()
        print("ONLY %d CASE READ. A retained fraction on its own says nothing; pass a known" % seen)
        print("draw-order positive alongside the suspect or this comparison is not a comparison.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
