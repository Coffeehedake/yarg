import json, struct, sys, os
for path in sys.argv[1:]:
    d = open(path, "rb").read()
    off = 12; js = None
    while off < len(d):
        cl, ct = struct.unpack_from("<II", d, off); off += 8
        if ct == 0x4E4F534A: js = json.loads(d[off:off+cl].decode("utf-8"))
        off += cl
    print("== " + os.path.basename(path))
    for m in js.get("materials", []):
        mt = m.get("extensions", {}).get("VRMC_materials_mtoon", {})
        print("   %-26s alphaMode=%-7s cutoff=%-5s doubleSided=%s %s" % (
            m.get("name"), m.get("alphaMode", "OPAQUE"), m.get("alphaCutoff", "-"),
            m.get("doubleSided", False), "(mtoon)" if mt else ""))
