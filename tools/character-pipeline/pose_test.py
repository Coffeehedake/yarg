"""Pose the spring chains and render, to see whether the weighting holds.

A rest-pose render verifies nothing about weights: at rest every weighting is
the identity, so a torn rig and a good one look exactly alike. Bend the chains
and look at what the mesh does."""
import math
import sys

import bpy
from mathutils import Vector

SRC, PATTERN, OUT = sys.argv[sys.argv.index("--") + 1:][:3]
DEG = float(sys.argv[sys.argv.index("--") + 4]) if len(sys.argv) > sys.argv.index("--") + 4 else 35.0

if SRC.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for o in list(bpy.data.objects):
        if o.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(o, do_unlink=True)
else:
    bpy.ops.wm.read_homefile(use_empty=True)
    if bpy.ops.import_scene.vrm(filepath=SRC) != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import failed")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]

print("armatures in scene:", [o.name for o in bpy.data.objects if o.type == "ARMATURE"])
for o in meshes[:4]:
    tgt = [m.object.name for m in o.modifiers if m.type == "ARMATURE" and m.object]
    print("   mesh %-24s armature modifier -> %s" % (o.name[:24], tgt))
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"
            and any(m.type == "ARMATURE" and m.object is o
                    for me in meshes for m in me.modifiers)), arm)
print("driving armature:", arm.name)

hits = [b.name for b in arm.data.bones if PATTERN.lower() in b.name.lower()]
print("matched %d bones: %s" % (len(hits), hits[:10]))
if not hits:
    raise SystemExit("ABORT: no bones match %r - nothing to test" % PATTERN)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
for n in hits:
    pb = arm.pose.bones[n]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler[0] = math.radians(DEG)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

# how far did the hair actually travel, and did anything fly off?
deps = bpy.context.evaluated_depsgraph_get()
# Measure a real vertex, not just the bounding box: a box can stay the same
# while the hair moves inside it.
_probe = meshes[0]
_ev = _probe.evaluated_get(deps)
_me = _ev.to_mesh()
_sample = [_me.vertices[i].co.copy() for i in range(0, len(_me.vertices), max(1, len(_me.vertices) // 500))]
_ev.to_mesh_clear()
print("posed sample vertex[0] =", tuple(round(v, 4) for v in _sample[0]))
lo = Vector((1e18,) * 3); hi = Vector((-1e18,) * 3)
for o in meshes:
    ev = o.evaluated_get(deps)
    for c in ev.bound_box:
        w = ev.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
print("posed extent %.3f x %.3f x %.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
ctr = (lo + hi) / 2.0
h = max(hi.z - lo.z, 0.1)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.scene.collection.objects.link(cam)
cam.location = (ctr.x + h * 1.6, ctr.y - h * 1.6, ctr.z + h * 0.15)
cam.rotation_euler = (math.radians(85), 0, math.radians(45))
bpy.context.scene.camera = cam
for loc, e in (((2, -3, 3), 4.0), ((-3, -2, 2), 2.5), ((0, 3, 2), 2.0)):
    lt = bpy.data.objects.new("L", bpy.data.lights.new("L", type="AREA"))
    lt.data.energy = e * h * h * 120
    lt.data.size = h
    lt.location = (ctr.x + loc[0] * h / 2, ctr.y + loc[1] * h / 2, ctr.z + loc[2] * h / 4)
    bpy.context.scene.collection.objects.link(lt)
w = bpy.data.worlds.new("W"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.08, 0.08, 0.1, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.2
bpy.context.scene.world = w
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 760, 1000
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
