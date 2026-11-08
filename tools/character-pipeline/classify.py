"""One line per model: which rig family it is, so a batch can be triaged
without opening each one by hand."""
import re
import sys

import bpy
from mathutils import Vector

SRC = sys.argv[sys.argv.index("--") + 1]
TAG = sys.argv[sys.argv.index("--") + 2]

try:
    low = SRC.lower()
    if low.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=SRC)
    elif low.endswith((".glb", ".gltf")):
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=SRC)
    elif low.endswith((".usd", ".usdc", ".usda", ".usdz")):
        bpy.ops.wm.usd_import(filepath=SRC)
    elif low.endswith(".dae"):
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.wm.collada_import(filepath=SRC)
    else:
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=SRC)
except Exception as e:
    print("%-6s IMPORT FAILED %s" % (TAG, e))
    raise SystemExit(0)

arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
if not arms:
    print("%-6s NO ARMATURE  meshes=%d" % (TAG, len(meshes)))
    raise SystemExit(0)
arm = max(arms, key=lambda a: len(a.data.bones))
names = {b.name for b in arm.data.bones}
joined = "|".join(names)

def has(*xs):
    return all(any(x.lower() == n.lower() for n in names) for x in xs)

fam = "UNKNOWN"
if "CC_Base_Hip" in names:
    fam = "cc_base"
elif any(n.startswith("DEF-") for n in names):
    fam = "rigify_def"
elif any(n.startswith("fml_un_") for n in names):
    fam = "multiversus"
elif any(n.startswith("bip_") for n in names):
    fam = "bip"
elif "lShldrBend" in names or "lThighBend" in names:
    fam = "daz"
elif has("pelvis", "clavicle_l", "thigh_l"):
    fam = "ue4"
elif any(n.endswith("_root") for n in names) and any(n.endswith("upperarm_l") for n in names):
    fam = "rp"
elif any(n.lower().endswith("hips") for n in names) and any(n.lower().endswith("leftarm") for n in names):
    fam = "mixamo"
elif sum(1 for n in names if re.match(r"^Bone(\.\d+)?$", n)) > 5:
    fam = "GENERIC (Bone.NNN - needs a hand map)"

lo = Vector((1e18,) * 3); hi = Vector((-1e18,) * 3)
deps = bpy.context.evaluated_depsgraph_get()
for o in meshes:
    ev = o.evaluated_get(deps)
    for c in ev.bound_box:
        w = ev.matrix_world @ Vector(c)
        for i in range(3):
            lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
size = hi - lo if meshes else Vector((0, 0, 0))
springy = sorted({n for n in names if re.search(
    r"(hair|braid|tail|skirt|cape|cloth|coat|ear|antenna|tie|ribbon)", n, re.I)})
print("%-6s %-14s arms=%d bones=%-4d meshes=%-3d extent=%.2f/%.2f/%.2f roots=%s springy=%d %s"
      % (TAG, fam, len(arms), len(arm.data.bones), len(meshes),
         size.x, size.y, size.z,
         [b.name for b in arm.data.bones if b.parent is None][:2],
         len(springy), springy[:4]))
