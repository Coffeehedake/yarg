import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    nz = sum(1 for v in o.data.vertices if any(g.weight>0.01 for g in v.groups))
    print("MESH %s parent=%s ptype=%s mods=%s vgroups=%d weighted=%d/%d" % (
        o.name, o.parent.name if o.parent else "-", o.parent_type,
        [(m.type, getattr(m,'object',None).name if getattr(m,'object',None) else None) for m in o.modifiers],
        len(o.vertex_groups), nz, len(o.data.vertices)))
print("DONE")
