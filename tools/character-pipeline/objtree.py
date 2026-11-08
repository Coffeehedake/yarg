import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
for o in bpy.data.objects:
    print("%-24s type=%-9s parent=%-16s ptype=%-9s scale=%s cons=%s mods=%s hide=%s inscene=%s" % (
        o.name, o.type, o.parent.name if o.parent else "-", o.parent_type,
        tuple(round(v,4) for v in o.matrix_world.to_scale()),
        [c.type for c in o.constraints], [m.type for m in o.modifiers],
        o.hide_viewport, o.name in bpy.context.scene.objects))
print("DONE")
