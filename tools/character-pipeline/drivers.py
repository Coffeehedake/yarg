"""Which bones drive each mesh, and is each of those bones actually driven?

AND WHETHER THE MESH IS SKINNED AT ALL. This reported Lola Bunny clean while
three of her four meshes had skin=None -- both sets of teeth and her hair,
static nodes that nothing could ever move. It only examined meshes carrying
JOINTS_0, which is to say it looked exclusively at the meshes capable of
failing its test, and called the silence a pass.

A vertex can carry full weight and still never move: if its bone is not a
humanoid bone, not in a spring chain, and not a descendant of one, nothing in
the game ever rotates it. The mesh then hangs in space while the character
moves around it, which looks like a rigging failure and measures as perfect.
"""
import json
import struct
import sys

CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
      5125: ("I", 4), 5126: ("f", 4)}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
path = sys.argv[1]
want = sys.argv[2].lower() if len(sys.argv) > 2 else ""

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


def read(i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    f, sz = CT[a["componentType"]]
    n = NC[a["type"]]
    stride = bv.get("byteStride") or sz * n
    scale = {5121: 255.0, 5123: 65535.0}.get(a["componentType"], 1.0)
    # JOINTS_0 is an unsigned INDEX, not a normalised value: dividing it by
    # 255 collapsed every joint to 0 and made every mesh look like it hung off
    # one undriven root bone. Trust the accessor flag only.
    norm = bool(a.get("normalized"))
    out = []
    for k in range(a["count"]):
        v = struct.unpack_from("<" + f * n, bins, base + k * stride)
        out.append(tuple(x / scale for x in v) if norm and scale != 1.0 else v)
    return out


name = [n.get("name", "?") for n in g["nodes"]]
parent = {}
for i, n in enumerate(g["nodes"]):
    for c in n.get("children", []):
        parent[c] = i
hum = g["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
humset = set(v["node"] for v in hum.values())
springs = g.get("extensions", {}).get("VRMC_springBone", {}).get("springs", [])
springset = set(j["node"] for s in springs for j in s.get("joints", []))


def driven(i):
    """Does anything ever move this bone? Walk up to a humanoid or spring bone."""
    seen = set()
    while i is not None and i not in seen:
        seen.add(i)
        if i in humset or i in springset:
            return True
        i = parent.get(i)
    return False


for node in g["nodes"]:
    if "mesh" not in node:
        continue
    nm = node.get("name", "?")
    if "skin" not in node:
        # Not skinned AT ALL, which is worse than bad weights and was being
        # passed over in silence. Report it first: a static node cannot move,
        # whatever the skeleton does.
        if not want or want in nm.lower():
            n_v = sum(g["accessors"][p_["attributes"]["POSITION"]]["count"]
                      for p_ in g["meshes"][node["mesh"]]["primitives"])
            print("%-36s NOT SKINNED -- %d verts that nothing can move"
                  % (nm, n_v))
        continue
    if want and want not in nm.lower():
        continue
    joints = g["skins"][node["skin"]]["joints"]
    tally = {}
    for prim in g["meshes"][node["mesh"]].get("primitives", []):
        at = prim["attributes"]
        if "JOINTS_0" not in at:
            continue
        js, ws = read(at["JOINTS_0"]), read(at["WEIGHTS_0"])
        for j4, w4 in zip(js, ws):
            for j, w in zip(j4, w4):
                if w > 0.01:
                    tally[joints[int(j)]] = tally.get(joints[int(j)], 0.0) + w
    if not tally:
        continue
    tot = sum(tally.values())
    stuck = [(v, k) for k, v in tally.items() if not driven(k)]
    stuck.sort(reverse=True)
    print("%-36s %d bones%s" % (nm[:36], len(tally),
                                "" if not stuck else
                                "  <-- %.1f%% of its weight is on bones nothing drives"
                                % (100.0 * sum(v for v, _ in stuck) / tot)))
    for v, k in stuck[:6]:
        print("      %-28s %5.1f%%" % (name[k][:28], 100.0 * v / tot))
