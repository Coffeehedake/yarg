"""Measure a .vrm's real-world extent from its POSITION accessors and node scales."""
import json
import struct
import sys

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        d = f.read()
    off = 12
    js = None
    while off < len(d):
        cl, ct = struct.unpack_from("<II", d, off)
        off += 8
        if ct == 0x4E4F534A:
            js = json.loads(d[off:off + cl].decode("utf-8"))
        off += cl

    lo = [1e18] * 3
    hi = [-1e18] * 3
    accs = js.get("accessors", [])
    for m in js.get("meshes", []):
        for p in m.get("primitives", []):
            ai = p.get("attributes", {}).get("POSITION")
            if ai is None:
                continue
            a = accs[ai]
            if "min" in a and "max" in a:
                for i in range(3):
                    lo[i] = min(lo[i], a["min"][i])
                    hi[i] = max(hi[i], a["max"][i])

    size = [hi[i] - lo[i] for i in range(3)]
    scales = [n.get("scale") for n in js.get("nodes", []) if n.get("scale")]
    root_scales = {tuple(round(v, 5) for v in s) for s in scales}
    print("%-26s raw mesh extent  x=%.3f y=%.3f z=%.3f" % (path.split("\\")[-1], *size))
    print("%-26s non-unit node scales present: %s" % ("", sorted(root_scales)[:4] if root_scales else "none"))
