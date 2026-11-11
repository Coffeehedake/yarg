"""How far does each bone sit from the mesh it carries? Expect a few centimetres.

    blender --background --python bone_fit.py -- <file.vrm>

For every bone that carries at least 10 vertices at weight > 0.5, take the centroid of
those vertices (rest pose, as written in the file) and measure its distance to the bone's
head-to-tail segment. A finger bone that lies 10 or 25 cm from its own finger mesh is a bone
that is not inside the mesh: the mesh rotates about a pivot that is far from it, and the
fingers fly out as long thin strips when the animation curls them. Judy/Miku-style
pose-versus-rest checks cannot see this, because pose and rest can agree with each other
and both disagree with the mesh.
"""
import sys

import bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mw = arm.matrix_world

sums, cnts = {}, {}
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    names = {g.index: g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        for g in v.groups:
            if g.weight > 0.5 and names.get(g.group) in arm.data.bones:
                n = names[g.group]
                sums[n] = sums.get(n, Vector()) + o.matrix_world @ v.co
                cnts[n] = cnts.get(n, 0) + 1


def seg_dist(p, a, b):
    ab = b - a
    t = 0.0 if ab.length_squared == 0 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


rows = []
for n, c in cnts.items():
    if c < 10:
        continue
    bone = arm.data.bones[n]
    a, b = mw @ bone.head_local, mw @ bone.tail_local
    rows.append((seg_dist(sums[n] / c, a, b) * 100.0, n))
rows.sort(reverse=True)
far = [r for r in rows if r[0] > 5]
import re
_FIN = re.compile(r"thumb|index|mid|ring|pinky|little|f_|finger", re.I)
_TOE = re.compile(r"toe", re.I)
fing = [r for r in rows if _FIN.search(r[1]) and not _TOE.search(r[1])]
fing_far = [r for r in fing if r[0] > 5]
print("FINGERFIT %s: %d of %d finger bones more than 5 cm from their mesh (worst %.1f cm)" % (
    SRC.replace("\\", "/").split("/")[-1], len(fing_far), len(fing), fing[0][0] if fing else 0.0))
print("BONEFIT %s: %d bones, %d more than 5 cm from their mesh" % (SRC.replace("\\", "/").split("/")[-1], len(rows), len(far)))
for d, n in rows[:5]:
    print("  %6.1f cm  %s" % (d, n))
