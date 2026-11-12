# -*- coding: utf-8 -*-
"""Measured spring-bone colliders for a VRM armature.

A spring chain with nothing to hit passes through the body. Every one of the
66 characters installed here shipped with ZERO colliders, which is why Gadget's
hair goes through her face, Power Girl's through hers, and why Lola Bunny's
ponytail had nothing to stop it once its lever was wrong.

Shared by `build_vrm.py`, which calls this while building, and
`add_colliders.py`, which retro-fits a `.vrm` that was built before this
existed -- most of the 66 have no source file on this machine any more, so a
round trip through the built VRM is the only way to reach them. One copy of
the logic, so the two paths cannot drift.

Sizes are MEASURED per character, never fixed. These models run from Yoda to
Skibidi Toilet to a 2.9 m Alcina Dimitrescu, and one hardcoded radius would be
a helmet on one and a pebble on another.

The radius is deliberately a MEDIAN distance, not a maximum. Hair rests on the
scalp, so the sphere wants to sit at the skull rather than enclose the nose,
ears and chin -- a collider drawn around the widest point holds the hair off
the head and looks worse than no collider at all.
"""
import os
import re

import bpy
from mathutils import Vector

# Chest springs sit ON the torso, so handing them the torso capsule would push
# them out of the body they belong to.
CHEST = r"(breast|bust|pectoral|boob)"

# The limbs, parent -> child, one capsule per bone. See the LIMBS block in
# fit() for why these exist at all.
LIMBS = [
    ("left_upper_arm", "left_lower_arm"), ("left_lower_arm", "left_hand"),
    ("right_upper_arm", "right_lower_arm"), ("right_lower_arm", "right_hand"),
    ("left_upper_leg", "left_lower_leg"), ("left_lower_leg", "left_foot"),
    ("right_upper_leg", "right_lower_leg"), ("right_lower_leg", "right_foot"),
]

# Err SMALL. A collider a little too small lets hair sink slightly into the
# body; one a little too big holds it visibly off the head, which reads as
# broken rather than as imperfect. The median distance is the deliberate
# choice, and VRM_COLLIDER_SCALE exists so the next in-game look can move it
# without an edit here.
SCALE = float(os.environ.get("VRM_COLLIDER_SCALE", "1.0"))


