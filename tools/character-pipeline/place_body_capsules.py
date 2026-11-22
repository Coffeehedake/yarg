# -*- coding: utf-8 -*-
"""Write a WHOLE BODY of fitted capsules into one collider group, and point chains at it.

    python place_body_capsules.py <file.yargchar> --chain NAME [--chain NAME ...]
           [--group NAME] [--min-verts N] [--percentile P] [--exclude a,b,c]
           [--garment-match SUB] [--allow-displace MM] [--allow-contain PCT] [--write]

WHY THIS EXISTS. Jay, after three failed attempts at a radius: *"We need the entirety of the
character's body to deflect any of the cape that IS attached to a spring bone."* The measurement
behind that is **69.1% of Batman's body skin sits outside every one of his ten authored
colliders** -- his whole belt and waist, his chest, his feet, most of his hips. There was never
a radius that could fix that; the body simply was not represented. `fit_body_capsules.py` fits
one capsule per bone from the skin that bone itself owns; this writes the result.

`place_collider.py` cannot: it writes ONE collider into ONE new group, so forty-one invocations
would leave the character with forty-one groups and forty-one entries on every cape chain. This
writes one group holding all of them, which is also how the character's own author did it --
his `Body` group holds ten.

WHAT IT REFUSES, and the first of these is the one that matters most here:

  * a capsule that would START a named chain's joint inside it. Forty-one new volumes around a
    body is forty-one new chances to swallow a joint that is resting against the skin, and the
    solver's first act is to shove such a joint to the surface -- a visible jump on frame one,
    not a collision. Every new capsule is tested against every joint of every named chain.
    Refused above `--allow-displace`, stated in millimetres.
  * a capsule that swallows more of the body than the fattest collider the character's own
    author drew, above `--allow-contain`. A bone whose principal axis runs ACROSS the figure
    can still produce a tube around several parts, which is exactly what put a cape around
    Batman's arms on 2026-11-21.
  * a chain that does not exist, a bone with no GameObject, a round trip that does not reproduce
    what was asked, an orphaned component, and bytes that are no longer a `UnityFS` bundle.

It backs the file up first and verifies on the BYTES IN HAND, in world space, rather than on the
file -- a file written and then found wrong is a file somebody may already have installed.
"""
import copy
import hashlib
import io as _io
import math
import os
import shutil
import sys

