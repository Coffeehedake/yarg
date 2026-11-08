"""Build a YARG-ready VRM 1.0 from a rigged FBX.

usage: -- <fbx> <texdir> <height_m> <rig: mixamo|reallusion> <name> <out.vrm> <texmax>
"""
import math
import os
import re
import sys

import bpy
from mathutils import Matrix, Vector

a = sys.argv[sys.argv.index("--") + 1:]
FBX, TEXDIR, HEIGHT, RIG, NAME, OUTVRM, TEXMAX = (
    a[0], a[1], float(a[2]), a[3], a[4], a[5], int(a[6]))

# Echo the whole invocation. A build log that does not say what it was built FROM
# cannot be reproduced from, and every env switch below changes the result: an
# hour went into reconstructing Yoda's arguments out of the side effects his log
# happened to mention. Print it before anything can fail.
print("ARGV: " + " ".join("%r" % x for x in a))
print("ENV: " + " ".join(
    "%s=%r" % (_k, _v) for _k, _v in sorted(os.environ.items())
    if _k.startswith(("VRM_", "HAIR_", "BIND_", "RENDER_"))))

if FBX.lower().endswith(".blend"):
    bpy.ops.wm.open_mainfile(filepath=FBX)
elif FBX.lower().endswith((".usd", ".usdc", ".usda", ".usdz")):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.wm.usd_import(filepath=FBX)
elif FBX.lower().endswith((".glb", ".gltf")):
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=FBX)
else:
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=FBX)
bpy.context.scene.unit_settings.system = "METRIC"

# A file can carry more than one armature, and the FIRST one is not reliably
# the one that matters: a Rigify .blend keeps the 151-bone METARIG beside the
# 629-bone generated rig, and taking the metarig mapped 0 of 50 humanoid bones
# while every DEF- bone it wanted was on the other one. Pick the armature that
# actually deforms the most geometry.
_ARMS = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not _ARMS:
    raise SystemExit("ABORT: the file has no armature")
arm = _ARMS[0]
if len(_ARMS) > 1:
    _weight = {a: 0 for a in _ARMS}
    for _o in bpy.data.objects:
        if _o.type != "MESH":
            continue
        _n = len(_o.data.vertices)
        for _m in _o.modifiers:
            if _m.type == "ARMATURE" and _m.object in _weight:
                _weight[_m.object] += _n
        if _o.parent in _weight and _o.parent_type in {"ARMATURE", "BONE"}:
            _weight[_o.parent] += _n
    arm = max(_weight, key=lambda a: (_weight[a], len(a.data.bones)))
    print("chose armature '%s' (%d bones) of %d: it deforms %d vertices"
          % (arm.name, len(arm.data.bones), len(_ARMS), _weight[arm]))
meshes = [o for o in bpy.data.objects if o.type == "MESH"]

# Sketchfab scenes often ship set dressing (floors, backdrops, particle planes)
# alongside the character. Left in, they inflate the bundle and sit around the
# figure on the podium. EXCLUDE is an optional regex over mesh and material names.
EXCLUDE = a[7] if len(a) > 7 else ""
if EXCLUDE:
    keep = []
    for o in meshes:
        # Match the MESH name only. Matching material names too is a trap: a
        # character mesh that happens to carry an 'M_Outline' slot gets dropped
        # along with the scenery, leaving nothing to export.
        if re.search(EXCLUDE, o.name, re.I):
            print("  dropping mesh '%s' (matches /%s/)" % (o.name, EXCLUDE))
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            keep.append(o)
    meshes = keep
    if not meshes:
        raise SystemExit("ABORT: the exclude pattern /%s/ removed every mesh" % EXCLUDE)

# Anything that is neither the armature nor a kept mesh is studio furniture:
# lights, cameras, the turntable empty, and TEXT objects, which the VRM exporter
# happily converts to geometry (Pomni shipped two watermark captions as meshes).
# The exporter walks the scene, not the selection, so these have to go.
_keep = set(meshes) | {arm}
_junk = [o for o in bpy.data.objects if o not in _keep]
_junk_names = sorted(o.name for o in _junk)   # names first: a removed object cannot be read
# Some of that furniture is a PARENT of the character, and its transform is
# load-bearing. A USDZ arrives as a chain of empties -- Sketchfab_model,
# RootNode, SkinnedMeshes -- that between them stand the model up; deleting them
# laid Harley Quinn flat, and the height scale then stretched her DEPTH to 1.7 m
# and she came out 7.26 m wide. Hold the world placement of everything we keep
# across the purge.
_hold_world = [(o, o.matrix_world.copy()) for o in _keep]
for o in _junk:
    bpy.data.objects.remove(o, do_unlink=True)
for o, _mw in _hold_world:
    if o.parent is None:
        o.matrix_parent_inverse.identity()
    o.matrix_world = _mw
bpy.context.view_layer.update()
if _junk_names:
    print("purged %d non-character objects: %s" % (len(_junk_names), _junk_names[:12]))

# Drop empty placeholder meshes. A file can carry named objects with no
# geometry at all ('Droid1', 'VIFS01_1_1'), and they do real harm: they count as
# meshes, so the real geometry can be mistaken for scenery, and an empty one
# sent through automatic weighting reports a successful bind of nothing.
_empty = [o for o in meshes if not len(o.data.vertices)]
if _empty:
    _names = sorted(o.name for o in _empty)
    # Rebuild the keep-list BEFORE deleting: reading .name off an object that
    # has already been removed raises ReferenceError.
    meshes = [o for o in meshes if len(o.data.vertices)]
    for o in _empty:
        bpy.data.objects.remove(o, do_unlink=True)
    print("dropped %d empty mesh objects: %s" % (len(_names), _names[:8]))
if not meshes:
    raise SystemExit("ABORT: every mesh in this file is empty")

print("armature:", arm.name, "bones:", len(arm.data.bones), "meshes:", len(meshes))


def trace(stage):
    """Print one mesh's EVALUATED world box at a named stage.

    Set VRM_TRACE to a mesh-name substring. Chasing a part that ends up in the
    wrong place by reasoning about matrices is how three wrong fixes got
    written; measuring it at every stage says which stage moved it."""
    want = os.environ.get("VRM_TRACE")
    if not want:
        return
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    for o in bpy.data.objects:
        if o.type != "MESH" or want.lower() not in o.name.lower():
            continue
        ev = o.evaluated_get(deps)
        if not len(ev.data.vertices):
            continue
        ws = [ev.matrix_world @ v.co for v in ev.data.vertices]
        print("  TRACE %-22s %-28s x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f"
              % (stage, o.name[:28],
                 min(w.x for w in ws), max(w.x for w in ws),
                 min(w.y for w in ws), max(w.y for w in ws),
                 min(w.z for w in ws), max(w.z for w in ws)))


trace("after import")

# Some sources ship an animation (a Mixamo clip download, say). If one is left
# attached the model exports frozen mid-stride instead of in its bind pose, which
# wrecks the humanoid avatar. Drop any action and reset every bone to rest.
_had_anim = bool(arm.animation_data)
if _had_anim:
    print("clearing animation:", arm.animation_data.action.name if arm.animation_data.action else "<no action>")
    arm.animation_data_clear()
for o in meshes:
    if o.animation_data:
        o.animation_data_clear()


# ...unless the clip IS the T-pose, in which case it is the most valuable thing
# in the file and throwing it away is what breaks the arms.
#
# A Mixamo auto-rig download is the case that matters. Its REST skeleton is the
# arms-down original the uploader supplied -- Sonic HD measures 77.8 degrees off
# X with the elbow bent 32.4 -- and the "T-Pose" animation is the only thing that
# straightens it. Clear that and the rest pose is an A-pose, so the T-pose step
# further down has to REBUILD the T out of its own rotations. It gets the arm on
# to the X axis, and the result still reads as wrong: the synthesized rotation
# carries no information about the axial ROLL of the limb or the orientation of
# the hand, so the arm arrives twisted along its own length. That is the
# "squiggly arms" Sonic shipped with.
#
# Mixamo's clip has all of it right, because an animator posed it. So measure
# both and keep the better one. The test is deliberately narrow -- the pose must
# be a genuine T and rest must not be -- because most clips in these archives are
# jumps, ragdolls and walk cycles that MUST be dropped. Of 80-odd builds the only
# clips that pass are the ones whose name says T-Pose.
def _early_arms():
    """(sx, upper_arm, hand) per side, found by name before MAP exists."""
    _names = [b.name for b in arm.data.bones]
    _FING = ("finger", "thumb", "index", "middle", "ring", "pinky", "little")
    out = []
    for _sx, _tags in ((1.0, ("left", "_l", ".l", "l_")),
                       (-1.0, ("right", "_r", ".r", "r_"))):
        def _pick(words, skip=()):
            hits = [n for n in _names
                    if any(w in n.lower() for w in words)
                    and any(t in n.lower() for t in _tags)
                    and not any(s in n.lower() for s in skip)]
            hits.sort(key=len)
            return hits[0] if hits else None
        _ua = _pick(("upperarm", "upper_arm", "uparm", "arm"),
                    skip=_FING + ("forearm", "fore_arm", "lowarm", "lower_arm",
                                  "hand", "wrist", "shoulder", "shldr", "clavicle"))
        _hd = _pick(("hand", "wrist"), skip=_FING)
        if _ua and _hd:
            out.append((_sx, _ua, _hd))
    return out


def _early_legs():
    """(thigh, foot) per side, found the same way."""
    _names = [b.name for b in arm.data.bones]
    out = []
    for _tags in (("left", "_l", ".l", "l_"), ("right", "_r", ".r", "r_")):
        def _pick(words, skip=()):
            hits = [n for n in _names
                    if any(w in n.lower() for w in words)
                    and any(t in n.lower() for t in _tags)
                    and not any(s in n.lower() for s in skip)]
            hits.sort(key=len)
            return hits[0] if hits else None
        _th = _pick(("upleg", "up_leg", "upperleg", "thigh"),
                    skip=("lowleg", "lower_leg", "foot", "toe", "calf", "shin"))
        if _th is None:
            _th = _pick(("leg",), skip=("lowleg", "lower_leg", "foot", "toe",
                                        "calf", "shin", "upleg", "up_leg"))
        _ft = _pick(("foot", "ankle"), skip=("toe", "ball"))
        if _th and _ft and _th != _ft:
            out.append((_th, _ft))
    return out


def _bone_line(a_name, b_name, pose):
    """The a->b bone line in WORLD space.

    Bone heads are in the armature's own space, and an FBX import leaves the
    armature object rotated 90 degrees about X so that the source's Y-up becomes
    Blender's Z-up. Measured in that local space Sonic stands 57 units tall along
    +Y, so a perfectly straight pair of legs reads 87.9 degrees away from -Z and
    a T-pose looks like a frame of motion. X happens to survive the rotation,
    which is why an arms-only test passes anyway and hides the bug.
    """
    M = arm.matrix_world
    if pose:
        a, b = arm.pose.bones[a_name].head, arm.pose.bones[b_name].head
    else:
        a, b = arm.data.bones[a_name].head_local, arm.data.bones[b_name].head_local
    return (M @ b) - (M @ a)


def _off_axis(v, tgt):
    """Degrees between a vector and a target direction."""
    if v.length < 1e-9:
        return 180.0
    return math.degrees(math.acos(max(-1.0, min(1.0, v.normalized().dot(tgt)))))


def _off_x(a_name, b_name, sx, pose):
    return _off_axis(_bone_line(a_name, b_name, pose), Vector((sx, 0.0, 0.0)))


_keep_anim_pose = False
if _had_anim:
    bpy.context.view_layer.update()
    _ea = _early_arms()
    if len(_ea) == 2:
        _p = max(_off_x(_ua, _hd, _sx, True) for _sx, _ua, _hd in _ea)
        _r = max(_off_x(_ua, _hd, _sx, False) for _sx, _ua, _hd in _ea)
        # Straight arms alone are not enough: a jump or a ragdoll frame can have
        # one arm out. Read the LEGS too, which a T-pose keeps straight down and
        # a frame of motion does not. Do NOT test the root's translation instead
        # -- Mixamo's own T-pose clip moves the hips 11 units of a 57-unit rig,
        # so a drift test rejects the very pose this is here to keep.
        _legs = _early_legs()
        _lg = 180.0
        if _legs:
            _lg = 0.0
            for _th, _ft in _legs:
                _lg = max(_lg, _off_axis(_bone_line(_th, _ft, True),
                                         Vector((0.0, 0.0, -1.0))))
        print("  animated pose: arms %.1f deg off X, legs %.1f deg off -Z; "
              "rest pose arms %.1f deg off X" % (_p, _lg, _r))
        if _p < 10.0 <= _r and _lg < 20.0:
            _keep_anim_pose = True
            print("  KEEPING the animated pose: it is a T-pose and the rest pose "
                  "is not, so it is the authored bind the model wants. Synthesizing "
                  "a T from the rest pose instead would lose the limb roll.")

# The second reason to keep an animated pose: the GEOMETRY was sculpted around
# it, so it is the bind pose no matter what the clip looks like.
#
# Anakin Skywalker ships as "anakin pose.fbx" -- a character frozen in a mid-air
# leap, with one skinned head and sixteen thousand vertices of unrigged body. The
# clip is not a T-pose and never will be, so the test above correctly declines
# it. But the skeleton still belongs to that leap: measured against the UNRIGGED
# meshes, bone midpoints sit 0.443 m from the nearest vertex at rest and 0.067 m
# when posed. At rest the skeleton is simply not in the body.
#
# Reset such a rig to its rest pose and the bones walk out of the mesh, so
# nothing can be weighted to them and the automatic rescue below has no chance.
# Bake the pose instead and bones and geometry coincide, which is the one
# configuration worth binding in.
#
# Measure on the unrigged meshes ONLY, and on raw vertex coordinates. A SKINNED
# mesh stores its vertices at bind position, so for those the rest pose always
# wins by construction and the comparison says nothing. An unrigged mesh is
# static geometry, so where it sits is evidence.
if _had_anim and not _keep_anim_pose:
    _loose = [o for o in meshes
              if not any(m.type == "ARMATURE" for m in o.modifiers)
              and not o.vertex_groups and len(o.data.vertices) >= 50]
    _pts = [o.matrix_world @ _v.co for o in _loose for _v in o.data.vertices]
    if len(_pts) >= 200:
        from mathutils.kdtree import KDTree
        _kd = KDTree(len(_pts))
        for _i, _q in enumerate(_pts):
            _kd.insert(_q, _i)
        _kd.balance()
        _M = arm.matrix_world
        _fit = {}
        for _lbl, _posed in (("rest", False), ("pose", True)):
            _ds = []
            for _b in arm.data.bones:
                if "_end" in _b.name:
                    continue
                if _posed:
                    _pb = arm.pose.bones[_b.name]
                    _mid = _M @ ((_pb.head + _pb.tail) / 2.0)
                else:
                    _mid = _M @ ((_b.head_local + _b.tail_local) / 2.0)
                _ds.append(_kd.find(_mid)[2])
            _fit[_lbl] = sum(_ds) / len(_ds) if _ds else 0.0
        _hs = [(_M @ _b.head_local).z for _b in arm.data.bones]
        _span = (max(_hs) - min(_hs)) or 1.0
        print("  rig fit against %d unrigged mesh(es): rest %.3f m from the "
              "geometry, posed %.3f m (rig spans %.2f m)"
              % (len(_loose), _fit["rest"], _fit["pose"], _span))
        if _fit["pose"] < 0.5 * _fit["rest"] and _fit["pose"] < 0.08 * _span:
            _keep_anim_pose = True
            print("  KEEPING the animated pose: the skeleton lies INSIDE the "
                  "unrigged geometry when posed and outside it at rest, so the "
                  "model was sculpted in this pose and this is its bind. "
                  "Resetting to rest would move the bones out of the mesh.")

# Reset the bones ONLY if an animation was actually attached. A static pose in
# matrix_basis is not a stray animation frame -- it can be the model's SHAPE.
# Alcina Dimitrescu is 9 feet 6 inches because her pose says so, with no action
# attached at all; resetting her to rest compressed her head and torso to 59%
# and left her hat and hair floating above them. The pose that survives here is
# baked into the rest pose further down, before anything is scaled.
if _had_anim and not _keep_anim_pose:
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
else:
    _static = sum(1 for pb in arm.pose.bones
                  if any(abs(pb.matrix_basis[i][j] - (1.0 if i == j else 0.0)) > 1e-5
                         for i in range(4) for j in range(4)))
    if _static:
        print("keeping a static pose on %d bones (%s)"
              % (_static, "this pose is the bind, per the reason above"
                 if _keep_anim_pose
                 else "no animation was attached, so this is the model's shape, "
                      "not a stray frame"))
bpy.context.view_layer.update()
print("actions left in file:", [a.name for a in bpy.data.actions])


def bake_pose_to_rest(why):
    """Make the current pose the rest pose, moving the geometry with it.

    A BIND is defined relative to the rest pose, so the rest pose has to be
    final before anything is bound to the skeleton. Bind first and bake second
    and the pose is applied twice to whatever was just bound: Anakin Skywalker's
    body was auto-weighted while the armature stood in his leap, then the leap
    was baked into rest underneath it, and he exported in pieces -- head, hair
    and eyes in one place and the body half a metre away, because the head was
    skinned before the bake and the body after it.

    Compute the deformation by hand rather than applying the armature modifier:
    these meshes also carry Solidify and Subdivision, so the evaluated mesh has a
    different vertex count from the one being written back.
    """
    posed = [pb for pb in arm.pose.bones
             if any(abs(pb.matrix_basis[i][j] - (1.0 if i == j else 0.0)) > 1e-5
                    for i in range(4) for j in range(4))]
    if not posed:
        return False
    # Let BLENDER compute the deformation; do not reimplement it.
    #
    # The obvious hand-rolled version -- sum w * (pose @ rest-inverse) @ v over
    # each vertex's groups -- looks like the armature modifier and is not it. On
    # Anakin it left every unrigged mesh correct and moved the one already
    # skinned mesh, his head, by 0.523 m, which read as a head floating above a
    # perfectly good body. Weight normalisation, unweighted vertices and the
    # object's own parenting all feed into the real deform.
    #
    # So evaluate the object with ONLY its armature modifier switched on and
    # copy the result back. to_mesh() returns coordinates in the object's own
    # space, which is what the base mesh wants, and a deform modifier cannot
    # change the vertex count. The other modifiers are the reason this cannot
    # simply apply the modifier stack: a Solidify or Subdivision ahead of it
    # would change that count.
    _skipped = []
    for _o in meshes:
        if not any(m.type == "ARMATURE" and m.object is arm for m in _o.modifiers):
            continue
        _saved = [(m, m.show_viewport) for m in _o.modifiers]
        for _m, _ in _saved:
            if _m.type != "ARMATURE":
                _m.show_viewport = False
        _dg = bpy.context.evaluated_depsgraph_get()
        _ev = _o.evaluated_get(_dg)
        _me = _ev.to_mesh()
        _coords = [_v.co.copy() for _v in _me.vertices]
        _ev.to_mesh_clear()
        for _m, _flag in _saved:
            _m.show_viewport = _flag
        if len(_coords) != len(_o.data.vertices):
            _skipped.append(_o.name)
            continue
        if _o.data.users > 1:
            _o.data = _o.data.copy()
        for _v, _c in zip(_o.data.vertices, _coords):
            _v.co = _c
        _o.data.update()
    if _skipped:
        print("  WARNING: could not bake the pose into %s -- evaluating with "
              "only the armature modifier still changed the vertex count"
              % _skipped)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    print("  baked a non-identity rest pose (%d bones) into the rest pose%s"
          % (len(posed), why))
    return True

# Drop shape keys and keep the BASE mesh.
#
# A shape key is a morph target and a morph target's weight is ZERO in engine, so
# the base mesh is what YARG will show no matter what Blender displays. Build
# around any other mix and the measurements taken here describe a model that will
# never exist in the game.
#
# Prix is the worked example, and she fooled three rounds of diagnosis. Her FBX
# ships six keys non-zero, at least one of which holds a corrupt, four-times-
# oversized body. Blender's viewport, the evaluated bounds and every render
# therefore showed a 1.95 m tangle of shards, while the base mesh - the real
# character, in a clean T-pose - was 0.478 m. The builder scaled to make the
# GARBAGE 1.70 m, which left the real mesh at 0.416 m, and that is exactly the
# size she arrived at in game. "Tiny" was never a scale bug at all: it was the
# build measuring a shape the engine would never render.
#
# Zeroing first is strictly more faithful than collapsing at the author's values,
# because zero is what the engine uses.
for o in meshes:
    sk = o.data.shape_keys
    if not sk or not sk.key_blocks:
        continue
    live = [(kb.name, round(kb.value, 3)) for kb in sk.key_blocks if abs(kb.value) > 1e-6]
    nkeys = len(sk.key_blocks)
    basis = [p.co.copy() for p in sk.key_blocks[0].data]
    bpy.context.view_layer.objects.active = o
    o.shape_key_clear()
    for i, c in enumerate(basis):
        o.data.vertices[i].co = c
    o.data.update()
    print("  dropped %d shape keys on '%s', kept the base mesh%s"
          % (nkeys, o.name,
             " (IGNORED non-zero: %s - the engine would have ignored them too)" % live
             if live else ""))

def bounds():
    lo = Vector((1e18,) * 3); hi = Vector((-1e18,) * 3)
    deps = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        ev = o.evaluated_get(deps)
        for c in ev.bound_box:
            w = ev.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi


lo, hi = bounds()
size = hi - lo
print("imported size: %.4f %.4f %.4f" % (size.x, size.y, size.z))
up = max(range(3), key=lambda i: size[i])
if up == 1:
    arm.rotation_euler[0] += math.radians(90)
    bpy.context.view_layer.update()
    lo, hi = bounds(); size = hi - lo
    print("stood up -> %.4f %.4f %.4f" % (size.x, size.y, size.z))

# Meshes parented to a BONE rather than to the object cannot be baked as
# ordinary children, so convert them into skinned meshes first: re-parent to the
# object, weight every vertex to the bone they hung off, and drive them with an
# Armature modifier. Behaviour is identical (eyes still follow the head) but the
# geometry now bakes correctly, which matters because YARG parents the microphone
# to the hand and it would inherit any scale left on the root.
# Pick the FIRST UV layer where a mesh has several. Maya exports often carry
# spare channels ('map1', 'map1.001', 'map1.002') and whichever one Blender
# marks active may be empty, so a perfectly good texture samples one blank texel
# and the surface renders flat white - which is what happened to Thanos' face
# while his body, a single-UV mesh, textured correctly.
for o in meshes:
    uvs = o.data.uv_layers
    if len(uvs) > 1 and not uvs[0].active_render:
        uvs[0].active = True
        uvs[0].active_render = True
        print("  '%s' had %d UV layers; using '%s'" % (o.name, len(uvs), uvs[0].name))

# Inverted-hull outlines do not survive the trip. A Solidify modifier paired
# with a black "line art" material draws an outline in Blender by flipping an
# offset shell inside-out; exported, the shell is just more geometry and it
# wraps the character in translucent duplicates. Opt-in, because a Solidify can
# also be load-bearing (Pomni's eyelids use one and she exports correctly).
if os.environ.get("VRM_DROP_SOLIDIFY"):
    _n = 0
    for o in meshes:
        for m in [m for m in o.modifiers if m.type == "SOLIDIFY"]:
            o.modifiers.remove(m)
            _n += 1
    if _n:
        print("removed %d Solidify modifiers (inverted-hull outlines)" % _n)

