"""Which VOLUME verdicts change when the closed-shell gate is counted correctly?

    blender --background --python gate_recheck.py -- <file.vrm> [min_faces]

`facing_check.py` splits a mesh into pieces by joining faces across edges shared by exactly two
faces, so pieces are SEPARATED at non-manifold edges. It then decided whether a piece is a
closed shell by counting each edge against `comp[fl[0]]` -- the component of whichever face came
first on it. A piece bounded by non-manifold edges therefore never got its own boundary into its
denominator, sailed through the 95% gate, and received a signed-volume verdict it was not
eligible for. Pomni's 168-face piece is the proof: 90.9% manifold by its own edges, admitted
anyway, and flagged INSIDE-OUT on a volume that changes by 121x with the reference point.

This runs BOTH counting rules over the same pieces and reports every piece whose GATE DECISION
differs, in both directions:

    SKIPPED->JUDGED   the old denominator was inflated by edges belonging to other pieces, so a
                      genuinely closed shell was refused a verdict it should have had
    JUDGED->SKIPPED   the old denominator was missing the piece's own boundary, so a sheet was
                      given a verdict it was never eligible for

BOTH DIRECTIONS ARE PRINTED EVEN WHEN EMPTY, because "no piece moved" is a result about the blast
radius and must not look like a sweep that failed. The volume sign is carried alongside, so a
moved gate can be read as a moved VERDICT rather than only a moved flag.

THE SECOND DIRECTION IS THE NON-CIRCULAR CONTROL. The fix was derived from Pomni, so Pomni will
always confirm it. A piece the OLD gate skipped and the NEW one admits cannot have been fitted to
her, because nothing about her case predicts it. If none exists anywhere on the roster, that is
worth saying in those words rather than leaving the fix validated only by the case that produced
it.
"""
import collections
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
SRC = args[0]
MIN_FACES = int(args[1]) if len(args) > 1 else 100
NAME = SRC.replace("\\", "/").split("/")[-1]

bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)

moved_in = []
moved_out = []
same = 0

for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    me = o.data
    mw = o.matrix_world
    n3 = mw.to_3x3()
    polys = list(me.polygons)
    if len(polys) < 100:
        continue

    # --- components, exactly as facing_check builds them -------------------------------------
    wid, weld = {}, {}
    for p in polys:
        for vi in p.vertices:
            if vi not in weld:
                co = me.vertices[vi].co
                weld[vi] = wid.setdefault(
                    (round(co.x * 1e4), round(co.y * 1e4), round(co.z * 1e4)), len(wid))
    edges = collections.defaultdict(list)
    for p in polys:
        vs = [weld[v] for v in p.vertices]
        for i in range(len(vs)):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            if a != b:
                edges[(min(a, b), max(a, b))].append(p.index)
    adj = collections.defaultdict(list)
    for fl in edges.values():
        if len(fl) == 2:
            adj[fl[0]].append(fl[1])
            adj[fl[1]].append(fl[0])
    comp = {}
    nc = 0
    for p in polys:
        if p.index in comp:
            continue
        comp[p.index] = nc
        stack = [p.index]
        while stack:
            f = stack.pop()
            for g in adj[f]:
                if g not in comp:
                    comp[g] = nc
                    stack.append(g)
        nc += 1

    # --- the two counting rules ---------------------------------------------------------------
    old = collections.defaultdict(lambda: [0, 0])
    for fl in edges.values():
        c = comp[fl[0]]
        old[c][1] += 1
        if len(fl) == 2:
            old[c][0] += 1

    new = collections.defaultdict(lambda: [0, 0])
    for fl in edges.values():
        per = collections.Counter(comp[f] for f in fl)
        for c, n in per.items():
            new[c][1] += 1
            if n == 2:
                new[c][0] += 1

    byc = collections.defaultdict(list)
    for p in polys:
        byc[comp[p.index]].append(p)

    for cid, ps in byc.items():
        if len(ps) < MIN_FACES:
            continue
        o2, ot = old[cid]
        n2, nt = new[cid]
        old_ok = ot > 0 and o2 / ot >= 0.95
        new_ok = nt > 0 and n2 / nt >= 0.95
        if old_ok == new_ok:
            same += 1
            continue

        cen = Vector((0.0, 0.0, 0.0))
        for p in ps:
            cen += mw @ p.center
        cen /= len(ps)
        vol = 0.0
        for p in ps:
            vol += p.area * ((mw @ p.center) - cen).dot((n3 @ p.normal).normalized()) / 3.0
        mats = collections.Counter(
            o.material_slots[p.material_index].material.name
            if p.material_index < len(o.material_slots) and o.material_slots[p.material_index].material
            else "?" for p in ps)
        zs = [(mw @ p.center).z for p in ps]
        row = (len(ps), o.name, mats.most_common(1)[0][0], cid,
               (o2 / ot if ot else 0.0), (n2 / nt if nt else 0.0), vol, min(zs), max(zs))
        (moved_in if new_ok else moved_out).append(row)

print("")
print("GATE %s | %d pieces unchanged | %d now SKIPPED | %d now JUDGED"
      % (NAME, same, len(moved_out), len(moved_in)))

for label, rows, note in (
        ("JUDGED->SKIPPED", moved_out,
         "a sheet was given a volume verdict it was never eligible for"),
        ("SKIPPED->JUDGED", moved_in,
         "a closed shell was refused a verdict it should have had -- THE NON-CIRCULAR CONTROL"),
):
    print("  %s (%d) -- %s" % (label, len(rows), note))
    if not rows:
        print("      none in this file")
    for n, on, mat, cid, oldr, newr, vol, zlo, zhi in sorted(rows, reverse=True):
        verdict = "INSIDE-OUT" if vol < 0 else "outward"
        print("      %-10s %-14s piece %-4d %5d faces  manifold %.1f%% -> %.1f%%  vol %+.8f  %s  z %.2f..%.2f"
              % (on[:10], mat[:14], cid, n, 100 * oldr, 100 * newr, vol, verdict, zlo, zhi))
