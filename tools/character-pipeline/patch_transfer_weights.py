# -*- coding: utf-8 -*-
"""patch_transfer_weights.py <yargchar> --from <donor> --to <mesh>[,<mesh>...]
                             [--out X] [--dry-run]

Give a garment the weights of the body underneath it, in the installed bundle.

THE FAULT. Jessica Rabbit's dress is two meshes, 37,310 vertices between them,
and every vertex of both is weighted -- at ONE influence -- to a single bone,
`spine`, which is her humanoid hips. It follows her hips and nothing else, so
it cannot bend with her legs, her torso or her chest: the body moves inside a
rigid shell, and her sprung breast chains swing out through cloth that is not
following them. Reported as the dress clipping through her and the dress and
the sprung parts of her body moving separately, which is exactly what that is.

WHY IT HAPPENS, since the same source will do it again. Her GLB holds the
skinned character at z 32..44 and an UNSKINNED pile at z 0..10 -- the dress
sculpt, beside the mic-stand parts. `build_vrm.py` auto-weights unrigged
meshes, but at that moment the dress is thirty units from the body and the
only bone anywhere near it is the file's own root joint, a single bone 38.6
units long running the height of the scene. Bone heat has nothing else to
choose, so the whole dress lands on it; the orphan-bone step then moves that
weight down to the hips because the root sits above the humanoid root, and the
dress arrives welded to one bone. The arithmetic closes exactly: 24,035 bodice
vertices plus the 2,769 skirt vertices the cloth rig did not claim is the
26,804 that step reports moving.

WHY THIS PATCHES RATHER THAN REBUILDS THE WEIGHTS. By the time the bundle
exists the geometry is already right: measured on her, the body's raw vertex
data spans y 0.004..1.732, the bodice 0.890..1.396 and the skirt -0.025..0.991,
all in one space and all in the correct relative places. Only the WEIGHTS are
wrong, and both weight channels live alone in their own vertex stream, so they
can be rewritten without touching a single position, normal or UV.

THE CHECK THAT MATTERS is that re-weighting moves nothing at rest. With
consistent bind poses every bone's world*bindPose is the same data->world map,
so the rest pose is independent of which bones carry a vertex -- and if that is
NOT true of this file, the transfer would shift the garment and must not
happen. So every vertex's rest position is computed before and after and the
file is kept only if the largest movement is under a tenth of a millimetre.
That is a real test: it fails loudly on a file whose bind poses disagree.
"""
import math
import os
import struct
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cloth_collide_installed import read                         # noqa: E402
from patch_springs import decode_ch, mat4, mul, trs, xform        # noqa: E402

SZ = {0: 4, 1: 2, 2: 1, 3: 1, 4: 2, 5: 2, 6: 1, 7: 1, 8: 2, 9: 2, 10: 4, 11: 4}
PACK = {0: "f", 1: "e", 8: "H", 9: "h", 10: "I", 11: "i", 6: "B", 7: "b",
        2: "B", 3: "b", 4: "H", 5: "h"}
REST_TOL = 1e-4          # metres; 0.1 mm


def die(msg):
    raise SystemExit("ABORT: %s" % msg)


def parse(argv):
    pos, donor, targets, out, dry = [], None, [], None, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dry-run":
            dry = True
        elif a in ("--from", "--to", "--out"):
            i += 1
            if i >= len(argv):
                die("%s needs a value" % a)
            if a == "--from":
                donor = argv[i]
            elif a == "--to":
                targets = [x.strip() for x in argv[i].split(",") if x.strip()]
            else:
                out = argv[i]
        elif a.startswith("--"):
            die("unknown flag %r" % a)
        else:
            pos.append(a)
        i += 1
    if len(pos) != 1 or not donor or not targets:
        die("usage: patch_transfer_weights.py <yargchar> --from <donor mesh> "
            "--to <mesh>[,<mesh>] [--out X] [--dry-run]")
    return pos[0], donor, targets, (out or pos[0]), dry


def layout(tt):
    """(stream starts, strides, channels, raw bytes, vertex count)."""
    vd = tt.get("m_VertexData") or {}
    n = vd.get("m_VertexCount") or 0
    chans = vd.get("m_Channels") or []
    raw = bytes(vd.get("m_DataSize") or b"")
    strides = {}
    for c in chans:
        if not c.get("dimension"):
            continue
        strides[c["stream"]] = strides.get(c["stream"], 0) \
            + SZ.get(c["format"], 0) * c["dimension"]
    starts, off = {}, 0
    for st in sorted(strides):
        off = (off + 15) // 16 * 16
        starts[st] = off
        off += strides[st] * n
    if off != len(raw):
        return None
    return starts, strides, chans, raw, n


