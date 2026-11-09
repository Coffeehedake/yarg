"""Connected islands of a built .vrm, with the bone that carries each.

A prop sharing a mesh with the body has no name of its own, but it is its own
connected island and it hangs off one bone. Both are readable from the file.
"""
import json, struct, sys, collections
CT = {5120:("b",1),5121:("B",1),5122:("h",2),5123:("H",2),5125:("I",4),5126:("f",4)}
NC = {"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}
d = open(sys.argv[1], "rb").read()
off, g, bins = 12, None, None
while off < len(d):
    ln, ty = struct.unpack_from("<II", d, off)
    ch = d[off+8:off+8+ln]
    if ty == 0x4E4F534A: g = json.loads(ch.decode("utf-8"))
    elif ty == 0x004E4942: bins = ch
    off += 8 + ln + ((4-ln%4)%4)
def read(i):
    a = g["accessors"][i]; bv = g["bufferViews"][a["bufferView"]]
    base = bv.get("byteOffset",0)+a.get("byteOffset",0)
    f,sz = CT[a["componentType"]]; n = NC[a["type"]]
    st = bv.get("byteStride") or sz*n
    return [struct.unpack_from("<"+f*n, bins, base+k*st) for k in range(a["count"])]
names = [n.get("name","?") for n in g["nodes"]]
want = sys.argv[2].lower() if len(sys.argv) > 2 else ""
for mi, m in enumerate(g["meshes"]):
    if want and want not in m.get("name","").lower():
        continue
    skin = next((n.get("skin") for n in g["nodes"] if n.get("mesh")==mi), None)
    joints = g["skins"][skin]["joints"] if skin is not None else []
    for pi, pr in enumerate(m["primitives"]):
        P = read(pr["attributes"]["POSITION"])
        I = [x[0] for x in read(pr["indices"])]
        # weld by position so a split-but-touching prop counts as one island
        key = {}
        rep = list(range(len(P)))
        for i, p in enumerate(P):
            k = (round(p[0],5), round(p[1],5), round(p[2],5))
            if k in key: rep[i] = key[k]
            else: key[k] = i
        par = {}
        def find(a):
            while par.get(a, a) != a: a = par[a]
            return a
        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb: par[ra] = rb
        for t in range(0, len(I), 3):
            a, b, c = rep[I[t]], rep[I[t+1]], rep[I[t+2]]
            uni(a, b); uni(b, c)
        comp = collections.defaultdict(list)
        for i in range(len(P)):
            comp[find(rep[i])].append(i)
        J = read(pr["attributes"]["JOINTS_0"]) if "JOINTS_0" in pr["attributes"] else None
        W = read(pr["attributes"]["WEIGHTS_0"]) if J else None
        rows = []
        for root, vs in comp.items():
            xs = [P[i][0] for i in vs]; ys = [P[i][1] for i in vs]; zs = [P[i][2] for i in vs]
            bone = "-"
            if J:
                acc = collections.Counter()
                for i in vs:
                    for j, w in zip(J[i], W[i]):
                        if w > 0.001: acc[names[joints[j]]] += w
                bone = acc.most_common(1)[0][0] if acc else "-"
            rows.append((len(vs), bone, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
        rows.sort(key=lambda r: -r[0])
        print("%s prim %d: %d islands" % (m.get("name","?"), pi, len(rows)))
        for i, r in enumerate(rows[:14]):
            print("   %2d %6d verts  on %-22s x %6.2f..%5.2f  y %6.2f..%5.2f  z %6.2f..%5.2f"
                  % (i, r[0], r[1][:22], r[2], r[3], r[4], r[5], r[6], r[7]))
