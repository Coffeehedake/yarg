# -*- coding: utf-8 -*-
"""Knuckle bend in a SOURCE model, to compare against the installed bundle.

    blender --background --python knuckle_bend_source.py -- <file.fbx|.glb|.blend>

WHY. `knuckle_bend_installed.py` says what bend an installed character still carries. It cannot
say whether that bend was ever there. The 2026-11-14 roster work established that the VRM
add-on replaces authored bend with exactly 0.0 degrees -- so a flat installed hand has two
completely different explanations, and only the source separates them:

  * the SOURCE carries bend and the bundle reads 0.0  ->  the build destroyed it, and
    rebuilding with `VRM_EXPORT_POSE=rest` is the fix.
  * the SOURCE is flat too                            ->  nothing was destroyed, the model
    arrived that way, and no rebuild helps.

**43 of 65 installed characters read flat, so this distinction is the whole question.** Acting
on a flat bundle alone would mean rebuilding the roster to chase a model's own geometry.

MEASURED JOINT TO JOINT, from one bone's head to the next bone's head, never from a bone's own
axis. A bone's tail is synthesised wherever the rig does not pin one, so an axis-based reading
is a fact about the importer; `fingerpose.py` summed bone axes once and reported a 32.5 degree
curl on a hand that reads 0.0 from the file.

Bone names are matched case-insensitively against the usual conventions (`RightHandIndex1`,
`index.01.R`, `f_index.01.R`, `mixamorig:RightHandIndex1`) and every finger this finds is
printed with the three bones it used, so a wrong match is visible rather than averaged in. A
finger whose three bones are not found prints `-`, never 0.0.

Nothing is written and the source file is only ever read.
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

FINGERS = ["thumb", "index", "middle", "ring", "little"]
ALIASES = {"little": ["little", "pinky"]}


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
        print("NO ARMATURE in %s -- unmeasured, not 'flat'" % SRC)
        return 1
    arm = max(arms, key=lambda a: len(a.data.bones))
    bones = {b.name.lower(): b for b in arm.data.bones}
    print("source   : %s" % SRC)
    print("armature : %s, %d bones" % (arm.name, len(arm.data.bones)))
    print()

    def find(side, finger, idx):
        """idx is 1,2,3 -- proximal, intermediate, distal."""
        names = ALIASES.get(finger, [finger])
        s_long, s_short = ("right", "r") if side == "R" else ("left", "l")
        for nm in names:
            for low, b in bones.items():
                if nm not in low:
                    continue
                # the joint number, as a standalone 1/2/3 or .01/.02/.03
                if not re.search(r"(^|[^0-9])0?%d([^0-9]|$)" % idx, low):
                    continue
                if re.search(r"(^|[._\- :])%s([._\- ]|$)" % s_short, low) or s_long in low:
                    return b
        return None

    worst = {}
    for side in ("R", "L"):
        print("  %s hand" % ("RIGHT" if side == "R" else "LEFT"))
        best = None
        for f in FINGERS:
            bs = [find(side, f, i) for i in (1, 2, 3)]
            if any(b is None for b in bs):
                print("    %-8s -        (bones found: %s)"
                      % (f, ", ".join(b.name if b else "MISSING" for b in bs)))
                continue
            p = [b.head_local for b in bs]
            u = p[1] - p[0]
            v = p[2] - p[1]
            if u.length < 1e-9 or v.length < 1e-9:
                print("    %-8s -        (zero-length segment)" % f)
                continue
            ang = math.degrees(math.acos(max(-1.0, min(1.0, u.normalized().dot(v.normalized())))))
            print("    %-8s %6.1f   via %s" % (f, ang, " -> ".join(b.name for b in bs)))
            best = ang if best is None else max(best, ang)
        worst[side] = best
        print()

    r, l = worst.get("R"), worst.get("L")
    print("WORST knuckle bend: right %s, left %s"
          % (("%.1f" % r) if r is not None else "-", ("%.1f" % l) if l is not None else "-"))
    if r is not None and l is not None:
        print("left-right asymmetry: %.1f degrees" % abs(r - l))
    print()
    print("Compare against knuckle_bend_installed.py on the same character. Bend HERE and")
    print("0.0 THERE means the build flattened it and a rebuild recovers it. Flat in both")
    print("means the model arrived that way and no rebuild helps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