def _point_seg(p, a, b):
    """Distance from a point to a line segment."""
    ab = b - a
    l2 = ab.length_squared
    if l2 < 1e-12:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
    return (a + ab * t - p).length


def flatten(pre):
    """Bake `pre` x (world transform) of the armature and every mesh into their
    DATA, leaving every object matrix at identity.

    This is the only reliable way to resize a skinned character, and getting it
    wrong is invisible until the model is in the engine. The obvious route --
    scale the armature, select the lot, transform_apply -- does NOT work: for a
    mesh that is a CHILD of the armature, transform_apply bakes only that
    object's own local matrix, and Blender pushes the parent's share into
    matrix_parent_inverse so the viewport does not jump. The scale therefore
    survives as a hidden parent-inverse factor. Two separate symptoms came out
    of that one cause:

      * the viewport and the evaluated bounds read correctly while the exported
        mesh DATA is the wrong size, so the character renders at the data size
        in engine (Prix: 0.416 m of geometry reported as 1.70 m); and
      * the VRM exporter writes those meshes as STATIC nodes carrying a scale
        rather than as skinned ones, so the character cannot animate at all, no
        matter how good the avatar and the controller are (Pomni: 18 mesh nodes,
        0 of them skinned, node scales of 0.036 and 0.046).

    Transforming the data directly, rather than going through transform_apply,
    also survives shape keys -- the operator refuses a mesh that has them.
    """
    snap = [(o, pre @ o.matrix_world) for o in meshes + [arm]]
    for o, mw in snap:
        if o.data.users > 1:
            o.data = o.data.copy()
        if o.type == "MESH":
            o.data.transform(mw, shape_keys=True)
            # A mirrored object (scale -1 on an axis, as a mirror-duplicated
            # eyelash gets) has a negative determinant: baking it turns the mesh
            # inside out unless the winding is flipped to match.
            if mw.determinant() < 0:
                o.data.flip_normals()
                print("  flipped winding on mirrored mesh '%s'" % o.name)
            o.data.update()
        elif hasattr(o.data, "transform"):
            o.data.transform(mw)
        else:
            raise SystemExit("ABORT: %s data has no transform()" % o.type)
        o.parent = None
        o.matrix_parent_inverse.identity()
        o.matrix_basis.identity()
        # matrix_basis does NOT cover the delta transforms, and matrix_world
        # does. Leave a delta behind and it is still in the exported node: a
        # delta scale of -1 on one eyelash is a hard VRM 1.0 validation error
        # ("negative value for the scale") that cancels the whole export.
        o.delta_location = (0.0, 0.0, 0.0)
        o.delta_rotation_euler = (0.0, 0.0, 0.0)
        o.delta_rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        o.delta_scale = (1.0, 1.0, 1.0)
    for o in meshes:
        o.parent = arm
        o.parent_type = "OBJECT"
        o.matrix_parent_inverse.identity()
        o.matrix_basis.identity()
    bpy.context.view_layer.update()



# VRM_FINGER_FILL: give finger geometry that has no bone of its own the nearest
# finger chain that does.
#
# A rig can carry fewer finger chains than the mesh has fingers. Hatsune Miku's
# 3ds Max Biped has a thumb and two two-joint chains per hand while the mesh
# models five fingers, so her ring and little fingers are weighted to the HAND
# and stay rigid while the others curl. Mixamo's auto-rigger refuses her
# outright -- three attempts, three bounces back to the marker screen -- and at
# 59 vertices per hand there is nothing to hang new chains off: each finger is
# about ten vertices. Re-aiming those vertices at the nearest chain that does
# exist costs nothing and makes the whole hand move together.
if os.environ.get("VRM_FINGER_FILL"):
    _filled = 0
    for _side in ("left", "right"):
        _hand = MAP.get("%s_hand" % _side) if "MAP" in dir() else None
        _hand = _hand or next((b.name for b in arm.data.bones
                               if b.name.lower().endswith(
                                   ("l hand", "r hand", "lhand", "rhand"))
                               and ("l" if _side == "left" else "r")
                               in b.name.lower().split()[-2:][0].lower()), None)
    _hands = [b for b in arm.data.bones if "hand" in b.name.lower()]
    for _hb in _hands:
        _side_tag = _hb.name.lower()
        _chains = [b for b in arm.data.bones
                   if b.name != _hb.name and _hb.name in
                   [a.name for a in b.parent_recursive]]
        _tips = [b for b in _chains if not b.children]
        if not _tips:
            continue
        _segs = []
        for _b in _chains:
            _segs.append((_b.name, _b.head_local.copy(), _b.tail_local.copy()))
        for _o in meshes:
            _g2n = {g.index: g.name for g in _o.vertex_groups}
            _M = arm.matrix_world.inverted() @ _o.matrix_world
            _hw, _ht = _hb.head_local, _hb.tail_local
            _axis = (_ht - _hw)
            _len = _axis.length
            if _len < 1e-9:
                continue
            _axis = _axis / _len
            _grp = {}
            for _v in _o.data.vertices:
                _w = 0.0
                for _g in _v.groups:
                    if _g2n.get(_g.group) == _hb.name:
                        _w = _g.weight
                    elif _g2n.get(_g.group) in {n for n, _, _ in _segs} and _g.weight > 0.05:
                        _w = 0.0
                        break
                if _w <= 0.5:
                    continue
                _p = _M @ _v.co
                # "Past the knuckles" cannot be measured along the hand bone:
                # on this rig the finger bones start beyond its tail, so no
                # hand-weighted vertex is past even 60% of its length. Ask the
                # simpler question instead -- is this vertex nearer a finger
                # bone than the hand bone?
                _best = min(_segs, key=lambda sg: _point_seg(_p, sg[1], sg[2]))
                if _point_seg(_p, _best[1], _best[2]) >= _point_seg(_p, _hw, _ht):
                    continue
                _grp.setdefault(_best[0], []).append(_v.index)
            for _n, _vs in _grp.items():
                _vg = _o.vertex_groups.get(_n) or _o.vertex_groups.new(name=_n)
                _vg.add(_vs, 1.0, "REPLACE")
                _hvg = _o.vertex_groups.get(_hb.name)
                if _hvg:
                    _hvg.remove(_vs)
                _filled += len(_vs)
    if _filled:
        bpy.context.view_layer.update()
        print("  finger fill: %d vertices past the knuckles moved from the hand "
              "bone onto the nearest finger chain" % _filled)


# Convert constraint- and bone-driven parts into proper skinned meshes BEFORE
# anything else looks at what is rigged. A part held on by a CHILD_OF constraint
# has no armature modifier and no vertex groups, so the unrigged-mesh rescue
# below claimed it, re-baked the armature's object transform, and the constraint
# then re-evaluated against an armature that had moved: Alcina Dimitrescu's hat
# was already 0.362 m tall instead of 0.651 by the time the conversion ran, and
# every fix aimed at the conversion was aimed at the wrong stage.
# If the pose we decided to KEEP is the bind, settle it into the rest pose now,
# before any of that conversion or the rescue binds a single vertex. A bind is
# expressed relative to rest, so a rest pose that changes afterwards is applied
# twice to everything bound before the change and once to everything bound
# after. That is what shattered Anakin: his head was skinned in the file and his
# body was auto-weighted here, so the two were bound on opposite sides of the
# bake and ended up half a metre apart.
if _keep_anim_pose:
    bake_pose_to_rest(" -- doing this BEFORE anything binds to the skeleton, "
                      "since a bind is relative to the rest pose")

bpy.context.view_layer.update()   # pose matrices below must be evaluated
CHILD_OF = [(o, c) for o in meshes for c in list(o.constraints)
            if c.type == "CHILD_OF" and c.target is arm]
for o, c in CHILD_OF:
    _bone = getattr(c, "subtarget", "") or ""
    # Read the EVALUATED object. A constraint's contribution lives only there:
    # the original datablock's matrix_world is the basis, without it. Alcina
    # Dimitrescu's armature is scaled 1.8577, her hat hangs off it by
    # constraint, and reading the unevaluated matrix lost exactly that factor --
    # the hat came out 0.348 m tall against 0.651 and no amount of correcting
    # its PLACEMENT helped, because the size was wrong before placement began.
    _mw = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()
    if os.environ.get("VRM_TRACE", "").lower() in o.name.lower():
        _dg0 = bpy.context.evaluated_depsgraph_get()
        _ev0 = o.evaluated_get(_dg0)
        _w0 = [_ev0.matrix_world @ v.co for v in _ev0.data.vertices]
        _raw = [v.co for v in o.data.vertices]
        print("    ENTRY mw_scale=%s evalmw_scale=%s | eval z %.3f..%.3f | raw z %.3f..%.3f | arm_scale=%s"
              % (tuple(round(v, 4) for v in o.matrix_world.to_scale()),
                 tuple(round(v, 4) for v in _mw.to_scale()),
                 min(w.z for w in _w0), max(w.z for w in _w0),
                 min(v.z for v in _raw), max(v.z for v in _raw),
                 tuple(round(v, 4) for v in arm.matrix_world.to_scale())))
    o.constraints.remove(c)
    o.matrix_world = _mw
    if _bone and _bone in {b.name for b in arm.data.bones}:
        # The constraint put the part where the POSED bone is. An armature
        # modifier applies that same pose again, so a posed rig doubles it:
        # Alcina's armature carries a pose on 23 of its 66 bones and her hat,
        # hair and earrings floated a hand's width above her head. Place the
        # part at the bone's REST position, so re-applying the pose lands it
        # exactly where the author put it. A no-op on an unposed rig.
        _pb = arm.pose.bones.get(_bone)
        _rb = arm.data.bones.get(_bone)
        if _pb is not None and _rb is not None:
            _A = arm.matrix_world.copy()
            # Two things have to be true before an armature modifier will put
            # this part back exactly where the constraint had it, and getting
            # either wrong is invisible until the character is built:
            #
            #  1. REST, not posed. The constraint placed the part at the POSED
            #     bone; a modifier applies that pose again. Undo it first.
            #  2. The part must sit in the ARMATURE's object space. Blender
            #     conjugates the deformation by (arm.matrix_world-1 @
            #     mesh.matrix_world), so a mesh at scale 1.0 hanging off an
            #     armature at scale 1.8577 has the pose applied to it through
            #     that ratio. Alcina Dimitrescu's hat shrank by exactly
            #     1/1.8577 -- 0.651 m tall to 0.348 -- and no amount of
            #     correcting the PLACEMENT fixed a scale that was coming from
            #     the space.
            _want = (_A @ _rb.matrix_local @ _pb.matrix.inverted()
                     @ _A.inverted()) @ _mw
            _D = _A.inverted() @ _want
            if o.data.users > 1:
                o.data = o.data.copy()
            o.data.transform(_D)
            if _D.determinant() < 0:
                o.data.flip_normals()
            o.data.update()
            o.parent = None
            o.matrix_parent_inverse.identity()
            o.matrix_world = _A
        _vg = o.vertex_groups.get(_bone) or o.vertex_groups.new(name=_bone)
        _vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
        if os.environ.get("VRM_TRACE", "").lower() in o.name.lower():
            bpy.context.view_layer.update()
            _dg = bpy.context.evaluated_depsgraph_get()
            _ev = o.evaluated_get(_dg)
            _w = [_ev.matrix_world @ v.co for v in _ev.data.vertices]
            print("    PRE-MOD  mw_scale=%s parent=%s  z %.3f..%.3f"
                  % (tuple(round(v, 4) for v in o.matrix_world.to_scale()),
                     o.parent.name if o.parent else None,
                     min(w.z for w in _w), max(w.z for w in _w)))
        if not any(m.type == "ARMATURE" for m in o.modifiers):
            _md = o.modifiers.new(name="Armature", type="ARMATURE")
            _md.object = arm
        if os.environ.get("VRM_TRACE", "").lower() in o.name.lower():
            bpy.context.view_layer.update()
            _dg = bpy.context.evaluated_depsgraph_get()
            _ev = o.evaluated_get(_dg)
            _w = [_ev.matrix_world @ v.co for v in _ev.data.vertices]
            print("    POST-MOD mw_scale=%s  z %.3f..%.3f"
                  % (tuple(round(v, 4) for v in o.matrix_world.to_scale()),
                     min(w.z for w in _w), max(w.z for w in _w)))
        print("  rebound constraint-driven mesh '%s' to bone '%s' as a skinned mesh"
              % (o.name, _bone))
    else:
        print("  removed a CHILD_OF constraint on '%s' that named no usable bone"
              % o.name)
# Any OTHER constraint would survive flatten the same way, so refuse rather than
# ship a character whose parts drift.
for o in meshes:
    for c in list(o.constraints):
        o.constraints.remove(c)
        print("  removed a leftover %s constraint on '%s'" % (c.type, o.name))
if CHILD_OF:
    bpy.context.view_layer.update()

trace("after CHILD_OF")

BONE_PARENTED = [o for o in meshes if o.parent_type == "BONE" and o.parent_bone]
for o in BONE_PARENTED:
    bone = o.parent_bone
    mw = o.matrix_world.copy()
    o.parent_type = "OBJECT"
    o.matrix_world = mw
    # Same double-pose trap as the CHILD_OF conversion above.
    _pb = arm.pose.bones.get(bone)
    _rb = arm.data.bones.get(bone)
    if _pb is not None and _rb is not None:
        _A = arm.matrix_world
        o.matrix_world = (_A @ _rb.matrix_local @ _pb.matrix.inverted()
                          @ _A.inverted()) @ mw
    vg = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
    vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    if not any(m.type == "ARMATURE" for m in o.modifiers):
        md = o.modifiers.new(name="Armature", type="ARMATURE")
        md.object = arm
    print("  rebound bone-parented mesh '%s' to bone '%s' as a skinned mesh" % (o.name, bone))
if BONE_PARENTED:
    bpy.context.view_layer.update()

# A mesh with no armature modifier AND no vertex groups is not rigged at all.
# It exports as a static node, so it neither animates nor follows the T-pose
# correction - Judy Hopps' 17,064-vertex body arrived this way while a 355-vertex
# offcut was the only skinned thing in the file. Bind it with automatic weights;
# an approximate binding that moves beats a perfect one that cannot.
# A model whose bind pose we had to REPLACE cannot keep its old weights.
#
# When the animated pose turns out to be the bind, the rest pose the file
# shipped with is discarded -- and every weight already in the file was authored
# against that discarded rest. Meshes bound before the swap and meshes bound
# after it then describe two different skeletons. Anakin is the worked example:
# his body, auto-weighted here, came out a clean standing figure, while his
# head, eyes, hair and shoulder tabards -- the only parts the file itself had
# bound, to four bones between them -- floated half a metre above it. Nothing
# was wrong with either binding; they simply were not the same binding.
#
# So when the pose was swapped in, re-bind everything in one pass, in one
# configuration, at one moment. Only meshes bound to FEW bones are taken: a
# properly skinned character carries real weights worth keeping, whereas these
# are rigid attachments that automatic weighting reproduces at no loss.
_REBIND_MAXG = int(os.environ.get("VRM_REBIND_MAX_GROUPS", "4"))
# OPT-IN. Measured on Yoda, whose eyes and eyelashes this claimed and whose
# scale factor then moved from 0.6471 to 0.1022 -- a six-fold change in the
# geometry it was measuring. It is right for a model whose own bindings are
# a handful of rigid attachments (Anakin), and wrong where those bindings
# were authored and good. Ask for it.
if _keep_anim_pose and os.environ.get("VRM_REBIND_STALE"):
    _stale = [o for o in meshes
              if any(m.type == "ARMATURE" and m.object is arm for m in o.modifiers)
              and 0 < len(o.vertex_groups) <= _REBIND_MAXG]
    for _o in _stale:
        for _m in [m for m in _o.modifiers if m.type == "ARMATURE"]:
            _o.modifiers.remove(_m)
        for _g in list(_o.vertex_groups):
            _o.vertex_groups.remove(_g)
        _o.parent_type = "OBJECT"
    if _stale:
        bpy.context.view_layer.update()
        print("  dropped the old weights on %d mesh(es) bound to %d bones or "
              "fewer (%s): their weights were authored against the rest pose "
              "this build just replaced, so they are re-bound below with "
              "everything else"
              % (len(_stale), _REBIND_MAXG, [o.name for o in _stale][:6]))

UNRIGGED = [o for o in meshes
            if not any(m.type == "ARMATURE" for m in o.modifiers)
            and not o.vertex_groups
            and not (o.parent_type == "BONE" and o.parent_bone)]
