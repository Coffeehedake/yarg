"""Which way do a character's faces point, relative to the bone that drives them?

    blender --background --python facing_check.py -- <file.vrm> [min_faces]

For every face, take the bone that carries most of its weight, find the nearest point on that
bone's head-to-tail segment, and call the face OUTWARD if its normal points away from that point.
That works for legs, arms, fingers, the torso and the head in any pose, which "away from the body
axis" does not (an arm in a T-pose is nowhere near the body axis). Output is the outward share per
mesh and material.

Read it like this:
- a TEXTURED material well under 50% is clothing or skin modelled inside-out. It draws as its far
  interior under back-face culling, and the only reason it ever looked right is a hull drawn over it.
- an UNTEXTURED near-black material that hugs the body with inward normals is the outline hull
  itself. Low outward share is what it is meant to have.
- a sheet (cloth, hair card, ear) has no inside: either share is plausible, so judge those by eye.

The VOLUME lines are the exact test, and the one to trust for closed pieces. A connected piece of
surface (faces joined by shared edges, vertices welded by position) whose edges are at least 95%
shared by exactly two faces is a closed shell, and its signed volume (divergence theorem) is
positive when the faces point outward and NEGATIVE when the whole piece is inside-out. It needs no
bone, so it is right where the bone vote is wrong: Alastor's coat skirt is a closed shell driven by
the thigh bones, voted 52% outward, and had a negative volume. Open sheets (cloth, hair cards) have
no volume; for those only the outward share above means anything.

Alastor's coat, pants and boots read 0-12% before they were flipped. Faces within 1 cm of the bone
are skipped, so a bone running through the middle of a thin part does not decide it.
"""
import collections
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
SRC = args[0]
MIN_FACES = int(args[1]) if len(args) > 1 else 150

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
amw = arm.matrix_world
seg = {b.name: (amw @ b.head_local, amw @ b.tail_local) for b in arm.data.bones}


def nearest(p, a, b):
    ab = b - a
    t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return a + ab * t


def has_texture(mat):
    if not mat or not mat.use_nodes:
        return False
    return any(n.type == "TEX_IMAGE" and n.image for n in mat.node_tree.nodes)


name = SRC.replace("\\", "/").split("/")[-1]
rows = []
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    me = o.data
    mw = o.matrix_world
    n3 = mw.to_3x3()
    gname = {g.index: g.name for g in o.vertex_groups}
    st = collections.defaultdict(lambda: [0, 0])
    for p in me.polygons:
        mat = o.material_slots[p.material_index].material if p.material_index < len(o.material_slots) else None
        w = collections.Counter()
        for vi in p.vertices:
            for g in me.vertices[vi].groups:
                w[gname.get(g.group, "")] += g.weight
        best = next((b for b, _ in w.most_common() if b in seg), None)
        if best is None:
            continue
        c = mw @ p.center
        out = c - nearest(c, *seg[best])
        if out.length < 0.01:
            continue
        key = (o.name, mat.name if mat else "?", has_texture(mat))
        st[key][0] += 1
        st[key][1] += 1 if (n3 @ p.normal).normalized().dot(out.normalized()) > 0 else 0
    # Winding conflicts: of the manifold edges shared by exactly two faces (vertices welded by
    # position), how many have neighbours that DISAGREE about which way is out? A clean surface
    # reads ~0%. A surface with a mix of inverted and correct faces reads high, and that is what a
    # whole-group flip cannot repair: it flips the good faces with the bad.
    wid = {}
    weld = {}
    for p in me.polygons:
        for vi in p.vertices:
            if vi not in weld:
                co = me.vertices[vi].co
                weld[vi] = wid.setdefault((round(co.x * 1e4), round(co.y * 1e4), round(co.z * 1e4)), len(wid))
    edges = collections.defaultdict(list)
    for p in me.polygons:
        vs = [weld[v] for v in p.vertices]
        for i in range(len(vs)):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            if a != b:
                edges[(min(a, b), max(a, b))].append((p.material_index, 1 if a < b else -1))
    conf = collections.defaultdict(lambda: [0, 0])
    for fl in edges.values():
        if len(fl) == 2 and fl[0][0] == fl[1][0]:
            m = o.material_slots[fl[0][0]].material if fl[0][0] < len(o.material_slots) else None
            key = (o.name, m.name if m else "?")
            conf[key][0] += 1
            if fl[0][1] == fl[1][1]:      # same direction: the neighbours disagree
                conf[key][1] += 1
    for (mn, mat, tex), (n, k) in st.items():
        if n >= MIN_FACES:
            ce, ck = conf.get((mn, mat), [0, 0])
            rows.append((100.0 * k / n, mn, mat, tex, n, (100.0 * ck / ce) if ce else -1.0))

