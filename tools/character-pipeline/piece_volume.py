"""Is a piece flagged INSIDE-OUT a solid shell, or a sheet whose volume sign is noise?

    blender --background --python piece_volume.py -- <file.vrm> [material] [min_faces]

WHY THIS EXISTS. `facing_check.py` splits a mesh into connected pieces and calls a piece
INSIDE-OUT when its signed volume (divergence theorem) is negative. That is the right test and
its docstring says so -- for a CLOSED piece. The same docstring also says a sheet "has no
inside: either share is plausible, so judge those by eye."

Those two statements meet on Pomni:

    VOLUME | Face piece 193 | 168 faces | z 1.16..1.20 | signed volume -0.00000 m3 | INSIDE-OUT

The verdict rests on the SIGN of a quantity printed as zero to five decimal places. For a
nearly-flat shell the enclosed volume approaches zero and its sign is decided by rounding and
vertex order rather than by which way the surface faces. So "INSIDE-OUT" there may be a true
statement about a float and no statement at all about the geometry.

WHAT THIS MEASURES, per piece, and why each number is here:

    faces, area          size, so a verdict on 168 faces is not read as a verdict on a mesh
    bbox (sorted)        the shape. A piece 40 x 30 x 0.2 mm is a sheet whatever its volume says
    flatness             smallest bbox side / largest. Near 0 is a sheet
    signed volume        FULL PRECISION, not rounded to the point where the sign is all that survives
    solidity             |V| / (A^1.5 / (6*sqrt(pi)))

SOLIDITY IS THE ONE THAT SETTLES IT, and it is dimensionless on purpose. A^1.5/(6*sqrt(pi)) is
the volume a sphere of that surface area would enclose -- the most volume any closed surface of
that area can hold. So solidity is 1.0 for a sphere, around 0.4-0.7 for ordinary closed body
parts, and collapses toward 0 as a shell flattens. A piece at 0.001 encloses a thousandth of the
volume its own area could, which is a sheet folded back on itself, and the sign of a number that
small is not evidence of anything.

A CONTROL IS PRINTED WHETHER OR NOT IT IS ASKED FOR. The largest piece in the file is measured
alongside, because a near-zero solidity means nothing without a piece from the same model that
is genuinely closed. If the control does not come out solid, this script is measuring wrongly
and says so rather than letting the suspect's number stand alone.
"""
import math
import sys
from collections import defaultdict

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
SRC = args[0]
WANT_MAT = args[1] if len(args) > 1 else None
MIN_FACES = int(args[2]) if len(args) > 2 else 100

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)


