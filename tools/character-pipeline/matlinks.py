import sys, bpy, os
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
for m in bpy.data.materials:
    if not m.use_nodes: continue
    bsdf = next((n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED"), None)
    if bsdf is None: continue
    for inp in ("Base Color","Normal","Emission Color"):
        if inp not in bsdf.inputs: continue
        li = bsdf.inputs[inp].links
        if not li: continue
        n = li[0].from_node
        seen=set()
        stack=[n]
        while stack:
            x=stack.pop()
            if x in seen: continue
            seen.add(x)
            if x.type=="TEX_IMAGE" and x.image:
                print("%-18s %-14s -> %s  packed=%s size=%s" % (m.name, inp, os.path.basename(x.image.filepath) or x.image.name, bool(x.image.packed_file), tuple(x.image.size)))
            for i in x.inputs:
                for l in i.links: stack.append(l.from_node)
print("DONE")
