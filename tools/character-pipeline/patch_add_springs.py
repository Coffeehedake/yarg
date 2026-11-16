# -*- coding: utf-8 -*-
"""patch_add_springs.py <bundle> <out> --chain A,B,C [--chain ...] [knobs]

Put EXISTING bones of an installed character on spring chains.

This is the opposite of `patch_springs.py --unrig-hair`, which takes chains
away, and it exists for a fault that tool cannot describe: a character whose
hair, tail or tie bones are named `Bone07`, `Bone08`, `Bone14(mirrored)`.
Every automatic rigger in this pipeline selects by NAME -- build_vrm.py's
DEFAULT_SPRING is a regex over bone names, and spring_scan.py uses the same
vocabulary -- so a rig with generic bone names reports "no hair chains found"
and is left entirely rigid, correctly, by a rule that simply cannot see it.

Miku is the case. Her twintails hang off ten bones a side called Bone06..Bone15
and her necktie off Bone01..Bone03, and none of those words is hair, tail, bang
or tie. What she shipped with instead were two chains of four bones each that
an earlier repair INVENTED and weighted a little of her hair onto: 38 of her
500 twintail vertices moved and 462 did not.

WHY THIS PATCHES RATHER THAN REBUILDS. The chains could be built by
build_vrm.py with an explicit SPRING pattern, and on a character being built
anyway that is the right road. On one already installed it is not: a rebuild
re-derives every other decision in the file -- her re-aimed necktie, her
flattened materials -- from a recipe, and the whole point here is to change
one thing. So the joints go into the bundle directly.

ADDING AN OBJECT TO A BUNDLE. UnityPy 1.25 has no API for it. What it does
have is enough: a SerializedFile keeps its objects in a plain dict keyed by
path_id and writes `sorted(self.objects.values(), ...)`, and an ObjectReader
writes `self.data` whenever `save_typetree` has set it. So a new joint is a
shallow copy of an existing one -- same assets_file, type_id, serialized_type,
class_id -- given a fresh path_id and its own typetree. Nothing is invented:
every joint this tool writes is structurally a copy of a joint the file was
already carrying, which is also why it refuses to run on a file that has none.

A COMPONENT IS A TWO-WAY LINK, AND THE FIRST VERSION OF THIS ONLY WROTE ONE
SIDE. The MonoBehaviour names its GameObject in `m_GameObject`, and the
GameObject must list the component back in `m_Component`. Setting only the
first makes an orphan: deserialised, present, reachable by a direct pointer,
and not a component of anything -- so the spring runtime does nothing with it.

Miku shipped that way on 2026-11-15. All 21 joints were orphans, her twintails
did not move, and every check agreed they would: the Unity load test followed
the Springs array's own pointers and found 29 joints, 0 null, because that is
the one direction that works whether or not the other does. The reporter saw
no change at all.

So the GameObject is updated too, and the verification pass re-reads the
written bytes and requires every new joint to be LISTED BY ITS BONE. A check
that only follows the pointers the patch wrote can only confirm the patch
wrote them.

THE GUARDS ARE THE TOOL. Writing the Springs array is six lines; being sure
the result is a chain and not a crash is the rest:

  * every bone must exist, and must be a child of the bone before it --
    a VRM chain is a PATH, and a list of unrelated bones is not one
  * no bone may be a humanoid bone -- a spring bone must not also be a limb
  * no bone may already be on a chain -- a bone belongs to exactly one
  * a chain needs two bones, because the last joint only marks the tip
  * no joint may START INSIDE one of its own colliders -- see below
  * and afterwards the written BYTES are re-read and every chain re-checked
    before the file is kept

A REST POSE ALREADY IN PENETRATION IS NOT A COLLISION, IT IS A DISPLACEMENT.
The solver's first act is to push a joint out to the collider's surface, so a
chain whose rest pose is inside a collider does not settle there -- it jumps,
on frame one, before anything has moved. Miku's necktie is the case and the
reason this guard exists: her three tie bones sit 44.4, 30.5 and 7.4 mm inside
the capsule that stands in for her torso, because that capsule is a crude
cylinder 132 mm in radius and she is slim. Giving the tie that group would
have thrown the knot 44 mm forward and reproduced, exactly, the "tie sticking
straight out" that had just been fixed by re-aiming the chain.

`--group none` is the escape, and it is a real trade rather than a way past
the check: a chain with no colliders can swing through the body. For a narrow
strap hanging at rest in front of the chest that is the better of the two
faults, and for hair it would not be.

It also reports how many vertices each chain actually dominates, because
"3 chains added" is a fact about the file and says nothing about how much of
the character moves -- which was the entire complaint that sent me here.
"""
import copy
import math
import os
import sys

