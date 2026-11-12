# -*- coding: utf-8 -*-
"""Retro-fit viseme bindings onto an already-built .vrm.

    VRM_VISEME="aa=Mesh/Key@1.0,..." \\
      blender --background --python add_visemes.py -- in.vrm out.vrm

WHY THIS EXISTS. 52 of the 65 installed characters have no viseme bound, so
their mouths never move. Most of them cannot be helped -- measured 2026-11-12,
22 of the 30 surviving `.vrm` files contain **zero shape keys**, and no
pipeline change can give a model a mouth shape it does not have. But a
character whose `.vrm` DOES carry mouth shapes and whose installed build
predates the viseme work needs only the bindings, and rebuilding from source is
not available: most of these characters have no source file on this machine any
more. A round trip through the `.vrm` is the only route, exactly as it is for
colliders -- see `add_colliders.py`, which this is modelled on.

THE MEASURING IS NOT DUPLICATED HERE. `viseme_fit.py` measures a model's shape
keys and emits a `VRM_VISEME=` line; this consumes that line and binds it. Two
tools, one measurement, and the mapping is visible in between where a human can
disagree with it -- which matters, because a viseme mapping is a guess about
what an artist meant and the fitter says so itself.

WHAT IS NOT DONE HERE. `VRM_VISEME_GAIN` is deliberately not supported. It
scales the shape key's own displacement, which rewrites mesh data rather than
adding a binding, and a round trip that edits geometry is a different risk from
one that edits a reference. If a character needs the gain, rebuild it.

LIKE add_colliders.py, THIS PRINTS WHAT THE ROUND TRIP COSTS -- triangle, mesh,
material, image, spring and collider counts before and after -- because a
silent loss should show up as a number rather than as a character that looks
wrong in game three days later.
"""
import json
import os
import struct
import sys

import bpy

VISEMES = ("aa", "ih", "ee", "ou", "oh")


def census(path):
    """Counts read straight out of the glTF, so they are what SHIPPED."""
    d = open(path, "rb").read()
    jl = struct.unpack("<I", d[12:16])[0]
    j = json.loads(d[20:20 + jl].decode("utf-8"))
    tris = 0
    for m in j.get("meshes", []):
        for p in m.get("primitives", []):
            if "indices" in p:
                tris += j["accessors"][p["indices"]]["count"] // 3
    sb = j.get("extensions", {}).get("VRMC_springBone", {})
    vrm = j.get("extensions", {}).get("VRMC_vrm", {})
    pre = (vrm.get("expressions", {}) or {}).get("preset", {}) or {}
    bound = sum(1 for k in VISEMES
                if (pre.get(k, {}) or {}).get("morphTargetBinds"))
    return {
        "tris": tris,
        "meshes": len(j.get("meshes", [])),
        "materials": len(j.get("materials", [])),
        "images": len(j.get("images", [])),
        "springs": len(sb.get("springs", [])),
        "colliders": len(sb.get("colliders", [])),
        "visemes": bound,
    }


