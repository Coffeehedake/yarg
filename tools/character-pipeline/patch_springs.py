# -*- coding: utf-8 -*-
"""Fix the spring simulation in an INSTALLED .yargchar, in place.

    python patch_springs.py <in.yargchar> [--cloth] [--limbs] [--unrig-hair]
        [--collide] [--group N] [--reclear] [--out X] [--dry-run]

Five independent defects, any or all:

  --cloth   re-parameterise every cloth-named spring chain to the authored
            reference, 0.50 stiffness / 0.05 drag / 0.00 gravity. Characters
            built before 2026-11-15 carry 0.85 / 0.80, which came from a
            diagnosis that was later withdrawn; drag 0.80 is above every value
            in any author-made bundle in the installed folder, for cloth or
            hair, and sixteen times what four VRoid authors give a skirt. A
            chain damped that hard barely moves, which is Peach's dress
            "moving as one piece". build_vrm.py's VRM_CLOTH_PARAMS carries the
            same numbers now; this is for the bundles that will not be rebuilt.

  --limbs   re-radius the arm and leg capsules to the 90th percentile of the
            flesh each bone carries. They were fitted at the MEDIAN, a rule
            written for a hair collider on a scalp, which leaves half of every
            limb outside its own collider -- and a VRM spring joint is
            deflected by a collider and by nothing else, so the capsule IS the
            leg as far as a skirt is concerned. Peach's calf reaches 0.080 from
            the bone axis against an 0.039 capsule.

  --unrig-hair
            REMOVE a generated hair chain that should never have been built:
            one that drives a facial feature, or one whose hair is sealed
            inside a rigid head mesh. Both are faults of the hair rigger's
            selection rather than of its parameters, so no parameter fixes
            them.

            Killer Clown, reported 2026-11-15 as hair clipping through her hat,
            is both at once. Her lashes, brows and hair share one material and
            the rigger's material fallback took all three, so 2,503 of the 2,890
            vertices her four chains move are her EYEBROWS (146 of 146) and
            EYELASHES (2,357 of 4,640), swinging on hair physics across her
            face. And of the 387 that are hair, 371 sit inside her jester hat,
            up to 51.8 mm deep, while 95% of the hair the rigger left rigid is
            outside it -- the physics went on the hair nobody can see.

            Removing a chain leaves its BONES in place, so every vertex stays
            exactly where the model skins it; what stops is the motion. That is
            why this is a removal and not a re-parameterisation: a stiffer
            spring still moves, and these have 2.9 degrees of room.

  --collide give the file's collider group to a spring chain that has NO
            group at all. A chain with no group is restrained by nothing and
            swings straight through the body, which is half of Peach's dress.
            Only a chain with no group is touched: one somebody gave a group
            has an answer, right or wrong, and this is not the tool to
            second-guess it.

            TWO guards, and the second one is the one that was missing.

            A joint that STARTS inside a collider is not restrained by it, it
            is EJECTED by it on frame one, so the fix aborts and names the
            joints rather than attaching the group. That refuses Killer Clown
            (both chains 7.6 mm inside the collider on `Hips`), Prix (186.5 mm
            inside the one on `FemaleBody_Head`) and Lola Bunny (51.2 mm
            inside `fml_un_C_pelvis_att`), and it refuses Miku's necktie,
            whose three joints sit 44.4, 30.5 and 7.4 mm inside `Bip01 Spine`.

            And a CHEST chain is skipped outright, because a chest chain with
            no collider group is this project's DECISION and not an omission
            -- see CHEST below. Without that skip this fix attached the group
            to the breast chains of five characters, all since reverted, and
            the clearance guard passed every one of them: they genuinely do
            clear the torso capsule at rest. A physical check cannot see an
            intent, which is why the intent has to be written in the code
            rather than inferred from the geometry.

  --reclear SHRINK a collider that swallows a non-anchor spring joint's
            sphere, to 0.95 of the real clearance. A joint inside a collider
            is not restrained by it, it is EJECTED to its surface and held
            there, so this is a permanent displacement rather than a glitch.

            The cause is one line in two places. `vrm_colliders.add()` and
            `--limbs` both shrank a collider to 0.95 of the distance to the
            nearest non-anchor joint's CENTRE, while the solver's condition
            is centre_distance >= collider_radius + joint_radius. Clearing
            the centre by 5% therefore leaves the nearest joint overlapping
            by (joint_radius - 5% of the distance): 14 to 19 mm at our 0.02
            hit radius. Both guards were corrected; this is for the bundles
            that will not be rebuilt, and it is the only fix that reaches the
            HEAD sphere and the TORSO capsule, which --limbs does not own.

            Measured in the spring runtime with YargSpringProbe's -still
            mode, which holds the character perfectly still so that any
            displacement at all is a collider ejecting a joint. Jinx, as
            installed, wind 0,0,0: peak 76.04 mm, 15 of 128 bones over 1 mm,
            her braid tips 76.0 and 70.2 mm out of place while she does
            nothing. After: 0.61 mm, 0 of 128.

            It only ever shrinks, it skips chest chains like every other fix
            here, and it leaves the limb capsules to --limbs when both are
            asked for so the two compose rather than race.

            AND IT HAS A FLOOR: never below 5 mm, and never below a quarter
            of the radius that was there. Without one it took Sayuri's
            `CC_Base_R_Upperarm` from 19 mm to 0.000 and Yoda's `Hips` from
            20 mm to 2 mm -- the Xenomorph catastrophe, reintroduced by the
            very guard meant to prevent it. Both were reverted from backups.
            Past the floor it leaves the overlap and says so, because a
            collider that is gone cannot deflect anything at all.

WHY PATCH RATHER THAN REBUILD. For 35 of the 65 installed characters there is
no source file left on this machine, so there is nothing to rebuild from. And
for some that do have one, the recorded recipe no longer reproduces what is
installed: Peach's rebuild matches her bundle on 173 bones with 63 rotation
mismatches, so rebuilding her would have shipped a pose change nobody asked for
alongside the spring fix. Changing the four scalars and provably nothing else
is the smaller claim and the one that can be checked.

The clearance guard is applied here too, and it is not optional: a collider
that CONTAINS a spring joint ejects it on frame one, which is the fault that
ballooned Gadget Hackwrench's hair into a mass bigger than she was. A capsule
is shrunk to 0.95 of the clearance to the nearest non-anchor joint's SPHERE
rather than being allowed to swallow it -- its surface, not its centre, since
the solver's condition is centre_distance >= collider_radius + joint_radius. The chain's FIRST joint is skipped, as in vrm_colliders.fit: it is
an anchor, its position comes from the skeleton rather than the simulation, and
guarding against it emptied the Xenomorph's torso capsule.

Verification is a full read-back: every object's state is fingerprinted before
and after, and anything differing that was not named is reported as a reason
NOT to install the result.
"""
import math
import os
import re
import struct
import sys

