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

# RENDER_HIDE=<substring> keeps the named meshes out of the render, which is
# how a part that draws over another gets NAMED instead of guessed at. Peach's
# face is a stack of six overlapping expression meshes from a Smash rip, and
# hiding them one at a time is what identified the plate across her brow as
# `Peach_Blink_VoiceA_VIS_O_OBJ_` rather than the eyes or the face itself.
_hide = _os.environ.get("RENDER_HIDE", "")
if _hide:
    for _o in bpy.data.objects:
        if _o.type == "MESH" and _hide.lower() in _o.name.lower():
            _o.hide_render = True
            print("hidden from the render: %s" % _o.name)

# RENDER_ONLY is the other half of the same question, and it is the one that
# settles a stack of overlapping parts: hiding a mesh tells you what was BEHIND
# it, which is a different fact from what the mesh itself draws.
_only = _os.environ.get("RENDER_ONLY", "")
if _only:
    for _o in bpy.data.objects:
        if _o.type == "MESH" and _only.lower() not in _o.name.lower():
            _o.hide_render = True

# RENDER_KEY="Face/A=1.0,Face/ClosedTeeth=0.5" drives shape keys before the
# render. Choosing a viseme mapping means looking at each candidate shape at
# full weight, and the only framing that reliably finds a face is the one this
# script already does -- framing on the head BONE. Four attempts at framing a
# mouth from the shape key's own displacement landed on Pomni's eyes instead,
# because her mouth keys move the eye region more than they move her lips.
for _spec in [x for x in _os.environ.get("RENDER_KEY", "").split(",") if x.strip()]:
    _ref, _, _val = _spec.partition("=")
    _mn, _, _kn = _ref.partition("/")
    _ob = bpy.data.objects.get(_mn.strip())
    if _ob is None or not _ob.data.shape_keys:
        raise SystemExit("ABORT: RENDER_KEY names mesh %r, which has no shape "
                         "keys here" % _mn.strip())
    _kb = _ob.data.shape_keys.key_blocks.get(_kn.strip())
    if _kb is None:
        raise SystemExit("ABORT: RENDER_KEY names key %r on %r; it has %s"
                         % (_kn.strip(), _mn.strip(),
                            [k.name for k in _ob.data.shape_keys.key_blocks]))
    _kb.value = float(_val or 1.0)
    print("shape key %s/%s = %.2f" % (_mn.strip(), _kn.strip(), _kb.value))

bpy.ops.render.render(write_still=True)
print("wrote", OUT)
