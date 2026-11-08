import json, struct, sys, os
for path in sys.argv[1:]:
    d = open(path, "rb").read()
    off = 12; js = None
    while off < len(d):
        cl, ct = struct.unpack_from("<II", d, off); off += 8
        if ct == 0x4E4F534A: js = json.loads(d[off:off+cl].decode("utf-8"))
        off += cl
    imgs = js.get("images", [])
    print("== %s: %d images, %d textures, %d materials" % (
        os.path.basename(path), len(imgs), len(js.get("textures", [])), len(js.get("materials", []))))
    for i, im in enumerate(imgs):
        print("   image[%d] name=%s mime=%s" % (i, im.get("name"), im.get("mimeType")))
    for m in js.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        bct = pbr.get("baseColorTexture")
        print("   mat %-22s baseColorTexture=%s  baseColorFactor=%s" % (
            m.get("name"), bct.get("index") if bct else None,
            [round(v, 3) for v in pbr.get("baseColorFactor", [1, 1, 1, 1])]))