rows.sort()
for share, mn, mat, tex, n, conflict in rows:
    print("FACING %s | %s | %s | %s | %d faces | %.0f%% outward | %s winding conflicts" % (
        name, mn, mat, "textured" if tex else "untextured", n, share,
        ("%.0f%%" % conflict) if conflict >= 0 else "n/a"))


# ------------------------------------------------------------------ exact test: signed volume
def pieces_report():
    closed_total = 0
    inside_out = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        me = o.data
        mw = o.matrix_world
        n3 = mw.to_3x3()
        polys = list(me.polygons)
        if len(polys) < 100:
            continue
        wid, weld = {}, {}
        for p in polys:
            for vi in p.vertices:
                if vi not in weld:
                    co = me.vertices[vi].co
                    weld[vi] = wid.setdefault((round(co.x * 1e4), round(co.y * 1e4), round(co.z * 1e4)), len(wid))
        edges = collections.defaultdict(list)
        for p in polys:
            vs = [weld[v] for v in p.vertices]
            for i in range(len(vs)):
                a, b = vs[i], vs[(i + 1) % len(vs)]
                if a != b:
                    edges[(min(a, b), max(a, b))].append(p.index)
        adj = collections.defaultdict(list)
        for fl in edges.values():
            if len(fl) == 2:
                adj[fl[0]].append(fl[1])
                adj[fl[1]].append(fl[0])
        comp = {}
        nc = 0
        for p in polys:
            if p.index in comp:
                continue
            comp[p.index] = nc
            stack = [p.index]
            while stack:
                f = stack.pop()
                for g in adj[f]:
                    if g not in comp:
                        comp[g] = nc
                        stack.append(g)
            nc += 1
        ecount = collections.defaultdict(lambda: [0, 0])
        for fl in edges.values():
            c = comp[fl[0]]
            ecount[c][1] += 1
            if len(fl) == 2:
                ecount[c][0] += 1
        byc = collections.defaultdict(list)
        for p in polys:
            byc[comp[p.index]].append(p)
        for cid, ps in byc.items():
            if len(ps) < 100:
                continue
            e2, et = ecount[cid]
            if et == 0 or e2 / et < 0.95:
                continue                      # not a closed shell: no volume to judge
            closed_total += 1
            cen = Vector((0.0, 0.0, 0.0))
            for p in ps:
                cen += mw @ p.center
            cen /= len(ps)
            vol = 0.0
            for p in ps:
                vol += p.area * ((mw @ p.center) - cen).dot((n3 @ p.normal).normalized()) / 3.0
            if vol < 0:
                mats = collections.Counter(
                    o.material_slots[p.material_index].material.name
                    if p.material_index < len(o.material_slots) and o.material_slots[p.material_index].material else "?"
                    for p in ps)
                zs = [(mw @ p.center).z for p in ps]
                inside_out.append((len(ps), o.name, cid, min(zs), max(zs), vol, mats.most_common(2)))
    for n, on, cid, zlo, zhi, vol, mats in sorted(inside_out, reverse=True):
        print("VOLUME %s | %s piece %d | %d faces | z %.2f..%.2f | signed volume %+.5f m3 | INSIDE-OUT | %s" % (
            name, on, cid, n, zlo, zhi, vol, ", ".join("%s %d" % m for m in mats)))
    print("VOLSUM %s | %d closed pieces of 100+ faces measured | %d inside-out" % (name, closed_total, len(inside_out)))


pieces_report()
