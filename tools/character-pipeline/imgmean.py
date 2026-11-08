import sys, os, bpy
D = sys.argv[sys.argv.index("--")+1]
for f in sorted(os.listdir(D)):
    if not f.lower().endswith((".png",".jpg",".jpeg",".tga",".bmp")): continue
    im = bpy.data.images.load(os.path.join(D,f))
    px = list(im.pixels)
    n = len(px)//4
    step = max(1, n//20000)
    r=g=b=0.0; c=0
    for i in range(0, n, step):
        r+=px[i*4]; g+=px[i*4+1]; b+=px[i*4+2]; c+=1
    print("%-55s %dx%d mean=%.3f/%.3f/%.3f" % (f[:55], im.size[0], im.size[1], r/c, g/c, b/c))
    bpy.data.images.remove(im)
print("DONE")
