# -*- coding: utf-8 -*-
"""Tile a YargCharAnim frame sequence into ONE image, and measure it.

    python anim_sheet.py <dir-of-frames> <out.png> [<name-prefix>]

WHY A SHEET AND NOT A GIF. The point of rendering an animation here is for it to be LOOKED at,
and a reader that can open a still image cannot watch a GIF or an MP4 -- an animated GIF arrives
as its first frame and a video as nothing at all. A contact sheet is the form that survives: the
whole motion in one still, read left to right, beside numbers that say what moved.

WHAT IT MEASURES, per frame, on the character's own silhouette (largest connected component, so
the song title across the top of the frame and the podium underneath are excluded -- a per-row
measurement that includes either is measuring the furniture):

    area      silhouette pixels. Hair flung out grows it; hair settling in shrinks it.
    w, h      bounding box of the character.
    cx        horizontal centroid, relative to the median across the sequence. A limb or a
              ponytail swinging one way moves it; a character standing still does not.
    span      widest row. This is the one that catches a ballooning hair chain, because hair
              reaches wider than the body does.

A SEQUENCE THAT DOES NOT MOVE IS REPORTED AS A FAULT OF THE MEASUREMENT, NOT OF THE SUBJECT.
Identical frames look exactly like a character correctly standing still, and this project has
already read a harness's own zero as a finding about five different characters. So if nothing
changes across the sequence this says the frames are unusable rather than letting the reader
conclude the character is static. YargCharAnim makes the same check inside Unity; agreeing
checks at both ends is deliberate, because the failure is silent at both.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

try:
    from scipy import ndimage
except ImportError:
    ndimage = None


def silhouette(path):
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    mask = im.max(axis=2) > 18
    if ndimage is not None and mask.any():
        lab, n = ndimage.label(mask)
        if n > 0:
            sizes = ndimage.sum(mask, lab, range(1, n + 1))
            mask = lab == (int(np.argmax(sizes)) + 1)
    return im, mask


def podium_cut(masks, frames):
    """The row where the podium starts, found from the data rather than guessed.

    THE CHARACTER STANDS ON THE PODIUM AND HIS FEET TOUCH IT, so "largest connected component"
    does NOT isolate him -- it returns him WELDED TO THE FURNITURE, and every measurement then
    carries a constant that is not the subject. Measured here: both characters' components ran
    to the same y=633 and the same widest row of 217 px at y=546, which is the podium disc in
    both. Two different characters agreeing to the pixel is the tell.

    The podium is identified by the one property it has and the character does not: IT DOES NOT
    MOVE. Pixels byte-identical across every frame are furniture by construction. That only
    locates the CUT ROW -- measurement above it uses the whole mask, so a character's own still
    interior is not thrown away with it.
    """
    if len(frames) < 2:
        return None
    static = np.ones(frames[0].shape[:2], dtype=bool)
    for f in frames[1:]:
        static &= (np.abs(f - frames[0]).max(axis=2) <= 8)
    furniture = static & masks[0]
    if ndimage is None or not furniture.any():
        return None
    lab, n = ndimage.label(furniture)
    sizes = ndimage.sum(furniture, lab, range(1, n + 1))
    blob = lab == (int(np.argmax(sizes)) + 1)
    ys, _ = np.nonzero(blob)
    # Only treat it as the podium if it is a big static blob in the LOWER half of the frame.
    if blob.sum() < 2000 or ys.min() < frames[0].shape[0] // 2:
        return None
    return int(ys.min())


def measure(mask, cut=None):
    m = mask if cut is None else mask[:cut, :]
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return None
    # EXTENT per row, not the COUNT of filled pixels in it. The count is not a width: a figure
    # with its legs apart has a gap, so the count under-reads, and it reads the podium's solid
    # disc as the widest thing in the frame. That bug held this field at a constant 217 across
    # 24 frames and two characters, which looked like a stable measurement and was a dead one.
    ext = np.zeros(m.shape[0], dtype=int)
    rows = np.nonzero(m.any(axis=1))[0]
    for y in rows:
        x = np.nonzero(m[y])[0]
        ext[y] = x[-1] - x[0]
    return {
        "area": int(m.sum()),
        "w": int(xs.max() - xs.min()),
        "h": int(ys.max() - ys.min()),
        "cx": float(xs.mean()),
        "span": int(ext.max()),
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    d, out = sys.argv[1], sys.argv[2]
    pre = sys.argv[3] if len(sys.argv) > 3 else ""
    files = sorted(f for f in os.listdir(d)
                   if f.lower().endswith(".png") and f.startswith(pre) and "_f" in f)
    if not files:
        print("no frames matching %r in %s" % (pre, d))
        return 2

    ims, masks, thumbs = [], [], []
    for f in files:
        im, mask = silhouette(os.path.join(d, f))
        ims.append(im)
        masks.append(mask)
        t = Image.fromarray(im.astype(np.uint8))
        t.thumbnail((260, 260))
        thumbs.append(t)

    cut = podium_cut(masks, ims)
    if cut is None:
        print("NOTE: no static podium blob found; measuring the whole component. If these frames "
              "contain a podium the character stands on, these numbers include it.")
    else:
        print("podium found at y=%d; everything below it is excluded from the measurements." % cut)
    rows = [(f, measure(m, cut)) for f, m in zip(files, masks)]

    cols = min(6, len(thumbs))
    cw, chh = thumbs[0].size[0] + 6, thumbs[0].size[1] + 20
    nrows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, nrows * chh), (26, 26, 30))
    dr = ImageDraw.Draw(sheet)
    for i, t in enumerate(thumbs):
        x, y = (i % cols) * cw, (i // cols) * chh
        sheet.paste(t, (x + 3, y + 3))
        dr.text((x + 6, y + t.size[1] + 5), "f%d" % i, fill=(210, 210, 215))
    sheet.save(out)

    good = [m for _, m in rows if m]
    base = float(np.median([m["cx"] for m in good])) if good else 0.0
    print("%-6s %-8s %-6s %-6s %-9s %-6s" % ("frame", "area", "w", "h", "cx(rel)", "span"))
    for i, (f, m) in enumerate(rows):
        if not m:
            print("f%-5d (empty frame)" % i)
            continue
        print("f%-5d %-8d %-6d %-6d %-+9.1f %-6d"
              % (i, m["area"], m["w"], m["h"], m["cx"] - base, m["span"]))

    if len(good) > 1:
        areas = np.array([m["area"] for m in good], dtype=float)
        spans = np.array([m["span"] for m in good], dtype=float)
        cxs = np.array([m["cx"] for m in good], dtype=float)
        rng = areas.max() - areas.min()
        print("")
        print("area range %.0f px (%.2f%% of mean), span range %.0f, cx range %.1f"
              % (rng, 100.0 * rng / areas.mean(), spans.max() - spans.min(), cxs.max() - cxs.min()))
        # The control. Identical frames are indistinguishable from a character standing still,
        # so this refuses to let the sequence be read at all rather than reporting "no motion".
        if rng == 0 and (spans.max() - spans.min()) == 0 and (cxs.max() - cxs.min()) == 0:
            print("CONTROL FAILED: every frame is identical. These frames say NOTHING about the "
                  "character -- the Animator did not advance, or the meshes were not re-baked "
                  "per frame. Do not read this as 'it does not move'.")
            return 1
        print("CONTROL OK: the sequence moves, so differences between frames are the subject's.")
    print("")
    print("sheet -> %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
