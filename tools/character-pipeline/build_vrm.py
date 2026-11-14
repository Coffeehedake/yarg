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
    # Choosing one armature SILENTLY UNBINDS every mesh skinned to the others.
    # Lola Bunny's glTF carries four skins -- body, both sets of teeth, and her
    # hair -- each properly weighted. The body won on vertex count and the
    # other three meshes came out with skin=None: 2,452 vertices that nothing
    # in the file could ever move. "Her hair and teeth don't animate with her
    # body" was this line, not her weights, which were correct all along.
    #
    # The skins are nearly always the same rig split up, so the vertex groups
    # already name bones the chosen armature has. Re-point the modifier and
    # the binding comes back; report what a mesh loses when they do not.
    _rebound, _lost = [], []
    for _o in [o for o in bpy.data.objects if o.type == "MESH"]:
        _mods = [m for m in _o.modifiers if m.type == "ARMATURE"]
        if not _mods or any(m.object is arm for m in _mods):
            continue
        _names = set(b.name for b in arm.data.bones)
        _have = [g.name for g in _o.vertex_groups if g.name in _names]
        _miss = [g.name for g in _o.vertex_groups if g.name not in _names]
        # A glTF that carries the same rig TWICE uniquifies the second copy's
        # bone names with a numeric suffix. Batman's cape hangs off
        # 'fml_un_C_pelvis_331' and his body off 'fml_un_C_pelvis_818': the
        # same bone, and a literal comparison calls them strangers. Strip a
        # trailing _NNN from both sides and match on what is left, then rename
        # the groups so the modifier can read them.
        if not _have and _miss:
            _strip = lambda _n: re.sub(r"_\d+$", "", _n)
            _by = {}
            for _b in arm.data.bones:
                _by.setdefault(_strip(_b.name), _b.name)
            _ren = []
            for _g in list(_o.vertex_groups):
                _t = _by.get(_strip(_g.name))
                if _t and _t != _g.name:
                    _g.name = _t
                    _ren.append(_t)
            if _ren:
                _have, _miss = _ren, []
                print("  matched %d vertex group(s) on '%s' to the chosen "
                      "armature by stripping the uniquifying suffix (same rig "
                      "exported twice): %s"
                      % (len(_ren), _o.name, ", ".join(_ren[:4])))
        for _m in _mods:
            _m.object = arm
        _o.parent = arm
        if _have:
            _rebound.append((_o.name, len(_have), len(_miss)))
        else:
            _lost.append(_o.name)
    if _rebound:
        print("  re-bound %d mesh(es) that were skinned to a DISCARDED "
              "armature, which would have shipped unskinned: %s"
              % (len(_rebound), ", ".join(
                  "%s (%d groups kept, %d absent)" % t for t in _rebound[:6])))
    if _lost:
        print("  WARNING: %d mesh(es) were skinned to a discarded armature and "
              "share NO bone names with the chosen one, so re-binding them "
              "would be a guess: %s" % (len(_lost), ", ".join(_lost[:6])))
# A glTF exporter that has to uniquify names appends _NNN to every bone, and a
# rig that was perfectly well named stops matching its own family. Jessica
# Rabbit's glTF is a Rigify skeleton -- spine, spine.001, face, nose -- with
# 159 of its 160 bones carrying a suffix, so rigify_plain matches not one of
# them and she cannot be built at all.
#
# Strip it, but only when it is really a suffix and not part of the name:
# every bone must carry one, and stripping must not collide two bones into a
# single name. Refuse otherwise and leave the rig alone, because renaming a
# bone the weights refer to is not recoverable. Vertex groups are renamed with
# the bones, since they are what the modifier reads.
if not os.environ.get("VRM_KEEP_SUFFIX"):
    _sfx = re.compile(r"_\d+$")
    _all = [b.name for b in arm.data.bones]
    _hit = [n for n in _all if _sfx.search(n)]
    if _all and len(_hit) >= max(4, int(len(_all) * 0.9)):
        _new = dict((n, _sfx.sub("", n)) for n in _all)
        _vals = list(_new.values())
        if len(set(_vals)) == len(_vals) and all(_vals):
            _groups = {}
            for _o in bpy.data.objects:
                if _o.type == "MESH":
                    for _g in _o.vertex_groups:
                        _groups.setdefault(_g.name, []).append(_g)
            for _b in arm.data.bones:
                _t = _new[_b.name]
                if _t != _b.name:
                    for _g in _groups.get(_b.name, []):
                        _g.name = _t
                    _b.name = _t
            print("stripped a uniquifying suffix from %d of %d bones (and "
                  "their vertex groups): the rig is named normally underneath "
                  "-- e.g. %s" % (len(_hit), len(_all),
                                  ", ".join(sorted(set(_vals))[:4])))
        else:
            print("  bones carry a _NNN suffix but stripping it would collide "
                  "%d names into %d -- left alone"
                  % (len(_vals), len(set(_vals))))

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

def _islands(o, weld=False):
    """Connected vertex islands of a mesh, biggest first.

    `weld=True` treats vertices that share a POSITION as one first. A USD
    import arrives fully SPLIT -- every face carries its own copy of each
    corner, and no two faces share an edge -- so without welding, Vigilante's
    weapons mesh reports 146 islands of four vertices each instead of 4, and
    any rule of the form "most of this island is X" becomes trivially true of a
    single quad. It is off by default because the island RANKS feed
    VRM_RIGID and the hair rigger (`island:7+8` picks Miku's twintails), and
    welding would renumber them.
    """
    rep = list(range(len(o.data.vertices)))
    if weld:
        seen = {}
        for v in o.data.vertices:
            k = (round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5))
            rep[v.index] = seen.setdefault(k, v.index)
    adj = {}
    for e in o.data.edges:
        a, b = rep[e.vertices[0]], rep[e.vertices[1]]
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    members = {}
    for v in range(len(o.data.vertices)):
        members.setdefault(rep[v], []).append(v)
    seen, out = set(), []
    for v in sorted(members):
        if v in seen:
            continue
        comp, stack = [], [v]
        seen.add(v)
        while stack:
            x = stack.pop()
            comp += members.get(x, [x])
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        out.append(comp)
    out.sort(key=len, reverse=True)
    return out


# A prop can share a MESH with gear that belongs on the character, and then no
# name pattern can separate the two. Vigilante's two held weapons, the sheath on
# his back and the holster on his hip are four islands of ONE mesh: excluding it
# takes his kit away with the weapons, and keeping it leaves the weapons in his
# hands -- where YARG puts a microphone.
#
#   VRM_DROP_ISLAND="<mesh-pattern>=<bone>[+<bone>...][,<pattern>=<bone>...]"
#
# drops every connected island of a matching mesh that is mostly driven by one
# of those bones -- what the bone CARRIES rather than what it is.
#
# The mesh pattern is not optional, and that is the whole safety of it: a hand
# is itself weighted to the hand bone, so a bone named on its own would take the
# hand off with what it is holding. Naming the prop's own mesh is what makes the
# selection safe, and an island that is only partly the bone's (the threshold is
# four fifths) is left alone, because a part that shares a bone with real body
# geometry is not a prop.
for _spec in [x for x in os.environ.get("VRM_DROP_ISLAND", "").split(",")
              if x.strip()]:
    _pat, _, _bones = _spec.strip().rpartition("=")
    if not _pat or not _bones:
        raise SystemExit("ABORT: VRM_DROP_ISLAND spec %r is not "
                         "'<mesh-pattern>=<bone>[+<bone>]'" % _spec)
    _want = []
    for _b in _bones.split("+"):
        _hit = [b.name for b in arm.data.bones
                if b.name == _b or b.name.endswith(":" + _b)
                or b.name.endswith("_" + _b)]
        if not _hit:
            raise SystemExit("ABORT: VRM_DROP_ISLAND names bone %r, which this "
                             "rig has not got" % _b)
        _want.append(_hit[0])
    _hits = [o for o in meshes if re.search(_pat, o.name, re.I)]
    if not _hits:
        raise SystemExit("ABORT: VRM_DROP_ISLAND mesh pattern /%s/ matched "
                         "nothing" % _pat)
    _dropped = 0
    for _o in list(_hits):
        _gi = dict((_g.index, _g.name) for _g in _o.vertex_groups)
        _kill = []
        for _isl in _islands(_o, weld=True):
            _n = 0
            for _vi in _isl:
                _gs = _o.data.vertices[_vi].groups
                _best = max(_gs, key=lambda g: g.weight) if len(_gs) else None
                if _best is not None and _gi.get(_best.group) in _want:
                    _n += 1
            if _n * 5 < len(_isl) * 4:
                continue
            _co = [_o.matrix_world @ _o.data.vertices[i].co for i in _isl]
            print("  drop island: '%s' %d verts carried by %s, "
                  "x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f"
                  % (_o.name, len(_isl), "/".join(_want),
                     min(c.x for c in _co), max(c.x for c in _co),
                     min(c.y for c in _co), max(c.y for c in _co),
                     min(c.z for c in _co), max(c.z for c in _co)))
            _kill += _isl
            _dropped += len(_isl)
        if not _kill:
            continue
        if len(_kill) == len(_o.data.vertices):
            print("  drop island: '%s' was ALL prop -- removing the mesh" % _o.name)
            bpy.data.objects.remove(_o, do_unlink=True)
            meshes.remove(_o)
            continue
        import bmesh as _bmesh
        _bm = _bmesh.new()
        _bm.from_mesh(_o.data)
        _bm.verts.ensure_lookup_table()
        _bmesh.ops.delete(_bm, geom=[_bm.verts[i] for i in _kill],
                          context="VERTS")
        _bm.to_mesh(_o.data)
        _bm.free()
    # A spec that matches meshes and drops nothing is a spec that did not do
    # what it says. Say so here, rather than let a silent no-op be read in a
    # render as "the prop is gone".
    if not _dropped:
        raise SystemExit("ABORT: VRM_DROP_ISLAND %r matched %d mesh(es), but no "
                         "island of them is carried by %s -- nothing was dropped"
                         % (_spec, len(_hits), "/".join(_want)))
if not meshes:
    raise SystemExit("ABORT: VRM_DROP_ISLAND removed every mesh")

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
    # VRM_TRACE_OFFSET="a,b" tracks one material group RELATIVE to another at
    # every stage, which a whole-mesh box cannot do: Gadget Hackwrench's teeth
    # and her face are the same mesh, so the box moves with the face and says
    # nothing about the teeth inside it.
    #
    # Measured against the EYES rather than the floor on purpose. The first
    # attempt at her used absolute z against model height, read as a vertical
    # drop, and sent three rebuilds chasing the pose bake. Teeth-to-eye offset
    # needs no shared origin, no scale and no facing, and it showed the real
    # signal is HORIZONTAL: 0.011 in front of her eyes in the source, 0.124 in
    # the build.
    _pair = os.environ.get("VRM_TRACE_OFFSET")
    if _pair and "," in _pair:
        _a, _b = [x.strip().lower() for x in _pair.split(",", 1)]
        bpy.context.view_layer.update()
        _deps = bpy.context.evaluated_depsgraph_get()

        def _mat_centre(sub):
            acc = Vector((0.0, 0.0, 0.0))
            n = 0
            for ob in bpy.data.objects:
                if ob.type != "MESH":
                    continue
                idx = [i for i, sl in enumerate(ob.material_slots)
                       if sl.material and sub in sl.material.name.lower()]
                if not idx:
                    continue
                ev = ob.evaluated_get(_deps)
                me = ev.data
                if len(me.vertices) != len(ob.data.vertices):
                    # evaluated mesh differs (a subsurf, say): use its own polys
                    pass
                vs = set()
                for poly in me.polygons:
                    if poly.material_index in idx:
                        vs.update(poly.vertices)
                for i in vs:
                    acc += ev.matrix_world @ me.vertices[i].co
                    n += 1
            return (acc / n, n) if n else (None, 0)

        _ca, _na = _mat_centre(_a)
        _cb, _nb = _mat_centre(_b)
        if _ca is not None and _cb is not None:
            _d = _ca - _cb
            print("  OFFSET %-22s %s(%d) - %s(%d) = (%+.4f,%+.4f,%+.4f)  |d|=%.4f"
                  % (stage, _a, _na, _b, _nb, _d.x, _d.y, _d.z, _d.length))
        else:
            print("  OFFSET %-22s %s=%d verts %s=%d verts -- nothing to compare"
                  % (stage, _a, _na, _b, _nb))

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


# VRM_KEEP_POSE=1 forces the decision below, the way VRM_NO_TPOSE and
# VRM_KEEP_GRIP force theirs. The heuristic reads the rig against the UNRIGGED
# meshes, so a character with nothing unrigged -- every mesh skinned or
# bone-parented, which is most of a Rigify file -- gives it nothing to measure
# and it declines by default. That is the right default and it is not always
# the right answer, so there has to be a way to say otherwise per character.
_keep_anim_pose = os.environ.get("VRM_KEEP_POSE") == "1"
if _keep_anim_pose:
    print("VRM_KEEP_POSE=1: keeping the file's pose and baking it into rest")
if _had_anim and not _keep_anim_pose:
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
# ZEROING a key is not the same as DELETING it, and this used to do the second
# while only needing the first. Everything above argues that the base mesh is
# what to MEASURE; none of it argues that the keys should not SHIP. A key at
# weight zero contributes nothing to the bounds, the renders or the game, and
# it is still there for anything that wants to drive it.
#
# Pomni is why it matters. Her irises are supposed to resize -- that is the
# character -- and her source carries 'Big' and 'Small' on Eye.L, 'Closed' on
# her lashes, and three doodle keys for her face. Every one was deleted at this
# line, and she exported with ZERO morph targets, so the eyes that are meant to
# animate could never move. Nothing downstream reported a loss, because by then
# there was nothing left to lose.
#
# Prix's corrupt key is a real hazard and it is not an argument for deleting
# all of them: it is an argument for spotting THAT one. It holds a body four
# times oversized, so measure each key's displacement against the mesh it
# belongs to and drop only the ones that are plainly broken.
#
# OPT-IN, because they are not free. Prix carries 37 keys on a 61k-vertex mesh
# and keeping them takes her from 8.6 MB to 28.3 MB -- 3.3x -- for morphs that
# are no part of her character and that nothing drives. Pomni's cost 2.6 -> 4.0
# MB and ARE her character. So VRM_KEEP_MORPHS=1 asks for them, per character,
# and the default stays as it was.
_MORPH_MAX = float(os.environ.get("VRM_MORPH_MAX_DISP", "0.5"))
# An eye-closing key is worth keeping even when the rest are not. It is ONE
# key, it is the only expression YARG drives, and dropping it is what left all
# 66 characters unable to blink. Defined here because the pass below has to
# know which keys to spare; the binding itself happens after the humanoid map.
# Not anchored at the start: Character Creator names them 'Eye_Blink_L' and
# 'Eye_Blink_R', so a start-anchored pattern finds nothing on an entire rig
# family. Still anchored at a WORD boundary, so 'Mouth_Close' -- which sits
# directly beside them on Heels' CC_Base_Body -- is not mistaken for an eye.
_BLINK_KEY = re.compile(r"(^|[_. -])(blink|wink)", re.I)
_BLINK_EXACT = re.compile(r"^(closed?|eye_?closed?)$", re.I)
_BLINK_MESH = re.compile(r"(lash|lid|eye|brow)", re.I)


# Visemes, for lipsync. Measured across the 28 characters built so far: NOT
# ONE had a single viseme bound, so lipsync could not work on any of them --
# not because the models lack the shapes but because this pass deleted them.
# Heels' source carries 420 shape keys including the whole Character Creator
# viseme set; what shipped was two, both blink.
#
# Keep the handful that are actually bound rather than all 420. That is the
# difference between a few hundred KB and Prix's 8.6 -> 28.3 MB.
#
# The mapping is phoneme-group to phoneme-group, so it is approximate by
# nature. Character Creator has no separate IH, so 'ih' and 'ee' both take
# V_Wide; that is a real limitation of the source set, not a guess that can be
# improved by picking a different key.
#
# VRM_NO_VISEMES=1 opts out, for a character whose size matters more than its
# mouth.
_VISEME_SPECS = (
    ("aa", (r"^V_Open$", r"^A$", r"^viseme_aa$", r"^mouth_?a$", r"^vrc\.v_aa$",
            r"^jawOpen$")),
    ("ee", (r"^V_Wide$", r"^E$", r"^viseme_E$", r"^mouth_?e$", r"^vrc\.v_e$")),
    ("ih", (r"^V_Wide$", r"^I$", r"^viseme_I$", r"^mouth_?i$", r"^vrc\.v_ih$")),
    ("oh", (r"^V_Tight_O$", r"^O$", r"^viseme_O$", r"^mouth_?o$", r"^vrc\.v_oh$")),
    ("ou", (r"^V_Tight$", r"^U$", r"^viseme_U$", r"^mouth_?u$", r"^vrc\.v_ou$")),
)
_VISEME_RE = [(_a, [re.compile(_p, re.I) for _p in _ps]) for _a, _ps in _VISEME_SPECS]


# VRM_VISEME="aa=Face/A,ee=Face/ClosedTeeth@0.8,..." maps presets BY HAND.
#
# A model can have a perfectly good mouth and still not match any naming
# convention. Pomni's face carries 'A', 'ClosedTeeth', 'ClosedTeethVariation'
# and 'OpenNoTeeth' -- real mouth shapes, named for an artist rather than for a
# phoneme set, and only 'A' is guessable.
#
# The weight suffix is what makes this more than a rename. A VRM morph target
# bind carries its own weight, so ONE open-mouth shape can serve several
# visemes at different openings. It does not invent lip rounding that the model
# has no geometry for: 'ou' driven from a wide-open mouth reads as "open less",
# not as rounded lips. It reads as talking, which is the point, and it is
# honest to say it is not accurate phonetics.
_VISEME_OVERRIDE = {}
for _spec in [x for x in os.environ.get("VRM_VISEME", "").split(",") if x.strip()]:
    _pre_name, _, _rest = _spec.partition("=")
    _ref, _, _w = _rest.partition("@")
    _mn, _, _kn = _ref.partition("/")
    _pre_name, _mn, _kn = _pre_name.strip(), _mn.strip(), _kn.strip()
    if _pre_name not in ("aa", "ih", "ou", "ee", "oh"):
        raise SystemExit("ABORT: VRM_VISEME names preset %r, which is not one "
                         "of aa/ih/ou/ee/oh" % _pre_name)
    _o = bpy.data.objects.get(_mn)
    if _o is None or not _o.data.shape_keys or _kn not in _o.data.shape_keys.key_blocks:
        raise SystemExit("ABORT: VRM_VISEME names %s/%s, which this file has "
                         "not got" % (_mn, _kn))
    _VISEME_OVERRIDE.setdefault((_mn, _kn), []).append(
        (_pre_name, float(_w) if _w.strip() else 1.0))


def _viseme_targets(_mesh_name, _key_name):
    """Which VRM preset expressions does this shape key feed, if any?

    Returns (preset, weight) pairs. An explicit VRM_VISEME mapping wins; the
    patterns are the fallback.

    Anchored patterns only. A loose 'mouth' match would catch the 70-odd
    Mouth_Smile / Mouth_Pucker shapes sitting beside the visemes on a CC body
    and bind an expression to a smirk.
    """
    _hit = _VISEME_OVERRIDE.get((_mesh_name, _key_name))
    if _hit:
        return list(_hit)
    if os.environ.get("VRM_NO_VISEMES") or _VISEME_OVERRIDE:
        # Once a character has been mapped by hand, guessing alongside it only
        # adds binds nobody asked for.
        return []
    return [(_a, 1.0) for _a, _ps in _VISEME_RE
            if any(_p.match(_key_name) for _p in _ps)]


def _is_blink(_mesh_name, _key_name):
    # search, not match: the pattern allows a leading separator because the
    # name is 'Eye_Blink_L', and match() anchors at position 0, so it found
    # nothing on an entire rig family while looking like it was working.
    return bool(_BLINK_KEY.search(_key_name)
                or (_BLINK_EXACT.match(_key_name)
                    and _BLINK_MESH.search(_mesh_name)))
# VRM_EXPR="Wide_eyed=Eye.L/Big;Squint=Eye.L/Small" -- shape keys to spare and
# expose as CUSTOM VRM expressions. YARG sets a custom expression whenever a
# lipsync event's type NAME equals the expression's name (VRMCharacter.cs
# TryGetExpressionKey(string)), and the chart generator emits Brow_*, Squint
# and Wide_eyed on its own. So a character's own facial keys can be reached
# without any change to the game, provided they are called by those names.
_EXPR = {}
for _part in [x for x in os.environ.get("VRM_EXPR", "").split(";") if x.strip()]:
    _en, _, _tgt = _part.partition("=")
    _mn, _, _kn = _tgt.strip().rpartition("/")
    _EXPR.setdefault(_en.strip(), []).append((_mn, _kn))
