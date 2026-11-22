# -*- coding: utf-8 -*-
"""Set `m_jointRadius` / `m_gravityPower` on chosen joints of chosen spring chains.

    python set_joint_params.py <file.yargchar> --chain NAME [--chain NAME ...]
           [--from-index N] [--joint-radius MM] [--gravity P] [--write]

WHY. The cape probe measured the thing that decides how deep cloth gets: **distance from a
garment vertex to the nearest spring joint**, and the ceiling steps sharply at about 40 mm.

    dist to nearest joint    penetrating    max depth
    0-20 mm                        3.5%       21.0 mm
    20-40 mm                       7.3%       25.2 mm
    40-60 mm                      10.7%       61.0 mm
    60-80 mm                      12.3%       70.2 mm
    100-150 mm                    10.4%      124.8 mm

Nothing within 40 mm of a joint ever exceeded 25 mm; past it, 125 mm. Batman's joints carry
`m_jointRadius = 0.02`, so **the protected zone is about twice the joint radius** -- which says
the same hole can be closed from either end: more joints across the sheet, or a bigger radius
on the joints already there. His cape's adjacent chains are 236-337 mm apart, so closing it with
chains means roughly tripling them (~240 new bones and a cape re-weight); this tool is the other
end, and it is a float.

WHAT THIS IS NOT. Raising the radius on a joint that RESTS against the body is the same mistake
as fattening a collider, which was measured on 2026-11-21 to make penetration 3.07x worse:
collision tests `dist(joint, collider) < colliderR + jointR`, so the two are additive, and a
joint that starts inside is shoved out on frame one and the spring then overshoots. That is why
`--from-index` exists and defaults to 3: the joints near the attachment are the ones lying on the
skin, and they keep their authored radius. Raising everything uniformly is predicted to
reproduce the 3x harm, and the prediction is recorded here rather than in a commit message after
the fact.

`m_gravityPower` is 0.00 on every chain of this roster, so a cape has no restoring force once
something throws it. That is a separate lever on a separate mechanism and is applied separately.

It backs the file up, keeps the bundle a `UnityFS` bundle, and verifies on the bytes in hand --
checking BOTH directions, that every selected joint changed and that no unselected joint did.
"""
import hashlib
import io as _io
import os
import shutil
import sys

import cloth_collide_installed as cci
import UnityPy

BACKUP_DIR = r"C:\dev\YARG - Open Source Contributions\character-backups"


