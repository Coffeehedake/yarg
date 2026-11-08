import json, struct, sys, os
for path in sys.argv[1:]:
    d = open(path, "rb").read()
    off = 12; js = None
    while off < len(d):
        cl, ct = struct.unpack_from("<II", d, off); off += 8
        if ct == 0x4E4F534A: js = json.loads(d[off:off+cl].decode("utf-8"))
        off += cl
    nodes = js.get("nodes", [])
    skins = js.get("skins", [])
    skinned = sum(1 for n in nodes if "skin" in n)
    static = [n.get("name","?") for n in nodes if "mesh" in n and "skin" not in n]
    print("%-18s nodes=%-4d meshes=%-3d skins=%-3d skinnednodes=%-3d joints=%s" % (
        os.path.basename(path), len(nodes), len(js.get("meshes", [])), len(skins),
        skinned, [len(s.get("joints", [])) for s in skins]))
    if static:
        print("   STATIC MESH NODES (will never animate):", static)
    hum = js.get("extensions", {}).get("VRMC_vrm", {}).get("humanoid", {}).get("humanBones", {})
    print("   humanBones mapped: %d  -> %s" % (len(hum), "ok" if len(hum) >= 15 else "TOO FEW"))
