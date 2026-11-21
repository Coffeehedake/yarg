# -*- coding: utf-8 -*-
"""Is a SOURCE model's rest pose a T-pose? The gate on using VRM_EXPORT_POSE=rest.

    blender --background --python rest_pose_source.py -- <file.fbx|.glb|.blend|.vrm>

WHY THIS IS NOT OPTIONAL BEFORE USING THAT KNOB. `VRM_EXPORT_POSE=rest` stops the VRM add-on
applying a T-pose estimate of its own. That is the right thing when the estimate is destroying
authored detail -- it is what flattens knuckle bend. **It is the wrong thing when the add-on's
estimate is the ONLY thing T-posing the character**, because Unity builds the humanoid avatar
from the bind pose, so shipping a bent rest pose mis-aims every muscle axis the character has.

This file records that failure under Prix: *"a Mixamo rig: the T-pose step prints nothing for
him, so the add-on was the only thing T-posing him"*, with the guard firing at `forearm 21.2
deg`. Elite Terrorist is also `rig=mixamo`, so the same question has to be asked of him before
the knob is used, not after.

MEASURED JOINT TO JOINT, head to head, never by bone axis -- a bone's tail is synthesised
wherever the rig does not pin one, and the build-time version of this guard got exactly that
wrong first, reporting arms 90.0 degrees off and legs 180.0, both sides, to the decimal.
Numbers that round are not a pose.

THE AXES COME FROM THE RIG, NOT FROM A CONVENTION, and the first version of this got that wrong
in the way this project keeps warning about. It assumed Blender's Z-up and measured the legs at
**89.5 degrees off "down"**, which is impossible for a standing figure -- it means the file is
Y-up and the importer did not rotate it, or the armature object carries the rotation. On that
reading it printed "NOT a T-pose, this is the Prix case", confidently, about a character whose
legs are perfectly straight.

So "up" is taken as hips->head and "across" as right hand->left hand, both measured in WORLD
space from this rig's own bones. A T-pose then means each upper arm and forearm lies along
`across` and each thigh and shin along `-up`, and the answer is the same whatever convention the
file was written in. Nothing here needs to know which way is up in the abstract.
"""
import math
import re
import sys

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:]
if not ARGS:
    print("usage: ... -- <file>")
    sys.exit(2)
SRC = ARGS[0]

# (label, proximal, distal, axis in BLENDER's frame: X across, -Z down)
SEGMENTS = [
    ("upperarm.R", ["rightarm", "upper_arm.r", "arm.r", "shoulder.r"],
     ["rightforearm", "forearm.r", "elbow.r"], "right"),
    ("forearm.R", ["rightforearm", "forearm.r", "elbow.r"],
     ["righthand", "hand.r", "wrist.r"], "right"),
    ("upperarm.L", ["leftarm", "upper_arm.l", "arm.l", "shoulder.l"],
     ["leftforearm", "forearm.l", "elbow.l"], "left"),
    ("forearm.L", ["leftforearm", "forearm.l", "elbow.l"],
     ["lefthand", "hand.l", "wrist.l"], "left"),
    ("thigh.R", ["rightupleg", "thigh.r", "upper_leg.r"],
     ["rightleg", "shin.r", "lower_leg.r", "knee.r"], "down"),
    ("shin.R", ["rightleg", "shin.r", "lower_leg.r", "knee.r"],
     ["rightfoot", "foot.r", "ankle.r"], "down"),
    ("thigh.L", ["leftupleg", "thigh.l", "upper_leg.l"],
     ["leftleg", "shin.l", "lower_leg.l", "knee.l"], "down"),
    ("shin.L", ["leftleg", "shin.l", "lower_leg.l", "knee.l"],
     ["leftfoot", "foot.l", "ankle.l"], "down"),
]


