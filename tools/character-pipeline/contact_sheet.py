"""One image of every texture in a folder, labelled. Far cheaper than opening
thirty files one at a time when an archive names them '_01' ... '_27'."""
import os, sys
from PIL import Image, ImageDraw
D, OUT = sys.argv[1:3]
files = sorted(f for f in os.listdir(D) if f.lower().endswith((".png",".jpg",".jpeg",".tga")))
cols, cell = 7, 190
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols*cell, rows*(cell+18)), (40, 40, 44))
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    try:
        im = Image.open(os.path.join(D, f)).convert("RGB")
        im.thumbnail((cell-6, cell-6))
    except Exception:
        continue
    x, y = (i % cols)*cell, (i // cols)*(cell+18)
    sheet.paste(im, (x+3, y+3))
    dr.text((x+3, y+cell+2), f[:28], fill=(230, 230, 230))
sheet.save(OUT)
print("wrote %s  (%d textures)" % (OUT, len(files)))
