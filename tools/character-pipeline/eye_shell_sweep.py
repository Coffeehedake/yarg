# -*- coding: utf-8 -*-
"""Is an opaque shell parked in front of anybody else's eyes?

    python eye_shell_sweep.py <dir-of-yargchar | file.yargchar ...>

WHY THIS EXISTS. Three characters have now shipped with a flat lens covering
perfect eyes, and each was found by accident rather than by a check:

  Alice Ivy  EyeMoisture_Left/_Right, black at the source's own alpha 0.051,
             flattened to baseColorFactor [0,0,0,1] -- a black disc per eye
  Ariel      Cornea, alpha max 0.051 under a 0.50 cutoff -- deliberate, left
  Prix       aiStandardSurface4 on L_iris/R_iris, opaque, wearing her SKIN
             atlas -- blank featureless eyes

NO EXISTING SWEEP CATCHES IT. `alpha_sweep_installed.py` keys on a material's
base MAP, so a bare colour factor is invisible to it (that is how Alice's disc
survived every check), and a shell that DOES carry a map -- Prix's, wearing the
wrong atlas -- looks like an ordinary opaque material. The thing the three have
in common is not their alpha and not their texture. It is that a mesh whose
NAME says it is an eye covering is drawn solid.

So this reads the geometry: meshes whose names look like an eye shell, their
material's alpha mode, and whether the material is opaque. Every hit is a
CANDIDATE -- a mesh called `Cornea` that is correctly opaque because it is a
cartoon eye painted on a solid ball is a perfectly ordinary thing, and only a
render can tell the two apart. The point is to have the list at all.

A character with no eye-shell mesh prints a line too, because "no shells" and
"never looked" read the same otherwise.

IT READS `.vrm` FILES TOO, AND IT HAS TO. A bundle RENAMES every material to
`<Character>_<n>`, so only MESH names survive the export -- and Alice Ivy's
shell was a MATERIAL (`EyeMoisture_Left`) inside an ordinarily-named mesh
(`Custom_Eye`). The bundle pass cannot see that shape of it at all. The `.vrm`
keeps the authored material names, so pass the `.vrm` files as well where they
still exist; 30 of the 65 do.
"""
import json
import os
import re
import struct
import sys

import UnityPy

# Names that mean "a layer in front of the eye". `eye` alone is far too broad:
# it matches the eyeball itself, eyelashes, eyebrows and eyelids, and a sweep
# that flags the eyeball for covering the eyeball is noise.
SHELL = re.compile(
    r"(cornea|eyemoisture|eye_moisture|eyewet|eye_wet|moisture|"
    r"iris|lens|eyeshell|eye_shell|eyeocclusion|eye_occlusion|tearline)",
    re.I)


def read(path):
    """-> [(mesh name, material name, alpha mode, has base map)]"""
    env = UnityPy.load(path)
    mats = {}
    go_name = {}
    rows = []
    objs = []
    for obj in env.objects:
        try:
            ty = obj.type.name
        except Exception:                                   # noqa: BLE001
            continue
        objs.append((ty, obj))
        if ty == "GameObject":
            try:
                go_name[obj.path_id] = obj.read().m_Name
            except Exception:                               # noqa: BLE001
                pass
        elif ty == "Material":
            try:
                d = obj.read()
                keys = set()
                try:
                    keys = set(d.m_ShaderKeywords.split())
                except Exception:                           # noqa: BLE001
                    pass
                floats = {}
                try:
                    for k, v in d.m_SavedProperties.m_Floats:
                        floats[str(k)] = v
                except Exception:                           # noqa: BLE001
                    pass
                has_map = False
                try:
                    for k, v in d.m_SavedProperties.m_TexEnvs:
                        if str(k) == "_BaseMap" and getattr(
                                getattr(v, "m_Texture", None), "path_id", 0):
                            has_map = True
                except Exception:                           # noqa: BLE001
                    pass
                surface = floats.get("_Surface", 0.0)
                clip = floats.get("_AlphaClip", 0.0)
                mode = ("BLEND" if surface >= 0.5 else
                        "CUTOUT" if clip >= 0.5 else "OPAQUE")
                mats[obj.path_id] = (d.m_Name, mode, has_map)
            except Exception:                               # noqa: BLE001
                pass
    for ty, obj in objs:
        if ty != "SkinnedMeshRenderer":
            continue
        try:
            d = obj.read()
            gid = getattr(getattr(d, "m_GameObject", None), "path_id", 0)
            name = go_name.get(gid, "?")
            if not SHELL.search(name):
                continue
            for m in (d.m_Materials or []):
                info = mats.get(getattr(m, "path_id", 0))
                if info:
                    rows.append((name,) + info)
        except Exception:                                   # noqa: BLE001
            pass
    return rows


