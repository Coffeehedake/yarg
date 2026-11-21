# -*- coding: utf-8 -*-
"""Write a NEW collider capsule at a given place into an installed bundle, and prove it landed.

    python place_collider.py <file.yargchar> --host BONE --radius MM \\
           --offset x,y,z --tail x,y,z --chain NAME [--chain NAME ...] \\
           [--group NAME] [--append] [--write]

Derive the arguments with `fit_body_capsule.py`, which prints them in exactly this form. Do not
pick a radius or a position by hand: the two bounds are 2-20 mm apart on every case measured so
far, and a number chosen by eye lands outside them.

WHY THIS EXISTS, and what it does that `patch_chain_collider.py` does not. That tool CLONES an
existing collider and changes its radius, which covers the case where a capsule is already in
the right place and only the wrong size -- Miku's necktie, where her spine capsule was 132.2 mm
and wanted 86.6. It cannot help where the problem is WHERE the capsule is. Jessica Rabbit's
`spine` collider runs up her back, 250 mm behind her front dress panel, so no radius about it
describes her hips; Batman's cape is held off a capsule on his pelvis axis. Both reports needed
a collider somewhere a bone did not already have one.

PLACING ONE NEEDS NO NEW GameObject, which is the fact this tool rests on. `Offset` and `Tail`
are stored in the collider's host BONE's frame, so a capsule is positioned by choosing a bone
and writing two vectors in that bone's coordinates. The bone supplies the frame; nothing has to
be created, parented or added to the transform hierarchy, and the one structure that has to be
written on both sides is the component link.

WHAT IT REFUSES, because each of these has cost this project a bundle or a day:

  * a joint that would START inside the new capsule. The solver's first act is to push a joint
    out to the surface, so that is a displacement on frame one and not a collision that gets
    handled -- it is how a necktie ends up sticking straight out. Refused unless the
    displacement is under --allow-displace, which must be stated as a number.
  * a chain that already has a collider group, unless --append is given. Replacing an existing
    guard silently removes collision the character already had.
  * a round trip that does not reproduce what was asked. The radius is stored in the bone's
    local scale, so the tool re-reads its own output in WORLD space and compares the capsule it
    actually wrote against the one it was told to write. A local number that round-trips to the
    wrong world radius looks exactly like a correct one in the file.
  * an orphan. A collider and a group that are not listed in their host GameObject's
    `m_Component` deserialise perfectly and are components of nothing -- 21 of them passed
    every check this project had on 2026-11-15. Verified in the direction that can fail.

It backs the file up before writing, into the project's character-backups directory, and it
verifies on the BYTES IN HAND rather than on the file, because a file written and then found
wrong is a file somebody may already have installed.
"""
import copy
import hashlib
import io as _io
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


def vec(s):
    xs = [float(x) for x in s.split(",")]
    if len(xs) != 3:
        die("a vector takes three comma-separated numbers, got %r" % s)
    return tuple(xs)


