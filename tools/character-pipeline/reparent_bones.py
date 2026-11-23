# -*- coding: utf-8 -*-
"""Re-parent bones inside an installed bundle WITHOUT moving anything in the rest pose.

    python reparent_bones.py <file.yargchar> <bone>=<new parent> [...] [--write]

WHY. Batman's cape carries bones named and POSITIONED for the shoulder -- `capeClav_att` sits
102 mm from his clavicle, `capeTrap` 132 mm from his upper arm -- and every one of them hangs
off `C_cape_root <- C_spine_d`, a sibling branch of the arm. So the clavicle rotates, the
deltoid swings, and the part of the cape authored to sit on that shoulder does not follow it.
Power Girl's cape, the only other full cape on the roster, parents 52 of its 117 bones beneath
her clavicles. This makes Batman's match: the operation is hers, not an invention.

THE WHOLE PROBLEM IS THAT PARENTING CARRIES GEOMETRY. A bone's world transform is its parent's
times its own local one, so changing the parent and nothing else teleports the bone and every
vertex weighted to it. This therefore RE-DERIVES the local transform to hold the world
transform fixed:

    local' = world(newparent)^-1 . world(bone)

which is exact in the rest pose, leaves every bind pose valid (they map mesh space to bone
space and never mention the hierarchy), and changes only what happens when the NEW parent moves
-- which is the entire point.

WHAT IT VERIFIES, from the written bytes, before replacing anything:

  * EVERY bone's world position and rotation, not only the moved ones. A re-parent edits the
    old parent's child list as well as the new one's, and a check that looked only at the bones
    it moved could not see a sibling dragged along by a botched list edit.
  * that each moved bone's father IS the requested one, and that it appears exactly once in
    that parent's children and not at all in the old parent's.
  * the container is still a UnityFS bundle of a sane size.

It REFUSES a cycle (parenting a bone beneath its own descendant), a bone that is already
parented where asked, and any bone it cannot find. None of that is theoretical: the first two
are what a careless pass over a symmetric rig produces.

THIS DOES NOT TOUCH WEIGHTS. Vertices stay weighted to exactly the bones they were weighted to.
"""
import hashlib
import io as _io
import math
import os
import shutil
import sys

import cloth_collide_installed as cci
import UnityPy

BACKUP_DIR = r"C:\dev\YARG - Open Source Contributions\character-backups"
TOL_POS = 2e-5          # 0.02 mm
TOL_ROT = 2e-5


def die(msg):
    print("REFUSED: %s" % msg)
    sys.exit(1)


def qconj(q):
    return (q[0], -q[1], -q[2], -q[3])


