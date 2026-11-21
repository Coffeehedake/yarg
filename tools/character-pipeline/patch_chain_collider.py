# -*- coding: utf-8 -*-
"""Give one spring chain a collider group of its OWN, with a radius of its own.

    python patch_chain_collider.py <file.yargchar> --chain Tie --radius 86.6
                                   [--on "Bip01 Spine"] [--group TieChest] [--write]

WHY THIS EXISTS. A chain that shares a collider group is stuck with that group's radii. Miku's
necktie is the case: all three of its bones start INSIDE the `Body` group's spine capsule
(-44.4, -30.5, -7.4 mm), so attaching `Body` would have the solver shove the knot ~44 mm forward
on frame one, before anything moved -- reproducing a "tie sticking straight out" fault fixed the
same morning. The recorded decision was to attach nothing, and the reason given for not simply
shrinking the capsule was that *the twintail chains share it*.

That rules out shrinking the SHARED capsule. It does not rule out a second one. A chain
references a list of groups, a group references a list of colliders, and nothing says two groups
may not sit on the same bone. So this clones the capsule the chain is stuck inside, gives the
clone a smaller radius on the same axis, puts it in a new group, and points only that chain at
it. The shared group is not touched, so every chain that relies on it is unaffected -- which is
asserted after the write, not assumed.

DERIVE THE RADIUS, DO NOT PICK ONE. `tie_collider_fit.py` computes the feasible interval from
the character's own geometry: above the body surface beside each joint, below each joint's rest
distance, both expressed as a capsule radius after subtracting the joint's own radius. For
Miku's tie that interval is [85.5, 87.8] mm and the midpoint is 86.6. **Both bounds are on the
same quantity and the joint radius belongs in both** -- the solver holds the joint CENTRE at
`r_capsule + r_joint`, and the first version of that tool compared a capsule radius against a
surface distance, dropped the 20 mm joint radius, and reported a feasible fix as impossible.

A COMPONENT IS A TWO-WAY LINK. The MonoBehaviour names its GameObject in `m_GameObject` and the
GameObject must list the component back in `m_Component`. Writing only the first makes an
orphan: deserialised, present, reachable through a direct pointer, and a component of nothing.
Miku shipped exactly that way on 2026-11-15 -- 21 orphaned joints, twintails that did not move,
and every check agreeing they would, because following the Springs array's own pointers is the
one direction that works whether or not the other does. Both sides are written here and both are
verified by walking the GameObject's component list, which is the direction that can fail.

NOTHING IS WRITTEN WITHOUT `--write`. The default is a dry run that prints what it would do.
Back the bundle up first; `--write` refuses unless a backup of the same bytes exists.
"""
import copy
import hashlib
import math
import os
import shutil
import sys

import cloth_collide_installed as cci
import UnityPy

BACKUP_DIR = r"C:\dev\YARG - Open Source Contributions\character-backups"


def die(msg):
    print("REFUSED: %s" % msg)
    sys.exit(1)