import UnityPy

import cloth_collide_installed as cci

CLOTH = r"(skirt|dress|cloth|cape|coat|robe|apron|tabard|sash|scarf)"
CHEST = r"(breast|bust|pectoral|boob)"
CLOTH_PARAMS = (0.5, 0.05, 0.0)
# --unrig-hair. Same three patterns as build_vrm.py's hair rigger, so the
# bundle patcher and the builder agree on what counts as hair, as a face and as
# headwear.
HAIRC = r"(hair|ponytail|braid|bang|fringe|twintail)"
FACE = (r"(lash|brow|iris|cornea|sclera|pupil|teeth|tooth|tongue|gum|mouth"
        r"|lip|eye)")
SHELL = (r"(hat|helmet|hood|cap|crown|mask|beanie|visor|headgear|headband"
         r"|horn)")
SEALED = float(os.environ.get("VRM_HAIR_SEALED", "0.5"))
# Beyond this, a nearest-VERTEX normal stops describing the local surface and
# starts inventing. Without the bound the first sweep written for this reported
# Peach's skirt as 1,583 mm "inside" her crown and Heels' hem as 447 mm inside
# a mesh called CC_Base_TearLine. The builder does not need the bound in the
# same way -- in Blender closest_point_on_mesh gives an exact face normal --
# but it applies the same 50 mm for the same reason.
SHELL_NEAR = 0.05
RIGID = 0.99
LIMB_PCT = float(os.environ.get("VRM_LIMB_PCT", "0.90"))
LIMBS = [("LeftUpperLeg", "LeftLowerLeg"), ("LeftLowerLeg", "LeftFoot"),
         ("RightUpperLeg", "RightLowerLeg"), ("RightLowerLeg", "RightFoot"),
         ("LeftUpperArm", "LeftLowerArm"), ("LeftLowerArm", "LeftHand"),
         ("RightUpperArm", "RightLowerArm"), ("RightLowerArm", "RightHand")]

# Unity VertexFormat: 0 Float32, 1 Float16, 2 UNorm8, 3 SNorm8, 4 UNorm16,
# 5 SNorm16, 6 UInt8, 7 SInt8, 8 UInt16, 9 SInt16, 10 UInt32, 11 SInt32.
# A wrong size here does not raise -- it shifts every later channel and returns
# plausible garbage -- so the stride is asserted against the buffer length.
SZ = {0: 4, 1: 2, 2: 1, 3: 1, 4: 2, 5: 2, 6: 1, 7: 1, 8: 2, 9: 2, 10: 4, 11: 4}
FMT = {0: "f", 1: "e", 6: "B", 7: "b", 8: "H", 9: "h", 10: "I", 11: "i"}


def trs(p, q, s):
    """A bone's world matrix, as 12 floats (3x4, row-major)."""
    w, x, y, z = q
    m = [
        (1 - 2 * (y * y + z * z)) * s[0], 2 * (x * y - w * z) * s[1],
        2 * (x * z + w * y) * s[2], p[0],
        2 * (x * y + w * z) * s[0], (1 - 2 * (x * x + z * z)) * s[1],
        2 * (y * z - w * x) * s[2], p[1],
        2 * (x * z - w * y) * s[0], 2 * (y * z + w * x) * s[1],
        (1 - 2 * (x * x + y * y)) * s[2], p[2]]
    return m


def mat4(d):
    return [d["e%d%d" % (r, c)] for r in range(3) for c in range(4)] \
        + [d["e30"], d["e31"], d["e32"], d["e33"]]


def mul(a, b):
    """a * b, both 3x4-plus-last-row; returns 3x4 (16 floats in, 12 out)."""
    out = []
    for r in range(3):
        for c in range(4):
            v = 0.0
            for k in range(3):
                v += a[r * 4 + k] * b[k * 4 + c]
            v += a[r * 4 + 3] * (b[12 + c] if len(b) > 12 else
                                 (1.0 if c == 3 else 0.0))
            out.append(v)
    return out


