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
    for (mn, mat, tex), (n, k) in st.items():
        if n >= MIN_FACES:
            rows.append((100.0 * k / n, mn, mat, tex, n))

rows.sort()
for share, mn, mat, tex, n in rows:
    print("FACING %s | %s | %s | %s | %d faces | %.0f%% outward" % (
        name, mn, mat, "textured" if tex else "untextured", n, share))
