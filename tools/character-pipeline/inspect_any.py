"""Report what a source model actually contains, before choosing a rig map."""
import sys
import bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
if SRC.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=SRC)
else:
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=SRC)

arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
other = sorted({o.type for o in bpy.data.objects} - {"ARMATURE", "MESH"})
print("ARMATURES: %d %s" % (len(arms), [a.name for a in arms]))
print("MESHES: %d %s" % (len(meshes), [o.name for o in meshes][:14]))
print("OTHER OBJECT TYPES:", other)
print("ACTIONS:", [a.name for a in bpy.data.actions][:6])
sk = [(o.name, len(o.data.shape_keys.key_blocks),
       [kb.name for kb in o.data.shape_keys.key_blocks if abs(kb.value) > 1e-6])
      for o in meshes if o.data.shape_keys]
print("SHAPE KEYS:", sk[:6] if sk else "none")

lo = Vector((1e18,) * 3); hi = Vector((-1e18,) * 3)
deps = bpy.context.evaluated_depsgraph_get()
for o in meshes:
    ev = o.evaluated_get(deps)
    for c in ev.bound_box:
        w = ev.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
if meshes:
    print("EXTENT: %.3f x %.3f x %.3f" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
for a in arms:
    bones = a.data.bones
    print("ARM '%s': %d bones, scale=%s, roots=%s"
          % (a.name, len(bones), tuple(round(s, 4) for s in a.scale),
             [b.name for b in bones if b.parent is None][:4]))
    print("  BONES: " + "|".join(sorted(b.name for b in bones)))
print("DONE")
