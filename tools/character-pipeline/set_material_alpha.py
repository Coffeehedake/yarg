# -*- coding: utf-8 -*-
"""Make one material in an already-built .vrm transparent.

    SETALPHA="Material=0.08" blender --background --python set_material_alpha.py -- in.vrm out.vrm

WHY THIS EXISTS. "An eye shell shipped opaque over the eye" is now the third
occurrence of one fault: Alice Ivy's `EyeMoisture_Left/_Right`, Ariel's
`Cornea`, and Prix's `aiStandardSurface4` on `L_iris`/`R_iris`. In every case
the eyes underneath are perfect and a flat lens is parked in front of them.

Alice had a source archive, so her own authored alpha (0.051) could be honoured
with `VRM_VALUE_ALPHA=1` at build time. Prix has no source on this machine --
she is one of the characters that exist only as a built `.vrm` -- so there is
no authored value to honour and no rebuild available. This edits the built file
instead, the same round trip `add_colliders.py` and `add_visemes.py` use.

THE NUMBER IS A CHOICE, NOT A MEASUREMENT, which is why it is an argument.
Prix was settled at 0.08 by rendering three ways -- as shipped, at 0.08, and
with the lens hidden entirely as the control -- and 0.08 is indistinguishable
from the control while keeping the lens for its highlight.

IT REFUSES a material whose Alpha has a MAP wired into it. Overriding a real
opacity map with a flat value is a different decision from giving a value to a
material that has none, and the one place this project did that by accident
(Heels' corneas, 0.553 over a texture doing work) washed her iris out.
"""
import os
import sys

import bpy

spec = os.environ.get("SETALPHA", "")
if "=" not in spec:
    raise SystemExit("ABORT: SETALPHA must be Material=alpha")
mat_name, _, a = spec.partition("=")
mat_name = mat_name.strip()
alpha = float(a)

argv = sys.argv[sys.argv.index("--") + 1:]
src, dst = argv[0], argv[1]

bpy.ops.wm.read_homefile(use_empty=True)
if bpy.ops.import_scene.vrm(filepath=src) != {"FINISHED"}:
    raise SystemExit("ABORT: vrm import failed")

mat = bpy.data.materials.get(mat_name)
if mat is None:
    raise SystemExit("ABORT: no material %r (have: %s)"
                     % (mat_name, ", ".join(sorted(m.name for m in
                                                   bpy.data.materials))))
if not mat.use_nodes:
    raise SystemExit("ABORT: %s has no node tree" % mat_name)
bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
            None)
if bsdf is None or "Alpha" not in bsdf.inputs:
    raise SystemExit("ABORT: %s has no Principled Alpha input" % mat_name)
if bsdf.inputs["Alpha"].links:
    raise SystemExit("ABORT: %s has a MAP wired into Alpha -- setting a value "
                     "would be ignored, and overriding a real opacity map is a "
                     "different decision" % mat_name)

was = bsdf.inputs["Alpha"].default_value
bsdf.inputs["Alpha"].default_value = alpha
mat.blend_method = "BLEND"
print("  %s: alpha %.3f -> %.3f, blend_method -> BLEND" % (mat_name, was, alpha))

# The VRM exporter takes its alphaMode from mtoon1 when that block is enabled
# and from blend_method otherwise. Set whichever is live rather than guessing.
try:
    mt = mat.vrm_addon_extension.mtoon1
    if getattr(mt, "enabled", False):
        mt.alpha_mode = "BLEND"
        mt.pbr_metallic_roughness.base_color_factor[3] = alpha
        print("  mtoon1 is enabled: alpha_mode -> BLEND, factor alpha -> %.3f"
              % alpha)
    else:
        print("  mtoon1 is not enabled, so blend_method is what the exporter "
              "reads")
except Exception as e:                                  # noqa: BLE001
    print("  (no mtoon1 block: %s)" % e)

arm = max((o for o in bpy.data.objects if o.type == "ARMATURE"),
          key=lambda a_: len(a_.data.bones))
bpy.ops.object.select_all(action="DESELECT")
for o in bpy.data.objects:
    if o.type in ("MESH", "ARMATURE"):
        o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.vrm(filepath=dst)
print("  wrote %s" % dst)
