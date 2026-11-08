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
# MIXAMO_UP="<hipsBone>,<headBone>" stands a POSED SCULPT up before export.
#
# Mixamo wants an upright mesh and will not make sense of one that is not. Anakin
# Skywalker's geometry is a mid-air leap, lying 102 degrees off vertical, so it
# has to be turned before it is uploaded -- and turned RIGIDLY, by rotating every
# vertex together, because the whole reason to go to Mixamo is that this model's
# own weights cannot straighten anything without tearing it. A rotation deforms
# nothing.
#
# Name the bones explicitly: a rig like this one calls them 'Bone' and
# 'Bone.004', so nothing can be inferred from the names.
import os
UP_SPEC = os.environ.get("MIXAMO_UP", "")
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
# Work the rotation out BEFORE the armature is thrown away.
from mathutils import Vector
_R = None
if UP_SPEC:
    _hips, _head = [x.strip() for x in UP_SPEC.split(",")][:2]
    _arm = max((o for o in bpy.data.objects if o.type == "ARMATURE"),
               key=lambda o: len(o.data.bones))
    bpy.context.view_layer.update()
    _pb = _arm.pose.bones
    _M = _arm.matrix_world
    _up = (_M @ _pb[_head].head) - (_M @ _pb[_hips].head)
    if _up.length < 1e-9:
        raise SystemExit("ABORT: MIXAMO_UP bones are in the same place")
    _R = _up.normalized().rotation_difference(Vector((0.0, 0.0, 1.0))).to_matrix().to_4x4()
    print("standing up: %s->%s ran %.1f deg off vertical"
          % (_hips, _head,
             __import__("math").degrees(__import__("math").acos(
                 max(-1.0, min(1.0, _up.normalized().dot(Vector((0.0, 0.0, 1.0)))))))))

# Bake any existing skinning into the geometry FIRST.
#
# A partly-rigged model keeps its skinned meshes at BIND position while its
# unrigged ones sit wherever they were sculpted. Throw the armature away without
# baking and the two disagree: Anakin uploaded as a headless body with his head
# floating beside it, because his head is the one mesh the file had skinned.
#
# Evaluate each with only its armature modifier on and copy the result back --
# the same reason as in build_vrm.py, and the same caveat: a Solidify or
# Subdivision ahead of it would change the vertex count, so check.
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    if not any(m.type == "ARMATURE" for m in o.modifiers):
        continue
    _saved = [(m, m.show_viewport) for m in o.modifiers]
    for _m, _ in _saved:
        if _m.type != "ARMATURE":
            _m.show_viewport = False
    _dg = bpy.context.evaluated_depsgraph_get()
    _ev = o.evaluated_get(_dg)
    _me = _ev.to_mesh()
    _co = [v.co.copy() for v in _me.vertices]
    _ev.to_mesh_clear()
    for _m, _flag in _saved:
        _m.show_viewport = _flag
    if len(_co) != len(o.data.vertices):
        print("WARNING: could not bake the pose into '%s'" % o.name)
        continue
    if o.data.users > 1:
        o.data = o.data.copy()
    for _v, _c in zip(o.data.vertices, _co):
        _v.co = _c
    o.data.update()
    print("baked the existing skinning into '%s'" % o.name)
bpy.context.view_layer.update()

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
if _R is not None:
    for o in bpy.data.objects:
        if o.data.users > 1:
            o.data = o.data.copy()
        o.data.transform(_R @ o.matrix_world, shape_keys=True)
        o.data.update()
        o.matrix_basis.identity()
    bpy.context.view_layer.update()
    _pts = [v.co for o in bpy.data.objects for v in o.data.vertices]
    print("stood up: now %.2f m tall, %.2f wide, %.2f deep"
          % (max(p.z for p in _pts) - min(p.z for p in _pts),
             max(p.x for p in _pts) - min(p.x for p in _pts),
             max(p.y for p in _pts) - min(p.y for p in _pts)))
# Join everything into ONE mesh.
#
# Mixamo's auto-rigger wants a single mesh and fails quietly on a set of them:
# the job is accepted (PUT .../rig -> 202), the monitor polls to 200, and then
# the page simply reloads the UNRIGGED asset with no error anywhere on screen.
# Anakin failed that way three times as ten separate objects -- body, head,
# eyes, hair, tabards -- while every model that has rigged successfully here went
# up as one. Joining keeps the materials: they become slots on the joined mesh.
_objs = [o for o in bpy.data.objects if o.type == "MESH"]
if len(_objs) > 1:
    bpy.ops.object.select_all(action="DESELECT")
    for _o in _objs:
        _o.select_set(True)
    bpy.context.view_layer.objects.active = _objs[0]
    bpy.ops.object.join()
    _j = bpy.context.view_layer.objects.active
    print("joined %d meshes into one: %d verts, %d material slot(s)"
          % (len(_objs), len(_j.data.vertices), len(_j.data.materials)))

bpy.context.view_layer.update()
print("exporting", [(o.name, len(o.data.vertices)) for o in bpy.data.objects])
# MIXAMO_NO_TEX=1 drops the embedded textures. The browser upload is capped at
# 10 MB and Mando's embedded export is 12.6 MB; the auto-rigger only needs the
# geometry, and build_vrm.py re-applies the textures from the archive's own
# texture folder afterwards anyway.
_EMBED = not os.environ.get("MIXAMO_NO_TEX")
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=False,
                         path_mode="COPY" if _EMBED else "AUTO",
                         embed_textures=_EMBED, apply_scale_options="FBX_SCALE_NONE",
                         object_types={"MESH"}, add_leaf_bones=False)
print("wrote", OUT)