def load(path):
    low = path.lower()
    bpy.ops.wm.read_homefile(use_empty=True)
    if low.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif low.endswith((".glb", ".gltf", ".vrm")):
        bpy.ops.import_scene.gltf(filepath=path)
    elif low.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    else:
        print("UNSUPPORTED: %s" % path)
        sys.exit(2)


def main():
    load(SRC)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        print("NO ARMATURE in %s -- unmeasured, which is not the same as a T-pose" % SRC)
        return 1
    arm = max(arms, key=lambda a: len(a.data.bones))
    bones = list(arm.data.bones)
    print("source   : %s" % SRC)
    print("armature : %s, %d bones" % (arm.name, len(bones)))
    print()

    def find(cands):
        for c in cands:
            for b in bones:
                low = b.name.lower().split(":")[-1]
                if low == c or re.search(r"(^|[._\- ])%s([._\- ]|$)" % re.escape(c), low):
                    return b
        return None

    M = arm.matrix_world

    def wpos(b):
        return M @ b.head_local

    # THE RIG'S OWN AXES. hips->head is up; right hand->left hand is across. Both in world
    # space, so the armature object's own rotation is included rather than ignored.
    hips = find(["hips", "pelvis", "root"])
    head = find(["head"])
    rhand = find(["righthand", "hand.r", "wrist.r"])
    lhand = find(["lefthand", "hand.l", "wrist.l"])
    if hips is None or head is None or rhand is None or lhand is None:
        print("cannot establish the rig's own axes (need hips, head and both hands); found")
        print("hips=%s head=%s rhand=%s lhand=%s -- UNMEASURED"
              % (hips and hips.name, head and head.name, rhand and rhand.name,
                 lhand and lhand.name))
        return 1
    up = (wpos(head) - wpos(hips)).normalized()
    across = (wpos(lhand) - wpos(rhand)).normalized()
    # Make across perpendicular to up, so an A-pose's downward component does not leak in.
    across = (across - up * across.dot(up)).normalized()
    print("    rig axes: up = hips->head (%.3f, %.3f, %.3f)" % (up.x, up.y, up.z))
    print("              across = R hand->L hand (%.3f, %.3f, %.3f)"
          % (across.x, across.y, across.z))
    print()
    AX = {"left": across, "right": -across, "down": -up}

    worst, rows = 0.0, []
    for label, pc, dc, axis_name in SEGMENTS:
        a, b = find(pc), find(dc)
        if a is None or b is None:
            rows.append((label, None, "%s / %s" % (a.name if a else "MISSING",
                                                   b.name if b else "MISSING")))
            continue
        v = wpos(b) - wpos(a)
        if v.length < 1e-9:
            rows.append((label, None, "zero-length"))
            continue
        d = v.normalized().dot(AX[axis_name])
        ang = math.degrees(math.acos(max(-1.0, min(1.0, d))))
        worst = max(worst, ang)
        rows.append((label, ang, "%s -> %s" % (a.name, b.name)))

    for label, ang, via in rows:
        print("    %-12s %8s   %s" % (label, ("%.1f" % ang) if ang is not None else "-", via))
    print()
    print("WORST segment: %.1f degrees off the axis a T-pose puts it on." % worst)
    print()
    if worst < 5.0:
        print("VERDICT: this source IS a T-pose. VRM_EXPORT_POSE=rest is safe here -- the")
        print("add-on's estimate is not the only thing straightening the character, so")
        print("declining it costs nothing and preserves authored finger detail.")
    elif worst < 15.0:
        print("VERDICT: BORDERLINE. Close to a T-pose but not on it. Using the knob ships")
        print("this pose into the bind, and Unity builds every muscle axis from the bind.")
        print("Weigh it against what the knob is being used to preserve.")
    else:
        print("VERDICT: this source is NOT a T-pose. DO NOT use VRM_EXPORT_POSE=rest on it")
        print("alone -- the add-on's estimate is what is straightening this character, and")
        print("declining it mis-aims every muscle axis. This is the Prix case.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
