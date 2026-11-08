import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
o = next(x for x in bpy.data.objects if x.type=="MESH")
idx = {g.index: g.name for g in o.vertex_groups}
cnt = {}
for v in o.data.vertices:
    for g in v.groups:
        if g.weight > 0.3:
            cnt[idx[g.group]] = cnt.get(idx[g.group], 0) + 1
for n, c in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print("  %-14s %d" % (n, c))
print("TOTAL verts", len(o.data.vertices))
print("DONE")
