# -*- coding: utf-8 -*-
"""Bake a glTF joint's SCALE into its subtree, so no importer can drop it.

    python glb_bake_joint_scale.py <in.glb> <out.glb>

A Blender rest bone has a head, a tail and a roll and NO SCALE, so a glTF
joint carrying one cannot survive `import_scene.gltf`. Prix's `hairAll` carries
22.085905; her hair imports at 3.9 x 3.8 x 6.3 mm at the world origin and she
ships bald with a 2 cm pellet of hair at her ankles. The Sketchfab Blender
plugin calls the same importer, so it loses the same thing.

WHY THIS AND NOT A FIX AFTER IMPORT. The first attempt restored the scale in
the builder by learning the GLB->Blender mapping from the bones the importer
placed correctly, then applying it to the ones it had not. That rests on the
mapping being a SIMILARITY, and it is not: fitted over 115 control joints it
leaves 124 mm of residual, with `FemaleBody_L_eye_J_0104` 421.9 mm out and a
finger joint 188.0 mm out, on a 434 mm span. Blender does not place bones from
the node hierarchy alone, so there is no one transform to recover. Rewriting
the file is the honest fix: it works in glTF space, where every quantity is
defined, and it fixes the asset for every tool rather than for ours.

THE TRANSFORMATION, which leaves the rendered result identical:

    a skinned vertex is  sum_i w_i * (world(joint_i) * IBM_i) * v

Removing a scale `s` from joint J changes world() for J and everything under
it. Multiply every descendant's local translation by `s` and the TRANSLATIONS
all come back to where they were, while the linear part loses its factor of
`s`. The inverse bind matrices then carry the correction:

    IBM' = inverse(world') * world * IBM

computed per joint, so `world' * IBM'` equals `world * IBM` exactly and no
vertex moves. Afterwards no node in the file has a scale for an importer to
discard.

The inverse bind matrices are a contiguous float32 block in one bufferView, so
they are rewritten IN PLACE and the binary chunk keeps its length; only the
JSON chunk changes size. The tool verifies its own arithmetic before writing:
every joint matrix is recomposed and compared against the original, and it
refuses if any disagrees by more than a micrometre.
"""
import json
import struct
import sys

import numpy as np


