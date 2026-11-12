# What alpha mode does each material in a .vrm actually carry?
#
#   python vrm_alpha_modes.py <a.vrm> [b.vrm ...]
#
# WHY THIS EXISTS. On 2026-11-12 the exporter was fixed to carry a blend across
# instead of flattening it to a cutout, and the obvious next step was to rebuild
# the six characters whose soft alpha ships as a hard cutout. This script is the
# measurement that said a rebuild alone would change nothing: of the 20 flagged
# materials, only THREE were `alphaMode: BLEND` in their .vrm. The other 17 were
# MASK -- chosen by build_vrm.py's opacity-map path, not by the exporter -- so a
# re-export would have reproduced every cutout exactly and reported success.
#
# The glTF alphaMode is what the Unity importer turns into a RenderType tag, and
# the exporter branches on that tag. So it is the INPUT to the alpha fix, and
# checking it before building is the difference between a rebuild and a rebuild
# that does something.
#
# Read it alongside alpha_sweep_installed.py, which measures the other end: that
# one says what a material's alpha LOOKS like in the installed bundle, this one
# says what the .vrm ASKED FOR. A disagreement between them is the bug.
import json
import os
import struct
import sys


def read_gltf_json(path):
    """The JSON chunk of a .vrm (a GLB), without a glTF library."""
    with open(path, "rb") as f:
        magic, _ver, total = struct.unpack("<III", f.read(12))
        if magic != 0x46546C67:
            raise ValueError("not a GLB/VRM")
        while f.tell() < total:
            length, kind = struct.unpack("<II", f.read(8))
            data = f.read(length)
            if kind == 0x4E4F534A:            # 'JSON'
                return json.loads(data.decode("utf-8"))
    raise ValueError("no JSON chunk")


def report(path):
    js = read_gltf_json(path)
    mats = js.get("materials", [])
    imgs = js.get("images", [])
    texs = js.get("textures", [])
    counts = {}
    rows = []
    for m in mats:
        mode = m.get("alphaMode", "OPAQUE")
        counts[mode] = counts.get(mode, 0) + 1
        base = "-"
        idx = (m.get("pbrMetallicRoughness", {})
                .get("baseColorTexture", {}).get("index"))
        if idx is not None and idx < len(texs):
            src = texs[idx].get("source")
            if src is not None and src < len(imgs):
                base = imgs[src].get("name", "?")
        # mtoon1 is where the VRM add-on keeps the mode it actually exported;
        # `enabled` defaults to false and the mode is inert without it.
        mtoon = m.get("extensions", {}).get("VRMC_materials_mtoon", {})
        rows.append((m.get("name", "?"), mode, m.get("alphaCutoff"),
                     bool(mtoon), base))
    print("== %s  %d materials  %s" % (
        os.path.basename(path), len(mats),
        " ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    for name, mode, cutoff, mtoon, base in rows:
        if mode == "OPAQUE":
            continue
        print("     %-32s %-6s cutoff=%-5s %-6s %s"
              % (name[:32], mode, cutoff, "mtoon" if mtoon else "", base))


def main():
    files = sys.argv[1:]
    if not files:
        print(__doc__ or "usage: vrm_alpha_modes.py <a.vrm> [b.vrm ...]")
        return 2
    bad = 0
    for p in files:
        try:
            report(p)
        except Exception as e:                # noqa: BLE001
            print("== %s  UNREADABLE: %s: %s"
                  % (os.path.basename(p), type(e).__name__, e))
            bad += 1
    # Say how many files were examined. "Nothing non-opaque found" and "nothing
    # was read" print the same thing otherwise.
    print("\n%d file(s) examined, %d unreadable" % (len(files), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
