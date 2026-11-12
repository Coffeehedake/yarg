# -*- coding: utf-8 -*-
"""Make one material USE the alpha channel its base texture already carries.

    HONOUR="Material[,Material2]" [HONOUR_MODE=CLIP|BLEND]       blender --background --python honour_alpha.py -- in.vrm out.vrm

`alpha_sweep_installed.py` calls these UNUSED: an opaque material whose base
texture has an alpha channel nobody reads. Honouring one means wiring that
channel into Alpha and switching the material off OPAQUE.

THIS TOOL EXISTS TO BE TRIED AND REJECTED, and on 2026-11-12 it was, on all
three candidates that were reachable -- see *Honouring the alpha ruins all
three* in docs/character-models.md. Keep it, because the next UNUSED candidate
deserves the same five-minute test rather than an argument.

It is NOT set_material_alpha.py. That one gives a flat value to a material with
no map; this hands control to a map that is already there. They fail in
opposite directions, which is why they are separate.

It walks UPSTREAM from Base Color to find the image rather than demanding one
hop: Jinx's goes through a colour multiply, and insisting on a direct link made
a perfectly ordinary material read as "not an image texture".
"""
import os
import sys

import bpy

names = [x.strip() for x in os.environ.get("HONOUR", "").split(",")
         if x.strip()]
mode = os.environ.get("HONOUR_MODE", "CLIP").upper()
if mode not in ("CLIP", "BLEND"):
    raise SystemExit("ABORT: HONOUR_MODE must be CLIP or BLEND")
if not names:
    raise SystemExit("ABORT: HONOUR is empty")

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]

bpy.ops.wm.read_homefile(use_empty=True)
if bpy.ops.import_scene.vrm(filepath=src) != {"FINISHED"}:
    raise SystemExit("ABORT: vrm import failed")

done = []
for n in names:
    mat = bpy.data.materials.get(n)
    if mat is None:
        raise SystemExit("ABORT: no material %r (have: %s)"
                         % (n, ", ".join(sorted(m.name for m in
                                                bpy.data.materials))))
    if not mat.use_nodes:
        raise SystemExit("ABORT: %s has no node tree" % n)
    bsdf = next((x for x in mat.node_tree.nodes
                 if x.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        raise SystemExit("ABORT: %s has no Principled BSDF" % n)
    if bsdf.inputs["Alpha"].links:
        raise SystemExit("ABORT: %s already has something wired into Alpha -- "
                         "it is not one of the UNUSED ones" % n)
    if not bsdf.inputs["Base Color"].links:
        raise SystemExit("ABORT: %s has no image on Base Color" % n)
    # Base Color is not always wired STRAIGHT to the image: Jinx's goes through
    # a colour multiply. Walk upstream rather than demanding one hop, or a
    # perfectly ordinary material reads as "not an image texture".
    def find_image(node, seen=None, depth=0):
        seen = seen if seen is not None else set()
        if node in seen or depth > 6:
            return None
        seen.add(node)
        if node.type == "TEX_IMAGE" and node.image is not None:
            return node
        for inp in node.inputs:
            for link in inp.links:
                got = find_image(link.from_node, seen, depth + 1)
                if got is not None:
                    return got
        return None

    tex = find_image(bsdf.inputs["Base Color"].links[0].from_node)
    if tex is None:
        raise SystemExit("ABORT: no image texture upstream of %s's Base Color"
                         % n)
    if tex.image.channels != 4:
        raise SystemExit("ABORT: %s's base image %r has no alpha channel -- "
                         "there is nothing to honour"
                         % (n, tex.image.name))
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    mat.blend_method = mode
    if mode == "CLIP":
        try:
            mat.alpha_threshold = 0.5
        except Exception:                               # noqa: BLE001
            pass
    # blend_method ALONE IS NOT ENOUGH, and the first Shrek build proved it:
    # CLIP in Blender came out `alphaMode: BLEND` in the .vrm, because the VRM
    # exporter reads mtoon1 when that block is live and only falls back to
    # blend_method when it is not. A blended card has no z-write and sorts by
    # draw order, which this project has already paid for once on hair -- so a
    # cutout asked for must be a cutout written.
    extra = ""
    try:
        mt = mat.vrm_addon_extension.mtoon1
        # `mtoon1.enabled` defaults to FALSE and the exporter only writes the
        # extension's alpha_mode when it is on; with it off, Blender's CLIP
        # comes out as glTF BLEND. build_vrm.py turns it on for exactly this
        # reason. HONOUR_MTOON=0 leaves it off and accepts BLEND, because
        # enabling MToon swaps that material's SHADING MODEL -- fine on a hair
        # card, and the thing that put a tan unlit plate across Peach's brow.
        if mode == "CLIP" and os.environ.get("HONOUR_MTOON", "1") != "0":
            mt.enabled = True
        if getattr(mt, "enabled", False):
            mt.alpha_mode = "MASK" if mode == "CLIP" else "BLEND"
            if mode == "CLIP":
                mt.alpha_cutoff = 0.5
            extra = ", mtoon1 ON, alpha_mode=%s" % mt.alpha_mode
    except Exception as e:                              # noqa: BLE001
        extra = ", (no mtoon1 block: %s)" % e
    done.append("%s (%s, %s%s)" % (n, tex.image.name, mode, extra))

print("  honoured: %s" % "; ".join(done))

arm = max((o for o in bpy.data.objects if o.type == "ARMATURE"),
          key=lambda a: len(a.data.bones))
bpy.ops.object.select_all(action="DESELECT")
for o in bpy.data.objects:
    if o.type in ("MESH", "ARMATURE"):
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.vrm(filepath=dst)
print("  wrote %s" % dst)
