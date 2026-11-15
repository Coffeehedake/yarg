# -*- coding: utf-8 -*-
"""Fix the spring simulation in an INSTALLED .yargchar, in place.

    python patch_springs.py <in.yargchar> [--cloth] [--limbs] [--out X]
        [--dry-run]

Two independent defects, either or both:

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
is shrunk to 0.95 of the nearest non-anchor joint rather than being allowed to
swallow it. The chain's FIRST joint is skipped, as in vrm_colliders.fit: it is
an anchor, its position comes from the skeleton rather than the simulation, and
guarding against it emptied the Xenomorph's torso capsule.

Verification is a full read-back: every object's state is fingerprinted before
and after, and anything differing that was not named is reported as a reason
NOT to install the result.
"""
import os
import re
import struct
import sys

import UnityPy

import cloth_collide_installed as cci

CLOTH = r"(skirt|dress|cloth|cape|coat|robe|apron|tabard|sash|scarf)"
CHEST = r"(breast|bust|pectoral|boob)"
CLOTH_PARAMS = (0.5, 0.05, 0.0)
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
    for idx in (0, 12, 13):
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
    return out[0], out[12], out[13]


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
    dry = "--dry-run" in args
    out = None
    if "--out" in args:
        out = args[args.index("--out") + 1]
    files = [a for a in args
             if not a.startswith("--") and a != out]
    if len(files) != 1 or not (do_cloth or do_limbs):
        print(__doc__)
        return 2
    src = files[0]
    out = out or src
    if not do_cloth and not do_limbs:
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
                    guard.append(world(tid)[0])
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
            near = min((cci.seg_dist(g, A, B) for g in guard), default=None)
            shrunk = None
            if near is not None and near * 0.95 < want:
                shrunk = (want, near * 0.95, near)
                want = near * 0.95
            if want > 1e-5:
                want_col[bn] = (hk, want, shrunk)

    # ---- apply -----------------------------------------------------------
    done_j, done_c, skip_j, skip_c = [], [], 0, 0
    found_col = set()
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            cn = obj.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            continue
        if do_cloth and cn == "VRM10SpringBoneJoint" \
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
        elif do_limbs and cn == "VRM10SpringBoneCollider":
            tt = obj.read_typetree()
            tid = go_tf.get(tt["m_GameObject"]["m_PathID"])
            nm = tf.get(tid, {}).get("name") if tid is not None else None
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
    if skip_c:
        print("  limbs: %d collider(s) left alone (head, torso, or already "
              "right)" % skip_c)
    if not done_j and not done_c:
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
    expect = len(done_j) + len(done_c)
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
