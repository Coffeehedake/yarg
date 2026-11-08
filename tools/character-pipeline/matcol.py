import sys, os, bpy
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.open_mainfile(filepath=SRC)
use = {}
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    for ms in o.material_slots:
        if ms.material: use.setdefault(ms.material.name, []).append((o.name, len(o.data.vertices)))
for m in bpy.data.materials:
    if m.name not in use: continue
    col = None; tex = []
    if m.use_nodes and m.node_tree:
        b = next((n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED"), None)
        if b: col = tuple(round(v,3) for v in b.inputs["Base Color"].default_value[:3])
        tex = [os.path.basename((n.image.filepath or n.image.name).replace("\\","/"))
               for n in m.node_tree.nodes if n.type=="TEX_IMAGE" and n.image]
    print("%-16s col=%-22s tex=%-40s meshes=%s" % (m.name, col, tex[:2], use[m.name][:2]))
print("DONE")
