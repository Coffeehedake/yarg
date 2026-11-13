"""Decide per MATERIAL whether its geometry needs drawing double-sided.

    blender --background --python sidedness.py -- file.vrm

The question is not "what does the file's doubleSided flag say" -- that is almost
always true because Blender's glTF exporter defaults it that way -- but "does
this material's geometry HAVE a back face". Two numbers answer it, per connected
piece of surface (vertices welded by position so UV seams do not split a piece):

  OPENNESS   boundary_edge_length / sqrt(surface_area)
             An edge used by one triangle is a boundary. A closed solid with a
             small hole (a wrist, a neck) has a tiny boundary against its area;
             a single-layer sheet is boundary all the way round. A flat disc
             scores 2*sqrt(pi) = 3.5; a sphere with a hole of 1/10 its radius
             scores 0.18.

  SOLIDITY   |signed volume| / area^1.5, about the piece's own centroid.
             A sphere scores 0.094, a limb-shaped cylinder 0.058, and anything
             with no enclosed volume -- an open sheet, a single-layer card --
             scores about 0. This is what tells a CAPE (big, few boundary edges
             relative to its area, but no volume) from a TORSO.

A piece needs double-sided when it is open AND has no volume. Both, because
either alone is wrong: openness alone condemns every solid with a wrist hole,
and solidity alone condemns a closed paper-thin slab that has a real back face
and culls perfectly well.

The verdict is per MATERIAL and a material spans pieces, so a material is drawn
double-sided when a meaningful share of its AREA sits in sheet pieces.
"""
import sys, math, collections
import bpy, bmesh
from mathutils import Vector

# Must match YargCharExporter.cs. That file carries the reasoning for the
# values and the sensitivity data behind them; this is the cross-check, so if
# the two ever drift the check silently stops being one.
OPEN_MIN = 1.5      # boundary/sqrt(area) above this is "open all the way round"
SOLID_MIN = 0.02    # |V|/A^1.5 below this is "encloses nothing"
AREA_SHARE = 0.20   # fraction of a material's area that must be sheet
MIN_FACES = 12

src = sys.argv[sys.argv.index("--")+1:][0]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

mat_area = collections.Counter()
mat_sheet = collections.Counter()
detail = collections.defaultdict(list)

for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bm.faces.ensure_lookup_table()
    seen = set()
    for f0 in bm.faces:
        if f0.index in seen: continue
        stack=[f0]; grp=[]; seen.add(f0.index)
        while stack:
            c = stack.pop(); grp.append(c)
            for e in c.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index); stack.append(nf)
        if len(grp) < MIN_FACES: continue

        area = sum(f.calc_area() for f in grp)
        if area <= 0: continue
        cen = Vector((0,0,0)); 
        for f in grp: cen += f.calc_center_median() * f.calc_area()
        cen /= area
        vol = 0.0
        for f in grp:
            vs = f.verts
            for k in range(1, len(vs)-1):
                a = vs[0].co - cen; b = vs[k].co - cen; c = vs[k+1].co - cen
                vol += a.dot(b.cross(c)) / 6.0
        edges = set()
        for f in grp:
            for e in f.edges: edges.add(e)
        blen = sum(e.calc_length() for e in edges if len(e.link_faces) == 1)

        openness = blen / math.sqrt(area)
        solidity = abs(vol) / (area ** 1.5)
        sheet = (openness > OPEN_MIN) and (solidity < SOLID_MIN)

        mats = collections.Counter()
        for f in grp:
            if f.material_index < len(o.material_slots) and o.material_slots[f.material_index].material:
                mats[o.material_slots[f.material_index].material.name] += f.calc_area()
        print("PIECE	%s	%d	%.6f	%.6f	%.6f	%s" % (
            (mats.most_common(1)[0][0] if mats else "?"), len(grp), area, openness, solidity, sheet))
        for mn, a in mats.items():
            mat_area[mn] += a
            if sheet: mat_sheet[mn] += a
            detail[mn].append((a, openness, solidity, sheet, len(grp)))

print("MATERIAL VERDICTS for %s" % src.replace("\\","/").split("/")[-1])
for mn in sorted(mat_area, key=lambda m: -mat_sheet[m]/max(mat_area[m],1e-9)):
    share = mat_sheet[mn] / max(mat_area[mn], 1e-9)
    worst = max(detail[mn], key=lambda d: d[0])
    print("VERDICT %-30s %-13s sheet-area %5.1f%%  (largest piece: %d faces, open %.2f, solid %.4f)"
          % (mn[:30], "DOUBLE-SIDED" if share >= AREA_SHARE else "culled",
             100*share, worst[4], worst[1], worst[2]))
