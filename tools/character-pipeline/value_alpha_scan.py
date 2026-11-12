# Which materials in a SOURCE model state their transparency as a VALUE, with
# no map to carry it?
#
#   blender --background --python value_alpha_scan.py -- <source file>
#
# WHY THIS EXISTS. Alice Ivy shipped with a solid black disc over each eye for
# the whole life of the character. The cause was EyeMoisture_Left/_Right: a wet
# film her archive defines as HASHED, black, at alpha 0.051 -- a 5% sheen --
# with nothing wired into the Alpha socket. build_vrm.py flattened that to
# `baseColorFactor [0, 0, 0, 1]` and OPAQUE, so the 5% film became a 100% slab
# in front of her real eyes. Her eyes were never damaged, only covered.
#
# NO ALPHA SWEEP COULD HAVE CAUGHT IT. alpha_sweep_installed.py measures a
# material's base MAP, and this material has none -- there is nothing to
# measure, so the material is invisible to that tool. The fault is only legible
# in the source, which is what this reads.
#
# The builder's condition for honouring such a value is, verbatim:
#
#     VRM_VALUE_ALPHA and not cut and _src_blend in ("BLEND", "HASHED")
#     and _src_alpha_img is None and _src_alpha_val < 0.99
#
# Every clause is reproduced here EXCEPT `not cut`, which cannot be read from
# the source: the builder also finds opacity maps by FILENAME in the texture
# directory and through VRM_TEX, neither of which is visible in the material.
# So a hit is a CANDIDATE, not a defect. Sayuri's Eye_Shadows states alpha
# 0.000 and has an opacity map pinned over it by VRM_TEX; it is `cut`, the
# branch never sees it, and it ships correctly as BLEND.
#
# READING A HIT. Two further facts decide whether a candidate is a problem:
#   * is the base colour DARK and untextured? Then flattening it paints a slab
#     of that colour, which is Alice's failure. A textured base keeps showing
#     its texture and merely loses some see-through.
#   * what is in front of what? The same construction on a cornea is harmless;
#     over an eyeball it is a black disc.
# VRM_VALUE_ALPHA is therefore off by default, and deliberately so: Heels'
# Std_Cornea_L/R are the same HASHED construction at alpha 0.553 over a
# TEXTURED base, and honouring that value washed her iris out against the
# sclera. "55% transparent over a texture doing work" and "95% transparent over
# nothing" are different problems.
#
# MEASURED 2026-11-12 across the five extracted sources. Only Alice Ivy had the
# failure; Heels has the documented cornea pair, Sayuri's one candidate is cut
# by a pinned map, and Alcina (0 of 17) and Ariel (0 of 26) state no value
# transparency at all.
#
# WHY THE TOTALS ARE PRINTED. "No candidates" and "the import failed" print the
# same empty list otherwise, and this project has already shipped one sweep
# that found nothing because it never ran. Every material is counted, and the
# skipped ones are counted BY REASON, so a zero can be read against how many
# materials were actually examined.
import os
import sys

import bpy

src = sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
low = src.lower()
if low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=src)
elif low.endswith((".gltf", ".glb")):
    bpy.ops.import_scene.gltf(filepath=src)
elif low.endswith(".vrm"):
    if bpy.ops.import_scene.vrm(filepath=src) != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import failed")
else:
    bpy.ops.import_scene.fbx(filepath=src)

seen = 0
no_bsdf = 0
mapped = 0         # something IS plugged into Alpha -- a map carries it
val_opaque = 0     # alpha >= 0.99 -- nothing is lost by flattening
mode_opaque = 0    # a value alpha, but the material renders OPAQUE anyway
hits = []

print("\n### %s" % os.path.basename(src))
for m in sorted(bpy.data.materials, key=lambda x: x.name):
    seen += 1
    bsdf = None
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bsdf = n
                break
    if bsdf is None or "Alpha" not in bsdf.inputs:
        no_bsdf += 1
        continue
    al = bsdf.inputs["Alpha"]
    if al.links:
        mapped += 1
        continue
    if al.default_value >= 0.99:
        val_opaque += 1
        continue
    blend = getattr(m, "blend_method", "?")
    if blend not in ("BLEND", "HASHED"):
        # Blender itself draws this solid, so shipping it solid MATCHES the
        # source. Counted, not flagged.
        mode_opaque += 1
        continue
    bc = bsdf.inputs["Base Color"]
    textured = bool(bc.links)
    col = ("<textured>" if textured
           else [round(v, 3) for v in bc.default_value[:3]])
    lum = (None if textured else
           0.2126 * bc.default_value[0] + 0.7152 * bc.default_value[1]
           + 0.0722 * bc.default_value[2])
    flag = ""
    if lum is not None and lum < 0.25:
        flag = "   <-- DARK and untextured: ships as a solid slab of that colour"
    hits.append((m.name, blend, al.default_value, col, flag))

for name, blend, a, col, flag in hits:
    print("   %-26s %-7s alpha=%.3f base=%s%s"
          % (name[:26], blend, a, col, flag))
print("   %d candidate(s) out of %d material(s)   "
      "[skipped: %d no-BSDF, %d alpha is mapped, %d alpha>=0.99, "
      "%d value alpha but OPAQUE mode]"
      % (len(hits), seen, no_bsdf, mapped, val_opaque, mode_opaque))