_EXPR_KEEP = {(m, k) for v in _EXPR.values() for m, k in v}
for o in meshes:
    sk = o.data.shape_keys
    if not sk or not sk.key_blocks:
        continue
    live = [(kb.name, round(kb.value, 3)) for kb in sk.key_blocks
            if abs(kb.value) > 1e-6]
    nkeys = len(sk.key_blocks)
    basis = [p.co.copy() for p in sk.key_blocks[0].data]
    bpy.context.view_layer.objects.active = o
    if not os.environ.get("VRM_KEEP_MORPHS"):
        _spare = [kb.name for kb in list(sk.key_blocks)[1:]
                  if _is_blink(o.name, kb.name)
                  or _viseme_targets(o.name, kb.name)
                  or (o.name, kb.name) in _EXPR_KEEP]
        for _kb in list(sk.key_blocks)[1:]:
            if _kb.name not in _spare:
                o.shape_key_remove(_kb)
        if not _spare:
            o.shape_key_clear()
        else:
            for _kb in sk.key_blocks:
                _kb.value = 0.0
            o.show_only_shape_key = False
            o.active_shape_key_index = 0
        for i, c in enumerate(basis):
            o.data.vertices[i].co = c
        o.data.update()
        print("  dropped %d shape keys on '%s', kept the base mesh%s%s"
              % (nkeys - len(_spare), o.name,
                 " and %s for the blink/viseme expressions" % _spare
                 if _spare else "",
                 " (IGNORED non-zero: %s)" % live if live else ""))
        continue
    _bb = [Vector(c) for c in o.bound_box]
    _diag = max((a - b).length for a in _bb for b in _bb) or 1.0
    _bad = []
    for _kb in list(sk.key_blocks)[1:]:
        _d = 0.0
        for _i, _pt in enumerate(_kb.data):
            if _i < len(basis):
                _d = max(_d, (_pt.co - basis[_i]).length)
        if _d > _diag * _MORPH_MAX:
            _bad.append((_kb.name, round(_d / _diag, 2)))
            o.shape_key_remove(_kb)
    for _kb in sk.key_blocks:
        _kb.value = 0.0
    o.show_only_shape_key = False
    o.active_shape_key_index = 0
    for i, c in enumerate(basis):
        o.data.vertices[i].co = c
    o.data.update()
    print("  shape keys on '%s': kept %d at weight 0 (the engine's own value)%s%s"
          % (o.name, len(sk.key_blocks) if sk.key_blocks else 0,
             ", dropped %s as corrupt -- displaced more than %.0f%% of the mesh"
             % (_bad, _MORPH_MAX * 100) if _bad else "",
             " (author had non-zero: %s)" % live if live else ""))

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
    # Force the ARMATURE to rebuild from its edit bones.
    #
    # Transforming arm.data moves the rest bones, and view_layer.update() does
    # NOT rebuild the evaluated pose from them: pose_bone.head keeps returning
    # the positions from before the transform. Every later measurement taken in
    # pose space then describes a skeleton that no longer exists.
    #
    # That is what made the facing turn so destructive. Judy Hopps faces +Y, so
    # she is turned 180 degrees about Z, and immediately afterwards her left
    # upper arm read POSE +0.0748 against REST -0.0748 -- mirror images, with an
    # identity matrix_basis, no constraints and an identity object matrix. The
    # T-pose step measures the pose, decides the arm is on +X, and then rotates
    # a bone whose rest is on -X, so the arm ends up rooted on one side and
    # reaching across to the other. Her span came out 0.429 m on a 1.05 m body
    # instead of 0.729, and Power Girl's 1.150 on 1.800. Measuring the side more
    # cleverly could never have fixed it: the measurement was right and the
    # skeleton under it was stale.
    #
    # A trip through edit mode is what actually refreshes it.
    _act = bpy.context.view_layer.objects.active
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = _act
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
            # shape_keys=True or the keys stay where the vertices no longer
            # are. Mesh.transform defaults to leaving them behind, and a mesh
            # with keys is EVALUATED from the keys -- so the divergence is
            # invisible in any render and shows up only as mesh DATA and
            # evaluated bounds disagreeing.
            o.data.transform(_D, shape_keys=True)
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
    # use_deform is not a setting for bone heat; it is the armature's own
    # switch, and clearing it stops the bone deforming ANYTHING -- including
    # the meshes that were already rigged and perfectly weighted before this
    # step ran. It was never turned back on.
    #
    # Jessica Rabbit is the measured case. Her rig carries 160 bones and this
    # takes 73 of them out, leaving 87. Her body is weighted to those 73 as
    # well, so every vertex weighted only to a disabled bone stopped deforming
    # and stayed at its rest position: her evaluated box went from z
    # 0.47..11.65 to 0.47..43.61 at this stage, half of her standing and half
    # of her still in the bind pose. The scale step then measured a figure
    # nearly four times too tall and squashed her to 0.08 m wide.
    #
    # Nothing caught it because every count stayed right: the build reported a
    # verified height, a full 52/52 humanoid and every mesh skinned, and the
    # character was ruined. So restore the flags the moment bone heat is done
    # with them.
    _deform_was = [b.name for b in arm.data.bones if b.use_deform]
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
    _restored = 0
    for _n in _deform_was:
        _b = arm.data.bones.get(_n)
        if _b is not None and not _b.use_deform:
            _b.use_deform = True
            _restored += 1
    if _restored:
        bpy.context.view_layer.update()
        print("  restored use_deform on %d bone(s) that were switched off only "
              "so bone heat would ignore them -- leaving them off stops them "
              "deforming the meshes that were ALREADY rigged" % _restored)
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
    # Same again. This is the one that caught Pomni: her lashes carry a
    # 'Closed' key, this step put them into the armature's space without it,
    # and her mesh DATA then measured 1.3949 m against a 1.70 m target -- the
    # height guard fired on lashes whose vertices had moved and whose keys had
    # not. Before the keys were kept there was nothing to desync, so this line
    # was correct for exactly as long as the keys were being thrown away.
    _o.data.transform(_D, shape_keys=True)
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
    # Rigify deform bones. Chest and upperChest are left unmapped -- both are
    # optional in VRM.
    #
    # The neck and head are NOT at fixed indices. Rigify names a spine chain
    # DEF-spine, DEF-spine.001, ... and the head is whatever the chain ends on,
    # which depends on how many spine bones the rigger drew. This was hardcoded
    # to .004 and .005, read off the first rig that needed it, and it is wrong
    # on any chain that does not happen to stop at .005: Tenna and Gadget
    # Hackwrench both run to DEF-spine.006, so both had their HEAD mapped to
    # their neck, their neck mapped to the bone below it, and the actual skull
    # bone -- 41 cm of it on a 1.30 m Gadget -- left out of the humanoid
    # entirely. Head-look then pivots at the throat.
    #
    # Nothing caught it because the map was complete and self-consistent: every
    # bone it named existed, the readback matched, and a mis-mapping is only
    # visible if you ask where the bone IS. So count the chain instead.
    _sp = sorted(int(_n.split(".")[1]) for _n in bone_names
                 if _n.startswith("DEF-spine.") and _n.split(".")[-1].isdigit())
    _top = _sp[-1] if _sp else 5
    MAP = {"hips": "DEF-spine", "spine": "DEF-spine.001",
           "neck": ("DEF-neck" if "DEF-neck" in bone_names
                    else "DEF-spine.%03d" % max(_top - 1, 2)),
           "head": ("DEF-head" if "DEF-head" in bone_names
                    else "DEF-spine.%03d" % _top)}
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
elif RIG == "mandousd":
    # The Fortnite Mandalorian's USDZ. Blender reads it natively, and unlike the
    # glTF of the same pack its skeleton is REAL: 150 bones, 121 of them
    # deforming, sitting 0.08 inside a body 0.84 wide. The glTF's is collapsed --
    # foot bone and head bone two units apart on a 144-unit mesh -- which is why
    # that route needed Mixamo and a mesh join at all.
    #
    # Numbered bones again, so the map comes off the hierarchy and the rest
    # positions. Mando hangs entirely off root n29; Grogu has his own root n101,
    # along with the cradle, jetpack and rifle, and those meshes are excluded.
    # Up is -Y here: the head sits at y=-144 and the feet at y=-10.
    MAP = {"hips": "n29", "spine": "n30", "chest": "n31",
           "upper_chest": "n32", "neck": "n36", "head": "n37"}
    for s_, sh, ua, la, hd, ul, ll, ft, to, th, f1, f2, f3, f4 in (
            ("left", "n39", "n40", "n41", "n42", "n90", "n91", "n92", "n93",
             46, 62, 58, 54, 50),
            ("right", "n66", "n67", "n68", "n69", "n95", "n96", "n97", "n98",
             70, 86, 82, 78, 74)):
        MAP["%s_shoulder" % s_] = sh
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = hd
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
        MAP["%s_toes" % s_] = to
        MAP["%s_thumb_metacarpal" % s_] = "n%d" % th
        MAP["%s_thumb_proximal" % s_] = "n%d" % (th + 1)
        MAP["%s_thumb_distal" % s_] = "n%d" % (th + 2)
        # The four chains run in Z across the hand; the one nearest the thumb is
        # the index. Each is three bones, which is exactly what VRM wants.
        for _f, _b in (("index", f1), ("middle", f2), ("ring", f3), ("little", f4)):
            MAP["%s_%s_proximal" % (s_, _f)] = "n%d" % _b
            MAP["%s_%s_intermediate" % (s_, _f)] = "n%d" % (_b + 1)
            MAP["%s_%s_distal" % (s_, _f)] = "n%d" % (_b + 2)
elif RIG == "judyusd":
    # A USDZ whose bones are called 'n13', 'n14' ... and carry no information at
    # all, so the map is read off the hierarchy, the rest positions and what
    # each bone actually deforms: 123 bones, of which only 56 deform anything --
    # the rest are a subtree of zero-length controls parked at the origin.
    #
    # Y is up in this file, so the sides come off X and the chain off Y. Both
    # shoulders hang off the NECK rather than the chest, which is the 3ds Max
    # Biped trap the hierarchy repair already knows how to fix.
    #
    # Her fingers are two-bone chains where VRM wants three, so they are left
    # unmapped: a finger mapped to the wrong joint is worse than no finger. Her
    # ears are two five-bone chains and want spring bones -- pass
    # '^n(29|3[0-8])$' as the spring pattern, since nothing in the names says
    # "ear".
    MAP = {"hips": "n14", "spine": "n15", "chest": "n26",
           "neck": "n27", "head": "n28"}
    # LEFT and RIGHT were the wrong way round here, and that is what "Judy's
    # arms and legs are criss-crossed" was. Her ankle sits at z=+15.55 and her
    # toes at z=-16.81, so she faces -Z, which puts her left at +X -- and n21,
    # at x=-20.44, was mapped as her left leg.
    #
    # Nothing caught it because nothing looked: this map predates the sides
    # check, and neither of her build logs has a 'sides:' line at all. Asked
    # afterwards, that check answers "4 of 4 limb pairs are mirrored", which is
    # an entirely separate mechanism agreeing with the geometry.
    for s_, sh, ua, la, hd, ul, ll, ft, to in (
            ("right", "n76", "n77", "n78", "n79", "n21", "n22", "n23", "n24"),
            ("left", "n47", "n48", "n49", "n50", "n16", "n17", "n18", "n19")):
        MAP["%s_shoulder" % s_] = sh
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = hd
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
        MAP["%s_toes" % s_] = to
elif RIG == "kronkusd":
    # Another numbered USDZ rig, and it fits NONE of the families above -- the
    # dcseries/shaggyusd finder wants a parentless 'nNNN' bone with three or
    # more children as the hips, and Kronk's root 'n6' has exactly one. His
    # hips are two levels down.
    #
    # 87 bones, of which 58 carry weight: the other 29 are zero-length tips all
    # parked on the root's own position, so a bone with no vertex group here is
    # a stub and not a joint.
    #
    # THE FRAME IS INVERTED. His import maps USD +Y onto world -Z, so he hangs
    # upside down in world space: feet at z=+0.05, head at z=-2.70, and HEIGHT
    # is -z. Every position below is read that way. Reading it the other way up
    # maps the pelvis to the skull and everything after it is nonsense.
    #
    # SIDES ARE MEASURED, not assumed -- this is the trap that criss-crossed
    # Judy's arms and legs. His toes sit at greater world Y than his ankles on
    # both legs (n15 +0.072 against n14 -0.025; n20 +0.131 against n19 +0.021),
    # so he faces +Y. With up at -Z that puts his LEFT at +X, which is the n12
    # leg and the n67 arm. Check it with limb_check.py after building: it should
    # answer 4 of 4 limb pairs mirrored.
    #
    # His fingers are three two-bone chains per hand where VRM wants three
    # bones, so they are left unmapped, exactly as Judy's are: a finger mapped
    # to the wrong joint is worse than no finger.
    #
    # He has no neck bone -- chest n23 carries straight into head n24, which is
    # also the heaviest bone in the file (326 of the weight) and the parent of
    # 18 face and hair stubs.
    MAP = {"hips": "n11", "spine": "n22", "chest": "n23", "head": "n24"}
    for s_, sh, ua, la, hd, ul, ll, ft, to in (
            ("left", "n67", "n68", "n69", "n70", "n12", "n13", "n14", "n15"),
            ("right", "n80", "n81", "n82", "n83", "n17", "n18", "n19", "n20")):
        MAP["%s_shoulder" % s_] = sh
        MAP["%s_upper_arm" % s_] = ua
        MAP["%s_lower_arm" % s_] = la
        MAP["%s_hand" % s_] = hd
        MAP["%s_upper_leg" % s_] = ul
        MAP["%s_lower_leg" % s_] = ll
        MAP["%s_foot" % s_] = ft
        MAP["%s_toes" % s_] = to
    # Every name is checked to exist, so a file this does not fit aborts rather
    # than mapping a leg to a finger -- the same guard the dcseries table has.
    _missing = [b for b in MAP.values() if b not in arm.data.bones]
    if _missing:
        raise SystemExit("ABORT: rig 'kronkusd' does not fit this file -- missing %s"
                         % ", ".join(sorted(_missing)))
elif RIG in ("dcseries", "shaggyusd"):
    # More numbered bones, and this time they come in a family. The Peacemaker
    # and Vigilante rips are the SAME rig: identical tree, identical rest
    # positions to three decimals, and names that are bare numbers offset by a
    # constant -- Peacemaker's hips are 'n115' and Vigilante's are 'n8', with
    # every other bone the same distance behind. Shaggy is a second rig of the
    # same numbered kind, with a fuller skeleton: an upper chest, toes, and
    # three-bone thumbs, which is the whole 52-slot humanoid.
    #
    # So each is a table of OFFSETS from the hips, and the hips are found rather
    # than named: the parentless bone with three children, which is the only
    # thing in a numbered rig that can be the junction of a spine and two legs.
    # Every name the table then produces is checked to exist, so a file this
    # does not actually fit aborts instead of mapping a leg to a finger.
    _cands = [b for b in arm.data.bones
              if b.parent is None and re.match(r"^n\d+$", b.name)
              and len(b.children) >= 3]
    if not _cands:
        raise SystemExit("ABORT: rig '%s' expects a parentless 'nNNN' bone with "
                         "three children (spine + two legs) and this file has "
                         "none -- it is not this rig" % RIG)
    _root = max(_cands, key=lambda b: len(b.children_recursive))
    _B = int(_root.name[1:])
    print("  %s: hips is %s, so the rig is based at %d" % (RIG, _root.name, _B))
    if RIG == "dcseries":
        # Five body bones -- no upper chest -- and legs that stop at the foot.
        _BODY = (("hips", 0), ("spine", 1), ("chest", 2),
                 ("neck", 3), ("head", 4))
        _LIMB = (("shoulder", 6), ("upper_arm", 7), ("lower_arm", 8),
                 ("hand", 9), ("upper_leg", 72), ("lower_leg", 73),
                 ("foot", 74))
        # The four fingers run in Z across the hand and the one nearest the
        # thumb is the index; the little finger is also the shortest chain,
        # which agrees. The thumb is only TWO bones, and the first of them
        # starts at the palm rather than out at the knuckles, so it is the
        # metacarpal and the distal joint is simply absent. Leaving it out is
        # the point -- a finger bone mapped to the wrong joint is worse than a
        # missing one.
        _FING = (("index", 16), ("middle", 10), ("ring", 33), ("little", 22))
        _THUMB, _THUMB_N, _SIDE = 28, 2, 33
        _LEG_SIDE = 4
    else:
        _BODY = (("hips", 0), ("spine", 1), ("chest", 2), ("upper_chest", 3),
                 ("neck", 4), ("head", 5))
        _LIMB = (("shoulder", 7), ("upper_arm", 8), ("lower_arm", 9),
                 ("hand", 10), ("upper_leg", 55), ("lower_leg", 56),
                 ("foot", 57), ("toes", 58))
        _FING = (("index", 15), ("middle", 19), ("ring", 23), ("little", 27))
        _THUMB, _THUMB_N, _SIDE = 11, 3, 24
        _LEG_SIDE = 5
    for _k, _o in _BODY:
        MAP[_k] = "n%d" % (_B + _o)
    for _s, _d in (("left", 0), ("right", 1)):
        for _k, _o in _LIMB:
            _step = _LEG_SIDE if _k.endswith("leg") or _k in ("foot", "toes") \
                else _SIDE
            MAP["%s_%s" % (_s, _k)] = "n%d" % (_B + _o + _d * _step)
        _t = _B + _THUMB + _d * _SIDE
        for _j, _k in enumerate(("metacarpal", "proximal", "distal")[:_THUMB_N]):
            MAP["%s_thumb_%s" % (_s, _k)] = "n%d" % (_t + _j)
        for _f, _o in _FING:
            _n = _B + _o + _d * _SIDE
            for _j, _k in enumerate(("proximal", "intermediate", "distal")):
                MAP["%s_%s_%s" % (_s, _f, _k)] = "n%d" % (_n + _j)
    _missing = sorted(k for k, v in MAP.items() if v not in bone_names)
    if _missing:
        raise SystemExit("ABORT: rig '%s' based at %d wants %d bone(s) this "
                         "file has not got, so the base is wrong or this is a "
                         "different rig: %s"
                         % (RIG, _B, len(_missing),
                            ", ".join("%s=%s" % (k, MAP[k]) for k in _missing)))
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

# 2b. A HIPS THAT SITS ON THE FLOOR.
#
#    The hips are found as the junction of a spine and two legs, which is right
#    whenever the legs hang off the pelvis. Where they hang off the ARMATURE
#    ROOT instead, the only bone that qualifies is that root -- and it is on the
#    floor. Gadget Hackwrench mapped hips to a bone literally called 'root' at
#    0.6% of her height, against 0.41 to 1.07 for all 142 other built files, and
#    the nearest healthy rig is at 0.405, so 0.25 separates them with room.
#
#    It passes every static check. The bind pose never consults the humanoid
#    map, so she rendered perfectly; in game Unity pivots the whole body about a
#    floor-level hips, which whips the head and her hair springs turn that into
#    a spike. Her screenshot was read as a collider fault and then as a weighting
#    fault before this was measured.
#
#    The repair below already re-parents the legs onto whatever hips ends up
#    being, so the only thing needed here is to choose the right bone: the
#    parent of the mapped spine, which is the pelvis by construction.
_h, _sp = MAP.get("hips"), MAP.get("spine")
if _h in bone_names and _sp in bone_names:
    _zs = [arm.data.bones[b].head_local.z for b in MAP.values() if b in bone_names]
    _span = (max(_zs) - min(_zs)) if _zs else 0.0
    if _span > 1e-6:
        _hf = (arm.data.bones[_h].head_local.z - min(_zs)) / _span
        if _hf < 0.25:
            _cand = arm.data.bones[_sp].parent
            _cf = ((_cand.head_local.z - min(_zs)) / _span) if _cand else -1.0
            # The candidate must be UNDER the old hips, or re-parenting the legs
            # onto it would lift them out of the skeleton entirely.
            _under = _cand is not None and _h in _ancestry(_cand.name)
            if _cand is not None and _cand.name != _h and _cf >= 0.25 and _under:
                print("  hips '%s' sits at %.1f%% of height, which is the floor -- "
                      "promoting '%s' at %.1f%% (the parent of the mapped spine); "
                      "the legs are re-parented onto it below"
                      % (_h, 100 * _hf, _cand.name, 100 * _cf))
                MAP["hips"] = _cand.name
            else:
                # Say so rather than shipping a floor-level hips in silence.
                print("  WARNING hips '%s' sits at %.1f%% of height, which looks like "
                      "the armature root, and no better candidate was found "
                      "(parent of spine: %s at %.1f%%, under old hips: %s)"
                      % (_h, 100 * _hf, _cand.name if _cand else None,
                         100 * _cf, _under))

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
# The feet are only a good forward signal while the feet are not themselves
# posed. Jessica Rabbit is the case against: she is a posed statue, feet
# crossed in heels, and her toe direction came out (1.00, -0.02, 0.00) --
# within 2 degrees of her own SHOULDER LINE. No body stands like that; feet
# point across the shoulders, not along them. Aligning her by the feet turned
# her 89 degrees and shipped her in profile, and because the arm straightening
# afterwards works per-arm from its own side, the arms still came out along X
# and nothing downstream noticed.
#
# So cross-check the feet against something posing cannot move. The heads of
# the shoulder bones sit at the collarbone roots beside the spine: they are
# where the arm STARTS, not where it points, so they stay put however the arm
# is posed. That gives the left-right axis outright, and forward is
# perpendicular to it.
#
# A perpendicular has two directions, and the feet cannot break the tie when it
# was the feet that were wrong. The knees can: a leg bends forward, so the knee
# sits in front of the line from hip to ankle. That is a rest-pose property of
# every biped rig here, and it is read BEFORE the legs are straightened a few
# steps below, while the bend is still there to measure.
def _flat(v):
    v = Vector((v.x, v.y, 0.0))
    return v.normalized() if v.length > 1e-6 else None


_lat = None
for _a, _b in (("left_shoulder", "right_shoulder"),
               ("left_upper_arm", "right_upper_arm")):
    _l, _r = MAP.get(_a), MAP.get(_b)
    if _l in bone_names and _r in bone_names:
        _lat = _flat(arm.data.bones[_l].head_local - arm.data.bones[_r].head_local)
        if _lat is not None:
            break

_knee = Vector((0.0, 0.0, 0.0))
for _s in ("left", "right"):
    _h, _k, _f = (MAP.get("%s_upper_leg" % _s), MAP.get("%s_lower_leg" % _s),
                  MAP.get("%s_foot" % _s))
    if _h in bone_names and _k in bone_names and _f in bone_names:
        _mid = (arm.data.bones[_h].head_local + arm.data.bones[_f].head_local) / 2.0
        _kv = _flat(arm.data.bones[_k].head_local - _mid)
        if _kv is not None:
            _knee += _kv
_knee = _flat(_knee) if _knee.length > 1e-6 else None

if _lat is not None and _fwd.length > 1e-6:
    _par = abs(_flat(_fwd).dot(_lat))
    if _par > 0.707:
        _perp = Vector((_lat.y, -_lat.x, 0.0)).normalized()
        if _knee is not None and abs(_knee.dot(_perp)) > 0.3:
            _new = _perp if _knee.dot(_perp) > 0 else -_perp
            print("  facing: the feet point %s, which is %.0f deg off this "
                  "rig's own shoulder line -- feet do not point along the "
                  "shoulders, so they are posed. Taking forward from the "
                  "shoulders instead, %s, with the knees breaking the tie."
                  % (tuple(round(v, 2) for v in _fwd),
                     math.degrees(math.acos(min(1.0, _par))),
                     tuple(round(v, 2) for v in _new)))
            _fwd = _new
        else:
            print("  facing: the feet point along the shoulder line and the "
                  "knees do not say which way is front -- leaving the "
                  "orientation alone rather than guessing")
            _fwd = Vector((0.0, 0.0, 0.0))

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
        # VRM_STANDUP_LEGS=0 keeps only the rigid rotation and skips the legs.
        # Straightening a leg is a DEFORMATION, and on a model whose weights
        # came from automatic weighting of a contorted pose it is the
        # deformation that tears: Anakin's legs smear while his arms come out
        # clean, because his knee was folded against his chest when it was
        # bound. His legs are already apart, so for an upload that is only going
        # to be re-rigged elsewhere there is nothing to gain by moving them.
        for _s in (() if os.environ.get("VRM_STANDUP_LEGS") == "0"
                   else ("left", "right")):
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


# Which way is +X for THIS model? Ask the arms, not their names.
#
# "Left" is the modeller's label and +X is this pipeline's convention, and the
# facing step turns a character that faces the wrong way 180 degrees about Z,
# which swaps them. Straightening an arm toward the wrong side sweeps it ACROSS
# the body instead of outward and roughly halves the span.
#
# This is only answerable now that flatten() rebuilds the armature: until it
# did, pose space and rest space disagreed by exactly this 180 degrees, so the
# measurement said one thing and the bone it governed was the other way round.
# Compare the two upper arms with each other rather than against the spine --
# the hips bone is not always centred, and on Power Girl it is not.
if len(_arms) == 2:
    _x = {sd: arm.pose.bones[ua].head.x for sd, _s, ua, _l, _h in _arms}
    if abs(_x["left"] - _x["right"]) > 1e-5:
        _lx = 1.0 if _x["left"] > _x["right"] else -1.0
        if _lx != 1.0:
            print("  arms: this model's LEFT is -X (upper arms at %.3f / %.3f) "
                  "-- straightening each arm outward from its own side"
                  % (_x["left"], _x["right"]))
        _arms = [(sd, (_lx if sd == "left" else -_lx), ua, la, hd)
                 for sd, _s, ua, la, hd in _arms]

# Legs, on the same terms as the arms.
#
# Straightening a leg already exists -- _straighten_axis against -Z -- but only
# inside the stand-up path, which is opt-in AND requires the spine to lie more
# than 25 degrees off vertical. Jessica Rabbit stands perfectly upright with
# her legs CROSSED at the microphone, so that gate can never reach her, and she
# baked a crossed-leg bind that every animation in the game would then deform
# from.
#
# Measured the same way the arms are, and acted on only when a leg is really
# bent: VRM_STRAIGHTEN_LEGS=1 asks for it, because straightening a leg is a
# DEFORMATION and on weights taken from a contorted pose it is the deformation
# that tears -- the reason the stand-up path says the same thing about Anakin.
_DOWNV = Vector((0.0, 0.0, -1.0))
_legs = []
for _s in ("left", "right"):
    _ul, _ll = MAP.get("%s_upper_leg" % _s), MAP.get("%s_lower_leg" % _s)
    _ft = MAP.get("%s_foot" % _s)
    if _ul in bone_names and _ll in bone_names:
        _legs.append((_s, _ul, _ll, _ft if _ft in bone_names else None))
