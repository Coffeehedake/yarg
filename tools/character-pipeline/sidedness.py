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

A DECAL IS NOT A PATCH, and that distinction is what makes the union safe. On
its own, by-material attribution reintroduces the exact bug the exporter was
fixed for: Ariel's `Ears`, `Irises` and `Lips` are patches of a CLOSED HEAD, and
measured on their own faces alone they look like open sheets -- the same three
materials that were the signature of the per-submesh bug in `YargCharExporter`.
Unioned naively it added six such false positives across 227 materials (those
three, Alcina's `Material.007` and `.013`, Sayuri's `Eyelashes`).

The discriminator is whether the material's own boundary edges are ALSO boundary
edges of the whole mesh:

  A DECAL  lies ON a surface. Its rim is free in the mesh too -- nothing else
           uses those edges. Sayuri's moles, Vegeta's Material_46.
  A PATCH  is part of a surface. Its rim is shared with the neighbouring
           material, so in the whole mesh those edges are used twice and the
           surface is closed. Ariel's lips, ears and irises.

So by-material may only rescue a material whose own-face rim is genuinely open
in the full mesh.

WHERE THAT LEAVES IT, measured over all 227 materials of the 17 characters that
carry a flip -- not over the 34 flips alone, which can only ever show one
direction of error:

  224 of 227 agree with the exporter.
  0   undercounts: everything the exporter calls a sheet, this now calls a sheet.
  3   disagreements, and an isolated render says the EXPORTER is wrong on two:

    Sayuri   `Eyelashes`      check 69.9%, exporter 0.0%  -- render: CLOSED,
                              0.00% lost in all three views. The check is
                              overcounting; these lashes are modelled as solid
                              volume, not cards. Known residual defect.
    Alcina   `Material.007`   check 100%,  exporter 0.0%  -- render: 1.42% lost
    Alcina   `Material.013`   check 100%,  exporter 0.0%  -- render: 2.05% lost
                              from behind. The EXPORTER is undercounting these
                              two; they are genuine sheets it culls.

That last pair is a defect in `YargCharExporter.cs`, not here, and it could only
surface by comparing every material rather than only the ones it flipped.

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
    mesh_edge = collections.Counter()      # edge usage across the WHOLE mesh
    def wkey(v):
        return (round(v.x*Q), round(v.y*Q), round(v.z*Q))
    for o in [x for x in bpy.data.objects if x.type == "MESH"]:
        me = o.data
        for poly in me.polygons:
            vs = [o.matrix_world @ me.vertices[i].co for i in poly.vertices]
            ks = [wkey(v) for v in vs]
            for i in range(len(ks)):
                mesh_edge[tuple(sorted((ks[i], ks[(i+1) % len(ks)])))] += 1
            if poly.material_index >= len(o.material_slots): continue
            slot = o.material_slots[poly.material_index].material
            if slot is None: continue
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
            blen = 0.0; free = 0; rim = 0
            for (p_, q_), n in edge.items():
                if n != 1: continue
                ka, kb = inv[p_], inv[q_]
                pa = Vector([x/Q for x in ka]); pb = Vector([x/Q for x in kb])
                blen += (pa-pb).length
                rim += 1
                # Free in the WHOLE mesh, not just within this material: that is
                # what separates a decal lying on a surface from a patch of one.
                if mesh_edge.get(tuple(sorted((ka, kb))), 0) <= 1: free += 1
            openness = blen/math.sqrt(area); solidity = abs(vol)/(area**1.5)
            total_a += area
            decal = rim > 0 and free >= rim * 0.5
            if openness > OPEN_MIN and solidity < SOLID_MIN and decal: sheet_a += area
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
