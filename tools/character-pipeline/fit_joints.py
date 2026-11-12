# Put the limb joints where the MESH says they are.
#
# A uniform rescale fixed The Rock's legs and left his arms 0.26 m short,
# because the rig is not uniformly wrong: legs and arms are off by different
# factors. Scaling cannot express that. Fitting can.
#
# For a chain parent -> child, the joint between them is the boundary between
# the two flesh clusters, so place it at the midpoint of their weighted-vertex
# centroids. The last bone keeps its own direction and length ratio.
#
# Connected bones must be disconnected before writing, or a child's head is
# dragged back to its parent's tail and later writes undo earlier ones.
import bpy, sys
from mathutils import Vector

src, dst = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=src)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.find_armature() == arm]

def centroid(bone):
    pts = []
    for o in meshes:
        g = o.vertex_groups.get(bone)
        if g is None:
            continue
        i = g.index
        for v in o.data.vertices:
            for gg in v.groups:
                if gg.group == i and gg.weight > 0.5:
                    pts.append(o.matrix_world @ v.co)
                    break
    if len(pts) < 8:
        return None
    c = Vector((0, 0, 0))
    for p in pts:
        c += p
    return c / len(pts)

CHAINS = []
for s in ("Left", "Right"):
    CHAINS.append([s+"Shoulder", s+"Arm", s+"ForeArm", s+"Hand"])
    CHAINS.append([s+"UpLeg", s+"Leg", s+"Foot", s+"ToeBase"])

cen = {}
for ch in CHAINS:
    for b in ch:
        if b in arm.data.bones and b not in cen:
            cen[b] = centroid(b)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
snap = {b.name: b.use_connect for b in eb}
# Remember where everything started. Disconnecting is required (a connected
# child's head is pinned to its parent's tail), but it also means a child no
# longer follows its parent -- so the finger bones sat still while the hand
# moved, and the worst-offender metric did not shift by a millimetre. Record
# the originals so untouched descendants can be carried along afterwards.
before = {b.name: b.head.copy() for b in eb}
parent_of = {b.name: (b.parent.name if b.parent else None) for b in eb}
for b in eb:
    b.use_connect = False

moved = 0
for ch in CHAINS:
    ch = [b for b in ch if b in eb and cen.get(b) is not None]
    for i in range(1, len(ch)):
        par, cur = ch[i-1], ch[i]
        joint = (cen[par] + cen[cur]) / 2.0          # boundary of the two clusters
        eb[par].tail = joint
        eb[cur].head = joint
        moved += 1
    if len(ch) >= 2:                                  # last bone: keep direction, land in its flesh
        last = ch[-1]
        d = (cen[last] - eb[last].head)
        if d.length > 1e-6:
            eb[last].tail = eb[last].head + d * 2.0

# Carry every descendant of a fitted bone by that bone's displacement, so the
# fingers travel with the hand and the toes with the foot.
fitted = set()
for ch in CHAINS:
    for b in ch:
        if b in eb:
            fitted.add(b)
delta = {n: (eb[n].head - before[n]) for n in fitted if n in eb}
carried = 0
for b in eb:
    if b.name in fitted:
        continue
    a = parent_of.get(b.name)
    while a is not None and a not in fitted:
        a = parent_of.get(a)
    if a is not None and delta.get(a) is not None and delta[a].length > 1e-9:
        b.head = b.head + delta[a]
        b.tail = b.tail + delta[a]
        carried += 1
print("descendants carried with their fitted ancestor: %d" % carried)

for b in eb:
    b.use_connect = snap[b.name]
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()
print("joints repositioned: %d" % moved)
mw = arm.matrix_world
for nm in ("LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"):
    b = arm.data.bones.get(nm)
    if b and cen.get(nm):
        m = (mw @ b.head_local + mw @ b.tail_local) / 2
        print("  %-14s mid.x %6.3f   mesh.x %6.3f   gap %6.3f" % (nm, m.x, cen[nm].x, m.x - cen[nm].x))
bpy.ops.wm.save_as_mainfile(filepath=dst)
print("saved")
