# -*- coding: utf-8 -*-
"""Where does a cape's WEIGHT actually hang -- on the chest, or through the clavicles?

    python cape_weight_anchor.py <file.vrm> [cape-name-substring]

A hierarchy survey says which bones are PARENTED under what. That is not the same question as
where the weight is, and the difference decides what a fix has to do:

  (a) cape bones parented under the clavicle, mantle weighted to those cape bones
  (b) mantle vertices weighted DIRECTLY to the clavicle bones, parenting incidental
  (c) both

Re-parenting and re-weighting are different operations with different risks -- re-parenting a
bone inside a bundle without fixing its local transform MOVES geometry -- so "copy how Power
Girl's is built" cannot be honoured until it is known which of the three hers is.

NO NAME MATCHING FOR THE SHOULDER. The clavicles are taken from the VRM humanoid map
(`leftShoulder` / `rightShoulder` -> node index), which is the rig's own declaration. Bone names
here run to `fml_un_L_clav`, `fml_un_L_capeClav_a` and `fml_un_L_samurai_claviclePad_1`, and a
substring match on "clav" collects all three -- two of which are not the shoulder joint. A name
matcher on this project has already "found" bones an earlier run of itself invented.

Reads the glb directly rather than through Blender: the skin's JOINTS_0/WEIGHTS_0 accessors are
what the engine binds with, and going via an importer adds a translation nobody needs here.
"""
import json
import struct
import sys

import numpy as np

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb(path):
    with open(path, "rb") as f:
        magic, _ver, _len = struct.unpack("<III", f.read(12))
        if magic != 0x46546C67:
            raise ValueError("not a glb: %s" % path)
        js = None
        bin_ = b""
        while True:
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            clen, ctype = struct.unpack("<II", hdr)
            data = f.read(clen)
            if ctype == 0x4E4F534A:
                js = json.loads(data.decode("utf-8"))
            elif ctype == 0x004E4942:
                bin_ = data
    return js, bin_


