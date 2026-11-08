import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    nz = 0
    for v in o.data.vertices:
        if v.groups: nz += 1
    print("%s parent_type=%s vgroups=%d verts_with_weights=%d/%d mods=%s shapekeys=%s" % (
        o.name, o.parent_type, len(o.vertex_groups), nz, len(o.data.vertices),
        [m.type for m in o.modifiers],
        len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0))
print("DONE")
