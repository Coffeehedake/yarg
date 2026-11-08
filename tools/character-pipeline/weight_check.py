"""Do any vertices actually have weight on the named bones?

A bone can be present in the skin's joint list and still drive nothing. Read
the JOINTS_0 / WEIGHTS_0 accessors and count real influence."""
import json
import os
import struct
import sys

PATH, PATTERN = sys.argv[1], sys.argv[2]
d = open(PATH, "rb").read()
off, js, bin_chunk = 12, None, None
while off < len(d):
    cl, ct = struct.unpack_from("<II", d, off)
    off += 8
    if ct == 0x4E4F534A:
        js = json.loads(d[off:off + cl].decode("utf-8"))
    elif ct == 0x004E4942:
        bin_chunk = d[off:off + cl]
    off += cl

nodes = js["nodes"]
skin = js["skins"][0]
joints = skin["joints"]
want = {ji for ji, ni in enumerate(joints)
        if PATTERN.lower() in (nodes[ni].get("name") or "").lower()}
print("%s: %d joints, %d of them match %r" % (os.path.basename(PATH), len(joints), len(want), PATTERN))
if not want:
    raise SystemExit("none of the skin's joints match - the bones are not in the skin")

CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read(ai):
    a = js["accessors"][ai]
    bv = js["bufferViews"][a["bufferView"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    fmt, sz = CT[a["componentType"]]
    n = NC[a["type"]]
    stride = bv.get("byteStride") or sz * n
    out = []
    for i in range(a["count"]):
        out.append(struct.unpack_from("<" + fmt * n, bin_chunk, base + i * stride))
    return out


hit_verts = 0
total = 0
max_w = 0.0
for m in js["meshes"]:
    for p in m["primitives"]:
        at = p["attributes"]
        if "JOINTS_0" not in at or "WEIGHTS_0" not in at:
            continue
        J, W = read(at["JOINTS_0"]), read(at["WEIGHTS_0"])
        norm = js["accessors"][at["WEIGHTS_0"]]["componentType"] != 5126
        for jv, wv in zip(J, W):
            total += 1
            s = 0.0
            for j, w in zip(jv, wv):
                if j in want:
                    fw = w / 65535.0 if norm and w > 1 else float(w)
                    s += fw
            if s > 0.01:
                hit_verts += 1
                max_w = max(max_w, s)
print("vertices with real weight on those bones: %d of %d (max combined weight %.3f)"
      % (hit_verts, total, max_w))