def die(msg):
    print("REFUSED: %s" % msg)
    sys.exit(1)


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    chains = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--chain"]
    if not chains:
        die("--chain is required; this tool never touches a chain nobody named")
    frm = int(arg("--from-index", 3))
    jr = arg("--joint-radius")
    gp = arg("--gravity")
    write = "--write" in sys.argv
    if jr is None and gp is None:
        die("nothing asked for: pass --joint-radius and/or --gravity")
    jr = None if jr is None else float(jr) / 1000.0
    gp = None if gp is None else float(gp)

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    by_name = {s[0]: s for s in springs}
    missing = [c for c in chains if c not in by_name]
    if missing:
        die("no chain(s) %s; this file has %s" % (missing, sorted(by_name)))

    # the joints to touch, by path_id, and what they carry now
    want = {}
    for cn in chains:
        jps = by_name[cn][1]
        if frm >= len(jps):
            die("--from-index %d selects nothing on %s, which has %d joint(s)"
                % (frm, cn, len(jps)))
        for i, jp in enumerate(jps):
            if i < frm:
                continue
            rec = joints.get(jp)
            if rec is None:
                die("a joint of %s is not readable; refusing to write against an incomplete "
                    "measurement" % cn)
            want[jp] = (cn, i, rec[1], rec[2], rec[3], rec[4])
    if not want:
        die("no joint selected")

    rads = sorted({round(v[5], 5) for v in want.values()})
    gravs = sorted({round(v[4], 5) for v in want.values()})
    print("%d chain(s), %d joint(s) selected from index %d" % (len(chains), len(want), frm))
    print("they currently carry jointRadius %s, gravityPower %s"
          % (["%.1f mm" % (r * 1000) for r in rads], ["%.2f" % g for g in gravs]))
    if jr is not None:
        print("  jointRadius -> %.1f mm" % (jr * 1000))
    if gp is not None:
        print("  gravityPower -> %.2f" % gp)

    # STATE THE REST-POSE RISK IN THE TOOL'S OWN OUTPUT, because it is the one that was
    # measured to matter: a joint whose radius now reaches a collider it used to clear will
    # be shoved out on frame one.
    if jr is not None:
        import capsule_contains as cc
        shapes = cc.collider_shapes(tf, go_tf, colliders, world)
        risky = []
        for jp, (cn, i, _st, _dr, _gv, oldr) in sorted(want.items(), key=lambda t: t[1][1]):
            rec = joints[jp]
            tp = go_tf.get(rec[0])
            if tp is None:
                continue
            wp, _q, ws = world(tp)
            clear = min((cc.seg_dist(wp, v[2], v[3]) - v[1] for v in shapes.values()),
                        default=9.9)
            if clear < jr * ws[0]:
                risky.append((cn, i, clear, jr * ws[0]))
        print()
        if risky:
            print("%d selected joint(s) would now REACH a collider they currently clear:"
                  % len(risky))
            for cn, i, clear, newr in risky[:10]:
                print("    %-26s [%2d] clears %6.1f mm, new radius %.1f mm"
                      % (cn[:26], i, clear * 1000, newr * 1000))
            print("  Each is a frame-one shove. This is the mechanism that made the capsule")
            print("  relax 3.07x worse; raise --from-index or lower the radius.")
        else:
            print("no selected joint reaches a collider it currently clears, so no joint is")
            print("displaced at rest -- which is the condition the capsule relax violated.")

    if not write:
        print()
        print("DRY RUN -- nothing written. Re-run with --write to apply.")
        return 0

    if not os.path.isdir(BACKUP_DIR):
        die("the backup directory %s does not exist" % BACKUP_DIR)
    src = open(path, "rb").read()
    src_md5 = hashlib.md5(src).hexdigest()
    found = None
    for f in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp) and os.path.getsize(fp) == len(src):
            if hashlib.md5(open(fp, "rb").read()).hexdigest() == src_md5:
                found = f
                break
    if found:
        print("backup present: %s" % found)
    else:
        dest = os.path.join(BACKUP_DIR, "%s.%s.bak" % (os.path.basename(path), src_md5[:8]))
        shutil.copy2(path, dest)
        print("backed up to %s" % dest)

    env = UnityPy.load(path)
    touched = 0
    for o in env.objects:
        if o.type.name != "MonoBehaviour" or o.path_id not in want:
            continue
        t = o.read_typetree()
        if jr is not None:
            t["m_jointRadius"] = jr
        if gp is not None:
            t["m_gravityPower"] = gp
        o.save_typetree(t)
        touched += 1
    if touched != len(want):
        die("expected to touch %d joint(s), touched %d -- the selection and the file disagree"
            % (len(want), touched))

    data = env.file.save(packer="original")
    if not data.startswith(b"UnityFS"):
        die("the written bytes do not start with 'UnityFS', so this is no longer an "
            "AssetBundle and the game cannot load it. Nothing written.")
    if not (0.5 * len(src) <= len(data) <= 2.0 * len(src)):
        die("the written bytes are %d against %d in. Setting floats cannot do that. "
            "Nothing written." % (len(data), len(src)))
    print("container: UnityFS kept, %d bytes against %d in (%+d)"
          % (len(data), len(src), len(data) - len(src)))

    # VERIFY BOTH DIRECTIONS. A check that only confirms the selected joints changed cannot
    # see a write that also moved one it was not asked to.
    env2 = UnityPy.load(_io.BytesIO(data))
    problems, seen = [], 0
    for o in env2.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn != "VRM10SpringBoneJoint":
            continue
        t = o.read_typetree()
        if o.path_id in want:
            seen += 1
            if jr is not None and abs(t.get("m_jointRadius", -1) - jr) > 1e-7:
                problems.append("%s[%d] radius is %s, expected %s"
                                % (want[o.path_id][0], want[o.path_id][1],
                                   t.get("m_jointRadius"), jr))
            if gp is not None and abs(t.get("m_gravityPower", -1) - gp) > 1e-7:
                problems.append("%s[%d] gravity is %s, expected %s"
                                % (want[o.path_id][0], want[o.path_id][1],
                                   t.get("m_gravityPower"), gp))
        else:
            old = joints.get(o.path_id)
            if old is None:
                continue
            if abs(t.get("m_jointRadius", 0.0) - old[4]) > 1e-7:
                problems.append("an UNSELECTED joint's radius moved to %s from %s"
                                % (t.get("m_jointRadius"), old[4]))
            if abs(t.get("m_gravityPower", 0.0) - old[3]) > 1e-7:
                problems.append("an UNSELECTED joint's gravity moved to %s from %s"
                                % (t.get("m_gravityPower"), old[3]))
    if seen != len(want):
        problems.append("read back %d of the %d joints that were set" % (seen, len(want)))
    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems[:12]))

    open(path, "wb").write(data)
    print("WRITTEN. %d joint(s) on %d chain(s) from index %d." % (touched, len(chains), frm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
