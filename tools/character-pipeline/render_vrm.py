"""Render a .vrm from the front, through the glTF importer -- a .vrm IS a glb.
obj_import does not read one and fails without raising, which renders an empty
frame that looks like a successful check. The trade is that MToon becomes plain
PBR, so judge geometry, pose, UVs and texture assignment from these renders,
not the shading.

Three explanations for one failure were written into this file before the cause
was measured, and all three were wrong: an add-on race, a context that
`read_homefile` destroys, and an extension filter that refuses '.vrm'. The cause
was in the CALLER -- a shell-quoting bug that passed a path with an unexpanded
variable still in it. Measured here afterwards, in this Blender:

    gltf, fresh session, no read_homefile           -> {'FINISHED'}
    gltf, AFTER read_homefile(use_empty=True)       -> {'FINISHED'}
    gltf given a .vrm, filepath only                -> {'FINISHED'}
    gltf given a path that does not exist           -> RAISED Please select a file
    vrm add-on given a path that does not exist     -> {'CANCELLED'}

"Please select a file" and {'CANCELLED'} are what a MISSING FILE looks like.
Both read as a broken importer and neither is one. Print the path the importer
was handed before theorising about the importer."""


def clear_scene():
    """Empty the scene by removing its objects.

    `read_homefile(use_empty=True)` does this just as well; the measurements
    above are what demote it from "never do this" -- which this file used to
    say -- to a matter of taste."""
    import bpy as _b
    for _o in list(_b.data.objects):
        _b.data.objects.remove(_o, do_unlink=True)


def import_gltf(path):
    """Import a .glb/.gltf/.vrm.

    The glTF importer reads a .vrm by filepath alone. An earlier version of this
    function copied every .vrm to a temporary '.glb' first, on the belief that
    the operator's filter_glob refuses the extension; the table above is that
    belief being tested."""
    import bpy as _b
    return _b.ops.import_scene.gltf(filepath=path)


def imported_meshes():
    """The meshes this import brought in, and only those.

    Anything else in the scene has to stay out of the bounding box that aims the
    camera, and an add-on sharing this Blender can put objects in the scene at
    any moment: BlenderMCP leaves a 2 m 'Icosphere' at the origin, which
    survives clear_scene() because it arrives DURING the import. It stretched
    Peacemaker's measured extent from 1.85 m to 2.85 m and framed the shot
    around a sphere. The character was fine; the ruler was not.

    Comparing the scene before and after cannot separate them, for exactly that
    reason. Every importer here leaves what it created SELECTED, which does not
    depend on when anything else appeared."""
    import bpy as _b
    sel = [o for o in _b.context.selected_objects if o.type == "MESH"]
    if sel:
        return sel
    # No selection means the importer did not make one: fall back to the whole
    # scene rather than render an empty frame, and say so.
    print("render: importer left nothing selected - framing every mesh in the "
          "scene, which may include objects it did not create")
    return [o for o in _b.data.objects if o.type == "MESH"]
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
    clear_scene()
    low = SRC.lower()
    if low.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=SRC)
    elif low.endswith((".glb", ".gltf")):
        import_gltf(SRC)
    else:
        bpy.ops.wm.usd_import(filepath=SRC)
else:
    clear_scene()
    res = import_gltf(SRC)
    if res != {"FINISHED"}:
        raise SystemExit("ABORT: vrm import returned %s" % res)
if SRC.lower().endswith(".blend"):
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
else:
    meshes = imported_meshes()
    _skip = sorted(o.name for o in bpy.data.objects
                   if o.type == "MESH" and o not in set(meshes))
    if _skip:
        print("render: ignoring %d mesh(es) the import did not create: %s"
              % (len(_skip), ", ".join(_skip[:6])))
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
