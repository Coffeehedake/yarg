"""Is a flat-white surface caused by broken custom split normals?

Report each mesh's normals, then clear the custom ones and report again."""
import sys

import bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
WANT = sys.argv[sys.argv.index("--") + 2]
OUT = sys.argv[sys.argv.index("--") + 3]

bpy.ops.wm.read_homefile(use_empty=True)
low = SRC.lower()
if low.endswith((".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.usd_import(filepath=SRC)
else:
    bpy.ops.import_scene.fbx(filepath=SRC)

targets = [o for o in bpy.data.objects if o.type == "MESH" and WANT.lower() in o.name.lower()]
print("matched meshes:", [o.name for o in targets])
for o in targets:
    me = o.data
    has_custom = me.has_custom_normals if hasattr(me, "has_custom_normals") else "?"
    ns = [Vector(l.vector) for l in me.corner_normals] if hasattr(me, "corner_normals") else []
    bad = sum(1 for n in ns if n.length < 0.5)
    print("  %-30s custom_normals=%s corner_normals=%d degenerate=%d"
          % (o.name[:30], has_custom, len(ns), bad))

# keep only the target meshes, so the render shows just them
for o in [x for x in bpy.data.objects if x.type == "MESH" and x not in targets]:
    bpy.data.objects.remove(o, do_unlink=True)
for o in [x for x in bpy.data.objects if x.type == "ARMATURE"]:
    bpy.data.objects.remove(o, do_unlink=True)

if "--clear" in sys.argv:
    for o in targets:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        try:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            print("  cleared custom split normals on", o.name)
        except Exception as e:
            print("  could not clear on %s: %s" % (o.name, e))
        try:
            bpy.ops.object.shade_smooth()
        except Exception:
            pass

lo = Vector((1e18,) * 3)
hi = Vector((-1e18,) * 3)
for o in targets:
    for v in o.data.vertices:
        c = o.matrix_world @ v.co
        for i in range(3):
            lo[i] = min(lo[i], c[i])
            hi[i] = max(hi[i], c[i])
ctr = (lo + hi) / 2.0
h = max((hi - lo).z, 0.01)
import math
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.scene.collection.objects.link(cam)
cam.location = (ctr.x, ctr.y - h * 2.6, ctr.z)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam
for loc, e in (((2, -3, 3), 4.0), ((-3, -2, 2), 2.5)):
    lt = bpy.data.objects.new("L", bpy.data.lights.new("L", type="AREA"))
    lt.data.energy = e * h * h * 120
    lt.data.size = h
    lt.location = (ctr.x + loc[0] * h / 2, ctr.y + loc[1] * h / 2, ctr.z + loc[2] * h / 4)
    bpy.context.scene.collection.objects.link(lt)
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.08, 0.08, 0.1, 1)
bpy.context.scene.world = w
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 600, 700
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
