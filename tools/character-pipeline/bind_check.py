"""Compare every bone's POSE with its REST in an exported .vrm. Expect zero.

    blender --background --python bind_check.py -- <file.vrm>

A VRM stores node transforms (what the game poses the skeleton with) and inverse
bind matrices (what the mesh was bound against). Blender's glTF importer builds
the rest pose from one and the pose from the other, so a bone whose pose differs
from its rest is a bone the game will deform the mesh by. That difference is the
whole defect when a character's hands stand up out of the cuffs.

Measured 2026-11-10: Pomni 0 bones over 5 degrees. Judy Hopps with stub fingers
laid down a hand bone that points straight down: 106 of 141, the hand and every
finger 100.1 degrees off. Laid along the forearm: 14, all of them weightless
thumb stubs and the ears, which are 11 degrees off with or without the fix.

This is the check the build CANNOT do for itself. A pose-versus-rest test run
inside the build said "every bone is at rest" for the broken character, because
the defect only exists in the written file.
"""
import math
import sys

import bpy

SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
res = []
for pb in arm.pose.bones:
    d = (pb.matrix @ pb.bone.matrix_local.inverted()).to_quaternion().angle
    res.append((round(math.degrees(d), 1), pb.name))
res.sort(reverse=True)
off = [r for r in res if r[0] > 5]
print("BINDCHECK %s: %d bones, %d over 5 degrees" % (SRC, len(res), len(off)))
for a, n in off[:60]:
    print("  %6.1f  %s" % (a, n))