def xform(m, v):
    return (m[0] * v[0] + m[1] * v[1] + m[2] * v[2] + m[3],
            m[4] * v[0] + m[5] * v[1] + m[6] * v[2] + m[7],
            m[8] * v[0] + m[9] * v[1] + m[10] * v[2] + m[11])


def decode(tt):
    """positions, blend weights and bone indices out of the vertex buffer."""
    got = decode_ch(tt, (0, 12, 13))
    return None if got is None else (got[0], got[12], got[13])


def decode_ch(tt, idxs):
    """{channel index: [tuple per vertex]} for the channels asked for.

    Channel 0 is Position, 1 Normal, 12 BlendWeight, 13 BlendIndices.
    m_Skin and m_BoneNameHashes are empty in these bundles; this buffer is
    where the skinning actually is.
    """
    vd = tt.get("m_VertexData") or {}
    n = vd.get("m_VertexCount") or 0
    chans = vd.get("m_Channels") or []
    raw = bytes(vd.get("m_DataSize") or b"")
    if not n or not raw:
        return None
    strides = {}
    for c in chans:
        if not c.get("dimension"):
            continue
        strides[c["stream"]] = strides.get(c["stream"], 0) \
            + SZ.get(c["format"], 0) * c["dimension"]
    starts, off = {}, 0
    for st in sorted(strides):
        off = (off + 15) // 16 * 16     # each stream STARTS 16-byte aligned
        starts[st] = off
        off += strides[st] * n          # the last one is not padded at the end
    if off != len(raw):
        return None
    out = {}
    for idx in idxs:
        if idx >= len(chans) or not chans[idx].get("dimension"):
            return None
        c = chans[idx]
        if c["format"] not in FMT:
            return None
        fmt = "<%d%s" % (c["dimension"], FMT[c["format"]])
        base, stride = starts[c["stream"]] + c["offset"], strides[c["stream"]]
        vals = []
        for i in range(n):
            p = base + i * stride
            if p + struct.calcsize(fmt) > len(raw):
                return None
            vals.append(struct.unpack_from(fmt, raw, p))
        out[idx] = vals
    return out


def _pct(vals, q):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(q * len(vals)))] if vals else 0.0


