# Scale a rest skeleton onto its own mesh, about the hips, feet on the floor.
#
# THIS STEP WAS DOCUMENTED AND NEVER WRITTEN DOWN AS CODE. The Rock's recipe
# row says "scale the rest skeleton about the hips (already correct at 0.573
# of height) anchored on feet-on-floor" and then "fit_joints.py does both",
# which it does not -- fit_joints only moves joints. The scale was done by
# hand, once, and so could not be repeated: rebuilding him from source gives
# a skeleton 4.18 m tall for a 1.96 m mesh with the feet 1.4 m below the
# floor, which is the original defect verbatim.
#
# Why the hips are the anchor: on every rig measured here the hips sit at
# about 0.573 of total height, and that ratio is right even when the skeleton
# is the wrong size. So the hips give a point to scale about that does not
# need to be guessed, and feet-on-floor gives the factor.
#
# WHY THIS MUST RUN BEFORE fit_joints.py, not instead of it: a uniform scale
# cannot express a rig that is wrong by a different factor in each limb, which
# The Rock is. But fit_joints alone cannot do it either -- it only moves the
# joints it fits, so an unfitted bone (the shoulder, deliberately, since
# fitting it doubled his shoulder span) is left wherever the unscaled skeleton
# had it, metres from the mesh. Scale first so everything is approximately
# right, then fit the hinges that are still wrong.
#
#   blender --background --python scale_rig.py -- <in.blend> <out.blend>
#
#   RIG_HIPS_RATIO=0.573   where the hips sit as a fraction of mesh height
#   RIG_HIPS_BONE=Hips     override the hips bone name
import os
import sys

import bpy
from mathutils import Vector

src, dst = sys.argv[-2], sys.argv[-1]
RATIO = float(os.environ.get("RIG_HIPS_RATIO", "0.573"))

bpy.ops.wm.open_mainfile(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm]
if not meshes:
    raise SystemExit("ABORT: no meshes are bound to the armature")

# The MESH is the authority for height. The skeleton is the thing being
# corrected, so measuring against it would be circular.
lo = min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
hi = max((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
height = hi - lo
print("mesh: %.4f .. %.4f  height %.4f" % (lo, hi, height))

hips_name = os.environ.get("RIG_HIPS_BONE", "")
if not hips_name:
    for cand in ("Hips", "hips", "Bip01 Pelvis", "Pelvis", "pelvis", "Root"):
        if cand in arm.data.bones:
            hips_name = cand
            break
if hips_name not in arm.data.bones:
    raise SystemExit("ABORT: no hips bone found; set RIG_HIPS_BONE. Have: %s"
                     % [b.name for b in arm.data.bones][:12])

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
mw = arm.matrix_world
inv = mw.inverted()

hips_world = mw @ eb[hips_name].head
bone_lo = min((mw @ b.head).z for b in eb)
print("hips at z %.4f, lowest bone at z %.4f, skeleton span %.4f"
      % (hips_world.z, bone_lo, max((mw @ b.head).z for b in eb) - bone_lo))

# 1. Put the hips where the mesh says they belong.
target_hips = lo + RATIO * height
d = target_hips - hips_world.z
# 2. Scale about the hips so the lowest bone lands on the mesh's own floor.
span = target_hips - (bone_lo + d)
if abs(span) < 1e-6:
    raise SystemExit("ABORT: hips and lowest bone are at the same height")
f = (target_hips - lo) / span
print("translate z by %+.4f, then scale about the hips by %.4f" % (d, f))

anchor = Vector((hips_world.x, hips_world.y, target_hips))
snap = {b.name: b.use_connect for b in eb}
for b in eb:
    b.use_connect = False
for b in eb:
    for attr in ("head", "tail"):
        p = mw @ getattr(b, attr)
        p.z += d
        setattr(b, attr, inv @ (anchor + (p - anchor) * f))
    b.length = max(b.length, 1e-4)
for b in eb:
    b.use_connect = snap[b.name]

new_lo = min((mw @ b.head).z for b in eb)
new_hi = max((mw @ b.head).z for b in eb)
print("after: lowest bone z %.4f (mesh floor %.4f), highest %.4f (mesh top %.4f)"
      % (new_lo, lo, new_hi, hi))
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=dst)
print("saved", dst)
