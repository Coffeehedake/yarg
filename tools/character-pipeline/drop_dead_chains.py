# -*- coding: utf-8 -*-
"""Remove named spring chains from an installed bundle, and refuse to remove a live one.

    python drop_dead_chains.py <file.yargchar> <chain-name> [<chain-name> ...] [--write]

WHY. A spring chain whose bones own no skin weight costs the solver its full per-frame work
and moves nothing. Removing it is free. Removing one that DOES own weight makes a garment go
rigid, and the two are told apart only by measurement -- which is why this tool takes the
measurement itself rather than trusting the names it was handed.

WHAT IT REFUSES, and each of these is a mistake this project has actually made:

  * A chain carrying ANY weight. The bound is `sum w > 0`, not "a small amount", and it is
    computed by `chain_weight_installed.per_chain` -- the same instrument whose output was
    read before deciding, not a second implementation of it that could differ.
  * A chain whose bones did not JOIN to the skin. An unmatched bone measures nothing, so its
    0.0 is the join failing and not a dead chain.
  * A name that matches no chain, or matches more than one.
  * Dropping EVERY chain, or every chain that carries weight -- that is a typo, not a request.
  * A bundle where no skinned mesh could be read at all, since then every weight is 0.0.

WHAT IT DOES NOT DO. The `VRM10SpringBoneJoint` components themselves are LEFT IN THE FILE,
inert. The solver reaches a joint only through `Vrm10Instance.SpringBone.Springs`, so an
unreferenced component is never stepped; deleting objects out of an AssetBundle risks every
other PPtr in it for no gain. The tool therefore reports what it orphaned, by count, and
CHECKS THE OTHER DIRECTION: that nothing else in the file still points at those joints. A
patch that only confirms its own edit cannot see a reference it left behind -- 21 orphaned
components once passed every test here.

Both the drop and the keep are verified after the write, from the written bytes: the kept
chains must still have their exact joints, collider groups and all four floats, and the
dropped names must be gone. A chain count alone would miss a write that dropped the right
number of the wrong chains.
"""
import hashlib
import io as _io
import os
import shutil
import sys

import chain_weight_installed as cwi
import cloth_collide_installed as cci
import UnityPy

BACKUP_DIR = r"C:\dev\YARG - Open Source Contributions\character-backups"


def die(msg):
    print("REFUSED: %s" % msg)
    sys.exit(1)


