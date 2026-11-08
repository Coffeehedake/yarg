import sys, bpy, bmesh
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_homefile(use_empty=True)
low = SRC.lower()
if low.endswith(".blend"): bpy.ops.wm.open_mainfile(filepath=SRC)
elif low.endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=SRC)
elif low.endswith((".usd",".usdc",".usda",".usdz")): bpy.ops.wm.usd_import(filepath=SRC)
else: bpy.ops.import_scene.fbx(filepath=SRC)
for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen=set(); isl=[]
    for v in bm.verts:
        if v.index in seen: continue
        stack=[v]; comp=[]
        seen.add(v.index)
        while stack:
            x=stack.pop(); comp.append(x)
            for e in x.link_edges:
                y=e.other_vert(x)
                if y.index not in seen:
                    seen.add(y.index); stack.append(y)
        isl.append(comp)
    isl.sort(key=len, reverse=True)
    print("MESH %s  %d islands" % (o.name, len(isl)))
    for i, c in enumerate(isl[:12]):
        lo=Vector((min(p.co.x for p in c), min(p.co.y for p in c), min(p.co.z for p in c)))
        hi=Vector((max(p.co.x for p in c), max(p.co.y for p in c), max(p.co.z for p in c)))
        print("   island %-2d verts=%-6d  x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f"
              % (i, len(c), lo.x,hi.x, lo.y,hi.y, lo.z,hi.z))
    bm.free()
print("DONE")
