# Pose the HUMANOID bones and measure what moves.
#
# A podium shot cannot show a detached part, because at rest a bone nothing
# drives is indistinguishable from one that is driven. Posing is the test that
# can -- but a posed PICTURE can mislead the same way, so measure instead:
# evaluate every mesh at rest and again posed, and report each mesh's maximum
# vertex displacement. A mesh that stays still while the others move is hanging
# on something the game never rotates.
#
# The control is built in. If NOTHING moves, the pose did not apply and the
# run proves nothing -- which is reported as such rather than as "all clean".
import bpy, sys, json, struct, math
from mathutils import Vector, Euler

src = sys.argv[sys.argv.index("--") + 1]
out = sys.argv[sys.argv.index("--") + 2]

# Which nodes are the humanoid bones, read from the file itself.
d = open(src, "rb").read()
off, g = 12, None
while off < len(d):
    ln, ty = struct.unpack_from("<II", d, off)
    if ty == 0x4E4F534A:
        g = json.loads(d[off + 8:off + 8 + ln].decode("utf-8"))
    off += 8 + ln + ((4 - ln % 4) % 4)
nodes = [n.get("name", "?") for n in g["nodes"]]
hum = g["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
humname = {k: nodes[v["node"]] for k, v in hum.items()}

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.vrm(filepath=src)
dg = bpy.context.evaluated_depsgraph_get()

def world_verts():
    dgl = bpy.context.evaluated_depsgraph_get()
    res = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dgl)
        me = ev.to_mesh()
        mw = ev.matrix_world
        res[o.name] = [mw @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    return res

# A POSITIVE CONTROL, on demand. Everything measured so far MOVED, which is
# the good answer but does not show the test can spot the bad one. With
# POSE_CONTROL=<mesh substring> the named mesh is unbound from the armature
# before posing: it then cannot move, and the run must flag it. A detector
# that has never been seen to fire has not been verified.
import os as _os
_ctl = _os.environ.get("POSE_CONTROL")
if _ctl:
    for _o in bpy.data.objects:
        if _o.type == "MESH" and _ctl.lower() in _o.name.lower():
            for _m in list(_o.modifiers):
                if _m.type == "ARMATURE":
                    _o.modifiers.remove(_m)
            print("CONTROL: unbound %s from the armature" % _o.name)

rest = world_verts()

arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if arm is None:
    print("NO ARMATURE"); sys.exit(0)

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")

# Rotate several humanoid bones, so the whole body plainly changes shape.
PLAN = {"hips": (0.35, 0.0, 0.45), "spine": (0.25, 0.0, 0.0),
        "leftUpperArm": (0.0, 0.0, -0.8), "rightUpperArm": (0.0, 0.0, 0.8),
        "leftUpperLeg": (0.5, 0.0, 0.0), "rightUpperLeg": (-0.4, 0.0, 0.0),
        "head": (0.3, 0.0, 0.3), "neck": (0.15, 0.0, 0.0)}
applied = []
for key, rot in PLAN.items():
    bn = humname.get(key)
    if not bn:
        continue
    pb = arm.pose.bones.get(bn)
    if pb is None:
        continue
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = Euler(rot, "XYZ")
    applied.append(key)
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

posed = world_verts()

print("POSED BONES: %s" % ",".join(applied))
# PER VERTEX, not per mesh. A detached belt or a static pair of eyes lives
# INSIDE a mesh that moves, so a per-mesh maximum reports it as healthy --
# which is how "every mesh moved" can be true of a character whose belt hangs
# in space. Count the vertices that did not move, and say where they are.
rows = []
for nm, rv in rest.items():
    pv = posed.get(nm)
    if not pv or len(pv) != len(rv):
        continue
    mx = 0.0
    tot = 0.0
    stat = []
    for i, (a, b) in enumerate(zip(rv, pv)):
        dd = (a - b).length
        tot += dd
        if dd > mx:
            mx = dd
        if dd < float(_os.environ.get('POSE_STATIC_EPS', '0.001')):
            stat.append(a)
    rows.append((mx, tot / max(len(rv), 1), len(rv), nm, stat))
rows.sort(reverse=True)
moved = sum(1 for r in rows if r[0] > 0.01)
print("MESHES: %d, moved: %d" % (len(rows), moved))
if moved == 0:
    print("CONTROL FAILED -- nothing moved, so this run proves NOTHING")
for mx, av, n, nm, stat in rows:
    frac = 100.0 * len(stat) / max(n, 1)
    flag = ""
    if mx <= 0.01:
        flag = "   <-- WHOLE MESH DID NOT MOVE"
    elif frac > 1.0:
        # Vertices sitting exactly on a rotated bone's pivot legitimately stay
        # put, so a few are expected. A COHERENT CLUSTER away from the pivots
        # is a detached part; print its extent so the two can be told apart.
        xs = [v.x for v in stat]; ys = [v.y for v in stat]; zs = [v.z for v in stat]
        flag = ("   <-- %.1f%% static (%d verts), z %.2f..%.2f"
                % (frac, len(stat), min(zs), max(zs)))
    print("   %-30s verts=%-7d max=%.4f avg=%.4f%s"
          % (nm[:30], n, mx, av, flag))

# and a picture of the pose
sc = bpy.context.scene
allv = [v for vs in posed.values() for v in vs]
zmin = min(v.z for v in allv); zmax = max(v.z for v in allv)
cx = (min(v.x for v in allv) + max(v.x for v in allv)) / 2
sc.render.resolution_x = 560; sc.render.resolution_y = 760
try: sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError: pass
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 1.6
cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd)
sc.collection.objects.link(cam); sc.camera = cam
cd.type = "ORTHO"; cd.ortho_scale = (zmax - zmin) * 1.45
cam.location = (cx, -6, (zmin + zmax) / 2)
cam.rotation_euler = (math.radians(90), 0, 0)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("wrote", out)