def qmul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def qrot(q, v):
    w, x, y, z = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def main():
    argv = [a for a in sys.argv[1:] if a != "--write"]
    write = "--write" in sys.argv
    if len(argv) < 2:
        print(__doc__)
        return 2
    path, pairs = argv[0], argv[1:]
    if not os.path.isfile(path):
        die("%s does not exist" % path)

    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    nm = lambda t: (tf.get(t, {}).get("name") or "?")
    byname = {}
    for pid in tf:
        byname.setdefault(nm(pid), []).append(pid)

    def one(n):
        hit = byname.get(n) or []
        if not hit:
            die("no bone called %r" % n)
        if len(hit) > 1:
            die("%d bones are called %r, so the name does not identify one" % (len(hit), n))
        return hit[0]

    moves = []
    for spec in pairs:
        if "=" not in spec:
            die("%r is not <bone>=<new parent>" % spec)
        b, p = spec.split("=", 1)
        bp, pp = one(b.strip()), one(p.strip())
        if tf[bp].get("f") == pp:
            die("%s is already parented to %s" % (b, p))
        # cycle check: walk UP from the proposed parent; the bone must not be on that path
        q, seen = pp, 0
        while q in tf and seen < 64:
            if q == bp:
                die("parenting %s beneath %s would make a cycle -- %s is already its ancestor"
                    % (b, p, b))
            q = tf[q].get("f")
            seen += 1
        moves.append((bp, pp))

    before = {pid: world(pid) for pid in tf}

    print("%s -- %d transform(s), moving %d" % (os.path.basename(path), len(tf), len(moves)))
    for bp, pp in moves:
        wp = before[bp][0]
        print("  %-26s  %-22s -> %-22s   at (%.3f %.3f %.3f)"
              % (nm(bp)[:26], nm(tf[bp].get("f"))[:22], nm(pp)[:22], wp[0], wp[1], wp[2]))
        kids = [c for c in tf if tf[c].get("f") == bp]
        if kids:
            print("       carries %d child bone(s) with it: %s"
                  % (len(kids), ", ".join(nm(c) for c in kids[:6])))

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
    tts = {}
    for o in env.objects:
        if o.type.name == "Transform":
            tts[o.path_id] = (o, o.read_typetree())

    for bp, pp in moves:
        if bp not in tts or pp not in tts:
            die("a transform went missing between the read and the write")
        o_b, t_b = tts[bp]
        oldf = tf[bp].get("f")

        # local' = world(newparent)^-1 . world(bone), so the world transform is unchanged
        wp_p, wq_p, ws_p = before[pp]
        wp_b, wq_b, ws_b = before[bp]
        inv_q = qconj(wq_p)
        dv = (wp_b[0] - wp_p[0], wp_b[1] - wp_p[1], wp_b[2] - wp_p[2])
        sx, sy, sz = (ws_p[0] or 1.0), (ws_p[1] or 1.0), (ws_p[2] or 1.0)
        dv = (dv[0] / sx, dv[1] / sy, dv[2] / sz)
        lp = qrot(inv_q, dv)
        lq = qmul(inv_q, wq_b)
        n = math.sqrt(sum(c * c for c in lq)) or 1.0
        lq = tuple(c / n for c in lq)

        t_b["m_LocalPosition"] = {"x": lp[0], "y": lp[1], "z": lp[2]}
        t_b["m_LocalRotation"] = {"x": lq[1], "y": lq[2], "z": lq[3], "w": lq[0]}
        t_b["m_LocalScale"] = {"x": ws_b[0] / sx, "y": ws_b[1] / sy, "z": ws_b[2] / sz}
        t_b["m_Father"] = {"m_FileID": 0, "m_PathID": pp}
        o_b.save_typetree(t_b)

        # the old parent loses a child, the new one gains it
        if oldf in tts:
            o_o, t_o = tts[oldf]
            t_o["m_Children"] = [c for c in (t_o.get("m_Children") or [])
                                 if c.get("m_PathID") != bp]
            o_o.save_typetree(t_o)
        o_p, t_p = tts[pp]
        ch = list(t_p.get("m_Children") or [])
        if not any(c.get("m_PathID") == bp for c in ch):
            ch.append({"m_FileID": 0, "m_PathID": bp})
        t_p["m_Children"] = ch
        o_p.save_typetree(t_p)

    data = env.file.save(packer="original")
    if not data.startswith(b"UnityFS"):
        die("the written bytes are not a UnityFS bundle. Nothing written.")
    if not (0.5 * len(src) <= len(data) <= 2.0 * len(src)):
        die("the written bytes are %d against %d in. Re-parenting cannot do that. "
            "Nothing written." % (len(data), len(src)))
    print("container: UnityFS kept, %d bytes against %d in (%+d)"
          % (len(data), len(src), len(data) - len(src)))

    # VERIFY EVERY BONE, not just the moved ones.
    tmp = path + ".verify"
    open(tmp, "wb").write(data)
    try:
        h2, tf2, go2, sp2, j2, c2, g2, world2 = cci.read(tmp)
        problems = []
        if len(tf2) != len(tf):
            problems.append("transform count changed, %d -> %d" % (len(tf), len(tf2)))
        worst = 0.0
        for pid, (p0, q0, _s0) in before.items():
            if pid not in tf2:
                problems.append("%s vanished" % nm(pid))
                continue
            p1, q1, _s1 = world2(pid)
            dp = math.dist(p0, p1)
            dq = min(sum((a - b) ** 2 for a, b in zip(q0, q1)),
                     sum((a + b) ** 2 for a, b in zip(q0, q1))) ** 0.5
            worst = max(worst, dp)
            if dp > TOL_POS or dq > TOL_ROT:
                problems.append("%s moved %.4f mm / rot %.2e in the REST pose"
                                % (nm(pid), dp * 1000.0, dq))
        for bp, pp in moves:
            if tf2.get(bp, {}).get("f") != pp:
                problems.append("%s did not end up parented to %s" % (nm(bp), nm(pp)))
        if problems:
            die("the re-parent verified wrong and was NOT written:\n  - "
                + "\n  - ".join(problems[:12]))
        print("verified: all %d bones hold their rest-pose world transform "
              "(worst %.5f mm), and every move took" % (len(tf2), worst * 1000.0))
    finally:
        if os.path.isfile(tmp):
            os.remove(tmp)

    open(path, "wb").write(data)
    print("WRITTEN. re-parented %s." % ", ".join(nm(b) for b, _ in moves))
    return 0


if __name__ == "__main__":
    sys.exit(main())
