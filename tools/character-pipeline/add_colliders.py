# -*- coding: utf-8 -*-
"""Retro-fit spring-bone colliders onto an already-built .vrm.

    blender --background --python add_colliders.py -- in.vrm out.vrm

Most of the 66 characters have no source file on this machine any more -- they
were downloads in per-session scratchpads, and only the built VRM survives. A
round trip through the VRM is therefore the only way to give them colliders
without re-acquiring and re-deriving every recipe.

The measuring is NOT duplicated here: it lives in vrm_colliders.py and is the
same code build_vrm.py runs, so a fix to one is a fix to both.

A round trip is not free, and this prints what it costs: triangle, mesh,
material, texture and spring-chain counts before and after, so a silent loss
shows up as a number rather than as a character that looks wrong in game three
days later. Check those lines before shipping the result.
"""
import json
import os
import struct
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vrm_colliders  # noqa: E402

HUMAN_KEYS = ("hips", "spine", "chest", "upper_chest", "neck", "head")


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
    return {
        "tris": tris,
        "meshes": len(j.get("meshes", [])),
        "materials": len(j.get("materials", [])),
        "images": len(j.get("images", [])),
        "springs": len(sb.get("springs", [])),
        "colliders": len(sb.get("colliders", [])),
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    src, dst = argv[0], argv[1]

    before = census(src)
    if before["colliders"]:
        # Built by build_vrm.py, which already ran the same fitting. Adding a
        # second group here would double every collider.
        print("%s already has %d collider(s) -- left alone"
              % (os.path.basename(src), before["colliders"]))
        sys.exit(2)

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.vrm(filepath=src)

    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        print("FAILED: no armature in %s" % src)
        sys.exit(1)
    arm = max(arms, key=lambda a: len(a.data.bones))
    ext = arm.data.vrm_addon_extension

    # Read the humanoid map back off the file rather than guessing at bone
    # names. A rip's bones are called 'n47'; only this mapping knows which one
    # is the head.
    hb = ext.vrm1.humanoid.human_bones
    MAP = {}
    for k in HUMAN_KEYS:
        slot = getattr(hb, "%s_bone" % k, None) or getattr(hb, k, None)
        name = getattr(getattr(slot, "node", None), "bone_name", "") if slot else ""
        if name:
            MAP[k] = name
    if "head" not in MAP:
        print("FAILED: no humanoid head bone in %s" % src)
        sys.exit(1)

    bone_names = set(b.name for b in arm.data.bones)
    made = vrm_colliders.fit(arm, ext, MAP, bone_names)
    if not made:
        print("nothing to do for %s" % os.path.basename(src))
        sys.exit(2)

    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type in ("MESH", "ARMATURE"):
            o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.vrm(filepath=dst)

    after = census(dst)
    bad = [k for k in ("tris", "meshes", "materials", "images", "springs")
           if after[k] != before[k]]
    print("  round trip: " + ", ".join(
        "%s %d->%d" % (k, before[k], after[k])
        for k in ("tris", "meshes", "materials", "images", "springs",
                  "colliders")))
    if bad:
        print("  WARNING: the round trip CHANGED %s -- do not ship this "
              "without looking at why" % ", ".join(bad))
    else:
        print("  round trip lost nothing; colliders %d -> %d"
              % (before["colliders"], after["colliders"]))


main()
