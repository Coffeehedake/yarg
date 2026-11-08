"""Power Girl arrives as a Sketchfab .blend: Y-up, with a backdrop plane, and a
14-bone toy rig that has no hands, no feet and only one forearm -- nothing VRM
can accept. Strip it to the geometry, stand it up, and let Mixamo rig it."""
import sys, math, bpy
from mathutils import Matrix, Vector
SRC, OUT = sys.argv[sys.argv.index("--")+1:][:2]
bpy.ops.wm.open_mainfile(filepath=SRC)
for o in list(bpy.data.objects):
    if o.type != "MESH" or o.name.startswith("pg_back"):
        bpy.data.objects.remove(o, do_unlink=True)
for o in bpy.data.objects:
    for m in list(o.modifiers):
        if m.type == "ARMATURE":
            o.modifiers.remove(m)
    o.vertex_groups.clear()
    o.parent = None
    o.matrix_parent_inverse.identity()
bpy.context.view_layer.update()
# Stand it up: this file's height runs along Y.
R = Matrix.Rotation(math.radians(90.0), 4, "X")
for o in bpy.data.objects:
    mw = R @ o.matrix_world
    if o.data.users > 1:
        o.data = o.data.copy()
    o.data.transform(mw)
    o.matrix_basis.identity()
lo = Vector((1e18,)*3); hi = Vector((-1e18,)*3)
for o in bpy.data.objects:
    for v in o.data.vertices:
        for i in range(3):
            lo[i] = min(lo[i], v.co[i]); hi[i] = max(hi[i], v.co[i])
print("after standing up: %.3f x %.3f x %.3f" % tuple(hi - lo))
bpy.ops.export_scene.fbx(filepath=OUT, use_selection=False, path_mode="COPY",
                         embed_textures=True, object_types={"MESH"}, add_leaf_bones=False)
print("wrote", OUT)