if UNRIGGED:
    # An unrigged mesh and its armature were never forced to agree, because
    # nothing ever deformed one by the other. The HD Sonic's skeleton stands
    # 35 units tall beside a 1.009 m mesh -- the FBX put the inch-to-metre
    # conversion on the MESH object alone -- so bone heat finds no vertex near
    # any bone and binds nothing at all. That failure is silent: the model
    # exports, renders perfectly at rest, reports a clean 21/21 humanoid, and
    # cannot move a finger in game.
    #
    # Fit the skeleton to the mesh instead: keep its rotation, scale uniformly
    # by the ratio of the two heights, and stand the lowest bone on the mesh's
    # lowest point. Adopt the fit only if it actually brings the bones CLOSER
    # to the surface, measured, so a rig that was already aligned is left alone.
    def _bone_fit_error(mw, verts, bones):
        tot = 0.0
        for b in bones:
            q = mw @ b.head_local
            tot += min((q - v).length for v in verts)
        return tot / max(1, len(bones))

    # Hold the meshes still across the refit. They are CHILDREN of the
    # armature, so moving it drags them with it -- the refit then cancels
    # itself out exactly, leaving the skeleton as misfitted as before while
    # every measurement says it worked, and the whole scene 34x too small.
    # Refitting and flattening are rescues for a skeleton that matches NOTHING
    # -- a model shipped with no working rig, like the HD Sonic. If the armature
    # already deforms other meshes correctly then the skeleton is right, and
    # resizing it to fit one stray unweighted part is vandalism: Alcina
    # Dimitrescu has a 49,091-vertex dress train with no weights, and fitting
    # the skeleton to it shrank her whole rig by 0.5568, which put her hat above
    # her head and her cigarette holder through the floor. Bind the stray part
    # where it is and leave the rig alone.
    _already_bound = [o for o in meshes
                      if o not in UNRIGGED
                      and any(m.type == "ARMATURE" and m.object is arm
                              for m in o.modifiers)]
    if _already_bound:
        print("  %d mesh(es) are already bound to this armature, so the "
              "skeleton is not refitted for the %d unrigged one(s)"
              % (len(_already_bound), len(UNRIGGED)))
    _vs = [] if _already_bound else [
        v for o in UNRIGGED for v in (o.matrix_world @ x.co for x in o.data.vertices)]
    _vs = _vs[::max(1, len(_vs) // 2000)]
    _bs = [b for b in arm.data.bones if b.use_deform][:24]
    if _vs and _bs:
        _hz = [ (arm.matrix_world @ b.head_local).z for b in arm.data.bones ]
        _span = max(_hz) - min(_hz)
        _mlo = min(v.z for v in _vs)
        _mspan = max(v.z for v in _vs) - _mlo
        if _span > 1e-9 and _mspan > 1e-9:
            _k = _mspan / _span
            _fit = (Matrix.Translation((0.0, 0.0, _mlo - min(_hz) * _k))
                    @ Matrix.Diagonal((_k, _k, _k, 1.0)) @ arm.matrix_world)
            _before = _bone_fit_error(arm.matrix_world, _vs, _bs)
            _after = _bone_fit_error(_fit, _vs, _bs)
            if _after < _before * 0.9:
                arm.matrix_world = _fit
                bpy.context.view_layer.update()
                print("  refitted the skeleton to the unrigged mesh (x%.4f): mean "
                      "bone-to-surface %.3f m -> %.3f m" % (_k, _before, _after))
    # parent_set() re-parents the mesh to the ARMATURE OBJECT, so whatever
    # rotation that object is carrying lands on the mesh. An FBX whose armature
    # root keeps the importer's 90-degree Z-up correction while the mesh's own
    # world matrix does not (Blender hides the difference in
    # matrix_parent_inverse) therefore comes out LYING ON ITS BACK, and the
    # height scale that follows reads the depth as the height: the HD Sonic
    # measured 0.736 x 1.500 x 1.000 against a source of 0.495 x 0.672 x 1.009.
    # Bake the armature's transform into its bones first and restore every
    # mesh's world placement, so the re-parent is a no-op geometrically.
    if arm.matrix_world != Matrix.Identity(4) and not _already_bound:
        # Bake the armature's object transform into the DATA -- but for the
        # armature and every mesh TOGETHER, which is exactly what flatten()
        # does. Doing it for the armature alone and then putting the meshes
        # back by world matrix is not equivalent: a mesh the armature DEFORMS
        # has its deformation conjugated by (arm.matrix_world-1 @
        # mesh.matrix_world), so moving one and not the other re-aims every
        # bound part. Alcina Dimitrescu's cigarette holder and its smoke went
        # from z 0.958..1.322 to z -0.647..-0.283 -- through the floor -- on
        # that one step alone.
        flatten(Matrix.Identity(4))
        print("  flattened the armature's object transform before automatic "
              "weighting")
    # Automatic weights bind to every bone with use_deform set, and an FBX
    # import adds a '_end' leaf to the tip of each chain. Those tips sit INSIDE
    # the mesh, so bone-heat happily gives them the surrounding geometry: Judy
    # Hopps' body came out weighted to 'pelvis.R_end', 'Pupil.R_end' and the
    # head, and her arms then ignored the arm bones entirely. Take the tips out
    # of the running first; they never deform anything in a sane rig.
    # Facial bones sit inside the head and bone-heat will happily hand them
    # whole limbs: Judy's torso came back weighted to 'Pupil.R' and 'Eye.L'.
    # They cannot deform a body, so take them out of the running as well.
    _FACE = re.compile(r"(eye|pupil|brow|lash|lid|tongue|teeth|jaw|nose|mouth|"
                       r"cheek|lip|chin|tooth|iris)", re.I)
    _off = [b for b in arm.data.bones
            if b.use_deform and (b.name.endswith("_end") or b.name.endswith(".end")
                                 or _FACE.search(b.name))]
    # A rig can also carry helper leaves that sit exactly on top of the joint
    # they name -- Elbow_L on ForeArm_L, Knee_L on Calf_L, Wrist_L on Hand_L,
    # Socks_L on Foot_L. They are not humanoid bones, so they never move, and
    # bone heat splits the limb's weights with them: the elbow then freezes.
    _dup = [b for b in arm.data.bones
            if b.use_deform and b.parent is not None and not b.children
            and (b.head_local - b.parent.head_local).length < 1e-4]
    if _dup:
        print("  excluded %d co-located helper bones from automatic weighting: %s"
              % (len(_dup), ", ".join(sorted(b.name for b in _dup)[:8])))
    for b in _off + _dup:
        b.use_deform = False
    if _off:
        print("  excluded %d tip/facial bones from automatic weighting "
              "(%d deform bones left)"
              % (len(_off), sum(1 for b in arm.data.bones if b.use_deform)))
    for o in UNRIGGED:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
            print("  auto-weighted unrigged mesh '%s' (%d verts) to the skeleton"
                  % (o.name, len(o.data.vertices)))
        except Exception as e:
            print("  could not auto-weight '%s': %s" % (o.name, e))
        # Bone heat solves a diffusion problem over the surface and gives up on
        # geometry it cannot solve -- a mesh of many separate shells, as a
        # character with loose eyes, mouth and quills is. It reports that as a
        # WARNING, returns FINISHED, and leaves every weight at zero. Nothing
        # downstream notices: the file exports, renders perfectly at rest and
        # reports a clean humanoid, and the character is a statue in game.
        # Count the weights instead of trusting the operator, and fall back to
        # straight proximity, which cannot fail on topology.
        _bound = sum(1 for v in o.data.vertices
                     if any(g.weight > 0.01 for g in v.groups))
        if _bound < len(o.data.vertices) * 0.5:
            _db = [b for b in arm.data.bones if b.use_deform]
            if _db:
                # Nearest two bone segments, sharply weighted. Occlusion
                # testing was tried twice here -- reject a bone the vertex
                # cannot see, so a hand hanging beside the shoe cannot claim it
                # -- and made the result WORSE both times (1.379 m wide against
                # a 0.490 m character), because a mesh of loose shells blocks
                # nearly every line: 1,965 vertices could see no bone at all and
                # fell back to the nearest one regardless.
                _M = arm.matrix_world.inverted() @ o.matrix_world
                _segs = [(b.name, b.head_local.copy(), b.tail_local.copy())
                         for b in _db]
                _grp = {}
                for _n, _h, _t in _segs:
                    _grp[_n] = o.vertex_groups.get(_n) or o.vertex_groups.new(name=_n)
                for _v in o.data.vertices:
                    _p = _M @ _v.co
                    _ds = []
                    for _n, _h, _t in _segs:
                        _ab = _t - _h
                        _l2 = _ab.length_squared
                        _u = 0.0 if _l2 < 1e-12 else max(0.0, min(1.0, (_p - _h).dot(_ab) / _l2))
                        _ds.append(((_h + _ab * _u - _p).length, _n))
                    _ds.sort(key=lambda x: x[0])
                    _near = _ds[:2]
                    _d0 = max(_near[0][0], 1e-6)
                    _ws = [(_n, (_d0 / max(_d, 1e-6)) ** 4) for _d, _n in _near]
                    _sw = sum(w for _, w in _ws)
                    for _n, _w in _ws:
                        _grp[_n].add([_v.index], _w / _sw, "REPLACE")
                bpy.context.view_layer.update()
                _bound = sum(1 for v in o.data.vertices
                             if any(g.weight > 0.01 for g in v.groups))
                print("  bone heat bound nothing usable on '%s'; weighted it by "
                      "proximity to %d bones instead (%d/%d verts now bound)"
                      % (o.name, len(_db), _bound, len(o.data.vertices)))
            if not any(m.type == "ARMATURE" for m in o.modifiers):
                _md = o.modifiers.new(name="Armature", type="ARMATURE")
                _md.object = arm
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.update()

# A part that is meant to be RIGID can be forced onto one bone. An auto-rigger
# weights by proximity to its own humanoid skeleton and has no idea which lumps
# of a stylised character are supposed to bend: Mixamo split Sonic's back quills
# between head, neck and chest, so they folded over themselves the moment he
# moved. The quills are one connected island of the mesh (2,139 verts, the whole
# head mass), so naming that island and the bone it belongs to fixes it exactly.
#   VRM_RIGID="island:0=Head[,island:3=Hand_L]"
# The bone is matched on the END of its name, so 'Head' finds 'mixamorig:Head'.
def _islands(o):
    adj = {}
    for e in o.data.edges:
        a, b = e.vertices
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen, out = set(), []
    for v in range(len(o.data.vertices)):
        if v in seen:
            continue
        comp, stack = [], [v]
        seen.add(v)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        out.append(comp)
    out.sort(key=len, reverse=True)
    return out


for _spec in [x for x in os.environ.get("VRM_RIGID", "").split(",") if x.strip()]:
    _sel, _, _bone = _spec.strip().partition("=")
    _hit = [b.name for b in arm.data.bones
            if b.name == _bone or b.name.endswith(":" + _bone)
            or b.name.endswith("_" + _bone)]
    if not _hit:
        raise SystemExit("ABORT: VRM_RIGID names bone %r, which this rig has not "
                         "got" % _bone)
    _bn = _hit[0]
    if _sel.startswith("mesh:"):
        # A whole mesh, by name. An auto-rigger skins a loose outer garment to
        # the arms as if it were skin, so Yoda's robe webbed between his arms
        # and his body the moment they went to a T-pose. A robe hangs off the
        # torso; say so.
        _pat = _sel.split(":", 1)[1]
        _hits = [o for o in meshes if re.search(_pat, o.name, re.I)]
        if not _hits:
            raise SystemExit("ABORT: VRM_RIGID mesh pattern /%s/ matched nothing"
                             % _pat)
        _tgt = max(_hits, key=lambda o: len(o.data.vertices))
        _vs = [v.index for v in _tgt.data.vertices]
    elif _sel.startswith("island:"):
        _k = int(_sel.split(":", 1)[1])
        _tgt = max(meshes, key=lambda o: len(o.data.vertices))
        _isl = _islands(_tgt)
        if _k >= len(_isl):
            raise SystemExit("ABORT: '%s' has only %d islands" % (_tgt.name, len(_isl)))
        _vs = _isl[_k]
    else:
        raise SystemExit("ABORT: VRM_RIGID selector %r is not 'island:N' or "
                         "'mesh:<pattern>'" % _sel)
    for _g in _tgt.vertex_groups:
        _g.remove(_vs)
    _vg = _tgt.vertex_groups.get(_bn) or _tgt.vertex_groups.new(name=_bn)
    _vg.add(_vs, 1.0, "REPLACE")
    print("  rigid: %s -> '%s' (%d verts) bound wholly to '%s'"
          % (_sel, _tgt.name, len(_vs), _bn))

# A part can also ride a bone through a CHILD_OF CONSTRAINT rather than through
# parenting. It looks identical in the viewport and is invisible to everything
# that reads parent/parent_type -- but a constraint keeps contributing to
# matrix_world after the parent has been cleared, so the scale it carries
# survives flatten() and the exporter would write it on a node. Alcina
# Dimitrescu arrives this way: her hat, hair, earrings, cigarette holder and its
# smoke all hang off 'spine.005', 'hand.L' and 'shoulder.L' by constraint, and
# Cube.042 aborted the build still carrying a world scale of 0.5383.
# Bake the constraint into the object and rebind the part as a skinned mesh.


# flatten() is only safe when the armature and the meshes it deforms share an
# object transform. Where they differ, baking each object's OWN world matrix
# into its data leaves the bones in one scale and the geometry in another, and
# the pose is then applied across that mismatch. Alcina Dimitrescu's armature
# carries a 1.8577 object scale -- that is how a 2.9 m woman is built from a
# normal body -- while her meshes sit at 1.0, and her head and torso came out
# compressed to 59% with her hat and hair left floating above them.
# Put the meshes into the armature's space first. The world appearance does not
# change (A @ (A-1 @ M) == M), and on a file where they already agree this does
# nothing at all.
_A = arm.matrix_world.copy()
_Ai = _A.inverted()
_realigned = []
for _o in ([] if os.environ.get("VRM_NO_REALIGN") else meshes):
    if not any(m.type == "ARMATURE" and m.object is arm for m in _o.modifiers):
        continue
    _D = _Ai @ _o.matrix_world
    if max(abs(_D[i][j] - (1.0 if i == j else 0.0))
           for i in range(4) for j in range(4)) < 1e-6:
        continue
    if _o.data.users > 1:
        _o.data = _o.data.copy()
    _o.data.transform(_D)
    if _D.determinant() < 0:
        _o.data.flip_normals()
    _o.data.update()
    _o.parent = None
    _o.matrix_parent_inverse.identity()
    _o.matrix_world = _A
    _realigned.append(_o.name)
if _realigned:
    bpy.context.view_layer.update()
    print("  put %d deformed mesh(es) into the armature's own space: %s"
          % (len(_realigned), _realigned[:6]))

trace("after realign")

# A hand posed around a prop that is no longer there.
#
# Alcina Dimitrescu holds a cigarette holder. The holder is excluded from the
# build (^NurbsPath) because it skewers her hand, but her LEFT fingers stay
# clamped around the hole where it was, and Jay reported them as mangled.
#
# The model supplies its own control, which is what makes this safe to automate:
# her RIGHT hand's pose is identical to rest on all five finger chains, to 0.0
# degrees, while her left thumb is 125.7 degrees further curled than rest and her
# middle finger 112.9. So the rest pose IS the modeller's neutral hand, and the
# left hand is the odd one out. Relaxing it to rest reproduces the hand the model
# already has on the other side rather than inventing one.
#
# Fire only on that asymmetry: one hand at rest, the other far from it. A
# character posed with BOTH hands gripping shows no asymmetry and is left alone,
# which is the case this must not break -- YARG puts a microphone in the hand and
# a deliberate two-handed grip is a real thing to ship. Only finger bones are
# touched; the blanket reset-to-rest is what destroyed Alcina's 9'6" proportions
# once already, and this is not that.
_FINGER_W = ("thumb", "index", "middle", "ring", "pinky", "little", "finger")
_FING_BONES = [b for b in arm.data.bones
               if any(w in b.name.lower() for w in _FINGER_W)]


def _hand_side(n):
    l = n.lower()
    if l.endswith(".l") or l.endswith("_l") or "_l_" in l or "left" in l:
        return "L"
    if l.endswith(".r") or l.endswith("_r") or "_r_" in l or "right" in l:
        return "R"
    return "?"


def _finger_chains():
    """Each finger as a bone list, root first."""
    out = []
    for b in _FING_BONES:
        if b.parent is not None and any(w in b.parent.name.lower()
                                        for w in _FINGER_W):
            continue
        ch, cur = [b.name], b
        while True:
            kids = [c for c in cur.children
                    if any(w in c.name.lower() for w in _FINGER_W)]
            if not kids:
                break
            kids.sort(key=lambda x: -x.length)
            ch.append(kids[0].name)
            cur = kids[0]
        if len(ch) >= 2:
            out.append(ch)
    return out


def _curl(chain, pose):
    """Total bend down a finger, summed over its joints.

    Measure the SHAPE of the hand, never the direction its bones point. A
    direction test also sees the whole arm's rotation: Alcina's right hand came
    out 65.9 degrees "off rest" purely because her static pose lifts that arm,
    and the asymmetry this check needs vanished. Curl is the angle between
    CONSECUTIVE bones, so rotating the whole hand does not change it.
    """
    ds = []
    for n in chain:
        if pose:
            pb = arm.pose.bones[n]
            v = pb.tail - pb.head
        else:
            db = arm.data.bones[n]
            v = db.tail_local - db.head_local
        ds.append(v.normalized() if v.length > 1e-9 else Vector((0.0, 0.0, 0.0)))
    tot = 0.0
    for p, q in zip(ds, ds[1:]):
        if p.length > 0 and q.length > 0:
            tot += math.degrees(math.acos(max(-1.0, min(1.0, p.dot(q)))))
    return tot


_FING_CHAINS = _finger_chains()


def _finger_offset(side):
    """Mean |pose curl - rest curl| over that hand's fingers."""
    vals = [abs(_curl(c, True) - _curl(c, False))
            for c in _FING_CHAINS if _hand_side(c[0]) == side]
    return (sum(vals) / len(vals), len(vals)) if vals else (0.0, 0)


if _FING_BONES and not os.environ.get("VRM_KEEP_GRIP"):
    _lo, _ln = _finger_offset("L")
    _ro, _rn = _finger_offset("R")
    if _ln and _rn:
        print("  fingers: left hand curls %.1f deg away from rest (%d chains), "
              "right hand %.1f deg (%d chains)" % (_lo, _ln, _ro, _rn))
        for _s, _mine, _other in (("L", _lo, _ro), ("R", _ro, _lo)):
            if _mine >= 20.0 and _other < 5.0:
                _n = 0
                for _b in _FING_BONES:
                    if _hand_side(_b.name) == _s:
                        arm.pose.bones[_b.name].matrix_basis.identity()
                        _n += 1
                bpy.context.view_layer.update()
                print("  fingers: relaxed the %s hand's %d finger bones to rest "
                      "-- it is posed %.1f deg off rest while the other hand sits "
                      "AT rest, so it is gripping a prop this build has removed "
                      "(VRM_KEEP_GRIP=1 keeps it)" % (_s, _n, _mine))

# A rest pose that is NOT the bind pose is a trap for the scale step that
# follows. A USD import can leave a leaf bone at the origin in the rest pose and
# place it with a pose LOCATION instead: Harley Quinn's USDZ did that on 13 of
# her 65 bones, with offsets as large as 1.9. A pose location is expressed
# relative to the bone's rest length, so scaling the rest changes what it means
# -- she measured 7.26 m wide the moment the character was scaled, while the
# source scene was perfectly fine. Move the geometry with the bones and make the
# pose the rest, so there is nothing left to re-interpret.
bake_pose_to_rest("")

trace("after pose bake")

# Re-measure here, not earlier: binding an unrigged mesh or converting a
# bone-parented one can change the evaluated bounds, and a stale measurement
# makes the scale miss (Judy came out 1.203 m against a 1.05 m target).
lo, hi = bounds()
size = hi - lo
k = HEIGHT / size.z
pre = (Matrix.Translation((-(lo.x + hi.x) / 2.0 * k, -(lo.y + hi.y) / 2.0 * k, -lo.z * k))
       @ Matrix.Diagonal((k, k, k, 1.0)))
flatten(pre)
lo, hi = bounds()
size = hi - lo
# Converge, do not assume. One computed scale lands on most files and misses on
# some -- Gadget Hackwrench came out 1.2656 m against a 1.30 m target, 2.6%
# short, which the data-height assert (rightly) refuses to ship. Measure what
# actually happened and apply the remainder, the same way the T-pose correction
# does.
for _ in range(4):
    if abs(size.z - HEIGHT) / HEIGHT <= 0.002 or size.z <= 1e-9:
        break
    _k2 = HEIGHT / size.z
    flatten(Matrix.Translation((0.0, 0.0, -lo.z * _k2))
            @ Matrix.Diagonal((_k2, _k2, _k2, 1.0)))
    lo, hi = bounds()
    size = hi - lo
    k *= _k2
    print("  rescaled x%.4f -> height %.4f m" % (_k2, size.z))
print("scaled x%.4f -> height %.4f m, feet z=%.4f" % (k, size.z, lo.z))
trace("after scale")


def raw_extent():
    """Extent of the undeformed mesh DATA. This is what the exporter writes; the
    evaluated bounds can disagree if any scale is still sitting in an object
    transform or in the armature's bind pose."""
    rlo = Vector((1e18,) * 3)
    rhi = Vector((-1e18,) * 3)
    for o in meshes:
        for v in o.data.vertices:
            for i in range(3):
                rlo[i] = min(rlo[i], v.co[i])
                rhi[i] = max(rhi[i], v.co[i])
    return rlo, rhi


# The check that matters. The scene measuring correctly proves nothing: both
# Prix and Pomni measured 1.70 m in Blender and shipped broken. Compare the
# DATA, and refuse to write a file that would be wrong in engine.
rlo, rhi = raw_extent()
raw = rhi - rlo
print("VERIFIED scene height %.4f m (feet z=%.4f, width %.4f m); "
      "mesh DATA height %.4f m" % (size.z, lo.z, size.x, raw.z))
if abs(raw.z - HEIGHT) / HEIGHT > 0.01 or os.environ.get("VRM_DEBUG"):
    # Per-object report: which object disagrees, and what is left on it.
    _deps = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        zs = [v.co.z for v in o.data.vertices]
        ev = o.evaluated_get(_deps)
        ez = [(ev.matrix_world @ Vector(c)).z for c in ev.bound_box]
        print("  DBG %-22s data=%.4f eval=%.4f basis_scale=%s world_scale=%s "
              "delta_scale=%s mods=%s"
              % (o.name[:22], (max(zs) - min(zs)) if zs else 0.0, max(ez) - min(ez),
                 tuple(round(v, 4) for v in o.matrix_basis.to_scale()),
                 tuple(round(v, 4) for v in o.matrix_world.to_scale()),
                 tuple(round(v, 4) for v in o.delta_scale),
                 [m.type for m in o.modifiers]))
    _pb = arm.pose.bones[0]
    print("  DBG armature world_scale=%s  bone[0]=%s rest_len=%.4f  pose==rest: %s"
          % (tuple(round(v, 4) for v in arm.matrix_world.to_scale()), _pb.name,
             arm.data.bones[0].length,
             all(max(abs(a - b) for a, b in zip(sum((list(r) for r in pb.matrix), []),
                 sum((list(r) for r in pb.bone.matrix_local), []))) < 1e-4
                 for pb in arm.pose.bones)))

if abs(raw.z - HEIGHT) / HEIGHT > 0.01:
    raise SystemExit("ABORT: mesh DATA measures %.4f m but the target is %.4f m. "
                     "A scale is still hiding in an object transform; the model "
                     "would render at the DATA size in engine." % (raw.z, HEIGHT))
if abs(size.z - HEIGHT) / HEIGHT > 0.01:
    # The DATA check above is the one that decides, because the data is what the
    # exporter writes. The evaluated scene can legitimately differ where meshes
    # carry Subdivision or Solidify, so say so rather than refusing to build.
    print("  NOTE: the evaluated scene measures %.4f m against a %.4f m target, "
          "while the mesh data is correct - modifiers account for the difference"
          % (size.z, HEIGHT))
if abs(lo.z) > 0.10:
    raise SystemExit("ABORT: feet not on the floor (z=%.4f)" % lo.z)
elif abs(lo.z) > 0.02:
    # A small offset here is usually a modifier widening the evaluated bounds;
    # the foot-weighted re-seat below is what actually places the character.
    print("  NOTE: lowest point is %.4f m off the floor before re-seating" % lo.z)
if size.x < HEIGHT * 0.15:
    raise SystemExit("ABORT: implausibly narrow (%.4f m wide for %.4f m tall) - "
                     "the scale was applied non-uniformly" % (size.x, size.z))
# Check matrix_WORLD, not matrix_basis: the basis excludes delta transforms and
# the parent chain, so a basis-only check passes while the exported node still
# carries a scale.
for o in meshes + [arm]:
    _s = o.matrix_world.to_scale()
    if max(abs(v - 1.0) for v in _s) > 1e-4:
        raise SystemExit("ABORT: '%s' still carries a world scale of %s; the "
                         "exporter would write that scale into its node" % (
                             o.name, tuple(round(v, 5) for v in _s)))
    if o.matrix_world.determinant() < 0:
        raise SystemExit("ABORT: '%s' is mirrored; VRM 1.0 rejects a negative "
                         "scale and the export would cancel" % o.name)



if RIG == "mixamo":
    n = 0
    for b in arm.data.bones:
        if b.name.startswith("mixamorig:"):
            b.name = b.name[len("mixamorig:"):]; n += 1
    print("stripped mixamorig: from", n, "bones")
    # Some rips also number every bone: 'mixamorig:Hips_02', 'Spine_03',
    # 'LeftForeArm_011'. The Fortnite Mandalorian is one, and it carries a
    # SECOND, Unreal-named skeleton beside the Mixamo one, so a blind strip of
    # every trailing _NNN would collide names across the two. Rename only where
    # stripping the suffix produces a name Mixamo is expected to have, and only
    # where that name is still free -- so this cannot invent a mapping that was
    # not already there, and does nothing at all on a normal Mixamo rig.
    _EXPECT = {"Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"}
    for _S in ("Left", "Right"):
        _EXPECT |= {_S + x for x in ("Shoulder", "Arm", "ForeArm", "Hand",
                                     "UpLeg", "Leg", "Foot", "ToeBase")}
        for _f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
            _EXPECT |= {"%sHand%s%d" % (_S, _f, _i) for _i in (1, 2, 3)}
    if "Hips" not in {b.name for b in arm.data.bones}:
        _taken = {b.name for b in arm.data.bones}
        _renamed = 0
        for b in arm.data.bones:
            _base = re.sub(r"_\d+$", "", b.name)
            if _base != b.name and _base in _EXPECT and _base not in _taken:
                _taken.discard(b.name)
                b.name = _base
                _taken.add(_base)
                _renamed += 1
        if _renamed:
            print("stripped a numeric suffix from %d Mixamo bone(s)" % _renamed)

bone_names = {b.name for b in arm.data.bones}

# ---------------------------------------------------------------- bone maps
MAP = {}
if RIG == "mixamo":
    # The Mixamo bone NAMES are sometimes shipped under a different prefix
    # ('FemaleBody_Hips' rather than 'mixamorig:Hips'). Detect it from the root
    # rather than requiring a separate rig type per exporter.
    PRE = ""
    if "Hips" not in bone_names:
        for b in arm.data.bones:
            if b.parent is None and b.name.endswith("Hips"):
                PRE = b.name[:-len("Hips")]
                break
    if PRE:
        print("detected Mixamo bone prefix: '%s'" % PRE)
    MAP = {"hips": PRE + "Hips", "spine": PRE + "Spine", "chest": PRE + "Spine1",
           "upper_chest": PRE + "Spine2", "neck": PRE + "Neck", "head": PRE + "Head"}
    for s, S in (("left", "Left"), ("right", "Right")):
        MAP["%s_shoulder" % s] = PRE + "%sShoulder" % S
        MAP["%s_upper_arm" % s] = PRE + "%sArm" % S
        MAP["%s_lower_arm" % s] = PRE + "%sForeArm" % S
        MAP["%s_hand" % s] = PRE + "%sHand" % S
        MAP["%s_thumb_metacarpal" % s] = PRE + "%sHandThumb1" % S
        MAP["%s_thumb_proximal" % s] = PRE + "%sHandThumb2" % S
        MAP["%s_thumb_distal" % s] = PRE + "%sHandThumb3" % S
        for vf, mf in (("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = PRE + "%sHand%s1" % (S, mf)
            MAP["%s_%s_intermediate" % (s, vf)] = PRE + "%sHand%s2" % (S, mf)
            MAP["%s_%s_distal" % (s, vf)] = PRE + "%sHand%s3" % (S, mf)
        MAP["%s_upper_leg" % s] = PRE + "%sUpLeg" % S
        MAP["%s_lower_leg" % s] = PRE + "%sLeg" % S
        MAP["%s_foot" % s] = PRE + "%sFoot" % S
        MAP["%s_toes" % s] = PRE + "%sToeBase" % S
elif RIG == "reallusion":
    MAP = {"hips": "hip", "spine": "spineA", "chest": "spineC", "upper_chest": "spineE",
           "neck": "neckA", "head": "head"}
    for s, p in (("left", "l"), ("right", "r")):
        MAP["%s_upper_arm" % s] = "%s_shoulder" % p
        MAP["%s_lower_arm" % s] = "%s_elbow" % p
        MAP["%s_hand" % s] = "%s_wrist" % p
        MAP["%s_thumb_metacarpal" % s] = "%s_finThumbA" % p
        MAP["%s_thumb_proximal" % s] = "%s_finThumbB" % p
        MAP["%s_thumb_distal" % s] = "%s_finThumbC" % p
        for vf, rf in (("index", "Index"), ("middle", "Mid"), ("ring", "Ring"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s_fin%sA" % (p, rf)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s_fin%sB" % (p, rf)
            MAP["%s_%s_distal" % (s, vf)] = "%s_fin%sC" % (p, rf)
        MAP["%s_upper_leg" % s] = "%s_thigh" % p
        MAP["%s_lower_leg" % s] = "%s_knee" % p
        MAP["%s_foot" % s] = "%s_ankle" % p
        MAP["%s_toes" % s] = "%s_ball" % p
elif RIG == "rigify":
    # Blender Rigify/metarig deform naming. 'spine' is the hips: it parents both
    # the spine chain and the thighs. The shoulders hang off spine.003, which is
    # therefore the upper chest. spine.005 is the neck adjacent to the head.
    MAP = {"hips": "spine", "spine": "spine.001", "chest": "spine.002",
           "upper_chest": "spine.003", "neck": "spine.005", "head": "spine.006"}
    for s, S in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s] = "shoulder.%s" % S
        MAP["%s_upper_arm" % s] = "upper_arm.%s" % S
        MAP["%s_lower_arm" % s] = "forearm.%s" % S
        MAP["%s_hand" % s] = "hand.%s" % S
        MAP["%s_thumb_metacarpal" % s] = "thumb.01.%s" % S
        MAP["%s_thumb_proximal" % s] = "thumb.02.%s" % S
        MAP["%s_thumb_distal" % s] = "thumb.03.%s" % S
        for vf, rf in (("index", "f_index"), ("middle", "f_middle"),
                       ("ring", "f_ring"), ("little", "f_pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s.01.%s" % (rf, S)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s.02.%s" % (rf, S)
            MAP["%s_%s_distal" % (s, vf)] = "%s.03.%s" % (rf, S)
        MAP["%s_upper_leg" % s] = "thigh.%s" % S
        MAP["%s_lower_leg" % s] = "shin.%s" % S
        MAP["%s_foot" % s] = "foot.%s" % S
        MAP["%s_toes" % s] = "toe.%s" % S
elif RIG == "bip":
    # Source/Valve-style 'bip_' rig. The collars hang off spine_4, so that is the
    # upper chest; the neck chain is neck1->neck2->neck, and 'bip_neck' is the one
    # adjacent to the head.
    MAP = {"hips": "bip_pelvis", "spine": "bip_spine_0", "chest": "bip_spine_2",
           "upper_chest": "bip_spine_4", "neck": "bip_neck", "head": "bip_head"}
    for s, S in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s] = "bip_collar_%s" % S
        MAP["%s_upper_arm" % s] = "bip_upperArm_%s" % S
        MAP["%s_lower_arm" % s] = "bip_lowerArm_%s" % S
        MAP["%s_hand" % s] = "bip_hand_%s" % S
        MAP["%s_thumb_metacarpal" % s] = "bip_thumb_0_%s" % S
        MAP["%s_thumb_proximal" % s] = "bip_thumb_1_%s" % S
        MAP["%s_thumb_distal" % s] = "bip_thumb_2_%s" % S
        for vf, bf in (("index", "index"), ("middle", "middle"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "bip_%s_0_%s" % (bf, S)
            MAP["%s_%s_intermediate" % (s, vf)] = "bip_%s_1_%s" % (bf, S)
            MAP["%s_%s_distal" % (s, vf)] = "bip_%s_2_%s" % (bf, S)
        MAP["%s_upper_leg" % s] = "bip_hip_%s" % S
        MAP["%s_lower_leg" % s] = "bip_knee_%s" % S
        MAP["%s_foot" % s] = "bip_foot_%s" % S
        MAP["%s_toes" % s] = "bip_toe_%s" % S
elif RIG == "xeno":
    # Maya 'XenosBiped_*SHJnt' rig. Note the hand has only a thumb and THREE
    # fingers, so the outermost is mapped to VRM's 'little' slot rather than
    # 'ring' — YARG reads rightLittleProximal/Distal to place the microphone,
    # and leaving those empty loses the mic entirely.
    P = "XenosBiped_"
    # upper_chest MUST be Spine_03: the clavicles are its children, not
    # Spine_Top's. Get this wrong and the exporter decides the humanoid chain is
    # broken, runs its own structure search, and maps the arms to the back tubes.
    MAP = {"hips": P + "ROOTSHJnt", "spine": P + "Spine_01SHJnt",
           "chest": P + "Spine_02SHJnt", "upper_chest": P + "Spine_03SHJnt",
           "neck": P + "Neck_TopSHJnt", "head": P + "Head_TopSHJnt"}
    for s, p in (("left", "l"), ("right", "r")):
        MAP["%s_shoulder" % s] = "%s%s_Arm_ClavicleSHJnt" % (P, p)
        MAP["%s_upper_arm" % s] = "%s%s_Arm_ShoulderSHJnt" % (P, p)
        MAP["%s_lower_arm" % s] = "%s%s_Arm_Elbow_CurveSHJnt" % (P, p)
        MAP["%s_hand" % s] = "%s%s_Arm_WristSHJnt" % (P, p)
        MAP["%s_thumb_metacarpal" % s] = "%s%s_Thumb_01_01SHJnt" % (P, p)
        MAP["%s_thumb_proximal" % s] = "%s%s_Thumb_01_02SHJnt" % (P, p)
        MAP["%s_thumb_distal" % s] = "%s%s_Thumb_01_03SHJnt" % (P, p)
        for vf, n in (("index", "01"), ("middle", "02"), ("little", "03")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s%s_Finger_%s_01SHJnt" % (P, p, n)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s%s_Finger_%s_02SHJnt" % (P, p, n)
            MAP["%s_%s_distal" % (s, vf)] = "%s%s_Finger_%s_03SHJnt" % (P, p, n)
        MAP["%s_upper_leg" % s] = "%s%s_Leg_HipSHJnt" % (P, p)
        MAP["%s_lower_leg" % s] = "%s%s_Leg_Knee1SHJnt" % (P, p)
        MAP["%s_foot" % s] = "%s%s_Leg_AnkleSHJnt" % (P, p)
        MAP["%s_toes" % s] = "%s%s_Toe00_Base_SHJnt" % (P, p)
elif RIG == "rigify_def":
    # Rigify deform bones. This rig has only two spine bones, so chest and
    # upperChest are left unmapped — both are optional in VRM.
    MAP = {"hips": "DEF-spine", "spine": "DEF-spine.001",
           "neck": ("DEF-neck" if "DEF-neck" in bone_names else "DEF-spine.004"),
           "head": ("DEF-head" if "DEF-head" in bone_names else "DEF-spine.005")}
    for s, S in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s] = "DEF-shoulder.%s" % S
        MAP["%s_upper_arm" % s] = "DEF-upper_arm.%s" % S
        MAP["%s_lower_arm" % s] = "DEF-forearm.%s" % S
        MAP["%s_hand" % s] = "DEF-hand.%s" % S
        MAP["%s_thumb_metacarpal" % s] = "DEF-thumb.01.%s" % S
        MAP["%s_thumb_proximal" % s] = "DEF-thumb.02.%s" % S
        MAP["%s_thumb_distal" % s] = "DEF-thumb.03.%s" % S
        for vf, rf in (("index", "f_index"), ("middle", "f_middle"),
                       ("ring", "f_ring"), ("little", "f_pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "DEF-%s.01.%s" % (rf, S)
            MAP["%s_%s_intermediate" % (s, vf)] = "DEF-%s.02.%s" % (rf, S)
            MAP["%s_%s_distal" % (s, vf)] = "DEF-%s.03.%s" % (rf, S)
        MAP["%s_upper_leg" % s] = "DEF-thigh.%s" % S
        MAP["%s_lower_leg" % s] = "DEF-shin.%s" % S
        MAP["%s_foot" % s] = "DEF-foot.%s" % S
        MAP["%s_toes" % s] = "DEF-toe.%s" % S
elif RIG == "daz":
    # DAZ Genesis. The *Bend bones carry the joint; the *Twist bones are helpers.
    MAP = {"hips": "hip", "spine": "abdomenLower", "chest": "abdomenUpper",
           "upper_chest": "chestUpper", "neck": "neckUpper", "head": "head"}
    for s, p in (("left", "l"), ("right", "r")):
        MAP["%s_shoulder" % s] = "%sCollar" % p
        MAP["%s_upper_arm" % s] = "%sShldrBend" % p
        MAP["%s_lower_arm" % s] = "%sForearmBend" % p
        MAP["%s_hand" % s] = "%sHand" % p
        MAP["%s_thumb_metacarpal" % s] = "%sThumb1" % p
        MAP["%s_thumb_proximal" % s] = "%sThumb2" % p
        MAP["%s_thumb_distal" % s] = "%sThumb3" % p
        for vf, df in (("index", "Index"), ("middle", "Mid"),
                       ("ring", "Ring"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s%s1" % (p, df)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s%s2" % (p, df)
            MAP["%s_%s_distal" % (s, vf)] = "%s%s3" % (p, df)
        MAP["%s_upper_leg" % s] = "%sThighBend" % p
        MAP["%s_lower_leg" % s] = "%sShin" % p
        MAP["%s_foot" % s] = "%sFoot" % p
        MAP["%s_toes" % s] = "%sToe" % p
elif RIG == "pomni":
    # Hand-built cartoon rig. Two notes: the hand has FOUR fingers (no ring), and
    # the thumb has only two joints, so the thumb is mapped proximal+distal and
    # the metacarpal slot is left empty — rightThumbDistal is what YARG reads.
    for b in arm.data.bones:
        if "-" in b.name and b.name[-2] == "-":
            fixed = b.name[:-2] + "." + b.name[-1]
            print("  renaming typo'd bone '%s' -> '%s'" % (b.name, fixed))
            b.name = fixed
    # VRM wants a complete three-bone thumb. This rig has only two joints, and an
    # incomplete chain makes the exporter cancel, so extend it with a short tip
    # bone continuing the last joint's direction.
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for S in ("L", "R"):
        src, tip = "Thumb2.%s" % S, "Thumb3.%s" % S
        if src in arm.data.edit_bones and tip not in arm.data.edit_bones:
            pb = arm.data.edit_bones[src]
            nb = arm.data.edit_bones.new(tip)
            d = pb.tail - pb.head
            nb.head = pb.tail
            nb.tail = pb.tail + (d * 0.6 if d.length > 1e-6 else Vector((0.0, 0.0, 0.01)))
            nb.parent = pb
            nb.use_connect = True
            print("  added missing thumb tip bone '%s'" % tip)
    bpy.ops.object.mode_set(mode="OBJECT")

    bone_names = {b.name for b in arm.data.bones}
    MAP = {"hips": "Spine", "spine": "Spine2", "chest": "Spine3",
           "upper_chest": "Chest", "neck": "Neck", "head": "Head"}
    for s, S in (("left", "L"), ("right", "R")):
        MAP["%s_upper_arm" % s] = "Arm.%s" % S
        MAP["%s_lower_arm" % s] = "Forearm.%s" % S
        MAP["%s_hand" % s] = "Hand.%s" % S
        MAP["%s_thumb_metacarpal" % s] = "Thumb.%s" % S
        MAP["%s_thumb_proximal" % s] = "Thumb2.%s" % S
        MAP["%s_thumb_distal" % s] = "Thumb3.%s" % S
        for vf, pf in (("index", "Index"), ("middle", "Middle"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s.%s" % (pf, S)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s2.%s" % (pf, S)
            MAP["%s_%s_distal" % (s, vf)] = "%s3.%s" % (pf, S)
        MAP["%s_upper_leg" % s] = "Leg.%s" % S
        MAP["%s_lower_leg" % s] = "Knee.%s" % S
        MAP["%s_foot" % s] = "Foot1.%s" % S
        MAP["%s_toes" % s] = "Foot2.%s" % S
elif RIG == "rp":
    # Renderpeople scan: UE4-style names carrying the scan's own prefix
    # ('rp_sophia_animated_003_idling_upperarm_l'). Read the prefix off the root
    # rather than hard-coding one scan's name.
    PRE = ""
    for b in arm.data.bones:
        if b.parent is None and b.name.endswith("root"):
            PRE = b.name[:-len("root")]
            break
    print("detected Renderpeople prefix: '%s'" % PRE)
    MAP = {"hips": PRE + "hip", "spine": PRE + "spine_01", "chest": PRE + "spine_02",
           "upper_chest": PRE + "spine_03", "neck": PRE + "neck", "head": PRE + "head"}
    for s, p in (("left", "l"), ("right", "r")):
        MAP["%s_shoulder" % s] = "%sshoulder_%s" % (PRE, p)
        MAP["%s_upper_arm" % s] = "%supperarm_%s" % (PRE, p)
        MAP["%s_lower_arm" % s] = "%slowerarm_%s" % (PRE, p)
        MAP["%s_hand" % s] = "%shand_%s" % (PRE, p)
        MAP["%s_thumb_metacarpal" % s] = "%sthumb_01_%s" % (PRE, p)
        MAP["%s_thumb_proximal" % s] = "%sthumb_02_%s" % (PRE, p)
        MAP["%s_thumb_distal" % s] = "%sthumb_03_%s" % (PRE, p)
        for vf, rf in (("index", "index"), ("middle", "middle"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s%s_01_%s" % (PRE, rf, p)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s%s_02_%s" % (PRE, rf, p)
            MAP["%s_%s_distal" % (s, vf)] = "%s%s_03_%s" % (PRE, rf, p)
        MAP["%s_upper_leg" % s] = "%supperleg_%s" % (PRE, p)
        MAP["%s_lower_leg" % s] = "%slowerleg_%s" % (PRE, p)
        MAP["%s_foot" % s] = "%sfoot_%s" % (PRE, p)
        MAP["%s_toes" % s] = "%sball_%s" % (PRE, p)
elif RIG == "steve":
    # A hand-built blocky rig whose bones are called 'Bone', 'Bone.001' ... and
    # carry no information at all, so the map is read off the hierarchy instead:
    # one chain up the middle (hips, spine, head), two hanging off the chest
    # (arms) and two off the hips (legs). Sides by X, with +X the character's
    # LEFT. The '_end' leaves the FBX importer adds serve as hand and foot,
    # which VRM requires and this rig has no other bone for.
    MAP = {"hips": "Bone", "spine": "Bone.001", "head": "Bone.010"}
    for s_, ua, la, ha in (("left", "Bone.002", "Bone.005", "Bone.005_end"),
                           ("right", "Bone.003", "Bone.004", "Bone.004_end")):
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = ha
    for s_, ul, ll, ft in (("left", "Bone.008", "Bone.009", "Bone.009_end"),
                           ("right", "Bone.006", "Bone.007", "Bone.007_end")):
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
elif RIG == "ue4":
    # Unreal Engine mannequin skeleton: the same family as the Renderpeople
    # naming but with its own words - pelvis not hip, clavicle not shoulder,
    # thigh/calf not upperleg/lowerleg - and no prefix.
    MAP = {"hips": "pelvis", "spine": "spine_01", "chest": "spine_02",
           "upper_chest": "spine_03", "neck": "neck_01", "head": "head"}
    for s_, p_ in (("left", "l"), ("right", "r")):
        MAP["%s_shoulder" % s_] = "clavicle_%s" % p_
        MAP["%s_upper_arm" % s_] = "upperarm_%s" % p_
        MAP["%s_lower_arm" % s_] = "lowerarm_%s" % p_
        MAP["%s_hand" % s_] = "hand_%s" % p_
        MAP["%s_thumb_metacarpal" % s_] = "thumb_01_%s" % p_
        MAP["%s_thumb_proximal" % s_] = "thumb_02_%s" % p_
        MAP["%s_thumb_distal" % s_] = "thumb_03_%s" % p_
        for vf, uf in (("index", "index"), ("middle", "middle"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%s_01_%s" % (uf, p_)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%s_02_%s" % (uf, p_)
            MAP["%s_%s_distal" % (s_, vf)] = "%s_03_%s" % (uf, p_)
        MAP["%s_upper_leg" % s_] = "thigh_%s" % p_
        MAP["%s_lower_leg" % s_] = "calf_%s" % p_
        MAP["%s_foot" % s_] = "foot_%s" % p_
        MAP["%s_toes" % s_] = "ball_%s" % p_
elif RIG == "multiversus":
    # MultiVersus rig: 'fml_un_<side>_<part>'. The hand is 'wrist' and each
    # finger runs base/mid/tip under its own metacarpal ('hand_index').
    F = "fml_un_"
    # Hips must be the common ancestor of BOTH the spine and the legs. Here the
    # legs hang off 'C_pelvis_att' alongside 'C_pelvis', not under it, so using
    # 'C_pelvis' leaves the legs outside the hips chain and the export cancels.
    MAP = {"hips": F + "C_pelvis_att", "spine": F + "C_spine_a",
           "chest": F + "C_spine_b", "upper_chest": F + "C_spine_c",
           "neck": F + "C_neck_a", "head": F + "C_head"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        q = F + p_ + "_"
        MAP["%s_shoulder" % s_] = q + "clav"
        MAP["%s_upper_arm" % s_] = q + "uparm"
        MAP["%s_lower_arm" % s_] = q + "loarm"
        MAP["%s_hand" % s_] = q + "wrist"
        MAP["%s_thumb_metacarpal" % s_] = q + "hand_thumb"
        MAP["%s_thumb_proximal" % s_] = q + "thumb_base"
        MAP["%s_thumb_distal" % s_] = q + "thumb_mid"
        for vf, mf in (("index", "index"), ("middle", "middle"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%s%s_base" % (q, mf)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%s%s_mid" % (q, mf)
            MAP["%s_%s_distal" % (s_, vf)] = "%s%s_tip" % (q, mf)
        MAP["%s_upper_leg" % s_] = q + "upleg"
        MAP["%s_lower_leg" % s_] = q + "loleg"
        MAP["%s_foot" % s_] = q + "foot"
        MAP["%s_toes" % s_] = q + "ball"
elif RIG == "valvebiped":
    # Source engine / Half-Life: 'ValveBiped.Bip01_L_UpperArm'. Fingers run
    # Finger0 (thumb) .. Finger4 (pinky), each with two numbered joints after it.
    V = "ValveBiped.Bip01_"
    MAP = {"hips": V + "Pelvis", "spine": V + "Spine", "chest": V + "Spine1",
           "upper_chest": V + "Spine2", "neck": V + "Neck1", "head": V + "Head1"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        q = "%s%s_" % (V, p_)
        MAP["%s_shoulder" % s_] = q + "Clavicle"
        MAP["%s_upper_arm" % s_] = q + "UpperArm"
        MAP["%s_lower_arm" % s_] = q + "Forearm"
        MAP["%s_hand" % s_] = q + "Hand"
        for vf, d in (("thumb", 0), ("index", 1), ("middle", 2),
                      ("ring", 3), ("little", 4)):
            a_, b_, c_ = ("%sFinger%d" % (q, d), "%sFinger%d1" % (q, d),
                          "%sFinger%d2" % (q, d))
            if vf == "thumb":
                MAP["%s_thumb_metacarpal" % s_] = a_
                MAP["%s_thumb_proximal" % s_] = b_
                MAP["%s_thumb_distal" % s_] = c_
            else:
                MAP["%s_%s_proximal" % (s_, vf)] = a_
                MAP["%s_%s_intermediate" % (s_, vf)] = b_
                MAP["%s_%s_distal" % (s_, vf)] = c_
        MAP["%s_upper_leg" % s_] = q + "Thigh"
        MAP["%s_lower_leg" % s_] = q + "Calf"
        MAP["%s_foot" % s_] = q + "Foot"
        MAP["%s_toes" % s_] = q + "Toe0"
elif RIG == "maxbiped":
    # 3ds Max Biped, where the parts are SPACE separated and the prefix is the
    # root's own name ('Bip001 L UpperArm', 'Bip01 L UpperArm'). Read it off the
    # root rather than hard-coding, because both spellings are in the wild.
    B = next((b.name for b in arm.data.bones
              if b.parent is None and re.match(r"^Bip\d+$", b.name)), "Bip001")
    print("detected Max Biped prefix: '%s'" % B)
    MAP = {"hips": B + " Pelvis", "spine": B + " Spine", "chest": B + " Spine1",
           "neck": B + " Neck", "head": B + " Head"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        q = "%s %s " % (B, p_)
        MAP["%s_shoulder" % s_] = q + "Clavicle"
        MAP["%s_upper_arm" % s_] = q + "UpperArm"
        MAP["%s_lower_arm" % s_] = q + "Forearm"
        MAP["%s_hand" % s_] = q + "Hand"
        for vf, d in (("thumb", 0), ("index", 1), ("middle", 2),
                      ("ring", 3), ("little", 4)):
            a_, b_, c_ = ("%sFinger%d" % (q, d), "%sFinger%d1" % (q, d),
                          "%sFinger%d2" % (q, d))
            if vf == "thumb":
                MAP["%s_thumb_metacarpal" % s_] = a_
                MAP["%s_thumb_proximal" % s_] = b_
                MAP["%s_thumb_distal" % s_] = c_
            else:
                MAP["%s_%s_proximal" % (s_, vf)] = a_
                MAP["%s_%s_intermediate" % (s_, vf)] = b_
                MAP["%s_%s_distal" % (s_, vf)] = c_
        MAP["%s_upper_leg" % s_] = q + "Thigh"
        MAP["%s_lower_leg" % s_] = q + "Calf"
        MAP["%s_foot" % s_] = q + "Foot"
        MAP["%s_toes" % s_] = q + "Toe0"
elif RIG == "anakin":
    # Another meaningless 'Bone.0NN' rig, read off the hierarchy and the rest
    # geometry exactly as 'steve' was. 85 bones, three roots, and a full set of
    # fingers. Sides by X, with +X the character's LEFT; the feet point -Y, which
    # is what fixes that convention here.
    #
    # Two shapes in it that VRM will reject until the hierarchy repair runs:
    # both hands hang off 'Bone.057', a two-hand control bone under the chest
    # rather than off their own forearms, and the toes are their own ROOTS
    # instead of children of the feet.
    #
    # Each finger has four bones where VRM wants three: the first is a
    # metacarpal, which VRM only has a slot for on the thumb, so fingers map
    # from the second bone on. The thumb keeps its metacarpal and skips its
    # intermediate instead, since VRM gives the thumb no intermediate slot.
    MAP = {"hips": "Bone", "spine": "Bone.001", "chest": "Bone.002",
           "neck": "Bone.003", "head": "Bone.004"}
    for s_, sh, ua, la, hd, ul, ll, ft, to in (
            ("left", "Bone.059", "Bone.011", "Bone.012", "Bone.013",
             "Bone.005", "Bone.006", "Bone.060", "Bone.007"),
            ("right", "Bone.058", "Bone.034", "Bone.035", "Bone.036",
             "Bone.008", "Bone.009", "Bone.061", "Bone.010")):
        MAP["%s_shoulder" % s_] = sh
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = hd
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
        MAP["%s_toes" % s_] = to
    # Finger chains, listed by their metacarpal. Ordered little -> thumb, which
    # is how they run in Y: the index sits nearest the thumb, furthest forward.
    for s_, base in (("left", 14), ("right", 37)):
        for i_, f_ in enumerate(("little", "ring", "middle", "index")):
            n_ = base + i_ * 4
            MAP["%s_%s_proximal" % (s_, f_)] = "Bone.%03d" % (n_ + 1)
            MAP["%s_%s_intermediate" % (s_, f_)] = "Bone.%03d" % (n_ + 2)
            MAP["%s_%s_distal" % (s_, f_)] = "Bone.%03d" % (n_ + 3)
        t_ = base + 16
        MAP["%s_thumb_metacarpal" % s_] = "Bone.%03d" % t_
        MAP["%s_thumb_proximal" % s_] = "Bone.%03d" % (t_ + 1)
        MAP["%s_thumb_distal" % s_] = "Bone.%03d" % (t_ + 3)
elif RIG == "simple":
    # A minimal hand-built rig: one bone per limb segment, no neck, no fingers.
    MAP = {"hips": "Hip_Bone", "spine": "Spine_Bone", "head": "Head_Bone"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        MAP["%s_upper_arm" % s_] = "Arm_Upper_Bone_%s" % p_
        MAP["%s_lower_arm" % s_] = "Arm_Lower_Bone_%s" % p_
        MAP["%s_hand" % s_] = "Hand_Bone_%s" % p_
        MAP["%s_upper_leg" % s_] = "Leg_Upper_Bone_%s" % p_
        MAP["%s_lower_leg" % s_] = "Leg_Lower_Bone_%s" % p_
        MAP["%s_foot" % s_] = "Foot_Bone_%s" % p_
elif RIG == "sonicforces":
    # Hedgehog Engine rig: plain CamelCase parts with a _L/_R suffix.
    MAP = {"hips": "Hips", "spine": "Spine", "chest": "Spine1",
           "neck": "Neck", "head": "Head"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s_] = "Shoulder_%s" % p_
        MAP["%s_upper_arm" % s_] = "UpperArm_%s" % p_
        MAP["%s_lower_arm" % s_] = "ForeArm_%s" % p_
        MAP["%s_hand" % s_] = "Hand_%s" % p_
        MAP["%s_upper_leg" % s_] = "Thigh_%s" % p_
        MAP["%s_lower_leg" % s_] = "Calf_%s" % p_
        MAP["%s_foot" % s_] = "Foot_%s" % p_
        MAP["%s_toes" % s_] = "Toe_%s" % p_
elif RIG == "arp":
    # Auto-Rig Pro: '.x' for centre bones, '.l'/'.r' for sides, and the
    # deforming limb bones carry a '_stretch' suffix.
    MAP = {"hips": "root.x", "spine": "spine_01.x", "chest": "spine_02.x",
           "neck": "neck.x", "head": "head.x"}
    for s_, p_ in (("left", "l"), ("right", "r")):
        MAP["%s_shoulder" % s_] = "shoulder.%s" % p_
        MAP["%s_upper_arm" % s_] = "arm_stretch.%s" % p_
        MAP["%s_lower_arm" % s_] = "forearm_stretch.%s" % p_
        MAP["%s_hand" % s_] = "hand.%s" % p_
        MAP["%s_thumb_metacarpal" % s_] = "thumb1.%s" % p_
        MAP["%s_thumb_proximal" % s_] = "thumb2.%s" % p_
        MAP["%s_thumb_distal" % s_] = "thumb3.%s" % p_
        for vf, af in (("index", "index"), ("middle", "middle"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%s1.%s" % (af, p_)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%s2.%s" % (af, p_)
            MAP["%s_%s_distal" % (s_, vf)] = "%s3.%s" % (af, p_)
        MAP["%s_upper_leg" % s_] = "thigh_stretch.%s" % p_
        MAP["%s_lower_leg" % s_] = "leg_stretch.%s" % p_
        MAP["%s_foot" % s_] = "foot.%s" % p_
        MAP["%s_toes" % s_] = "toes_01.%s" % p_
elif RIG == "rigify_plain":
    # Rigify's deform bones exported WITHOUT the DEF- prefix: the spine is a
    # numbered chain and the head may be a named bone or the chain's last link.
    MAP = {"hips": "spine", "spine": "spine.001", "chest": "spine.002",
           "upper_chest": "spine.003",
           "neck": ("neck" if "neck" in bone_names else "spine.004"),
           "head": ("Head" if "Head" in bone_names
                    else ("head" if "head" in bone_names else "spine.005"))}
    for s_, p_ in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s_] = "shoulder.%s" % p_
        MAP["%s_upper_arm" % s_] = "upper_arm.%s" % p_
        MAP["%s_lower_arm" % s_] = "forearm.%s" % p_
        MAP["%s_hand" % s_] = "hand.%s" % p_
        MAP["%s_thumb_metacarpal" % s_] = "thumb.01.%s" % p_
        MAP["%s_thumb_proximal" % s_] = "thumb.02.%s" % p_
        MAP["%s_thumb_distal" % s_] = "thumb.03.%s" % p_
        for vf, rf in (("index", "f_index"), ("middle", "f_middle"),
                       ("ring", "f_ring"), ("little", "f_pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%s.01.%s" % (rf, p_)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%s.02.%s" % (rf, p_)
            MAP["%s_%s_distal" % (s_, vf)] = "%s.03.%s" % (rf, p_)
        MAP["%s_upper_leg" % s_] = "thigh.%s" % p_
        MAP["%s_lower_leg" % s_] = "shin.%s" % p_
        MAP["%s_foot" % s_] = "foot.%s" % p_
        MAP["%s_toes" % s_] = "toe.%s" % p_
elif RIG == "advskel":
    # Advanced Skeleton: '_M' for middle, '_L'/'_R' for sides, and the limbs are
    # named after the JOINT above them - 'Shoulder_L' is the upper arm.
    MAP = {"hips": "Root_M", "spine": "Spine1_M", "chest": "Spine2_M",
           "upper_chest": "Chest_M", "neck": "Neck_M", "head": "Head_M"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        if "Scapula_%s" % p_ in bone_names:
            MAP["%s_shoulder" % s_] = "Scapula_%s" % p_
        MAP["%s_upper_arm" % s_] = "Shoulder_%s" % p_
        MAP["%s_lower_arm" % s_] = "Elbow_%s" % p_
        MAP["%s_hand" % s_] = "Wrist_%s" % p_
        for vf, af in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"),
                       ("ring", "Ring"), ("little", "Pinky")):
            a_, b_, c_ = ("%sFinger1_%s" % (af, p_), "%sFinger2_%s" % (af, p_),
                          "%sFinger3_%s" % (af, p_))
            if vf == "thumb":
                MAP["%s_thumb_metacarpal" % s_] = a_
                MAP["%s_thumb_proximal" % s_] = b_
                MAP["%s_thumb_distal" % s_] = c_
            else:
                MAP["%s_%s_proximal" % (s_, vf)] = a_
                MAP["%s_%s_intermediate" % (s_, vf)] = b_
                MAP["%s_%s_distal" % (s_, vf)] = c_
        MAP["%s_upper_leg" % s_] = "Hip_%s" % p_
        MAP["%s_lower_leg" % s_] = "Knee_%s" % p_
        MAP["%s_foot" % s_] = "Ankle_%s" % p_
        MAP["%s_toes" % s_] = "Toes_%s" % p_
elif RIG == "mayajnt":
    # Maya joint rig inside a namespace: '<ns>:jnt_<side>_<part>_<name>'. The
    # namespace is read off the bones rather than hard-coded.
    import re as _re
    _pref = ""
    for b in arm.data.bones:
        m = _re.match(r"^(.*:jnt_)", b.name)
        if m:
            _pref = m.group(1)
            break
    print("detected Maya joint prefix: '%s'" % _pref)
    J = _pref
    MAP = {"hips": J + "c_torso_origin", "spine": J + "c_torso_spine_1",
           "chest": J + "c_torso_spine_2", "upper_chest": J + "c_torso_spine_3",
           "neck": J + "c_torso_neck", "head": J + "c_torso_head"}
    for s_, p_ in (("left", "l"), ("right", "r")):
        q = "%s%s_" % (J, p_)
        MAP["%s_shoulder" % s_] = q + "arm_clavicle"
        MAP["%s_upper_arm" % s_] = q + "arm_shoulder"
        MAP["%s_lower_arm" % s_] = q + "arm_elbow"
        MAP["%s_hand" % s_] = q + "arm_wrist"
        MAP["%s_thumb_metacarpal" % s_] = q + "hand_thumb_1"
        MAP["%s_thumb_proximal" % s_] = q + "hand_thumb_2"
        MAP["%s_thumb_distal" % s_] = q + "hand_thumb_3"
        for vf, mf in (("index", "index"), ("middle", "mid"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%shand_%s_1" % (q, mf)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%shand_%s_2" % (q, mf)
            MAP["%s_%s_distal" % (s_, vf)] = "%shand_%s_3" % (q, mf)
        MAP["%s_upper_leg" % s_] = q + "leg_hip"
        MAP["%s_lower_leg" % s_] = q + "leg_knee"
        MAP["%s_foot" % s_] = q + "leg_ankle"
        MAP["%s_toes" % s_] = q + "leg_ball"
elif RIG == "b1":
    # Another rig whose bones are called 'Bone.0NN', mapped by reading the
    # hierarchy: three stubs meet at the pelvis - two leg chains and one spine -
    # and the arms hang off the spine's top. +X is the character's LEFT. There
    # is no hips bone, so the left hip stub serves as one and the other two
    # roots get re-parented under it.
    MAP = {"hips": "Bone.011", "spine": "Bone.023",
           "neck": "Bone.002", "head": "Bone.004"}
    for s_, (clav, ua, la, hd) in (("left", ("Bone.003", "Bone.008", "Bone.009", "Bone.010")),
                                   ("right", ("Bone.005", "Bone.006", "Bone.007", "Bone.021"))):
        MAP["%s_shoulder" % s_] = clav
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = hd
    for s_, (ul, ll, ft) in (("left", ("Bone.013", "Bone.015", "Bone.016")),
                             ("right", ("Bone.014", "Bone.017", "Bone.018"))):
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
elif RIG == "sonic":
    # Hand-built cartoon rig, 135 bones all called 'Bone.0NN', mapped by reading
    # the hierarchy. His torso bone runs straight into his head with nothing
    # between them, and VRM requires a spine, so synthesise a short one and hang
    # the head off it. The arms are long bendy chains - seven links from shoulder
    # to hand - so only the ends are mapped and the rest ride along.
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    _ebs = arm.data.edit_bones
    if "SpineSynth" not in _ebs and "Bone" in _ebs and "Bone.001" in _ebs:
        _torso = _ebs["Bone"]
        _dir = (_torso.tail - _torso.head)
        _nb = _ebs.new("SpineSynth")
        _nb.head = _torso.tail.copy()
        _nb.tail = _torso.tail + (_dir.normalized() * (_torso.length * 0.25)
                                  if _dir.length > 1e-6 else Vector((0.0, 0.0, 0.1)))
        _nb.parent = _torso
        _nb.use_connect = False
        _ebs["Bone.001"].parent = _nb
        print("  synthesised a spine bone between the torso and the head")
    bpy.ops.object.mode_set(mode="OBJECT")
    bone_names = {b.name for b in arm.data.bones}

    MAP = {"hips": "Bone", "spine": "SpineSynth", "head": "Bone.001"}
    for s_, (clav, ua, la, hd) in (
            ("left", ("Bone.002", "Bone.038", "Bone.041", "Bone.042")),
            ("right", ("Bone.094", "Bone.096", "Bone.099", "Bone.100"))):
        MAP["%s_shoulder" % s_] = clav
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = hd
    for s_, (ul, ll, ft, to) in (
            ("left", ("Bone.058", "Bone.062", "Bone.063", "Bone.064")),
            ("right", ("Bone.115", "Bone.119", "Bone.120", "Bone.121"))):
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
        MAP["%s_toes" % s_] = to
elif RIG == "cc_base":
    # Reallusion Character Creator export. Twist and ShareBone helpers are
    # ignored; only the joint-carrying bones are mapped.
    C = "CC_Base_"
    MAP = {"hips": C + "Hip", "spine": C + "Waist", "chest": C + "Spine01",
           "upper_chest": C + "Spine02", "neck": C + "NeckTwist02", "head": C + "Head"}
    for s, p in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s] = "%s%s_Clavicle" % (C, p)
        MAP["%s_upper_arm" % s] = "%s%s_Upperarm" % (C, p)
        MAP["%s_lower_arm" % s] = "%s%s_Forearm" % (C, p)
        MAP["%s_hand" % s] = "%s%s_Hand" % (C, p)
        MAP["%s_thumb_metacarpal" % s] = "%s%s_Thumb1" % (C, p)
        MAP["%s_thumb_proximal" % s] = "%s%s_Thumb2" % (C, p)
        MAP["%s_thumb_distal" % s] = "%s%s_Thumb3" % (C, p)
        for vf, cf in (("index", "Index"), ("middle", "Mid"),
                       ("ring", "Ring"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s, vf)] = "%s%s_%s1" % (C, p, cf)
            MAP["%s_%s_intermediate" % (s, vf)] = "%s%s_%s2" % (C, p, cf)
            MAP["%s_%s_distal" % (s, vf)] = "%s%s_%s3" % (C, p, cf)
        MAP["%s_upper_leg" % s] = "%s%s_Thigh" % (C, p)
        MAP["%s_lower_leg" % s] = "%s%s_Calf" % (C, p)
        MAP["%s_foot" % s] = "%s%s_Foot" % (C, p)
        MAP["%s_toes" % s] = "%s%s_ToeBase" % (C, p)
elif RIG == "smash":
    # Smash Bros / NUD rips number every bone in hierarchy order:
    # '_03_-_HipN', '_15_-_LShoulderJ'. The ordinal is position, not identity,
    # so map on what follows it. Note 'LShoulderN' is the clavicle and
    # 'LShoulderJ' is the upper arm.
    _by_suffix = {}
    for _b in arm.data.bones:
        _by_suffix.setdefault(re.sub(r"^_\d+_-_", "", _b.name).lower(), _b.name)

    def _sb(n):
        return _by_suffix.get(n.lower(), n)

    MAP = {"hips": _sb("HipN"), "spine": _sb("WaistN"), "chest": _sb("BustN"),
           "neck": _sb("NeckN"), "head": _sb("HeadN")}
    for s_, p_ in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s_] = _sb("%sShoulderN" % p_)
        MAP["%s_upper_arm" % s_] = _sb("%sShoulderJ" % p_)
        MAP["%s_lower_arm" % s_] = _sb("%sArmJ" % p_)
        MAP["%s_hand" % s_] = _sb("%sHandN" % p_)
        MAP["%s_upper_leg" % s_] = _sb("%sLegJ" % p_)
        MAP["%s_lower_leg" % s_] = _sb("%sKneeJ" % p_)
        MAP["%s_foot" % s_] = _sb("%sFootJ" % p_)
        MAP["%s_toes" % s_] = _sb("%sToeN" % p_)
        MAP["%s_thumb_metacarpal" % s_] = _sb("%sThumb1N" % p_)
        MAP["%s_thumb_proximal" % s_] = _sb("%sThumb2N" % p_)
        MAP["%s_thumb_distal" % s_] = _sb("%sThumb3N" % p_)
        for vf, nf in (("index", "Index"), ("middle", "Middle"),
                       ("ring", "Ring"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = _sb("%s%s1N" % (p_, nf))
            MAP["%s_%s_intermediate" % (s_, vf)] = _sb("%s%s2N" % (p_, nf))
            MAP["%s_%s_distal" % (s_, vf)] = _sb("%s%s3N" % (p_, nf))
elif RIG == "linkoot":
    # A Blender rig with CamelCase part names and '.l'/'.r' sides, a numbered
    # 'Spine_NN' chain, and the forearm spelled as a '.001' continuation of the
    # upper arm. It also carries a parallel '_ik' control skeleton, which is not
    # mapped and must not be: an IK control is not a deform bone.
    MAP = {"hips": "Pelvis", "spine": "Spine_01", "chest": "Spine_02",
           "upper_chest": "Spine_03", "neck": "Neck", "head": "Head"}
    for s_, p_ in (("left", "l"), ("right", "r")):
        MAP["%s_shoulder" % s_] = "Clavicle.%s" % p_
        MAP["%s_upper_arm" % s_] = "Upperarm.%s" % p_
        MAP["%s_lower_arm" % s_] = "Upperarm.%s.001" % p_
        MAP["%s_hand" % s_] = "Hand.%s" % p_
        MAP["%s_upper_leg" % s_] = "Thigh.%s" % p_
        MAP["%s_lower_leg" % s_] = "Calf.%s" % p_
        MAP["%s_foot" % s_] = "Foot.%s" % p_
        MAP["%s_toes" % s_] = "Foot_tip.%s" % p_
        MAP["%s_thumb_metacarpal" % s_] = "Thumb_01.%s" % p_
        MAP["%s_thumb_proximal" % s_] = "Thumb_02.%s" % p_
        MAP["%s_thumb_distal" % s_] = "Thumb_03.%s" % p_
        for vf, lf in (("index", "Index"), ("middle", "Middle"),
                       ("ring", "Ring"), ("little", "Pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%s_01.%s" % (lf, p_)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%s_02.%s" % (lf, p_)
            MAP["%s_%s_distal" % (s_, vf)] = "%s_03.%s" % (lf, p_)
elif RIG == "mariojnt":
    # Short Maya-style joint names with an L_/R_ prefix, as the N64-era Mario
    # rip uses. No chest bone, and the clavicles hang off the NECK, which is
    # the 3ds Max Biped trap the hierarchy repair already knows how to fix.
    MAP = {"hips": "Hip", "spine": "SpineM", "neck": "Neck", "head": "HeadJoin"}
    for s_, p_ in (("left", "L"), ("right", "R")):
        MAP["%s_shoulder" % s_] = "%s_clav" % p_
        MAP["%s_upper_arm" % s_] = "%s_Shold" % p_
        MAP["%s_lower_arm" % s_] = "%s_Elb" % p_
        MAP["%s_hand" % s_] = "%s_Wrist" % p_
        MAP["%s_upper_leg" % s_] = "%s_Thigh" % p_
        MAP["%s_lower_leg" % s_] = "%s_Knee" % p_
        MAP["%s_foot" % s_] = "%s_Ankle" % p_
        MAP["%s_toes" % s_] = "%s_Foot" % p_
        MAP["%s_thumb_metacarpal" % s_] = "%s_Thumb1" % p_
        MAP["%s_thumb_proximal" % s_] = "%s_Thumb2" % p_
        MAP["%s_thumb_distal" % s_] = "%s_Thumb3" % p_
        for vf, mf in (("index", "index"), ("middle", "middle"),
                       ("ring", "ring"), ("little", "pinky")):
            MAP["%s_%s_proximal" % (s_, vf)] = "%s_%s1" % (p_, mf)
            MAP["%s_%s_intermediate" % (s_, vf)] = "%s_%s2" % (p_, mf)
            MAP["%s_%s_distal" % (s_, vf)] = "%s_%s3" % (p_, mf)
else:
    raise SystemExit("unknown rig: " + RIG)

# Resolve every mapped name against the bones that are actually there, allowing
# for two things a rig family cannot usefully enumerate:
#   * CASE. The Mario rip spells one chain 'L_index1', 'L_index2', 'L_Index3'.
#   * A trailing '_NN' index. The Skibidi Toilet's Source rig ships
#     'ValveBiped.Bip01_L_Forearm_41', and matching it strictly mapped 0 of 52
#     humanoid bones while every bone it needed was sitting right there.
_LOWER = {}
_STRIPPED = {}
for _b in arm.data.bones:
    _LOWER.setdefault(_b.name.lower(), _b.name)
    _STRIPPED.setdefault(re.sub(r"_\d+$", "", _b.name).lower(), _b.name)
_fuzzy = 0
for _slot in list(MAP):
    _want = MAP[_slot]
    if _want in bone_names:
        continue
    _got = _LOWER.get(_want.lower()) or _STRIPPED.get(_want.lower())
    if _got:
        MAP[_slot] = _got
        _fuzzy += 1
if _fuzzy:
    print("resolved %d mapped bone name(s) by case or trailing index" % _fuzzy)

# VRM checks the HIERARCHY, not just the names: each humanoid bone has to be a
# descendant of the one above it. Rigs break that in two routine ways, and the
# export cancels with a message naming only the bone it gave up on.


def _ancestry(name):
    out, b = [], arm.data.bones.get(name)
    while b:
        out.append(b.name)
        b = b.parent
    return out


# 1. Hips. Several rigs hang the legs off a sibling of the bone that looks like
#    the pelvis (Batman's legs come off 'C_pelvis_att' while the spine comes off
#    'C_pelvis'; Max Biped does the same with 'Bip001'). The real hips is the
#    nearest common ancestor of the spine and both legs.
_sp, _ll, _rl = (MAP.get("spine"), MAP.get("left_upper_leg"), MAP.get("right_upper_leg"))
if all(x and x in bone_names for x in (_sp, _ll, _rl)):
    _chains = [_ancestry(_sp), _ancestry(_ll), _ancestry(_rl)]
    _common = [n for n in _chains[0] if all(n in c for c in _chains[1:])]
    _taken = {v for k, v in MAP.items() if k != "hips"}
    _lca = next((n for n in _common if n not in _taken), None)
    if _lca and MAP.get("hips") != _lca:
        print("  hips: '%s' is not above both legs and the spine - using '%s'"
              % (MAP.get("hips"), _lca))
        MAP["hips"] = _lca

# 1b. A limb may not hang off another humanoid bone. Some Max Biped exports
#     parent the thighs to 'Bip001 Spine' rather than the pelvis, so the legs
#     come out as children of the VRM spine, which is rejected. Where that
#     happens the bone is really the hips: promote it and shift the spine chain
#     up a link.
for _ in range(3):
    _sp = MAP.get("spine")
    _ll = MAP.get("left_upper_leg")
    if not (_sp and _ll and _sp in bone_names and _ll in bone_names):
        break
    if _sp not in _ancestry(_ll):
        break
    print("  spine: the legs hang off '%s', so it is really the hips - promoting it"
          % _sp)
    MAP["hips"] = _sp
    if MAP.get("chest"):
        MAP["spine"] = MAP["chest"]
        if MAP.get("upper_chest"):
            MAP["chest"] = MAP.pop("upper_chest")
        else:
            del MAP["chest"]
    else:
        del MAP["spine"]
        break

# 2. Upper chest / chest. If the shoulders do not actually hang below the bone
#    mapped as upper chest, that slot is wrong rather than the shoulder; VRM
#    treats chest and upper chest as optional, so drop the bad one instead of
#    failing (Tenna's shoulders sit above her mapped upper chest).
for _slot in ("upper_chest", "chest"):
    _c = MAP.get(_slot)
    if not _c or _c not in bone_names:
        continue
    _below = True
    for _s in ("left", "right"):
        _limb = MAP.get("%s_shoulder" % _s) or MAP.get("%s_upper_arm" % _s)
        if _limb and _limb in bone_names and _c not in _ancestry(_limb):
            _below = False
    if not _below:
        print("  %s: the shoulders are not below '%s' - leaving that slot empty"
              % (_slot, _c))
        del MAP[_slot]

# 3. Rebuild the humanoid hierarchy where it is missing. Rigify's DEF bones are
#    driven by constraints in the original rig, so an FBX export of them can
#    arrive completely FLAT - Tenna's shoulders, upper arms and thighs were all
#    root bones with no parent at all. VRM needs each humanoid bone under the
#    one above it. Re-parenting at rest is deformation-neutral: the armature
#    reads bone.matrix_local, which re-parenting does not move.
PARENT_SLOT = {
    "spine": ("hips",), "chest": ("spine", "hips"),
    "upper_chest": ("chest", "spine"),
    "neck": ("upper_chest", "chest", "spine"), "head": ("neck", "upper_chest", "chest"),
}
for _s in ("left", "right"):
    PARENT_SLOT["%s_shoulder" % _s] = ("upper_chest", "chest", "spine")
    PARENT_SLOT["%s_upper_arm" % _s] = ("%s_shoulder" % _s, "upper_chest", "chest")
    PARENT_SLOT["%s_lower_arm" % _s] = ("%s_upper_arm" % _s,)
    PARENT_SLOT["%s_hand" % _s] = ("%s_lower_arm" % _s,)
    PARENT_SLOT["%s_upper_leg" % _s] = ("hips",)
    PARENT_SLOT["%s_lower_leg" % _s] = ("%s_upper_leg" % _s,)
    PARENT_SLOT["%s_foot" % _s] = ("%s_lower_leg" % _s,)
    PARENT_SLOT["%s_toes" % _s] = ("%s_foot" % _s,)
    for _f in ("thumb", "index", "middle", "ring", "little"):
        a_ = "%s_%s_metacarpal" % (_s, _f) if _f == "thumb" else None
        PARENT_SLOT["%s_%s_proximal" % (_s, _f)] = tuple(
            x for x in (a_, "%s_hand" % _s) if x)
        PARENT_SLOT["%s_%s_intermediate" % (_s, _f)] = ("%s_%s_proximal" % (_s, _f),)
        PARENT_SLOT["%s_%s_distal" % (_s, _f)] = ("%s_%s_intermediate" % (_s, _f),)
    PARENT_SLOT["%s_thumb_metacarpal" % _s] = ("%s_hand" % _s,)

_fixes = []
for _slot, _parents in PARENT_SLOT.items():
    _b = MAP.get(_slot)
    if not _b or _b not in bone_names:
        continue
    _want = next((MAP[x] for x in _parents if MAP.get(x) in bone_names), None)
    if not _want or _want == _b:
        continue
    # Reaching the right parent is not enough: VRM also rejects a chain that
    # passes THROUGH another humanoid bone. Max Biped hangs the clavicles off
    # the NECK, so the shoulders did reach the spine - by way of a bone that is
    # itself mapped, which is invalid.
    _anc = _ancestry(_b)
    if _want in _anc:
        _between = _anc[1:_anc.index(_want)]
        _mapped = {v for k, v in MAP.items() if v and k != _slot}
        if not any(x in _mapped for x in _between):
            continue
    _fixes.append((_b, _want))

if _fixes:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    _ebs = arm.data.edit_bones
    _done = 0
    for _b, _want in _fixes:
        _eb, _pb = _ebs.get(_b), _ebs.get(_want)
        if not _eb or not _pb:
            continue
        # never create a cycle
        _p, _cyc = _pb, False
        while _p:
            if _p.name == _b:
                _cyc = True
                break
            _p = _p.parent
        if _cyc:
            continue
        _eb.use_connect = False
        _eb.parent = _pb
        _done += 1
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    print("  hierarchy: re-parented %d humanoid bones that were detached or "
          "hanging in the wrong place (e.g. %s -> %s)"
          % (_done, _fixes[0][0], _fixes[0][1]))

# VRM wants a single root under the hips. Rigs that keep helper roots alongside
# it (expression drivers, prop bones) make the exporter reject the humanoid, so
# re-parent any stray root to the hips bone rather than deleting it — the meshes
# may still be weighted to them.
_hips = MAP.get("hips")
if _hips and _hips in bone_names:
    _strays = [b.name for b in arm.data.bones if b.parent is None and b.name != _hips]
    if _strays:
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        for n in _strays:
            arm.data.edit_bones[n].parent = arm.data.edit_bones[_hips]
        bpy.ops.object.mode_set(mode="OBJECT")
        print("re-parented stray root bones under '%s': %s" % (_hips, _strays))

# ---------------------------------------------------------------- T-pose
# VRM 1.0 requires a T-pose and Unity builds the humanoid avatar on that
# assumption, so a model whose arms hang at its sides gets roughly 90 degrees of
# error in every arm muscle. In game that reads as the arms bending the wrong
# way the moment an animation plays. Measured 2026-11-07: Pomni's upper arm and
# hand shared an X of 0.1030 (arms straight down) and her arms inverted, while
# the Xenomorph and Prix -- both of which looked right -- run from shoulder to
# wrist along X.
# ---------------------------------------------------------------- facing
# Everything downstream assumes the character faces -Y: the T-pose swings the
# arms onto the X axis, and VRM itself requires the model to face forward. A
# model built facing sideways gets its arms rotated front-to-back instead of
# out, which looks like destroyed geometry rather than a rotation (measured on
# Batman: arm span 0.44 m across and a 1.31 m "depth" that was his cape seen
# edge-on). Read the facing off the feet, which point where the character does.
_fwd = Vector((0.0, 0.0, 0.0))
for _s in ("left", "right"):
    _ft, _to = MAP.get("%s_foot" % _s), MAP.get("%s_toes" % _s)
    if _ft in bone_names and _to in bone_names:
        _v = arm.data.bones[_to].head_local - arm.data.bones[_ft].head_local
        _v.z = 0.0
        if _v.length > 1e-6:
            _fwd += _v.normalized()
if _fwd.length > 1e-6:
    _fwd.normalize()
    _want = Vector((0.0, -1.0, 0.0))
    _ang = math.degrees(math.acos(max(-1.0, min(1.0, _fwd.dot(_want)))))
    # The feet are a good forward signal but not an infallible one: a cartoon
    # rig can have feet splayed sideways (Sonic's point along -X). If the arms
    # ALREADY run along X the character is a correct T-pose, and only a 180
    # degree turn leaves it that way - anything near 90 would swing the arms
    # front-to-back, which is the very thing this step exists to prevent.
    _turn = math.atan2(_want.y, _want.x) - math.atan2(_fwd.y, _fwd.x)
    _armx = 0.0
    _ua, _hd = MAP.get("left_upper_arm"), MAP.get("left_hand")
    if _ua in bone_names and _hd in bone_names:
        _av = arm.data.bones[_hd].head_local - arm.data.bones[_ua].head_local
        if _av.length > 1e-6:
            _armx = abs(_av.normalized().x)
    _near180 = abs(abs(math.degrees(_turn)) - 180.0) < 25.0
    if _ang > 20.0 and _armx > 0.9 and not _near180:
        print("  facing: feet point %s but the arms already lie along X - "
              "leaving the orientation alone rather than swinging them %.0f deg"
              % (tuple(round(v, 2) for v in _fwd), math.degrees(_turn)))
    elif _ang > 20.0:
        print("  facing: feet point %s, %.0f deg off forward - turning the "
              "character %.0f deg about Z"
              % (tuple(round(v, 2) for v in _fwd), _ang, math.degrees(_turn)))
        flatten(Matrix.Rotation(_turn, 4, "Z"))
        lo, hi = bounds()
        size = hi - lo
        for _o in bpy.data.objects:
            pass
        print("  facing: extent is now %.3f x %.3f x %.3f" % (size.x, size.y, size.z))
    else:
        print("  facing: feet point %s - already forward" % (tuple(round(v, 2) for v in _fwd),))

_arms = []
for _side, _sx in (("left", 1.0), ("right", -1.0)):
    _ua, _la = MAP.get("%s_upper_arm" % _side), MAP.get("%s_lower_arm" % _side)
    _hd = MAP.get("%s_hand" % _side)
    if _ua and _hd and _ua in bone_names and _hd in bone_names:
        _arms.append((_side, _sx, _ua,
                      _la if (_la and _la in bone_names) else None, _hd))


def _arm_error(ua, hd, sx):
    """Degrees between two bone heads' line and the X axis, measured on the
    POSE so it reflects corrections already applied."""
    v = arm.pose.bones[hd].head - arm.pose.bones[ua].head
    if v.length < 1e-9:
        return 0.0, None
    v.normalize()
    tgt = Vector((sx, 0.0, 0.0))
    return math.degrees(math.acos(max(-1.0, min(1.0, v.dot(tgt))))), v.rotation_difference(tgt)


# A Rigify DEF bone is DRIVEN by a Copy Transforms constraint from the control
# rig, so rotating it does nothing at all: Gadget Hackwrench's arms sat 26.4
# degrees off X and stayed there however many times the loop tried. Bake what
# the constraints are currently doing into the pose, then take them away, so the
# bones are ours to move. The exported skeleton has no use for a control rig.
_CONSTRAINED = [pb for pb in arm.pose.bones if pb.constraints]
if _CONSTRAINED:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.visual_transform_apply()
    for _pb in arm.pose.bones:
        for _c in list(_pb.constraints):
            _pb.constraints.remove(_c)
    bpy.ops.pose.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    print("  baked and removed constraints on %d pose bones (a driven bone "
          "cannot be posed)" % len(_CONSTRAINED))

def _straighten(rot_bone, from_bone, to_bone, sx):
    """Rotate `rot_bone` until the from->to line lies along the X axis.

    Converge rather than assume. One computed rotation lands exactly on some
    rigs and not on others - on a Mixamo rig with a shoulder bone a single 53
    degree correction left the arm 74 degrees out, worse than it started.
    Measure after each attempt and apply what is left."""
    for _ in range(8):
        _ang, _q = _arm_error(from_bone, to_bone, sx)
        if _ang < 2.0 or _q is None:
            break
        _pb = arm.pose.bones[rot_bone]
        _pb.rotation_mode = "QUATERNION"
        _h = _pb.head.copy()
        _pb.matrix = (Matrix.Translation(_h) @ _q.to_matrix().to_4x4()
                      @ Matrix.Translation(-_h)) @ _pb.matrix
        bpy.context.view_layer.update()
        # Assigning pose_bone.matrix can leave scale and translation in the
        # basis when the parent chain is not unit-scaled, and the loop then
        # applies it again on every iteration. Gordon Freeman came out 7.58 m
        # wide that way. Keep the ROTATION and nothing else.
        _l, _r, _sc = _pb.matrix_basis.decompose()
        _pb.matrix_basis = Matrix.LocRotScale(
            Vector((0.0, 0.0, 0.0)), _r, Vector((1.0, 1.0, 1.0)))
        bpy.context.view_layer.update()
    return _arm_error(from_bone, to_bone, sx)[0]


def _axis_error(a_name, b_name, tgt):
    """Degrees between the a->b bone line and `tgt`, plus the rotation closing it."""
    v = arm.pose.bones[b_name].head - arm.pose.bones[a_name].head
    if v.length < 1e-9:
        return 0.0, None
    v = v.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, v.dot(tgt))))), v.rotation_difference(tgt)


def _straighten_axis(rot_bone, from_bone, to_bone, tgt):
    """_straighten, for any target direction rather than only the X axis."""
    for _ in range(8):
        _ang, _q = _axis_error(from_bone, to_bone, tgt)
        if _ang < 2.0 or _q is None:
            break
        _pb = arm.pose.bones[rot_bone]
        _pb.rotation_mode = "QUATERNION"
        _h = _pb.head.copy()
        _pb.matrix = (Matrix.Translation(_h) @ _q.to_matrix().to_4x4()
                      @ Matrix.Translation(-_h)) @ _pb.matrix
        bpy.context.view_layer.update()
        _l, _r, _sc = _pb.matrix_basis.decompose()
        _pb.matrix_basis = Matrix.LocRotScale(
            Vector((0.0, 0.0, 0.0)), _r, Vector((1.0, 1.0, 1.0)))
        bpy.context.view_layer.update()
    return _axis_error(from_bone, to_bone, tgt)[0]


def _rotate_rig(M):
    """Turn the whole rig and all its geometry by M, keeping them together.

    flatten() cannot do this: it hands the matrix to Armature.transform(), which
    on this file left every bone exactly where it was -- hips->head stayed
    (-0.748, -0.385, -0.183) before and after, to three decimals. Write the rest
    bones directly instead, through EditBone.matrix so that head, tail and ROLL
    all move together, and transform each mesh by the same matrix. Requires the
    pose to be identity, which it is once the bind pose has been baked.
    """
    bpy.ops.object.mode_set(mode="OBJECT")
    for _o in meshes:
        if _o.data.users > 1:
            _o.data = _o.data.copy()
        _o.data.transform(M, shape_keys=True)
        _o.data.update()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for _eb in arm.data.edit_bones:
        _eb.matrix = M @ _eb.matrix
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


# Stand the character UP before asking anything about its arms.
#
# A T-pose is a standing pose, and every arm measurement here assumes a spine
# that runs up +Z. Anakin Skywalker's bind pose is a mid-air leap -- the file is
# literally called "anakin pose.fbx" -- so his spine lies nearly horizontal. The
# arm correction duly put both arms along X and left him lying down, a perfectly
# straight-armed character flat on his face, because nothing in the pipeline had
# ever had to rotate a whole character upright.
#
# Do it in two parts, and in this order. First turn the WHOLE rig so hips->head
# runs up: a whole-object rotation cannot break a binding, and it fixes the bulk
# of the error in one step. Then straighten each leg joint by joint onto -Z,
# which a global rotation cannot do because the legs are folded relative to the
# spine. Arms come after, below, and are left exactly as they were.
_SPINE_TILT = float(os.environ.get("VRM_STANDUP_DEG", "25"))
_hipsb, _headb = MAP.get("hips"), MAP.get("head")
# OPT-IN, and it stays that way until the measurement below is trustworthy.
# Sonic reads 115.4 degrees off vertical here and Yoda 93.4, yet both stand
# up perfectly well without this step: whatever space this is measuring in,
# it is not the one it looks like. Standing an upright character "up" is a
# regression, so only a model known to need it asks for it.
if (os.environ.get("VRM_STANDUP") and (not os.environ.get("VRM_NO_TPOSE"))
        and _hipsb in bone_names and _headb in bone_names):
    _A = arm.matrix_world
    _up = (_A @ arm.pose.bones[_headb].head) - (_A @ arm.pose.bones[_hipsb].head)
    _tilt = (math.degrees(math.acos(max(-1.0, min(1.0,
             _up.normalized().dot(Vector((0.0, 0.0, 1.0)))))))
             if _up.length > 1e-6 else 0.0)
    if _tilt > _SPINE_TILT:
        print("  stand up: the spine lies %.1f deg off vertical -- this bind "
              "pose is not a standing one" % _tilt)
        # Converge, do not compute. A connected bone's head is pinned to its
        # parent's tail, so setting every EditBone.matrix at once is not the
        # rigid rotation it looks like -- the first pass took the spine from
        # 102.3 degrees off vertical only as far as 76.3. Re-measure and apply
        # what is left.
        _UP = Vector((0.0, 0.0, 1.0))
        for _ in range(12):
            _v = (arm.matrix_world @ arm.pose.bones[_headb].head
                  - arm.matrix_world @ arm.pose.bones[_hipsb].head)
            if _v.length < 1e-9:
                break
            _off = math.degrees(math.acos(max(-1.0, min(1.0,
                _v.normalized().dot(_UP)))))
            if _off < 2.0:
                break
            _rotate_rig(_v.normalized().rotation_difference(_UP)
                        .to_matrix().to_4x4())
        _up2 = (arm.matrix_world @ arm.pose.bones[_headb].head
                - arm.matrix_world @ arm.pose.bones[_hipsb].head)
        print("  stand up: spine now %.1f deg off vertical"
              % math.degrees(math.acos(max(-1.0, min(1.0,
                  _up2.normalized().dot(Vector((0.0, 0.0, 1.0))))))))
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="POSE")
        _DOWN = Vector((0.0, 0.0, -1.0))
        for _s in ("left", "right"):
            _ul, _ll = MAP.get("%s_upper_leg" % _s), MAP.get("%s_lower_leg" % _s)
            _ft = MAP.get("%s_foot" % _s)
            if not (_ul in bone_names and _ll in bone_names):
                continue
            _e1 = _straighten_axis(_ul, _ul, _ll, _DOWN)
            _e2 = (_straighten_axis(_ll, _ll, _ft, _DOWN)
                   if _ft in bone_names else 0.0)
            print("  stand up: %s leg thigh %.1f deg off -Z, shin %.1f deg"
                  % (_s, _e1, _e2))
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
        # Standing him up spun him round the vertical axis too, and the facing
        # step ran long before this, so re-aim him now. The feet say where a
        # character looks; flatten them to the ground plane and turn the rig
        # about Z until they point -Y. Converge, for the same reason as above.
        _WANT = Vector((0.0, -1.0, 0.0))
        for _ in range(12):
            _f = Vector((0.0, 0.0, 0.0))
            for _s in ("left", "right"):
                _fb = MAP.get("%s_foot" % _s)
                if _fb not in bone_names:
                    continue
                _pb = arm.pose.bones[_fb]
                _d = (_pb.tail - _pb.head)
                _d.z = 0.0
                if _d.length > 1e-6:
                    _f += _d.normalized()
            if _f.length < 1e-6:
                break
            _f.normalize()
            _ang = math.degrees(math.acos(max(-1.0, min(1.0, _f.dot(_WANT)))))
            if _ang < 2.0:
                break
            _rotate_rig(Matrix.Rotation(
                math.atan2(_WANT.y, _WANT.x) - math.atan2(_f.y, _f.x), 4, "Z"))
        print("  stand up: feet now point %s"
              % (tuple(round(v, 2) for v in _f),))


if (not os.environ.get("VRM_NO_TPOSE")) and any(
        _arm_error(_ua, _hd, _sx)[0] >= 15.0 for _, _sx, _ua, _la, _hd in _arms):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for _side, _sx, _ua, _la, _hd in _arms:
        # Straighten the arm JOINT BY JOINT, not shoulder-to-hand in one go.
        # Rotating only the upper arm until the HAND sits on the X axis leaves
        # whatever bend the elbow had: Alcina Dimitrescu's static pose holds her
        # left elbow at 119.3 degrees, and correcting the arm as a single
        # segment swung the whole forearm round the shoulder and pinched the
        # sleeve into a crimp at the elbow. Put the upper arm along X first,
        # then the forearm, and the joint is genuinely straight.
        if _la:
            _e1 = _straighten(_ua, _ua, _la, _sx)
            _e2 = _straighten(_la, _la, _hd, _sx)
            print("  T-pose: %s upper arm %.1f deg off X, forearm %.1f deg "
                  "('%s' / '%s')" % (_side, _e1, _e2, _ua, _la))
        else:
            _e1 = _straighten(_ua, _ua, _hd, _sx)
            print("  T-pose: %s arm now %.1f deg off X ('%s') - no forearm bone "
                  "mapped, so the elbow keeps whatever bend it had"
                  % (_side, _e1, _ua))
    bpy.context.view_layer.update()

    # Move the geometry with the bones BEFORE making this pose the rest pose, or
    # the mesh keeps the old bind and the character tears apart. Computed by hand
    # rather than via modifier_apply: some of these meshes also carry Solidify
    # and Subdivision, and the evaluated mesh has a different vertex count.
    for _o in meshes:
        _g2n = {g.index: g.name for g in _o.vertex_groups}
        print("  T-pose bake: '%s' has %d groups, %d/%d verts weighted"
              % (_o.name, len(_o.vertex_groups),
                 sum(1 for v in _o.data.vertices
                     if any(g.weight > 0.0 for g in v.groups)),
                 len(_o.data.vertices)))
        _new = []
        for _v in _o.data.vertices:
            _acc = Vector((0.0, 0.0, 0.0))
            _tot = 0.0
            for _g in _v.groups:
                _pb = arm.pose.bones.get(_g2n.get(_g.group, ""))
                if _pb is None or _g.weight <= 0.0:
                    continue
                _acc += ((_pb.matrix @ _pb.bone.matrix_local.inverted()) @ _v.co) * _g.weight
                _tot += _g.weight
            _new.append(_acc / _tot if _tot > 1e-9 else _v.co.copy())
        for _v, _c in zip(_o.data.vertices, _new):
            _v.co = _c
        _o.data.update()

    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    for _side, _sx, _ua, _la, _hd in _arms:
        _res = _arm_error(_ua, _hd, _sx)[0]
        if _res > 15.0:
            raise SystemExit("ABORT: %s arm is still %.1f deg off X after the "
                             "T-pose correction" % (_side, _res))
    lo, hi = bounds()
    size = hi - lo

# ---------------------------------------------------------------- hair rig
# Spring bones need bones. A character whose hair is skinned straight to the
# head bone - Character Creator and stock Mixamo rigs both do this - has nothing
# to spring at all, so build the chains: find the hair by material, split it
# into strands, run a bone chain down each, and weight the hair onto them while
# leaving the scalp on the head so it cannot tear away.
HAIRRIG = a[9] if len(a) > 9 and a[9] else ""
# HAIR_BONE overrides what the new chains hang from. The rigger was written
# for hair, which hangs off the head, but the same machinery is what a CLOAK
# needs -- and a cloak hangs off the chest. Yoda's robe was skinned to his arms
# by the auto-rigger and webbed between arm and body the moment he T-posed.
_ANCHOR_BONE = os.environ.get("HAIR_BONE", "")
if _ANCHOR_BONE:
    _hit = [b.name for b in arm.data.bones
            if b.name == _ANCHOR_BONE or b.name.endswith(":" + _ANCHOR_BONE)
            or b.name.lower() == _ANCHOR_BONE.lower()]
    if not _hit:
        raise SystemExit("ABORT: HAIR_BONE names %r, which this rig has not got"
                         % _ANCHOR_BONE)
    _ANCHOR_BONE = _hit[0]
if HAIRRIG and (_ANCHOR_BONE or MAP.get("head") in bone_names):
    HEAD = _ANCHOR_BONE or MAP["head"]
    if _ANCHOR_BONE:
        print("  hair rig: hanging the new chains from '%s'" % HEAD)
    # Defaults suit loose hair. A FITTED garment needs most of itself pinned:
    # rigging Gwen's hood with these made it peel off her head and expose it,
    # because a worn-up hood has no loose cloth except its trailing edge.
    N_SEG = int(os.environ.get("HAIR_SEGS", "4"))        # bones per strand
    N_STRAND = int(os.environ.get("HAIR_STRANDS", "4"))  # strands to split into
    ANCHOR = float(os.environ.get("HAIR_ANCHOR", "0.30"))  # top fraction left rigid

    # Match a MESH name or a MATERIAL name: some models keep the hair as its own
    # object ('RL_G6_Hair', 'jester hat'), others as a material inside one body
    # mesh. Taking only one of the two missed half the set.
    hair = {}
    if HAIRRIG.lower().startswith("island:"):
        # Manual escape hatch for a part that has no name of its own: Gwen's
        # hood is inside one mesh called 'default' with one material covering
        # the whole costume, so neither a mesh nor a material name can select
        # it. It is a separate connected island, though, so address it by rank:
        # island:0 is the biggest, island:1 the next, and so on.
        # Several islands at once: a pair of twintails is two islands, and
        # rigging only the larger one leaves the other hanging rigid.
        want = [int(x) for x in HAIRRIG.split(":", 1)[1].split("+") if x.strip()]
        from collections import deque
        ranked = []
        for o in meshes:
            me = o.data
            adj = [[] for _ in range(len(me.vertices))]
            for e in me.edges:
                va, vb = e.vertices
                adj[va].append(vb)
                adj[vb].append(va)
            seen = [False] * len(me.vertices)
            for st in range(len(me.vertices)):
                if seen[st]:
                    continue
                q = deque([st]); seen[st] = True; comp = []
                while q:
                    v = q.popleft(); comp.append(v)
                    for w in adj[v]:
                        if not seen[w]:
                            seen[w] = True; q.append(w)
                ranked.append((len(comp), o, comp))
        ranked.sort(key=lambda t: -t[0])
        for _w in want:
            if _w < len(ranked):
                cnt, obj, comp = ranked[_w]
                hair.setdefault(obj, set()).update(comp)
                print("  hair rig: island %d of %d on mesh '%s', %d verts"
                      % (_w, len(ranked), obj.name, cnt))
            else:
                print("  hair rig: island %d does not exist (only %d)"
                      % (_w, len(ranked)))
    for o in (meshes if not hair else []):
        if re.search(HAIRRIG, o.name, re.I):
            hair[o] = {v.index for v in o.data.vertices}
            continue
        slots = [i for i, ms in enumerate(o.material_slots)
                 if ms.material and re.search(HAIRRIG, ms.material.name, re.I)]
        if not slots:
            continue
        vs = set()
        for poly in o.data.polygons:
            if poly.material_index in slots:
                vs.update(poly.vertices)
        if vs:
            hair[o] = vs

    total = sum(len(v) for v in hair.values())
    if not total:
        print("  hair rig: no material matches /%s/ - nothing to rig" % HAIRRIG)
    else:
        allz = [o.data.vertices[i].co.z for o, vs in hair.items() for i in vs]
        z_max, z_min = max(allz), min(allz)
        span = z_max - z_min
        z_anchor = z_max - span * ANCHOR
        pts = [(o.data.vertices[i].co.copy(), o, i)
               for o, vs in hair.items() for i in vs
               if o.data.vertices[i].co.z < z_anchor]
        print("  hair rig: %d hair verts spanning %.3f m; %d loose below z=%.3f"
              % (total, span, len(pts), z_anchor))

        if len(pts) < 50 or span < 0.05:
            print("  hair rig: too little loose hair to be worth rigging")
        else:
            # Split the loose hair into strands: k-means on the XY of the tips,
            # which is where separate strands are furthest apart.
            lo_cut = z_min + (z_anchor - z_min) * 0.35
            seeds = [p for p in pts if p[0].z < lo_cut] or pts
            cen = []
            for k in range(N_STRAND):
                c = seeds[int(len(seeds) * (k + 0.5) / N_STRAND)][0]
                cen.append(Vector((c.x, c.y)))
            buckets = [[] for _ in range(N_STRAND)]
            for _ in range(24):
                buckets = [[] for _ in range(N_STRAND)]
                for co, o, i in seeds:
                    xy = Vector((co.x, co.y))
                    k = min(range(N_STRAND), key=lambda j: (xy - cen[j]).length)
                    buckets[k].append(xy)
                moved = 0.0
                for k, b in enumerate(buckets):
                    if b:
                        nc = sum(b, Vector((0.0, 0.0))) / len(b)
                        moved = max(moved, (nc - cen[k]).length)
                        cen[k] = nc
                if moved < 1e-5:
                    break
            keep = [k for k in range(N_STRAND) if buckets[k]]
            print("  hair rig: %d strands at %s"
                  % (len(keep), [tuple(round(v, 3) for v in cen[k]) for k in keep]))

            assign = {}
            for co, o, i in pts:
                xy = Vector((co.x, co.y))
                assign[(o.name, i)] = min(keep, key=lambda j: (xy - cen[j]).length)

            bpy.context.view_layer.objects.active = arm
            bpy.ops.object.mode_set(mode="EDIT")
            ebs = arm.data.edit_bones
            made = []
            for k in keep:
                own = [p for p in pts if assign[(p[1].name, p[2])] == k]
                zs = [c.z for c, _, _ in own]
                top, bot = max(zs), min(zs)
                if top - bot < 0.02 or len(own) < 20:
                    continue
                step = (top - bot) / N_SEG

                def centre_between(z_hi, z_lo, members):
                    sel = [c for c, _, _ in members if z_lo <= c.z <= z_hi]
                    if not sel:
                        return None
                    s = Vector((0.0, 0.0))
                    for c in sel:
                        s += Vector((c.x, c.y))
                    return s / len(sel)

                prev = ebs.get(HEAD)
                chain = []
                for seg in range(N_SEG):
                    z0 = top - step * seg
                    z1 = top - step * (seg + 1)
                    a_xy = centre_between(z0, z1, own) or cen[k]
                    b_xy = centre_between(z1, z1 - step, own) or a_xy
                    nb = ebs.new("HairSpring_%d_%d" % (k, seg))
                    nb.head = Vector((a_xy.x, a_xy.y, z0))
                    nb.tail = Vector((b_xy.x, b_xy.y, z1))
                    nb.parent = prev
                    nb.use_connect = False
                    prev = nb
                    chain.append(nb.name)
                made.append((k, chain))
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.context.view_layer.update()
            print("  hair rig: built %d chains of %d bones" % (len(made), N_SEG))

            chain_of = dict(made)
            all_chain = {n for _, c in made for n in c}
            weighted = 0
            for o, vs in hair.items():
                groups = {}
                for k, c in made:
                    for n in c:
                        groups[n] = o.vertex_groups.get(n) or o.vertex_groups.new(name=n)
                hg = o.vertex_groups.get(HEAD) or o.vertex_groups.new(name=HEAD)
                # Clear whatever held this hair before. Models that keep the hair
                # on a single rigid bone ('RL_G6_Hair', 'hair') leave that weight
                # at 1.0; the armature normalises by total weight, so the old
                # bone would simply out-vote the new chain and the hair would not
                # move at all.
                loose = [i for i in vs if (o.name, i) in assign]
                if loose:
                    for vg in o.vertex_groups:
                        if vg.name not in all_chain and vg.name != HEAD:
                            vg.remove(loose)
                for i in vs:
                    key = (o.name, i)
                    if key not in assign:
                        continue
                    c = chain_of.get(assign[key])
                    if not c:
                        continue
                    z_top = arm.data.bones[c[0]].head_local.z
                    z_bot = arm.data.bones[c[-1]].tail_local.z
                    if z_top - z_bot < 1e-6:
                        continue
                    u = max(0.0, min(1.0, (z_top - o.data.vertices[i].co.z) / (z_top - z_bot)))
                    t = u * N_SEG
                    seg = min(N_SEG - 1, int(t))
                    frac = t - seg
                    # Hold on to the head across the first bone's length so the
                    # hair blends out of the scalp instead of detaching from it.
                    w_head = max(0.0, 1.0 - t)
                    w_chain = 1.0 - w_head
                    for n in c:
                        groups[n].remove([i])
                    hg.add([i], w_head, "REPLACE")
                    if w_chain > 0.0:
                        groups[c[seg]].add([i], w_chain * (1.0 - frac), "REPLACE")
                        if seg + 1 < N_SEG:
                            groups[c[seg + 1]].add([i], w_chain * frac, "REPLACE")
                    weighted += 1
            bone_names = {b.name for b in arm.data.bones}
            print("  hair rig: weighted %d hair vertices onto the new chains" % weighted)

# Seat on the FEET, not on the lowest vertex. A tail, cape or trailing prop can
# hang below the soles, and seating on the mesh minimum then lifts the character
# clear of the podium (measured on the Xenomorph: his tail put him in mid-air).
_feet = [MAP.get(k) for k in ("left_foot", "right_foot", "left_toes", "right_toes")]
_feet = [n for n in _feet if n and n in bone_names]
if _feet:
    _idx = {}
    for o in meshes:
        for vg in o.vertex_groups:
            if vg.name in _feet:
                _idx.setdefault(o, set()).add(vg.index)
    _zs = []
    for o, groups in _idx.items():
        mw = o.matrix_world
        for v in o.data.vertices:
            if any(g.group in groups and g.weight > 0.5 for g in v.groups):
                _zs.append((mw @ v.co).z)
    if _zs:
        _floor = min(_zs)
        if abs(_floor) > 0.005:
            print("  re-seating on the feet: sole is at z=%.4f (lowest vertex was %.4f)"
                  % (_floor, lo.z))
            flatten(Matrix.Translation((0.0, 0.0, -_floor)))
            lo, hi = bounds()
            print("  after re-seat: lowest vertex z=%.4f (below the floor is fine - "
                  "that is the tail)" % lo.z)

# ---------------------------------------------------------------- textures
# Only files Blender can actually open as an image.
#
# The texture folder is an extracted archive, so it also holds the .fbx, the
# .blend, readme.txt and a .mtl. Left in the pool those are candidates like any
# other, and the last-resort "largest file" rule makes the MODEL the strongest
# candidate of all -- it is usually the biggest file in the folder. Yoda's eye
# material was assigned 'yoda_rigged.fbx' and his eyes rendered magenta, which
# reads as a missing texture rather than as a texture that is a 3D model.
# Sonic's log carried the same line. Blender reports it only as a passing
# "failed to load image buffer" among a hundred packing warnings.
_IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tga", ".tif", ".tiff",
            ".exr", ".hdr", ".dds", ".webp", ".jp2", ".sgi", ".rgb", ".dpx")
files = ([f for f in os.listdir(TEXDIR) if f.lower().endswith(_IMG_EXT)]
         if os.path.isdir(TEXDIR) else [])
_skipped = ([f for f in os.listdir(TEXDIR) if not f.lower().endswith(_IMG_EXT)]
            if os.path.isdir(TEXDIR) else [])
if _skipped:
    print("textures: %d image(s) in %s; ignored %d non-image file(s): %s"
          % (len(files), TEXDIR, len(_skipped), _skipped[:6]))
# Biggest first, for the last-resort pool.
BY_SIZE = sorted(files, key=lambda f: -os.path.getsize(os.path.join(TEXDIR, f)))
# Which meshes wear each material, so a material with a meaningless name can be
# routed by the mesh it is on.
MAT_MESH = {}
for _o in meshes:
    for _ms in _o.material_slots:
        if _ms.material:
            MAT_MESH.setdefault(_ms.material.name, []).append(_o.name)
TOKENS = {
    # 'difus' deliberately, not 'diffuse': real-world assets ship 'Difusel',
    # 'Difuse' and similar misspellings, and a miss here means an untextured model.
    "base": ("basecolor", "difus", "diffus", "albedo", "baseco", "alb"),
    "metal": ("metallic", "metalness", "metall"),
    "rough": ("roughness", "roughn", "specular", "spec", "gloss"),
    "normal": ("normal",),
    "emis": ("emissive", "emission"),
    "height": ("height", "bump"),
    "alpha": ("opacity", "transparency", "alphamask"),
}


def norm(s):
    """Strip separators so 'Base_Color', 'BaseColor' and 'base color' all match."""
    return "".join(c for c in s.lower() if c.isalnum())


def _words(name):
    """Split a name into words: separators and camelCase boundaries both count."""
    # A bare number is not a word. Blender's '.001' duplicate suffix turns up on
    # almost every name in a busy file, so matching on it made Jessica Rabbit's
    # mesh 'hair1.001' share a "word" with 'Body_resculpt1.001_Bake1_Diffuse'
    # and her red hair took the dress bake and rendered black.
    return [w for w in re.split(r"[^A-Za-z0-9]+|(?<=[a-z])(?=[A-Z])", name)
            if len(w) >= 3 and not w.isdigit()]


def _shares_word(a_words, name):
    b_words = _words(name)
    for a in a_words:
        na = norm(a)
        for b in b_words:
            nb = norm(b)
            if na == nb or (len(na) >= 3 and na in nb) or (len(nb) >= 3 and nb in na):
                return True
    return False


# Some asset packs spell the map type as a short code in the LAST name part
# rather than as a word: 'C038_Base_C_2.png' is Lola Bunny's colour map and
# 'C038_Base_N_0.png' is her normal map. Neither carries a word the token table
# knows, so both counted as "no map word" and the size-ordered pool handed her
# the NORMAL map as skin -- she came out tangent-space purple. Only codes that
# cannot be mistaken for something else are listed: a lone 'R' or 'L' is a SIDE
# far more often than it is roughness.
_CODE = {"n": "normal", "nrm": "normal", "norm": "normal", "nor": "normal",
         "nml": "normal", "orm": "orm", "rma": "orm", "mra": "orm",
         "rough": "rough", "spec": "rough", "metal": "metal", "ao": "ao",
         "c": "base", "col": "base", "clr": "base", "diff": "base",
         "alb": "base", "bc": "base"}


def code_kind(stem):
    """The map type a short code at the end of the name implies, or None."""
    parts = [x for x in re.split(r"[^A-Za-z0-9]+", stem) if x]
    for x in reversed(parts):
        k = _CODE.get(x.lower())
        if k:
            return k
    return None


_NORMAL_CACHE = {}


def is_normal_map(path):
    """Does this image MEASURE as a tangent-space normal map?

    Names lie, and some archives ship nothing else: Harley Quinn's whole texture
    folder is one file called
    'INJ-2_iOS_VILLAIN_Harleen_Quinzell_Harley_.png', which names no map type at
    all and is a normal map -- used as her base colour it rendered her uniformly
    lavender, which reads as a broken export rather than a missing file. A
    normal map has a very particular signature no colour map shares: red and
    green centred on 0.5 and blue almost saturated.
    """
    if path in _NORMAL_CACHE:
        return _NORMAL_CACHE[path]
    verdict = False
    try:
        im = bpy.data.images.load(path, check_existing=False)
        try:
            im.scale(32, 32)
            px = list(im.pixels)
            n = len(px) // 4
            r = sum(px[i * 4] for i in range(n)) / n
            g = sum(px[i * 4 + 1] for i in range(n)) / n
            b = sum(px[i * 4 + 2] for i in range(n)) / n
            verdict = (abs(r - 0.5) < 0.09 and abs(g - 0.5) < 0.09 and b > 0.85)
        finally:
            bpy.data.images.remove(im)
    except Exception:
        verdict = False
    _NORMAL_CACHE[path] = verdict
    return verdict


def choose(pool, kind, loose=False):
    """First file in `pool` carrying this map type's token.

    `loose` additionally treats a file with NO map-type word as a base colour
    ('Teeth.png'). That is safe for a pool already narrowed to this material or
    its mesh, and NOT safe for the global pool: applied there it handed every
    one of Pomni's flat-colour materials - Blue, Red, Yellow, Outline - an
    unrelated 'Eyes.png' as their base map and wiped her colours out. A flat
    material with no texture of its own must keep its base-colour VALUE."""
    toks = [norm(t) for t in TOKENS[kind]]
    any_tok = [norm(t) for ts in TOKENS.values() for t in ts]
    if kind in ("base", "emis"):
        pool = [f for f in pool
                if not is_normal_map(os.path.join(TEXDIR, f))]
    # A PBR set can put the SAME word in several filenames: Yoda ships
    # 'yoda-mesh-RoninShader4_metallicRoughness_metal_scale0.jpg' and
    # '..._metallicRoughness_rough.jpg', and both contain "roughness". The
    # metal one sorted first and became his ROUGHNESS -- a 1x1 black image, so
    # roughness 0, so a mirror, and his robe shipped looking like wet plastic.
    # The short code at the end of the name is the tie-breaker.
    _coded = [(f, code_kind(os.path.splitext(f)[0])) for f in pool]
    _exact = [f for f, k in _coded if k == kind]
    if _exact:
        pool = _exact
    else:
        _other = {"normal", "orm", "rough", "metal", "ao", "base"} - {kind}
        pool = [f for f, k in _coded if k not in _other]
    for f in pool:
        if any(t in norm(f) for t in toks):
            return os.path.join(TEXDIR, f)
    if loose and kind == "base":
        plain = [f for f in pool if not any(t in norm(f) for t in any_tok)]
        coded = [(f, code_kind(os.path.splitext(f)[0])) for f in plain]
        if any(k == "base" for _, k in coded):
            plain = [f for f, k in coded if k == "base"]
        else:
            plain = [f for f, k in coded if k in (None, "base")]
        # Among files with no map word, a generically named one is the main
        # colour map; a specifically named one belongs to a part. Sonic's four
        # textures are eye2 / mouth / sonic_shoes / sonic_texture, and picking
        # by size alone gave his whole body the shoes.
        GENERIC = ("texture", "main", "body", "base", "skin")
        for f in plain:
            if any(g in norm(f) for g in GENERIC):
                return os.path.join(TEXDIR, f)
        for f in plain:
            return os.path.join(TEXDIR, f)
    return None


def pick(mat_name, kind, wide=True):
    """Three pools, narrowest first.

    1. files naming the MATERIAL;
    2. files sharing a word with a MESH that uses it -- because a material
       called 'ai_skin', 'phong1' or 'lambert8' names nothing, while the mesh it
       sits on ('female_body_Prinx') shares 'body' with
       'body 3_initialShadingGroup_BaseColor.png';
    3. everything, largest first. The old fallback took whatever os.listdir
       returned first, which handed all nine of Prix's materials an eyelash
       alpha map and rendered her black. Size is a crude signal but a far better
       one than alphabetical order: the main body map is normally the biggest
       file in the folder.
    """
    base = re.sub(r"\.\d{3}$", "", mat_name)
    base = re.sub(r"^(M|MI|MAT|Mtl)[_\-]", "", base, flags=re.I)
    slug = norm(base)
    # The '.NNN' suffix is noise on 'Dress.001' and INFORMATION when the folder
    # exports one map set per material: stripping it let every one of Alcina's
    # fourteen 'Material.NNN' materials claim 'Material.014_Base_Color.png', so
    # her skin, hat, hair and gloves all wore the same map.
    if re.search(r"\.\d{3}$", mat_name) and any(
            re.match(re.escape(base) + r"\.\d{3}", os.path.splitext(f)[0], re.I)
            for f in files):
        slug = norm(mat_name)
    named = []
    for f in files:
        nf = norm(f)
        stem = norm(os.path.splitext(f)[0])
        if slug and (slug in nf or (len(stem) >= 4 and stem in slug)):
            named.append(f)
    if named:
        # 'Link' is a whole word in 'Link_Link_BaseColor' and merely the start
        # of one in 'LinkEquip_Equipment_BaseColor'. Alphabetical order put the
        # equipment first, so Link's tunic, hair and skin all wore his shield.
        # Both 'Link_Link_BaseColor' and 'LinkEquip_Equipment_BaseColor' contain
        # 'Link' as a whole word, and alphabetical order put the equipment first,
        # so Link's tunic, hair and skin all wore his shield. The narrower name
        # is the better match: rank by how much is left once the map word and
        # the material's own name are taken out.
        def _slack(f):
            st = MAPTOK.sub("", os.path.splitext(f)[0])
            return len(norm(st).replace(slug, "", 1))
        return choose(sorted(named, key=_slack), kind, loose=True)
    # Files sharing a WORD with the material. 'shoes' does not appear inside
    # 'sonic_shoes' as a slug, but it is plainly the same word.
    # A name that is only a generic word names nothing, and matching on it is
    # how 'Material.016' reached 'Material.014_Base_Color.png' by the back door.
    _GENERIC_NAME = {"material", "mat", "mtl", "default", "standard", "surface",
                     "shader", "untitled", "new", "object", "mesh", "lambert",
                     "phong", "blinn", "basecolor", "color", "colour"}
    mat_words = [w for w in _words(base) if w.lower() not in _GENERIC_NAME]
    if mat_words:
        by_word = [f for f in BY_SIZE if _shares_word(mat_words, os.path.splitext(f)[0])]
        hit = choose(by_word, kind, loose=wide)
        if hit:
            return hit
    mesh_words = []
    for o in MAT_MESH.get(mat_name, []):
        mesh_words += _words(o)
    if mesh_words:
        by_mesh = [f for f in files if _shares_word(mesh_words, os.path.splitext(f)[0])]
        hit = choose(by_mesh, kind, loose=wide)
        if hit:
            return hit
    # The widest pool is a guess, and a guess must never overwrite a colour the
    # author chose on purpose -- see the deliberate-colour test at the call site.
    if not wide:
        return None
    return choose(BY_SIZE, kind)


# Many FBX/blend files point at the original author's own machine. The paths are
# dead but the BASENAMES are correct and tell us which texture each material
# wants, which beats guessing from the material's name. Relocate them into TEXDIR.
by_base = {f.lower(): os.path.join(TEXDIR, f) for f in files}
# Last resort for an archive whose names carry no information at all:
#   VRM_TEX="Material.005=CABELOO_preto_1.png,Material.019=hat.png:base"
TEX_OVERRIDE = {}
for _o in [x.strip() for x in os.environ.get("VRM_TEX", "").split(",") if x.strip()]:
    _m, _, _f = _o.partition("=")
    _f, _, _k = _f.partition(":")
    _k = _k or "base"
    _path = by_base.get(_f.strip().lower())
    if _path is None:
        raise SystemExit("ABORT: VRM_TEX names %r, which is not in %s" % (_f, TEXDIR))
    TEX_OVERRIDE[(_m.strip(), _k)] = _path
if TEX_OVERRIDE:
    print("texture overrides: %s" % sorted(k[0] + ":" + k[1] for k in TEX_OVERRIDE))
relocated = 0
for img in bpy.data.images:
    if not img.filepath:
        continue
    b = os.path.basename(img.filepath.replace("\\", "/")).lower()
    if b in by_base:
        img.filepath = by_base[b]
        relocated += 1
print("relocated %d broken image paths into the textures folder" % relocated)

SUFFIX = {
    "base": ("", "_basecolor", "_albedo", "_d"),
    "normal": ("_n", "_normal", "_nrm"),
    "rough": ("_s", "_r", "_roughness", "_spec"),
    "metal": ("_m", "_metallic", "_metalness"),
    "emis": ("_e", "_emissive", "_emission"),
    "height": ("_h", "_height", "_bump"),
    "alpha": ("_opacity", "_alpha", "_transparency"),
}
STEMS = {os.path.splitext(f)[0]: f for f in files}


# Every map-type word a texture filename may end with. Stripping one off a
# filename leaves the stem its whole SET shares.
MAPTOK = re.compile(
    r"[_\- ]*(base[_\- ]?colou?r|albedo(?:transparency)?|diffuse|difuse|difusel|"
    r"normal(?:map)?|nrm|metal(?:lic|ness)?|rough(?:ness)?|specular|spec|"
    r"emissive|emission|height|bump|opacity|alpha|ao|occlusion)$", re.I)


def _raw_stem(mat):
    """The stem a material's own texture reference points at, unjudged."""
    if not mat.use_nodes or not mat.node_tree:
        return None
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.filepath:
            b = os.path.basename(n.image.filepath.replace("\\", "/"))
            if b.lower() in by_base:
                return os.path.splitext(b)[0]
    return None


_STEM_POOL = {}
for _f in files:
    _STEM_POOL.setdefault(os.path.splitext(_f)[0].lower(), os.path.join(TEXDIR, _f))


def _link_image(bsdf, slot):
    """The image feeding this shader input, however many nodes back it sits."""
    if slot not in bsdf.inputs or not bsdf.inputs[slot].links:
        return None
    seen, stack = set(), [bsdf.inputs[slot].links[0].from_node]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n.type == "TEX_IMAGE" and n.image:
            return n.image
        for i in n.inputs:
            for l in i.links:
                stack.append(l.from_node)
    return None


def _link_node(bsdf, slot):
    """The TEX_IMAGE node feeding this shader input, however many nodes back."""
    if slot not in bsdf.inputs or not bsdf.inputs[slot].links:
        return None
    seen, stack = set(), [bsdf.inputs[slot].links[0].from_node]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n.type == "TEX_IMAGE" and n.image:
            return n
        for i in n.inputs:
            for l in i.links:
                stack.append(l.from_node)
    return None


def procedural_colour(bsdf):
    """One representative colour for a Base Color driven by PROCEDURAL nodes.

    glTF has no way to express a gradient texture through a colour ramp into a
    mix node, so the exporter writes plain white and the surface ships looking
    exactly like a missing texture. Jessica Rabbit's red hair was authored that
    way. Average every colour the graph names -- ramp stops, RGB nodes, unlinked
    colour sockets -- and use that one value instead. Returns None if a real
    image is in there, which the normal texture path already handles.
    """
    bi = bsdf.inputs.get("Base Color")
    if bi is None or not bi.links:
        return None
    cols, seen, stack = [], set(), [bi.links[0].from_node]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n.type == "TEX_IMAGE":
            return None
        if n.type == "VALTORGB":
            cols += [tuple(e.color[:3]) for e in n.color_ramp.elements]
        elif n.type == "RGB":
            cols.append(tuple(n.outputs[0].default_value[:3]))
        for i in n.inputs:
            if i.links:
                stack.append(i.links[0].from_node)
            elif i.type == "RGBA":
                try:
                    cols.append(tuple(i.default_value[:3]))
                except TypeError:
                    pass
    if not cols:
        return None
    return tuple(sum(c[k] for c in cols) / len(cols) for k in range(3))


def already_good(bsdf, slot):
    """The node already wired here, if its image actually has pixels.

    A .blend can carry its textures PACKED, with no filepath at all to match
    against the extracted texture folder: every one of Alcina Dimitrescu's
    materials wired a real image whose filepath was empty, so every name-based
    rule missed and the global pool handed her skin, hat, hair and gloves the
    one texture that did have a usable name. An image with pixels is the
    author's own answer and beats anything this file can guess, so keep it and
    do not go looking.
    """
    n = _link_node(bsdf, slot)
    if n is None:
        return None
    try:
        if n.image.has_data or (n.image.size[0] > 0 and n.image.size[1] > 0):
            return n
    except Exception:
        pass
    return None


def authored(bsdf, slot):
    """The file the SOURCE material points at for this slot, if the pool has it.

    This is the narrowest pool there is -- one file, named by the author -- and
    it beats every heuristic below, which exist only because so many archives
    say nothing. The HD Sonic says plenty: his four materials name the body,
    shoe, cloth and eye maps outright, and guessing from names called
    'Material__131' gave his body the EYE texture, so he rendered white with
    green eyes smeared down his legs.

    Matching is deliberately tolerant of the extension and of a truncated tail,
    because an archive's embedded reference and its extracted file routinely
    disagree: 'sonic_body..._d5hhp2h-pre.jpg' embedded against
    '..._d5hhp2h-pre.jpeg' on disk, and an eye map whose extracted name was cut
    short. A prefix match must be long and unique, or it is a guess again.
    """
    img = _link_image(bsdf, slot)
    if img is None:
        return None
    base = os.path.basename((img.filepath or img.name).replace("\\", "/"))
    stem = os.path.splitext(base)[0].lower()
    if not stem:
        return None
    # A reference that EVERY material shares is a placeholder, not information
    # -- the same trap SHARED_STEMS exists for on the name-matching path.
    if SHARED_STEMS and os.path.splitext(base)[0] in SHARED_STEMS:
        return None
    if stem in _STEM_POOL:
        return _STEM_POOL[stem]
    hits = [v for k, v in _STEM_POOL.items()
            if len(os.path.commonprefix([k, stem])) >= 12
            and (k.startswith(stem) or stem.startswith(k))]
    return hits[0] if len(hits) == 1 else None


def mat_stem(mat):
    """The stem this material's OWN texture reference shares with its map set.

    The material's own reference is the most reliable signal there is -- far
    better than guessing from a material called 'phong1' -- but only if the map
    word is stripped off it. Prix's skin material points at
    'body 3_initialShadingGroup_BaseColor.png'; returning that whole name as the
    stem means nothing matches 'stem + _BaseColor', the lookup fails, and the
    material falls through to the global pool, where it collects whichever file
    happens to sort first. Every one of her nine materials ended up wearing an
    eyelash alpha map, which is why she rendered black.
    """
    raw = _raw_stem(mat)
    if raw is None:
        return None
    # A reference EVERY material shares is a placeholder, not information.
    # Jessica Rabbit's materials all point at one baked body map, so trusting it
    # gave her skin, hair and gloves the same red dress texture.
    if SHARED_STEMS and raw in SHARED_STEMS:
        return None
    stripped = MAPTOK.sub("", raw)
    return stripped if len(stripped) >= 3 else raw


_stem_count = {}
for _m in bpy.data.materials:
    _r = _raw_stem(_m)
    if _r:
        _stem_count[_r] = _stem_count.get(_r, 0) + 1
_live_mats = max(1, len({ms.material.name for o in meshes for ms in o.material_slots if ms.material}))
SHARED_STEMS = {k for k, v in _stem_count.items() if v > max(2, _live_mats * 0.5)}
if SHARED_STEMS:
    print("ignoring %d texture reference(s) shared by most materials: %s"
          % (len(SHARED_STEMS), sorted(SHARED_STEMS)[:3]))


def pick_stem(stem, kind):
    """Any texture sharing this stem whose remainder names this map type.

    Matching on a fixed suffix list is too brittle for real downloads: the same
    set ships '_BaseColor', '_AlbedoTransparency', '_Difusel' and '_N'. Compare
    the leftover instead."""
    want = norm(stem)
    if not want:
        return None
    toks = [norm(t) for t in TOKENS[kind]]
    cands = [(norm(st), f) for st, f in STEMS.items() if norm(st).startswith(want)]
    # Same trap as in choose(): a PBR set can carry one map type's word in
    # several of its filenames. '..._metallicRoughness_metal_scale0.jpg' and
    # '..._metallicRoughness_rough.jpg' both contain "roughness", and the metal
    # one -- a 1x1 black image -- became Yoda's ROUGHNESS, so his robe shipped
    # as a mirror. Prefer the file whose short end-code names this map type.
    _exact = [(ns, f) for ns, f in cands
              if code_kind(os.path.splitext(f)[0]) == kind]
    if _exact:
        cands = _exact
    else:
        _other = {"normal", "orm", "rough", "metal", "ao", "base"} - {kind}
        cands = [(ns, f) for ns, f in cands
                 if code_kind(os.path.splitext(f)[0]) not in _other]
    for ns, f in cands:
        if any(t in ns[len(want):] for t in toks):
            return os.path.join(TEXDIR, f)
    if kind == "base":
        # a file that IS the stem, with no map word at all, is the base colour
        for ns, f in cands:
            if ns == want:
                return os.path.join(TEXDIR, f)
    return None


# Some downloads (a Mixamo animation export, for instance) carry no materials at
# all. Without one there is nothing to attach the textures to and the character
# exports blank, so give every bare mesh a material named after it.
for o in meshes:
    if not any(ms.material for ms in o.material_slots):
        m = bpy.data.materials.new(name=o.name)
        m.use_nodes = True
        o.data.materials.clear()
        o.data.materials.append(m)
        print("  created material '%s' for untextured mesh" % m.name)

used = set()
for o in meshes:
    for ms in o.material_slots:
        if ms.material:
            used.add(ms.material.name)

for mat in bpy.data.materials:
    if mat.name not in used:
        print("  material %-12s -> SKIPPED (not used by any mesh)" % mat.name)
        continue
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out:
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    # If the source file already told us which texture this material uses, trust
    # that over guessing from the material's name — generic names like
    # 'Material.013' carry no information at all.
    stem = mat_stem(mat)
    wired = []
    base_tex = None
    # Maps ship in SETS. Once the base colour is chosen, every other map for
    # this material should come from the same set, because a metalness map from
    # the wrong set is not a near miss -- it is a mirror. Link's tunic, hair and
    # skin all took 'LinkEquip_Equipment_Metallic.png' and he came out chromed.
    set_prefix = None
    # Blender's untouched default is 0.8 grey, and plain white is the other
    # "nothing here yet" value. Anything else was chosen -- Pomni's flat
    # Blue/Red/Yellow, Jessica Rabbit's red hair -- and the widest pool, which
    # is a guess, must not paint over it. That holds for EVERY map, not just the
    # base colour: handing her hair an unrelated metalness map turned it into a
    # mirror and it rendered white, which looked exactly like a missing texture.
    try:
        _bc = tuple(bsdf.inputs["Base Color"].default_value[:3])
    except (TypeError, KeyError):
        _bc = (1.0, 1.0, 1.0)
    _default_col = (all(c > 0.9 for c in _bc)
                    or all(abs(c - 0.8) < 0.02 for c in _bc))
    for kind, slot in (("base", "Base Color"), ("metal", "Metallic"),
                       ("rough", "Roughness"), ("emis", "Emission Color")):
        _ov = TEX_OVERRIDE.get((mat.name, kind)) or TEX_OVERRIDE.get((mat.name, "base"))             if kind == "base" else TEX_OVERRIDE.get((mat.name, kind))
        if _ov:
            img = bpy.data.images.load(_ov, check_existing=True)
            if kind not in ("base", "emis"):
                img.colorspace_settings.name = "Non-Color"
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
            nt.links.new(t.outputs["Color"], bsdf.inputs[slot])
            if kind == "base":
                base_tex = t
            wired.append((kind, "override:" + os.path.basename(_ov)))
            continue
        keep = already_good(bsdf, slot)
        if keep is not None:
            if kind == "base":
                base_tex = keep
            wired.append((kind, "packed:" + (keep.image.name or "?")))
            continue
        if set_prefix and kind != "base":
            # The set is the answer, including when the answer is "this set has
            # no such map". Borrowing one from another set is not a near miss:
            # Link's tunic took the equipment metalness and came out chromed.
            p = choose([f for f in files
                        if norm(os.path.splitext(f)[0]).startswith(set_prefix)], kind)
        else:
            p = (authored(bsdf, slot)
                 or (pick_stem(stem, kind) if stem else None)
                 or pick(mat.name, kind, wide=_default_col))
        if p is None and kind == "base" and slot in bsdf.inputs:
            # Nothing named this material and nothing shares a word with its
            # mesh. Whether it WANTS a texture is readable from the material
            # itself: one sitting at default white was expecting a map (this
            # file's 'HairFace' and 'Scalp'), while one carrying a real colour
            # is meant to be flat and must keep it - handing Pomni's Blue, Red
            # and Yellow a texture from the global pool wiped her colours out.
            col = bsdf.inputs[slot].default_value
            if _default_col:
                p = choose(BY_SIZE, kind, loose=True)
        if not p or slot not in bsdf.inputs:
            continue
        img = bpy.data.images.load(p, check_existing=True)
        if kind != "base" and kind != "emis":
            img.colorspace_settings.name = "Non-Color"
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], bsdf.inputs[slot])
        if kind == "base":
            base_tex = t
            _st = norm(MAPTOK.sub("", os.path.splitext(os.path.basename(p))[0]))
            set_prefix = _st if len(_st) >= 4 else None
        wired.append((kind, p))
        if kind == "emis" and "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 1.0
    if already_good(bsdf, "Normal") is not None:
        p = None
    elif set_prefix:
        _inset = [f for f in files
                  if norm(os.path.splitext(f)[0]).startswith(set_prefix)]
        p = choose(_inset, "normal") or choose(_inset, "height")
    else:
        p = (authored(bsdf, "Normal")
             or (pick_stem(stem, "normal") if stem else None)
             or (pick_stem(stem, "height") if stem else None)
             or pick(mat.name, "normal", wide=_default_col)
             or pick(mat.name, "height", wide=_default_col))
    if already_good(bsdf, "Normal") is not None:
        wired.append(("normal", "packed"))
    if p:
        img = bpy.data.images.load(p, check_existing=True)
        img.colorspace_settings.name = "Non-Color"
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        if "normal" in os.path.basename(p).lower():
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nt.links.new(t.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
            wired.append(("normal", p))
        else:
            bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.4
            nt.links.new(t.outputs["Color"], bm.inputs["Height"])
            nt.links.new(bm.outputs["Normal"], bsdf.inputs["Normal"])
            wired.append(("height", p))
    # Kill emission where there is no emissive MAP. An imported material can
    # carry a white emission colour left over from the source, and the exporter
    # writes it as emissiveFactor [1,1,1]: the surface then glows pure white and
    # drowns its own base colour, which is exactly why Thanos had a blank face
    # while the rest of him textured correctly. A material that really glows
    # (his gauntlet) has a map, and keeps it.
    if not any(k == "emis" for k, _ in wired):
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 0.0
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (0.0, 0.0, 0.0, 1.0)
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = (0.0, 0.0, 0.0, 1.0)

    # Transparency. Hair, eyelashes and lace are cards whose shape lives entirely
    # in an alpha channel: ignore it and they render as opaque slabs, or vanish.
    # Prix's hair texture averages 27% opacity, which is why she came out bald.
    # Prefer a dedicated opacity map (Sayuri ships 'Bikini_Opacity.png'); fall
    # back to the base colour's own alpha, but only when that alpha is really
    # carrying a shape - an all-zero channel would make the mesh invisible.
    ap = (pick_stem(stem, "alpha") if stem else None) or pick(mat.name, "alpha")
    cut = False
    if ap and "Alpha" in bsdf.inputs:
        img = bpy.data.images.load(ap, check_existing=True)
        img.colorspace_settings.name = "Non-Color"
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], bsdf.inputs["Alpha"])
        wired.append(("alpha", ap))
        cut = True
    # Only a DEDICATED opacity map is trusted. Inferring a cutout from the base
    # map's own alpha channel was tried and withdrawn: Prix's hair mesh is
    # 'CN_F_HAIR_111' while the only hair texture in her folder is
    # 'CN_F_HAIR_110_hair.png' - a different hair model's atlas. Its alpha cut
    # away the wrong regions and left her bald. A wrong cutout destroys geometry;
    # a missed one merely leaves it solid, so the cautious way round is right.
    # Metalness with no MAP is the same trap as emission with no map, one slot
    # over: a leftover Metallic of 1.0 turns the surface into a mirror that
    # reflects the world instead of showing its own colour. Link's face shipped
    # gold. A material that is really metal carries a map, and keeps it.
    if not any(k == "metal" for k, _ in wired) and "Metallic" in bsdf.inputs:
        try:
            if bsdf.inputs["Metallic"].default_value > 0.2:
                print("    metallic %.2f with no map -> 0"
                      % bsdf.inputs["Metallic"].default_value)
                bsdf.inputs["Metallic"].default_value = 0.0
        except TypeError:
            pass

    # Roughness with no MAP, left at 0, makes cloth look like wet plastic. The
    # Mixamo round-trip returns materials that way. A material that really is
    # glossy carries a map, or a value somebody chose.
    if not any(k == "rough" for k, _ in wired) and "Roughness" in bsdf.inputs:
        try:
            if bsdf.inputs["Roughness"].default_value < 0.15:
                print("    roughness %.2f with no map -> 0.6"
                      % bsdf.inputs["Roughness"].default_value)
                bsdf.inputs["Roughness"].default_value = 0.6
        except TypeError:
            pass

    if base_tex is None:
        _pc = procedural_colour(bsdf)
        if _pc is not None:
            _bi = bsdf.inputs["Base Color"]
            for _l in list(_bi.links):
                nt.links.remove(_l)
            _bi.default_value = (_pc[0], _pc[1], _pc[2], 1.0)
            _bc = _pc
            print("    flattened a procedural base colour to %s"
                  % (tuple(round(c, 3) for c in _pc),))

    # Say what the alpha mode IS, rather than letting the exporter guess.
    # Blender 4.2 removed Material.blend_method, and with nothing to read the VRM
    # add-on wrote alphaMode=BLEND for every material in the file - skin, bikini
    # and all. Blended opaque geometry sorts against itself and samples the base
    # map's alpha channel, which is what turned Sayuri's skin into brown and
    # white blotches. Set it on the add-on's own property instead.
    for attr, val in (("blend_method", "CLIP"), ("shadow_method", "CLIP"),
                      ("surface_render_method", "BLENDED" if cut else "DITHERED")):
        try: setattr(mat, attr, val)
        except Exception: pass
    try:
        mt = mat.vrm_addon_extension.mtoon1
        mt.alpha_mode = "MASK" if cut else "OPAQUE"
        mt.alpha_cutoff = 0.5
        # Once mtoon1 is in play the exporter writes ITS base colour factor,
        # which starts at white, and the Principled node's colour never leaves
        # Blender. A material whose whole appearance is a flat colour -- Jessica
        # Rabbit's red hair, Pomni's Blue/Red/Yellow -- then ships pure white,
        # which is indistinguishable from a missing texture.
        if base_tex is None:
            mt.pbr_metallic_roughness.base_color_factor = (
                _bc[0], _bc[1], _bc[2], 1.0)
        else:
            mt.pbr_metallic_roughness.base_color_factor = (1.0, 1.0, 1.0, 1.0)
    except Exception as _e:
        print("    (could not set alpha mode: %s)" % _e)

    print("  material %-22s col=%s %s-> %s" % (mat.name,
          tuple(round(c, 3) for c in _bc), "TEX " if base_tex is not None else "", ", ".join(
        "%s=%s" % (k, os.path.basename(v)) for k, v in wired) or "NONE"))

# An .exr/.hdr is lighting, not character skin. A blend that ships its studio
# HDRI wires it into the materials, which keeps it alive through the unused-image
# purge below and packs tens of megabytes of float image into the bundle (Pomni's
# courtyard.exr: a 12 MB character became 43 MB).
for _mat in bpy.data.materials:
    if not _mat.use_nodes or not _mat.node_tree:
        continue
    for _n in list(_mat.node_tree.nodes):
        _im = getattr(_n, "image", None)
        if _im is None:
            continue
        _ext = os.path.splitext(_im.filepath or _im.name)[1].lower()
        if _ext in {".exr", ".hdr"}:
            print("  dropping environment map '%s' from material '%s'" % (_im.name, _mat.name))
            _mat.node_tree.nodes.remove(_n)

# Drop materials no mesh uses, then any image left with no users. Without this a
# Sketchfab scene's discarded scenery still ships its textures inside the VRM.
for mat in list(bpy.data.materials):
    if mat.name not in used:
        bpy.data.materials.remove(mat)
removed = 0
for img in list(bpy.data.images):
    if img.users == 0:
        bpy.data.images.remove(img)
        removed += 1
print("purged %d unused images" % removed)

for img in bpy.data.images:
    if not img.has_data and img.filepath:
        try: img.reload()
        except Exception: pass
    w, h = img.size
    if w > TEXMAX or h > TEXMAX:
        img.scale(min(w, TEXMAX), min(h, TEXMAX))
    try: img.pack()
    except Exception: pass
print("images kept:", [i.name for i in bpy.data.images])

# ---------------------------------------------------------------- vrm
ext = arm.data.vrm_addon_extension
ext.spec_version = "1.0"
meta = ext.vrm1.meta
meta.vrm_name = NAME
meta.version = "1.0"
try:
    meta.authors.clear(); meta.authors.add().value = "fatalexception (conversion)"
except Exception: pass
for attr, value in (
    ("copyright_information", "Third-party model. Personal use only. Not for redistribution."),
    ("avatar_permission", "onlyAuthor"), ("commercial_usage", "personalNonProfit"),
    ("credit_notation", "required"), ("allow_redistribution", False),
    ("modification", "prohibited"), ("license_url", "https://vrm.dev/licenses/1.0/"),
):
    try: setattr(meta, attr, value)
    except Exception: pass

trace("before export")
hb = ext.vrm1.humanoid.human_bones
ok, missing = 0, []
for slot, bone in MAP.items():
    t = getattr(hb, slot, None)
    if t is None:
        missing.append((slot, "NO SLOT")); continue
    if bone not in bone_names:
        missing.append((slot, bone)); continue
    t.node.bone_name = bone
    ok += 1
wrong = sum(1 for s, b in MAP.items()
            if getattr(hb, s, None) is not None and b in bone_names
            and getattr(hb, s).node.bone_name != b)
print("humanoid: assigned %d/%d, readback mismatches %d" % (ok, len(MAP), wrong))
for s, b in missing:
    print("  UNMAPPED %-26s %s" % (s, b))

# ---------------------------------------------------------------- spring bones
# Unity's humanoid system has no muscle for a tail, hair or cloth, so those stay
# rigid no matter what the animation does. VRM moves them with spring bones, and
# YARG drives those at runtime (VRMCharacter.SetWind / SetSpringPause).
# Unity's humanoid rig has no muscle for hair, a skirt or a tail, so without
# spring bones they stay rigid however well the character animates. Rather than
# naming the chains per model, detect the usual ones; an explicit pattern still
# overrides. Humanoid bones are excluded - a spring bone must not also be a
# limb, and matching 'tail' against a real skeleton would do exactly that.
DEFAULT_SPRING = (r"(hair|ponytail|pigtail|braid|bang|tail|skirt|dress|cloth|"
                  r"ribbon|scarf|cape|coat|tassel|fringe|antenna|hat|bell|horn|wing|feather|tie)")
SPRING = a[8] if len(a) > 8 and a[8] else DEFAULT_SPRING
if SPRING:
    try:
        sb = ext.spring_bone1
        humanoid_bones = {v for v in MAP.values()}

        def springy(b):
            return re.search(SPRING, b.name, re.I) and b.name not in humanoid_bones

        roots = [b for b in arm.data.bones
                 if springy(b) and not (b.parent and springy(b.parent))]
        made = 0
        def walk(bone):
            """One chain per branch. Following only the first child quietly
            dropped two of Prix's three hair chains: her three strands share a
            parent called 'hairAll', so a single-path walk sprang one strand and
            left the others rigid. A bone may belong to only one chain, so a
            shared trunk is emitted separately rather than repeated in each."""
            path, cur = [], bone
            while True:
                path.append(cur.name)
                kids = [c for c in cur.children if springy(c)]
                if len(kids) == 1:
                    cur = kids[0]
                    continue
                if not kids:
                    yield path
                    return
                if len(path) >= 2:
                    yield path
                for k in kids:
                    for sub in walk(k):
                        yield sub
                return

        for chain in [c for root in roots for c in walk(root)]:
            if len(chain) < 2:
                continue
            spring = sb.springs.add()
            try:
                spring.vrm_name = chain[0]
            except Exception:
                pass
            for n in chain:
                j = spring.joints.add()
                j.node.bone_name = n
                for prop, val in (("hit_radius", 0.02), ("stiffness", 0.6),
                                  ("drag_force", 0.45), ("gravity_power", 0.0)):
                    try:
                        setattr(j, prop, val)
                    except Exception:
                        pass
            made += 1
            print("  spring chain '%s': %d joints" % (chain[0], len(chain)))
        print("spring bone chains added: %d%s" % (
            made, "" if made else "  (no hair/skirt/tail bones in this rig - its "
            "hair and clothes are skinned to the body, so there is nothing to spring)"))
    except Exception as e:
        print("spring bone setup failed: %s: %s" % (type(e).__name__, e))

if os.environ.get("VRM_SAVE_BLEND"):
    bpy.ops.wm.save_as_mainfile(filepath=os.environ["VRM_SAVE_BLEND"])
    print("saved pre-export scene to", os.environ["VRM_SAVE_BLEND"])
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = arm
try:
    _res = bpy.ops.export_scene.vrm(filepath=OUTVRM)
    print("export_scene.vrm returned:", _res)
except Exception as _e:
    print("export_scene.vrm RAISED:", type(_e).__name__, _e)
if not os.path.exists(OUTVRM):
    # Ask the add-on's own validator why, rather than guessing. detect_errors
    # wants a Blender CollectionProperty, not a list -- passing a list raises
    # AttributeError and the real reason never gets printed, which is how a
    # cancelled export looked like an unexplained one. Register a throwaway
    # collection of its own error type and read the messages out of that.
    try:
        from bl_ext.user_default.vrm.editor.validation import (  # type: ignore
            WM_OT_vrm_validator, VrmValidationError)
        bpy.types.Scene.vrm_probe_errors = bpy.props.CollectionProperty(
            type=VrmValidationError)
        coll = bpy.context.scene.vrm_probe_errors
        coll.clear()
        WM_OT_vrm_validator.detect_errors(bpy.context, coll, arm.name)
        if len(coll):
            for e in coll:
                print("  VALIDATION [%s] %s" % (
                    "FATAL" if getattr(e, "fatal", True) else "warn",
                    getattr(e, "message", e)))
        else:
            print("  (the validator reported no errors - the cancel is elsewhere)")
    except Exception as _e:
        print("  (validator probe failed: %s: %s)" % (type(_e).__name__, _e))
    raise SystemExit("ABORT: the VRM exporter produced no file")
print("VRM: %s  %.1f MB" % (OUTVRM, os.path.getsize(OUTVRM) / 1048576))
print("DONE")