def _pct(vals, q):
    if not vals:
        return 0.0
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def fit(arm, ext, MAP, bone_names, log=print):
    """Add a measured collider group and attach it to the spring chains.

    Returns the number of colliders made. Safe to call twice: an existing
    group made by this function is replaced rather than added to.
    """
    sb = ext.spring_bone1

    # Clear out anything a PREVIOUS run of this function left behind.
    #
    # The docstring above used to say this already happened -- "safe to call
    # twice: an existing group made by this function is replaced rather than
    # added to" -- and it did not. There was no removal code at all, so a
    # second call would have doubled every collider. Nothing had ever called it
    # twice, so the claim was never tested, and it read as a guarantee.
    # Re-fitting the 18 characters with unguarded chains is the first thing
    # that needs it.
    ours = [i for i, grp in enumerate(sb.collider_groups)
            if getattr(grp, "uuid", "") == "colgrp_body"
            or (getattr(grp, "vrm_name", "") or "") == "Body"]
    if ours:
        dead = set()
        uuids = set()
        for i in ours:
            uuids.add(getattr(sb.collider_groups[i], "uuid", ""))
            for r in sb.collider_groups[i].colliders:
                dead.add(r.collider_uuid)
        for sp in sb.springs:
            for i in reversed(range(len(sp.collider_groups))):
                ref = getattr(sp.collider_groups[i], "collider_group_uuid", "")
                if ref in uuids:
                    sp.collider_groups.remove(i)
        for i in reversed(ours):
            sb.collider_groups.remove(i)
        for i in reversed(range(len(sb.colliders))):
            if getattr(sb.colliders[i], "uuid", "") in dead:
                sb.colliders.remove(i)
        log("colliders: cleared %d from a previous fit" % len(dead))

    sprung = set()
    for sp in sb.springs:
        for j in sp.joints:
            if j.node.bone_name:
                sprung.add(j.node.bone_name)
    if not sprung:
        log("colliders: this character has no spring chains, so nothing would "
            "collide -- skipped")
        return 0

    def subtree(name):
        b = arm.data.bones.get(name)
        if b is None:
            return set()
        return set([name]) | set(c.name for c in b.children_recursive)

    def verts_on(names):
        """World-space vertices whose DOMINANT group is one of these bones.

        Dominant rather than any, so a vertex blended between the jaw and the
        neck is counted once, where it mostly is.
        """
        out = []
        for o in bpy.data.objects:
            if o.type != "MESH":
                continue
            if not any(m.type == "ARMATURE" and m.object is arm
                       for m in o.modifiers):
                continue
            gn = [g.name for g in o.vertex_groups]
            mw = o.matrix_world
            for v in o.data.vertices:
                if not v.groups:
                    continue
                best = max(v.groups, key=lambda g: g.weight)
                if best.group < len(gn) and gn[best.group] in names:
                    out.append(mw @ v.co)
        return out

    # Every joint this group will be attached to, in armature space. A
    # collider must never CONTAIN one of these.
    #
    # This is the invariant, and getting it wrong was worse than having no
    # colliders at all. A VRM collider ejects whatever is inside it, so a
    # joint that starts inside is shoved out to the surface on frame one and
    # stays there. On Gadget Hackwrench three hair joints sat inside a 0.193
    # sphere, one of them 44% in, and the ejection pushed her hair out by
    # ~10 cm on a head 0.45 wide: it ballooned into a mass bigger than she was.
    # Measured across the batch, 8 of 23 characters had at least one joint
    # inside, which is exactly the set that came back looking wrong.
    #
    # So the radius is the largest that clears every joint, or the measured
    # median, whichever is SMALLER. On a rig whose hair roots sit deep in the
    # skull that leaves a small collider -- Lola's nearest joint is 0.069 from
    # the head centre against a 0.146 median -- and a small collider still
    # stops hair driving through the face, where an ejecting one is a visible
    # catastrophe. Err small, again, and for the same reason.
    guard = []
    for sp in sb.springs:
        if re.search(CHEST, getattr(sp, "vrm_name", "") or "", re.I):
            continue
        # Skip the chain's FIRST joint. It is the anchor: its position comes
        # from the skeleton, not from the simulation, so no collider can eject
        # it -- and guarding against it is actively harmful, because an anchor
        # is normally attached to the very body part the collider represents.
        #
        # The Xenomorph is the case. His tail is rooted on his spine, so
        # `XenosBiped_TailRoot_SHJnt` sits at EXACTLY 0.0000 m from the torso
        # capsule's axis, the guard shrank the capsule to 0.000, and `add`
        # dropped it. He ended up with eight limb colliders and nothing at all
        # on his torso -- which is where his lower back tubes hang. A joint on
        # the axis has no outward direction to be ejected along either, so the
        # old behaviour was not even protecting anything.
        #
        # The joints that matter are still guarded: his next tail joint is at
        # 0.073 and his back-tube roots at 0.123, so the capsule comes out at
        # 0.070 rather than vanishing.
        for j in list(sp.joints)[1:]:
            b = arm.data.bones.get(j.node.bone_name)
            if b is not None:
                guard.append(b.head_local)

    def _seg_dist(p, a, b):
        ab = b - a
        L2 = ab.dot(ab)
        if L2 < 1e-12:
            return (p - a).length
        t = max(0.0, min(1.0, (p - a).dot(ab) / L2))
        return (p - (a + ab * t)).length

    cols = []

    def add(bone, kind, centre, radius, tail=None):
        b = arm.data.bones.get(bone)
        radius = radius * SCALE
        if guard:
            if kind == "Sphere":
                near = min((g - centre).length for g in guard)
            else:
                near = min(_seg_dist(g, centre, tail) for g in guard)
            if near * 0.95 < radius:
                print("  collider: %s on %s shrunk %.3f -> %.3f so it clears "
                      "the nearest spring joint at %.3f"
                      % (kind, bone[:22], radius, near * 0.95, near))
                radius = near * 0.95
        if b is None or radius <= 1e-5:
            return
        c = sb.colliders.add()
        c.name = "col_%s_%d" % (bone, len(cols))
        c.node.bone_name = bone
        try:
            c.shape_type = kind
        except Exception:
            pass
        inv = b.matrix_local.inverted()
        if kind == "Sphere":
            c.shape.sphere.offset = inv @ centre
            c.shape.sphere.radius = radius
        else:
            c.shape.capsule.offset = inv @ centre
            c.shape.capsule.tail = inv @ tail
            c.shape.capsule.radius = radius
        if not c.uuid:
            c.uuid = c.name
        cols.append(c)
        log("  collider: %-7s on %-22s r=%.3f at world %s"
            % (kind, bone[:22], radius, tuple(round(v, 3) for v in centre)))

    # HEAD -- the skull and face, minus anything a spring already drives. The
    # hair must not be part of the thing it collides with, or it will push
    # itself away from the head.
    hb = MAP.get("head")
    if hb in bone_names:
        hv = verts_on(subtree(hb) - sprung)
        if len(hv) >= 32:
            ctr = Vector((sum(v.x for v in hv) / len(hv),
                          sum(v.y for v in hv) / len(hv),
                          sum(v.z for v in hv) / len(hv)))
            add(hb, "Sphere", ctr, _pct([(v - ctr).length for v in hv], 0.5))

    # TORSO -- a capsule down the spine stops long hair sinking into the back,
    # which a head sphere alone cannot do.
    #
    # The bones give the AXIS; the geometry gives the ends. Gadget Hackwrench
    # is why: her shipped humanoid map has `hips -> root`, a bone sitting on
    # the floor at z=0.005, so a capsule drawn between the mapped bone heads
    # ran from her feet to her neck. The bones can be mapped oddly and the
    # capsule still has to land on the torso, so the ends are read off the
    # vertices that are actually there.
    chain = [MAP.get(k) for k in
             ("hips", "spine", "chest", "upper_chest", "neck")]
    chain = [b for b in chain if b in bone_names]
    if len(chain) >= 2:
        tv = verts_on(set(chain) - sprung)
        if len(tv) >= 32:
            base = arm.data.bones[chain[0]].head_local
            ax = arm.data.bones[chain[-1]].head_local - base
            if ax.length > 1e-5:
                axn = ax.normalized()
                ts = [(v - base).dot(axn) for v in tv]
                t_lo, t_hi = _pct(ts, 0.05), _pct(ts, 0.95)
                if t_hi - t_lo > 1e-4:
                    d = []
                    for v in tv:
                        rel = v - base
                        t = rel.dot(axn)
                        if t_lo <= t <= t_hi:
                            d.append((rel - axn * t).length)
                    add(chain[0], "Capsule", base + axn * t_lo, _pct(d, 0.5),
                        base + axn * t_hi)

    # LIMBS -- the arms and legs, one capsule per bone.
    #
    # A spring joint is deflected by a collider and by nothing else: the body's
    # own geometry is invisible to the simulation. With a head sphere and a
    # torso capsule and nothing else, a skirt hanging around the thighs has
    # nothing to push it aside, so the legs walk straight through it. That is
    # Peach's "dress so reactive her legs clip through", and it is not a spring
    # parameter at all -- her skirt chains are stiffer and more damped than her
    # hair's (0.85/0.80 against 0.60/0.45).
    #
    # Measured across the 65 installed characters with `cloth_collide_installed
    # .py`: 107 of 422 spring chains sit nearest a part that carries no
    # collider. The downloaded VRoid bundles in the same folder are the
    # reference, and they are not ours -- Harq Alkahana, Inforder Trogen and
    # both Hatsune Mikus each carry 28 colliders across arms, legs and torso,
    # and all three come back with ZERO unguarded chains. Two colliders was
    # never enough; it only looked enough because nothing counted.
    #
    # The axis is the BONE, not the geometry. Capsules drawn between bone heads
    # meet at the elbow and the knee with no gap, which two independently
    # geometry-clipped capsules would not -- and a gap at the knee is exactly
    # where a hem would slip through.
    #
    # The clearance guard in add() does the rest: a limb whose own cloth rests
    # inside the flesh radius (Jinx's braids, 0.061 against a 0.083 thigh) gets
    # a capsule shrunk to clear it rather than one that ejects it.
    if os.environ.get("VRM_LIMB_COLLIDERS", "1") != "0":
        for pk, ck in LIMBS:
            pb, cb = MAP.get(pk), MAP.get(ck)
            if pb not in bone_names or cb not in bone_names:
                continue
            own = subtree(pb) - subtree(cb) - sprung
            lv = verts_on(own)
            if len(lv) < 16:
                continue
            a = arm.data.bones[pb].head_local
            b = arm.data.bones[cb].head_local
            if (b - a).length < 1e-4:
                continue
            add(pb, "Capsule", a,
                _pct([_seg_dist(v, a, b) for v in lv], 0.5), b)

    if not cols:
        log("colliders: none could be measured on this rig")
        return 0

    grp = sb.collider_groups.add()
    try:
        grp.vrm_name = "Body"
    except Exception:
        pass
    if not grp.uuid:
        grp.uuid = "colgrp_body"
    for c in cols:
        grp.colliders.add().collider_uuid = c.uuid

    n = 0
    for sp in sb.springs:
        nm = getattr(sp, "vrm_name", "") or ""
        if re.search(CHEST, nm, re.I):
            continue
        if any(getattr(r, "collider_group_uuid", "") == grp.uuid
               for r in sp.collider_groups):
            continue
        sp.collider_groups.add().collider_group_uuid = grp.uuid
        n += 1
    log("colliders: %d in one group, attached to %d of %d spring chain(s)"
        % (len(cols), n, len(sb.springs)))
    return len(cols)
