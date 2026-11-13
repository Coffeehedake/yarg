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

TWO ATTRIBUTIONS, UNIONED -- added 2026-11-13 after this check disagreed with the
exporter on two of 34 flips and was WRONG BOTH TIMES.

  BY PIECE     the original: build connected pieces across a whole mesh and ask
               what share of a material's area lands in sheet pieces.
  BY MATERIAL  build pieces from THAT MATERIAL'S OWN FACES only.

They differ exactly where a decal shares a surface with a solid. Sayuri's
`Moles` is 12 triangles whose vertices coincide with her body, so by piece they
weld into a 25,648-face BODY piece -- a closed body, "not a sheet", 0.0% -- while
by material they are a 12-triangle patch at open 4.75, solid 0.0161, a sheet at
100%. An isolated geometry-only render settles it: culled, her moles DISAPPEAR
COMPLETELY. Vegeta's `Material_46` is the same shape of error and loses 12.79%
of its silhouette from behind when culled.

A union is the right combination rather than a replacement, because each
attribution UNDERCOUNTS on its own and neither overcounts: measured over all 34
flips the exporter was vindicated by render every time, by-piece missed 2 and
by-material missed 4 (Alice Ivy's `Teeth`, Ariel's three `Brows`). Taking either
as sufficient can therefore only move toward the render-confirmed answer.

None of which makes this an arbiter. Use `isolate.py` for anything disputed: it
replaces the material with a matte stand-in and asks whether culling the faces
loses geometry a viewer could see, which is the only question that matters.
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

# ---- second attribution: each material's OWN faces, as connected pieces ----
Q = 10000.0   # 0.1 mm, the exporter's WeldQuant

def by_material():
    tri = collections.defaultdict(list)
    for o in [x for x in bpy.data.objects if x.type == "MESH"]:
        me = o.data
        for poly in me.polygons:
            if poly.material_index >= len(o.material_slots): continue
            slot = o.material_slots[poly.material_index].material
            if slot is None: continue
            vs = [o.matrix_world @ me.vertices[i].co for i in poly.vertices]
            for k in range(1, len(vs)-1):
                tri[slot.name].append((vs[0], vs[k], vs[k+1]))
    out = {}
    for name, tris in tri.items():
        ids = {}; T = []
        for a, b, c in tris:
            t = []
            for v in (a, b, c):
                key = (round(v.x*Q), round(v.y*Q), round(v.z*Q))
                if key not in ids: ids[key] = len(ids)
                t.append(ids[key])
            T.append((t, (a, b, c)))
        adj = collections.defaultdict(set)
        for i, (t, _g) in enumerate(T):
            for k in range(3): adj[tuple(sorted((t[k], t[(k+1)%3])))].add(i)
        parent = list(range(len(T)))
        def find(a):
            while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for _e, fs in adj.items():
            fs = sorted(fs)
            for f in fs[1:]:
                ra, rb = find(fs[0]), find(f)
                if ra != rb: parent[ra] = rb
        groups = collections.defaultdict(list)
        for i in range(len(T)): groups[find(i)].append(i)
        inv = {v: k for k, v in ids.items()}
        sheet_a = 0.0; total_a = 0.0
        for _r, fs in groups.items():
            if len(fs) < MIN_FACES: continue
            edge = collections.Counter(); area = 0.0; cen = Vector((0,0,0))
            for i in fs:
                t, (a, b, c) = T[i]
                for k in range(3): edge[tuple(sorted((t[k], t[(k+1)%3])))] += 1
                ar = (b-a).cross(c-a).length/2.0
                area += ar; cen += (a+b+c)/3.0*ar
            if area <= 0: continue
            cen /= area
            vol = 0.0
            for i in fs:
                _t, (a, b, c) = T[i]
                vol += (a-cen).dot((b-cen).cross(c-cen))/6.0
            blen = 0.0
            for (p_, q_), n in edge.items():
                if n != 1: continue
                pa = Vector([x/Q for x in inv[p_]]); pb = Vector([x/Q for x in inv[q_]])
                blen += (pa-pb).length
            openness = blen/math.sqrt(area); solidity = abs(vol)/(area**1.5)
            total_a += area
            if openness > OPEN_MIN and solidity < SOLID_MIN: sheet_a += area
        out[name] = (sheet_a/total_a) if total_a > 0 else 0.0
    return out

own = by_material()

print("MATERIAL VERDICTS for %s" % src.replace("\\","/").split("/")[-1])
for mn in sorted(set(mat_area) | set(own),
                 key=lambda m: -max(mat_sheet[m]/max(mat_area[m],1e-9), own.get(m, 0.0))):
    piece_share = mat_sheet[mn] / max(mat_area[mn], 1e-9) if mn in mat_area else 0.0
    own_share = own.get(mn, 0.0)
    share = max(piece_share, own_share)
    note = ""
    if (piece_share >= AREA_SHARE) != (own_share >= AREA_SHARE):
        note = "  [by-piece %.1f%% vs by-material %.1f%% -- UNION applied]" % (100*piece_share, 100*own_share)
    if detail[mn]:
        worst = max(detail[mn], key=lambda d: d[0])
        where = "(largest piece: %d faces, open %.2f, solid %.4f)" % (worst[4], worst[1], worst[2])
    else:
        where = "(no piece above the %d-triangle minimum by piece)" % MIN_FACES
    print("VERDICT %-30s %-13s sheet-area %5.1f%%  %s%s"
          % (mn[:30], "DOUBLE-SIDED" if share >= AREA_SHARE else "culled",
             100*share, where, note))
