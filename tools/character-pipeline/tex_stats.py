import os, sys, bpy
D = sys.argv[sys.argv.index("--") + 1]
for f in sys.argv[sys.argv.index("--") + 2:]:
    img = bpy.data.images.load(os.path.join(D, f))
    img.scale(32, 32)
    px = list(img.pixels)
    n = len(px) // 4
    rgba = [sum(px[i::4]) / n for i in range(4)]
    distinct = len({tuple(round(v, 2) for v in px[i*4:i*4+3]) for i in range(n)})
    print("  %-52s mean=%s distinct_colours=%d" % (f, [round(v, 3) for v in rgba], distinct))
print("DONE")
