# Are the limbs straight, and do the two sides match -- in WORLD space?
#
# TWO WAYS TO GET THIS WRONG, both of which produced a confident, wrong report
# of a Sonic wrist defect before the third way was found.
#
# 1. LOCAL ROTATIONS. A bone's local rotation is relative to its parent, and
#    left/right bone ROLLS need not match, so a correct rig can look wildly
#    asymmetric. Sonic's installed build gives LeftHand 0.87 degrees against
#    RightHand 69.76, and LeftHandIndex1 0.09 against 127.43. Those numbers
#    are real and they mean nothing: in world space the same rig is straight
#    and mirrored to within 2-7 mm.
#
# 2. BONE AXES. A bone's own head-to-tail direction is only meaningful when
#    the tail is pinned by a child. The VRM importer SYNTHESISES a tail
#    wherever the hierarchy does not pin one, and a synthetic tail points
#    somewhere arbitrary. That read as "the wrist is bent exactly 90.00 degrees
#    on both sides" on one Sonic build and "the elbow is bent 86.8 degrees" on
#    Ariel, who renders with perfectly straight arms. Both were artefacts.
#    Measured gaps between tail and child head: Ariel's lHand 0.0741 against a
#    bone length of 0.0067, which is eleven times the bone.
#
# So measure JOINT TO JOINT. The angle at the elbow is the angle between the
# shoulder-to-elbow segment and the elbow-to-wrist segment, built from bone
# HEAD positions only, which no synthesised tail can disturb. Bones are
# addressed through the HUMANOID map, so this works on any rig family.
#
# The tail sanity is still reported, so nobody re-derives the artefact and
# believes it.
#
# Usage:  blender --background --python limb_check.py -- <character.vrm>
#         LIMB_CONTROL=1   bends an elbow first, to prove the check can fire.
import json
import math
import struct
import sys

import os

import bpy
import mathutils

# (parent, child, straight?) -- an ANKLE is legitimately bent near 90 degrees
# in a standing rest pose, the foot pointing forward while the leg points down,
# so the straightness rule must not apply to it or the check cries wolf on
# every healthy character. Measured: the installed Sonic reads 55.6/57.0 there
# and is correct. Only the left/right comparison is meaningful for an ankle.
PAIRS = [(("UpperArm", "LowerArm", "Hand"), True),          # elbow
         (("LowerArm", "Hand", "IndexProximal"), True),     # wrist
         (("UpperLeg", "LowerLeg", "Foot"), True),          # knee
         (("LowerLeg", "Foot", "Toes"), False)]             # ankle


def main():
    src = sys.argv[-1]
    d = open(src, "rb").read()
    off, g = 12, None
    while off < len(d):
        ln, ty = struct.unpack_from("<II", d, off)
        if ty == 0x4E4F534A:
            g = json.loads(d[off + 8:off + 8 + ln].decode("utf-8"))
        off += 8 + ln + ((4 - ln % 4) % 4)
    nodes = [n.get("name", "?") for n in g["nodes"]]
    hum = {k: nodes[v["node"]]
           for k, v in g["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"].items()}

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.vrm(filepath=src)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    mw = arm.matrix_world

    def head(key):
        n = hum.get(key)
        if not n:
            return None
        b = arm.data.bones.get(n)
        return None if b is None else (mw @ b.head_local)

    def seg(a, b):
        """Direction of the limb SEGMENT from joint a to joint b.

        Not the bone's own tail. A VRM-imported bone's tail is synthesised
        wherever the hierarchy does not pin it, and a twist bone between the
        elbow and the wrist is enough to send it somewhere meaningless -- which
        is how Ariel first measured an 86.8 degree elbow while rendering with
        perfectly straight arms. Joint-to-joint cannot lie that way.
        """
        ha, hb = head(a), head(b)
        if ha is None or hb is None:
            return None
        v = hb - ha
        return None if v.length < 1e-6 else v.normalized()

    def ang(a, b):
        if a is None or b is None:
            return None
        return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))

    # Say whether bone axes would have been trustworthy here. This check does
    # not use them -- but the artefact is seductive enough to be worth naming.
    synth = 0
    for k in hum:
        b = arm.data.bones.get(hum[k])
        if b is None or not b.children:
            continue
        blen = (b.tail_local - b.head_local).length
        gap = min((b.tail_local - c.head_local).length for c in b.children)
        if gap > 0.05 * max(blen, 1e-6) + 1e-4:
            synth += 1
    if synth:
        print("note: %d bone(s) carry a SYNTHETIC tail -- bone-axis angles "
              "would be meaningless on this rig; this check uses joint "
              "positions and is unaffected." % synth)

    if os.environ.get("LIMB_CONTROL"):
        # Bend an elbow by moving the wrist, so the check has something real
        # to find. A detector never seen to fire has not been verified.
        n = hum.get("leftHand")
        b = arm.data.bones.get(n) if n else None
        if b is not None:
            bpy.context.view_layer.objects.active = arm
            bpy.ops.object.mode_set(mode="EDIT")
            eb = arm.data.edit_bones.get(n)
            d = eb.tail - eb.head
            eb.head = eb.head + mathutils.Vector((0.0, -0.25, 0.0))
            eb.tail = eb.head + d
            bpy.ops.object.mode_set(mode="OBJECT")
            print("CONTROL: left wrist displaced 0.25 m")

    print("%-30s %8s %8s %8s" % ("relationship", "LEFT", "RIGHT", "L-R"))
    worst = 0.0
    for (p, c, nxt), straight in PAIRS:
        l = ang(seg("left" + p, "left" + c), seg("left" + c, "left" + nxt))
        r = ang(seg("right" + p, "right" + c), seg("right" + c, "right" + nxt))
        if l is None or r is None:
            print("%-30s   not mapped" % (p + "/" + c + "/" + nxt))
            continue
        flag = ""
        if straight and max(l, r) > 30.0:
            flag = "   <-- BENT; a rest pose should be straight here"
        elif abs(l - r) > 10.0:
            flag = "   <-- ASYMMETRIC"
        worst = max(worst, max(l, r) if straight else 0.0, abs(l - r))
        print("%-30s %8.2f %8.2f %8.2f%s" % (c + " joint", l, r, abs(l - r), flag))
    print()
    print("worst reading: %.2f degrees" % worst)


if __name__ == "__main__":
    main()