def seg_dist(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    L = sum(x * x for x in ab)
    t = 0.0 if L <= 0 else max(0.0, min(1.0, sum(ap[i] * ab[i] for i in range(3)) / L))
    c = [a[i] + ab[i] * t for i in range(3)]
    return math.sqrt(sum((p[i] - c[i]) ** 2 for i in range(3)))


def parse(argv):
    k = {"chain": None, "radius": None, "on": None, "group": None, "write": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--write":
            k["write"] = True
        elif a.startswith("--") and a[2:] in k and i + 1 < len(argv):
            key = a[2:]
            i += 1
            k[key] = float(argv[i]) if key == "radius" else argv[i]
        else:
            die("unrecognised argument %r" % a)
        i += 1
    return k


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    k = parse(sys.argv[2:])
    if not k["chain"] or k["radius"] is None:
        die("--chain and --radius are both required (derive the radius with "
            "tie_collider_fit.py; do not pick one)")
    want_r = k["radius"] / 1000.0

    # ---------------------------------------------------------------- measure first
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    chain = next((s for s in springs if s[0] == k["chain"]), None)
    if chain is None:
        die("no chain called %r; this file has %s"
            % (k["chain"], sorted(s[0] for s in springs)))
    _nm, joint_pids, existing_groups = chain
    if existing_groups:
        die("chain %r ALREADY has %d collider group(s). This tool adds a group to a chain "
            "that has none; changing an existing attachment is a different decision and "
            "should be made deliberately." % (k["chain"], len(existing_groups)))

    jrows = []
    for jp in joint_pids:
        rec = joints.get(jp)
        gid, jr = rec[0], rec[4]
        tp = go_tf.get(gid)
        wp, _wq, ws = world(tp)
        jrows.append((tf.get(tp, {}).get("name") or "?", wp, jr * ws[0]))

    # Resolve every collider into world space, exactly as cloth_collide_installed does.
    shapes = {}
    for cp, t in colliders.items():
        cgid = (t.get("m_GameObject") or {}).get("m_PathID")
        ctp = go_tf.get(cgid)
        if ctp is None:
            continue
        wp, wq, ws = world(ctp)

        def to_world(v, wq=wq, ws=ws, wp=wp):
            sc = (v.get("x", 0.0) * ws[0], v.get("y", 0.0) * ws[1], v.get("z", 0.0) * ws[2])
            r = cci.qrot(wq, sc)
            return (wp[0] + r[0], wp[1] + r[1], wp[2] + r[2])

        a = to_world(t.get("Offset") or {})
        b = to_world(t.get("Tail") or {}) if t.get("ColliderType", 0) == 1 else a
        shapes[cp] = (tf.get(ctp, {}).get("name") or "?", cgid, ctp,
                      float(t.get("Radius", 0.0)) * ws[0], a, b, ws[0])

    # Which capsule to clone: the one the chain is deepest inside, unless named.
    if k["on"]:
        cands = [cp for cp, s in shapes.items() if s[0] == k["on"]]
        if not cands:
            die("no collider on a bone called %r; this file has colliders on %s"
                % (k["on"], sorted(set(s[0] for s in shapes.values()))))
        donor_cp = cands[0]
    else:
        donor_cp = min(shapes,
                       key=lambda cp: min(seg_dist(wp, shapes[cp][4], shapes[cp][5])
                                          - shapes[cp][3] - jr for _b, wp, jr in jrows))
    dname, dgid, dtp, dr, da, db, dws = shapes[donor_cp]

    print("chain %r: %d joints, currently 0 collider groups" % (k["chain"], len(jrows)))
    print("cloning the capsule on %r (world radius %.1f mm) at %.1f mm"
          % (dname, dr * 1000, want_r * 1000))
    print()
    print("%-20s %12s %12s %12s" % ("joint", "rest d(mm)", "new clear", "standoff"))
    worst = None
    for bn, wp, jr in jrows:
        d = seg_dist(wp, da, db)
        clear = d - want_r - jr
        print("%-20s %12.1f %12.1f %12.1f"
              % (bn[:20], d * 1000, clear * 1000, (want_r + jr) * 1000))
        worst = clear if worst is None else min(worst, clear)
    print()
    if worst < 0:
        die("at %.1f mm a joint would START %.1f mm INSIDE the new capsule. The solver's "
            "first act is to push it out, so this is a displacement on frame one and not a "
            "collision that gets handled. Derive the radius with tie_collider_fit.py."
            % (want_r * 1000, -worst * 1000))
    print("every joint clears the new capsule at rest, the tightest by %.2f mm." % (worst * 1000))

    if not k["write"]:
        print()
        print("DRY RUN -- nothing written. Re-run with --write to apply.")
        return 0

    # ------------------------------------------------------------------ backup gate
    if not os.path.isdir(BACKUP_DIR):
        die("the backup directory %s does not exist" % BACKUP_DIR)
    src_bytes = open(path, "rb").read()
    src_md5 = hashlib.md5(src_bytes).hexdigest()
    have = False
    for f in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fp) and os.path.getsize(fp) == len(src_bytes):
            if hashlib.md5(open(fp, "rb").read()).hexdigest() == src_md5:
                have = True
                print("backup present: %s" % f)
                break
    if not have:
        dest = os.path.join(BACKUP_DIR, "%s.%s.bak"
                            % (os.path.basename(path), src_md5[:8]))
        shutil.copy2(path, dest)
        print("backed up to %s" % dest)

    # ------------------------------------------------------------------ write
    env = UnityPy.load(path)
    col_obj = group_obj = inst_obj = None
    inst_tree = None
    go_objs = {}
    for o in env.objects:
        if o.type.name == "GameObject":
            go_objs[o.path_id] = o
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            continue
        if cn == "VRM10SpringBoneCollider" and o.path_id == donor_cp:
            col_obj = o
        elif cn == "VRM10SpringBoneColliderGroup" and group_obj is None:
            group_obj = o
        elif cn == "Vrm10Instance":
            inst_obj = o
            inst_tree = o.read_typetree()
    if col_obj is None or group_obj is None or inst_obj is None:
        die("this file does not carry a collider, a collider group and a Vrm10Instance to "
            "copy from -- nothing is invented here, so there is nothing to do")

    # The path_id space belongs to the SERIALIZED file, which is reached through an object
    # that lives in it. `env.file` is the BUNDLE and has no `.objects` at all.
    af = col_obj.assets_file
    used = set(af.objects.keys())
    nxt = max(used) + 1

    # 1. the collider: a copy of the donor with one field changed.
    ct = copy.deepcopy(col_obj.read_typetree())
    ct["Radius"] = want_r / (dws if dws else 1.0)
    new_col = copy.copy(col_obj)
    new_col.path_id = nxt
    new_col.save_typetree(ct)
    af.objects[nxt] = new_col
    col_id = nxt
    nxt += 1

    # 2. the group: a copy of an existing one, naming only the new collider.
    gt = copy.deepcopy(group_obj.read_typetree())
    gt["Name"] = k["group"] or ("%sOwn" % k["chain"])
    gt["Colliders"] = [{"m_FileID": 0, "m_PathID": col_id}]
    gt["m_GameObject"] = {"m_FileID": 0, "m_PathID": dgid}
    new_grp = copy.copy(group_obj)
    new_grp.path_id = nxt
    new_grp.save_typetree(gt)
    af.objects[nxt] = new_grp
    grp_id = nxt

    # 3. BOTH SIDES OF THE LINK. The GameObject must list them back, or they are orphans
    #    that deserialise fine and are components of nothing.
    host = go_objs.get(dgid)
    if host is None:
        die("the bone GameObject %d that carries the donor collider is not in this file"
            % dgid)
    ht = host.read_typetree()
    comps = ht.get("m_Component") or []
    comps.append({"component": {"m_FileID": 0, "m_PathID": col_id}})
    comps.append({"component": {"m_FileID": 0, "m_PathID": grp_id}})
    ht["m_Component"] = comps
    host.save_typetree(ht)

    # 4. point the chain, and ONLY that chain, at the new group.
    sb = inst_tree["SpringBone"]
    touched = 0
    for s in sb["Springs"]:
        if s.get("Name") == k["chain"]:
            s["ColliderGroups"] = [{"m_FileID": 0, "m_PathID": grp_id}]
            touched += 1
    if touched != 1:
        die("expected exactly one chain called %r, found %d" % (k["chain"], touched))
    inst_obj.save_typetree(inst_tree)

    data = af.save(packer="original")

    # ------------------------------------------------------- verify BEFORE writing out
    # On the bytes in hand, because a file written and THEN found wrong is a file somebody
    # may already have installed.
    import io
    env2 = UnityPy.load(io.BytesIO(data))
    seen_col = seen_grp = False
    attached = False
    chains_after = {}
    for o in env2.objects:
        if o.type.name == "GameObject":
            t = o.read_typetree()
            if o.path_id == dgid:
                ids = [c["component"]["m_PathID"] for c in (t.get("m_Component") or [])]
                attached = col_id in ids and grp_id in ids
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            continue
        if o.path_id == col_id and cn == "VRM10SpringBoneCollider":
            seen_col = True
        if o.path_id == grp_id and cn == "VRM10SpringBoneColliderGroup":
            seen_grp = True
        if cn == "Vrm10Instance":
            for s in o.read_typetree()["SpringBone"]["Springs"]:
                chains_after[s.get("Name")] = [g["m_PathID"]
                                               for g in (s.get("ColliderGroups") or [])]

    problems = []
    if not seen_col:
        problems.append("the new collider is not in the written file")
    if not seen_grp:
        problems.append("the new group is not in the written file")
    if not attached:
        problems.append("the bone GameObject does not list them as components -- ORPHANS")
    if chains_after.get(k["chain"]) != [grp_id]:
        problems.append("chain %r does not reference the new group" % k["chain"])
    for nm, gs in chains_after.items():
        if nm == k["chain"]:
            continue
        before = next((s[2] for s in springs if s[0] == nm), None)
        if before is not None and sorted(gs) != sorted(before):
            problems.append("chain %r had its groups CHANGED (%s -> %s)" % (nm, before, gs))
    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems))

    with open(path, "wb") as fh:
        fh.write(data)
    print()
    print("WRITTEN. collider %d (r %.1f mm) and group %r %d on %r; chain %r now references it."
          % (col_id, want_r * 1000, gt["Name"], grp_id, dname, k["chain"]))
    print("%d other chain(s) verified unchanged." % (len(chains_after) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
