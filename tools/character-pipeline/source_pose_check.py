# -*- coding: utf-8 -*-
"""Is a character's source POSED, and is that pose separable from its rest pose?

    blender --background "<source.blend>" --python source_pose_check.py
    blender --background --python source_pose_check.py -- <source.glb|.usdz|.fbx>

WHY THIS EXISTS. Several characters here were built from sources their authors had POSED --
Jessica Rabbit leaning on a microphone, Kronk doing the Hokey Pokey. A pose reaches the shipped
character in one of two completely different ways, and which one decides whether there is an
easy fix or a hard one:

  * BAKED INTO THE REST POSE. A `.glb`/`.usdz` export of a posed scene has the pose as its rest
    shape. There is no pose to clear; correcting it is a deformation on weights taken from a
    contorted pose, which is what `VRM_STRAIGHTEN_LEGS` warns tears.
  * A POSE ON TOP OF A CLEAN REST POSE. A native `.blend` keeps `matrix_basis` separate from
    `matrix_local`. The pose is then CLEARABLE and the character is rebuildable straight, with no
    deformation and no trade.

THE TWO LOOK IDENTICAL in a viewport and in a render. They are told apart only by reading rest
and pose as separate quantities, which is what this does.

MEASURED CASE -- Jessica Rabbit, 2026-11-20. Her shipped character has its Hips sideways axis
25.71 degrees out of horizontal, burying her left foot 92 mm below the floor, and the project had
twice concluded "leave her: every correction trades the buried shoe for a twisted pelvis". Run on
the author's `source/JR - Copy.blend` this reported a rest pose level and symmetric to 1e-8
(thigh dz 0.00 mm, feet dz 0.00 mm) with the whole 25.71 degrees sitting in `spine`'s
`matrix_basis`. The conclusion was about the GLB; nobody had read the .blend.

IT ALSO REPORTS THE HAZARD, because clearing a pose is only safe if everything follows the rig.
A mesh with no armature deformation never moved, so it was modelled where the author wanted it to
sit in the POSED scene: clear the pose and it stays behind. On Jessica the six unbound meshes
turned out to be a sculpt duplicate plus a microphone and its stand -- props to exclude, not
geometry to rescue -- but that was a measurement, not a safe assumption, and on another character
it will be an earring or a prop in a hand.

CONVENTIONS. Blender is Z-UP; the VRM/Unity side is Y-UP. "Tilted out of horizontal" is therefore
asin(|z|) here and asin(|y|) there, and a number copied between them without that swap is wrong
by exactly the amount that makes it look plausible.

READ-ONLY. Nothing is written and no pose is cleared; that is a build step, not a probe.
"""
import math
import re
import sys

import bpy
from mathutils import Vector

# Bones worth reading on any humanoid rig, by any of the naming families seen here.
INTEREST = ("hip", "pelvis", "spine", "thigh", "upperleg", "upper_leg", "shin", "calf",
            "lowerleg", "lower_leg", "foot", "toe", "shoulder", "upperarm", "upper_arm",
            "forearm", "root")
PAIR_TAGS = ("thigh", "upperleg", "upper_leg", "shin", "foot", "toe", "shoulder",
             "upperarm", "upper_arm")


def _import_if_asked():
    """With a path after `--`, import it; otherwise work on the already-open .blend."""
    argv = sys.argv
    if "--" not in argv:
        return None
    rest = argv[argv.index("--") + 1:]
    if not rest:
        return None
    path = rest[0]
    low = path.lower()
    if low.endswith((".usd", ".usdc", ".usda", ".usdz")):
        bpy.ops.wm.usd_import(filepath=path)
    elif low.endswith((".glb", ".gltf", ".vrm")):
        # A .vrm IS a glTF container, and this pipeline's every OUTPUT is one -- so without
        # it here the tool can read what goes into a build and not what comes out, which is
        # the comparison that localises a fault to the builder.
        bpy.ops.import_scene.gltf(filepath=path)
    elif low.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif low.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    else:
        print("UNKNOWN EXTENSION %r -- nothing imported, and that is not an empty scene" % path)
        sys.exit(2)
    return path


