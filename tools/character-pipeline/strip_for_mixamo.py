"""Export just the geometry, textured and unrigged, for Mixamo's auto-rigger.

Mixamo wants a single upright mesh with no skeleton; it builds its own. Keep the
materials so the download comes back textured."""
import sys, bpy
import re
_a = sys.argv[sys.argv.index("--")+1:]
SRC, OUT = _a[0], _a[1]
# Optional third argument: a regex of MESH names to leave behind. An auto-rigger
# skins a loose outer garment to the arms as if it were skin, so a robe or a
# cape is better rigged separately -- hold it back here, rig the body, then
# graft it on afterwards with spring bones.
DROP = _a[2] if len(_a) > 2 else ""
_low = SRC.lower()
if _low.endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
else:
    bpy.ops.wm.read_homefile(use_empty=True)
    if _low.endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=SRC)
    elif _low.endswith((".usd", ".usdc", ".usda", ".usdz")):
        bpy.ops.wm.usd_import(filepath=SRC)
    else:
        bpy.ops.import_scene.fbx(filepath=SRC)
for o in list(bpy.data.objects):
    if o.type != "MESH" or (DROP and re.search(DROP, o.name, re.I)):
        if o.type == "MESH":
            print("holding back mesh '%s'" % o.name)
        bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.data.objects:
    for m in list(o.modifiers):
        if m.type == "ARMATURE":
            o.modifiers.remove(m)
    o.vertex_groups.clear()
    o.parent = None
    o.matrix_parent_inverse.identity()
bpy.context.view_layer.update()
print("exporting", [(o.name, len(o.data.vertices)) for o in bpy.data.objects])
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=False, path_mode="COPY",
                         embed_textures=True, apply_scale_options="FBX_SCALE_NONE",
                         object_types={"MESH"}, add_leaf_bones=False)
print("wrote", OUT)
