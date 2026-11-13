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
    edge = defaultdict(int)
    area = 0.0; cen = mathutils.Vector((0, 0, 0))
    for t, (a, b, c) in T:
        for i in range(3):
            e = tuple(sorted((t[i], t[(i+1) % 3])))
            edge[e] += 1
        ar = (b - a).cross(c - a).length / 2.0
        area += ar; cen += (a + b + c) / 3.0 * ar
    if area <= 0: print("%-34s ZERO AREA" % want); continue
    cen /= area
    vol = 0.0
    for _t, (a, b, c) in T:
        vol += (a - cen).dot((b - cen).cross(c - cen)) / 6.0
    bnd = sum(1 for e, n in edge.items() if n == 1)
    blen = 0.0
    inv = {v: k for k, v in ids.items()}
    for (p, q), n in edge.items():
        if n != 1: continue
        pa = mathutils.Vector([x / Q for x in inv[p]]); pb = mathutils.Vector([x / Q for x in inv[q]])
        blen += (pa - pb).length
    openness = blen / math.sqrt(area) if area > 0 else 0.0
    solidity = abs(vol) / (area ** 1.5) if area > 0 else 0.0
    print("%-34s faces=%-6d area=%.5f  boundary edges=%-5d  open=%.2f  solid=%.4f  -> %s"
          % (want, len(T), area, bnd, openness, solidity,
             "SHEET" if (openness > 1.5 and solidity < 0.02) else "not a sheet"))