def main():
    argv = [a for a in sys.argv[1:] if a != "--write"]
    write = "--write" in sys.argv
    if len(argv) < 2:
        print(__doc__)
        return 2
    path, names = argv[0], argv[1:]
    if not os.path.isfile(path):
        die("%s does not exist" % path)

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    env = UnityPy.load(path)
    gname = cwi.gameobject_names(env)
    wsum, wdom, walked, verts = cwi.bone_weights(env)
    if not walked or not verts:
        die("no skinned mesh was read (%d meshes, %d vertices), so every chain would measure "
            "0.0 weight and look droppable" % (walked, verts))

    rows, named, matched = cwi.per_chain(springs, joints, go_tf, gname, wsum, wdom)
    if named and matched == 0:
        die("not one joint bone joined to the skin, so every 0.0 is the join and not a "
            "dead chain")
    by_name = {}
    for r in rows:
        by_name.setdefault(r[0], []).append(r)

    print("%s -- %d chain(s), %d mesh(es), %d vertices, %d bone(s) named, %d matched"
          % (os.path.basename(path), len(springs), walked, verts, named, matched))

    live = [r for r in rows if r[2] > 0]
    if not live:
        die("no chain on this character carries any weight, which is an instrument fault")

    want = []
    for n in names:
        hit = by_name.get(n)
        if not hit:
            die("no chain is called %r. The chains are: %s"
                % (n, ", ".join(sorted(r[0] for r in rows))))
        if len(hit) > 1:
            die("%d chains are called %r, so the name does not identify one" % (len(hit), n))
        r = hit[0]
        if r[4]:
            die("%s has %d bone(s) that did not join to the skin, so its 0.0 is unmeasured"
                % (n, r[4]))
        if r[2] > 0:
            die("%s carries %.2f of skin weight over %d dominant vertices. Dropping it would "
                "make that geometry rigid." % (n, r[2], r[3]))
        want.append(r)

    # A WEIGHTLESS BONE CAN STILL CARRY A WEIGHTED CHILD. The solver writes a joint's
    # transform, and every descendant inherits it -- so a chain that deforms nothing itself
    # can still be the thing that MOVES something, and its own `sum w` of 0.00 is blind to
    # that. Measure the descendants before believing "no visual change".
    kids = {}
    for pid, rec in tf.items():
        kids.setdefault(rec.get("f") or 0, []).append(pid)

    def descend(tid, out):
        for k in kids.get(tid, []):
            out.append(k)
            descend(k, out)

    # THE WALK NEEDS ITS OWN CONTROL. Every chain on Batman reports zero weighted
    # descendants, and a broken father->child map reports exactly the same zero. So descend
    # from the root first: it must reach the skin, or the zeros below are the instrument.
    roots = [p for p, rec in tf.items() if not rec.get("f") or rec["f"] not in tf]
    reach = []
    for r in roots:
        descend(r, reach)
    reach_w = sum(1 for k in reach if wsum.get(k, 0.0) > 0)
    if reach_w == 0:
        die("descending from %d root transform(s) reached %d transforms and NOT ONE weighted "
            "bone, so the hierarchy walk is broken and every 'no weighted descendant' below "
            "would be that bug" % (len(roots), len(reach)))
    print("hierarchy walk control: %d root(s) reach %d transforms, %d of them weighted"
          % (len(roots), len(reach), reach_w))

    inherit = []
    for name, jps, _cg in springs:
        if name not in set(names):
            continue
        for jp in jps:
            rec = joints.get(jp)
            tid = go_tf.get(rec[0]) if rec else None
            if tid is None:
                continue
            sub = []
            descend(tid, sub)
            own = {go_tf.get(joints[j][0]) for j in jps if j in joints}
            for k in sub:
                if k in own:
                    continue                      # its own chain, going too
                w = wsum.get(k, 0.0)
                if w > 0:
                    inherit.append((name, tf.get(tid, {}).get("name") or "?",
                                    tf.get(k, {}).get("name") or "?", w))
    if inherit:
        print()
        print("WEIGHTED GEOMETRY HANGS BELOW A CHAIN BEING DROPPED -- %d case(s):" % len(inherit))
        for ch, par, kid, w in inherit[:12]:
            print("  %s: %s -> %s carries %.2f" % (ch, par, kid, w))
        die("those bones inherit motion from a chain this would stop, so 'it deforms nothing' "
            "is not the same as 'nothing moves'. Not a free drop.")
    print("no weighted bone hangs below any chain being dropped (checked every descendant "
          "outside the dropped chains themselves)")

    if len(want) >= len(rows):
        die("that is every chain on the character")

    keep = [r for r in rows if r[0] not in set(names)]
    print()
    print("DROPPING %d chain(s), %d joint(s):" % (len(want), sum(r[1] for r in want)))
    for r in want:
        print("  %-22s %2d joints, sum w %.2f, dom v %d" % (r[0], r[1], r[2], r[3]))
    print("KEEPING %d chain(s), %d joint(s):" % (len(keep), sum(r[1] for r in keep)))
    for r in keep:
        print("  %-22s %2d joints, sum w %.2f, dom v %d" % (r[0], r[1], r[2], r[3]))
    tot_j = sum(r[1] for r in rows)
    print()
    print("spring joints stepped per frame: %d -> %d (%.1f%% less)"
          % (tot_j, sum(r[1] for r in keep),
             100.0 * sum(r[1] for r in want) / max(1, tot_j)))

    # What the dropped chains referenced, so the orphan count is stated rather than implied.
    dropped_jps = set()
    for name, jps, _cg in springs:
        if name in set(names):
            dropped_jps.update(jps)
    print("joint components left in the file as inert data: %d" % len(dropped_jps))

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
        dest = os.path.join(BACKUP_DIR,
                            "%s.%s.bak" % (os.path.basename(path), src_md5[:8]))
        shutil.copy2(path, dest)
        print("backed up to %s" % dest)

    drop = set(names)
    touched = 0
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn != "Vrm10Instance":
            continue
        t = o.read_typetree()
        sb = t.get("SpringBone") or {}
        before = sb.get("Springs") or []
        after = [s for s in before if s.get("Name") not in drop]
        if len(before) - len(after) != len(drop):
            die("the Springs list has %d entries and %d would remain; expected to remove %d"
                % (len(before), len(after), len(drop)))
        sb["Springs"] = after
        t["SpringBone"] = sb
        o.save_typetree(t)
        touched += 1
    if touched != 1:
        die("expected exactly one Vrm10Instance to edit, found %d" % touched)

    data = env.file.save(packer="original")
    if not data.startswith(b"UnityFS"):
        die("the written bytes do not start with 'UnityFS', so this is no longer an "
            "AssetBundle and the game cannot load it. Nothing written.")
    if not (0.5 * len(src) <= len(data) <= 2.0 * len(src)):
        die("the written bytes are %d against %d in. Removing list entries cannot do that. "
            "Nothing written." % (len(data), len(src)))
    print("container: UnityFS kept, %d bytes against %d in (%+d)"
          % (len(data), len(src), len(data) - len(src)))

    # VERIFY FROM THE WRITTEN BYTES, BOTH DIRECTIONS.
    env2 = UnityPy.load(_io.BytesIO(data))
    springs2 = []
    for o in env2.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn == "Vrm10Instance":
            sb = (o.read_typetree().get("SpringBone") or {})
            for s in sb.get("Springs") or []:
                springs2.append((s.get("Name", "?"),
                                 [j["m_PathID"] for j in s.get("Joints") or []],
                                 [c["m_PathID"]
                                  for c in s.get("ColliderGroups") or []]))
    problems = []
    got = {s[0] for s in springs2}
    for n in names:
        if n in got:
            problems.append("%s is still in the Springs list" % n)
    was = {s[0]: (s[1], s[2]) for s in springs}
    for name, jps, cgs in springs2:
        if name not in was:
            problems.append("%s appeared and was not there before" % name)
            continue
        if jps != was[name][0]:
            problems.append("%s kept %d joints, had %d" % (name, len(jps),
                                                           len(was[name][0])))
        if cgs != was[name][1]:
            problems.append("%s collider groups changed" % name)
    for r in keep:
        if r[0] not in got:
            problems.append("%s was to be KEPT and is gone" % r[0])

    # The joints of the chains we kept must still carry the same four floats. A drop that
    # also moved a float would otherwise land unseen, and gravity 0.70 was installed today.
    kept_jps = {jp for _n, jps, _c in springs2 for jp in jps}
    seen = 0
    for o in env2.objects:
        if o.type.name != "MonoBehaviour" or o.path_id not in kept_jps:
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn != "VRM10SpringBoneJoint":
            continue
        seen += 1
        t = o.read_typetree()
        old = joints.get(o.path_id)
        if old is None:
            problems.append("a kept joint %d was not in the original" % o.path_id)
            continue
        for k, ix in (("m_stiffnessForce", 1), ("m_dragForce", 2),
                      ("m_gravityPower", 3), ("m_jointRadius", 4)):
            if abs(t.get(k, 0.0) - old[ix]) > 1e-7:
                problems.append("a kept joint's %s moved to %s from %s"
                                % (k, t.get(k), old[ix]))
    if seen != len(kept_jps):
        problems.append("read back %d of %d kept joints" % (seen, len(kept_jps)))

    # THE OTHER DIRECTION: does anything still point at a dropped joint?
    still = 0
    for o in env2.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception:                                            # noqa: BLE001
            continue

        def refs(v):
            n = 0
            if isinstance(v, dict):
                if "m_PathID" in v and v.get("m_PathID") in dropped_jps:
                    n += 1
                for x in v.values():
                    n += refs(x)
            elif isinstance(v, list):
                for x in v:
                    n += refs(x)
            return n
        still += refs(t)
    if still:
        problems.append("%d reference(s) to a dropped joint remain in some MonoBehaviour"
                        % still)

    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems[:12]))

    open(path, "wb").write(data)
    print("verified: %d chain(s) remain, %d kept joints unchanged on all four floats, "
          "0 references to the %d orphaned joints"
          % (len(springs2), seen, len(dropped_jps)))
    print("WRITTEN. dropped %s." % ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
