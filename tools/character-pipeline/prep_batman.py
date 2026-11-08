"""Batman ships as TWO skeletal meshes on TWO armatures: the body (569 bones,
'NoCape') and a cape-plus-head attachment (388 bones, 'Cape1'). Taking either
alone gives half a character - the cape mesh is 2,099 verts of which 1,901 are
cape. The body armature carries the cape bones too, so rebind the cape onto it
and throw the second armature away, leaving one character on one skeleton."""
import sys

import bpy

SRC, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

body_arm = bpy.data.objects["Batman_NoCape_SkelMesh"]
cape_arm = bpy.data.objects["Batman_Cape1_SkelMesh"]
body_bones = {b.name for b in body_arm.data.bones}

for o in list(bpy.data.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)

cape_mesh = bpy.data.objects["Batman_Cape1_SkelMesh.001"]
groups = {g.name for g in cape_mesh.vertex_groups}
missing = sorted(groups - body_bones)
print("cape mesh groups: %d, missing from the body skeleton: %d %s"
      % (len(groups), len(missing), missing[:6]))

mw = cape_mesh.matrix_world.copy()
cape_mesh.parent = body_arm
cape_mesh.matrix_parent_inverse.identity()
cape_mesh.matrix_world = mw
for m in cape_mesh.modifiers:
    if m.type == "ARMATURE":
        m.object = body_arm
bpy.data.objects.remove(cape_arm, do_unlink=True)

bpy.context.view_layer.update()
for o in bpy.data.objects:
    if o.type == "MESH":
        print("  mesh %-32s verts=%-6d modifier->%s" % (
            o.name[:32], len(o.data.vertices),
            [m.object.name for m in o.modifiers if m.type == "ARMATURE" and m.object]))
print("armatures left:", [o.name for o in bpy.data.objects if o.type == "ARMATURE"])
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("saved", OUT)