def pieces_of(obj):
    """Connected components over faces sharing an edge, with vertices welded by position.

    Welding by position matters: a piece split across duplicated vertices at a seam would
    otherwise come back as several open shells, each with a meaningless volume.
    """
    me = obj.data
    me.calc_loop_triangles()
    key = {}
    weld = []
    for v in me.vertices:
        k = (round(v.co.x, 6), round(v.co.y, 6), round(v.co.z, 6))
        if k not in key:
            key[k] = len(key)
        weld.append(key[k])

    tris = [(t.vertices[0], t.vertices[1], t.vertices[2], t.material_index)
            for t in me.loop_triangles]
    edge_faces = defaultdict(list)
    for i, (a, b, c, _m) in enumerate(tris):
        wa, wb, wc = weld[a], weld[b], weld[c]
        for e in ((wa, wb), (wb, wc), (wc, wa)):
            edge_faces[tuple(sorted(e))].append(i)

    parent = list(range(len(tris)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    # CONNECT ONLY ACROSS MANIFOLD EDGES -- edges shared by EXACTLY two faces. This matches
    # facing_check.py, and it is not a detail: joining faces across a non-manifold edge merges a
    # shell tucked inside another surface into its host. Measured on Pomni, unioning every shared
    # edge turns the 168-face piece that tool flags into a 992-face one, so the suspect piece is
    # never measured and a superset is reported in its place.
    for fs in edge_faces.values():
        if len(fs) != 2:
            continue
        union(fs[0], fs[1])

    groups = defaultdict(list)
    for i in range(len(tris)):
        groups[find(i)].append(i)
    return me, tris, groups, edge_faces, weld


def measure(obj, me, tris, idxs, edge_faces, weld):
    mw = obj.matrix_world
    co = [mw @ v.co for v in me.vertices]
    cen = Vector((0.0, 0.0, 0.0))
    for i in idxs:
        a, b, c, _m = tris[i]
        cen += (co[a] + co[b] + co[c]) / 3.0
    cen /= len(idxs)
    vol = 0.0
    vol_origin = 0.0
    area = 0.0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    shared2 = 0
    total_e = 0
    seen_e = set()
    for i in idxs:
        a, b, c, _m = tris[i]
        pa, pb, pc = co[a], co[b], co[c]
        # ABOUT THE PIECE'S OWN CENTROID, not the origin, matching facing_check.py. For a surface
        # that is perfectly closed the two agree, because the divergence theorem does not care
        # where the origin is. For one that is only 95% closed -- which this test explicitly
        # allows -- they do NOT agree, and on a piece whose volume is near zero the REFERENCE
        # POINT can decide the sign. That is worth knowing about a verdict that is a sign.
        vol += (pa - cen).dot((pb - cen).cross(pc - cen)) / 6.0
        vol_origin += pa.dot(pb.cross(pc)) / 6.0
        area += (pb - pa).cross(pc - pa).length / 2.0
        for p in (pa, pb, pc):
            lo.x = min(lo.x, p.x); lo.y = min(lo.y, p.y); lo.z = min(lo.z, p.z)
            hi.x = max(hi.x, p.x); hi.y = max(hi.y, p.y); hi.z = max(hi.z, p.z)
        wa, wb, wc = weld[a], weld[b], weld[c]
        for e in ((wa, wb), (wb, wc), (wc, wa)):
            k = tuple(sorted(e))
            if k in seen_e:
                continue
            seen_e.add(k)
            total_e += 1
            if len(edge_faces[k]) == 2:
                shared2 += 1

    dims = sorted([hi.x - lo.x, hi.y - lo.y, hi.z - lo.z])
    flat = (dims[0] / dims[2]) if dims[2] > 0 else 0.0
    # The most volume any closed surface of this area could enclose: a sphere.
    vmax = (area ** 1.5) / (6.0 * math.sqrt(math.pi)) if area > 0 else 0.0
    solidity = (abs(vol) / vmax) if vmax > 0 else 0.0
    closed = (shared2 / total_e) if total_e else 0.0
    return dict(faces=len(idxs), area=area, vol=vol, vol_origin=vol_origin, dims=dims,
                flat=flat, solidity=solidity, closed=closed, zlo=lo.z, zhi=hi.z)


rows = []
for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
    me, tris, groups, edge_faces, weld = pieces_of(obj)
    mats = [m.name if m else "<none>" for m in me.materials] or ["<none>"]
    for pid, idxs in groups.items():
        if len(idxs) < MIN_FACES:
            continue
        mi = defaultdict(int)
        for i in idxs:
            mi[tris[i][3]] += 1
        top = max(mi.items(), key=lambda kv: kv[1])[0]
        mat = mats[top] if top < len(mats) else "<none>"
        r = measure(obj, me, tris, idxs, edge_faces, weld)
        r["obj"] = obj.name
        r["mat"] = mat
        rows.append(r)

print("")
print("PIECE         faces      area m2   vol(centroid)      vol(origin)   solidity  flat  closed  z range        material")
for r in sorted(rows, key=lambda r: r["solidity"]):
    mark = ""
    if WANT_MAT and r["mat"] == WANT_MAT:
        mark = "  <-- asked for"
    # FULL material name, never truncated. Three of Scott Hall's materials share the first
    # fourteen characters -- Mouth, Teeth and Tongue all begin "Scott_Hall_OGs" -- so a
    # truncated column cannot say which piece a verdict is about.
    print("%-12s %5d  %11.8f %+15.10f %+15.10f  %8.5f %5.3f %5.1f%%  %.3f..%.3f  %s%s"
          % (r["obj"][:12], r["faces"], r["area"], r["vol"], r["vol_origin"],
             r["solidity"], r["flat"], 100 * r["closed"], r["zlo"], r["zhi"], r["mat"], mark))

if rows:
    ctrl = max(rows, key=lambda r: r["faces"])
    print("")
    print("CONTROL -- the largest piece in this file, which must come out SOLID for the")
    print("numbers above to mean anything:")
    print("  %s / %s: %d faces, solidity %.5f, flatness %.3f, %.1f%% of edges shared by two faces"
          % (ctrl["obj"], ctrl["mat"], ctrl["faces"], ctrl["solidity"], ctrl["flat"],
             100 * ctrl["closed"]))
    if ctrl["solidity"] < 0.05:
        print("  CONTROL FAILED: the biggest piece in the model reads as flat too, so this")
        print("  script is measuring wrongly and nothing above should be believed.")
    else:
        print("  CONTROL OK: a genuinely closed piece reads solid, so a near-zero solidity")
        print("  elsewhere is a statement about that piece.")