def read_vrm(path):
    """Same question of a .vrm, where the AUTHORED material names survive."""
    with open(path, "rb") as f:
        magic, _v, total = struct.unpack("<III", f.read(12))
        if magic != 0x46546C67:
            raise ValueError("not a GLB/VRM")
        js = None
        while f.tell() < total:
            length, kind = struct.unpack("<II", f.read(8))
            data = f.read(length)
            if kind == 0x4E4F534A:
                js = json.loads(data.decode("utf-8"))
                break
    if js is None:
        raise ValueError("no JSON chunk")
    mats = js.get("materials", [])
    mesh_name = {}
    for n in js.get("nodes", []):
        if "mesh" in n:
            mesh_name.setdefault(n["mesh"], n.get("name", "?"))
    rows = []
    for mi, m in enumerate(js.get("meshes", [])):
        for pr in m.get("primitives", []):
            idx = pr.get("material")
            if idx is None or idx >= len(mats):
                continue
            mat = mats[idx]
            mname = mat.get("name", "?")
            gname = mesh_name.get(mi, m.get("name", "?"))
            # EITHER name may carry the evidence, and only the .vrm has both.
            if not (SHELL.search(mname) or SHELL.search(gname)):
                continue
            pbr = mat.get("pbrMetallicRoughness", {})
            rows.append((gname, mname, mat.get("alphaMode", "OPAQUE"),
                         "baseColorTexture" in pbr))
    return rows


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: eye_shell_sweep.py <dir|file ...>   "
              "(.yargchar and/or .vrm)")
        return 2
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith((".yargchar", ".vrm"))]
        else:
            files.append(a)
    nflag = nchar = 0
    for p in sorted(files):
        name = os.path.basename(p).replace(".yargchar", "")
        try:
            rows = (read_vrm(p) if p.lower().endswith(".vrm") else read(p))
        except Exception as e:                              # noqa: BLE001
            print("  %-30s ERROR %s: %s" % (name[:30], type(e).__name__, e))
            continue
        opaque = [r for r in rows if r[2] == "OPAQUE"]
        if not rows:
            print("  %-30s no eye-shell mesh" % name[:30])
            continue
        nchar += 1
        print("  %-30s %d shell mesh/material pair(s), %d OPAQUE"
              % (name[:30], len(rows), len(opaque)))
        for mesh, mat, mode, has_map in rows:
            flag = "  <-- OPAQUE, so it DRAWS SOLID over whatever is behind it" \
                if mode == "OPAQUE" else ""
            print("      %-26s %-22s %-7s base map=%s%s"
                  % (mesh[:26], mat[:22], mode, "yes" if has_map else "no",
                     flag))
        nflag += len(opaque)
    print("\n%d bundle(s): %d carry an eye-shell mesh, %d opaque shell "
          "material(s) in all.\nEvery one is a CANDIDATE -- a solid eye is an "
          "ordinary thing on a stylised character,\nand only a render tells "
          "that from a lens covering a real eye." % (len(files), nchar, nflag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
