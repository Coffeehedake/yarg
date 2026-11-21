# Straighten a character's spine in the build INTERMEDIATE, and bake it.
#
#   blender --background --python straighten_spine.py -- <in.vrm> <out.vrm>
#       --hips n29 --chain n30,n31,n32,n36 --head n37 [--keep n39,n66,n90,n95]
#       [--control] [--no-bake] [--recentre n12,n17,n68,n81]
#
# The Mandalorian's spine leans 3.3 degrees: hips -14.0 mm, head +16.7 mm in
# the shipped bundle (signs negated in Blender). It cannot be corrected in the
# bundle -- a rest-pose edit on a MAPPED humanoid bone is discarded by the
# Animator, measured on Spartan Mark V and settled -- so it has to happen
# upstream of the Unity export, which is here.
#
# WHAT IT DOES, joint by joint rather than in one rotation. Each spine joint is
# posed so the segment to its chain-child points straight up, iterated, because
# rotating a parent moves every child below the one being aimed. The HIPS are
# deliberately not rotated: their other children are the legs, and turning the
# hips takes the legs with them and leaves the step where it was, only
# redistributed. That is also why VRM_STANDUP cannot reach this fault -- it
# rotates the WHOLE rig.
#
# Anything hanging off a rotated bone RIDES the correction. The arms hang off
# the top of the chain, so a T-posed character comes out with both arms tilted
# by the same angle -- tens of millimetres at the hand, a bigger error than the
# one being fixed. The legs hang off the hips, so including the hips joint in
# the chain tilts them too. `--keep` names the bones whose original ORIENTATION
# is restored afterwards while they keep the new POSITION their parent gives
# them: the limb is carried along but not turned.
#
# Including the hips is what makes this worth doing. Straightening from the
# spine up leaves the hips->spine segment, which is the steepest joint in the
# chain -- 8.76 mm over 100 mm, 5 degrees -- and takes the total from 37.2 mm
# only to 24.4. With the hips in, and the two leg roots in `--keep`, the whole
# figure comes plumb.
#
# THE MESH IS BAKED, which is the whole difficulty. Posing an armature does not
# change a mesh's rest shape, and applying the pose as the rest pose without
# baking throws the deformation away -- the character springs back and the run
# still reports success. So each mesh has its Armature modifier APPLIED, which
# writes the deformed shape into the mesh; the modifier is re-added; and only
# then is the pose applied as the new rest pose. These meshes carry no shape
# keys, which is what makes that legal, and the script refuses if any appear.
#
# `--no-bake` is the OTHER meaning of "straighten", and which one is wanted is
# a question about the character rather than about the words. Baking rotates
# the BODY with the bones, so it is right when the body leans. Not baking
# applies the pose as the new rest pose with the mesh left exactly where it
# was, so the BONES move inside a body that does not -- right when the body is
# already plumb and the skeleton is leaning inside it. On The Mandalorian the
# evidence is split: his limb geometry is centred on its bones to a millimetre
# or two, while his chest plate sits 9 mm and his helmet 25 mm to one side of
# the bones that carry them. So both are built and both are rendered, because
# the measurement does not settle it and a picture can.
#
# `--recentre` names bones whose mean X should end up at zero, and translates
# the whole rig and its meshes to put it there. It exists because the builder's
# own centring step averages FIVE humanoid pairs, and on a leaning character
# those pairs spread -- 116.7 mm on Kronk -- so centring their mean leaves
# every individual pair a long way off. His legs went from -3.0 mm to +13.9 mm
# that way, further from the axis rather than nearer. Once the spine is plumb
# the pairs agree and the same operation is well defined, so it is worth
# redoing here rather than leaving the character standing 20 mm off his own
# root. Pass the LEG and UPPER-ARM bones; their mean is the body's axis.
#
# `--control` does the whole round trip with a ZERO correction. Its output must
# measure the same as the shipped bundle; if it does not, nothing measured on
# the corrected build can be attributed to the correction rather than to the
# trip through Blender. On The Mandalorian it measured IDENTICALLY -- every
# bone to 0.1 mm, the mesh extents to four decimals -- which is what made the
# rest of the comparison readable.
#
# MEASURED 2026-11-17, and the two senses gave opposite answers:
#
#   build      skeleton spread   chest plate plane   helmet plane
#   shipped        37.2 mm            -8.0 mm           -8.6 mm
#   --control      37.2 mm            -8.0 mm           -9.6 mm
#   baked           5.9 mm           -24.3 mm          -58.6 mm
#   --no-bake       5.9 mm            -7.7 mm           -8.8 mm
#
# Baking took the skeleton plumb and threw his HELMET 50 mm to one side,
# visibly, because his body was already plumb and only the bones leaned inside
# it. `--no-bake` took the same skeleton plumb and left both armour planes
# where they were, to within 0.3 mm. For HIM, `--no-bake` is the answer; for a
# character whose body genuinely leans it would be exactly the wrong one, so
# this tool does not choose.
import math
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, DST = argv[0], argv[1]


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