def parse_spec(spec):
    """'aa=Mesh/Key@0.8,...' -> [(preset, mesh, key, weight), ...]"""
    out = []
    for chunk in [x.strip() for x in spec.split(",") if x.strip()]:
        if "=" not in chunk:
            raise SystemExit("ABORT: VRM_VISEME chunk %r has no '='" % chunk)
        preset, _, rest = chunk.partition("=")
        preset = preset.strip()
        if preset not in VISEMES:
            raise SystemExit("ABORT: VRM_VISEME names preset %r, which is not "
                             "one of %s" % (preset, ", ".join(VISEMES)))
        weight = 1.0
        if "@" in rest:
            rest, _, w = rest.partition("@")
            weight = float(w)
        if "/" not in rest:
            raise SystemExit("ABORT: VRM_VISEME chunk %r is not Mesh/Key"
                             % chunk)
        mesh, _, key = rest.partition("/")
        out.append((preset, mesh.strip(), key.strip(), weight))
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    if len(argv) < 2:
        print("usage: -- <in.vrm> <out.vrm>   (VRM_VISEME in the environment)")
        sys.exit(2)
    src, dst = argv[0], argv[1]

    spec = os.environ.get("VRM_VISEME", "").strip()
    if not spec:
        print("ABORT: VRM_VISEME is empty. Run viseme_fit.py on this file "
              "first and pass the line it emits.")
        sys.exit(2)
    binds = parse_spec(spec)

    before = census(src)
    if before["visemes"] and not os.environ.get("VRM_REVISEME"):
        print("%s already binds %d of 5 viseme(s) -- left alone "
              "(VRM_REVISEME=1 to rebind)"
              % (os.path.basename(src), before["visemes"]))
        sys.exit(2)

    bpy.ops.wm.read_homefile(use_empty=True)
    if bpy.ops.import_scene.vrm(filepath=src) != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import failed")

    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        raise SystemExit("ABORT: no armature in %s" % src)
    arm = max(arms, key=lambda a: len(a.data.bones))
    ext = arm.data.vrm_addon_extension

    # Every mesh and key named must EXIST. A binding to a name the file has not
    # got is written without complaint by the add-on and moves nothing in game,
    # which is the failure this whole class of bug is made of: a file that
    # looks lipsync-capable and is not.
    have = {}
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.shape_keys:
            continue
        have[o.name] = {kb.name for kb in o.data.shape_keys.key_blocks}
    for preset, mesh, key, _w in binds:
        if mesh not in have:
            raise SystemExit(
                "ABORT: VRM_VISEME names mesh %r, which this file has not got "
                "(it has: %s)" % (mesh, ", ".join(sorted(have)) or "no mesh "
                                  "with shape keys at all"))
        if key not in have[mesh]:
            raise SystemExit(
                "ABORT: VRM_VISEME names %s/%s, which this file has not got "
                "(that mesh has: %s)"
                % (mesh, key, ", ".join(sorted(have[mesh]))))

    pre = ext.vrm1.expressions.preset
    said = []
    for preset, mesh, key, w in binds:
        e = getattr(pre, preset, None)
        if e is None:
            raise SystemExit("ABORT: the VRM extension has no preset %r"
                             % preset)
        if os.environ.get("VRM_REVISEME"):
            e.morph_target_binds.clear()
    for preset, mesh, key, w in binds:
        e = getattr(pre, preset)
        b = e.morph_target_binds.add()
        b.node.mesh_object_name = mesh
        b.index = key
        b.weight = w
        said.append("%s<-%s/%s@%.2f" % (preset, mesh, key, w))
    print("  visemes: bound %d expression(s) -- %s"
          % (len(said), ", ".join(said)))
    missing = [v for v in VISEMES if v not in {p for p, _m, _k, _w in binds}]
    if missing:
        print("  visemes: NOT bound: %s -- the mouth will stall on those "
              "phonemes" % ", ".join(missing))

    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type in ("MESH", "ARMATURE"):
            o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.vrm(filepath=dst)

    after = census(dst)
    bad = [k for k in ("tris", "meshes", "materials", "images", "springs",
                       "colliders") if after[k] != before[k]]
    print("  round trip: " + ", ".join(
        "%s %d->%d" % (k, before[k], after[k])
        for k in ("tris", "meshes", "materials", "images", "springs",
                  "colliders", "visemes")))
    if bad:
        print("  WARNING: the round trip CHANGED %s -- do not ship this "
              "without looking at why" % ", ".join(bad))
    else:
        print("  round trip lost nothing; visemes %d -> %d"
              % (before["visemes"], after["visemes"]))
    if after["visemes"] != len({p for p, _m, _k, _w in binds}):
        print("  WARNING: %d viseme(s) asked for, %d in the written file"
              % (len({p for p, _m, _k, _w in binds}), after["visemes"]))
        sys.exit(1)


main()
