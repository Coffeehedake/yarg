"""Frame the camera tightly on one bone, to look at a detail like a hand."""
import math
import sys

import bpy
from mathutils import Vector

SRC, BONE, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
SPAN = float(sys.argv[sys.argv.index("--") + 4]) if len(sys.argv) > sys.argv.index("--") + 4 else 0.18

bpy.ops.wm.read_homefile(use_empty=True)
low = SRC.lower()
if low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for o in [x for x in bpy.data.objects if x.type in {"CAMERA", "LIGHT"}]:
        bpy.data.objects.remove(o, do_unlink=True)
elif low.endswith((".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.usd_import(filepath=SRC)
elif low.endswith(".vrm"):
    if bpy.ops.import_scene.vrm(filepath=SRC) != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import failed")
else:
    bpy.ops.import_scene.fbx(filepath=SRC)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
b = arm.data.bones.get(BONE)
if b is None:
    cand = [x.name for x in arm.data.bones if BONE.lower() in x.name.lower()]
    print("bone %r not found; close names: %s" % (BONE, cand[:8]))
    raise SystemExit(1)
ctr = arm.matrix_world @ ((b.head_local + b.tail_local) / 2.0)
print("framing %s at %s" % (BONE, tuple(round(v, 3) for v in ctr)))

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.scene.collection.objects.link(cam)
import os as _os
OFF = float(_os.environ.get("RENDER_OFFX", "0"))
import math as _m
AZ = _m.radians(float(_os.environ.get("RENDER_AZ", "0")))
EL = _m.radians(float(_os.environ.get("RENDER_EL", "0")))
d = SPAN * 2.2
cam.location = (ctr.x + OFF + d * _m.sin(AZ) * _m.cos(EL),
                ctr.y - d * _m.cos(AZ) * _m.cos(EL),
                ctr.z + d * _m.sin(EL))
cam.rotation_euler = (_m.radians(90) - EL, 0, AZ)
cam.data.lens = float(__import__("os").environ.get("RENDER_LENS", "85"))
bpy.context.scene.camera = cam
for loc, e in (((1, -2, 2), 3.0), ((-2, -1, 1), 2.0)):
    lt = bpy.data.objects.new("L", bpy.data.lights.new("L", type="AREA"))
    lt.data.energy = e * SPAN * SPAN * 400 * float(__import__("os").environ.get("RENDER_LIGHT", "1"))
    lt.data.size = SPAN
    lt.location = (ctr.x + loc[0] * SPAN, ctr.y + loc[1] * SPAN, ctr.z + loc[2] * SPAN)
    bpy.context.scene.collection.objects.link(lt)
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.1, 0.1, 0.12, 1)
bpy.context.scene.world = w
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 700, 700
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
