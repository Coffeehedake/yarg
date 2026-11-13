# One row per character: before | after | the difference, cropped to the
# bounding box of what actually changed, so each tile shows the change rather
# than a whole figure with a few altered pixels in it.
#
# A character whose pair is identical gets no row and is listed as such -- an
# empty tile would read as a render that failed.
import os, sys
from PIL import Image, ImageChops, ImageDraw

R, JOBS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
VIEWS = ("front", "side", "bodyfront", "bodyside")
TH = 8
rows = []; nil = []
for line in open(JOBS, encoding="utf-8"):
    if not line.strip(): continue
    name = line.rstrip("\r\n").split("|")[0]
    safe = "".join(c for c in name if c not in '/\:*?"<>|')
    best = None
    for v in VIEWS:
        a = os.path.join(R, "%s-%s-before.png" % (safe, v))
        b = os.path.join(R, "%s-%s-after.png" % (safe, v))
        if not (os.path.exists(a) and os.path.exists(b)): continue
        ia = Image.open(a).convert("RGB"); ib = Image.open(b).convert("RGB")
        d = ImageChops.difference(ia, ib).convert("L")
        mask = d.point(lambda x: 255 if x > TH else 0)
        bb = mask.getbbox()
        if not bb: continue
        px = mask.load(); w, h = mask.size
        n = sum(1 for y in range(bb[1], bb[3]) for x in range(bb[0], bb[2]) if px[x, y])
        if best is None or n > best[0]: best = (n, ia, ib, mask, bb, v, w * h)
    if best is None: nil.append(name); continue
    n, ia, ib, mask, bb, v, tot = best
    # Normalise every crop to the SAME square box, centred on the change.
    # Cropping tightly to the bounding box makes a 1-pixel-tall change (a
    # webshooter on a wrist) into a strip thousands of pixels wide once it is
    # scaled to a common row height, which buried every other row.
    side = max(bb[2]-bb[0], bb[3]-bb[1], 150) + 28
    side = min(side, min(ia.width, ia.height))
    ccx = (bb[0]+bb[2])//2; ccy = (bb[1]+bb[3])//2
    x0 = min(max(0, ccx - side//2), ia.width - side)
    y0 = min(max(0, ccy - side//2), ia.height - side)
    box = (x0, y0, x0+side, y0+side)
    ca, cb = ia.crop(box), ib.crop(box)
    cm = Image.merge("RGB", (mask.crop(box), mask.crop(box).point(lambda x: x//3), mask.crop(box).point(lambda x: x//3)))
    rows.append((name, v, 100.0*n/tot, ca, cb, cm))

TH_H = 190
tiles = []
for name, v, pct, ca, cb, cm in rows:
    sc = TH_H / ca.height
    w = max(40, int(ca.width * sc))
    tiles.append((name, v, pct, [im.resize((w, TH_H), Image.LANCZOS) for im in (ca, cb, cm)]))

GAP, LAB, HDR = 8, 150, 26
W = LAB + max(sum(t[3][i].width for i in range(3)) + GAP*3 for t in tiles) + GAP
H = HDR + sum(TH_H + GAP for t in tiles) + GAP
sheet = Image.new("RGB", (W, H), (18, 18, 20))
dr = ImageDraw.Draw(sheet)
dr.text((GAP, 8), "back-face culling: BEFORE  |  AFTER  |  what changed (red)   -- cropped to the change",
        fill=(235, 235, 235))
y = HDR
for name, v, pct, ims in tiles:
    dr.text((GAP, y + TH_H//2 - 14), name[:20], fill=(235, 235, 235))
    dr.text((GAP, y + TH_H//2 + 2), "%s  %.3f%%" % (v, pct), fill=(150, 150, 155))
    x = LAB
    for im in ims:
        sheet.paste(im, (x, y)); x += im.width + GAP
    y += TH_H + GAP
sheet.save(OUT)
print("wrote %s  (%dx%d)  %d rows" % (OUT, W, H, len(tiles)))
if nil: print("NO VISIBLE CHANGE in any of the four views: " + ", ".join(nil))