def _read(path):
    with open(path, "rb") as f:
        blob = f.read()
    magic, ver, total = struct.unpack_from("<4sII", blob, 0)
    if magic != b"glTF":
        raise SystemExit("not a GLB: %r" % magic)
    off = 12
    js = None
    bin_lo = bin_hi = None
    while off + 8 <= len(blob):
        clen, ctype = struct.unpack_from("<II", blob, off)
        body = off + 8
        if ctype == 0x4E4F534A:
            js = json.loads(blob[body:body + clen].decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_lo, bin_hi = body, body + clen
        off = body + clen
    if js is None or bin_lo is None:
        raise SystemExit("GLB is missing a JSON or BIN chunk")
    return blob, js, bin_lo, bin_hi, ver


def _mat(node):
    if node.get("matrix"):
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T
    M = np.eye(4)
    if node.get("rotation"):
        x, y, z, w = node["rotation"]
        M[:3, :3] = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ])
    if node.get("scale"):
        M[:3, :3] = M[:3, :3] @ np.diag(node["scale"])
    if node.get("translation"):
        M[:3, 3] = node["translation"]
    return M


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    blob, js, bin_lo, bin_hi, ver = _read(src)
    nodes = js.get("nodes") or []
    parent = {}
    for i, n in enumerate(nodes):
        for c in (n.get("children") or []):
            parent[c] = i

    def world_of(local):
        w = {}

        def go(i):
            if i in w:
                return w[i]
            p = parent.get(i)
            w[i] = (go(p) @ local[i]) if p is not None else local[i]
            return w[i]
        for i in range(len(nodes)):
            go(i)
        return w

    joints = set()
    for sk in (js.get("skins") or []):
        joints.update(sk.get("joints") or [])
    scaled = [i for i in joints
              if nodes[i].get("scale")
              and max(abs(v - 1.0) for v in nodes[i]["scale"]) > 1e-9]
    if not scaled:
        print("no joint carries a scale; nothing to bake")
        return 1

    local0 = [_mat(n) for n in nodes]
    world0 = world_of(local0)

    # Rewrite: drop the scale on each scaled joint, and multiply every
    # descendant's translation by it. Uniform scales only -- a non-uniform one
    # does not commute with the rotations below it and would need the whole
    # subtree re-expressed, which this deliberately will not attempt.
    for j in scaled:
        sc = nodes[j]["scale"]
        if max(sc) - min(sc) > 1e-9:
            print("ABORT: joint %d %r has a NON-UNIFORM scale %s; baking that "
                  "would need the subtree re-expressed and this tool will not "
                  "guess" % (j, nodes[j].get("name"), sc))
            return 2
        s = float(sc[0])
        sub = []
        stack = list(nodes[j].get("children") or [])
        while stack:
            k = stack.pop()
            sub.append(k)
            stack.extend(nodes[k].get("children") or [])
        for k in sub:
            if nodes[k].get("matrix"):
                M = _mat(nodes[k])
                M[:3, 3] *= s
                nodes[k]["matrix"] = list(M.T.reshape(16))
            elif nodes[k].get("translation"):
                nodes[k]["translation"] = [v * s for v in
                                           nodes[k]["translation"]]
        nodes[j].pop("scale", None)
        print("baked scale %.6f from joint %d %r into %d descendant(s)"
              % (s, j, nodes[j].get("name"), len(sub)))

    local1 = [_mat(n) for n in nodes]
    world1 = world_of(local1)

    # IBM' = inverse(world') * world * IBM, per joint, so that
    # world' * IBM' == world * IBM and no vertex moves.
    data = bytearray(blob)
    acc = js.get("accessors") or []
    bvs = js.get("bufferViews") or []
    worst = 0.0
    nmat = 0
    for sk in (js.get("skins") or []):
        ai = sk.get("inverseBindMatrices")
        if ai is None:
            continue
        A = acc[ai]
        if A.get("componentType") != 5126 or A.get("type") != "MAT4":
            print("ABORT: inverseBindMatrices accessor %d is not float32 MAT4"
                  % ai)
            return 2
        bv = bvs[A["bufferView"]]
        base = bin_lo + bv.get("byteOffset", 0) + A.get("byteOffset", 0)
        for n, jid in enumerate(sk.get("joints") or []):
            off = base + n * 64
            ibm = np.frombuffer(bytes(data[off:off + 64]),
                                dtype="<f4").reshape(4, 4).T.astype(np.float64)
            new = np.linalg.inv(world1[jid]) @ world0[jid] @ ibm
            chk = world1[jid] @ new - world0[jid] @ ibm
            worst = max(worst, float(np.abs(chk).max()))
            data[off:off + 64] = np.asarray(
                new.T.reshape(16), dtype="<f4").tobytes()
            nmat += 1
    print("rewrote %d inverse bind matrix/matrices; worst joint-matrix "
          "disagreement %.3e m" % (nmat, worst))
    if worst > 1e-6:
        print("ABORT: the recomposed joint matrices disagree by more than a "
              "micrometre, so this would move geometry. Nothing written.")
        return 2

    jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
    jb += b" " * ((4 - len(jb) % 4) % 4)
    binb = bytes(data[bin_lo:bin_hi])
    binb += b"\x00" * ((4 - len(binb) % 4) % 4)
    out = bytearray()
    out += struct.pack("<4sII", b"glTF", ver, 12 + 8 + len(jb) + 8 + len(binb))
    out += struct.pack("<II", len(jb), 0x4E4F534A) + jb
    out += struct.pack("<II", len(binb), 0x004E4942) + binb
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s (%d bytes, was %d)" % (dst, len(out), len(blob)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