def _side(name):
    """L or R, tolerating glTF's NUMERIC SUFFIX -- and that suffix is not a detail.

    `import_scene.gltf` renames every bone with a trailing `_<index>`: the .blend's `shin.L`
    arrives as `shin.L_165`. A matcher testing the END of the string then finds no side on any
    bone of any glTF-imported rig, so the pair table reports "no pair identified" on a rig that
    is entirely regular -- which is a fact about the matcher wearing the shape of a fact about
    the character. Measured on jessica_rabbit.glb 2026-11-20: 160 bones, 0 pairs found, and the
    only reason it was caught is that this tool says WHY it found none instead of printing zeros.
    """
    low = re.sub(r"_\d+$", "", name.lower())
    if low.endswith((".l", "_l", "-l")) or ".l." in low or "left" in low:
        return "L"
    if low.endswith((".r", "_r", "-r")) or ".r." in low or "right" in low:
        return "R"
    return None


def _ang(a, b):
    if a.length < 1e-9 or b.length < 1e-9:
        return float("nan")
    return math.degrees(math.acos(max(-1.0, min(1.0, a.normalized().dot(b.normalized())))))


def report(arm):
    bone_names = set(b.name for b in arm.data.bones)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]

    # ---------------------------------------------------------------- pose vs rest
    posed = []
    for pb in arm.pose.bones:
        b = pb.matrix_basis
        if (b.to_translation().length > 1e-6 or abs(b.to_quaternion().angle) > 1e-5
                or any(abs(s - 1.0) > 1e-6 for s in b.to_scale())):
            posed.append((pb.name, math.degrees(b.to_quaternion().angle),
                          b.to_translation().length))
    print()
    print("ARMATURE %r -- %d bones" % (arm.name, len(arm.data.bones)))

    # THE GATE, reported first, because it decides which of build_vrm.py's pose rules can run
    # at all. Everything there sits under `if _had_anim ...`; with no action attached the
    # builder takes the else and keeps the static pose as "the model's shape". A tool that
    # reports the pose without reporting whether an action exists cannot tell you which branch
    # a build will take, which is the only thing the pose is evidence FOR.
    _acts = [a.name for a in bpy.data.actions]
    _adt = arm.animation_data
    _assigned = _adt.action.name if (_adt and _adt.action) else None
    print("ACTIONS in file: %d %s   assigned to this armature: %s"
          % (len(_acts), _acts[:4] if _acts else "", _assigned or "NONE"))
    print("  => build_vrm.py would %s"
          % ("RESET the pose (an action is attached, so it may be a stray frame)"
             if _assigned else
             "KEEP the static pose (no action attached, so it reads as the model's shape)"))

    print("POSE ON TOP OF REST: %d bone(s)" % len(posed))
    if not posed:
        print("  NONE. The file is at its rest pose, so any lean you can see IS the rest pose")
        print("  and there is nothing to clear. A correction here is a deformation.")
    else:
        print("  The lean is SEPARABLE: clearing the pose returns the rest pose below.")
        for name, ang, tr in sorted(posed, key=lambda t: -t[1])[:12]:
            print("    %-26s rot %7.2f deg  translate %7.4f" % (name[:26], ang, tr))
        if len(posed) > 12:
            print("    ... and %d more" % (len(posed) - 12))

    # ---------------------------------------------------------------- the paired reading
    pairs = {}
    for b in arm.data.bones:
        low = b.name.lower()
        for tag in PAIR_TAGS:
            if tag in low and _side(b.name):
                pairs.setdefault(tag, {})[_side(b.name)] = b
    print()
    # SPAN-NORMALISED, because the raw figure is not comparable between two sources.
    # These files are not in metres and each carries its own scale: Jessica's rig sits at a
    # matrix_world scale of about 5.58 with her spine at Z ~ 6.9. So a dz of "597 mm" in one
    # file and "40 mm" in another says nothing about which character is worse off until both
    # are divided by the rig they belong to. The percentage is the comparable quantity and the
    # raw column is kept beside it only so a single file can be checked by hand.
    _hs = [(arm.matrix_world @ b.head_local).z for b in arm.data.bones]
    span = (max(_hs) - min(_hs)) if _hs else 0.0
    print("L/R PAIRS -- rest first, because that is what a rebuild inherits")
    print("rig span %.4f in this file's own units; %% columns are of that span" % span)
    print("%-12s %12s %7s %12s %7s   %s"
          % ("pair", "rest dz", "rest %", "posed dz", "posed %", "local mirror delta"))
    any_pair = False
    for tag, sides in sorted(pairs.items()):
        if "L" not in sides or "R" not in sides:
            continue
        any_pair = True
        L, R = sides["L"], sides["R"]
        lw = (arm.matrix_world @ L.matrix_local).to_translation()
        rw = (arm.matrix_world @ R.matrix_local).to_translation()
        pl, pr = arm.pose.bones.get(L.name), arm.pose.bones.get(R.name)
        rdz = lw.z - rw.z
        pdz = (((arm.matrix_world @ pl.matrix).to_translation().z
                - (arm.matrix_world @ pr.matrix).to_translation().z)
               if (pl and pr) else float("nan"))
        md = abs(abs(L.matrix_local.to_translation().x) - abs(R.matrix_local.to_translation().x))
        pct = (lambda v: (100.0 * v / span) if span else float("nan"))
        print("%-12s %12.4f %6.2f%% %12.4f %6.2f%%   %.2e"
              % (tag, rdz, pct(rdz), pdz, pct(pdz), md))
    if not any_pair:
        print("  NO L/R PAIR identified BY NAME. That is a fact about the naming, not a")
        print("  symmetric rig -- read the bone list before concluding anything.")

    # ---------------------------------------------------------------- limb angles
    print()
    print("LIMB ANGLES off -Z (Blender down), rest against posed")
    down = Vector((0.0, 0.0, -1.0))
    for side in ("L", "R"):
        for lo, hi, label in (("thigh", "shin", "thigh"), ("shin", "foot", "shin"),
                              ("upper_arm", "forearm", "upper_arm")):
            a = next((b for b in arm.data.bones
                      if lo in b.name.lower() and _side(b.name) == side), None)
            b2 = next((b for b in arm.data.bones
                       if hi in b.name.lower() and _side(b.name) == side), None)
            if not a or not b2:
                continue
            pa, pb = arm.pose.bones.get(a.name), arm.pose.bones.get(b2.name)
            rest = b2.head_local - a.head_local
            pose = (pb.head - pa.head) if (pa and pb) else rest
            print("  %-10s %-2s  rest %6.1f   posed %6.1f" % (label, side, _ang(rest, down),
                                                              _ang(pose, down)))

    # ---------------------------------------------------------------- the hazard
    print()
    print("WHAT WOULD BE LEFT BEHIND -- a mesh that does not follow the rig never moved,")
    print("so it fits the POSED scene and clearing the pose strands it")
    print("%-26s %7s %9s %6s %6s  %s"
          % ("mesh", "verts", "weighted", "mod?", "keys", "world centre"))
    unbound = []
    for m in sorted(meshes, key=lambda o: o.name.lower()):
        mods = [md for md in m.modifiers if md.type == "ARMATURE" and md.object == arm]
        idx = set(g.index for g in m.vertex_groups if g.name in bone_names)
        n = len(m.data.vertices)
        wt = sum(1 for v in m.data.vertices
                 if any(ge.group in idx and ge.weight > 0.0 for ge in v.groups))
        nk = (len(m.data.shape_keys.key_blocks) - 1) if m.data.shape_keys else 0
        c = sum((m.matrix_world @ v.co for v in m.data.vertices), Vector()) / max(n, 1)
        print("%-26s %7d %9d %6s %6d  (%+.3f %+.3f %+.3f)"
              % (m.name[:26], n, wt, "yes" if mods else "NO", nk, c.x, c.y, c.z))
        if not mods or wt == 0:
            unbound.append((m.name, n, wt, bool(mods), c))
    print()
    if unbound:
        print("%d MESH(ES) DO NOT FOLLOW THE RIG. Each needs a decision, not a sweep: a prop"
              % len(unbound))
        print("to exclude, or geometry of the character's that must be moved with M^-1*v.")
        for name, n, wt, mod, c in unbound:
            print("  %-26s %6d verts, %d weighted, modifier %s, centre (%+.3f %+.3f %+.3f)"
                  % (name[:26], n, wt, "yes" if mod else "NO", c.x, c.y, c.z))
    else:
        print("EVERY mesh is bound AND weighted, so every mesh returns with the pose. That is")
        print("the good case, and it is the one that makes clearing the pose cheap.")


def main():
    _import_if_asked()
    print("=" * 78)
    print("SOURCE POSE CHECK -- rest pose against pose, and what would be stranded")
    print("=" * 78)
    print("file: %s" % (bpy.data.filepath or "<imported>"))
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        print("NO ARMATURE FOUND. Nothing was measured; this is a statement about the file or")
        print("about the import, NOT a character with no pose.")
        return 1
    print("armatures: %d, meshes: %d"
          % (len(arms), len([o for o in bpy.data.objects if o.type == "MESH"])))
    for arm in arms:
        report(arm)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("PROBE FAILED: %s: %s" % (type(exc).__name__, exc))
        import traceback
        traceback.print_exc()
        sys.exit(1)
