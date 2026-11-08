"""Give a nameless skeleton the names of an identical, named one.

A USD export routinely strips every bone name to an ordinal -- Harley Quinn's
'mixamorig:Hips' arrives as 'n7' -- which makes the rig unmappable even though
it is bone-for-bone the rig the .fbx of the same model carries. The two are the
same skeleton in the same pose, so match them by WHERE the bones are: normalise
both to the same height and floor, then pair each bone with its nearest
counterpart. Positional matching needs no assumption about traversal order,
which an exporter is free to change.

  blender -b -P name_from_donor.py -- <target> <donor> <out.blend>
"""
import sys

import bpy
from mathutils import Vector

TGT, DONOR, OUT = sys.argv[sys.argv.index("--") + 1:][:3]


def load(path):
    low = path.lower()
    if low.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    elif low.endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=path)
    elif low.endswith((".usd", ".usdc", ".usda", ".usdz")):
        bpy.ops.wm.usd_import(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)


def heads(arm):
    """Bone heads in world space, normalised to height 1 with feet at z=0."""
    pts = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
    zs = [p.z for p in pts.values()]
    lo, span = min(zs), max(zs) - min(zs)
    if span < 1e-9:
        raise SystemExit("ABORT: %s has no vertical extent" % arm.name)
    # Centre sideways and front-to-back as well as standing it on the floor:
    # the two files place the character at different origins, and comparing raw
    # x/y put every bone three quarters of a body height from its counterpart.
    cx = sum(p.x for p in pts.values()) / len(pts)
    cy = sum(p.y for p in pts.values()) / len(pts)
    return {n: Vector(((p.x - cx) / span, (p.y - cy) / span, (p.z - lo) / span))
            for n, p in pts.items()}


bpy.ops.wm.read_homefile(use_empty=True)
load(TGT)
tgt = next(o for o in bpy.data.objects if o.type == "ARMATURE")
keep = set(bpy.data.objects)
T = heads(tgt)

load(DONOR)
donor = next(o for o in bpy.data.objects
             if o.type == "ARMATURE" and o not in keep)
D = heads(donor)
print("target %d bones, donor %d bones" % (len(T), len(D)))

# Walk the two trees together rather than matching all 65 bones against all 65
# at once. Flat nearest-neighbour matching is a 65x65 assignment problem that a
# greedy pass gets wrong -- it stranded one pair three quarters of a body height
# apart -- while SIBLINGS are trivially far apart (the hips' three children are
# the spine and the two legs), so disambiguating within a parent is easy and the
# tree shape validates the match as it goes.
mapping, worst = {}, 0.0


def ndesc(b, memo={}):
    """How many bones hang off this one. A subtree's SIZE is a far stronger
    signal than position when choosing between siblings: the hips' three
    children are a long spine and two short legs, and position alone paired the
    spine with a thigh."""
    key = (id(b.id_data), b.name)
    if key not in memo:
        memo[key] = sum(1 + ndesc(c) for c in b.children)
    return memo[key]


def pair(a, b):
    global worst
    mapping[a.name] = b.name
    worst = max(worst, (T[a.name] - D[b.name]).length)
    ca, cb = list(a.children), list(b.children)
    if len(ca) != len(cb):
        raise SystemExit("ABORT: '%s' has %d children but '%s' has %d -- these "
                         "are not the same skeleton" % (a.name, len(ca), b.name, len(cb)))
    free = list(cb)
    for x in sorted(ca, key=lambda n: -ndesc(n)):
        same = [n for n in free if ndesc(n) == ndesc(x)] or free
        y = min(same, key=lambda n: (T[x.name] - D[n.name]).length)
        free.remove(y)
        pair(x, y)


troots = [b for b in tgt.data.bones if b.parent is None]
droots = [b for b in donor.data.bones if b.parent is None]
if len(troots) != len(droots):
    raise SystemExit("ABORT: %d root(s) against %d" % (len(troots), len(droots)))
free_r = list(droots)
for r in sorted(troots, key=lambda n: -ndesc(n)):
    _same = [n for n in free_r if ndesc(n) == ndesc(r)] or free_r
    q = min(_same, key=lambda n: (T[r.name] - D[n.name]).length)
    free_r.remove(q)
    pair(r, q)
print("matched %d of %d bones, worst offset %.4f of body height"
      % (len(mapping), len(T), worst))
if worst > 0.05:
    print("  WARNING: the worst pair is %.1f%% of body height apart -- check the "
          "result before trusting it" % (worst * 100.0))

for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o, do_unlink=True)

# Rename via a placeholder pass, so a target name that collides with a donor
# name still in use cannot silently become 'Hips.001'.
for tn in mapping:
    tgt.data.bones[tn].name = "__tmp__" + tn
for tn, dn in mapping.items():
    tgt.data.bones["__tmp__" + tn].name = dn
left = [b.name for b in tgt.data.bones if b.name.startswith("__tmp__")]
if left:
    print("  %d bones kept a placeholder name: %s" % (len(left), left[:5]))
print("renamed %d bones on '%s'" % (len(mapping), tgt.name))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("wrote", OUT)
