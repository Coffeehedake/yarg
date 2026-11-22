# -*- coding: utf-8 -*-
"""Set a VRM10 spring joint's floats -- radius, gravity, stiffness, drag -- on chosen chains.

    python set_joint_params.py <file.yargchar> --chain NAME [--chain NAME ...]
           [--from-index N] [--to-index N] [--joint-radius MM] [--gravity P]
           [--stiffness S] [--drag D] [--write]

WHY. A spring joint carries four floats and this roster ships three of them untouched from the
converter's defaults. Each is a one-line experiment against a fault that otherwise costs a cape
re-weight, so the tool exists to make trying one cheap and reversible rather than to recommend
any particular value.

    m_jointRadius     how close a joint must come to a collider to be pushed off it
    m_gravityPower    the restoring force; 0.00 across this roster, so a flung cape stays flung
    m_stiffnessForce  the pull back toward the authored rest direction
    m_dragForce       velocity damping

WHAT COLLISION ACTUALLY DOES, because it bounds every radius experiment: it moves a JOINT, never
the sheet between two joints, and the test is `dist(joint, collider) < colliderR + jointR` -- so
collider radius and joint radius are additive, and a joint that starts inside a collider is
shoved out on frame one and the spring overshoots. Fattening the 41 fitted body capsules was
measured on 2026-11-21 to make penetration 2.28x worse by exactly that route, with garment travel
rising 1115 -> 1754 mm. That is why `--from-index` exists and defaults to 3: the joints near the
attachment lie on the skin. The rest-pose gate below names every joint whose new radius would
reach a collider it currently clears, and it only runs for `--joint-radius`, since the other
three floats cannot displace anything at rest.

TWO CLAIMS THIS DOCSTRING USED TO MAKE, BOTH WITHDRAWN 2026-11-22.

It carried a table of penetration depth against distance-to-nearest-joint, showing a sharp
ceiling at 40 mm, and inferred from it that "the protected zone is about twice the joint radius".
Both are gone:

  * **The table was measured over 38% of the animation.** The probe ran 240 frames at 60 fps
    against a 633-frame clip. At full coverage the band maxima are flat -- 142.6 mm for vertices
    within 20 mm of a joint -- so there is no ceiling and no step. The 32-chain, 231-bone job
    that table sized was an artefact of the window.
  * **The 2x-radius rule was then tested directly and is false.** Raising the radius from 20 mm
    to 65 mm on 55 joints moved the depth-weighted total by 1.6% and left the peak identical.

What remains true, and is a geometric fact rather than a measurement of this tool: adjacent cape
chains are 236-337 mm apart, so a limb can pass between two chains without ever coming within
reach of a joint. Closing that needs chains, not floats.

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
    # --to-index bounds the range at the far end. Without it every float on this roster has only
    # ever been set across joints 1..10 at once, so "stiffness" has always meant the whole cape
    # -- and the arm contact lives in joints 1-3, which have never been touched alone.
    to = int(arg("--to-index", "1000000"))
    if to < frm:
        die("--to-index %d is before --from-index %d, which selects nothing" % (to, frm))
    jr = arg("--joint-radius")
    gp = arg("--gravity")
    st = arg("--stiffness")
    dg = arg("--drag")
    write = "--write" in sys.argv
    if jr is None and gp is None and st is None and dg is None:
        die("nothing asked for: pass --joint-radius, --gravity, --stiffness and/or --drag")
    jr = None if jr is None else float(jr) / 1000.0
    gp = None if gp is None else float(gp)
    st = None if st is None else float(st)
    dg = None if dg is None else float(dg)

    # Refuse the obviously wrong rather than write it and measure noise. UniVRM clamps drag to
    # 0..1 and treats stiffness as an unbounded force, but every joint on this roster carries
    # 0.0-1.0 for both, so a value far outside that is a typo (0.9 typed as 9) and not an
    # experiment somebody meant.
    for nm, v, hi in (("--stiffness", st, 4.0), ("--drag", dg, 1.0)):
        if v is None:
            continue
        if v < 0.0 or v > hi:
            die("%s %g is outside 0..%g; on this roster both floats sit in 0.0-1.0, so this "
                "is a typo rather than an experiment" % (nm, v, hi))

    # WHAT EACH FLOAT CAN AND CANNOT REACH, said once so a null result is not read as a fix
    # that did not take. jointRadius and gravityPower were both swept on Batman's cape:
    # gravity 0.30 cut the depth-weighted total 37% and the peak 63%, and is a measured
    # optimum -- 0.20, 0.25, 0.40, 0.50 and 0.70 are all worse at the gauntlets. Radius did
    # nothing. Stiffness and drag act on how far a joint travels from its rest direction, so
    # they can only help where the REST pose is already clear of the body; where a limb sweeps
    # through the sheet between two joints, no float reaches it.
    sets = [(k, v) for k, v in (("m_jointRadius", jr), ("m_gravityPower", gp),
                                ("m_stiffnessForce", st), ("m_dragForce", dg))
            if v is not None]
    OLD_IX = {"m_stiffnessForce": 1, "m_dragForce": 2, "m_gravityPower": 3, "m_jointRadius": 4}

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
            if i < frm or i > to:
                continue
            rec = joints.get(jp)
            if rec is None:
                die("a joint of %s is not readable; refusing to write against an incomplete "
                    "measurement" % cn)
            want[jp] = (cn, i, rec[1], rec[2], rec[3], rec[4])
    if not want:
        die("no joint selected")

    rng = ("from index %d" % frm) if to >= 1000000 else ("indices %d..%d" % (frm, to))
    print("%d chain(s), %d joint(s) selected, %s" % (len(chains), len(want), rng))
    print("they currently carry:")
    for nm, ix, fmt in (("jointRadius", 5, "%.1f mm"), ("gravityPower", 4, "%.2f"),
                        ("stiffnessForce", 2, "%.3f"), ("dragForce", 3, "%.3f")):
        vals = sorted({round(v[ix], 5) for v in want.values()})
        shown = [fmt % (v * 1000 if nm == "jointRadius" else v) for v in vals]
        print("    %-15s %s" % (nm, ", ".join(shown)))
    print("asked for:")
    for k, v in sets:
        print("    %-15s -> %s" % (k[2:], "%.1f mm" % (v * 1000) if k == "m_jointRadius"
                                   else "%.3f" % v))

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
        for k, v in sets:
            t[k] = v
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
            for k, v in sets:
                if abs(t.get(k, -1.0) - v) > 1e-7:
                    problems.append("%s[%d] %s is %s, expected %s"
                                    % (want[o.path_id][0], want[o.path_id][1], k,
                                       t.get(k), v))
            # A joint we DID select must still keep the floats we were not asked to change.
            for k, ix in OLD_IX.items():
                if k in dict(sets):
                    continue
                if abs(t.get(k, 0.0) - joints[o.path_id][ix]) > 1e-7:
                    problems.append("%s[%d] %s moved to %s from %s, and was not asked to"
                                    % (want[o.path_id][0], want[o.path_id][1], k,
                                       t.get(k), joints[o.path_id][ix]))
        else:
            old = joints.get(o.path_id)
            if old is None:
                continue
            # Every float, not just the ones being written: a write that moved an unselected
            # joint's stiffness would have gone unseen while this checked only two of four.
            for k, ix in OLD_IX.items():
                if abs(t.get(k, 0.0) - old[ix]) > 1e-7:
                    problems.append("an UNSELECTED joint's %s moved to %s from %s"
                                    % (k, t.get(k), old[ix]))
    if seen != len(want):
        problems.append("read back %d of the %d joints that were set" % (seen, len(want)))
    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems[:12]))

    open(path, "wb").write(data)
    print("WRITTEN. %d joint(s) on %d chain(s), %s." % (touched, len(chains), rng))
    return 0


if __name__ == "__main__":
    sys.exit(main())