_leg_off = 0.0
for _s, _ul, _ll, _ft in _legs:
    _leg_off = max(_leg_off, _axis_error(_ul, _ll, _DOWNV)[0])
if _legs:
    print("  legs: worst thigh is %.1f deg off vertical%s"
          % (_leg_off,
             "" if os.environ.get("VRM_STRAIGHTEN_LEGS")
             else " (VRM_STRAIGHTEN_LEGS=1 straightens them)"))

if (not os.environ.get("VRM_NO_TPOSE")) and (
        any(_arm_error(_ua, _hd, _sx)[0] >= 15.0
            for _, _sx, _ua, _la, _hd in _arms)
        or (os.environ.get("VRM_STRAIGHTEN_LEGS") and _leg_off >= 15.0)):
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
    if os.environ.get("VRM_STRAIGHTEN_LEGS") and _leg_off >= 15.0:
        for _s, _ul, _ll, _ft in _legs:
            _f1 = _straighten_axis(_ul, _ul, _ll, _DOWNV)
            _f2 = (_straighten_axis(_ll, _ll, _ft, _DOWNV) if _ft else 0.0)
            print("  T-pose: %s leg thigh now %.1f deg off vertical, shin %.1f "
                  "('%s' / '%s')" % (_s, _f1, _f2, _ul, _ll))
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
        # One blended skinning matrix per vertex. Linear blending is a weighted
        # sum of the bone matrices, so it can be applied to ANY coordinate set,
        # and that is the point: a mesh that keeps shape keys is evaluated from
        # the KEY BLOCKS, not from vertices[].co. Writing only .co left every
        # keyed mesh (blink and viseme keys) in its old pose while the skeleton
        # went to T, which put the finger bones 20-33 cm from their own fingers
        # on Heels, Alice Ivy, Alastor and Chibi Rem: the hand animation then
        # swung each finger about a pivot far from it and threw it out as a
        # long thin strip.
        _mats = []
        for _v in _o.data.vertices:
            _M = None
            _tot = 0.0
            for _g in _v.groups:
                _pb = arm.pose.bones.get(_g2n.get(_g.group, ""))
                if _pb is None or _g.weight <= 0.0:
                    continue
                _m1 = (_pb.matrix @ _pb.bone.matrix_local.inverted()) * _g.weight
                _M = _m1 if _M is None else _M + _m1
                _tot += _g.weight
            _mats.append(_M * (1.0 / _tot) if (_M is not None and _tot > 1e-9) else None)
        if _o.data.shape_keys:
            for _kb in _o.data.shape_keys.key_blocks:
                for _i, _pt in enumerate(_kb.data):
                    if _i < len(_mats) and _mats[_i] is not None:
                        _pt.co = _mats[_i] @ _pt.co
        for _v, _M in zip(_o.data.vertices, _mats):
            if _M is not None:
                _v.co = _M @ _v.co
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

# ---------------------------------------------------------------- drop material faces
# VRM_DROP_MATERIAL_FACES="Material.001;..." deletes every face that uses a named material, and
# the vertices only they used. For a toon outline shell: an untextured, slightly larger copy of the
# body that is meant to be drawn inside-out. The game's renderer has screen-space ambient occlusion,
# soft shadows and per-pixel lights that a plain editor render does not, and a second layer hugging
# the body is the first suspect when a coat reads as inside-out only in game.
_DROPMAT = [x.strip() for x in os.environ.get("VRM_DROP_MATERIAL_FACES", "").split(";") if x.strip()]
if _DROPMAT:
    import bmesh
    for _o in meshes:
        _bm = bmesh.new()
        _bm.from_mesh(_o.data)
        _kill = [f for f in _bm.faces
                 if f.material_index < len(_o.material_slots)
                 and _o.material_slots[f.material_index].material
                 and _o.material_slots[f.material_index].material.name in _DROPMAT]
        if _kill:
            _n0 = len(_bm.faces)
            bmesh.ops.delete(_bm, geom=_kill, context='FACES')
            bmesh.ops.delete(_bm, geom=[v for v in _bm.verts if not v.link_faces], context='VERTS')
            _bm.to_mesh(_o.data)
            _o.data.update()
            print("  dropped %d of %d faces using %s on '%s'" % (len(_kill), _n0, _DROPMAT, _o.name))
        _bm.free()

# ---------------------------------------------------------------- flip faces
# Clothing and skin modelled INSIDE-OUT behind an outline hull draws as its far interior the
# moment the hull is dropped or the renderer culls back faces. Two ways to turn it round, both of
# which reverse the winding AND the split normals together.
#
# VRM_FLIP_FACES="MeshName:z<0.9;Other:z<0.3" reverses every face of the named mesh whose centre
# sits below that height (metres, after scaling): the blunt tool, for a region you can name.
#
# VRM_ORIENT_OUTWARD="Body.001@0.25" does it from the data. For each mesh, material and DRIVING
# BONE (the bone carrying most of a face's weight) it measures how many faces point away from the
# nearest point of that bone, and flips the whole group when fewer than the given share do. Whole
# groups, never single faces, so a limb turns round together; groups between the threshold and
# the point where they read as correct are left alone (a double-layered coat is half in, half out
# and must not be touched). Alastor: forearms, hands, head, spine 0-8% outward before.
from mathutils import Vector as _Vec


def _flip_faces(_o, _flip_poly):
    import bmesh
    _me = _o.data
    _hadc = _me.has_custom_normals
    if _hadc:
        _new = [v.vector.copy() for v in _me.corner_normals]
        for _p in _me.polygons:
            if _p.index in _flip_poly:
                for _li in _p.loop_indices:
                    _new[_li] = -_new[_li]
    _bm = bmesh.new()
    _bm.from_mesh(_me)
    _bm.faces.ensure_lookup_table()
    bmesh.ops.reverse_faces(_bm, faces=[_bm.faces[i] for i in _flip_poly])
    _bm.to_mesh(_me)
    _bm.free()
    if _hadc:
        # reverse_faces reverses each flipped face's loop order, so remap the negated normals the
        # same way: loop k of a flipped face is now its old loop (n-k) mod n.
        _out = list(_new)
        for _p in _me.polygons:
            if _p.index in _flip_poly:
                _ls = list(_p.loop_indices)
                _n = len(_ls)
                for _k, _li in enumerate(_ls):
                    _out[_li] = _new[_ls[(_n - _k) % _n]]
        _me.normals_split_custom_set(_out)
    _me.update()


_FLIP = []
for _part in [x for x in os.environ.get("VRM_FLIP_FACES", "").split(";") if x.strip()]:
    _mn, _, _cond = _part.partition(":")
    _FLIP.append((_mn.strip(), float(_cond.strip().replace("z<", ""))))
for _o in meshes:
    for _mn, _zmax in _FLIP:
        if _o.name != _mn:
            continue
        _mw = _o.matrix_world
        _fp = set(p.index for p in _o.data.polygons if (_mw @ p.center).z < _zmax)
        _flip_faces(_o, _fp)
        print("  flipped %d of %d faces of '%s' below z=%.2f" % (len(_fp), len(_o.data.polygons), _o.name, _zmax))

_ORIENT = {}
for _part in [x for x in os.environ.get("VRM_ORIENT_OUTWARD", "").split(";") if x.strip()]:
    _mat, _, _thr = _part.partition("@")
    _ORIENT[_mat.strip()] = float(_thr) if _thr.strip() else 0.25
if _ORIENT:
    import collections as _col
    _amw = arm.matrix_world
    _seg = {b.name: (_amw @ b.head_local, _amw @ b.tail_local) for b in arm.data.bones}

    def _near(_pt, _a, _b):
        _ab = _b - _a
        _t = 0.0 if _ab.length_squared == 0 else max(0.0, min(1.0, (_pt - _a).dot(_ab) / _ab.length_squared))
        return _a + _ab * _t

    for _o in meshes:
        _me = _o.data
        _mw = _o.matrix_world
        _n3 = _mw.to_3x3()
        _gn = {g.index: g.name for g in _o.vertex_groups}
        _grp = _col.defaultdict(lambda: [[], 0])
        for _p in _me.polygons:
            _slot = _p.material_index
            _mat = _o.material_slots[_slot].material if _slot < len(_o.material_slots) else None
            if not _mat or _mat.name not in _ORIENT:
                continue
            _w = _col.Counter()
            for _vi in _p.vertices:
                for _g in _me.vertices[_vi].groups:
                    _w[_gn.get(_g.group, "")] += _g.weight
            _best = next((b for b, _ in _w.most_common() if b in _seg), None)
            if _best is None:
                continue
            _c = _mw @ _p.center
            _out = _c - _near(_c, *_seg[_best])
            if _out.length < 0.01:
                continue
            _g2 = _grp[(_mat.name, _best)]
            _g2[0].append(_p.index)
            if (_n3 @ _p.normal).normalized().dot(_out.normalized()) > 0:
                _g2[1] += 1
        _fp = set()
        _names = []
        for (_mn2, _bn), (_idx, _outn) in _grp.items():
            if len(_idx) >= 40 and _outn / len(_idx) < _ORIENT[_mn2]:
                _fp.update(_idx)
                _names.append("%s %d" % (_bn, len(_idx)))
        if _fp:
            _flip_faces(_o, _fp)
            print("  oriented %d faces outward on '%s' (%s)" % (_fp.__len__(), _o.name, ", ".join(_names)))

# VRM_ORIENT_CONSISTENT="Body.001;Other" is the per-piece version, and the better one. A GROUP
# rule cannot be right when a group is mixed: flipping a mostly-inverted group also flips the
# faces that were already correct, and those vanish under back-face culling (patches missing from
# gloves and cuffs); leaving a mixed group alone leaves its inverted half inside-out (a coat
# skirt). So work on connected pieces of surface instead. 1) Join faces that share an edge
# (vertices welded by position, so UV seams do not split a piece) and propagate ONE winding
# through each piece, so neighbours agree. 2) Then decide each piece as a whole: flip it when
# fewer than half of its faces point away from their driving bone.
if os.environ.get("VRM_ORIENT_CONSISTENT", "").strip():
    import collections as _c2
    _names = set(x.strip() for x in os.environ["VRM_ORIENT_CONSISTENT"].split(";") if x.strip())
    _amw2 = arm.matrix_world
    _seg2 = {b.name: (_amw2 @ b.head_local, _amw2 @ b.tail_local) for b in arm.data.bones}

    def _near2(_pt, _a, _b):
        _ab = _b - _a
        _t = 0.0 if _ab.length_squared == 0 else max(0.0, min(1.0, (_pt - _a).dot(_ab) / _ab.length_squared))
        return _a + _ab * _t

    for _o in meshes:
        _me = _o.data
        _mw = _o.matrix_world
        _n3 = _mw.to_3x3()
        _gn = {g.index: g.name for g in _o.vertex_groups}
        # EVERY face of the mesh takes part in the connectivity, so a small shell that touches faces
        # of another material is judged as the closed piece it is, not as an open sheet. Only pieces
        # that contain a face of a NAMED material are oriented.
        _polys = list(_me.polygons)
        _listed = set(p.index for p in _polys
                      if p.material_index < len(_o.material_slots)
                      and _o.material_slots[p.material_index].material
                      and _o.material_slots[p.material_index].material.name in _names)
        if not _listed:
            continue
        # Weld by position so UV seams do not cut a piece in two. NOT by rounding: two vertices that
        # should coincide can straddle a rounding boundary after the build's scaling, and a shell then
        # splits at the seam into fragments that each look open and are judged separately (a closed
        # 30-face solid on Alastor's head came out as an 8-face and a 12-face piece, flipped piecemeal).
        # A nearest-neighbour weld has no boundary to straddle. The tolerance is 0.1 mm: the same shell was
        # still in fragments at 0.02 mm, and the exported file joins it at 0.1 mm.
        from mathutils import kdtree as _kdt
        _used = sorted(set(v for p in _polys for v in p.vertices))
        _kd = _kdt.KDTree(len(_used))
        for _i, _v in enumerate(_used):
            _kd.insert(_me.vertices[_v].co, _i)
        _kd.balance()
        _par = list(range(len(_used)))

        def _find(_a):
            while _par[_a] != _a:
                _par[_a] = _par[_par[_a]]
                _a = _par[_a]
            return _a

        for _i, _v in enumerate(_used):
            for _co2, _j, _d in _kd.find_range(_me.vertices[_v].co, 1e-4):
                _ra, _rb = _find(_i), _find(_j)
                if _ra != _rb:
                    _par[_ra] = _rb
        _weld = {_v: _find(_i) for _i, _v in enumerate(_used)}
        _edges = _c2.defaultdict(list)          # welded edge -> [(face index, direction)]
        for _p in _polys:
            _vs = [_weld[v] for v in _p.vertices]
            for _i in range(len(_vs)):
                _a, _b = _vs[_i], _vs[(_i + 1) % len(_vs)]
                if _a != _b:
                    _edges[(min(_a, _b), max(_a, _b))].append((_p.index, 1 if _a < _b else -1))
        _adj = _c2.defaultdict(list)
        for _fl in _edges.values():
            if len(_fl) == 2:                    # manifold edges only
                (_f1, _d1), (_f2, _d2) = _fl
                _adj[_f1].append((_f2, _d1, _d2))
                _adj[_f2].append((_f1, _d2, _d1))
        _state = {}
        _comp = {}
        _ncomp = 0
        for _p in _polys:
            if _p.index in _state:
                continue
            _state[_p.index] = 1
            _comp[_p.index] = _ncomp
            _q = [_p.index]
            while _q:
                _f = _q.pop()
                for _g, _df, _dg in _adj[_f]:
                    if _g not in _state:
                        # neighbours agree when the shared edge is traversed in opposite directions
                        _state[_g] = -_df * _state[_f] * _dg
                        _comp[_g] = _ncomp
                        _q.append(_g)
            _ncomp += 1
        _out = _c2.defaultdict(lambda: [0, 0])
        for _p in _polys:
            _w = _c2.Counter()
            for _vi in _p.vertices:
                for _g in _me.vertices[_vi].groups:
                    _w[_gn.get(_g.group, "")] += _g.weight
            _best = next((b for b, _ in _w.most_common() if b in _seg2), None)
            if _best is None:
                continue
            _c = _mw @ _p.center
            _o2 = _c - _near2(_c, *_seg2[_best])
            if _o2.length < 0.01:
                continue
            _nrm = (_n3 @ _p.normal).normalized() * _state[_p.index]
            _out[_comp[_p.index]][0] += 1
            if _nrm.dot(_o2.normalized()) > 0:
                _out[_comp[_p.index]][1] += 1
        # A CLOSED piece has an exact answer that needs no bone: the signed volume (divergence
        # theorem) is positive when its faces point outward and negative when the whole piece is
        # inside-out. The bone vote is only a fallback for open sheets. It is wrong for a shell
        # driven by bones that run through its middle: Alastor's coat skirt (thigh bones) voted 52%
        # outward while its signed volume was negative, and it was left inside-out.
        _ecount = _c2.defaultdict(lambda: [0, 0])
        for _fl in _edges.values():
            _cid = _comp[_fl[0][0]]
            _ecount[_cid][1] += 1
            if len(_fl) == 2:
                _ecount[_cid][0] += 1
        _cen = _c2.defaultdict(lambda: [Vector((0.0, 0.0, 0.0)), 0])
        for _p in _polys:
            _cc = _cen[_comp[_p.index]]
            _cc[0] += _mw @ _p.center
            _cc[1] += 1
        _vol = _c2.defaultdict(float)
        for _p in _polys:
            _cid = _comp[_p.index]
            _cv = (_mw @ _p.center) - _cen[_cid][0] / _cen[_cid][1]
            _vol[_cid] += _p.area * _cv.dot((_n3 @ _p.normal).normalized() * _state[_p.index]) / 3.0
        _wanted = set(_comp[i] for i in _listed)
        _flipcomp = set()
        for _cid in _wanted:
            _closed = _ecount[_cid][1] > 0 and _ecount[_cid][0] / _ecount[_cid][1] >= 0.95
            _n, _k = _out.get(_cid, (0, 0))
            if _closed:
                if _vol[_cid] < 0:
                    _flipcomp.add(_cid)
            elif _n >= 1 and _k / _n < 0.5:     # any size: a single triangle can be inside-out
                _flipcomp.add(_cid)
        if os.environ.get("VRM_ORIENT_DEBUG"):
            _cnt = _c2.Counter(_comp[p.index] for p in _polys)
            for _cid in sorted(_wanted):
                if _cnt[_cid] <= 40:
                    _zz = [(_mw @ p.center).z for p in _polys if _comp[p.index] == _cid]
                    print("  ORIENT_DEBUG '%s' piece %d: %d faces z %.2f..%.2f closed %.2f vol %+.6f vote %s -> %s" % (
                        _o.name, _cid, _cnt[_cid], min(_zz), max(_zz), (_ecount[_cid][0] / max(1, _ecount[_cid][1])), _vol[_cid],
                        _out.get(_cid, 'none'), 'FLIP' if _cid in _flipcomp else 'keep'))
        _fp = set(p.index for p in _polys
                  if _comp[p.index] in _wanted
                  and (_state[p.index] == -1) != (_comp[p.index] in _flipcomp))
        if _fp:
            _flip_faces(_o, _fp)
            print("  made %d pieces of '%s' consistent: flipped %d of %d faces (%d pieces turned outward)"
                  % (_ncomp, _o.name, len(_fp), len(_polys), len(_flipcomp)))

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
# ONE pattern and ONE anchor bone was the whole interface, and it cannot rig a
# character who needs two groups. Jessica Rabbit has hair off her head AND a
# dress off her chest; Miku has twintails and a skirt. Rigging either one meant
# leaving the other rigid, which is exactly what the playtest reported for both
# of them -- not a bug in how they were built, a limit on what could be asked
# for.
#
# So the positional argument stays the hair group, byte for byte, and
# VRM_RIG_MORE adds further groups:
#
#   VRM_RIG_MORE="pattern@bone#segs,strands,anchor;pattern2@bone2"
#
# ';' separates groups, '@' names the bone the group hangs from, and '#' sets
# that group's own segments, strands and rigid-top fraction. The bone and the
# knobs are both optional. A group anchored anywhere other than the head gets
# its chains named ClothSpring rather than HairSpring, which is what puts it on
# the cloth spring parameters below: a cape and a ponytail want different
# numbers, and the chain's name is what the spring section judges by.
_SPECS = [(HAIRRIG, _ANCHOR_BONE, "HairSpring",
           os.environ.get("HAIR_SEGS", "4"),
           os.environ.get("HAIR_STRANDS", "4"),
           os.environ.get("HAIR_ANCHOR", "0.30"),
           os.environ.get("HAIR_LO", "0"), os.environ.get("HAIR_HI", "1"))]
if _ANCHOR_BONE and MAP.get("head") and _ANCHOR_BONE != MAP.get("head"):
    _SPECS[0] = (HAIRRIG, _ANCHOR_BONE, "ClothSpring") + _SPECS[0][3:]
for _more in [x for x in os.environ.get("VRM_RIG_MORE", "").split(";") if x.strip()]:
    _knob = ""
    if "#" in _more:
        _more, _, _knob = _more.partition("#")
    _pat, _, _bone = _more.partition("@")
    if not _pat.strip():
        continue
    _k = [x.strip() for x in _knob.split(",")] + ["", "", "", "", ""]
    _hit = [b.name for b in arm.data.bones
            if b.name == _bone or b.name.endswith(":" + _bone)
            or b.name.lower() == _bone.lower()] if _bone else []
    if _bone and not _hit:
        raise SystemExit("ABORT: VRM_RIG_MORE names bone %r, which this rig has "
                         "not got" % _bone)
    _SPECS.append((_pat.strip(), _hit[0] if _hit else "",
                   "HairSpring" if not _hit or _hit[0] == MAP.get("head")
                   else "ClothSpring",
                   _k[0] or "4", _k[1] or "4", _k[2] or "0.30",
                   _k[3] or "0", _k[4] or "1"))
    print("  rig group: /%s/ from '%s' (%s segs, %s strands, %s rigid at top, "
          "height band %s..%s)"
          % (_SPECS[-1][0], _SPECS[-1][1] or MAP.get("head"), _SPECS[-1][3],
             _SPECS[-1][4], _SPECS[-1][5], _SPECS[-1][6], _SPECS[-1][7]))

# Where a z sits in the character: 0 at the feet, 1 at the crown, and the
# inverse. Used by the height band below and by the island listing, so a recipe
# can be written straight from the build's own output.
_CZ = [_v.co.z for _o in meshes for _v in _o.data.vertices]
_CZ0, _CZ1 = (min(_CZ), max(_CZ)) if _CZ else (0.0, 1.0)


def _frac(_z):
    return (_z - _CZ0) / (_CZ1 - _CZ0) if _CZ1 > _CZ0 else 0.0


def _frac_z(_f):
    return _CZ0 + (_CZ1 - _CZ0) * _f


