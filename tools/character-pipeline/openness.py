"""Open sheet or closed solid? The question that decides whether a material
HONESTLY needs _Cull 0.

A closed piece has every edge shared by exactly two faces; a sheet has a
boundary. Only a sheet has no back face to fall back on, so only a sheet is
broken by culling in a way that double-siding legitimately fixes. A closed piece
that renders wrong is wound inside-out and wants its winding fixed instead.

    blender --background --python openness.py -- file.vrm
"""
import collections, sys
import bpy, bmesh

src = sys.argv[sys.argv.index("--")+1:][0]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

for o in [x for x in bpy.data.objects if x.type=="MESH"]:
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bm.faces.ensure_lookup_table()
    # connected pieces by shared edge
    seen=set(); pieces=[]
    for f in bm.faces:
        if f.index in seen: continue
        stack=[f]; grp=[]
        seen.add(f.index)
        while stack:
            c=stack.pop(); grp.append(c)
            for e in c.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index); stack.append(nf)
        pieces.append(grp)
    rows=[]
    for grp in pieces:
        if len(grp) < 60: continue
        edges=set()
        for f in grp:
            for e in f.edges: edges.add(e)
        boundary=sum(1 for e in edges if len(e.link_faces)==1)
        zs=[v.co.z for f in grp for v in f.verts]
        mats=collections.Counter(o.material_slots[f.material_index].material.name
                                 for f in grp if f.material_index < len(o.material_slots)
                                 and o.material_slots[f.material_index].material)
        rows.append((len(grp), boundary, min(zs), max(zs), mats.most_common(1)[0][0]))
    rows.sort(key=lambda r: -r[0])
    for n,b,z0,z1,m in rows[:18]:
        kind = "CLOSED SOLID" if b==0 else ("OPEN SHEET (%d boundary edges)" % b)
        print("PIECE %-14s %-6d faces  z %5.2f..%5.2f  mat=%-22s %s"
              % (o.name[:14], n, z0, z1, m[:22], kind))
    bm.free()
