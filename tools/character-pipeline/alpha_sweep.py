# -*- coding: utf-8 -*-
"""Materials shipping OPAQUE over a base map whose alpha is a cutout mask.

This is Peach's fault, generalised. Her iris, eyelash and eyelid layers are
separate meshes stacked over her eyeball, each carrying a clean two-valued
alpha mask in its own base map, and every one of them shipped `alphaMode:
OPAQUE` -- so the topmost layer drew as a solid plate and she had no eyes. The
report was "eyes missing"; the cause was three materials' alpha channels being
ignored.

The test is the same one `build_vrm.py` uses to DECIDE a cutout, deliberately:
a sweep that disagrees with the fix it recommends is worse than no sweep. An
alpha channel counts as a mask when it is mostly two-valued and is neither
almost entirely clear (which would erase the mesh) nor almost entirely opaque
(which would do nothing).

What it cannot tell you, and the reason this prints rather than fixes: an alpha
channel that LOOKS like a mask is not always meant as one. Pomni's eyes carry a
two-valued alpha that is not a cutout, and inferring one made her eyes
see-through in game. Peach's crown carries an alpha that is an OUTLINE, and
taking it as a cutout carved the jewel out of its setting. Read the hits,
decide per material, and pin the ones you want with
`VRM_CUTOUT_MATERIALS="a;b;c"` rather than turning the inference on wholesale.

    python alpha_sweep.py <file.vrm | dir> [...]
"""
import io
import json
import os
import struct
import sys

from PIL import Image


def load(path):
    d = open(path, "rb").read()
    off, g, bins = 12, None, None
    while off < len(d):
        ln, ty = struct.unpack_from("<II", d, off)
        ch = d[off + 8:off + 8 + ln]
        if ty == 0x4E4F534A:
            g = json.loads(ch.decode("utf-8"))
        elif ty == 0x004E4942:
            bins = ch
        off += 8 + ln + ((4 - ln % 4) % 4)
    return g, bins


def classify(img):
    """clear / solid fractions of the alpha channel, on a 96x96 sample."""
    if img.mode not in ("RGBA", "LA", "PA"):
        return None
    a = img.convert("RGBA").split()[3].resize((96, 96), Image.NEAREST)
    px = list(a.getdata())  # noqa: deprecated in Pillow 14, still correct here
    n = float(len(px))
    clear = sum(1 for v in px if v < 5) / n
    solid = sum(1 for v in px if v > 250) / n
    return clear, solid


def report(path):
    g, bins = load(path)
    name = os.path.basename(path).replace(".vrm", "")
    imgs = g.get("images", [])
    texs = [t.get("source") for t in g.get("textures", [])]
    cache = {}

    def decode(ti):
        if ti in cache:
            return cache[ti]
        src = texs[ti] if ti is not None and ti < len(texs) else None
        if src is None:
            cache[ti] = (None, "?")
            return cache[ti]
        im = imgs[src]
        try:
            bv = g["bufferViews"][im["bufferView"]]
            o = bv.get("byteOffset", 0)
            d = Image.open(io.BytesIO(bins[o:o + bv["byteLength"]]))
            cache[ti] = (classify(d), im.get("name", "img%d" % src))
        except Exception:                                        # noqa: BLE001
            cache[ti] = (None, im.get("name", "img%d" % src))
        return cache[ti]

    hits = []
    for m in g.get("materials", []):
        if m.get("alphaMode", "OPAQUE") != "OPAQUE":
            continue
        bt = m.get("pbrMetallicRoughness", {}).get("baseColorTexture", {})
        if "index" not in bt:
            continue
        res, iname = decode(bt["index"])
        if not res:
            continue
        clear, solid = res
        # TWO tiers, and the second one is why this tool was rewritten.
        #
        # The first version reported only the cutout-shaped tier -- the rule
        # `build_vrm` uses to DECIDE a mask. On Sayuri it flagged exactly one
        # material, `Lace`, and that was the least important of her five: her
        # EYELASHES were the serious fault, two opaque black slabs covering
        # both eyes, and the gate rejected them because a lash alpha is
        # FEATHERED (46.7% clear, 0.3% solid) rather than two-valued. So was
        # her hair, and so was the mole decal that drew as a pink rectangle on
        # her cheek.
        #
        # "Is this a clean mask?" and "does this material ignore real
        # transparency?" are different questions, and only the second one is
        # the defect. A feathered alpha wants BLEND, or a cutout with a cutoff
        # chosen for it -- not nothing at all.
        if 0.05 <= clear <= 0.90 and (clear + solid) >= 0.80:
            hits.append(("mask", m.get("name", "?"), iname, clear, solid))
        elif clear + (1.0 - solid) > 0.06:
            hits.append(("soft", m.get("name", "?"), iname, clear, solid))

    if hits:
        nm = sum(1 for h in hits if h[0] == "mask")
        print("%-24s %d material(s) OPAQUE over real transparency "
              "(%d cutout-shaped, %d feathered)"
              % (name[:24], len(hits), nm, len(hits) - nm))
        for kind, mn, iname, clear, solid in hits:
            print("    %-5s %-24s %-28s %5.1f%% clear, %5.1f%% solid"
                  % (kind, mn[:24], iname[:28], 100 * clear, 100 * solid))
    else:
        print("%-24s clean" % name[:24])
    return hits


def main():
    files = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".vrm")]
        else:
            files.append(a)
    tot = hit = nmat = 0
    for f in files:
        try:
            h = report(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-24s FAILED: %s" % (os.path.basename(f)[:24], e))
            continue
        tot += 1
        nmat += len(h)
        if h:
            hit += 1
    print("")
    print("%d file(s) read, %d material(s) flagged across %d character(s)"
          % (tot, nmat, hit))


main()