HIPS = opt("--hips")
CHAIN = [b for b in (opt("--chain") or "").split(",") if b]
HEAD = opt("--head")
KEEP = [b for b in (opt("--keep") or "").split(",") if b]
# --level rolls ONE bone until its sideways axis is horizontal. It is independent of the
# aim sweep and either may be used alone: a lean needs --chain, a roll needs --level, and
# nothing about a bone's segment pointing up constrains the roll about it.
LEVEL = opt("--level")
RECENTRE = [b for b in (opt("--recentre") or "").split(",") if b]
CONTROL = "--control" in argv
NOBAKE = "--no-bake" in argv

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.vrm(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in meshes:
    if o.data.shape_keys:
        raise SystemExit("ABORT: %s carries shape keys; applying the armature "
                         "modifier would discard them" % o.name)
# None is a legitimate value here now: --level alone needs no chain, and a chain needs no
# --level. Filter before the membership test, because `None in bones` raises a TypeError that
# reads as a broken armature rather than as a missing argument.
for n in [x for x in ([HIPS, HEAD, LEVEL] + CHAIN + KEEP + RECENTRE) if x]:
    if n not in arm.data.bones:
        raise SystemExit("ABORT: no bone %r in this armature" % n)
if not LEVEL and not CHAIN:
    raise SystemExit("ABORT: nothing to do -- pass --chain for a lean, --level for a roll, "
                     "or both. (A lean and a roll are different faults: aiming a segment "
                     "upward does not constrain the roll about it.)")

# Everything below works in ARMATURE space, so the object's own transform
# never has to be reasoned about; "up" is carried into that space once.
UP = (arm.matrix_world.to_3x3().inverted() @ Vector((0.0, 0.0, 1.0)))
UP.normalize()


def head_of(name):
    return arm.pose.bones[name].matrix.translation.copy()


def report(tag):
    # A ROLL run reports a different quantity from a LEAN run, and reporting the wrong one is
    # how a correction gets called a success: the sideways distance from hips to head barely
    # moves when a hips ROLL is levelled, while the thing that does move -- the two leg roots'
    # heights -- is not in the lean report at all.
    if LEVEL and not (HIPS and HEAD):
        pb = arm.pose.bones[LEVEL]
        x = pb.matrix.to_3x3().col[0].normalized()
        print("%s: %s sideways axis %.2f deg out of horizontal"
              % (tag, LEVEL, math.degrees(math.asin(max(-1.0, min(1.0, abs(x.z)))))))
        for a, b in (("thigh.L", "thigh.R"), ("foot.L", "foot.R")):
            if a in arm.pose.bones and b in arm.pose.bones:
                print("    %-7s vs %-7s  height difference %+8.2f mm"
                      % (a, b, (head_of(a).z - head_of(b).z) * 1000.0))
        for n in KEEP:
            print("    %-10s height %8.4f" % (n, head_of(n).z))
        return
    hips, head = head_of(HIPS), head_of(HEAD)
    d = head - hips
    off = (math.degrees(math.acos(max(-1.0, min(1.0, d.normalized().dot(UP)))))
           if d.length > 1e-9 else 0.0)
    print("%s: head is %+.2f mm sideways of the hips, %.2f deg off vertical"
          % (tag, (d - d.dot(UP) * UP).length * 1000
             * (1.0 if (d - d.dot(UP) * UP).x >= 0 else -1.0), off))
    for n in [HIPS] + CHAIN + [HEAD]:
        p = head_of(n)
        print("    %-6s x %+8.2f mm   height %8.4f" % (n, p.x * 1000, p.z))


report("BEFORE")

if CONTROL:
    print("CONTROL RUN: the round trip only, no correction applied")
else:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    pre = {n: arm.pose.bones[n].matrix.to_3x3().copy() for n in KEEP}

    # --level <bone>: ROLL a bone until its own sideways axis is horizontal.
    #
    # This is a different fault from the lean the sweep below corrects, and the sweep cannot
    # touch it. Aiming works by `rotation_difference(UP)`, which points a SEGMENT upward and
    # leaves the roll about that segment entirely free -- so a bone whose head-to-tail is
    # already vertical while the bone is rolled 25 degrees about it reads as perfectly
    # straight and is left alone.
    #
    # Jessica Rabbit is the case. Her Hips' local X points (+0.9009, +0.4339, +0.0142) in
    # world: 25.71 degrees out of horizontal. Her thighs hang off it mirrored to SEVEN decimal
    # places, so that roll maps a +-106 mm sideways offset into +-46 mm of HEIGHT and drops
    # her whole left leg chain -- 92.4 mm at the shoe, measured on geometry against two
    # controls at 0.0 mm. Nothing is wrong with either leg.
    #
    # So level the axis and put the thighs in `--keep`: they take the new, level positions
    # their parent gives them while their own orientation is restored, which moves the legs
    # without turning them.
    if LEVEL:
        pb = arm.pose.bones[LEVEL]
        x = pb.matrix.to_3x3().col[0].normalized()
        flat = Vector((x.x, x.y, 0.0))
        if flat.length < 1e-6:
            raise SystemExit("ABORT: --level %s has a sideways axis pointing straight up or "
                             "down, so 'horizontal' does not name a rotation for it." % LEVEL)
        flat.normalize()
        deg = math.degrees(math.acos(max(-1.0, min(1.0, x.dot(flat)))))
        q = x.rotation_difference(flat)
        h = pb.matrix.translation.copy()
        m = q.to_matrix().to_4x4() @ pb.matrix
        m.translation = h
        pb.matrix = m
        bpy.context.view_layer.update()
        x2 = arm.pose.bones[LEVEL].matrix.to_3x3().col[0].normalized()
        print("  levelled %s: sideways axis was %.2f deg out of horizontal, now %.3f deg"
              % (LEVEL, deg,
                 math.degrees(math.asin(max(-1.0, min(1.0, abs(x2.z)))))))

    order = CHAIN + [HEAD]
    for sweep in range(10):
        worst = 0.0
        for i, n in enumerate(CHAIN):
            v = head_of(order[i + 1]) - head_of(n)
            if v.length < 1e-9:
                continue
            worst = max(worst, math.degrees(math.acos(
                max(-1.0, min(1.0, v.normalized().dot(UP))))))
            q = v.normalized().rotation_difference(UP)
            pb = arm.pose.bones[n]
            # Rotate this bone about its OWN head: the translation is what
            # pins it to the parent and must survive the rotation untouched.
            h = pb.matrix.translation.copy()
            m = q.to_matrix().to_4x4() @ pb.matrix
            m.translation = h
            pb.matrix = m
            bpy.context.view_layer.update()
        print("  sweep %d: worst joint was %.3f deg off vertical"
              % (sweep, worst))
        if worst < 0.02:
            break
    for n in KEEP:
        pb = arm.pose.bones[n]
        h = pb.matrix.translation.copy()
        m = pre[n].to_4x4()
        m.translation = h
        pb.matrix = m
        bpy.context.view_layer.update()
        print("  %s kept its original orientation at its new position"
              % n)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    report("POSED, not yet baked")

    if NOBAKE:
        print("  NOT baking: the pose becomes the new rest pose and the meshes "
              "stay exactly where they are, so the BONES move inside the body")
    else:
        for o in meshes:
            bpy.context.view_layer.objects.active = o
            n_before = len(o.data.vertices)
            for m in list(o.modifiers):
                if m.type == "ARMATURE":
                    bpy.ops.object.modifier_apply(modifier=m.name)
            if len(o.data.vertices) != n_before:
                raise SystemExit("ABORT: %s changed vertex count in the bake"
                                 % o.name)
            mod = o.modifiers.new(name="Armature", type="ARMATURE")
            mod.object = arm
            print("  baked %s (%d verts)" % (o.name, n_before))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()

if RECENTRE and not CONTROL:
    xs = [head_of(n).x for n in RECENTRE]
    off = sum(xs) / len(xs)
    print("  recentre: %d bone(s) mean X is %+.2f mm; moving every edit bone "
          "and every vertex by that amount" % (len(xs), off * 1000))
    # Translating the OBJECTS is what the first version did, and the re-measure
    # below caught it doing nothing: these positions are read in ARMATURE
    # space, which an object transform does not touch, and whether the exporter
    # would have baked it was never in evidence either way. Moving the edit
    # bones and the vertices is unambiguous and survives any exporter.
    before = {b.name: head_of(b.name).x for b in arm.data.bones}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    # A CONNECTED bone's head is pinned to its parent's tail, so moving the
    # parent's tail moves it too -- and then moving it again here gives that
    # bone, and everything under it, TWICE the offset. The first version did
    # exactly that: Kronk's Chest and his feet came out 15.8 mm adrift of his
    # hips and head, one whole offset, while the four bones the re-centre
    # aimed at read a clean zero. Disconnect, translate, reconnect; the
    # reconnect is a no-op because every head and tail moved together.
    conn = {}
    for eb in arm.data.edit_bones:
        conn[eb.name] = eb.use_connect
        eb.use_connect = False
    for eb in arm.data.edit_bones:
        eb.head.x -= off
        eb.tail.x -= off
    for eb in arm.data.edit_bones:
        eb.use_connect = conn[eb.name]
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in meshes:
        for v in o.data.vertices:
            v.co.x -= off
        o.data.update()
    bpy.context.view_layer.update()
    xs = [head_of(n).x for n in RECENTRE]
    print("  recentre: now %+.2f mm" % (1000.0 * sum(xs) / len(xs)))
    # Check EVERY bone moved by exactly the offset, not just the ones aimed
    # at. The four target bones read a clean zero while the rig was broken.
    worst, who = off, "(none)"
    for b in arm.data.bones:
        moved = before[b.name] - head_of(b.name).x
        if abs(moved - off) > abs(worst - off):
            worst, who = moved, b.name
    if abs(worst - off) > 1e-5:
        raise SystemExit("ABORT: recentre moved %r by %.3f mm, not %.3f mm -- "
                         "the rig is no longer rigid"
                         % (who, worst * 1000, off * 1000))
    print("  recentre: all %d bones moved by %.3f mm (worst %r, %.4f mm)"
          % (len(arm.data.bones), off * 1000, who, worst * 1000))

report("AFTER")

bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = arm
res = bpy.ops.export_scene.vrm(filepath=DST)
print("export_scene.vrm returned: %s" % (res,))