def skinned(tt, r, world):
    """Rest-pose world position of every vertex, and its weights."""
    ch = decode_ch(tt, (0, 12, 13))
    bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
    bind = [mat4(m) for m in (tt.get("m_BindPose") or [])]
    if ch is None or len(bind) != len(bones) or not bones:
        return None
    V, W, I = ch[0], ch[12], ch[13]
    skin = [mul(trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
    pts = []
    for vi in range(len(V)):
        px = py = pz = 0.0
        for k in range(len(W[vi])):
            w, bi = W[vi][k], I[vi][k]
            if w > 0 and bi < len(skin):
                q = xform(skin[bi], V[vi])
                px += w * q[0]
                py += w * q[1]
                pz += w * q[2]
        pts.append((px, py, pz))
    return pts, V, W, I, bones, skin


def main():
    src, donor_name, target_names, out, dry = parse(sys.argv[1:])
    human, tf, go_tf, springs, joints, colliders, groups, world = read(src)

    env = UnityPy.load(src)
    objs = {}
    for o in env.objects:
        try:
            objs[o.path_id] = (o.type.name, o)
        except Exception:                                        # noqa: BLE001
            pass

    found = {}
    for pid, (ty, o) in objs.items():
        if ty != "SkinnedMeshRenderer":
            continue
        r = o.read_typetree()
        mp = (r.get("m_Mesh") or {}).get("m_PathID")
        if not mp or mp not in objs:
            continue
        mo = objs[mp][1]
        tt = mo.read_typetree()
        found[tt.get("m_Name")] = (o, r, mo, tt)

    if donor_name not in found:
        die("no mesh called %r; this file has %s"
            % (donor_name, sorted(found)[:10]))
    for t in target_names:
        if t not in found:
            die("no mesh called %r; this file has %s"
                % (t, sorted(found)[:10]))

    _do, dr, _dm, dtt = found[donor_name]
    got = skinned(dtt, dr, world)
    if got is None:
        die("the donor %r has no readable skin" % donor_name)
    dpts, _dV, dW, dI, dbones, _ds = got
    print("%s: donor %r, %d vertices" % (os.path.basename(src), donor_name,
                                         len(dpts)))

    CELL = 0.03
    grid = {}
    for i, p in enumerate(dpts):
        grid.setdefault((int(p[0] // CELL), int(p[1] // CELL),
                         int(p[2] // CELL)), []).append(i)

    def nearest(q):
        cx, cy, cz = (int(q[0] // CELL), int(q[1] // CELL), int(q[2] // CELL))
        best, bi, rad = 1e18, None, 1
        while rad <= 20:
            hit = False
            for dx in range(-rad, rad + 1):
                for dy in range(-rad, rad + 1):
                    for dz in range(-rad, rad + 1):
                        if rad > 1 and max(abs(dx), abs(dy), abs(dz)) != rad:
                            continue
                        for i in grid.get((cx + dx, cy + dy, cz + dz), ()):
                            p = dpts[i]
                            d = ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2
                                 + (p[2] - q[2]) ** 2)
                            if d < best:
                                best, bi, hit = d, i, True
            if bi is not None and math.sqrt(best) < rad * CELL:
                break
            rad += 1
        return bi, math.sqrt(best) if bi is not None else None

    edits = []
    for name in target_names:
        to, tr, tmo, ttt = found[name]
        got = skinned(ttt, tr, world)
        if got is None:
            die("%r has no readable skin" % name)
        tpts, tV, tW, tI, tbones, tskin = got
        lay = layout(ttt)
        if lay is None:
            die("%r: the vertex buffer does not add up; refusing to rewrite it"
                % name)
        starts, strides, chans, raw, n = lay
        wc, ic = chans[12], chans[13]
        if wc["stream"] != ic["stream"]:
            die("%r keeps its weights and indices in different streams; this "
                "tool rewrites one stream whole" % name)
        st = wc["stream"]
        own = [i for i, c in enumerate(chans)
               if c.get("dimension") and c["stream"] == st]
        if sorted(own) != [12, 13]:
            die("%r's stream %d also carries channel(s) %s, so rewriting it "
                "whole would destroy them"
                % (name, st, [i for i in own if i not in (12, 13)]))

        # ADOPT THE DONOR'S SKIN WHOLE, not just its weights.
        #
        # The first version mapped the donor's bones onto the target's own
        # bone list and kept the target's bind poses. On Jessica that moved
        # the bodice 35.7 mm at rest, and the guard below stopped it: a bind
        # pose is only interchangeable between bones when every bone's
        # world*bindPose is the same data->world map, and in a mesh that was
        # bound to ONE bone the other 161 entries have never had to be right.
        #
        # So the target takes the donor's m_Bones AND the donor's m_BindPose,
        # and then the donor's indices mean on the target exactly what they
        # mean on the donor. The two meshes' vertex data is already in one
        # space -- that is checked by the rest-pose test, which now has to
        # pass for a reason rather than by luck.
        tr["m_Bones"] = [{"m_FileID": 0, "m_PathID": b} for b in dbones]
        ttt["m_BindPose"] = list(dtt.get("m_BindPose") or [])
        tbones = list(dbones)
        tskin = [mul(trs(*world(b)), mat4(m))
                 for b, m in zip(dbones, ttt["m_BindPose"])]
        idx_of = {b: i for i, b in enumerate(tbones)}

        wfmt = PACK[wc["format"]]
        ifmt = PACK[ic["format"]]
        imax = (1 << (8 * SZ[ic["format"]])) - 1
        buf = bytearray(raw)
        base = starts[st]
        far = 0.0
        newW, newI = [], []
        for vi, q in enumerate(tpts):
            di, dist = nearest(q)
            if di is None:
                die("%r vertex %d found no donor vertex at all" % (name, vi))
            far = max(far, dist)
            ws = list(dW[di])
            bs = [idx_of[dbones[b]] if b < len(dbones) else 0
                  for b in dI[di]]
            tot = sum(w for w in ws if w > 0)
            if tot <= 0:
                die("%r: the donor vertex nearest to vertex %d carries no "
                    "weight" % (name, vi))
            ws = [w / tot for w in ws]
            for b in bs:
                if b > imax:
                    die("%r: bone index %d does not fit the file's %d-byte "
                        "index format" % (name, b, SZ[ic["format"]]))
            newW.append(tuple(ws))
            newI.append(tuple(bs))
            struct.pack_into("<" + wfmt * wc["dimension"], buf,
                             base + vi * strides[st] + wc["offset"], *ws)
            struct.pack_into("<" + ifmt * ic["dimension"], buf,
                             base + vi * strides[st] + ic["offset"], *bs)

        # the check that matters: nothing may MOVE at rest
        worst = 0.0
        for vi in range(n):
            px = py = pz = 0.0
            for k in range(len(newW[vi])):
                w, bi = newW[vi][k], newI[vi][k]
                if w > 0 and bi < len(tskin):
                    p = xform(tskin[bi], tV[vi])
                    px += w * p[0]
                    py += w * p[1]
                    pz += w * p[2]
            o0 = tpts[vi]
            worst = max(worst, math.sqrt((px - o0[0]) ** 2 + (py - o0[1]) ** 2
                                         + (pz - o0[2]) ** 2))
        inf = {}
        for ws in newW:
            k = sum(1 for w in ws if w > 1e-4)
            inf[k] = inf.get(k, 0) + 1
        used = len({b for bs, ws in zip(newI, newW)
                    for b, w in zip(bs, ws) if w > 1e-4})
        print("  %-12s %6d verts: 1 bone -> %d bones, influences %s"
              % (name, n, used, dict(sorted(inf.items()))))
        print("      furthest donor vertex %.1f mm; rest pose moved by at "
              "most %.4f mm" % (far * 1000, worst * 1000))
        if worst > REST_TOL:
            die("re-weighting %r moves it %.3f mm at rest (limit %.3f). The "
                "bind poses in this file are not consistent between bones, so "
                "the transfer would shift the garment. Nothing written."
                % (name, worst * 1000, REST_TOL * 1000))
        edits.append((to, tr, tmo, ttt, buf))

    if dry:
        print("  --dry-run: nothing written")
        return 0

    for to, tr, tmo, ttt, buf in edits:
        ttt["m_VertexData"]["m_DataSize"] = bytes(buf)
        tmo.save_typetree(ttt)
        to.save_typetree(tr)
    data = env.file.save(packer="original")

    env2 = UnityPy.load(data)
    objs2 = {}
    for o in env2.objects:
        try:
            objs2[o.path_id] = (o.type.name, o)
        except Exception:                                        # noqa: BLE001
            pass
    for pid, (ty, o) in objs2.items():
        if ty != "SkinnedMeshRenderer":
            continue
        r = o.read_typetree()
        mp = (r.get("m_Mesh") or {}).get("m_PathID")
        if not mp or mp not in objs2:
            continue
        tt = objs2[mp][1].read_typetree()
        if tt.get("m_Name") not in target_names:
            continue
        ch = decode_ch(tt, (12, 13))
        if ch is None:
            die("the written file's %r no longer decodes" % tt.get("m_Name"))
        k = max(sum(1 for w in ws if w > 1e-4) for ws in ch[12])
        if k < 2:
            die("the written file's %r still has one influence per vertex"
                % tt.get("m_Name"))
    with open(out, "wb") as fh:
        fh.write(data)
    print("  wrote %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
