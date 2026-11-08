import sys, bpy
SRC = sys.argv[sys.argv.index("--")+1]; WANT = sys.argv[sys.argv.index("--")+2]
bpy.ops.wm.open_mainfile(filepath=SRC)
m = bpy.data.materials.get(WANT)
print("material", WANT, "found", m is not None)
if m and m.use_nodes:
    for n in m.node_tree.nodes:
        print("  node %-22s type=%s" % (n.name, n.type))
    b = next((n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED"), None)
    if b:
        for inp in ("Base Color","Alpha","Emission Color"):
            if inp in b.inputs:
                i = b.inputs[inp]
                print("  %-14s linked=%s from=%s dv=%s" % (inp, bool(i.links),
                    i.links[0].from_node.type if i.links else None,
                    tuple(round(v,3) for v in i.default_value[:4]) if hasattr(i.default_value,'__len__') else i.default_value))
    out = next((n for n in m.node_tree.nodes if n.type=="OUTPUT_MATERIAL"), None)
    if out and out.inputs["Surface"].links:
        print("  surface driven by:", out.inputs["Surface"].links[0].from_node.type)
print("DONE")
