# What would ACTUALLY disappear if this material honoured its texture's alpha?
#
#   python -I uv_alpha.py <a.vrm> [b.vrm ...]
#
# WHY THE EXISTING NUMBER IS NOT THIS NUMBER. alpha_sweep_installed.py measures
# the WHOLE texture: what fraction of its pixels are clear. An atlas has large
# unused regions, and unused regions are usually clear, so a shared atlas reads
# as "32% clear" when every one of those clear pixels lies outside the UV
# islands any mesh actually uses. The sweep's figure is an upper bound on the
# damage, not an estimate of it.
#
# This samples the alpha at the material's OWN vertex UVs instead. That is the
# set of texels the geometry can reach, so "47% of the sampled texels are clear"
# means roughly half the material really would vanish, while "0.2%" means
# honouring it changes nothing worth a rebuild.
#
# IT IS AN APPROXIMATION, and the direction of the error is worth knowing: it
# samples at VERTICES, not across triangle interiors, so a small clear hole in
# the middle of a large triangle is under-counted. For hair cards and lace --
# dense geometry, small triangles -- that error is slight. For a 2-triangle
# billboard it would be severe, and such a material should be looked at with a
# render rather than this.
import json
import os
import struct
import sys
from io import BytesIO

from PIL import Image

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}
NUM = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load(path):
    d = open(path, "rb").read()
    off = 12
    js = bin_ = None
    while off < len(d):
        cl, ct = struct.unpack_from("<II", d, off)
        off += 8
        if ct == 0x4E4F534A:
            js = json.loads(d[off:off + cl].decode("utf-8"))
        elif ct == 0x004E4942:
            bin_ = d[off:off + cl]
        off += cl
    return js, bin_


def accessor(js, bin_, idx):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, size = COMP[a["componentType"]]
    n = NUM[a["type"]]
    stride = bv.get("byteStride") or size * n
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    out = []
    for i in range(a["count"]):
        o = start + i * stride
        out.append(struct.unpack_from("<" + fmt * n, bin_, o))
    return out


def report(path):
    js, bin_ = load(path)
    imgs = js.get("images", [])
    texs = js.get("textures", [])
    cache = {}

    def image_for(mat):
        pbr = mat.get("pbrMetallicRoughness", {})
        ti = pbr.get("baseColorTexture", {}).get("index")
        if ti is None or ti >= len(texs):
            return None, "-"
        src = texs[ti].get("source")
        if src is None or src >= len(imgs):
            return None, "?"
        if src in cache:
            return cache[src], imgs[src].get("name", "?")
        bv = js["bufferViews"][imgs[src]["bufferView"]]
        raw = bin_[bv.get("byteOffset", 0):
                   bv.get("byteOffset", 0) + bv["byteLength"]]
        im = Image.open(BytesIO(raw))
        im = im.convert("RGBA") if "A" in im.getbands() else None
        cache[src] = im
        return im, imgs[src].get("name", "?")

    per_mat = {}
    for m in js.get("meshes", []):
        for pr in m.get("primitives", []):
            mi = pr.get("material")
            if mi is None or "TEXCOORD_0" not in pr.get("attributes", {}):
                continue
            per_mat.setdefault(mi, []).append(pr["attributes"]["TEXCOORD_0"])

    print("== %s" % os.path.basename(path))
    print("   %-22s %-6s %7s %7s %7s  %s"
          % ("material", "mode", "clear", "solid", "mid", "texture"))
    any_row = False
    for mi, uv_accs in sorted(per_mat.items()):
        mat = js["materials"][mi]
        if mat.get("alphaMode", "OPAQUE") != "OPAQUE":
            continue                      # already honouring something
        im, tname = image_for(mat)
        if im is None:
            continue                      # no base map, or it has no alpha
        w, h = im.size
        px = im.load()
        clear = solid = mid = 0
        for ai in uv_accs:
            for u, v in accessor(js, bin_, ai):
                x = int(u % 1.0 * (w - 1))
                y = int((1.0 - v % 1.0) * (h - 1))
                a = px[x, y][3]
                if a <= 12:
                    clear += 1
                elif a >= 243:
                    solid += 1
                else:
                    mid += 1
        n = clear + solid + mid
        if not n:
            continue
        any_row = True
        print("   %-22s %-6s %6.1f%% %6.1f%% %6.1f%%  %s  (%d verts)"
              % (mat.get("name", "?")[:22], "OPAQUE", 100.0 * clear / n,
                 100.0 * solid / n, 100.0 * mid / n, tname[:28], n))
    if not any_row:
        print("   no opaque material with an alpha-carrying base map")


def main():
    if len(sys.argv) < 2:
        print("usage: uv_alpha.py <a.vrm> [b.vrm ...]")
        return 2
    for p in sys.argv[1:]:
        try:
            report(p)
        except Exception as e:                       # noqa: BLE001
            print("== %s  UNREADABLE: %s: %s"
                  % (os.path.basename(p), type(e).__name__, e))
    print("\n%d file(s) examined" % (len(sys.argv) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