def accessor(js, bin_, idx):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, size = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or (size * n)
    out = np.zeros((a["count"], n), dtype=np.float64)
    raw = bin_
    for i in range(a["count"]):
        base = off + i * stride
        out[i] = struct.unpack_from("<" + fmt * n, raw, base)
    if a.get("normalized") and fmt in ("B", "H"):
        out /= (255.0 if fmt == "B" else 65535.0)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else "cape"
    js, bin_ = load_glb(path)
    nodes = js.get("nodes", [])
    name = [n.get("name", "node%d" % i) for i, n in enumerate(nodes)]

    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i

    # --- the shoulders, from the rig's own humanoid declaration -----------------------------
    hum = {}
    ext = js.get("extensions", {})
    vrm0 = ext.get("VRM", {}).get("humanoid", {}).get("humanBones")
    vrm1 = ext.get("VRMC_vrm", {}).get("humanoid", {}).get("humanBones")
    if vrm0:
        for hb in vrm0:
            hum[hb.get("bone")] = hb.get("node")
    elif vrm1:
        for k, v in vrm1.items():
            hum[k] = v.get("node")
    shoulders = {hum.get("leftShoulder"), hum.get("rightShoulder")} - {None}
    chestish = {hum.get(k) for k in ("chest", "upperChest", "spine", "hips")} - {None}
    print("humanoid map: %d bones. shoulders=%s  chest-ish=%s"
          % (len(hum), sorted(name[s] for s in shoulders),
             sorted(name[c] for c in chestish)))
    if not shoulders:
        print("NO SHOULDER IN THE HUMANOID MAP -- this file cannot answer the question, and a")
        print("name match would be guessing. Stopping.")
        return 1

    def through_shoulder(node):
        """Does this node's ancestry pass through a humanoid shoulder?"""
        seen = 0
        cur = node
        while cur in parent and seen < 200:
            cur = parent[cur]
            seen += 1
            if cur in shoulders:
                return True
        return False

    # --- weights per skin ---------------------------------------------------------------------
    for mi, mesh in enumerate(js.get("meshes", [])):
        for pi, prim in enumerate(mesh.get("primitives", [])):
            attrs = prim.get("attributes", {})
            if "JOINTS_0" not in attrs or "WEIGHTS_0" not in attrs:
                continue
            skin_idx = None
            for ni, n in enumerate(nodes):
                if n.get("mesh") == mi and "skin" in n:
                    skin_idx = n["skin"]
                    break
            if skin_idx is None:
                continue
            joints = js["skins"][skin_idx]["joints"]
            J = accessor(js, bin_, attrs["JOINTS_0"]).astype(int)
            W = accessor(js, bin_, attrs["WEIGHTS_0"])

            tot = {}
            for vi in range(J.shape[0]):
                for k in range(J.shape[1]):
                    w = W[vi, k]
                    if w <= 0:
                        continue
                    nd = joints[J[vi, k]]
                    tot[nd] = tot.get(nd, 0.0) + w
            if not tot:
                continue

            cape = {nd: w for nd, w in tot.items() if want.lower() in name[nd].lower()}
            if not cape:
                continue

            # RESTRICT TO CAPE VERTICES. "Weight directly on the shoulder" summed over the whole
            # mesh counts the wearer's shoulder as if it were the cape: Power Girl's cape mesh is
            # only 52% cape-bone weight, so the other half is body and its clavicle weight is not
            # evidence about how a cape is anchored.
            cape_nodes = set(cape)
            is_cape_v = np.zeros(J.shape[0], dtype=bool)
            for vi in range(J.shape[0]):
                for k in range(J.shape[1]):
                    if W[vi, k] > 0 and joints[J[vi, k]] in cape_nodes:
                        is_cape_v[vi] = True
                        break
            direct = 0.0
            cape_v_total = 0.0
            for vi in np.nonzero(is_cape_v)[0]:
                for k in range(J.shape[1]):
                    w = W[vi, k]
                    if w <= 0:
                        continue
                    cape_v_total += w
                    if joints[J[vi, k]] in shoulders:
                        direct += w
            print("")
            print("  CAPE VERTICES: %d of %d, carrying %.2f weight"
                  % (int(is_cape_v.sum()), J.shape[0], cape_v_total))
            print("  of that, DIRECTLY on a shoulder bone   %10.2f  (%.1f%% of cape-vertex weight)"
                  % (direct, 100 * direct / max(cape_v_total, 1e-9)))
            via = sum(w for nd, w in cape.items() if through_shoulder(nd))
            other = sum(cape.values()) - via
            allw = sum(tot.values())

            print("")
            print("mesh %-22s prim %d   %d verts   total weight %.1f"
                  % (mesh.get("name", "?")[:22], pi, J.shape[0], allw))
            print("  weight on '%s' bones            %10.2f  (%.1f%% of mesh)"
                  % (want, sum(cape.values()), 100 * sum(cape.values()) / allw))
            print("  ...of which ancestry passes a SHOULDER %10.2f  (%.1f%% of cape weight)"
                  % (via, 100 * via / max(sum(cape.values()), 1e-9)))
            print("  ...of which it does not                %10.2f  (%.1f%%)"
                  % (other, 100 * other / max(sum(cape.values()), 1e-9)))
            print("  weight DIRECTLY on the shoulder bones  %10.2f  (%.1f%% of mesh)"
                  % (direct, 100 * direct / allw))
            # Both shares are against CAPE-VERTEX weight now, so they are comparable, and the
            # 1% floor stops a trace amount being reported as a structural choice -- the first
            # version called 21.91 of 2029 "(b) weighted directly to the clavicle".
            vs = 100 * via / max(sum(cape.values()), 1e-9)
            ds = 100 * direct / max(cape_v_total, 1e-9)
            verdict = ("(c) BOTH" if vs >= 1 and ds >= 1 else
                       "(a) parented under the clavicle" if vs >= 1 else
                       "(b) weighted DIRECTLY to the clavicle" if ds >= 1 else
                       "NEITHER -- hangs entirely off the chest")
            print("  => %s   (parented %.1f%%, direct %.1f%%)" % (verdict, vs, ds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