def parse(argv):
    k = {"host": None, "radius": None, "offset": None, "tail": None, "group": None,
         "chain": [], "write": False, "append": False, "allow-displace": 0.0,
         "expect-world": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--write":
            k["write"] = True
        elif a == "--append":
            k["append"] = True
        elif a == "--chain" and i + 1 < len(argv):
            i += 1
            k["chain"].append(argv[i])
        elif a.startswith("--") and a[2:] in k and i + 1 < len(argv):
            key = a[2:]
            i += 1
            if key in ("radius", "allow-displace"):
                k[key] = float(argv[i])
            elif key in ("offset", "tail"):
                k[key] = vec(argv[i])
            elif key == "expect-world":
                xs = [float(x) for x in argv[i].split(",")]
                if len(xs) != 6:
                    die("--expect-world takes x0,y0,z0,x1,y1,z1 (6 numbers)")
                k[key] = (tuple(xs[:3]), tuple(xs[3:]))
            else:
                k[key] = argv[i]
        else:
            die("unrecognised argument %r" % a)
        i += 1
    return k


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path = sys.argv[1]
    k = parse(sys.argv[2:])
    for need in ("host", "radius", "offset", "tail"):
        if k[need] is None:
            die("--%s is required; fit_body_capsule.py prints all four" % need)
    if not k["chain"]:
        die("--chain is required: a collider nothing references guards nothing")
    want_r_world = k["radius"] / 1000.0
    allow = k["allow-displace"] / 1000.0

    # ------------------------------------------------------------------ measure first
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    by_name = {s[0]: s for s in springs}
    missing = [c for c in k["chain"] if c not in by_name]
    if missing:
        die("no chain(s) %s; this file has %s" % (missing, sorted(by_name)))
    pre_groups = {s[0]: list(s[2]) for s in springs}
    have = [c for c in k["chain"] if pre_groups[c]]
    if have and not k["append"]:
        die("chain(s) %s already reference %s collider group(s). Pass --append to ADD this "
            "one, which keeps the existing guard; without it this tool would replace them "
            "and silently remove collision the character already has."
            % (have, [len(pre_groups[c]) for c in have]))

    # the host bone, and its frame
    htp = next((pid for pid, rec in tf.items() if (rec.get("name") or "") == k["host"]), None)
    if htp is None:
        die("no bone called %r in this file" % k["host"])
    hwp, hwq, hws = world(htp)
    if not (abs(hws[0] - hws[1]) < 1e-6 and abs(hws[1] - hws[2]) < 1e-6):
        die("bone %r has non-uniform world scale %s. A capsule radius is one number, so a "
            "non-uniform scale makes the written shape an ellipsoid and the radius below a "
            "fiction. Pick a different host bone." % (k["host"], hws))

    def to_world(v):
        sc = (v[0] * hws[0], v[1] * hws[1], v[2] * hws[2])
        r = cci.qrot(hwq, sc)
        return (hwp[0] + r[0], hwp[1] + r[1], hwp[2] + r[2])

    A, B = to_world(k["offset"]), to_world(k["tail"])

    # THE CROSS-CHECK THE ROUND TRIP CANNOT DO. The verification at the end of this tool
    # compares what it WROTE against what it was TOLD, so it is blind to arguments that were
    # wrong before they arrived. Measured 2026-11-21: fit_body_capsule.py had its quaternion
    # conjugate negating (w, x, y) instead of (x, y, z), handed over a position 450 mm behind
    # her, and this tool wrote it, verified it, and reported success with four honest
    # clearance numbers for a capsule in the wrong place. --expect-world closes that: the
    # fitter prints the WORLD axis it meant alongside the local vectors, and the two tools
    # are then checked against each other instead of each against itself.
    if k["expect-world"]:
        for lbl, want, got in (("A", k["expect-world"][0], A), ("B", k["expect-world"][1], B)):
            err = math.sqrt(sum((want[i] - got[i]) ** 2 for i in range(3)))
            if err > 0.0005:
                die("end %s lands at %s but was expected at %s, %.1f mm out. The --offset/"
                    "--tail given are not this bone's frame, or not this bundle's pose. "
                    "Nothing written."
                    % (lbl, " ".join("%.4f" % x for x in got),
                       " ".join("%.4f" % x for x in want), err * 1000))
        print("cross-check: both ends land where the fitter meant them to, within 0.5 mm.")
    else:
        print("NOTE: no --expect-world given, so nothing here can tell whether --offset and")
        print("--tail name the position you intended. fit_body_capsule.py prints it.")
    print("host bone %r  world scale %.5f" % (k["host"], hws[0]))
    print("new capsule, world: A %s  B %s  r %.1f mm, length %.1f mm"
          % (" ".join("%.4f" % x for x in A), " ".join("%.4f" % x for x in B),
             want_r_world * 1000,
             math.sqrt(sum((B[i] - A[i]) ** 2 for i in range(3))) * 1000))
    print()

    # every joint of every named chain against the capsule we are about to write
    print("%-24s %-20s %10s %10s" % ("chain", "joint", "rest d", "clearance"))
    print("-" * 68)
    worst, worst_j = None, None
    for cn in k["chain"]:
        for jp in by_name[cn][1]:
            rec = joints.get(jp)
            tp = go_tf.get(rec[0]) if rec else None
            if tp is None:
                die("a joint of %s has no transform -- refusing to write against an "
                    "incomplete measurement" % cn)
            wp, _q, ws = world(tp)
            jr = rec[4] * ws[0]
            d = seg_dist(wp, A, B)
            clear = d - want_r_world - jr
            print("%-24s %-20s %10.1f %10.1f"
                  % (cn[:24], (tf.get(tp, {}).get("name") or "?")[:20], d * 1000,
                     clear * 1000))
            if worst is None or clear < worst:
                worst, worst_j = clear, "%s/%s" % (cn, tf.get(tp, {}).get("name") or "?")
    print()
    if worst < -allow:
        die("%s would START %.1f mm INSIDE the new capsule, and --allow-displace is %.1f mm. "
            "The solver pushes it out on frame one, so this is a visible jump and not a "
            "collision. Re-derive with fit_body_capsule.py, or state the displacement you "
            "accept." % (worst_j, -worst * 1000, allow * 1000))
    if worst < 0:
        print("ACCEPTED DISPLACEMENT: %s starts %.1f mm inside and will be pushed out on "
              "frame one; --allow-displace permitted %.1f mm."
              % (worst_j, -worst * 1000, allow * 1000))
    else:
        print("every joint of every named chain clears it, the tightest by %.2f mm."
              % (worst * 1000))

    if not k["write"]:
        print()
        print("DRY RUN -- nothing written. Re-run with --write to apply.")
        return 0

    # ------------------------------------------------------------------ backup gate
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

    # ------------------------------------------------------------------ write
    env = UnityPy.load(path)
    donor_col = donor_grp = inst_obj = None
    inst_tree = None
    go_objs = {}
    for o in env.objects:
        if o.type.name == "GameObject":
            go_objs[o.path_id] = o
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if cn == "VRM10SpringBoneCollider" and donor_col is None:
            donor_col = o
        elif cn == "VRM10SpringBoneColliderGroup" and donor_grp is None:
            donor_grp = o
        elif cn == "Vrm10Instance":
            inst_obj, inst_tree = o, o.read_typetree()
    if donor_col is None or donor_grp is None or inst_obj is None:
        die("this file has no collider, collider group and Vrm10Instance to copy the SHAPE "
            "of the MonoBehaviour from. Nothing is invented here, so there is nothing to do")

    # the host bone's GameObject, which must exist to carry the components
    hgid = None
    for gid, tpid in go_tf.items():
        if tpid == htp:
            hgid = gid
            break
    if hgid is None or hgid not in go_objs:
        die("bone %r has no GameObject in this file" % k["host"])

    af = donor_col.assets_file
    nxt = max(af.objects.keys()) + 1

    ct = copy.deepcopy(donor_col.read_typetree())
    ct["m_GameObject"] = {"m_FileID": 0, "m_PathID": hgid}
    ct["ColliderType"] = 1                      # 1 = capsule; 0 would ignore Tail entirely
    ct["Radius"] = want_r_world / hws[0]
    ct["Offset"] = {"x": k["offset"][0], "y": k["offset"][1], "z": k["offset"][2]}
    ct["Tail"] = {"x": k["tail"][0], "y": k["tail"][1], "z": k["tail"][2]}
    new_col = copy.copy(donor_col)
    new_col.path_id = nxt
    new_col.save_typetree(ct)
    af.objects[nxt] = new_col
    col_id = nxt
    nxt += 1

    gt = copy.deepcopy(donor_grp.read_typetree())
    gt["Name"] = k["group"] or ("Placed_%s" % k["chain"][0])
    gt["Colliders"] = [{"m_FileID": 0, "m_PathID": col_id}]
    gt["m_GameObject"] = {"m_FileID": 0, "m_PathID": hgid}
    new_grp = copy.copy(donor_grp)
    new_grp.path_id = nxt
    new_grp.save_typetree(gt)
    af.objects[nxt] = new_grp
    grp_id = nxt

    host_go = go_objs[hgid]
    ht = host_go.read_typetree()
    comps = ht.get("m_Component") or []
    comps.append({"component": {"m_FileID": 0, "m_PathID": col_id}})
    comps.append({"component": {"m_FileID": 0, "m_PathID": grp_id}})
    ht["m_Component"] = comps
    host_go.save_typetree(ht)

    touched = 0
    for s in inst_tree["SpringBone"]["Springs"]:
        if s.get("Name") in k["chain"]:
            cur = list(s.get("ColliderGroups") or [])
            cur.append({"m_FileID": 0, "m_PathID": grp_id})
            s["ColliderGroups"] = cur
            touched += 1
    if touched != len(k["chain"]):
        die("expected to touch %d chain(s), touched %d" % (len(k["chain"]), touched))
    inst_obj.save_typetree(inst_tree)

    data = af.save(packer="original")

    # ------------------------------------------------- verify on the bytes, in WORLD space
    env2 = UnityPy.load(_io.BytesIO(data))
    problems = []
    seen_col = seen_grp = False
    attached = False
    chains_after = {}
    for o in env2.objects:
        if o.type.name == "GameObject" and o.path_id == hgid:
            ids = [c["component"]["m_PathID"]
                   for c in (o.read_typetree().get("m_Component") or [])]
            attached = col_id in ids and grp_id in ids
        if o.type.name != "MonoBehaviour":
            continue
        try:
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                            # noqa: BLE001
            continue
        if o.path_id == col_id and cn == "VRM10SpringBoneCollider":
            seen_col = True
        if o.path_id == grp_id and cn == "VRM10SpringBoneColliderGroup":
            seen_grp = True
        if cn == "Vrm10Instance":
            for s in o.read_typetree()["SpringBone"]["Springs"]:
                chains_after[s.get("Name")] = [g["m_PathID"]
                                               for g in (s.get("ColliderGroups") or [])]
    if not seen_col:
        problems.append("the new collider is not in the written bytes")
    if not seen_grp:
        problems.append("the new group is not in the written bytes")
    if not attached:
        problems.append("the host GameObject does not list them -- ORPHANS")
    for cn in k["chain"]:
        after = chains_after.get(cn) or []
        if grp_id not in after:
            problems.append("chain %r does not reference the new group" % cn)
        if sorted(x for x in after if x != grp_id) != sorted(pre_groups[cn]):
            problems.append("chain %r LOST a group it had (%s -> %s)"
                            % (cn, pre_groups[cn], after))
    for cn, gs in chains_after.items():
        if cn in k["chain"]:
            continue
        if sorted(gs) != sorted(pre_groups.get(cn, [])):
            problems.append("chain %r had its groups CHANGED (%s -> %s)"
                            % (cn, pre_groups.get(cn), gs))

    # THE ROUND TRIP. Read the capsule back the way cloth_collide_installed does, in world
    # space, and compare against what was asked for. The radius went in divided by the
    # bone's scale; if that scale is not what this tool thought, the file holds a capsule of
    # the wrong size and nothing above would notice.
    tmp = os.path.join(os.environ.get("TEMP", "."), "place_collider_verify.yargchar")
    with open(tmp, "wb") as fh:
        fh.write(data)
    try:
        _h, tf2, go_tf2, springs2, _j2, colliders2, groups2, world2 = cci.read(tmp)
        got = colliders2.get(col_id)
        if got is None:
            problems.append("the new collider does not read back as a collider at all")
        else:
            ctp = go_tf2.get((got.get("m_GameObject") or {}).get("m_PathID"))
            wp2, wq2, ws2 = world2(ctp)

            def tw2(v):
                sc = (v.get("x", 0.0) * ws2[0], v.get("y", 0.0) * ws2[1],
                      v.get("z", 0.0) * ws2[2])
                r = cci.qrot(wq2, sc)
                return (wp2[0] + r[0], wp2[1] + r[1], wp2[2] + r[2])

            A2, B2 = tw2(got.get("Offset") or {}), tw2(got.get("Tail") or {})
            r2 = float(got.get("Radius", 0.0)) * ws2[0]
            dA = math.sqrt(sum((A2[i] - A[i]) ** 2 for i in range(3)))
            dB = math.sqrt(sum((B2[i] - B[i]) ** 2 for i in range(3)))
            print()
            print("ROUND TRIP in world space: radius %.2f mm (asked %.2f), ends moved "
                  "%.3f and %.3f mm" % (r2 * 1000, want_r_world * 1000, dA * 1000, dB * 1000))
            if abs(r2 - want_r_world) > 0.0005:
                problems.append("the written capsule reads back at %.2f mm, not %.2f"
                                % (r2 * 1000, want_r_world * 1000))
            if max(dA, dB) > 0.0005:
                problems.append("the written capsule's ends read back %.2f mm away"
                                % (max(dA, dB) * 1000))
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems))

    with open(path, "wb") as fh:
        fh.write(data)
    print()
    print("WRITTEN. collider %d (r %.1f mm) and group %r %d on bone %r."
          % (col_id, want_r_world * 1000, gt["Name"], grp_id, k["host"]))
    print("chains now referencing it: %s" % ", ".join(k["chain"]))
    print("%d other chain(s) verified unchanged." % (len(chains_after) - len(k["chain"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
