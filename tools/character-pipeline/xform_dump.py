import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
for o in bpy.data.objects:
    mw = o.matrix_world
    l, r, s = mw.decompose()
    print("%-18s type=%-9s parent=%-14s loc=%s rotE=%s scale=%s" % (
        o.name, o.type, o.parent.name if o.parent else "-",
        tuple(round(v,3) for v in l),
        tuple(round(__import__("math").degrees(v),1) for v in r.to_euler()),
        tuple(round(v,5) for v in s)))
    if o.type == "MESH":
        for m in o.modifiers:
            print("    mod", m.type, getattr(m, "object", None))
print("DONE")
