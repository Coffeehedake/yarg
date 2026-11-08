"""Load every .obj in a folder into one scene and save a .blend.

UnityPy writes one OBJ per mesh with no transform, which is what a bundle
stores: the bind-pose geometry, already in its final place relative to the
others. Unity is left-handed and Y-up, so mirror X and stand the model up."""
import glob
import math
import os
import sys

import bpy
from mathutils import Matrix

SRCDIR, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_homefile(use_empty=True)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for f in sorted(glob.glob(os.path.join(SRCDIR, "*.obj"))):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=f, forward_axis="NEGATIVE_Z", up_axis="Y")
    for o in set(bpy.data.objects) - before:
        o.name = os.path.splitext(os.path.basename(f))[0]
# Unity is LEFT handed: without the mirror the model comes out inside out.
M = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    o.data.transform(M)
    o.data.flip_normals()
    o.data.update()
lo = [1e18] * 3
hi = [-1e18] * 3
for o in [x for x in bpy.data.objects if x.type == "MESH"]:
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        for i in range(3):
            lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    print("  %-28s verts=%d" % (o.name, len(o.data.vertices)))
print("assembled extent %.3f x %.3f x %.3f" % tuple(hi[i] - lo[i] for i in range(3)))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print("wrote", OUT)
