"""Render a .vrm from the front. Imports via the VRM add-on - obj_import does not
read a .vrm and fails without raising, which renders an empty frame that looks
like a successful check."""
import math
import sys

import bpy
from mathutils import Vector

SRC, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
if SRC.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
    for o in list(bpy.data.objects):
        if o.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(o, do_unlink=True)
elif SRC.lower().endswith((".fbx", ".glb", ".gltf", ".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.read_homefile(use_empty=True)
    low = SRC.lower()
    if low.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=SRC)
    elif low.endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=SRC)
    else:
        bpy.ops.wm.usd_import(filepath=SRC)
else:
    bpy.ops.wm.read_homefile(use_empty=True)
    res = bpy.ops.import_scene.vrm(filepath=SRC)
    if res != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import returned %s" % res)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not meshes:
    raise SystemExit("ABORT: import produced no meshes - the frame would be empty")

lo = Vector((1e18,) * 3)
hi = Vector((-1e18,) * 3)
deps = bpy.context.evaluated_depsgraph_get()
for o in meshes:
    ev = o.evaluated_get(deps)
    for c in ev.bound_box:
        w = ev.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i])
            hi[i] = max(hi[i], w[i])
ctr = (lo + hi) / 2.0
h = max(hi.z - lo.z, 0.1)
print("render: %d meshes, extent %.3f x %.3f x %.3f, centre z=%.3f"
      % (len(meshes), hi.x - lo.x, hi.y - lo.y, h, ctr.z))

cam_d = h * 2.2
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.scene.collection.objects.link(cam)
# optional orbit angle, so a model can be checked from more than one side
import os as _os
_az = math.radians(float(_os.environ.get("RENDER_AZ", "0")))
cam.location = (ctr.x + cam_d * math.sin(_az), ctr.y - cam_d * math.cos(_az), ctr.z)
cam.rotation_euler = (math.radians(90), 0, _az)
bpy.context.scene.camera = cam

for loc, e in (((2, -3, 3), 4.0), ((-3, -2, 2), 2.5), ((0, 3, 2), 2.0)):
    lt = bpy.data.objects.new("L", bpy.data.lights.new("L", type="AREA"))
    lt.data.energy = e * h * h * 120 * float(__import__("os").environ.get("RENDER_LIGHT", "1"))
    lt.data.size = h
    lt.location = (ctr.x + loc[0] * h / 2, ctr.y + loc[1] * h / 2, ctr.z + loc[2] * h / 4)
    bpy.context.scene.collection.objects.link(lt)
    ct = lt.constraints.new("TRACK_TO")
    ct.target = cam  # aim roughly at the subject
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.08, 0.08, 0.1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
bpy.context.scene.world = world

sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [
    i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
] else sc.render.engine
sc.render.resolution_x, sc.render.resolution_y = 700, 1000
sc.render.film_transparent = False
# A .blend brings its own render settings, and one saved with a video format
# refuses to write a single frame ("Cannot write a single file with an animation
# format selected") - the render looks like a missing model.
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