def flesh_radii(env, tf, go_tf, world, human, bone_name):
    """{bone name: p-th percentile distance of the flesh it dominates}."""
    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())
    per_bone, skipped = {}, 0
    for r in smrs:
        tt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if tt is None or not r.get("m_Enabled", True):
            continue
        got = decode(tt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [mat4(m) for m in (tt.get("m_BindPose") or [])]
        if got is None or len(bind) != len(bones) or not bones:
            skipped += 1
            continue
        V, W, I = got
        skin = [mul(trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
        for vi in range(len(V)):
            ws = W[vi]
            best, bw = None, -1.0
            px = py = pz = 0.0
            for k in range(len(ws)):
                w = ws[k]
                bi = I[vi][k]
                if w <= 0 or bi >= len(skin):
                    continue
                q = xform(skin[bi], V[vi])
                px += w * q[0]
                py += w * q[1]
                pz += w * q[2]
                if w > bw:
                    best, bw = bones[bi], w
            if best is not None:
                per_bone.setdefault(best, []).append((px, py, pz))
    return per_bone, skipped


def _skin_mesh(r, tt, world):
    """(world positions, world-ish normals, dominant bone) per vertex."""
    ch = decode_ch(tt, (0, 1, 12, 13))
    bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
    bind = [mat4(m) for m in (tt.get("m_BindPose") or [])]
    if ch is None or len(bind) != len(bones) or not bones:
        return None
    V, N, W, I = ch[0], ch[1], ch[12], ch[13]
    skin = [mul(trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
    pts, nrm, dom = [], [], []
    for vi in range(len(V)):
        px = py = pz = 0.0
        best, bw = None, -1.0
        for k in range(len(W[vi])):
            w, bi = W[vi][k], I[vi][k]
            if w <= 0 or bi >= len(skin):
                continue
            q = xform(skin[bi], V[vi])
            px += w * q[0]
            py += w * q[1]
            pz += w * q[2]
            if w > bw:
                best, bw = bones[bi], w
        pts.append((px, py, pz))
        # The normal is left in the mesh's own frame. These bundles place the
        # figure upright with no rotation on the root, so for the only use it
        # has here -- the SIGN of a dot product against a nearby face -- that
        # is the same answer. Its control is in probe form: the head's own
        # scalp must read inside the shell and the nose outside it.
        nrm.append(N[vi][:3])
        dom.append(best)
    return pts, nrm, dom


def _inside(p, pts, nrm, lo, hi):
    """Signed distance into a shell, or None when out of range.

    Declining is the point. A nearest-vertex normal describes the surface it
    belongs to and nothing further away, so a point metres from the shell gets
    no answer rather than a confident wrong one.
    """
    for i in range(3):
        if not (lo[i] - SHELL_NEAR <= p[i] <= hi[i] + SHELL_NEAR):
            return None
    bi, bd = 0, 1e9
    for i, q in enumerate(pts):
        dd = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2)
        if dd < bd:
            bi, bd = i, dd
    if bd > SHELL_NEAR ** 2:
        return None
    q, nv = pts[bi], nrm[bi]
    v = (p[0] - q[0], p[1] - q[1], p[2] - q[2])
    L = math.sqrt(nv[0] ** 2 + nv[1] ** 2 + nv[2] ** 2) or 1.0
    return (v[0] * nv[0] + v[1] * nv[1] + v[2] * nv[2]) / L


def hair_verdict(env, tf, go_tf, world, human, springs, joints):
    """[(spring index, name, [reason, ...])] for hair chains to remove."""
    owner = {}
    for si, (sname, jids, gids) in enumerate(springs):
        if not re.search(HAIRC, sname or "", re.I):
            continue
        for jid in jids:
            j = joints.get(jid)
            if not j:
                continue
            tid = go_tf.get(j[0])
            if tid is not None:
                owner[tid] = si
    if not owner:
        return [], 0

    head_tf = None
    for pid, n in tf.items():
        if n["name"] == human.get("Head"):
            head_tf = pid
            break

    tt_mesh, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt_mesh[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    shells, driven, undec = [], {}, 0
    for r in smrs:
        tt = tt_mesh.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if tt is None:
            continue
        mn = tt.get("m_Name") or "?"
        got = _skin_mesh(r, tt, world)
        if got is None:
            undec += 1
            continue
        pts, nrm, dom = got
        cnt = {}
        for d in dom:
            cnt[d] = cnt.get(d, 0) + 1
        top = max(cnt.items(), key=lambda kv: kv[1]) if cnt else (None, 0)
        if (top[0] is not None and top[0] == head_tf
                and top[1] >= RIGID * len(pts)
                and re.search(SHELL, mn, re.I)):
            shells.append((mn, pts, nrm,
                           tuple(min(p[i] for p in pts) for i in range(3)),
                           tuple(max(p[i] for p in pts) for i in range(3))))
        for p, d in zip(pts, dom):
            if d in owner:
                driven.setdefault(owner[d], []).append((mn, p))

    out = []
    for si, items in sorted(driven.items()):
        sname = springs[si][0]
        reasons = []
        faces = {}
        for mn, _p in items:
            if re.search(FACE, mn, re.I):
                faces[mn] = faces.get(mn, 0) + 1
        if faces:
            reasons.append("drives a facial feature: "
                           + ", ".join("%s %d vert(s)" % kv
                                       for kv in sorted(faces.items())))
        rest = [p for mn, p in items if not re.search(FACE, mn, re.I)]
        for mn, pts, nrm, lo, hi in shells:
            sd = [_inside(p, pts, nrm, lo, hi) for p in rest]
            ins = [s for s in sd if s is not None and s < 0]
            if rest and len(ins) >= SEALED * len(rest):
                reasons.append("%d of its %d non-facial vertices (%.0f%%) are "
                               "sealed inside '%s', deepest %.1f mm"
                               % (len(ins), len(rest),
                                  100.0 * len(ins) / len(rest), mn,
                                  -1000.0 * min(ins)))
        if reasons:
            out.append((si, sname, reasons))
    return out, undec


def fingerprint(env):
    """Everything readable, so an unintended change cannot hide."""
    fp = {}
    for obj in env.objects:
        t = obj.type.name
        try:
            tt = obj.read_typetree()
        except Exception:                                        # noqa: BLE001
            continue
        key = "%s:%d" % (t, obj.path_id)
        fp[key] = repr(tt)
    return fp


def main():
    args = [a for a in sys.argv[1:]]
    do_cloth = "--cloth" in args
    do_limbs = "--limbs" in args
    do_hair = "--unrig-hair" in args
    do_collide = "--collide" in args
    do_reclear = "--reclear" in args
    dry = "--dry-run" in args
    want_group = None
    if "--group" in args:
        want_group = args[args.index("--group") + 1]
    out = None
    if "--out" in args:
        out = args[args.index("--out") + 1]
    files = [a for a in args
             if not a.startswith("--") and a != out and a != want_group]
    if len(files) != 1 or not (do_cloth or do_limbs or do_hair
                              or do_collide or do_reclear):
        print(__doc__)
        return 2
    src = files[0]
    out = out or src

    # A path that does not exist used to reach cci.read, come back with
    # nothing, and be reported as "has no spring chains" -- a FALSE ZERO about
    # the character rather than a true statement about the path. A sweep whose
    # filenames had picked up a trailing \r reported that for all 21, Prix and
    # her five chains among them, and it reads exactly like a finding.
    if not os.path.isfile(src):
        print("ABORT: no file at %r (a trailing newline or carriage return in "
              "a generated list is the usual cause)" % src)
        return 2

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(src)
    if not springs:
        print("ABORT: %s has no spring chains" % os.path.basename(src))
        return 2
    env = UnityPy.load(src)
    before = fingerprint(env)

    bone_name = {}
    for pid, n in tf.items():
        if n["name"]:
            bone_name.setdefault(n["name"], pid)

    # ---- which joint MonoBehaviours belong to a cloth chain ---------------
    want_joint = {}
    nchain = 0
    for sname, jids, gids in springs:
        if re.search(CHEST, sname or "", re.I):
            continue
        if not re.search(CLOTH, sname or "", re.I):
            continue
        nchain += 1
        for jid in jids:
            want_joint[jid] = CLOTH_PARAMS
    if do_cloth:
        print("  cloth: %d chain(s), %d joint(s) -> stiffness %.2f, drag "
              "%.2f, gravity %.2f" % (nchain, len(want_joint),
                                      *CLOTH_PARAMS))
        if not want_joint:
            print("         no cloth-named chain in this bundle")

    # ---- which collider MonoBehaviours are limb capsules, and how big -----
    want_col = {}
    if do_limbs:
        per_bone, skipped = flesh_radii(env, tf, go_tf, world, human,
                                        bone_name)
        if skipped:
            print("  limbs: %d mesh(es) could not be decoded -- their "
                  "vertices are NOT in the measurement" % skipped)
        # Every non-anchor joint, for the clearance guard.
        guard = []
        for sname, jids, gids in springs:
            if re.search(CHEST, sname or "", re.I):
                continue
            for jid in jids[1:]:
                j = joints.get(jid)
                if not j:
                    continue
                tid = go_tf.get(j[0])
                if tid is not None:
                    # Position AND the joint's own hit radius, j[4]. It was
                    # read into `joints` all along and never used here; see
                    # the same fix in vrm_colliders.add() for why a guard
                    # that clears only centres leaves the nearest joint
                    # ejected by (joint_radius - 5% of the distance).
                    guard.append((world(tid)[0], j[4]))
        for hk, hc in LIMBS:
            bn, cn = cci.hname(human, hk), cci.hname(human, hc)
            if not bn or not cn or bn not in bone_name or cn not in bone_name:
                continue
            A, B = world(bone_name[bn])[0], world(bone_name[cn])[0]
            pts = per_bone.get(bone_name[bn]) or []
            if len(pts) < 16:
                print("  limbs: %-14s only %d vertices dominated by it -- "
                      "left alone" % (hk, len(pts)))
                continue
            want = _pct([cci.seg_dist(p, A, B) for p in pts], LIMB_PCT)
            # Clearance to the nearest joint's SURFACE, which is what the
            # solver compares against -- not to its centre.
            near = min((cci.seg_dist(g, A, B) - jr for g, jr in guard),
                       default=None)
            shrunk = None
            if near is not None and near * 0.95 < want:
                if near * 0.95 <= 1e-5:
                    print("  limbs: WARNING %s not resized -- a non-anchor "
                          "spring joint's sphere reaches the bone axis "
                          "(clearance %.4f); the joint radius is too large "
                          "for this limb" % (hk, near))
                    continue
                shrunk = (want, near * 0.95, near)
                want = near * 0.95
            if want > 1e-5:
                want_col[bn] = (hk, want, shrunk)

    # ---- which hair chains should not exist at all ------------------------
    drop = []
    if do_hair:
        drop, undec = hair_verdict(env, tf, go_tf, world, human, springs,
                                   joints)
        if undec:
            print("  hair: %d mesh(es) could not be decoded -- their vertices "
                  "are NOT in the measurement, so a chain that only drives "
                  "those will not be found" % undec)
        for si, sname, reasons in drop:
            print("  hair: REMOVE chain %d '%s'" % (si, sname))
            for r in reasons:
                print("          %s" % r)
        if not drop:
            print("  hair: no chain drives a facial feature or sits sealed "
                  "inside a rigid head mesh")

    # ---- apply -----------------------------------------------------------
    done_j, done_c, skip_j, skip_c = [], [], 0, 0
    done_h = 0
    # ---- --collide: give a chain that has NO collider group one ----------
    attach, gpid, done_g = [], None, 0
    if do_collide:
        from patch_add_springs import qrot as _qrot, seg_dist as _seg
        # cci.read returns `groups` as {group path_id: [collider path_ids]} --
        # the MEMBERS, not a name. So a group is chosen by being the only one,
        # or by its path_id, and not by a name this structure does not carry.
        if want_group:
            try:
                gpid = int(want_group)
            except ValueError:
                print("ABORT: --group takes a collider-group path_id (this "
                      "file has %s), because the group list carries members "
                      "rather than names" % sorted(groups))
                return 2
            if gpid not in groups:
                print("ABORT: no collider group with path_id %d; this file "
                      "has %s" % (gpid, sorted(groups)))
                return 2
        elif len(groups) == 1:
            gpid = list(groups)[0]
        else:
            print("ABORT: this file has %d collider groups (%s); name one "
                  "with --group <path_id>" % (len(groups), sorted(groups)))
            return 2
        # the group's colliders, in world space. Offset and Tail are in the
        # collider BONE's frame, so they go through that bone's matrix.
        _cols = []
        for _cp, _ct in colliders.items():
            _gid = _ct.get("m_GameObject", {}).get("m_PathID")
            _tp = go_tf.get(_gid)
            if _tp is None:
                continue
            _wp, _wq, _wsv = world(_tp)
            # cci.read's world() hands back scale as a 3-tuple, where
            # patch_add_springs' own returns a float. These colliders are
            # uniformly scaled, so take one component -- and take it
            # deliberately rather than by multiplying a tuple by a float,
            # which is what the first version did.
            _ws = _wsv[0] if isinstance(_wsv, (tuple, list)) else _wsv
            _o1 = _ct["Offset"]
            _t1 = _ct["Tail"]
            _a = _qrot(_wq, (_o1["x"] * _ws, _o1["y"] * _ws, _o1["z"] * _ws))
            _a = (_wp[0] + _a[0], _wp[1] + _a[1], _wp[2] + _a[2])
            if _ct.get("ColliderType") == 1:
                _b = _qrot(_wq, (_t1["x"] * _ws, _t1["y"] * _ws,
                                 _t1["z"] * _ws))
                _b = (_wp[0] + _b[0], _wp[1] + _b[1], _wp[2] + _b[2])
            else:
                _b = _a
            _cols.append((_cp, tf[_tp]["name"], _ct["Radius"] * _ws, _a, _b))
        _mine = [c for c in _cols if c[0] in (groups.get(gpid) or [])]
        _bad = []
        _chest = []
        for _si, (_sn, _jids, _gids) in enumerate(springs):
            if _gids:
                continue
            # A CHEST chain with no collider group is this project's own
            # DECISION, not an omission. vrm_colliders.add() skips exactly
            # these when it attaches the group, for the reason written beside
            # CHEST there and at the top of this file: a chest chain sits ON
            # the torso, and the torso capsule is a crude cylinder outside the
            # ribcage, so handing it over pushes the chest out of the body it
            # belongs to.
            #
            # --collide shipped WITHOUT this check and attached the group to
            # the breast chains of Jessica Rabbit, Tenna, Power Girl, Sayuri
            # and Heels before anyone read the constant three hundred lines
            # above, in this same file, that already excludes them from
            # --cloth and from the --limbs guard. All five were reverted.
            #
            # The clearance guard did not catch it and could not: it asks
            # whether a joint starts INSIDE a collider, and four of the five
            # cleared every collider of the group at rest -- Jessica's
            # tightest was +19.5 mm. "Is this physically possible" is not
            # "is this what the builder decided", and the measurement only
            # ever answered the first one.
            if re.search(CHEST, _sn or "", re.I):
                _chest.append(_sn)
                continue
            for _jid in _jids:
                _j = joints.get(_jid)
                if not _j:
                    continue
                _t = go_tf.get(_j[0])
                if _t is None:
                    continue
                _jp = world(_t)[0]
                _jr = _j[4]
                for _cp, _cn, _r, _a, _b in _mine:
                    _clear = _seg(_jp, _a, _b) - _r - _jr
                    if _clear < 0.0:
                        _bad.append((_sn, tf[_t]["name"], _cn, _clear))
            attach.append((_si, _sn))
        if _bad:
            print("ABORT: these joints START INSIDE a collider of the group "
                  "they would be given:")
            for _sn, _bn, _cn, _c in _bad[:8]:
                print("    chain %-18s joint %-20s is %6.1f mm inside the "
                      "collider on %r" % (_sn, _bn, -_c * 1000, _cn))
            print("  The solver's first act is to push a joint out to the "
                  "collider's surface, so this would displace the chain on "
                  "frame one rather than restrain it. Nothing written.")
            return 2
        if _chest:
            print("  collide: %d chest chain(s) deliberately left with no "
                  "collider group (%s) -- see CHEST above, and "
                  "vrm_colliders.add()" % (len(_chest), ", ".join(_chest)))
        if not attach:
            print("  collide: no chain is missing a collider group it is "
                  "meant to have")
        else:
            print("  collide: %d chain(s) have no collider group and clear "
                  "all %d colliders of the group at rest -- attaching it: %s"
                  % (len(attach), len(_mine),
                     ", ".join(n for _i, n in attach)))

    # ---- --reclear: shrink a collider that SWALLOWS a spring joint -------
    #
    # The same arithmetic as the --limbs guard, applied to the colliders
    # --limbs does not own: the head sphere and the torso capsule. Both are
    # written by vrm_colliders.add(), whose guard cleared a joint's CENTRE and
    # not its sphere, so the nearest non-anchor joint of every chain that
    # references them starts (joint_radius - 5% of the distance) inside.
    #
    # Measured in the spring runtime on Jinx, standing perfectly still with
    # zero external force, her chains are ejected permanently: braid tips
    # 76.0 and 70.2 mm out of place, 15 bones over 1 mm. --limbs with the
    # fixed guard takes the braids to 0.6 mm; her bangs stay at 38.8 mm
    # because they ride the `head` sphere, which is this fix's job.
    #
    # It only ever SHRINKS, which is the direction vrm_colliders already
    # argues for ("err SMALL"), and it costs nothing in reach: the surface
    # the solver actually tests is radius + joint_radius, so taking the
    # radius down by the joint radius leaves that surface where the joint
    # rests -- on the body -- instead of 19 mm outside it.
    reclear = {}
    if do_reclear:
        rguard = []
        for _sn, _jids, _gids in springs:
            if re.search(CHEST, _sn or "", re.I):
                continue
            for _jid in _jids[1:]:
                _j = joints.get(_jid)
                if not _j:
                    continue
                _tid = go_tf.get(_j[0])
                if _tid is not None:
                    rguard.append((world(_tid)[0], _j[4]))
        if not rguard:
            print("  reclear: no non-anchor spring joint in this bundle -- "
                  "nothing to clear against")
        for _cp, _ct in colliders.items():
            _tid = go_tf.get((_ct.get("m_GameObject") or {}).get("m_PathID"))
            if _tid is None:
                continue
            _bn = tf[_tid]["name"]
            # --limbs owns the limb capsules; keep the two fixes disjoint so
            # they compose instead of racing to set the same radius.
            if _bn in want_col:
                continue
            _wp, _wq, _wsv = world(_tid)
            _ws = _wsv[0] if isinstance(_wsv, (tuple, list)) else _wsv
            if _ws <= 1e-9:
                continue
            _o, _t = _ct["Offset"], _ct["Tail"]
            _a = cci.qrot(_wq, (_o["x"] * _ws, _o["y"] * _ws,
                                _o["z"] * _ws))
            _a = (_wp[0] + _a[0], _wp[1] + _a[1], _wp[2] + _a[2])
            if _ct.get("ColliderType") == 1:
                _b = cci.qrot(_wq, (_t["x"] * _ws, _t["y"] * _ws,
                                    _t["z"] * _ws))
                _b = (_wp[0] + _b[0], _wp[1] + _b[1], _wp[2] + _b[2])
            else:
                _b = _a
            _rw = float(_ct.get("Radius", 0.0)) * _ws
            _near = min((cci.seg_dist(_g, _a, _b) - _jr
                         for _g, _jr in rguard), default=None)
            if _near is None or _near * 0.95 >= _rw:
                continue
            # A FLOOR, and it is not optional. `1e-5` was the first guard
            # here and it is far too lenient: a clearance of 0.0001 m passes
            # it and writes a 0.1 mm collider, which is a deleted collider
            # with extra steps. Applied to the roster it took Sayuri's
            # `CC_Base_R_Upperarm` from 19 mm to 0.000 and Yoda's `Hips` from
            # 20 mm to 2 mm -- the Xenomorph catastrophe, reintroduced by the
            # guard meant to prevent it. Both were reverted from backups.
            #
            # So: never below 5 mm, and never below a quarter of what was
            # there. A reduction past either means the nearest joint sits
            # essentially ON the bone axis, and the honest answer is that the
            # joint radius is too large for that geometry -- not that the
            # body part should stop existing. Leaving the overlap is the
            # lesser fault, because a collider that is gone cannot deflect
            # anything at all.
            _floor = max(0.005, 0.25 * _rw)
            if _near * 0.95 < _floor:
                print("  reclear: WARNING %s left alone -- clearing it would "
                      "need %.4f m, below the floor of %.4f (5 mm, or a "
                      "quarter of its %.3f). A non-anchor joint sits almost "
                      "on this bone's axis; its %.0f mm radius is too large "
                      "for this geometry. The overlap stays."
                      % ((_bn or "?")[:22], _near * 0.95, _floor, _rw,
                         min(jr for _g, jr in rguard) * 1000))
                continue
            reclear[_cp] = (_bn, _rw, _near * 0.95, _near, _ws)
        if do_reclear and not reclear:
            print("  reclear: every collider outside --limbs' reach already "
                  "clears every non-anchor joint's sphere")

    done_rc = []
    found_col = set()
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            cn = obj.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            continue
        if do_collide and attach and cn == "Vrm10Instance" and not done_g:
            # A chain with NO collider group is not restrained by anything:
            # it swings straight through the body. That is Peach's dress, and
            # it is why --cloth alone did not fix her.
            #
            # It was ALSO claimed of Jessica Rabbit's two breast chains, and
            # that was wrong: a chest chain having no group is deliberate.
            # See the CHEST skip in the candidate loop above.
            #
            # Only chains that have NO group at all are touched. A chain
            # somebody gave a group already has an answer, right or wrong, and
            # this is not the tool to second-guess it.
            tt = obj.read_typetree()
            sb = tt.get("SpringBone") or {}
            arr = sb.get("Springs") or []
            if len(arr) != len(springs):
                print("  collide: this Vrm10Instance lists %d spring(s) but "
                      "the read found %d -- NOT touching it"
                      % (len(arr), len(springs)))
                continue
            ok = True
            for si, _nm in attach:
                if (arr[si].get("Name") or "?") != springs[si][0]:
                    print("  collide: index %d is '%s' here and '%s' in the "
                          "read -- NOT touching it"
                          % (si, arr[si].get("Name"), springs[si][0]))
                    ok = False
                    break
            if not ok:
                continue
            for si, _nm in attach:
                arr[si]["ColliderGroups"] = [{"m_FileID": 0,
                                              "m_PathID": gpid}]
            sb["Springs"] = arr
            tt["SpringBone"] = sb
            obj.save_typetree(tt)
            done_g = len(attach)
        elif do_hair and drop and cn == "Vrm10Instance":
            # The Springs array is the single source of truth: the runtime
            # builds its simulation buffers from vrm.SpringBone.Springs and
            # never looks for joint components on its own, so an orphaned
            # VRM10SpringBoneJoint is inert and is left where it is. The BONES
            # stay too, which is the whole point -- every vertex keeps the
            # position the model gives it and only the motion stops.
            tt = obj.read_typetree()
            sb = tt.get("SpringBone") or {}
            arr = sb.get("Springs") or []
            if len(arr) != len(springs):
                print("  hair: this Vrm10Instance lists %d spring(s) but the "
                      "read found %d -- NOT touching it" % (len(arr),
                                                            len(springs)))
                continue
            bad = [si for si, _n, _r in drop]
            for si in bad:
                got = (arr[si].get("Name") or "?")
                if got != springs[si][0]:
                    print("  hair: index %d is '%s' here and '%s' in the read "
                          "-- NOT touching it" % (si, got, springs[si][0]))
                    bad = None
                    break
            if bad is None:
                continue
            sb["Springs"] = [s for i, s in enumerate(arr) if i not in bad]
            tt["SpringBone"] = sb
            obj.save_typetree(tt)
            done_h = len(bad)
        elif do_cloth and cn == "VRM10SpringBoneJoint" \
                and obj.path_id in want_joint:
            tt = obj.read_typetree()
            s, d, g = want_joint[obj.path_id]
            if (abs(tt.get("m_stiffnessForce", 0.0) - s) < 1e-6
                    and abs(tt.get("m_dragForce", 0.0) - d) < 1e-6
                    and abs(tt.get("m_gravityPower", 0.0) - g) < 1e-6):
                skip_j += 1
                continue
            done_j.append((tt.get("m_stiffnessForce", 0.0),
                           tt.get("m_dragForce", 0.0)))
            tt["m_stiffnessForce"] = s
            tt["m_dragForce"] = d
            tt["m_gravityPower"] = g
            obj.save_typetree(tt)
        elif (do_limbs or do_reclear) and cn == "VRM10SpringBoneCollider":
            tt = obj.read_typetree()
            tid = go_tf.get(tt["m_GameObject"]["m_PathID"])
            nm = tf.get(tid, {}).get("name") if tid is not None else None
            if obj.path_id in reclear:
                _bn, _rw, _new, _near, _ws = reclear[obj.path_id]
                old_r = float(tt.get("Radius", 0.0))
                tt["Radius"] = _new / _ws
                obj.save_typetree(tt)
                done_rc.append((_bn, _rw, _new, _near))
                continue
            if nm not in want_col:
                skip_c += 1
                continue
            hk, want, shrunk = want_col[nm]
            found_col.add(nm)
            old = float(tt.get("Radius", 0.0))
            # 0.01 mm, not 1e-6 m: below that it is float noise reported as a
            # change, and it would be counted in the read-back's expected total.
            if abs(old - want) < 1e-5:
                skip_c += 1
                continue
            tt["Radius"] = want
            obj.save_typetree(tt)
            done_c.append((hk, nm, old, want, shrunk))

    if done_j:
        olds = sorted(set("%.2f/%.2f" % v for v in done_j))
        print("  cloth: %d joint(s) changed, from %s"
              % (len(done_j), ", ".join(olds)))
    if skip_j:
        print("  cloth: %d joint(s) already at the target" % skip_j)
    for hk, nm, old, want, shrunk in done_c:
        print("  limbs: %-14s %-24s %.3f -> %.3f (%+.1f mm)%s"
              % (hk, nm[:24], old, want, (want - old) * 1000,
                 ("  -- shrunk from %.3f so it clears the nearest spring "
                  "joint at %.3f" % (shrunk[0], shrunk[2])) if shrunk else ""))
    # A bone this wanted to resize but found no collider on. Printing the
    # intended radius without this reads as work that happened: Yoda's four
    # leg capsules were "shrunk to 0.033" in an early run and he has no leg
    # colliders at all, so nothing was resized and nothing said so.
    for nm, (hk, want, _s) in sorted(want_col.items()):
        if nm not in found_col:
            print("  limbs: %-14s %-24s NO COLLIDER on this bone -- --limbs "
                  "resizes one that exists, it cannot add a missing one "
                  "(wanted %.3f)" % (hk, nm[:24], want))
    # Gated on do_limbs: with only --reclear running, want_col is empty, so
    # every collider lands in skip_c and this would report the whole file as
    # "left alone" in the same breath as reclear reporting it changed.
    if skip_c and do_limbs:
        print("  limbs: %d collider(s) left alone (head, torso, or already "
              "right)" % skip_c)
    for _bn, _rw, _new, _near in sorted(done_rc, key=lambda x: x[1] - x[2],
                                        reverse=True):
        print("  reclear: %-24s %.3f -> %.3f (%+.1f mm) so it clears the "
              "nearest non-anchor joint's SPHERE at %.3f"
              % ((_bn or "?")[:24], _rw, _new, (_new - _rw) * 1000, _near))
    if done_h:
        print("  hair: %d chain(s) removed from the Springs array; their "
              "bones, joints and meshes are untouched" % done_h)
    if (not done_j and not done_c and not done_h and not done_g
            and not done_rc):
        print("nothing to do")
        return 2
    if dry:
        print("  --dry-run: nothing written")
        return 0

    # packer="original" keeps the bundle's own compression; a plain save()
    # writes it uncompressed and quadruples the file.
    #
    # Verified from the bytes in memory, BEFORE anything is written. Writing a
    # temp file and reading it back works until it does not: UnityPy holds the
    # handle open, so on Windows the rename afterwards fails with WinError 32
    # and leaves a verified-but-unnamed file on disk. Verifying first also
    # means a failed check writes nothing at all.
    data = env.file.save(packer="original")
    after = fingerprint(UnityPy.load(data))
    changed = [k for k in before if before.get(k) != after.get(k)]
    gone = [k for k in before if k not in after]
    added = [k for k in after if k not in before]
    # One object per changed joint, one per resized collider, and ONE for the
    # whole hair removal however many chains it dropped -- they all live in the
    # single Vrm10Instance.
    expect = (len(done_j) + len(done_c) + len(done_rc)
              + (1 if (done_h or done_g) else 0))
    print("  read-back: %d object(s) readable, %d changed (expected %d), "
          "%d gone, %d added"
          % (len(after), len(changed), expect, len(gone), len(added)))
    bad = gone + added
    if len(changed) != expect or bad:
        for k in sorted(changed)[:6]:
            if not k.startswith("MonoBehaviour:"):
                print("    unexpected: %s" % k)
        print("  WARNING: the read-back does not match what was asked for -- "
              "nothing was written")
        return 1
    with open(out, "wb") as f:
        f.write(data)
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
