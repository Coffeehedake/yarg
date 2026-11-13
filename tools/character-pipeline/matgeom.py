# Openness and solidity for ONE MATERIAL'S OWN FACES, with no rendering.
#
#   blender --background --python matgeom.py -- <in.vrm> <material> [...]
#
# This is the question the exporter and sidedness.py answer differently. The
# exporter builds connected pieces within a MESH; sidedness.py builds them
# across the whole scene. Where a decal lies on a body and shares its vertex
# positions, those give opposite answers -- Sayuri's moles weld into a
# 25,648-face body piece in one and stay a 12-face patch in the other.
#
# The isolated render already settled Sayuri: culled, the moles vanish
# completely from behind; unculled they are there. So the material's OWN faces
# are what culling acts on, and that is what this measures.
import math, sys
from collections import defaultdict
import bpy, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.vrm(filepath=argv[0])
Q = 10000.0   # 0.1 mm, the exporter's WeldQuant

for want in argv[1:]:
    tris = []
    for o in [x for x in bpy.data.objects if x.type == "MESH"]:
        idx = [i for i, s in enumerate(o.material_slots) if s.material and s.material.name == want]
        if not idx: continue
        me = o.data
        for p in me.polygons:
            if p.material_index not in idx: continue
            vs = [o.matrix_world @ me.vertices[i].co for i in p.vertices]
            for k in range(1, len(vs) - 1):
                tris.append((vs[0], vs[k], vs[k+1]))
    if not tris:
        print("%-34s NO FACES" % want); continue
    key = lambda v: (round(v.x*Q), round(v.y*Q), round(v.z*Q))
    ids = {}; T = []
    for a, b, c in tris:
        t = []
        for v in (a, b, c):
            k = key(v)
            if k not in ids: ids[k] = len(ids)
            t.append(ids[k])
        T.append((t, (a, b, c)))
    # Split into CONNECTED PIECES first. Lumping a material's faces together
    # corrupts both numbers when they are not connected: several separate closed
    # blobs share one centroid, so their signed volumes partly cancel and the
    # boundary of all of them is divided by the area of all of them. The
    # exporter and sidedness.py both work per piece, so this must too.
    adj = defaultdict(set)
    for i, (t, _g) in enumerate(T):
        for k in range(3):
            adj[tuple(sorted((t[k], t[(k+1) % 3])))].add(i)
    parent = list(range(len(T)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb: parent[ra] = rb
    for e, fs in adj.items():
        fs = sorted(fs)
        for f in fs[1:]: union(fs[0], f)
    pieces = defaultdict(list)
    for i in range(len(T)): pieces[find(i)].append(i)

    print("%-30s %d face(s) in %d connected piece(s)" % (want, len(T), len(pieces)))
    sheet_area = 0.0; total_area = 0.0; rows = []
    for _r, fs in sorted(pieces.items(), key=lambda kv: -len(kv[1])):
        edge = defaultdict(int); area = 0.0; cen = mathutils.Vector((0, 0, 0))
        for i in fs:
            t, (a, b, c) = T[i]
            for k in range(3): edge[tuple(sorted((t[k], t[(k+1) % 3])))] += 1
            ar = (b - a).cross(c - a).length / 2.0
            area += ar; cen += (a + b + c) / 3.0 * ar
        if area <= 0: continue
        cen /= area
        vol = 0.0
        for i in fs:
            _t, (a, b, c) = T[i]
            vol += (a - cen).dot((b - cen).cross(c - cen)) / 6.0
        blen = 0.0
        inv = {v: k for k, v in ids.items()}
        for (p_, q_), n in edge.items():
            if n != 1: continue
            pa = mathutils.Vector([x / Q for x in inv[p_]]); pb = mathutils.Vector([x / Q for x in inv[q_]])
            blen += (pa - pb).length
        openness = blen / math.sqrt(area)
        solidity = abs(vol) / (area ** 1.5)
        is_sheet = openness > 1.5 and solidity < 0.02
        total_area += area
        if is_sheet: sheet_area += area
        rows.append((len(fs), area, openness, solidity, is_sheet))
    for n, area, op, so, sh in rows[:8]:
        print("   piece %-6d faces area=%.6f  open=%5.2f  solid=%.4f  %s"
              % (n, area, op, so, "SHEET" if sh else "-"))
    if len(rows) > 8: print("   ... %d more piece(s)" % (len(rows) - 8))
    share = 100.0 * sheet_area / total_area if total_area else 0.0
    print("   => sheet-area %.1f%%  -> %s  (exporter flips at >= 20%%)"
          % (share, "DOUBLE-SIDED" if share >= 20.0 else "culled"))