for _gi, (HAIRRIG, _ANCHOR_BONE, _PREFIX, _S_SEG, _S_STR, _S_ANC,
          _S_LO, _S_HI) in enumerate(_SPECS):
    if HAIRRIG and (_ANCHOR_BONE or MAP.get("head") in bone_names):
        HEAD = _ANCHOR_BONE or MAP["head"]
        if _ANCHOR_BONE:
            print("  hair rig: hanging the new chains from '%s'" % HEAD)
        # Defaults suit loose hair. A FITTED garment needs most of itself pinned:
        # rigging Gwen's hood with these made it peel off her head and expose it,
        # because a worn-up hood has no loose cloth except its trailing edge.
        N_SEG = int(_S_SEG)             # bones per strand
        N_STRAND = int(_S_STR)          # strands to split into
        ANCHOR = float(_S_ANC)          # top fraction left rigid

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
                    _iz = [obj.data.vertices[_c].co.z for _c in comp]
                    print("  hair rig: island %d of %d on mesh '%s', %d verts,"
                          " z %.3f..%.3f (%.2f..%.2f of the character)"
                          % (_w, len(ranked), obj.name, cnt,
                             min(_iz), max(_iz),
                             _frac(min(_iz)), _frac(max(_iz))))
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

        # A SKIRT often has no name, no material and no island of its
        # own. Miku's is the lower part of the torso island -- one mesh called
        # 'body', one material, 209 islands, and the skirt is simply where the
        # torso stops being a torso. None of the three existing selectors can
        # address that, which is why her dress was still rigid after
        # everything else had been rigged.
        #
        # So a group may be clipped to a band of the CHARACTER's height, given
        # as two fractions. Fractions rather than coordinates because the build
        # moves and rescales the figure before this runs, so the numbers in the
        # source file are not the numbers here -- but "the bottom third of the
        # torso" is the same thing either way.
        if (float(_S_LO) > 0.0 or float(_S_HI) < 1.0) and hair:
            _blo, _bhi = _frac_z(float(_S_LO)), _frac_z(float(_S_HI))
            _before = sum(len(v) for v in hair.values())
            for _o in list(hair):
                hair[_o] = {_i for _i in hair[_o]
                            if _blo <= _o.data.vertices[_i].co.z <= _bhi}
                if not hair[_o]:
                    del hair[_o]
            print("  hair rig: clipped to z %.3f..%.3f (%s..%s of the "
                  "character): %d verts of %d"
                  % (_blo, _bhi, _S_LO, _S_HI,
                     sum(len(v) for v in hair.values()), _before))

        total = sum(len(v) for v in hair.values())
        if not total:
            print("  hair rig: no material matches /%s/ - nothing to rig" % HAIRRIG)
        else:
            # WHICH END IS ATTACHED is not something z can be assumed to
            # answer. Hair hangs below the head, so for hair the top of the
            # group is the attached end and everything below it swings -- which
            # is what this was written against and why it went unquestioned.
            # Mando's cape is anchored at Spine1 and his build scene has z
            # running the other way, so the rigger took the HEM as the attached
            # end: it pinned the hem rigid on his thighs and ran the chain
            # upwards, putting the swinging tip at his collar. A cape bolted to
            # the legs and flapping at the neck is 'folded in on itself and
            # fairly static' exactly as reported.
            #
            # The anchor bone is the physical attachment and it is already
            # known, so measure against it instead of trusting an axis: the end
            # of the group nearer the anchor is the attached end. ZF flips the
            # sense of every comparison below when it is the low end, and the
            # bones themselves are still built at the real z.
            allz = [o.data.vertices[i].co.z for o, vs in hair.items() for i in vs]
            ZF = 1.0
            _ab = arm.data.bones.get(HEAD)
            if _ab is not None and allz:
                # Compare against the MIDDLE of the bone and in three
                # dimensions. The first cut of this used the bone's head and
                # the z axis alone, and flipped Gadget Hackwrench's hair: the
                # head bone's head is down at the neck, 0.80, while her hair
                # runs 0.50 to 1.25, so the bottom of her hair measured nearer
                # to it than the top. The bone occupies 0.80 to 1.21 and its
                # middle, 1.01, is inside the skull where the hair is actually
                # rooted. A bone is a segment; where it STARTS is not where it
                # is.
                _am = (_ab.head_local + _ab.tail_local) * 0.5
                _pv = [(ZZ, o.data.vertices[i].co)
                       for o, vs in hair.items() for i in vs
                       for ZZ in (o.data.vertices[i].co.z,)]
                _pv.sort(key=lambda t: t[0])
                _n10 = max(1, len(_pv) // 10)

                def _mid(_sel):
                    _a = Vector((0.0, 0.0, 0.0))
                    for _, _c in _sel:
                        _a = _a + _c
                    return _a / len(_sel)

                _d_lo = (_mid(_pv[:_n10]) - _am).length
                _d_hi = (_mid(_pv[-_n10:]) - _am).length
                if _d_lo < _d_hi:
                    ZF = -1.0
                    print("  hair rig: this group is attached at its BOTTOM "
                          "(%.3f m from '%s', against %.3f m at the top), so "
                          "the chains hang upward from it"
                          % (_d_lo, HEAD, _d_hi))
            allz = [ZF * _z for _z in allz]
            z_max, z_min = max(allz), min(allz)
            span = z_max - z_min
            z_anchor = z_max - span * ANCHOR
            pts = [(o.data.vertices[i].co.copy(), o, i)
                   for o, vs in hair.items() for i in vs
                   if ZF * o.data.vertices[i].co.z < z_anchor]
            print("  hair rig: %d hair verts spanning %.3f m; %d loose below z=%.3f"
                  % (total, span, len(pts), z_anchor))

            if len(pts) < 50 or span < 0.05:
                print("  hair rig: too little loose hair to be worth rigging")
            else:
                # Split the loose hair into strands: k-means on the XY of the tips,
                # which is where separate strands are furthest apart.
                lo_cut = z_min + (z_anchor - z_min) * 0.35
                seeds = [p for p in pts if ZF * p[0].z < lo_cut] or pts
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
                    zs = [ZF * c.z for c, _, _ in own]
                    top, bot = max(zs), min(zs)
                    if top - bot < 0.02 or len(own) < 20:
                        continue
                    step = (top - bot) / N_SEG

                    def centre_between(z_hi, z_lo, members):
                        sel = [c for c, _, _ in members
                               if z_lo <= ZF * c.z <= z_hi]
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
                        nb = ebs.new("%s_%d_%d_%d"
                                     % (_PREFIX, _gi, k, seg))
                        nb.head = Vector((a_xy.x, a_xy.y, ZF * z0))
                        nb.tail = Vector((b_xy.x, b_xy.y, ZF * z1))
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
                        if abs(z_top - z_bot) < 1e-6:
                            continue
                        # Sign-free on purpose: with the chain running the
                        # other way both halves of the ratio change sign
                        # together, so u still runs 0 at the anchor to 1 at the
                        # tip.
                        u = max(0.0, min(1.0, (z_top - o.data.vertices[i].co.z)
                                         / (z_top - z_bot)))
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

# A left/right swap breaks nothing that any count can see. The bone count is
# right, the humanoid count is right, the character stands up straight, and it
# only shows when the GAME poses it: Power Girl's legs cross over each other and
# Judy Hopps' do the same. Measured across the 66 characters built here, 258 of
# 264 limb pairs agree on which side is which and two characters supply all six
# of the disagreements.
#
# The map is built from bone NAMES, and a name is exactly what cannot be trusted
# here -- a rip can mirror a rig and leave the names where they were. The
# geometry cannot lie in the same way, so read the side off the x axis and say
# so. VRM_KEEP_SIDES=1 keeps a deliberate mapping.
_PAIRS = (("left_upper_arm", "right_upper_arm"), ("left_hand", "right_hand"),
          ("left_upper_leg", "right_upper_leg"), ("left_foot", "right_foot"))
_MWb = arm.matrix_world
_votes = []
for _l, _r in _PAIRS:
    _ln, _rn = MAP.get(_l), MAP.get(_r)
    if not _ln or not _rn or _ln not in bone_names or _rn not in bone_names:
        continue
    _lx = (_MWb @ arm.data.bones[_ln].head_local).x
    _rx = (_MWb @ arm.data.bones[_rn].head_local).x
    if abs(_lx - _rx) > 1e-4:
        _votes.append(1 if _lx > _rx else -1)
if _votes:
    # The character's own left is +x once the builder has turned it to face -Y,
    # which every other stage here already depends on.
    _wrong = sum(1 for v in _votes if v < 0)
    if _wrong > len(_votes) / 2.0:
        if os.environ.get("VRM_KEEP_SIDES"):
            print("  sides: %d of %d limb pairs are mirrored; VRM_KEEP_SIDES "
                  "keeps them" % (_wrong, len(_votes)))
        else:
            _sw = 0
            for _k in list(MAP):
                if _k.startswith("left_"):
                    _o = "right_" + _k[5:]
                    if _o in MAP:
                        MAP[_k], MAP[_o] = MAP[_o], MAP[_k]
                        _sw += 1
            print("  sides: %d of %d limb pairs sat on the wrong side of the "
                  "body, so the rig is mirrored against its own names -- "
                  "swapped %d left/right mappings"
                  % (_wrong, len(_votes), _sw))
    else:
        print("  sides: all %d limb pairs are on the side their names claim"
              % len(_votes))

# Weight on a bone the EXPORTER will not write is weight on nothing, and it
# fails in exactly the same way as the orphan bones below -- except that the
# bone is a perfectly good parent in Blender right up to the moment it is
# dropped.
#
# The VRM exporter writes only bones with use_deform set. A Rigify rig carries
# three bones for every joint -- ORG- (the original), MCH- (mechanism) and DEF-
# (the one that deforms) -- and only the DEF- bones have that flag. Gadget
# Hackwrench measured this: her eyes are bone-parented to MCH-eye.L and
# MCH-eye.R, the bone-parent conversion above dutifully bound them to those
# bones, the export then dropped both, and the glTF exporter gave the orphaned
# weights to a bone of its own invention -- 'neutral_bone' at the root, which
# never moves. Her eyes stayed where they were bound while her head turned.
# 172 joints came out of a 677-bone armature, and nothing in the build said a
# word about the 505 that went.
#
# So: for every vertex group naming a bone that will not survive, move the
# weight to the nearest ANCESTOR that will. An eye bound to the head is right;
# an eye bound to nothing is not.
# Walking up the parents is the FIRST choice and frequently finds nothing.
# Rigify's control bones are a hierarchy of their own: MCH-eye.L's parents run
# master_eye.L, ORG-face, ORG-spine.006, head, MCH-ROT-head, neck, torso, root
# -- thirteen bones to the root and not one of them deforms. The DEF- bones that
# do are a parallel tree. So when the walk runs out, fall back to the nearest
# humanoid bone by position, which is what the stray-geometry rescue does, and
# for an eye bone is the head.
#
# The first version of this pass gave up silently when the walk failed, and so
# reported nothing on the very character it was written for. A rescue that can
# decline must say when it declines.
_nd, _nd_no = [], []
_ndh = [(_n, arm.data.bones[_n].head_local) for _n in set(MAP.values())
        if _n in bone_names and arm.data.bones[_n].use_deform]
for _m in meshes:
    for _g in list(_m.vertex_groups):
        _b = arm.data.bones.get(_g.name)
        if _b is None or _b.use_deform:
            continue
        _idx = [_v.index for _v in _m.data.vertices
                for _vg in _v.groups if _vg.group == _g.index
                and _vg.weight > 0.0001]
        if not _idx:
            _m.vertex_groups.remove(_g)
            continue
        _anc = _b.parent
        while _anc is not None and not _anc.use_deform:
            _anc = _anc.parent
        _how = "ancestor"
        if _anc is None:
            if not _ndh:
                _nd_no.append((_m.name, _b.name, len(_idx)))
                continue
            _anc = arm.data.bones[min(_ndh, key=lambda t: (t[1] - _b.head_local).length)[0]]
            _how = "nearest"
        _tg = _m.vertex_groups.get(_anc.name) or _m.vertex_groups.new(name=_anc.name)
        _tg.add(_idx, 1.0, "REPLACE")
        _m.vertex_groups.remove(_g)
        _nd.append((_m.name, _b.name, _anc.name, len(_idx), _how))
if _nd:
    print("  non-deform weights: %d vertex group(s) named a bone the exporter "
          "will not write, so the weight would have landed on an invented bone "
          "that never moves -- rebound: %s"
          % (len(_nd), ", ".join("%s %s->%s (%d verts, %s)" % t
                                 for t in _nd[:6])))
if _nd_no:
    print("  non-deform weights: %d group(s) could NOT be rescued, and that "
          "geometry will not move: %s"
          % (len(_nd_no), ", ".join("%s %s (%d verts)" % t for t in _nd_no[:6])))

# A bone can deform geometry and still never move.
#
# VRM drives the 52 humanoid bones and the spring chains, and nothing else. Any
# other bone follows only if it is a DESCENDANT of one of those -- so a deform
# bone parented outside that hierarchy is dead weight in the literal sense: the
# vertices on it hold their bind position while the rest of the character moves
# away from them.
#
# It is invisible to every count. The mesh is there, the skin is there, every
# vertex carries full weight, the humanoid map is complete. Measured on the
# characters this was first seen on: 31% of Lola Bunny's body mesh hangs off
# fml_un_C_TopHead and fml_un_C_BotHead, which is why her head floats above her
# neck, and Gadget Hackwrench's eyes are 100% on bones outside the chain. Judy's
# belt, Joker's suit panels and Ariel's and Heels' lower hair are the same fault.
#
# Re-parent each orphan to the nearest humanoid bone, keeping its world
# position, so the geometry rides the body instead of being left behind.
# VRM_KEEP_ORPHANS=1 leaves them alone.
_driven = set()
for _n in MAP.values():
    if _n in bone_names:
        _driven.add(_n)
        _b = arm.data.bones.get(_n)
        if _b:
            for _c in _b.children_recursive:
                _driven.add(_c.name)
_deform_now = set()
for _m in meshes:
    _gnm = dict((_g.index, _g.name) for _g in _m.vertex_groups)
    for _v in _m.data.vertices:
        for _g in _v.groups:
            if _g.weight > 0.01:
                _deform_now.add(_gnm.get(_g.group))
_orphans = sorted(n for n in _deform_now
                  if n and n in bone_names and n not in _driven)
if _orphans and not os.environ.get("VRM_KEEP_ORPHANS"):
    _hum_bones = [(_n, arm.data.bones[_n].head_local) for _n in MAP.values()
                  if _n in bone_names]
    if _hum_bones:
        # An orphan ABOVE the humanoid root is a different animal, and the
        # first cut of this got it wrong in the most direct way possible.
        #
        # Miku's thighs hang off 'Bip01 Spine', so the build promotes that to
        # hips -- correctly -- which leaves 'Bip01 Spine's own parent,
        # 'Bip01 Pelvis', outside the humanoid hierarchy carrying 22.9% of her
        # body. It is an orphan by the test above, so this adopted it to the
        # nearest humanoid bone, which was 'Bip01 R Thigh': one of its own
        # grandchildren. Blender will not build that cycle, the re-parent
        # silently did nothing, and the log claimed the fix while the measured
        # 23.7% of undriven weight did not move at all. "Her dress doesn't move
        # with her" was that pelvis the whole time, and not a missing spring.
        #
        # Nothing above the root can be adopted by anything below it, so move
        # the WEIGHT down to the humanoid root instead. Anything below the root
        # is still re-parented as before.
        _hips = MAP.get("hips")
        _up, _moved = [], []
        for _n in list(_orphans):
            _b = arm.data.bones.get(_n)
            if _b is None or _hips is None or _hips == _n:
                continue
            if any(_c.name in _driven for _c in _b.children_recursive):
                _up.append(_n)
                _orphans.remove(_n)
        if _up and _hips in bone_names:
            _tot = 0
            for _m in meshes:
                for _gn in _up:
                    _g = _m.vertex_groups.get(_gn)
                    if _g is None:
                        continue
                    _idx = [_v.index for _v in _m.data.vertices
                            for _vg in _v.groups if _vg.group == _g.index
                            and _vg.weight > 0.0001]
                    if _idx:
                        _tg = (_m.vertex_groups.get(_hips)
                               or _m.vertex_groups.new(name=_hips))
                        _tg.add(_idx, 1.0, "REPLACE")
                        _tot += len(_idx)
                    _m.vertex_groups.remove(_g)
            print("  orphan bones: %d bone(s) sit ABOVE the humanoid root and "
                  "cannot be adopted by their own descendants, so their weight "
                  "moved down to '%s' instead -- %s, %d vertices"
                  % (len(_up), _hips, ", ".join(_up[:6]), _tot))
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        for _n in _orphans:
            _eb = arm.data.edit_bones.get(_n)
            if _eb is None or (_eb.parent and _eb.parent.name in _orphans):
                continue        # a child of another orphan rides with it
            _below = {_c.name for _c in arm.data.bones[_n].children_recursive}
            _cand = [t for t in _hum_bones if t[0] not in _below and t[0] != _n]
            if not _cand:
                continue
            _near = min(_cand, key=lambda t: (t[1] - _eb.head).length)
            _tb = arm.data.edit_bones.get(_near[0])
            if _tb is None or _tb == _eb:
                continue
            # use_connect FIRST, and restore the rest position afterwards.
            # Assigning a parent while the bone is still connected makes
            # Blender snap its head onto the new parent's TAIL, which moves the
            # bone -- and clearing use_connect afterwards does not put it back.
            #
            # This is what left Lola Bunny's teeth hanging beside her face.
            # Re-parenting at rest IS deformation-neutral, which is the whole
            # reason the hierarchy repair is safe, but only if the bone does not
            # move: the armature reads bone.matrix_local, and a snapped head
            # rewrites exactly that. Her head followed her body correctly and
            # the 118 bones the fix had "repaired" were displaced instead.
            _h, _t, _roll = _eb.head.copy(), _eb.tail.copy(), _eb.roll
            _eb.use_connect = False
            _eb.parent = _tb
            _eb.use_connect = False
            _eb.head, _eb.tail, _eb.roll = _h, _t, _roll
            _moved.append((_n, _near[0]))
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
        if _orphans:
            print("  orphan bones: %d deform bone(s) sat outside the humanoid "
                  "hierarchy, so nothing would ever have moved them -- "
                  "re-parented %d: %s"
                  % (len(_orphans), len(_moved),
                     ", ".join("%s->%s" % t for t in _moved[:8])))
elif _orphans:
    print("  orphan bones: %d outside the humanoid hierarchy, left alone by "
          "VRM_KEEP_ORPHANS: %s" % (len(_orphans), ", ".join(_orphans[:8])))

# Vertices with NO weight at all are a different fault from the orphan bones
# above, and they look identical in the game.
#
# The glTF exporter gives unweighted geometry a bone of its own invention --
# 'neutral_bone' -- which is parented at the root and never moves, so the
# geometry sits in space exactly as an orphan does. Gadget Hackwrench's eyes and
# teeth are 100% on it: they were never bound to anything.
#
# The existing unrigged-mesh rescue cannot catch this, by design. It exists for
# a model with NO rig at all and stands down the moment any mesh in the file is
# bound, because fitting a skeleton to one stray mesh once shrank Alcina's whole
# rig by 0.5568. That is still right. This is the narrower case: the rig is
# fine and a few meshes were left out of it, so bind those to the nearest
# humanoid bone and leave the skeleton alone.
_strays = []
_hb = [(_n, arm.data.bones[_n].head_local) for _n in set(MAP.values())
       if _n in bone_names]
if _hb:
    for _m in meshes:
        _have = set()
        for _v in _m.data.vertices:
            for _g in _v.groups:
                if _g.weight > 0.0001:
                    _have.add(_v.index)
                    break
        _loose = [_v.index for _v in _m.data.vertices if _v.index not in _have]
        if not _loose:
            continue
        # ASK THE NEIGHBOURS, NOT THE SKELETON.
        #
        # Binding to the nearest humanoid bone HEAD put Gadget Hackwrench's 188
        # unweighted TEETH vertices on DEF-shoulder.L, so her teeth hung at her
        # collar instead of in her mouth. A shoulder bone's head sits near the
        # base of the neck, which is closer to a mouth than a head bone whose
        # head sits up inside the skull -- the measure was simply the wrong one.
        #
        # Stray geometry is almost always a part of something that IS weighted:
        # teeth inside a mouth, a tongue, an eye. So take the weight of the
        # nearest vertex in the same mesh that already has some. That is local,
        # needs no idea of anatomy, and gets teeth onto whatever the mouth
        # around them uses. Only when the mesh has no weighted vertex at all
        # does it fall back to the nearest humanoid bone.
        _byb = {}
        _mw = _m.matrix_world
        _anchor = [(_m.data.vertices[_i].co,
                    max(((_g.weight, _m.vertex_groups[_g.group].name)
                         for _g in _m.data.vertices[_i].groups if _g.weight > 0.0001),
                        default=(0.0, None))[1])
                   for _i in _have]
        _anchor = [(c, n) for c, n in _anchor if n]
        for _i in _loose:
            _lc = _m.data.vertices[_i].co
            if _anchor:
                _pick = min(_anchor, key=lambda t: (t[0] - _lc).length_squared)[1]
            else:
                _co = _mw @ _lc
                _pick = min(_hb, key=lambda t: ((arm.matrix_world @ t[1]) - _co).length)[0]
            _byb.setdefault(_pick, []).append(_i)
        for _bn, _vs in _byb.items():
            _vg = _m.vertex_groups.get(_bn) or _m.vertex_groups.new(name=_bn)
            _vg.add(_vs, 1.0, "REPLACE")
        # A vertex group is a name until something reads it. Without an
        # ARMATURE modifier the mesh is not skinned at all, the exporter
        # writes it as a static node, and the weights just added are inert.
        #
        # Lola Bunny measured this: THREE of her four meshes -- both sets of
        # teeth and her hair -- came out with skin=None while her body was
        # skinned normally. They are not weighted wrongly, they are not
        # weighted at all, and nothing in the file can ever move them. That is
        # "her hair and teeth don't animate with her body".
        if not any(_md.type == "ARMATURE" and _md.object is arm
                   for _md in _m.modifiers):
            _amd = _m.modifiers.new(name="Armature", type="ARMATURE")
            _amd.object = arm
            _m.parent = arm
        _strays.append((_m.name, len(_loose), sorted(_byb, key=lambda k: -len(_byb[k]))[0]))
if _strays:
    print("  stray geometry: %d mesh(es) carried vertices with no weight at "
          "all, which the exporter would have hung on a bone of its own that "
          "never moves -- bound to whatever the nearest weighted neighbour "
          "uses: %s"
          % (len(_strays), ", ".join("%s %d verts -> %s" % t for t in _strays[:6])))

# ---------------------------------------------------------------- chest rig
# What a rig calls its chest bones, used both to FIND authored ones here
# and to spring them further down. Defined once, up here, because the
# chest rigger needs it 1100 lines before the spring section does.
BREAST = r"(breast|bust|boob|pector|chichi|oppai)"
# Spring bones need bones, and most rigs have no chest bones at all: of the 66
# characters built here, 16 carry them unsprung, 3 arrive already sprung, and
# 47 have none -- which includes most of the women. For those the bones have to
# be built, the way the hair rigger builds hair chains.
#
#   VRM_BREASTRIG=1      rig it
#   VRM_BREASTRIG=check  measure and print, change nothing
#
# `check` is not a convenience, it is how this was written. Sixteen characters
# here ship AUTHORED chest bones, so the detector can be run where a human has
# already answered and the two compared. A detector that has only ever run
# where the answer is unknown has not been tested.
BREASTRIG = os.environ.get("VRM_BREASTRIG", "")


def _chest_rig():
    """Build chest bones, or say why not.

    A FUNCTION so that every refusal can return. This was a plain
    `if` block with two `raise SystemExit`s in it, and one of them
    ended Gadget Hackwrench's entire conversion: she is 1.30 m with
    shoulders 0.146 m apart, which fails a sanity check written for
    human proportions, and she is a chipmunk. Jiggle is a cosmetic
    feature and must never cost a character its build."""
    global bone_names
    _cb = MAP.get("upper_chest") or MAP.get("chest") or MAP.get("spine")
    _nk = MAP.get("neck") or MAP.get("head")
    # The UPPER ARM heads, not the shoulders. A clavicle begins at the
    # sternum, so the two shoulder bones' heads are centimetres apart: on
    # Alcina they gave a "shoulder span" of 0.055 m for a 2.9 m character,
    # which shrank the search band to |x| < 0.023 and found both apexes on
    # her sternum, 25 and 40 cm from the bones she actually has.
    _shl = MAP.get("left_upper_arm") or MAP.get("left_shoulder")
    _shr = MAP.get("right_upper_arm") or MAP.get("right_shoulder")
    _from_arms = bool(MAP.get("left_upper_arm") and MAP.get("right_upper_arm"))
    _missing = [n for n in (_cb, _nk, _shl, _shr) if not n or n not in bone_names]
    if _missing:
        print("  chest rig: %d of the chest, neck and two shoulders are not "
              "mapped on this rig, so there is nothing to measure from"
              % len(_missing))
        return
    _MW = arm.matrix_world

    def _bw(n):
        return _MW @ arm.data.bones[n].head_local

    _chest_p, _neck_p = _bw(_cb), _bw(_nk)
    # The MIDLINE is where the spine is, not x=0. Nothing in this build
    # promises the character is centred on the origin, and Alcina is not: her
    # spine sits at x=-0.131, so measuring from zero put the search column
    # 13 cm off-centre and found her left apex at the column's inner edge
    # while the right one looked 39 cm from the bone she already has. Read off
    # the authored bones it is obvious -- breast.L at +0.050 and breast.R at
    # -0.311 are symmetric about -0.131, not about 0.
    _mid_x = _chest_p.x
    _span = (_bw(_shl) - _bw(_shr)).length
    # Every threshold below is a fraction of this, so a wrong span is not a
    # small error -- it moves the search band, the side split and the
    # protrusion test together, and all three stay plausible-looking.
    _torso_h = abs(_neck_p.z - _bw(MAP.get("hips") or _cb).z) or 1e-6
    # Judge this by WHICH BONES were found, not by the proportion they give.
    #
    # The failure this guards against is real: measured between the two
    # CLAVICLES -- which both begin at the sternum -- Alcina's "shoulder span"
    # came out as 0.055 m for a 2.9 m character, and every threshold here is a
    # fraction of that span. But a proportion cannot tell that apart from an
    # unusual body. Measured across all 66 installed characters, span/torso
    # runs from 0.203 (Gadget Hackwrench, a chipmunk, whose arms ARE correctly
    # mapped) up past 0.6, with no gap anywhere in between to put a line in.
    # The first version of this check drew it at 0.35 and threw her whole
    # conversion away.
    #
    # The two ranges OVERLAP outright: across the 66, arm span / torso runs
    # 0.203 to 1.407 and clavicle span / torso runs 0.034 to 0.554, so no
    # global line separates them. Within ONE character they never overlap --
    # of the 19 that map both, the clavicle span is smaller every time, by at
    # least 2.5x and typically 3.2x. So the question worth asking is which
    # pair the humanoid map actually gave us, which is known rather than
    # inferred.
    if not _from_arms:
        print("  chest rig: not rigged (a limitation, not a failure) -- this "
              "rig maps no upper arms, so the only width available is between "
              "the clavicles, which both start at the sternum and would "
              "mis-scale every measurement here")
        return
    if _span < _torso_h * 0.05:
        print("  chest rig: not rigged (a limitation, not a failure) -- the "
              "arm joints are %.3f m apart against a torso %.3f m tall, which "
              "is degenerate" % (_span, _torso_h))
        return
    # The arms must be out of this entirely. A vertex by the armpit belongs to
    # the shoulder as much as to the chest, and pulling one onto a spring bone
    # is how a sleeve tears the moment the arm comes down.
    # Which groups actually drive geometry: a bone that is only NAMED is not
    # a chest bone. Batman carries fml_un_C_breast because MultiVersus skins
    # its whole cast onto one shared female base, and it deforms nothing of
    # him.
    _deform_groups = set()
    for _m in meshes:
        _gnm = dict((_g.index, _g.name) for _g in _m.vertex_groups)
        for _v in _m.data.vertices:
            for _g in _v.groups:
                if _g.weight > 0.01:
                    _deform_groups.add(_gnm.get(_g.group))
    _armg = set()
    for _k in ("shoulder", "upper_arm", "lower_arm", "hand"):
        for _s in ("left", "right"):
            _n = MAP.get("%s_%s" % (_s, _k))
            if _n:
                _armg.add(_n)
    _torsog = set(n for n in (MAP.get("chest"), MAP.get("upper_chest"),
                              MAP.get("spine"), MAP.get("hips")) if n)
    _z_lo = _chest_p.z - (_neck_p.z - _chest_p.z) * 0.35
    _z_hi = _neck_p.z
    _x_lim = _span * 0.42
    _cand = []
    for _o in meshes:
        _gn = dict((_g.index, _g.name) for _g in _o.vertex_groups)
        _mw = _o.matrix_world
        for _v in _o.data.vertices:
            _w = _mw @ _v.co
            if not (_z_lo <= _w.z <= _z_hi) or abs(_w.x - _mid_x) > _x_lim:
                continue
            _gs = [(g.weight, _gn.get(g.group)) for g in _v.groups
                   if g.weight > 0.0]
            if not _gs:
                continue
            # Compare the SHARES, do not veto on a trace. Rejecting any vertex
            # with 0.05 of arm weight threw away all but 61 of Sophia's chest
            # vertices: she is a photogrammetry scan whose shoulder weights
            # bleed a little way across the whole upper chest, which is what
            # good weighting looks like. The test is whether the arm OWNS the
            # vertex, not whether it touches it.
            _wa = sum(w for w, n in _gs if n in _armg)
            _wt = sum(w for w, n in _gs if n in _torsog)
            if _wt <= 0.0 or _wa > 0.25 or _wa >= _wt:
                continue
            _cand.append((_w, _o, _v.index))
    print("  chest rig: %d torso vertices in the band z %.3f..%.3f, within "
          "%.3f of the midline at x=%.3f (shoulder span %.3f)"
          % (len(_cand), _z_lo, _z_hi, _x_lim, _mid_x, _span))
    # Front is -Y: the builder has already turned the character to face it.
    #
    # Look in a COLUMN at the offset the authored rigs use, not across the whole
    # chest. Reading the 48 chest bones the 16 authored characters carry, the
    # one number that transfers between rig families is how far out they sit:
    # 0.18 to 0.36 of the shoulder span, median 0.25. (Height does not transfer
    # -- it is measured from whichever bone that family calls the chest -- and
    # depth is better taken from the mesh than from another model's skeleton.)
    #
    # Searching the whole chest instead finds the most forward vertex anywhere
    # in the band, which on a dressed character is a collar or a bodice at the
    # midline: on Alcina it put both apexes on her sternum, 24 and 40 cm from
    # the bones she already has.
    # Front is -Y: the builder has already turned the character to face it.
    #
    # PROFILE the front surface across the half-chest and take its peak, rather
    # than assuming where the apex is. The 48 authored chest bones on the 16
    # characters that have them put the bone anywhere from 0.10 of the shoulder
    # span out (Ariel) to 0.41 (Alcina), so a fixed offset -- even their median
    # of 0.25 -- lands on the wrong part of most chests: at 0.25 Alcina's apex
    # came out 11 cm inboard of the bone she already has, pinned against the
    # edge of the search column, which is what a window in the wrong place
    # always looks like.
    #
    # The peak of the profile is the apex by construction, and it costs nothing
    # to let the geometry say where it is.
    _NBIN = 14
    # A spring moves VERTICES. Below a certain count there is nothing to move
    # smoothly: the patch deforms as a handful of flat facets, which reads worse
    # than a chest that does not move at all. Gwen Stacy is the measured
    # borderline -- 205 front vertices across her whole chest band and a patch
    # of 49 between the two sides, about 25 each, where Prix has 366 a side and
    # Sayuri more. This is a property of the MODEL, so refusing is a limitation
    # and not a failure, and it is said that way in the log.
    _DETAIL = int(os.environ.get("VRM_BREASTRIG_MIN_VERTS", "120"))
    _PATCH = int(os.environ.get("VRM_BREASTRIG_MIN_PATCH", "40"))
    _sides = {}
    for _side, _sgn in (("L", 1.0), ("R", -1.0)):
        _half = [(c, o, i) for c, o, i in _cand
                 if _span * 0.06 < (c.x - _mid_x) * _sgn < _span * 0.48
                 and c.y < _chest_p.y]
        if len(_half) < _DETAIL:
            print("  chest rig: %s not rigged (a limitation, not a failure) -- "
                  "%d front vertices across the half-chest, under the %d a "
                  "spring needs to move smoothly"
                  % (_side, len(_half), _DETAIL))
            continue
        # Several meshes can occupy this space, stacked: body, underwear,
        # dress. Alcina's gown hangs 6 cm in front of her body here, and the
        # most forward vertex in the space is one of its frills -- rigging that
        # would wobble the GOWN, which is a cloth problem and not this one. The
        # body is the innermost layer, so pick the layer first, apex second.
        _layers = {}
        for _t in _half:
            _layers.setdefault(_t[1].name, []).append(_t)
        _ranked = []
        for _ln, _lv in _layers.items():
            if len(_lv) < _DETAIL // 2:
                continue
            _ly = sorted(c.y for c, _, _ in _lv)
            _ranked.append((_ly[len(_ly) // 2], _ln, _lv))
        if not _ranked:
            print("  chest rig: %s no single mesh here has 24 vertices" % _side)
            continue
        _ranked.sort(reverse=True)          # largest median y = least forward
        if len(_ranked) > 1:
            print("  chest rig: %s layers, front to back: %s" % (
                _side, "; ".join("%s y=%.3f" % (n, y)
                                 for y, n, _ in reversed(_ranked))))
        _own = _ranked[0][2]
        _lo, _hi = _span * 0.06, _span * 0.48
        _bins = [[] for _ in range(_NBIN)]
        for _t in _own:
            _u = ((_t[0].x - _mid_x) * _sgn - _lo) / (_hi - _lo)
            _bins[max(0, min(_NBIN - 1, int(_u * _NBIN)))].append(_t)
        _prof = []
        for _k, _b in enumerate(_bins):
            if len(_b) < 6:
                continue
            _prof.append((min(t[0].y for t in _b), _k, _b))
        if not _prof:
            print("  chest rig: %s profile is too sparse to read" % _side)
            continue
        _prof.sort()
        _peak = _prof[0]
        _apex = min(_peak[2], key=lambda t: t[0].y)
        _ao, _ai = _apex[1], _apex[2]
        _amat = "?"
        for _poly in _ao.data.polygons:
            if _ai in _poly.vertices:
                _slots = _ao.data.materials
                if len(_slots) > _poly.material_index:
                    _m = _slots[_poly.material_index]
                    _amat = _m.name if _m else "(empty slot)"
                break
        # Proud of WHAT: the median of the same layer's front surface across
        # the whole half-chest. A flat chest is a plane, and its peak sits
        # level with its own surface; a breast stands out of it.
        _ys = sorted(c.y for c, _, _ in _own)
        _surf = _ys[len(_ys) // 2]
        _prot = (_surf - _apex[0].y) / _span if _span else 0.0
        _sides[_side] = (_apex[0], _prot)
        print("  chest rig: %s apex (%.3f, %.3f, %.3f) at %.2f of the span out,"
              " on '%s'/'%s', standing %.1f%% proud of that layer's surface"
              % (_side, _apex[0].x, _apex[0].y, _apex[0].z,
                 abs(_apex[0].x - _mid_x) / _span, _ao.name, _amat,
                 _prot * 100))
        # Ground truth, where the model carries it.
        for _b in arm.data.bones:
            if not re.search(BREAST, _b.name, re.I):
                continue
            _t = _MW @ _b.tail_local
            if (_t.x - _mid_x) * _sgn <= 0:
                continue
            _h = _MW @ _b.head_local
            print("  chest rig: %s authored '%s' head (%.3f, %.3f, %.3f) tail "
                  "(%.3f, %.3f, %.3f), %.2f of the span out"
                  % (_side, _b.name, _h.x, _h.y, _h.z, _t.x, _t.y, _t.z,
                     abs(_t.x - _mid_x) / _span))
    _authored = set()
    for _b in arm.data.bones:
        if re.search(BREAST, _b.name, re.I) and _b.name in _deform_groups:
            _authored.add(_b.name)
    _MIN = float(os.environ.get("VRM_BREASTRIG_MIN", "0.06"))
    _rig = [k for k, v in _sides.items() if v[1] >= _MIN]
    # Two more tests, both of which the protrusion test alone lets through.
    #
    # A peak at the MIDLINE is a sternum, a collar or a bow -- Pomni's chest
    # peaks 0.06 of a shoulder span from her spine and stands 11% proud of the
    # surface, which passes a protrusion test comfortably and is not a breast.
    # Of the 48 authored bones measured here the innermost is Ariel's pectoral
    # at 0.10, so anything inside that is something else.
    #
    # And the two sides must AGREE. A character is symmetric; a detector that
    # finds the apex 0.22 of the span out on one side and 0.30 on the other has
    # found noise on at least one of them, which is what sparse or clothed
    # geometry gives.
    _OUT = float(os.environ.get("VRM_BREASTRIG_MIN_OUT", "0.12"))
    _outs = dict((k, abs(v[0].x - _mid_x) / _span) for k, v in _sides.items())
    _inner = [k for k in _rig if _outs[k] < _OUT]
    if _inner:
        print("  chest rig: %s peak(s) only %s of the span from the midline, "
              "inside the %.2f floor -- that is a sternum, not a bust"
              % ("/".join(sorted(_inner)),
                 ", ".join("%.2f" % _outs[k] for k in sorted(_inner)), _OUT))
        _rig = [k for k in _rig if k not in _inner]
    if len(_rig) == 2:
        _gap = abs(_outs["L"] - _outs["R"])
        if _gap > 0.10:
            print("  chest rig: the two sides disagree by %.2f of the span "
                  "(L %.2f, R %.2f), so at least one of them is noise -- "
                  "nothing rigged" % (_gap, _outs["L"], _outs["R"]))
            _rig = []
    if len(_rig) < 2:
        # Say what the character HAS, not only what it did not get. Ariel,
        # Killer Clown and Jessica Rabbit each read as "not rigged" here and
        # then gained two chest chains two lines later, on bones of their own
        # -- the log told half the story and the alarming half.
        print("  chest rig: not rigged (a limitation, not a failure) -- %d of "
              "the 2 sides survive the tests above%s"
              % (len(_rig),
                 ("; this rig has its own chest bones (%s) and the spring "
                  "section below takes them" % ", ".join(sorted(_authored)))
                 if _authored else ""))
    elif BREASTRIG == "check":
        print("  chest rig: check only, nothing changed")
    elif _authored:
        # Alcina has breast.L and breast.R already, and rigging her anyway gave
        # her four chest chains: hers and a second pair 20 cm inboard, both
        # weighted to the same geometry and pulling against each other. A rig
        # that has the bones needs the SPRING section below, not this.
        print("  chest rig: this rig already has weighted chest bones (%s), so "
              "there is nothing to build -- the spring section below is what "
              "it needs" % ", ".join(sorted(_authored)))
    else:
        # Count the patch BEFORE building anything: a bone whose patch turns
        # out to be four facets has to be undone, and undoing a weight paint is
        # harder than not doing it.
        _thin = []
        for _side in _rig:
            _apex = _sides[_side][0]
            _R = float(os.environ.get("VRM_BREASTRIG_R", "0.25")) * _span
            _n = sum(1 for _c, _o, _i in _cand if (_c - _apex).length < _R)
            if _n < _PATCH:
                _thin.append((_side, _n))
        if _thin:
            print("  chest rig: not rigged (a limitation, not a failure) -- the "
                  "patch would be %s, under the %d vertices a side a spring "
                  "needs to deform smoothly rather than as flat facets"
                  % (", ".join("%d on %s" % (n, k) for k, n in _thin), _PATCH))
            return
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        _made = {}
        for _side in _rig:
            _apex, _prot = _sides[_side]
            # A short bone rooted on the ribs behind the apex, pointing
            # forward -- not a long one reaching back to the spine. The long
            # version swung Prix's whole bust sideways on a 40-degree test
            # because the lever ran from the midline: the mass sheared off the
            # ribcage instead of swinging on it, and the bikini cup was left
            # hanging over a hollow. A spring rotates a bone about its HEAD, so
            # the head is the hinge, and the hinge of a breast is its base.
            _depth = max(_prot * _span, _span * 0.04)
            _base = Vector((_apex.x + (_mid_x - _apex.x) * 0.12,
                            _apex.y + _depth,
                            _apex.z + _depth * 0.25))
            _nb = arm.data.edit_bones.new("BreastSpring_" + _side)
            _inv = _MW.inverted()
            _nb.head = _inv @ _base
            _nb.tail = _inv @ _apex
            _nb.parent = arm.data.edit_bones[_cb]
            _nb.use_connect = False
            _made[_side] = _nb.name
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.update()
        _wtd = 0
        for _side, _bn in _made.items():
            _apex = _sides[_side][0]
            # Size the patch by the character, not by the bone: the bone
            # reaches back towards the spine, so on a 2.9 m Alcina 1.6 times
            # its length took in 5,936 vertices -- most of her torso.
            _R = float(os.environ.get("VRM_BREASTRIG_R", "0.25")) * _span
            for _o in meshes:
                _vg = _o.vertex_groups.get(_bn) or _o.vertex_groups.new(name=_bn)
                _gn = dict((_g.index, _g.name) for _g in _o.vertex_groups)
                for _w_co, _oo, _i in _cand:
                    if _oo is not _o:
                        continue
                    _d = (_w_co - _apex).length
                    if _d >= _R:
                        continue
                    # Squared falloff, and never the whole vertex: leaving a
                    # share on the chest is what stops the edge of the patch
                    # tearing off the ribs when the spring moves.
                    _w = 0.9 * (1.0 - _d / _R) ** 2
                    if _w <= 0.01:
                        continue
                    _v = _o.data.vertices[_i]
                    for _g in list(_v.groups):
                        _n = _gn.get(_g.group)
                        if _n in _torsog and _g.weight > 0.0:
                            _o.vertex_groups[_n].add([_i], _g.weight * (1.0 - _w),
                                                     "REPLACE")
                    _vg.add([_i], _w, "REPLACE")
                    _wtd += 1
        bone_names = {b.name for b in arm.data.bones}
        print("  chest rig: built %s and weighted %d vertices onto them"
              % (", ".join(sorted(_made.values())), _wtd))

if BREASTRIG:
    _chest_rig()

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
    k = channel_kind(stem)
    if k:
        return k
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
    # An opacity map is different in kind from every other map, and the pools
    # below are wrong for it. Most materials genuinely have none, so ABSENCE is
    # the normal answer rather than a gap to fill -- and a wrong one does not
    # merely miscolour the mesh, it deletes parts of it.
    #
    # Scott Hall's folder holds exactly one opacity file,
    # 'Hall_eyelash_opacity.png', and every one of its forty filenames begins
    # with 'Hall'. So the shared-word pool below matches all forty on the
    # character's own name, which narrows nothing, and that eyelash cutout went
    # on his boots, both kneepads, both elbow pads, his tights and his vest.
    # Ranking by size, which fixed the same map reaching all nine of Prix's
    # materials, cannot help when there is only one candidate.
    #
    # So: an alpha map comes from a file that names the material, or not at all.
    if kind == "alpha":
        return None
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
    # Only these are read. The kind used to go unchecked while four of them were
    # wired, so ':alpha' and a typo like ':ruff' both validated, printed in the
    # override list, and then did nothing -- an override that silently does
    # nothing is worse than one that is rejected, because the build looks right.
    if _k not in ("base", "metal", "rough", "emis", "alpha"):
        raise SystemExit("ABORT: VRM_TEX kind %r is not one this builder reads "
                         "(base, metal, rough, emis, alpha)" % _k)
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
# The trailing 'map' is optional on EVERY token, not just on 'normal'.
# Gwen Stacy's files are GwenStacyDifuselMap / NormalMap / MetallnessMap, and
# with 'map' spelled out only after 'normal' her base stem kept 'difuselmap'
# whole -- see the set-of-one note below for what that then cost her.
MAPTOK = re.compile(
    r"[_\- ]*(base[_\- ]?colou?r|albedo(?:transparency)?|diffuse|difuse|difusel|"
    r"normal|nrm|metal(?:lic|ness)?|rough(?:ness)?|specular|spec|"
    r"emissive|emission|height|bump|opacity|alpha|ao|occlusion|oclussion)"
    r"[_\- ]?(?:map)?$", re.I)


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


# A packed metallicRoughness map, shipped pre-split into per-channel files.
#
# glTF packs one texture: R = occlusion, G = ROUGHNESS, B = METALLIC. A material
# that wires that single file to BOTH its Metallic and its Roughness input is
# correct -- the shader reads a different channel for each. But some archives
# ship it already split, as 'BODY_metallicRoughness@channels=B.png' and
# '...@channels=G.png', and then the material's own reference is no longer
# enough: following it faithfully hands ONE channel's file to both slots.
#
# The Mandalorian shipped chrome-plated for exactly that. His armour's real
# roughness map is a flat 1.000 and his cape's is 1.000, and both were given the
# B channel instead -- 0.520 and 0.613 -- so fully rough plate and cloth
# rendered as polished metal, which reads as smeared, shifted texturing.
#
# Every one of these filenames contains "metallicRoughness" and "metal", so no
# amount of word matching separates them. The channel letter is the only thing
# that does.
_CHANNEL_KIND = {"r": "ao", "g": "rough", "b": "metal"}
_CHANNEL_RE = re.compile(r"(channels?\s*=\s*)([RGB])(?![A-Za-z0-9])", re.I)


def channel_kind(name):
    """The map type an '@channels=X' marker implies, or None."""
    m = _CHANNEL_RE.search(name)
    return _CHANNEL_KIND.get(m.group(2).lower()) if m else None


def channel_sibling(path, kind):
    """The same split set's file for `kind`, if this one is the wrong channel."""
    want = next((c for c, k in _CHANNEL_KIND.items() if k == kind), None)
    if want is None or not path:
        return None
    base = os.path.basename(path)
    if channel_kind(base) in (None, kind):
        return None
    alt = _CHANNEL_RE.sub(lambda m: m.group(1) + want.upper(), base)
    for f in files:
        if f.lower() == alt.lower():
            return os.path.join(TEXDIR, f)
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
    _hit = None
    if stem in _STEM_POOL:
        _hit = _STEM_POOL[stem]
    else:
        hits = [v for k, v in _STEM_POOL.items()
                if len(os.path.commonprefix([k, stem])) >= 12
                and (k.startswith(stem) or stem.startswith(k))]
        _hit = hits[0] if len(hits) == 1 else None
    # The author named one packed map; the folder holds it split per channel.
    # Take the channel this slot actually wants.
    _kind = {"Metallic": "metal", "Roughness": "rough"}.get(slot)
    if _hit and _kind:
        _sib = channel_sibling(_hit, _kind)
        if _sib:
            print("    channels: %s wants %s, so '%s' -> '%s'"
                  % (slot, _kind, os.path.basename(_hit), os.path.basename(_sib)))
            return _sib
    return _hit


def _toks_eq(mat_name, path):
    """Is this file named for THIS material, rather than merely containing it?

    'RedEyes' against 'Eyes.png' shares a word and is not a match; 'PomniEyes'
    against 'PomniEyes.png' is. Compared as tokens, because stripping the
    separators is what made Eye/Eyelash indistinguishable elsewhere.
    """
    _split = lambda s_: [x.lower() for x in
                         re.split(r"[^0-9a-zA-Z]+", MAPTOK.sub(" ", s_)) if x]
    _m = _split(mat_name)
    _f = _split(os.path.splitext(os.path.basename(path))[0])
    return _m == _f or _f[:len(_m)] == _m or _m[:len(_f)] == _f


def _SET_OF(prefix):
    """The files that belong to one material's texture SET.

    A set exists to stop a map being borrowed from the wrong one -- Link's
    tunic took the equipment metalness and came out chromed. But the prefix is
    derived from the base colour's filename with its map token stripped, and
    when that strip fails the prefix is the whole stem, so the set contains the
    base file and nothing else. The rule "take only from this set" then means
    "take nothing", silently.

    That is what happened to Gwen Stacy: 'GwenStacyDifuselMap' kept its token,
    the set was one file, and her normal and metalness maps were sitting in the
    same folder being ignored. A set of one carries no information, so say so
    and let the ordinary pick run."""
    return [f for f in files
            if norm(os.path.splitext(f)[0]).startswith(prefix)]


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

# UniGLTF's merged-texture name: `<A>_Diffuse-<B>_Opacity.png`, the diffuse
# and the opacity joined across a hyphen. The hyphen is what makes this safe to
# match on -- `Hair_1001_Transparency_Diffuse.jpeg` is a plain diffuse used as a
# mask and must not be caught by it.
_MERGED_RE = re.compile(
    r"(?:diffuse|base_?color|albedo)[^-]*-[^-]*(?:opacity|alpha)", re.I)


def _is_glow_mask(path):
    """Is this emissive map a MASK, or just a copy of the base colour?

    Daz writes a full PBR channel set per surface, and that set includes an
    emission-COLOUR map for every surface whether or not it glows. In Daz that
    map is gated by an emission STRENGTH, which no FBX carries, so arriving
    here it looks exactly like a glow mask -- and wiring it sets strength 1.0
    and the surface lights itself up. Ariel shipped `Irises_Emissive.png` that
    way, at emissiveFactor [1,1,1].

    Mean brightness is the obvious test and it is the WRONG one. It looked
    decisive on a sample of two (Master Chief 0.0, Ariel 88) and fell apart on
    the full set: in linear terms Thanos's gauntlet sits at 0.013 and K-2SO's
    DROID_Misc at 0.044, both genuine, leaving no honest gap.

    What actually distinguishes them is not how bright the map is but how much
    of it is lit. A glow mask is LOCAL -- a visor, a gauntlet, a pair of eyes --
    on a black field. A colour copy covers the whole UV layout:

        MKV_Helmet              99.98% black    0.01% lit
        DROID_Body              99.90% black    0.03% lit
        Thanos gauntlet         95.43% black    4.06% lit
        Clone Phase1 helmet     93.73% black    4.17% lit
        DROID_Misc              89.91% black    9.10% lit
        Prix eyes               43.82% black    0.92% lit
        Ariel Irises             0.00% black  100.00% lit   <-- not one black pixel

    Every genuine mask lights at most 9.1% of its area; the copy lights all of
    it. The threshold is 50% -- five times clear of the genuine maps on one
    side and twice clear of the copy on the other.
    """
    try:
        img = bpy.data.images.load(path, check_existing=True)
    except Exception:
        return True
    w, h = img.size
    if w == 0 or h == 0:
        return True
    try:
        import numpy as np
        px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
        lum = px.reshape(-1, 4)[:, :3].max(axis=1)
        lit = float((lum > 0.05).mean())
    except ImportError:
        px = list(img.pixels)
        n = 0; hot = 0
        for i in range(0, w * h * 4, 4 * 97):
            if max(px[i], px[i + 1], px[i + 2]) > 0.05:
                hot += 1
            n += 1
        lit = float(hot) / max(n, 1)
    return lit <= 0.5


def _alpha_varies(img):
    """Does this image's alpha channel carry anything?

    An opacity map stored with an alpha channel that is flat 1.0 everywhere is
    an RGB mask wearing an RGBA container, and reading its alpha would report
    "fully opaque" for a surface whose mask is in the colour. Only trust the
    alpha channel when it actually varies.
    """
    w, h = img.size
    if w == 0 or h == 0:
        return False
    try:
        import numpy as np
        px = np.empty(w * h * 4, dtype=np.float32); img.pixels.foreach_get(px)
        a = px.reshape(-1, 4)[:, 3]
        return float(a.max() - a.min()) > 0.02
    except ImportError:
        px = list(img.pixels)
        lo, hi = 1.0, 0.0
        for i in range(3, w * h * 4, 4 * 97):
            lo = min(lo, px[i]); hi = max(hi, px[i])
        return (hi - lo) > 0.02


def _bake_opacity_into_base(nt, bsdf, base_tex, ap):
    """Put the opacity map INTO the base colour texture's alpha channel.

    glTF has no separate opacity map. Alpha is baseColorTexture's own alpha
    channel times baseColorFactor.a, and nothing else. Wiring a second image
    into the Principled node's Alpha input is therefore a Blender-side
    arrangement that has to survive a translation, and once mtoon1 is enabled
    -- which this builder does for every cutout, because without it alphaMode
    ships OPAQUE -- MToon carries ONE base colour texture and the second image
    has nowhere to go. It is dropped silently.

    Measured on Ariel, whose Cornea_Opacity.png is 100% below 10% opacity and
    whose Cornea_BaseColor.png is pure white: the exported Cornea texture came
    out RGB, with no alpha channel at all, so alpha fell back to 1.0, every
    pixel passed the MASK cutoff, and an opaque white shell was drawn over her
    eyes. Her Hair Cap failed the same way and painted a pale band across her
    forehead -- one bug, two symptoms that look unrelated.

    So do the merge here rather than hoping the exporter does it. After this
    the alpha is in the one place glTF reads, and no later stage can lose it.
    """
    bi = getattr(base_tex, "image", None)
    if bi is None or tuple(bi.size) == (0, 0):
        return False
    try:
        op = bpy.data.images.load(ap, check_existing=True)
    except Exception:
        return False
    if tuple(op.size) == (0, 0):
        return False
    op.colorspace_settings.name = "Non-Color"

    # WHICH CHANNEL of the opacity file actually holds the opacity.
    #
    # Not always the colour. UniGLTF writes a MERGED texture named
    # `<A>_Diffuse-<B>_Opacity.png`, whose RGB is the diffuse and whose alpha
    # is the mask, and the builder's name matcher picks those up as opacity
    # maps. Heels has six, and they are not alike -- `img.depth` tells them
    # apart where the name cannot:
    #
    #   High_Heels_Diffuse-High_Heels_Opacity        24  RGB, grey  dark leather
    #   Underwear_Bottoms_Diffuse-..._Opacity        24  RGB        coloured
    #   Std_Eyelash_Diffuse-Std_Eyelash_Opacity       8  grey       a real mask
    #   Std_Tearline_L_Diffuse-..._R_Opacity         16  grey+A     mask in A
    #   tail_Transparency_Diffuse-..._Opacity        32  RGBA       mask in A
    #
    # Taking the colour channel of the first of those put the shoes at 0.25,
    # under the 0.5 MASK cutoff, and HER SHOES VANISHED -- a regression this
    # fix would have introduced had the rebuild not been rendered before being
    # shipped. A merged file that arrives with no alpha channel has lost its
    # opacity altogether and carries nothing usable, so decline it and let the
    # caller fall back to the old separate-node path, which is what produced
    # the correct opaque shoe.
    _depth = getattr(op, "depth", 24)
    if _depth in (16, 32) and _alpha_varies(op):
        _chan = 3                      # the alpha channel really is the mask
    elif _depth == 8:
        _chan = 0                      # one channel can only ever be a mask
    elif _MERGED_RE.search(os.path.basename(ap)):
        print("    opacity %s is a merged diffuse whose alpha channel is gone "
              "-- it carries no opacity, declining to bake it"
              % os.path.basename(ap))
        return False
    else:
        _chan = 0

    w, h = bi.size
    if tuple(op.size) != (w, h):
        op = op.copy()
        try:
            op.scale(w, h)
        except Exception:
            return False
    n = w * h * 4
    try:
        import numpy as np
        bp = np.empty(n, dtype=np.float32); bi.pixels.foreach_get(bp)
        o_ = np.empty(n, dtype=np.float32); op.pixels.foreach_get(o_)
        bp[3::4] = o_[_chan::4]
        buf = bp
    except ImportError:
        bp = list(bi.pixels); o_ = list(op.pixels)
        bp[3::4] = o_[_chan::4]
        buf = bp
    # A float buffer, so the linear values read out of `pixels` go back in
    # without an 8-bit sRGB round trip mangling them. The colour space is
    # copied from the source for the same reason: `pixels` is scene-linear,
    # and tagging the copy differently would re-encode the RGB.
    new = bpy.data.images.new(bi.name + "_OPA", w, h, alpha=True, float_buffer=True)
    try:
        new.colorspace_settings.name = bi.colorspace_settings.name
    except Exception:
        pass
    try:
        new.pixels.foreach_set(buf)
    except Exception:
        new.pixels = list(buf)
    new.pack()
    base_tex.image = new
    if "Alpha" in bsdf.inputs:
        for l in list(bsdf.inputs["Alpha"].links):
            nt.links.remove(l)
        nt.links.new(base_tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return True


def _mostly_clear_under_uvs(mat, path):
    """Is this candidate base map transparent where THIS material's faces use it?

    A name match is a substring match, and the token guard beside it only
    protects a material that carries an authored colour. Pomni's 'PomniEyes'
    is the white of her eye -- 0.814 grey, no texture of its own in the file --
    and it took 'Eyes.png' because "Eyes" is inside "PomniEyes". Measured
    against its own UVs that map is 67% FULLY CLEAR, and shipped opaque those
    clear pixels render as the black underneath them: the marks above and
    below her iris.

    A name is a guess; this is a measurement, and it is the right one. A base
    colour map is not two-thirds transparent across the geometry that uses it.
    Materials that really are see-through take the cutout or blend path, where
    the transparency is the point and this test is never reached.

    Returns True only when it actually sampled something -- a file it cannot
    read, or a material with no faces, is not evidence of anything.
    """
    try:
        img = bpy.data.images.load(path, check_existing=True)
        if img.channels != 4 or not img.has_data:
            return False
        probe = img.copy()
        probe.scale(128, 128)
        buf = [0.0] * (128 * 128 * 4)
        probe.pixels.foreach_get(buf)
        bpy.data.images.remove(probe)
    except Exception:
        return False
    hits = 0
    clear = 0
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.materials:
            continue
        idx = [i for i, m in enumerate(o.data.materials) if m is mat]
        if not idx:
            continue
        uvl = o.data.uv_layers.active
        if uvl is None:
            continue
        uvd = uvl.data
        for poly in o.data.polygons:
            if poly.material_index not in idx:
                continue
            for li in poly.loop_indices:
                u, v = uvd[li].uv
                x = int(min(127, max(0, (u % 1.0) * 128)))
                y = int(min(127, max(0, (v % 1.0) * 128)))
                hits += 1
                if buf[(y * 128 + x) * 4 + 3] < 0.02:
                    clear += 1
            if hits > 40000:
                break
    if hits < 64:
        return False
    return (float(clear) / hits) > 0.5


# Does this file's base colours mean anything at all?
#
# The guard below lets a material's own colour veto a texture that merely
# shares a word with its name -- the fix for Pomni, whose RedEyes and BlueEyes
# are geometry rather than a picture and were being painted over by 'Eyes.png'.
# That guard assumes a colour is art direction. For some exports it is not: the
# colour is a per-material palette the exporter generated, carrying no
# information whatsoever.
#
# Ariel is the measured case. All 26 of her materials carry a different
# saturated pastel -- a PURE GREEN cornea (0.03, 1.0, 0.03), teal teeth, yellow
# toenails. Nobody authored that. The veto then fired on the three that needed
# it least, and her eyebrows shipped purple, her eyelashes pink and her scalp
# cap navy, painting a pale band across her forehead.
#
# Authored colours and generated ones separate cleanly when measured, because a
# real one is almost always either NEUTRAL (grey, white, black) or HUE-PURE (a
# primary, with its other channels near zero), while a generated palette is
# spread across mid-range pastels where neither holds:
#
#     Pomni      100%   0.8 greys, pure black, and Red/Blue/Yellow primaries
#     Heels      100%   Peach 100%   Alice Ivy 95%   Alcina 85%   Gordon 86%
#     Peacemaker  50%   muted but real: navy, brown hair, skin, neutral silver
#     Ariel        4%   <-- generated
#     Power Girl   0%   <-- generated, and its materials are named 'mesh0'
#
# Measured over every build log in the rollout: nothing else in the whole set
# falls below 79%. The threshold sits at 25%, which is a factor of two clear of
# Ariel on one side and of Peacemaker on the other -- deliberately well under
# Peacemaker, because the test UNDER-counts muted-but-real colours and it is
# the generated palettes that have to be unmistakable.
def _palette_is_generated():
    cols = []
    for _m in bpy.data.materials:
        if _m.name not in used or not _m.use_nodes:
            continue
        _b = next((n for n in _m.node_tree.nodes
                   if n.type == "BSDF_PRINCIPLED"), None)
        if _b is None or "Base Color" not in _b.inputs:
            continue
        try:
            cols.append(tuple(_b.inputs["Base Color"].default_value[:3]))
        except (TypeError, KeyError):
            continue
    if len(cols) < 4:
        return False
    good = 0
    for c in cols:
        mn, mx = min(c), max(c)
        if (mx - mn) < 0.05 or mn < 0.12:
            good += 1
    frac = float(good) / len(cols)
    gen = frac < 0.25
    print("  palette: %d of %d base colours are neutral or hue-pure (%.0f%%)%s"
          % (good, len(cols), frac * 100,
             " -- GENERATED, so a colour cannot veto a texture" if gen else ""))
    return gen


_PALETTE_GENERATED = _palette_is_generated()

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
    # What did the AUTHOR say about transparency, before this loop rewires
    # anything? Blender 4.5 still carries Material.blend_method, and a material
    # set to BLEND with an IMAGE wired into its Alpha is a statement, not a
    # guess -- the one case where transparency needs no inference at all.
    #
    # Pomni is why this exists. Her 'EyeDetails' is a detail sheet laid over the
    # eye: 'Eyes.png' feeds Base Color AND Alpha, blend_method BLEND, and the
    # image is 69.2% fully clear. Shipped OPAQUE, those clear pixels render as
    # the black they sit on -- the marks above and below her iris. Inferring a
    # CUTOUT instead was tried and is worse: a blend is not a mask, and masking
    # her eyes made them see-through into her skull. Neither of the two states
    # this loop had was the one the author wrote down.
    _src_blend = getattr(mat, "blend_method", None)
    _src_alpha_img = None
    # Transparency is not always a TEXTURE. A Character Creator cornea is
    # HASHED with a plain Alpha VALUE of 0.553 and nothing wired into it --
    # 55% see-through, so the iris reads through it. The rule below used to
    # demand BLEND *and* an image in Alpha, so a cornea failed both tests,
    # shipped alphaMode OPAQUE and became a solid grey disc over the eye.
    # Measured on Heels and Ariel: blank white eyes in the podium render,
    # while every eye material had its texture all along.
    _src_alpha_val = 1.0
    if bsdf is not None and "Alpha" in bsdf.inputs:
        for _l in bsdf.inputs["Alpha"].links:
            if _l.from_node.type == "TEX_IMAGE" and _l.from_node.image:
                _src_alpha_img = _l.from_node.image
        if not bsdf.inputs["Alpha"].links:
            try:
                _src_alpha_val = float(bsdf.inputs["Alpha"].default_value)
            except Exception:
                _src_alpha_val = 1.0

    # If the source file already told us which texture this material uses, trust
    # that over guessing from the material's name — generic names like
    # 'Material.013' carry no information at all.
    stem = mat_stem(mat)
    wired = []
    base_tex = None
    base_from = None
    # Maps ship in SETS. Once the base colour is chosen, every other map for
    # this material should come from the same set, because a metalness map from
    # the wrong set is not a near miss -- it is a mirror. Link's tunic, hair and
    # skin all took 'LinkEquip_Equipment_Metallic.png' and he came out chromed.
    set_prefix = None
    # Did the FILE wire this material's base map, rather than the folder being
    # searched for one? If so the author already said what this material uses,
    # and the widest pool -- which matches on the MAP-KIND word alone, so every
    # normal map in the folder answers to every material -- has no claim on its
    # other slots. Pomni's 'EyeDetails' carries a packed 'Eyes.png' and was
    # handed 'PomniNSFW_Hair_Normal.png': a HAIR normal map on an eye, matched
    # only because "normal" appears in the filename. Same shape as the rule
    # already written for opacity maps a few lines down in pick(): it comes
    # from a file that names the material, or not at all.
    _base_authored = False
    # A near-miss in the NAME pool was still the closest thing in the folder.
    # Falling through to the widest pool after declining it would reach for
    # something further away still, so the decline is final.
    _name_declined = False
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
                # An operator naming the map in VRM_TEX is the STRONGEST
                # provenance there is -- stronger than the author's own wiring,
                # which is itself stronger than any name match. This line was
                # missing, so the cutout gate below, which tests `base_from`,
                # treated a hand-pinned map as having no provenance at all and
                # refused to look at its alpha. Alcina's hair is pinned that
                # way and was one of the two materials that fault was found on.
                base_from = "override"
                _base_authored = True
            wired.append((kind, "override:" + os.path.basename(_ov)))
            continue
        keep = already_good(bsdf, slot)
        if keep is not None:
            if kind == "base":
                base_tex = keep
                _base_authored = True
            wired.append((kind, "packed:" + (keep.image.name or "?")))
            continue
        if set_prefix and len(_SET_OF(set_prefix)) > 1 and kind != "base":
            # The set is the answer, including when the answer is "this set has
            # no such map". Borrowing one from another set is not a near miss:
            # Link's tunic took the equipment metalness and came out chromed.
            p = choose([f for f in files
                        if norm(os.path.splitext(f)[0]).startswith(set_prefix)], kind)
        else:
            p = authored(bsdf, slot)
            _from = "authored" if p else None
            if p is None and stem:
                p = pick_stem(stem, kind)
                _from = "stem" if p else None
            if p is None:
                p = pick(mat.name, kind, wide=_default_col)
                _from = "name" if p else None
                # A NAME match is a substring match, and a material that
                # carries a real authored colour has everything it needs
                # already. Pomni's iris is geometry, not a picture: 'RedEyes'
                # is (0.800, 0.005, 0.017) and 'BlueEyes' is (0.027, 0.049,
                # 0.800), and the pinwheel is those two colours in alternating
                # segments. Both were handed 'Eyes.png' because "Eyes" is a
                # substring of "RedEyes" -- and once a base texture exists the
                # exported factor is forced to white, so the red and the blue
                # were thrown away and her irises shipped blank.
                #
                # The guard that keeps her plain Red/Blue/Yellow flat only
                # covers the loose global pool. This is the same mistake one
                # step earlier, and the same answer: when the colour is
                # authored, the texture has to be named for THIS material, not
                # merely contain its name. 'PomniEyes' sits at 0.814 grey --
                # no authored colour -- so it still takes the map.
                if (p is not None and kind == "base" and not _default_col
                        and not _PALETTE_GENERATED
                        and _toks_eq is not None
                        and not _toks_eq(mat.name, p)):
                    print("    %s carries its own colour %s and '%s' only "
                          "shares a word with it -- keeping the colour"
                          % (mat.name, tuple(round(c, 3) for c in _bc),
                             os.path.basename(p)))
                    p, _from = None, None
                # The same weak claim, where the colour cannot speak for the
                # material. Measure the map against the geometry instead.
                elif (p is not None and kind == "base"
                        and _toks_eq is not None and not _toks_eq(mat.name, p)
                        and _mostly_clear_under_uvs(mat, p)):
                    print("    %s only shares a word with '%s', and that map "
                          "is transparent over most of %s's own UVs -- "
                          "keeping the flat colour"
                          % (mat.name, os.path.basename(p), mat.name))
                    p, _from = None, None
                    _name_declined = True
        if p is None and kind == "base" and slot in bsdf.inputs:
            # Nothing named this material and nothing shares a word with its
            # mesh. Whether it WANTS a texture is readable from the material
            # itself: one sitting at default white was expecting a map (this
            # file's 'HairFace' and 'Scalp'), while one carrying a real colour
            # is meant to be flat and must keep it - handing Pomni's Blue, Red
            # and Yellow a texture from the global pool wiped her colours out.
            col = bsdf.inputs[slot].default_value
            if _default_col and not _name_declined:
                p = choose(BY_SIZE, kind, loose=True)
                _from = "loose" if p else None
        if not p or slot not in bsdf.inputs:
            continue
        img = bpy.data.images.load(p, check_existing=True)
        if kind != "base" and kind != "emis":
            img.colorspace_settings.name = "Non-Color"
        if kind == "emis" and not _is_glow_mask(p):
            print("    %s: '%s' lights its whole UV layout -- it is an "
                  "emission-COLOUR copy, not a glow mask, and wiring it makes "
                  "the surface light itself up. Refused."
                  % (mat.name, os.path.basename(p)))
            p = None
            continue
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
        nt.links.new(t.outputs["Color"], bsdf.inputs[slot])
        if kind == "base":
            base_tex = t
            base_from = _from
            if _from == "authored":
                _base_authored = True
            _st = norm(MAPTOK.sub("", os.path.splitext(os.path.basename(p))[0]))
            set_prefix = _st if len(_st) >= 4 else None
        wired.append((kind, p))
        if kind == "emis" and "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 1.0
    if already_good(bsdf, "Normal") is not None:
        p = None
    elif set_prefix and len(_SET_OF(set_prefix)) > 1:
        _inset = _SET_OF(set_prefix)
        p = choose(_inset, "normal") or choose(_inset, "height")
    else:
        p = (authored(bsdf, "Normal")
             or (pick_stem(stem, "normal") if stem else None)
             or (pick_stem(stem, "height") if stem else None)
             or pick(mat.name, "normal",
                     wide=_default_col and not _base_authored)
             or pick(mat.name, "height",
                     wide=_default_col and not _base_authored))
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
    # The SET rule applies here more than anywhere, and this was the one slot
    # that skipped it. Heels' material 'Std_Eye_L' was handed
    # 'Std_Eyelash_Diffuse-Std_Eyelash_Opacity.png' by the loose name match,
    # because "Eye" is a prefix of "Eyelash" -- and an eyelash-shaped cutout
    # applied to an eyeball deletes the eye. "Missing eye textures" is the eye
    # being cut away by somebody else's silhouette.
    #
    # A borrowed METALNESS makes a tunic look chrome and you can see what
    # happened. A borrowed OPACITY removes the surface, so there is nothing
    # left to look at and it reads as a texture that never loaded.
    ap = (TEX_OVERRIDE.get((mat.name, "alpha"))
          or (pick_stem(stem, "alpha") if stem else None)
          or pick(mat.name, "alpha"))
    # ...and then CHECK it belongs to this material. The set rule elsewhere
    # keys off set_prefix, which is only computed when the base texture came
    # from a FILE -- Heels' are packed in the .blend, so the guard was never
    # engaged and the loose name match stood.
    #
    # Validate against the base IMAGE's own stem instead, which works for a
    # packed image and a file alike. 'Std_Eye_L_Diffuse' strips to 'std_eye_l';
    # 'Std_Eyelash_Diffuse-Std_Eyelash_Opacity' does not start with it, so it
    # is refused. The two names differ by three letters and "Eye" is a prefix
    # of "Eyelash", which is all it took.
    if ap and base_tex is not None and base_tex.image:
        _bn = (os.path.basename(base_tex.image.filepath or "")
               or base_tex.image.name or "")
        # TOKENS, not a normalised string. norm() strips the separators, and
        # that is precisely the boundary that tells these two apart:
        # 'Std_Eye_L' normalises to 'stdeyel', which really is a prefix of
        # 'stdeyelash'. Comparing the stripped strings accepted the eyelash
        # map for the eye a second time, for a new reason.
        def _toks(_name):
            _t = re.split(r"[^0-9a-zA-Z]+", MAPTOK.sub(" ", _name))
            return [x.lower() for x in _t if x]

        _bt = _toks(os.path.splitext(_bn)[0])
        _at = _toks(os.path.splitext(os.path.basename(ap))[0])
        _bstem, _astem = "_".join(_bt), "_".join(_at)
        if (len(_bt) >= 2 and _at[:len(_bt)] != _bt
                and _bt[:len(_at)] != _at):
            print("    opacity %s belongs to '%s', not to '%s' -- refused, "
                  "because a borrowed cutout deletes the surface"
                  % (os.path.basename(ap), _astem, _bstem))
            ap = None
    cut = False
    blend = False
    blend_alpha = 1.0
    if ap and "Alpha" in bsdf.inputs:
        # Bake it into the base map's alpha channel where glTF reads it. The
        # separate-node arrangement below is kept only for a material that has
        # no base texture to bake into; see _bake_opacity_into_base.
        if base_tex is not None and _bake_opacity_into_base(nt, bsdf, base_tex, ap):
            print("    opacity %s baked into the base map's alpha channel"
                  % os.path.basename(ap))
        else:
            img = bpy.data.images.load(ap, check_existing=True)
            img.colorspace_settings.name = "Non-Color"
            t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
            nt.links.new(t.outputs["Color"], bsdf.inputs["Alpha"])
        wired.append(("alpha", ap))
        cut = True
    # A dedicated opacity map is the first choice, and plenty of characters
    # have none. Killer Clown's hair is hair CARDS -- her 'hair_base_color.png'
    # is 60.7% fully transparent, 38.9% fully opaque and 0.3% in between, a
    # textbook cutout mask -- and with no opacity map beside it the cards
    # shipped solid. "Her hair doesn't seem to have a texture" is a black slab
    # where the gaps between the cards should be.
    #
    # Inferring this from the base map's own alpha was tried once and withdrawn,
    # and the reason is worth being exact about, because it was NOT that alpha
    # inference is wrong. Prix's hair mesh is 'CN_F_HAIR_111' and the only hair
    # texture in her folder is 'CN_F_HAIR_110_hair.png': a DIFFERENT hair
    # model's atlas, reached by the loose global-pool fallback. Its alpha cut
    # away the wrong regions and left her bald. The fault was the provenance of
    # the texture, not the channel inside it.
    #
    # So infer, but only from a map this material can actually claim -- one that
    # was authored in the file, or matched its mesh stem, or matched its own
    # name -- never from the loose pool. And only when the alpha carries a
    # SHAPE: mostly-two-valued, and neither almost entirely transparent (which
    # would erase the mesh) nor almost entirely opaque (which would do nothing
    # and risks nibbling edges for no gain).
    # OPT-IN, because inferring a cutout is a guess about what an alpha channel
    # MEANS and the cost of guessing wrong is geometry that disappears. It is
    # right for Killer Clown -- hair cards, no opacity map, 60.7% clear -- and
    # it was wrong for Pomni, whose eye materials carry an alpha that is not a
    # cutout at all: inferred one and her eyes went see-through in game,
    # showing the inside of her head. The renders and every count said she was
    # fine. VRM_CUTOUT_INFER=1 asks for it.
    # `_base_authored` as well as `base_from`, and leaving it out was a hole in
    # exactly the strongest case. When the source material already had an image
    # wired into Base Color, `already_good` keeps it and sets `_base_authored`
    # -- but it never sets `base_from`, which stays None. So the one provenance
    # nobody could argue with, the author's own wiring, was the one the gate
    # refused. Peach is the character that showed it: every one of her maps is
    # packed in the .fbx, so VRM_CUTOUT_INFER=1 printed nothing at all and her
    # iris and eyelash layers shipped OPAQUE over her eyes.
    #
    # VRM_CUTOUT_MATERIALS="a;b;c" asks for the same inference on NAMED
    # materials only, which is what a character needs when the sweep is right
    # about some of its materials and wrong about others. Peach again: the
    # alpha on her iris, eyelash and eyelid maps is a clean two-valued mask and
    # the inference is exactly right, while the alpha on her crown is an
    # OUTLINE -- taking it as a cutout carved the jewel out of the setting and
    # left a wire ring. "77.4% solid" said nothing about which 77.4%.
    _cut_names = [s.strip() for s in
                  os.environ.get("VRM_CUTOUT_MATERIALS", "").split(";")
                  if s.strip()]
    _cut_want = (mat.name in _cut_names if _cut_names
                 else bool(os.environ.get("VRM_CUTOUT_INFER")))
    if (_cut_want
            and not cut and base_tex is not None
            and (_base_authored or base_from in ("authored", "stem", "name"))
            and "Alpha" in bsdf.inputs and base_tex.image
            and base_tex.image.channels == 4):
        try:
            # Read the alpha at FULL RESOLUTION. This used to copy the image,
            # `scale(96, 96)` it and measure that -- and Blender's scale is a
            # filtered resize, which AVERAGES. Averaging is the one operation
            # guaranteed to destroy the property the test is looking for: a
            # two-valued mask blurred down to 96x96 stops being two-valued, and
            # the finer and sparser the mask the worse it gets. Eyelashes and
            # hair cards are exactly that.
            #
            # Measured on Alcina Dimitrescu's `CILIOS` eyelash map: 87.1% clear
            # / 0.4% solid at full resolution, which passes, and 79.0% / 0.0%
            # after the averaging resize, which fails. The test rejected her
            # lashes because of its own instrument, and they shipped as two
            # black slabs over her eyes. Her hair atlas survived (0.930 against
            # 0.830) only because it is denser.
            #
            # numpy is used for the same reason it is used three times above --
            # a 1024x1024 RGBA image is 4.2 million floats, and a Python list
            # of those costs more than a hundred megabytes.
            import numpy as _np
            _im = base_tex.image
            _w, _h = _im.size
            _arr = _np.empty(_w * _h * 4, dtype=_np.float32)
            _im.pixels.foreach_get(_arr)
            _a = _arr[3::4]
            _clear = float((_a < 0.02).mean())
            _solid = float((_a > 0.98).mean())
            if 0.05 <= _clear <= 0.90 and (_clear + _solid) >= 0.80:
                nt.links.new(base_tex.outputs["Alpha"], bsdf.inputs["Alpha"])
                cut = True
                print("    %s: cutout from the base map's own alpha (%.1f%% "
                      "clear, %.1f%% solid, matched by %s)"
                      % (mat.name, 100.0 * _clear, 100.0 * _solid,
                         base_from or ("the author's own wiring"
                                       if _base_authored else "?")))
        except Exception as _e:
            print("    (could not read the base map's alpha: %s)" % _e)

    # VRM_BLEND_MATERIALS="a;b" -- the third state, named per material.
    #
    # Opaque, cutout and blended are three different things and only two of
    # them had a lever. Gordon Freeman's glasses are why: his `lens` material
    # carries a base map whose alpha has NO extremes at all (0.0% fully clear,
    # 0.0% fully solid, median 63/255) -- a uniformly semi-transparent pane,
    # which is what a lens is. There is no cutoff that expresses that. Masking
    # it at 0.5 would punch a mottled hole; leaving it opaque, which is what
    # shipped, drew two solid white rectangles over his eyes.
    #
    # Named rather than inferred, and after the same kind of per-material look
    # that VRM_CUTOUT_MATERIALS needs, because in a game rip an alpha channel
    # is as likely to be a SPECULAR mask as an opacity map. Gordon has three
    # alpha channels and only one is opacity: honouring `eye-iris-green.tga`
    # would make his irises invisible, since its alpha is black exactly on the
    # iris disc, and honouring `onefreeman` would erase his whole suit, since
    # its alpha is ~0 everywhere. The way to tell is to ask what the texture is
    # FOR and whether honouring its alpha would erase that.
    # IT OVERRIDES AN ESTABLISHED CUTOUT, and that is a deliberate reversal of
    # the precedence every other branch here follows. The guard used to be
    # `not cut`, which made this switch a no-op on exactly the materials that
    # needed it most: a dedicated opacity map sets `cut` before this runs, so
    # naming such a material did nothing and the cutout shipped. That is how
    # Heels' eyelashes came to be **99.6% clipped away** -- her lash alpha is
    # feathered, the 0.5 MASK threshold throws away almost all of it, and the
    # one lever that could have said otherwise declined to fire.
    #
    # "A dedicated opacity map is the stronger signal" is right when the
    # question is OPAQUE vs not. It is not an answer to MASK vs BLEND, which
    # is a question about the SHAPE of the alpha, not its provenance. An
    # explicit name from a person who has looked at the texture outranks an
    # inference either way, so this branch now wins over `cut`. `blend`
    # already dominates `cut` everywhere it is read (blend_method,
    # mtoon1.enabled, alpha_mode), so nothing else has to change.
    _blend_names = [s.strip() for s in
                    os.environ.get("VRM_BLEND_MATERIALS", "").split(";")
                    if s.strip()]
    if (mat.name in _blend_names and base_tex is not None
            and bsdf is not None and "Alpha" in bsdf.inputs
            and base_tex.image and base_tex.image.channels == 4):
        if not bsdf.inputs["Alpha"].links:
            nt.links.new(base_tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        print("    %s: blended on its base map's own alpha, by name%s"
              % (mat.name,
                 " -- OVERRIDING the cutout a dedicated opacity map had "
                 "already established" if cut else ""))
        blend = True
        cut = False

    # Honour the authored blend. Not a guess about what an alpha channel MEANS
    # -- the material was SET to BLEND with that image in its Alpha, and all
    # this does is carry that across. Only when a cutout was not already
    # established, since a dedicated opacity map is the stronger signal.
    elif not cut and _src_blend == "BLEND" and _src_alpha_img is not None             and bsdf is not None and "Alpha" in bsdf.inputs:
        _at = None
        if base_tex is not None and base_tex.image == _src_alpha_img:
            _at = base_tex
        else:
            _at = nt.nodes.new("ShaderNodeTexImage")
            _at.image = _src_alpha_img
        if not bsdf.inputs["Alpha"].links:
            nt.links.new(_at.outputs["Alpha"], bsdf.inputs["Alpha"])
        blend = True
        print("    the source material is BLEND with '%s' in its Alpha -- "
              "keeping it blended rather than flattening it to opaque"
              % _src_alpha_img.name)

    # The same statement made with a VALUE instead of a texture. HASHED counts
    # as well as BLEND: Blender's dithered transparency is still transparency,
    # and a cornea is the common case. The alpha has to travel on the base
    # colour FACTOR, since there is no map to carry it.
    #
    # OPT-IN, and the reason is worth keeping. Carrying the value across is
    # FAITHFUL to the source and still made Heels WORSE: her Std_Cornea_L/R sit
    # at HASHED alpha 0.553, and with the cornea opaque its own diffuse was
    # drawing her iris. Export it 55% transparent and the iris washes out
    # against the white sclera behind it -- measured on a head close-up, before
    # and after. On the podium at character-select distance it changed nothing
    # either way, so the blank-eye look that started this has a different
    # cause and is still open. Faithful is not the same as correct.
    elif (os.environ.get("VRM_VALUE_ALPHA")
            and not cut and _src_blend in ("BLEND", "HASHED")
            and _src_alpha_img is None and _src_alpha_val < 0.99):
        blend = True
        blend_alpha = _src_alpha_val
        print("    the source material is %s at alpha %.3f with nothing wired "
              "into it -- keeping it that transparent rather than flattening "
              "it to opaque" % (_src_blend, _src_alpha_val))

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
    for attr, val in (("blend_method", "BLEND" if blend else "CLIP"),
                      ("shadow_method", "CLIP"),
                      ("surface_render_method",
                       "BLENDED" if (cut or blend) else "DITHERED")):
        try: setattr(mat, attr, val)
        except Exception: pass
    try:
        mt = mat.vrm_addon_extension.mtoon1
        # `mtoon1.enabled` defaults to FALSE, and the exporter only writes the
        # extension's alpha_mode when it is on. Setting alpha_mode alone was
        # therefore inert: every material in every character exported
        # alphaMode=OPAQUE, and a cutout material -- hair cards, eyelashes,
        # lace, a tear line -- shipped as a solid slab. Heels is where it
        # showed: her installed build carries ten textures UniGLTF merged from
        # a diffuse and an opacity map, which it only does for a material that
        # is not opaque, and her rebuild had none.
        #
        # Turned on only for the materials that NEED a cutout. Enabling MToon
        # across a whole character swaps its shading model, which is a much
        # larger change than this defect warrants.
        #
        # It has a cost, and it is worth naming because it is invisible until
        # it lands on a big surface: a character ends up with TWO shading
        # models, MToon on its cutouts and standard PBR on everything else.
        # Hair cards, eyelashes and tear lines are small enough that nobody
        # notices. Peach's face is not -- hers is split across meshes, with
        # `Peach_faceN` carrying a rectangular hole that `Peach_Blink_VoiceA`
        # fills, and the moment the filling plate became a cutout it turned
        # unlit while the face around it stayed lit. A tan plate on a cream
        # face, with a hard polygon seam straight across her brow.
        #
        # VRM_MTOON_ALL=1 puts the whole character on one shading model, which
        # is the answer when a cutout shares a continuous surface with an
        # opaque material. It is opt-in because for most characters the
        # swap is the larger change.
        if cut or blend or os.environ.get("VRM_MTOON_ALL"):
            mt.enabled = True
        mt.alpha_mode = "BLEND" if blend else ("MASK" if cut else "OPAQUE")
        mt.alpha_cutoff = 0.5
        # Once mtoon1 is in play the exporter writes ITS base colour factor,
        # which starts at white, and the Principled node's colour never leaves
        # Blender. A material whose whole appearance is a flat colour -- Jessica
        # Rabbit's red hair, Pomni's Blue/Red/Yellow -- then ships pure white,
        # which is indistinguishable from a missing texture.
        # blend_alpha carries a transparency the source stated as a VALUE
        # rather than a map. With no texture to hold it, the base colour
        # factor's alpha is the only place it can travel.
        if base_tex is None:
            mt.pbr_metallic_roughness.base_color_factor = (
                _bc[0], _bc[1], _bc[2], blend_alpha)
        else:
            mt.pbr_metallic_roughness.base_color_factor = (
                1.0, 1.0, 1.0, blend_alpha)
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

# Fill in a finger chain the model does not have.
#
# YARG's AddMicrophoneToCharacter reads SIX bones off the humanoid map --
# rightHand, rightThumbDistal, rightLittleDistal, rightLittleProximal,
# rightIndexIntermediate, rightIndexProximal -- and a null one throws. The
# throw escapes before LoadCharacter can put the character on the Venue layer,
# so the character loads and is then INVISIBLE, which in game reads as "he
# doesn't show up at all, just a floating mic".
#
# Alastor is the case: his rig is a four-fingered cartoon hand with index, ring
# and thumb only, so rightLittle* genuinely do not exist and no mapping can
# find them. Note the game computes `littleGripCenter` from them and then never
# uses it -- the mic is placed from the index. The bones only have to be
# non-null.
#
# So synthesise them FUSED to a real finger: each new bone sits exactly on its
# donor counterpart and is parented to it, so it moves in lockstep rather than
# hanging beside the hand as a separate digit. That is what a four-fingered
# hand is anyway -- the outermost finger does the work of two -- and it means
# any animation that drives the little finger drives it correctly instead of
# waving a bone through empty space. The fused bones carry NO weight, so they
# change nothing about how the character deforms. VRM_FILL_FINGERS=0 opts out.
if os.environ.get("VRM_FILL_FINGERS", "1") != "0":
    # VRM names the thumb's joints differently from the other four.
    _FINGER_PARTS = {
        "thumb":  ("metacarpal", "proximal", "distal"),
        "index":  ("proximal", "intermediate", "distal"),
        "middle": ("proximal", "intermediate", "distal"),
        "ring":   ("proximal", "intermediate", "distal"),
        "little": ("proximal", "intermediate", "distal"),
    }
    # What YARG's microphone code actually dereferences. A missing one of these
    # is what makes a character invisible; the rest are cosmetic.
    _MIC_NEEDS = ("thumb", "index", "little")

    def _have(_side, _f):
        _parts = _FINGER_PARTS[_f]
        return all("%s_%s_%s" % (_side, _f, _c) in MAP
                   and MAP["%s_%s_%s" % (_side, _f, _c)] in bone_names
                   for _c in _parts)

    _made_fingers = []
    for _side in ("right", "left"):
        _handslot = "%s_hand" % _side
        if _handslot not in MAP or MAP[_handslot] not in bone_names:
            continue
        for _f in _MIC_NEEDS:
            if _have(_side, _f):
                continue
            # Donor: any finger on this hand that IS complete. Prefer a
            # neighbour, so a fused thumb lands on the index rather than
            # across the palm.
            _order = {"thumb": ("index", "middle", "ring", "little"),
                      "index": ("middle", "ring", "little", "thumb"),
                      "little": ("ring", "middle", "index", "thumb")}[_f]
            _donor = next((_d for _d in _order if _have(_side, _d)), None)
            _fparts = _FINGER_PARTS[_f]
            bpy.context.view_layer.objects.active = arm
            bpy.ops.object.mode_set(mode="EDIT")
            _hand_eb = arm.data.edit_bones.get(MAP[_handslot])
            # Positions come from the donor, so the new chain sits ON a real
            # finger. With no complete finger anywhere -- Judy and Miku -- step
            # along the hand instead; the bones are weightless, so this is only
            # about them existing somewhere sane.
            _src_names = ([MAP["%s_%s_%s" % (_side, _donor, _c)]
                           for _c in _FINGER_PARTS[_donor]] if _donor else [])
            # PARENTING MUST BE hand -> proximal -> intermediate -> distal.
            # Parenting each fused bone to its donor counterpart is what a
            # fused finger really is, and VRM rejects it: the exporter dropped
            # the bones silently, the humanoid map still reported 52/52, and
            # the written file had no little finger at all. The POSITION can be
            # fused; the hierarchy cannot. So they sit on the donor and move
            # with the hand rather than with that finger -- which for a
            # weightless bone nothing renders is a distinction without a
            # difference.
            _prev = _hand_eb
            _names = []
            for _i, _c in enumerate(_fparts):
                _nb = arm.data.edit_bones.new(
                    "%s_%s_%s_fused" % (_side, _f, _c))
                if _src_names:
                    _src = arm.data.edit_bones.get(_src_names[_i])
                    _nb.head, _nb.tail, _nb.roll = _src.head, _src.tail, _src.roll
                else:
                    # Along the FOREARM, not along the hand bone: a hand bone
                    # that points straight down (Judy's, 2.5 cm long, tail at
                    # -Z) laid its stubs downward, and with them present the
                    # exported hand came out turned 100 degrees against the
                    # pose the mesh is bound in -- the hands stood UP out of
                    # the cuffs in game. Measured by rest-vs-pose on the
                    # exported file: 106 of 141 bones off with the stubs laid
                    # down the bone, 8 without any.
                    _dir = ((_hand_eb.head - _hand_eb.parent.head)
                            if _hand_eb.parent else _hand_eb.vector)
                    _dir = _dir.normalized() * max(_hand_eb.length, 0.02) * 0.33
                    _nb.head = _hand_eb.head + _dir * (_i + 1)
                    _nb.tail = _hand_eb.head + _dir * (_i + 2)
                    _nb.roll = _hand_eb.roll
                _nb.parent = _prev
                _nb.use_connect = False
                _nb.use_deform = True  # humanoid slots must survive the export
                _prev = _nb
                _names.append(_nb.name)
            bpy.ops.object.mode_set(mode="OBJECT")
            bpy.context.view_layer.update()
            bone_names = set(b.name for b in arm.data.bones)
            for _c, _n in zip(_fparts, _names):
                MAP["%s_%s_%s" % (_side, _f, _c)] = _n
            _made_fingers.append("%s %s on %s" % (_side, _f, _donor or "the hand"))
    if _made_fingers:
        print("  fingers: filled %d missing finger chain(s) with WEIGHTLESS "
              "bones fused to a real one, because YARG's microphone code "
              "dereferences them and a null makes the character INVISIBLE "
              "-- %s" % (len(_made_fingers), ", ".join(_made_fingers)))

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

# Morph targets that nothing can reach are morph targets nobody gets.
#
# YARG reads a VRM's expressions (Assets/Script/Venue/Characters/VRMCharacter.cs)
# and drives exactly one of them from its own events: LipsyncType.Blink maps to
# ExpressionKey.Blink. Its custom-expression dictionary is only ever looked up
# BY LIPSYNC EVENT NAME, so a key called 'Big' or 'SpiralEyes' can sit in the
# file forever and never be asked for.
#
# Measured across the 66 installed characters: not one has a morph bind on ANY
# of its 18 preset expressions. The presets are all there and all empty. So
# every character that ships an eye-closing shape key -- Pomni has 'Closed' on
# each set of lashes -- has a blink available and unwired.
#
# Bind it. The matching is deliberately narrow, because the cost of a wrong
# bind is a character whose face collapses whenever the game blinks: a key
# named blink/wink anywhere counts, and a key named exactly 'Closed' counts
# only on a mesh that is plainly an eyelid or lash. Pomni's face also carries
# 'ClosedTeeth' and 'ClosedTeethVariation', which are mouth shapes, and must
# not be caught. VRM_BLINK="Mesh=Key,Mesh=Key" overrides the lot.
# BAKE A BLINK THE MODEL ANIMATES WITH BONES.
#
# Pomni's blink is four eyelid BONES (EyelidSup/Inf .L/.R) rotating about X on
# frames 26-34 of her 'Animation' action, with the lid meshes skinned to them.
# A VRM expression can only drive a MORPH TARGET, never a bone, so none of that
# is reachable -- and her only bound blink was Lashes/'Closed', which moves two
# tiny lash ticks and leaves the eyes fully open (measured 2026-11-10, both in
# the build and in her source file).
#
# So pose the lid bones to the closed frame, evaluate the lid meshes, store the
# difference from rest as a shape key, and bind that. Opt-in per character:
#   VRM_BLINK_BAKE="EyelidSup.L=1,0.55,0,0;EyelidInf.L=1,-0.5,0,0;..."  bone=quat
#   VRM_BLINK_MESH="^EyeLid"                                              meshes
# The vertex count of the evaluated mesh must equal the mesh's own, or a key
# written from it would be applied to the wrong vertices; refuse in that case.
_bake_binds = []
_bake_lash = []
_BAKE = os.environ.get("VRM_BLINK_BAKE", "").strip()
if _BAKE:
    _bake_pose = {}
    for _part in [x for x in _BAKE.split(";") if x.strip()]:
        _bn, _, _q = _part.partition("=")
        _bake_pose[_bn.strip()] = tuple(float(v) for v in _q.split(","))
    _missing = [b for b in _bake_pose if b not in arm.pose.bones]
    if _missing:
        raise SystemExit("ABORT: VRM_BLINK_BAKE names bones this rig has not "
                         "got: %s" % _missing)
    _lids = [o for o in meshes
             if re.search(os.environ.get("VRM_BLINK_MESH", "^EyeLid"), o.name)]
    if not _lids:
        raise SystemExit("ABORT: VRM_BLINK_BAKE matched no mesh")

    def _eval_local(_o):
        _dg = bpy.context.evaluated_depsgraph_get()
        _e = _o.evaluated_get(_dg)
        _m = _e.to_mesh()
        _p = [v.co.copy() for v in _m.vertices]
        _e.to_mesh_clear()
        return _p

    # Lid meshes usually carry Solidify and Subsurf AHEAD of the armature
    # modifier, and nothing else in this script applies them -- the exporter
    # does, at write time, which would turn the 81-vertex base the key is
    # written against into a 674-vertex mesh and drop the morph target. Apply
    # them here, while the lids have no shape keys, so the key is written on
    # the geometry that ships. Armature is last in the stack, so these are
    # first and modifier_apply has no ordering complaint.
    for _o in _lids:
        _stack = [m for m in _o.modifiers if m.type != "ARMATURE"]
        if not _stack or _o.data.shape_keys:
            continue
        if _o.data.users > 1:
            _o.data = _o.data.copy()
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = _o
        _o.select_set(True)
        for _m in _stack:
            bpy.ops.object.modifier_apply(modifier=_m.name)
        print("  blink bake: applied %s on %s -> %d vertices"
              % ("+".join(m.type for m in _stack), _o.name, len(_o.data.vertices)))
    bpy.context.view_layer.update()

    _was = {b: tuple(arm.pose.bones[b].rotation_quaternion) for b in _bake_pose}
    for b in _bake_pose:
        arm.pose.bones[b].rotation_mode = "QUATERNION"
        arm.pose.bones[b].rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    _rest = {o.name: _eval_local(o) for o in _lids}
    for b, q in _bake_pose.items():
        arm.pose.bones[b].rotation_quaternion = q
    bpy.context.view_layer.update()
    _closed = {o.name: _eval_local(o) for o in _lids}
    for b, q in _was.items():
        arm.pose.bones[b].rotation_quaternion = q
    bpy.context.view_layer.update()
    for _o in _lids:
        if len(_rest[_o.name]) != len(_o.data.vertices):
            print("  blink bake: SKIPPED %s -- evaluated %d vertices, mesh has "
                  "%d (a non-armature modifier is still live)"
                  % (_o.name, len(_rest[_o.name]), len(_o.data.vertices)))
            continue
        _moved = max(((c - r).length for c, r in
                      zip(_closed[_o.name], _rest[_o.name])), default=0.0)
        if _moved < 1e-5:
            print("  blink bake: %s does not move under this pose -- no key" % _o.name)
            continue
        if not _o.data.shape_keys:
            _o.shape_key_add(name="Basis")
        _kb = _o.shape_key_add(name="Blink", from_mix=False)
        for _i, (c, r) in enumerate(zip(_closed[_o.name], _rest[_o.name])):
            _kb.data[_i].co = _o.data.shape_keys.reference_key.data[_i].co + (c - r)
        _bake_binds.append((_o, "Blink"))
        print("  blink bake: %s/Blink, max displacement %.4f" % (_o.name, _moved))

    # LASHES CLOSE WITH THE LIDS. Pomni's lash ticks collapse onto the seam where
    # the lids meet (measured in her source at frame 30: a z-spread of 0.009 at
    # the eye's centre height), and the reference shows them lying along that
    # line. Her own 'Closed' key does this in the source and does NOT survive
    # the build -- it moves the lashes 0.011 the wrong way -- so write a fresh
    # key from the closed lids: slide each lash vertex to the seam height and
    # forward onto the lid's closed surface.
    #   VRM_BLINK_LASH="^Lashes"
    _LASH = os.environ.get("VRM_BLINK_LASH", "").strip()
    if _LASH and _bake_binds:
        import mathutils
        from mathutils.bvhtree import BVHTree
        _lashes = [o for o in meshes if re.search(_LASH, o.name)]
        _wcl = {o.name: [o.matrix_world @ c for c in _closed[o.name]] for o in _lids}
        def _xc(_n):
            _xs = [v.x for v in _wcl[_n]]
            return (min(_xs) + max(_xs)) / 2
        def _nearest(_kind, _x):
            _c = [o for o in _lids if _kind in o.name and o.name in _wcl]
            return min(_c, key=lambda o: abs(_xc(o.name) - _x)) if _c else None
        for _lo in _lashes:
            if not _lo.data.vertices:
                continue
            _wv = [_lo.matrix_world @ v.co for v in _lo.data.vertices]
            _cx = sum(v.x for v in _wv) / len(_wv)
            _sup, _inf = _nearest("Sup", _cx), _nearest("Inf", _cx)
            if _sup is None or _inf is None:
                print("  blink bake: no lid pair for %s -- lashes left alone" % _lo.name)
                continue
            _seam = (min(v.z for v in _wcl[_sup.name])
                     + max(v.z for v in _wcl[_inf.name])) / 2
            # Surface in front of the seam: ray from the front onto both lids.
            _verts = _wcl[_sup.name] + _wcl[_inf.name]
            _polys = []
            for _l in (_sup, _inf):
                _off = 0 if _l is _sup else len(_wcl[_sup.name])
                _polys += [[_off + i for i in pl.vertices] for pl in _l.data.polygons]
            _bvh = BVHTree.FromPolygons([tuple(v) for v in _verts], _polys)
            _inv = _lo.matrix_world.inverted()
            _targets = []
            # Keep 40% of each tick's height about the seam. Flattening them to
            # zero leaves invisible degenerate lines; her source keeps a z-spread
            # of 0.009 against 0.024 open, which is 0.375.
            _cz = sum(v.z for v in _wv) / len(_wv)
            for w in _wv:
                _zs = _seam + (w.z - _cz) * 0.4
                _o3 = mathutils.Vector((w.x, w.y - 1.0, _zs))
                _hit = _bvh.ray_cast(_o3, mathutils.Vector((0, 1, 0)), 2.0)
                _y = (_hit[0].y - 0.004) if _hit[0] is not None else w.y
                _targets.append(_inv @ mathutils.Vector((w.x, _y, _zs)))
            if not _lo.data.shape_keys:
                _lo.shape_key_add(name="Basis")
            _kb = _lo.shape_key_add(name="Blink", from_mix=False)
            for _i, t in enumerate(_targets):
                _kb.data[_i].co = t
            _bake_binds.append((_lo, "Blink"))
            _bake_lash.append(_lo)
            print("  blink bake: %s/Blink laid on the seam of %s + %s (z %.3f)"
                  % (_lo.name, _sup.name, _inf.name, _seam))

_blink_binds = []
for _spec in [x for x in os.environ.get("VRM_BLINK", "").split(",") if x.strip()]:
    _mn, _, _kn = _spec.partition("=")
    _o = bpy.data.objects.get(_mn.strip())
    if _o is None or not _o.data.shape_keys:
        raise SystemExit("ABORT: VRM_BLINK names mesh %r, which this file has "
                         "not got (or it has no shape keys)" % _mn.strip())
    _blink_binds.append((_o, _kn.strip()))
if not _blink_binds:
    for _o in meshes:
        _sk = _o.data.shape_keys
        if not _sk:
            continue
        for _kb in list(_sk.key_blocks)[1:]:
            if (_is_blink(_o.name, _kb.name)
                    and (_o, _kb.name) not in _bake_binds
                    and _o not in _bake_lash):
                _blink_binds.append((_o, _kb.name))
# Custom facial expressions (VRM_EXPR), reachable by YARG's own lipsync events.
for _en, _tg in _EXPR.items():
    _ce = ext.vrm1.expressions.custom.add()
    _ce.custom_name = _en
    _n = 0
    for _mn, _kn in _tg:
        _mo = bpy.data.objects.get(_mn)
        if _mo is None or not _mo.data.shape_keys or _kn not in _mo.data.shape_keys.key_blocks:
            raise SystemExit("ABORT: VRM_EXPR %s names %s/%s, which is not in "
                             "this file" % (_en, _mn, _kn))
        _b = _ce.morph_target_binds.add()
        _b.node.mesh_object_name = _mn
        _b.index = _kn
        _b.weight = 1.0
        _n += 1
    print("  expression: custom '%s' bound to %d key(s): %s"
          % (_en, _n, ", ".join("%s/%s" % t for t in _tg)))

# Baked lid keys go on the plain 'blink' expression only. Their mesh names carry
# an L that does not reliably mean the eye's side (Pomni's EyeLidSup.L.001 sits
# on the other eye), and YARG drives only 'blink' anyway.
for _o, _kn in _bake_binds:
    _b = ext.vrm1.expressions.preset.blink.morph_target_binds.add()
    _b.node.mesh_object_name = _o.name
    _b.index = _kn
    _b.weight = 1.0
if _bake_binds:
    print("  blink: bound %d baked eyelid key(s) to the blink expression: %s"
          % (len(_bake_binds), ", ".join(o.name for o, _ in _bake_binds)))

if _blink_binds:
    _pre = ext.vrm1.expressions.preset
    _side = {"blink": _pre.blink}
    for _attr, _pat in (("blink_left", r"(^|[._ ])(l|left)([._ ]|$)"),
                        ("blink_right", r"(^|[._ ])(r|right)([._ ]|$)")):
        _e = getattr(_pre, _attr, None)
        if _e is not None:
            _side[_attr] = _e
    _done = []
    for _o, _kn in _blink_binds:
        _targets = ["blink"]
        # The side is on the KEY first and the MESH second. Pomni has one lash
        # mesh per eye; Character Creator puts Eye_Blink_L and Eye_Blink_R on
        # one CC_Base_Body, so reading the mesh name would have called both of
        # Heels' eyes the same side.
        for _attr, _pat in (("blink_left", r"(^|[._ -])(l|left)([._ -]|$)"),
                            ("blink_right", r"(^|[._ -])(r|right)([._ -]|$)")):
            if _attr not in _side:
                continue
            if re.search(_pat, _kn, re.I) or (
                    not re.search(r"(^|[._ -])(l|r|left|right)([._ -]|$)",
                                  _kn, re.I)
                    and re.search(_pat, _o.name, re.I)):
                _targets.append(_attr)
        for _t in _targets:
            _b = _side[_t].morph_target_binds.add()
            _b.node.mesh_object_name = _o.name
            _b.index = _kn
            _b.weight = 1.0
        _done.append("%s/%s -> %s" % (_o.name, _kn, "+".join(_targets)))
    print("  blink: bound %d eye-closing shape key(s) to the blink "
          "expression, which is the one expression YARG drives: %s"
          % (len(_blink_binds), ", ".join(_done[:6])))
else:
    print("  blink: no eye-closing shape key in this model, so the blink "
          "expression stays empty")

# Bind the visemes the pass above spared, so the mouth can actually move.
#
# Without this every character shipped with all five viseme expressions
# DECLARED and none BOUND, which reads as a working lipsync setup right up
# until nothing moves. Measured across 28 built characters: 0 of 28 had a
# single viseme bound.
# Exaggerate the mouth before binding it.
#
# Pomni's visemes worked first time -- her mouth tracked the words -- and were
# "barely noticeable". A speaking mouth modelled for a close-up is far too
# subtle at the distance YARG draws a vocalist, and the bind WEIGHT cannot fix
# it: aa is already at 1.0, which is the ceiling. So scale the shape key's own
# displacement instead, and 1.0 then means a bigger mouth.
#
# Only viseme keys. Amplifying a blink would drive the eyelids through the eye.
_VIS_GAIN = float(os.environ.get("VRM_VISEME_GAIN", "1.0"))
if abs(_VIS_GAIN - 1.0) > 1e-6:
    _scaled = []
    for _o in meshes:
        _sk = _o.data.shape_keys
        if not _sk:
            continue
        _basis = _sk.key_blocks[0]
        for _kb in list(_sk.key_blocks)[1:]:
            if not _viseme_targets(_o.name, _kb.name):
                continue
            if _is_blink(_o.name, _kb.name):
                continue
            for _i, _pt in enumerate(_kb.data):
                _b = _basis.data[_i].co
                _pt.co = _b + (_pt.co - _b) * _VIS_GAIN
            _scaled.append("%s/%s" % (_o.name, _kb.name))
    if _scaled:
        print("  visemes: exaggerated %d mouth shape key(s) by %.2fx (%s)"
              % (len(_scaled), _VIS_GAIN, ", ".join(_scaled[:6])))

_vis_binds = {}
for _o in meshes:
    _sk = _o.data.shape_keys
    if not _sk:
        continue
    for _kb in list(_sk.key_blocks)[1:]:
        for _t, _w in _viseme_targets(_o.name, _kb.name):
            _vis_binds.setdefault(_t, []).append((_o.name, _kb.name, _w))
# IH is the one most models have no shape for -- Alastor has a, e, o and U and
# no i at all. An unbound viseme is a mouth that stops moving mid-word, so
# mirror EE at a lower weight rather than leave a hole.
if "ee" in _vis_binds and "ih" not in _vis_binds:
    _vis_binds["ih"] = [(_m, _k, _w * 0.7) for _m, _k, _w in _vis_binds["ee"]]
    print("  visemes: no 'ih' shape in this model -- mirroring 'ee' at 0.7 so "
          "the mouth does not stall mid-word")

if _vis_binds:
    _pre = ext.vrm1.expressions.preset
    _said = []
    for _t, _pairs in _vis_binds.items():
        _e = getattr(_pre, _t, None)
        if _e is None:
            continue
        for _mesh_name, _key_name, _w in _pairs:
            _b = _e.morph_target_binds.add()
            _b.node.mesh_object_name = _mesh_name
            _b.index = _key_name
            _b.weight = _w
        _said.append("%s<-%s@%.2f" % (_t, _pairs[0][1], _pairs[0][2]))
    print("  visemes: bound %d of 5 mouth expressions (%s)"
          % (len(_said), ", ".join(sorted(_said))))
else:
    print("  visemes: this model has no mouth shape keys, so it cannot "
          "lipsync -- nothing in the pipeline can add them")

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

# A source that has been through this pipeline before carries the spring
# configuration it was given last time, inside the .blend. Asking for no
# springs then quietly produces two anyway, because they were never added by
# this run -- they were inherited. Miku is the case: her intermediate holds
# the HairSpring chains an earlier session built, and rebuilding her with the
# hair rigger switched off still shipped them.
#
# VRM_CLEAR_SPRINGS=1 wipes what the file came with before anything is added.
# Deliberately opt-in: the VRoid characters arrive with their OWN authored
# chains, which are correct and must not be thrown away.
if os.environ.get("VRM_CLEAR_SPRINGS"):
    try:
        _sb0 = ext.spring_bone1
        _had = len(_sb0.springs)
        while len(_sb0.springs):
            _sb0.springs.remove(len(_sb0.springs) - 1)
        while len(_sb0.collider_groups):
            _sb0.collider_groups.remove(len(_sb0.collider_groups) - 1)
        while len(_sb0.colliders):
            _sb0.colliders.remove(len(_sb0.colliders) - 1)
        print("  cleared %d spring chain(s) the source file came with" % _had)
    except Exception as _e:
        print("  could not clear inherited springs: %s" % _e)
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

        # Hair swings and keeps swinging; a skirt does not. Peach's dress is
        # rigged and reported as so reactive that her legs pass through it,
        # which is the same defaults doing the wrong job: cloth hangs, drags
        # against itself and settles, so it wants more restoring force and far
        # more damping than hair. Judged by the chain's own name, which is what
        # selected it in the first place.
        _CLOTH = r"(skirt|dress|cloth|cape|coat|robe|apron|tabard|sash|scarf)"
        _cp = os.environ.get("VRM_CLOTH_PARAMS", "0.85,0.8,0.0").split(",")
        _c_stiff, _c_drag, _c_grav = [float(x) for x in _cp]
        # How much of the mesh does each bone actually carry? An attachment
        # bone is the giveaway, and it needs measuring rather than naming.
        _wt = {}
        for _o in bpy.data.objects:
            if _o.type != "MESH":
                continue
            if not any(m.type == "ARMATURE" and m.object is arm
                       for m in _o.modifiers):
                continue
            _gn = [g.name for g in _o.vertex_groups]
            for _v in _o.data.vertices:
                for _g in _v.groups:
                    if _g.group < len(_gn):
                        _wt[_gn[_g.group]] = _wt.get(_gn[_g.group], 0.0) + _g.weight

        def _trim_anchor(chain):
            """Drop a leading ATTACHMENT bone out of the chain.

            A VRM chain moves every joint by rotating the one before it, so
            joint 0 is not a passenger -- its rotation swings everything below
            it. That is wrong for a bone whose job is to hold the mesh ON.

            Lola Bunny's hair is the case. Her chain was
            hair_att -> hair1 -> hair2, and hair_att is 0.260 long carrying
            51.9% of the hair, against 0.100 and 48.1% for the whole rest of
            the chain. Rotating it swung the bulk of her hair on a lever two
            and a half times the length of the hair itself, pivoting at the
            base of her skull -- and with no colliders in the file, nothing
            caught it. In game her ponytail left her head.

            Both tests have to pass: LONGER than the rest of the chain put
            together (that is the lever) and carrying at least as much of the
            mesh (that is what the lever throws). A bone that is merely long,
            or merely heavy, is still an ordinary first segment.
            """
            if len(chain) < 3:
                return chain
            _b = arm.data.bones.get(chain[0])
            _rest = [arm.data.bones.get(x) for x in chain[1:]]
            if _b is None or any(x is None for x in _rest):
                return chain
            _rl = sum(x.length for x in _rest)
            _rw = sum(_wt.get(x.name, 0.0) for x in _rest)
            _bw = _wt.get(_b.name, 0.0)
            if _b.length > _rl and _bw >= _rw and (_bw + _rw) > 0.0:
                print("    '%s' is an attachment bone, not a segment: %.3f long "
                      "against %.3f for the rest of the chain, and carrying "
                      "%.0f%% of the weight -- anchoring at '%s' instead"
                      % (chain[0], _b.length, _rl,
                         100.0 * _bw / (_bw + _rw), chain[1]))
                return chain[1:]
            return chain

        for chain in [c for root in roots for c in walk(root)]:
            if len(chain) < 2:
                continue
            chain = _trim_anchor(chain)
            if len(chain) < 2:
                continue
            _is_cloth = bool(re.search(_CLOTH, chain[0], re.I))
            spring = sb.springs.add()
            try:
                spring.vrm_name = chain[0]
            except Exception:
                pass
            for n in chain:
                j = spring.joints.add()
                j.node.bone_name = n
                for prop, val in (("hit_radius", 0.02),
                                  ("stiffness", _c_stiff if _is_cloth else 0.6),
                                  ("drag_force", _c_drag if _is_cloth else 0.45),
                                  ("gravity_power",
                                   _c_grav if _is_cloth else 0.0)):
                    try:
                        setattr(j, prop, val)
                    except Exception:
                        pass
            made += 1
            print("  spring chain '%s': %d joints (%s)"
                  % (chain[0], len(chain), "cloth" if _is_cloth else "hair"))
        print("spring bone chains added: %d%s" % (
            made, "" if made else "  (no hair/skirt/tail bones in this rig - its "
            "hair and clothes are skinned to the body, so there is nothing to spring)"))
    except Exception as e:
        print("spring bone setup failed: %s: %s" % (type(e).__name__, e))

# Chest bones are their own case, and the hair pattern above cannot carry them.
#
# A rig that has them calls them breast / bust / pectoral, and NONE of those is
# a humanoid slot, so VRM leaves them rigid: 16 of the 66 characters installed
# here ship chest bones that nothing ever moves. Three more (the VRoid ones)
# arrive with their own chains already built, which is the proof that this is
# the normal thing to do rather than something the pipeline is inventing.
#
# Two reasons this is not just a longer DEFAULT_SPRING:
#
# - **A lone bone cannot spring.** A VRM chain moves every joint except the
#   last, so a one-bone chain moves nothing, and the loop above drops it on
#   `len(chain) < 2`. Alcina, Jessica Rabbit and Killer Clown all have exactly
#   one bone a side. They need a TIP -- a child at the bone's tail carrying no
#   weights, which is what the hair rigger builds for the same reason.
# - **A bone in the rig is not a bone in the MODEL.** Batman carries
#   `fml_un_C_breast` because MultiVersus skins its cast onto one shared female
#   base; it deforms nothing on him. Springing it would be invisible, which is
#   worse than wrong -- it would sit in the file looking like it worked. So the
#   test is whether the bone actually drives vertices, not whether it is named.
#
# VRM_BREAST_SPRING=0 turns it off; VRM_BREAST_PARAMS="stiffness,drag,gravity"
# overrides the feel. The defaults are stiffer and draggier than the hair ones
# -- hair swings and keeps swinging, this should move a little and settle.
if os.environ.get("VRM_BREAST_SPRING", "1") != "0":
    try:
        sb = ext.spring_bone1
        _hum = {v for v in MAP.values()}
        _deform = set()
        for _m in meshes:
            _gn = dict((_g.index, _g.name) for _g in _m.vertex_groups)
            for _v in _m.data.vertices:
                for _g in _v.groups:
                    if _g.weight > 0.01:
                        _deform.add(_gn.get(_g.group))
        _cands = [b for b in arm.data.bones
                  if re.search(BREAST, b.name, re.I) and b.name not in _hum
                  and not b.name.lower().endswith(("_end", "_att"))]
        _skipped = [b.name for b in _cands if b.name not in _deform]
        _cands = [b for b in _cands if b.name in _deform]
        if _skipped:
            print("  breast spring: %d bone(s) named but weighted to nothing, "
                  "so not sprung: %s" % (len(_skipped), ", ".join(_skipped)))
        # 0.85 / 0.60 was chosen by watching a 1.70 m character bend 12 degrees
        # in a still render, and in motion it is far too loose: Alcina at 2.9 m
        # and Killer Clown at 1.80 m were both reported as drifting like
        # balloons, so it is not only a scale problem. A VRM spring's stiffness
        # is a restoring force and its drag is damping, so a chest -- which in
        # life barely moves and settles at once -- wants both near the top of
        # their range. Hair swings and keeps swinging, which is the opposite,
        # and keeps its own 0.60 / 0.45.
        _par = os.environ.get("VRM_BREAST_PARAMS", "1.0,0.9,0.0").split(",")
        _stiff, _drag, _grav = [float(x) for x in _par]
        # Work out every chain BEFORE touching edit mode. Entering edit mode
        # invalidates every Bone reference held across it, and the references
        # do not fail -- they silently address a DIFFERENT bone. Held across a
        # tip insertion, '_b.name' started reporting 'f_pinky.02.L' and the
        # second pass sprang a FINGER on a model whose chest bones are called
        # breast.L and breast.R. Names survive; pointers do not.
        _names = set(b.name for b in _cands)
        _chains, _need_tip = [], []
        for _b in _cands:
            if _b.parent is not None and _b.parent.name in _names:
                continue                  # a lower joint of a chain, not a root
            _chain, _cur = [_b.name], _b
            while True:
                _kids = [c for c in _cur.children
                         if re.search(BREAST, c.name, re.I)]
                if len(_kids) != 1:
                    break
                _cur = _kids[0]
                _chain.append(_cur.name)
            if len(_chain) < 2:
                # Give the lone bone a tip to swing towards. It carries no
                # weights, so it changes no geometry -- it only gives the last
                # joint somewhere to be.
                _need_tip.append(_chain[0])
                _chain.append(_chain[0] + "_springTip")
            _chains.append(_chain)
        if _need_tip:
            bpy.context.view_layer.objects.active = arm
            bpy.ops.object.mode_set(mode="EDIT")
            for _n in _need_tip:
                _eb = arm.data.edit_bones[_n]
                _new = arm.data.edit_bones.new(_n + "_springTip")
                _vec = _eb.tail - _eb.head
                _new.head = _eb.tail
                # Half the bone's length, not all of it. A spring rotates about
                # the chain's head, so the tip is the lever arm: doubling the
                # bone doubled the travel at the surface.
                _new.tail = _eb.tail + _vec * 0.5
                _new.parent = _eb
                _new.use_deform = False
            bpy.ops.object.mode_set(mode="OBJECT")
            print("  breast spring: %d lone bone(s) given a weightless tip: %s"
                  % (len(_need_tip), ", ".join(_need_tip)))
        _made = 0
        for _chain in _chains:
            _spring = sb.springs.add()
            try:
                _spring.vrm_name = _chain[0]
            except Exception:
                pass
            for _n in _chain:
                _j = _spring.joints.add()
                _j.node.bone_name = _n
                for _prop, _val in (("hit_radius", 0.04), ("stiffness", _stiff),
                                    ("drag_force", _drag),
                                    ("gravity_power", _grav)):
                    try:
                        setattr(_j, _prop, _val)
                    except Exception:
                        pass
            _made += 1
            print("  breast spring chain '%s': %d joints (%s) stiffness %.2f, "
                  "drag %.2f" % (_chain[0], len(_chain), " -> ".join(_chain),
                                 _stiff, _drag))
        print("breast spring chains added: %d%s" % (
            _made, "" if _made else "  (no weighted chest bones in this rig)"))
    except Exception as _e:
        print("breast spring setup failed: %s: %s" % (type(_e).__name__, _e))

# ------------------------------------------------------------- colliders
# Measured per character and shared with add_colliders.py, which retro-fits a
# built .vrm -- most of the 66 have no source file on this machine any more.
# One copy of the logic, in vrm_colliders.py, so the two cannot drift.
#
# VRM_COLLIDERS=0 turns the step off.
if os.environ.get("VRM_COLLIDERS", "1") != "0":
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import vrm_colliders
        vrm_colliders.fit(arm, ext, MAP, bone_names)
    except Exception as _e:
        print("collider setup failed: %s: %s" % (type(_e).__name__, _e))

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