import capsule_contains as cc
import cloth_collide_installed as cci
import fit_body_capsules as fb
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
        die("--chain is required: a collider group nothing references guards nothing")
    group_name = arg("--group", "FittedBody")
    minv = int(arg("--min-verts", 60))
    pct = float(arg("--percentile", 90.0))
    excl = [s.strip().lower() for s in (arg("--exclude") or "").split(",") if s.strip()]
    gm = arg("--garment-match")
    allow_d = float(arg("--allow-displace", 0.0)) / 1000.0
    allow_c = float(arg("--allow-contain", 0.0)) / 100.0
    write = "--write" in sys.argv

    # ------------------------------------------------------------------ measure first
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    by_name = {s[0]: s for s in springs}
    missing = [c for c in chains if c not in by_name]
    if missing:
        die("no chain(s) %s; this file has %s" % (missing, sorted(by_name)))

    garment = cc.cloth_bones(tf, go_tf, springs, joints, gm)
    skin = cc.skin_vertices(path, tf, world, garment)
    if not skin:
        die("no skin decoded, so nothing can be fitted and nothing can be checked")
    shapes = cc.collider_shapes(tf, go_tf, colliders, world)
    fitted = fb.fit_capsules(tf, world, skin, minv, pct, excl)
    if not fitted:
        die("no bone owns %d or more skin vertices after the exclusions -- nothing to write"
            % minv)

    # the joints we must not displace
    # THE FIRST JOINT OF A CHAIN IS AN ANCHOR AND IS NEVER MOVED, so a capsule containing it
    # displaces nothing. UpdateFastSpringBoneJob iterates one "logic" per HEAD->TAIL pair and
    # writes NextTail; for joints J0..Jn the pairs are (J0,J1)...(Jn-1,Jn), so the positions
    # that move are J1..Jn and J0 comes from the skeleton. Testing it would refuse every
    # capsule that wraps the chest, because that is exactly where a cape is attached.
    jrows = []
    for cn in chains:
        for jp in by_name[cn][1][1:]:
            rec = joints.get(jp)
            tp = go_tf.get(rec[0]) if rec else None
            if tp is None:
                die("a joint of %s has no transform -- refusing to write against an "
                    "incomplete measurement" % cn)
            wp, _q, ws = world(tp)
            jrows.append((cn, tf.get(tp, {}).get("name") or "?", wp, rec[4] * ws[0]))

    step = max(1, len(skin) // 12000)
    sample = skin[::step]
    authored = max((cc.contains(sample, v[2], v[3], v[1])[0] for v in shapes.values()),
                   default=0.0)

    print("%d capsule(s) fitted, %d chain(s) named, %d joint(s) to protect"
          % (len(fitted), len(chains), len(jrows)))
    print("the fattest collider this character already ships holds %.1f%% of the body"
          % (authored * 100))
    print()
    print("%-26s %9s %9s %8s" % ("bone", "radius", "tightest", "share"))
    print("-" * 60)
    world_caps, bad_d, bad_c, shrunk = [], [], [], []
    final = []
    for bn, r, A, B, ws, wp, wq in fitted:
        WA = fb.to_world(A, wp, wq, ws)
        WB = fb.to_world(B, wp, wq, ws)
        wr = r * ws[0]

        # CLAMP BY THE CONSTRAINT RATHER THAN DROP THE CAPSULE. The fit answers "how big is
        # this part"; the solver imposes a second, independent bound -- no resting joint may
        # start inside -- and the honest capsule is the smaller of the two. Dropping an
        # offender instead would leave a hole exactly where the body is widest, which on
        # Batman is his belt: the single most uncovered part of him.
        if "--shrink-to-fit" in sys.argv:
            # half a millimetre of margin, because clamping exactly onto the bound leaves a
            # clearance of zero and the gate then trips on float error rather than on anything
            # real -- a refusal reading "0.0 mm inside" is a rounding artefact, not a fault.
            room = min((cc.seg_dist(jp, WA, WB) - jr for _c, _b, jp, jr in jrows),
                       default=wr) - 0.0005
            if room < wr:
                if room <= 0.005:
                    bad_d.append((bn, room - wr, "a joint is inside it whatever the radius"))
                    continue
                shrunk.append((bn, wr, room))
                wr = room
                r = wr / ws[0]

        final.append((bn, r, A, B, ws, wp, wq))
        world_caps.append((bn, wr, WA, WB))
        tight, tight_j = None, None
        for cn, jb, jp, jr in jrows:
            clear = cc.seg_dist(jp, WA, WB) - wr - jr
            if tight is None or clear < tight:
                tight, tight_j = clear, "%s/%s" % (cn, jb)
        share, _ = cc.contains(sample, WA, WB, wr)
        flag = ""
        if tight is not None and tight < -allow_d:
            bad_d.append((bn, tight, tight_j))
            flag = "  <- DISPLACES"
        if share > authored + allow_c:
            bad_c.append((bn, share))
            flag += "  <- OVER the author's fattest"
        print("%-26s %6.1f mm %6.1f mm %7.1f%%%s"
              % (bn[:26], wr * 1000, (tight or 0) * 1000, share * 100, flag))

    if bad_d:
        print()
        die("%d capsule(s) would START a joint inside them, worst %s at %.1f mm, and "
            "--allow-displace is %.1f mm. The solver shoves such a joint to the surface on "
            "frame one, which is a visible jump and not a collision. Nothing written.\n  %s"
            % (len(bad_d), bad_d[0][2], -min(b[1] for b in bad_d) * 1000, allow_d * 1000,
               "\n  ".join("%s %.1f mm inside %s" % (b[0], -b[1] * 1000, b[2]) for b in bad_d)))
    if bad_c:
        print()
        die("%d capsule(s) swallow more of the body than the %.1f%% of the fattest collider "
            "the author drew, and --allow-contain permits %.1f%% more. Nothing written.\n  %s"
            % (len(bad_c), authored * 100, allow_c * 100,
               "\n  ".join("%s %.1f%%" % (b[0], b[1] * 100) for b in bad_c)))

    before = sum(1 for _bn, q in sample
                 if not any(cc.seg_dist(q, a, b) < r for _n, r, a, b, _c in shapes.values()))
    after = sum(1 for _bn, q in sample
                if not any(cc.seg_dist(q, a, b) < r
                           for _n, r, a, b in world_caps + [(v[0], v[1], v[2], v[3])
                                                            for v in shapes.values()]))
    if shrunk:
        print()
        print("%d capsule(s) CLAMPED by the no-displacement bound:" % len(shrunk))
        for bn, was, now in sorted(shrunk, key=lambda t: t[1] - t[2], reverse=True)[:8]:
            print("    %-26s %6.1f mm -> %6.1f mm" % (bn[:26], was * 1000, now * 1000))
    print()
    print("every capsule clears every joint of every named chain.")
    print("body skin outside every collider: %.1f%% now -> %.1f%% after"
          % (100.0 * before / len(sample), 100.0 * after / len(sample)))

    if not write:
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
        dest = os.path.join(BACKUP_DIR, "%s.%s.bak" % (os.path.basename(path), src_md5[:8]))
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
        die("this file has no collider, collider group and Vrm10Instance to copy the SHAPE of "
            "the MonoBehaviour from. Nothing is invented here, so there is nothing to do")

    tf_of_name = {}
    for pid, rec in tf.items():
        tf_of_name.setdefault(rec.get("name") or "", pid)
    gid_of_tf = {}
    for gid, tpid in go_tf.items():
        gid_of_tf[tpid] = gid

    af = donor_col.assets_file
    nxt = max(af.objects.keys()) + 1

    new_ids, hosts = [], {}
    for bn, r, A, B, ws, wp, wq in final:
        tpid = tf_of_name.get(bn)
        hgid = gid_of_tf.get(tpid)
        if hgid is None or hgid not in go_objs:
            die("bone %r has no GameObject in this file" % bn)
        ct = copy.deepcopy(donor_col.read_typetree())
        ct["m_GameObject"] = {"m_FileID": 0, "m_PathID": hgid}
        ct["ColliderType"] = 1                  # 1 = capsule; 0 would ignore Tail entirely
        ct["Radius"] = r
        ct["Offset"] = {"x": A[0], "y": A[1], "z": A[2]}
        ct["Tail"] = {"x": B[0], "y": B[1], "z": B[2]}
        nc = copy.copy(donor_col)
        nc.path_id = nxt
        nc.save_typetree(ct)
        af.objects[nxt] = nc
        new_ids.append(nxt)
        hosts.setdefault(hgid, []).append(nxt)
        nxt += 1

    # the group lives on the Vrm10Instance's own GameObject: it belongs to no single bone, and
    # putting it on one of the forty-one hosts would make its home arbitrary.
    inst_gid = (inst_tree.get("m_GameObject") or {}).get("m_PathID")
    if inst_gid not in go_objs:
        die("the Vrm10Instance has no GameObject to carry the collider group")
    gt = copy.deepcopy(donor_grp.read_typetree())
    gt["Name"] = group_name
    gt["Colliders"] = [{"m_FileID": 0, "m_PathID": i} for i in new_ids]
    gt["m_GameObject"] = {"m_FileID": 0, "m_PathID": inst_gid}
    ng = copy.copy(donor_grp)
    ng.path_id = nxt
    ng.save_typetree(gt)
    af.objects[nxt] = ng
    grp_id = nxt
    hosts.setdefault(inst_gid, []).append(grp_id)

    # EVERY new component must be listed by its GameObject. A collider that deserialises
    # perfectly and is a component of nothing is an orphan, and 21 of those passed every check
    # this project had on 2026-11-15.
    for gid, ids in hosts.items():
        go = go_objs[gid]
        t = go.read_typetree()
        comps = t.get("m_Component") or []
        for i in ids:
            comps.append({"component": {"m_FileID": 0, "m_PathID": i}})
        t["m_Component"] = comps
        go.save_typetree(t)

    touched = 0
    for s in inst_tree["SpringBone"]["Springs"]:
        if s.get("Name") in chains:
            cur = list(s.get("ColliderGroups") or [])
            cur.append({"m_FileID": 0, "m_PathID": grp_id})
            s["ColliderGroups"] = cur
            touched += 1
    if touched != len(chains):
        die("expected to touch %d chain(s), touched %d" % (len(chains), touched))
    inst_obj.save_typetree(inst_tree)

    # SAVE THE BUNDLE, NOT THE ASSETS FILE. `af.save()` returns the SerializedFile inside the
    # UnityFS bundle; writing that as the .yargchar leaves a file UnityPy reads happily and
    # AssetBundle.LoadFromFile cannot open at all. It cost two installed characters.
    data = env.file.save(packer="original")
    if not data.startswith(b"UnityFS"):
        die("the written bytes do not start with 'UnityFS', so this is no longer an "
            "AssetBundle and the game cannot load it. Nothing written.")
    if not (0.5 * len(src) <= len(data) <= 2.0 * len(src)):
        die("the written bytes are %d against %d in -- a factor of %.1f. Nothing written."
            % (len(data), len(src), float(len(data)) / max(1, len(src))))
    print("container: UnityFS kept, %d bytes against %d in (%+d)"
          % (len(data), len(src), len(data) - len(src)))

    # ------------------------------------------- verify on the BYTES, in world space
    env2 = UnityPy.load(_io.BytesIO(data))
    human2, tf2, go_tf2, springs2, joints2, colliders2, groups2, world2 = \
        cci.read(_io.BytesIO(data))
    shapes2 = cc.collider_shapes(tf2, go_tf2, colliders2, world2)
    problems = []

    got = {}
    for _cp, (bn, r, A, B, ct) in shapes2.items():
        got.setdefault(bn, []).append((r, A, B, ct))
    for bn, wr, WA, WB in world_caps:
        cand = got.get(bn) or []
        hit = None
        for r, A, B, ct in cand:
            if abs(r - wr) < 1e-5 and ct == 1:
                d = max(math.dist(A, WA), math.dist(B, WB))
                if d < 1e-5:
                    hit = True
        if not hit:
            problems.append("%s: no capsule in the written bytes matches r=%.3f mm and both "
                            "endpoints" % (bn, wr * 1000))

    gfound = None
    for gp, ids in groups2.items():
        if len(ids) == len(new_ids) and set(ids) == set(new_ids):
            gfound = gp
    if gfound is None:
        problems.append("the written group does not hold exactly the %d new colliders"
                        % len(new_ids))
    else:
        for nm, _jps, g in springs2:
            if nm in chains and gfound not in g:
                problems.append("chain %s does not reference the new group" % nm)

    comp_ids = set()
    for o in env2.objects:
        if o.type.name == "GameObject":
            for c in (o.read_typetree().get("m_Component") or []):
                comp_ids.add(c["component"]["m_PathID"])
    orphans = [i for i in new_ids + [grp_id] if i not in comp_ids]
    if orphans:
        problems.append("%d new component(s) are listed by no GameObject -- orphans: %s"
                        % (len(orphans), orphans[:6]))

    if problems:
        die("the patch verified wrong and was NOT written:\n  - " + "\n  - ".join(problems))

    open(path, "wb").write(data)
    print("ROUND TRIP in world space: %d capsule(s), every radius and both endpoints within "
          "0.01 mm of what was asked" % len(world_caps))
    print("WRITTEN. group %r (%d colliders) on the Vrm10Instance, referenced by %d chain(s)."
          % (group_name, len(new_ids), touched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