import UnityPy

JOINT_CLEAR_MM = 0.0     # a joint must not be inside a collider at rest


def die(msg):
    raise SystemExit("ABORT: %s" % msg)


def qm(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def qrot(q, v):
    w, x, y, z = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def seg_dist(p, a, b):
    ab = [b[i] - a[i] for i in range(3)]
    ap = [p[i] - a[i] for i in range(3)]
    L = sum(x * x for x in ab)
    t = (0.0 if L <= 0 else
         max(0.0, min(1.0, sum(ap[i] * ab[i] for i in range(3)) / L)))
    c = [a[i] + ab[i] * t for i in range(3)]
    return math.sqrt(sum((p[i] - c[i]) ** 2 for i in range(3)))


def parse_args(argv):
    """Walk argv, so a flag's value can never be taken for a positional."""
    pos, chains = [], []
    knob = {"stiff": 0.6, "drag": 0.45, "grav": 0.0, "radius": 0.02,
            "name": None, "group": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--chain":
            i += 1
            if i >= len(argv):
                die("--chain needs a comma-separated list of bone names")
            chains.append([x.strip() for x in argv[i].split(",") if x.strip()])
        elif a.startswith("--") and a[2:] in knob:
            k = a[2:]
            i += 1
            if i >= len(argv):
                die("%s needs a value" % a)
            knob[k] = argv[i] if k in ("name", "group") else float(argv[i])
        elif a.startswith("--"):
            die("unknown flag %r" % a)
        else:
            pos.append(a)
        i += 1
    if len(pos) != 2:
        die("usage: patch_add_springs.py <bundle> <out> --chain A,B,C ...")
    if not chains:
        die("no --chain given; there is nothing to add")
    return pos[0], pos[1], chains, knob


def load(path):
    """Everything the patch needs, in one pass over the objects."""
    env = UnityPy.load(path)
    objs = {}
    for o in env.objects:
        try:
            objs[o.path_id] = (o.type.name, o)
        except Exception:                                        # noqa: BLE001
            pass

    name_to_go, go_name, human = {}, {}, set()
    tf_go, go_tf, parent_tf, tf = {}, {}, {}, {}
    for pid, (ty, o) in objs.items():
        if ty == "Transform":
            d = o.read()
            g = getattr(d, "m_GameObject", None)
            gid = getattr(g, "path_id", 0) if g is not None else 0
            fa = getattr(d, "m_Father", None)
            tf_go[pid] = gid
            parent_tf[pid] = getattr(fa, "path_id", 0) if fa is not None else 0
            lp, lr, ls = d.m_LocalPosition, d.m_LocalRotation, d.m_LocalScale
            tf[pid] = {"p": (lp.x, lp.y, lp.z),
                       "q": (lr.w, lr.x, lr.y, lr.z),
                       "s": (ls.x, ls.y, ls.z),
                       "f": parent_tf[pid]}
            if not gid:
                continue
            go_tf[gid] = pid
            try:
                nm = g.read().m_Name
            except Exception:                                    # noqa: BLE001
                continue
            go_name[gid] = nm
            name_to_go.setdefault(nm, gid)
        elif ty == "Avatar":
            d = o.read()
            hd = getattr(d, "m_HumanDescription", None)
            for e in (getattr(hd, "m_Human", None) or []):
                bn = getattr(e, "m_BoneName", None)
                if bn:
                    human.add(bn)
    go_parent = {g: tf_go.get(parent_tf.get(t, 0), 0) for g, t in go_tf.items()}

    def world(pid):
        """Position, rotation and uniform scale of a transform."""
        chain, k = [], pid
        while k in tf:
            chain.append(k)
            k = tf[k]["f"]
        p, q, s = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), 1.0
        for k in reversed(chain):
            n = tf[k]
            lp = qrot(q, tuple(n["p"][i] * s for i in range(3)))
            p = (p[0] + lp[0], p[1] + lp[1], p[2] + lp[2])
            q = qm(q, n["q"])
            s *= n["s"][0]
        return p, q, s

    inst = None
    joints, groups, gcols, raw_col = {}, {}, {}, {}
    for pid, (ty, o) in objs.items():
        if ty != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
            cn = o.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            continue
        if cn == "Vrm10Instance":
            inst = (pid, o, t)
        elif cn == "VRM10SpringBoneJoint":
            joints[pid] = (o, t)
        elif cn == "VRM10SpringBoneColliderGroup":
            groups[pid] = t.get("Name") or ""
            gcols[pid] = [c["m_PathID"] for c in (t.get("Colliders") or [])]
        elif cn == "VRM10SpringBoneCollider":
            raw_col[pid] = t

    # Colliders, resolved into world space. Offset and Tail are given in the
    # collider BONE's own frame, so they go through that bone's matrix -- read
    # as world offsets they land in the wrong place and every clearance is
    # wrong in a way that still looks like a number.
    colliders = {}
    for pid, t in raw_col.items():
        gid = t.get("m_GameObject", {}).get("m_PathID")
        tp = go_tf.get(gid)
        if tp is None:
            continue
        wp, wq, ws = world(tp)
        off, tail = t["Offset"], t["Tail"]
        a = qrot(wq, (off["x"] * ws, off["y"] * ws, off["z"] * ws))
        a = (wp[0] + a[0], wp[1] + a[1], wp[2] + a[2])
        if t.get("ColliderType") == 1:
            b = qrot(wq, (tail["x"] * ws, tail["y"] * ws, tail["z"] * ws))
            b = (wp[0] + b[0], wp[1] + b[1], wp[2] + b[2])
        else:
            b = a
        colliders[pid] = (go_name.get(gid, "?"), t.get("ColliderType"),
                          t["Radius"] * ws, a, b)

    return (env, objs, go_name, name_to_go, go_parent, human, inst, joints,
            groups, gcols, colliders, go_tf, world)


def vert_census(objs, go_name):
    """How many vertices each bone DOMINATES.

    The only honest measure of what a chain moves. A chain over bones that
    carry no weight is still three chains in the file and no motion on the
    character, and that is precisely the state this tool was written to end.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from patch_springs import decode_ch
    except Exception:                                            # noqa: BLE001
        return None
    tf_name = {}
    for pid, (ty, o) in objs.items():
        if ty == "Transform":
            d = o.read()
            g = getattr(d, "m_GameObject", None)
            gid = getattr(g, "path_id", 0) if g is not None else 0
            tf_name[pid] = go_name.get(gid)
    cnt = {}
    for pid, (ty, o) in objs.items():
        if ty != "SkinnedMeshRenderer":
            continue
        try:
            r = o.read_typetree()
            mp = (r.get("m_Mesh") or {}).get("m_PathID")
            if not mp or mp not in objs:
                continue
            tt = objs[mp][1].read_typetree()
            ch = decode_ch(tt, (12, 13))
            bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
            if ch is None or not bones:
                continue
            W, I = ch[12], ch[13]
            for vi in range(len(W)):
                best, bw = None, -1.0
                for k in range(len(W[vi])):
                    w, bi = W[vi][k], I[vi][k]
                    if w > bw and bi < len(bones):
                        best, bw = bones[bi], w
                nm = tf_name.get(best)
                cnt[nm] = cnt.get(nm, 0) + 1
        except Exception:                                        # noqa: BLE001
            continue
    return cnt


def reread(data):
    """Chains, by bone name and parameters, out of bytes just written.

    Also reports, per joint, whether the bone's GameObject LISTS it. Following
    only the Springs array's own pointers confirms that the patch wrote the
    pointers it wrote; it cannot see an orphan, which is how 21 of them
    shipped.
    """
    env2 = UnityPy.load(data)
    jn2, name2, springs, gcomp = {}, {}, [], {}
    for o in env2.objects:
        try:
            ty = o.type.name
        except Exception:                                        # noqa: BLE001
            continue
        if ty == "GameObject":
            gt = o.read_typetree()
            ids = []
            for c in (gt.get("m_Component") or []):
                d = c.get("component") if isinstance(c, dict) else None
                if isinstance(d, dict):
                    ids.append(d.get("m_PathID"))
            gcomp[o.path_id] = ids
        if ty == "Transform":
            d = o.read()
            g = getattr(d, "m_GameObject", None)
            gid = getattr(g, "path_id", 0) if g is not None else 0
            if gid:
                try:
                    name2[gid] = g.read().m_Name
                except Exception:                                # noqa: BLE001
                    pass
        elif ty == "MonoBehaviour":
            try:
                t = o.read_typetree()
                cn = o.read().m_Script.read().m_ClassName
            except Exception:                                    # noqa: BLE001
                continue
            if cn == "VRM10SpringBoneJoint":
                jn2[o.path_id] = t
            elif cn == "Vrm10Instance":
                springs = (t.get("SpringBone") or {}).get("Springs") or []
    out = []
    for s in springs:
        bs = []
        for j in (s.get("Joints") or []):
            jid = j["m_PathID"]
            t = jn2.get(jid)
            if t is None:
                die("the file that was written references joint %d, which is "
                    "not in it" % jid)
            gid = t.get("m_GameObject", {}).get("m_PathID")
            bs.append((name2.get(gid),
                       round(t.get("m_stiffnessForce", 0.0), 4),
                       round(t.get("m_dragForce", 0.0), 4),
                       round(t.get("m_jointRadius", 0.0), 5),
                       jid in gcomp.get(gid, ())))
        out.append((s.get("Name"), bs, len(s.get("ColliderGroups") or [])))
    return out


def main():
    src, out, chains, knob = parse_args(sys.argv[1:])
    (env, objs, go_name, name_to_go, go_parent, human, inst, joints,
     groups, gcols, colliders, go_tf, world) = load(src)

    if inst is None:
        die("no Vrm10Instance in %s -- this is not a VRM character bundle"
            % os.path.basename(src))
    _ipid, iobj, itree = inst
    sb = itree.get("SpringBone") or {}
    springs = list(sb.get("Springs") or [])
    if not joints:
        die("this file carries no VRM10SpringBoneJoint to copy, and this tool "
            "builds new joints only by copying one that already exists")

    before = reread(open(src, "rb").read())

    # which bones are already spoken for
    taken = {}
    for s in springs:
        for j in (s.get("Joints") or []):
            jt = joints.get(j["m_PathID"])
            if jt:
                g = jt[1].get("m_GameObject", {}).get("m_PathID")
                taken[go_name.get(g)] = s.get("Name")

    # ---------------------------------------------------------------- guards
    seen = {}
    for ci, ch in enumerate(chains):
        if len(ch) < 2:
            die("chain %d %r has %d bone(s); a VRM chain needs at least two, "
                "because the last joint only marks the tip and is never "
                "simulated" % (ci, ch, len(ch)))
        for bi, bn in enumerate(ch):
            if bn not in name_to_go:
                die("chain %d names bone %r, which this character has not got"
                    % (ci, bn))
            if bn in human:
                die("chain %d names %r, which is a HUMANOID bone -- a spring "
                    "bone must not also be a limb" % (ci, bn))
            if bn in taken:
                die("chain %d names %r, which is already a joint on chain %r "
                    "-- a bone belongs to exactly one chain"
                    % (ci, bn, taken[bn]))
            if bn in seen:
                die("%r appears on chain %d and again on chain %d"
                    % (bn, seen[bn], ci))
            seen[bn] = ci
            if bi:
                want = name_to_go[ch[bi - 1]]
                got = go_parent.get(name_to_go[bn], 0)
                if got != want:
                    die("chain %d is not a path: %r's parent is %r, not %r. "
                        "A VRM chain walks down the hierarchy; a list of "
                        "unrelated bones is not a chain."
                        % (ci, bn, go_name.get(got, "(none)"), ch[bi - 1]))

    gref = list(sb.get("ColliderGroups") or [])
    if knob["group"] and knob["group"].lower() == "none":
        gref = []
    elif knob["group"]:
        gref = [{"m_FileID": 0, "m_PathID": p} for p, n in groups.items()
                if n == knob["group"]]
        if not gref:
            die("no collider group called %r; this file has %s"
                % (knob["group"], sorted(set(groups.values())) or "none"))

    # --- does any joint START inside one of its own colliders?
    mine = []
    for g in gref:
        for cp in gcols.get(g["m_PathID"], []):
            if cp in colliders:
                mine.append(colliders[cp])
    bad = []
    for ci, ch in enumerate(chains):
        for bn in ch:
            wp = world(go_tf[name_to_go[bn]])[0]
            for cn2, _ct, r, a, b in mine:
                clear = seg_dist(wp, a, b) - r - knob["radius"]
                if clear < JOINT_CLEAR_MM:
                    bad.append((ci, bn, cn2, clear))
    if bad:
        lines = "\n".join(
            "    chain %d, joint %-22s is %6.1f mm inside the collider on %r"
            % (ci, bn, -c * 1000, cn2) for ci, bn, cn2, c in bad)
        die("these joints START INSIDE a collider of the group they were "
            "given:\n%s\n  The solver's first act is to push a joint out to "
            "the collider's surface, so this is not a collision that will be "
            "handled -- it is a displacement, on frame one, before anything "
            "has moved. Either the group is wrong for this chain or the rest "
            "pose is. Pass --group none to attach no colliders, accepting "
            "that the chain can then swing through the body."
            % lines)

    # ------------------------------------------------------------- the write
    donor_pid = sorted(joints)[0]
    donor_obj, donor_tree = joints[donor_pid]
    af = donor_obj.assets_file
    used = set(af.objects.keys())
    nxt = max(used) + 1

    # the GameObject objects, so the component can be attached to its bone
    go_obj = {}
    for o in env.objects:
        try:
            if o.type.name == "GameObject":
                go_obj[o.path_id] = o
        except Exception:                                        # noqa: BLE001
            pass

    added = []
    attach = {}
    for ci, ch in enumerate(chains):
        jl = []
        for bn in ch:
            while nxt in used:
                nxt += 1
            t = copy.deepcopy(donor_tree)
            t["m_GameObject"] = {"m_FileID": 0, "m_PathID": name_to_go[bn]}
            t["m_stiffnessForce"] = knob["stiff"]
            t["m_dragForce"] = knob["drag"]
            t["m_gravityPower"] = knob["grav"]
            t["m_jointRadius"] = knob["radius"]
            clone = copy.copy(donor_obj)
            clone.path_id = nxt
            clone.save_typetree(t)
            af.objects[nxt] = clone
            used.add(nxt)
            attach.setdefault(name_to_go[bn], []).append(nxt)
            jl.append({"m_FileID": 0, "m_PathID": nxt})
        nm = knob["name"] or ch[0]
        if knob["name"] and len(chains) > 1:
            nm = "%s_%d" % (knob["name"], ci)
        springs.append({"Name": nm, "ColliderGroups": list(gref),
                        "Joints": jl, "Center": {"m_FileID": 0, "m_PathID": 0}})
        added.append((nm, ch))

    # the other half of the link: each bone's GameObject must list its joint
    for gid, jids in attach.items():
        o = go_obj.get(gid)
        if o is None:
            die("bone GameObject %d is not in this file, so its joint could "
                "not be attached to it" % gid)
        gt = o.read_typetree()
        comps = gt.get("m_Component") or []
        for jid in jids:
            comps.append({"component": {"m_FileID": 0, "m_PathID": jid}})
        gt["m_Component"] = comps
        o.save_typetree(gt)

    sb["Springs"] = springs
    itree["SpringBone"] = sb
    iobj.save_typetree(itree)
    data = env.file.save(packer="original")

    # --------------------------------------------------------- verify FIRST
    # UnityPy.load(path) holds the handle open on Windows, so the check runs
    # on the bytes in hand. It also has to: a file written and THEN found
    # wrong is a file somebody may already have installed.
    after = reread(data)
    for nm, ch in added:
        hit = [c for c in after if c[0] == nm]
        if len(hit) != 1:
            die("chain %r is not in the written file exactly once" % nm)
        bs = [b[0] for b in hit[0][1]]
        if bs != ch:
            die("chain %r reads back as %s, not %s" % (nm, bs, ch))
        if hit[0][2] != len(gref):
            die("chain %r came back with %d collider group(s), not the %d it "
                "was given" % (nm, hit[0][2], len(gref)))
        for b in hit[0][1]:
            if (abs(b[1] - knob["stiff"]) > 1e-4
                    or abs(b[2] - knob["drag"]) > 1e-4
                    or abs(b[3] - knob["radius"]) > 1e-5):
                die("joint %r in chain %r reads back as %s, not the requested "
                    "%s/%s/%s" % (b[0], nm, b[1:4], knob["stiff"],
                                  knob["drag"], knob["radius"]))
            if not b[4]:
                die("joint on %r in chain %r is an ORPHAN: the bone's "
                    "GameObject does not list it in m_Component, so it is not "
                    "a component of anything and the spring runtime will "
                    "ignore it. This is the fault that shipped on Miku."
                    % (b[0], nm))
    # and the chains that were already there must be untouched
    keep_before = {c[0]: c[1] for c in before}
    for nm, bs, _g in after:
        if nm in keep_before and keep_before[nm] != bs:
            die("chain %r, which this patch was not asked to touch, changed "
                "from %s to %s" % (nm, keep_before[nm], bs))
    if len(after) != len(before) + len(added):
        die("the written file has %d chains; %d + %d were expected"
            % (len(after), len(before), len(added)))

    with open(out, "wb") as fh:
        fh.write(data)

    # ---------------------------------------------------------------- report
    cnt = vert_census(objs, go_name) or {}
    print("%s -> %s" % (os.path.basename(src), os.path.basename(out)))
    print("  %d chain(s) before, %d after; %d new joint component(s)"
          % (len(before), len(after), sum(len(c) for _n, c in added)))
    print("  colliders: %s"
          % (", ".join(sorted({groups[g["m_PathID"]] for g in gref
                               if g["m_PathID"] in groups}))
             or "NONE -- these chains can swing through the body"))
    tot = 0
    for nm, ch in added:
        v = sum(cnt.get(b, 0) for b in ch)
        tot += v
        print("    %-24s %-54s %4d vert(s)" % (nm, " -> ".join(ch), v))
        for b in ch:
            if not cnt.get(b):
                print("        note: %r carries no vertices of its own; it "
                      "moves only what hangs below it" % b)
    print("  %d vertices now on a spring that were rigid" % tot)
    print("  stiffness %.3f  drag %.3f  gravity %.3f  radius %.4f"
          % (knob["stiff"], knob["drag"], knob["grav"], knob["radius"]))
    print("  verified on the written bytes: every new chain reads back as "
          "asked and the %d pre-existing chain(s) are unchanged" % len(before))


if __name__ == "__main__":
    main()
