# -*- coding: utf-8 -*-
"""How tall is each INSTALLED character, and is anything but the body setting it?

Runlist item 2 asked for this sweep and it had never been built. The defect it
looks for is Peacemaker's: his USDZ carried a SECOND figure's helmet on a
second skeleton, floating above his head, and because the builder scales a
model to its target height by its own bounding box, scaling the FILE to 1.85 m
scaled the HELMET to 1.85 m and left Peacemaker himself 1.51 m tall. Nothing
in the build log said so. Nothing in a render of him alone says so either --
he is correctly proportioned, just small, and that only reads as wrong when he
stands next to somebody else.

Two separate measurements, because they fail in different ways:

  HEIGHT      the union of every rendered mesh's bounds, against the target
              height written down in the README's per-model table. A character
              that misses its own documented target is wrong by its own recipe.

  FLOAT       a mesh that is DETACHED from the body -- its whole vertical span
              sits clear of the body's, above or below it -- and how much of
              the figure's height that mesh is adding. That is the
              floating-prop signature, and it needs no target to read.

THE FIRST VERSION OF THE FLOAT CHECK WAS THE BUG, AND ITS OUTPUT SAID SO

It measured "how far the tallest mesh clears the top of everything else",
which sounds like the same thing and is not. It flagged 12 of the 65, and the
names gave it away immediately: Judy Hopps' tallest mesh is her FACE, Lola
Bunny's is `C038_SkelMesh` -- her whole body -- and Shadow's is `RIG`. On a
character whose accessories all sit low, the tallest mesh is the character,
and the metric was measuring nothing but that. Adachi Rei scored 99%: she has
two meshes, one of them a flat sliver at her feet, so "clears the rest" was
the height of her entire body.

What Peacemaker's helmet actually did was sit ABOVE him with nothing in
between -- its lowest vertex was higher than his highest. That is a test about
DISJOINTNESS, not about rank, and it cannot fire on a body mesh, because the
body is the thing everything else is measured against.

Read from the bundle rather than from a .vrm because only 30 of the 65 still
have a .vrm, and because the bundle is the thing the game loads -- the only
version of a character a claim about an installed defect may rest on.

WHAT IS MEASURED, and why it is not the vertices

Mesh.m_LocalAABB is in the mesh's own local space, and for these exports that
space IS the model root: Peacemaker's head mesh reports a centre at y=1.535,
which is head height for a 1.85 m man rather than anything local. So the union
of the AABBs is the figure, with no transforms to compose.

That is asserted, not assumed. --strict re-derives the same bounds from
m_VertexData for every mesh and fails if the two disagree by more than a
millimetre. (UnityPy's obj.read() convenience wrapper reports verts=0 for
these bundles, which is a limit of that wrapper and not a measurement -- the
typetree carries the real vertex buffer. identify_build.py's header says the
mesh data "is not readable that way", and that is true of the wrapper and
false of the typetree.)

ONLY RENDERED MESHES COUNT. A bundle can hold a mesh no renderer references,
and an orphan cannot make a character tall. Counting one would invent the
exact defect this tool exists to find.

    python height_check_installed.py <dir-of-yargchar | file.yargchar ...>

    HEIGHT_TARGETS=path   a "Name<TAB>metres" file; without it only the float
                          half runs, and the height column has nothing to judge
    HEIGHT_FLOAT=0.02     flag a detached mesh that inflates the figure's
                          height by more than this fraction of the body
    HEIGHT_TOL=0.03       height tolerance, as a fraction of the target
    HEIGHT_VERBOSE=1      every mesh's vertical span, tallest first
"""
import os
import struct
import sys

import UnityPy

FLOAT = float(os.environ.get("HEIGHT_FLOAT", "0.02"))
TOL = float(os.environ.get("HEIGHT_TOL", "0.03"))
VERBOSE = os.environ.get("HEIGHT_VERBOSE", "") == "1"
STRICT = "--strict" in sys.argv


def vertex_bounds(tt):
    """Re-derive the Y range from the raw vertex buffer.

    This exists to CHECK m_LocalAABB, not to replace it. Position is channel 0
    of the vertex data; its format is 0 for float32 here, and anything else
    returns None rather than guessing -- a half-float read as a float gives
    plausible numbers, which is the worst possible answer for a check.
    """
    vd = tt.get("m_VertexData") or {}
    n = vd.get("m_VertexCount") or 0
    chans = vd.get("m_Channels") or []
    data = vd.get("m_DataSize")
    if not n or not chans or not data:
        return None
    pos = chans[0]
    if pos.get("format") != 0 or pos.get("dimension") != 3:
        return None
    # Stride is the sum of every channel sharing position's stream.
    SZ = {0: 4, 1: 2, 2: 2, 3: 1, 4: 1, 11: 2, 12: 2}
    stride = 0
    for c in chans:
        if c.get("stream") != pos.get("stream") or not c.get("dimension"):
            continue
        stride += SZ.get(c.get("format"), 0) * c["dimension"]
    if stride < 12:
        return None
    raw = bytes(data)
    off = pos.get("offset", 0)
    lo = hi = None
    for i in range(n):
        p = i * stride + off
        if p + 12 > len(raw):
            return None
        y = struct.unpack_from("<f", raw, p + 4)[0]
        if lo is None or y < lo:
            lo = y
        if hi is None or y > hi:
            hi = y
    return lo, hi


def measure(path):
    env = UnityPy.load(path)
    meshes, renderers = {}, []
    for obj in env.objects:
        t = obj.type.name
        if t == "Mesh":
            try:
                meshes[obj.path_id] = obj.read_typetree()
            except Exception:
                pass
        elif t in ("SkinnedMeshRenderer", "MeshRenderer"):
            try:
                renderers.append(obj.read_typetree())
            except Exception:
                pass

    used, disabled = [], 0
    for r in renderers:
        if not r.get("m_Enabled", True):
            disabled += 1
            continue
        pid = (r.get("m_Mesh") or {}).get("m_PathID")
        if pid in meshes:
            used.append(pid)

    tops = []
    for pid in sorted(set(used)):
        tt = meshes[pid]
        box = tt.get("m_LocalAABB") or {}
        c, e = box.get("m_Center"), box.get("m_Extent")
        if not c or not e:
            continue
        lo, hi = c["y"] - e["y"], c["y"] + e["y"]
        if STRICT:
            vb = vertex_bounds(tt)
            if vb and (abs(vb[0] - lo) > 0.001 or abs(vb[1] - hi) > 0.001):
                print("  ABORT %s: AABB %.4f..%.4f but vertices %.4f..%.4f"
                      % (tt.get("m_Name", "?"), lo, hi, vb[0], vb[1]))
                return None
        tops.append((hi, lo, tt.get("m_Name", "?")))

    if not tops:
        return None
    tops.sort(reverse=True)
    top = max(t[0] for t in tops)
    floor = min(t[1] for t in tops)
    # THE BODY is the mesh with the greatest vertical extent, not the tallest
    # one, and everything else is judged against it -- so the body itself can
    # never be the thing flagged, which is the whole correction above. The
    # decision lives in detach() so --selftest exercises this code and not a
    # second copy of it that is free to agree with itself.
    detached, inflation = detach(tops)
    return {
        "height": top - floor,
        "inflation": inflation,
        "detached": detached,
        "meshes": len(tops),
        "orphans": len(meshes) - len(set(used)),
        "disabled": disabled,
        "tops": tops,
    }


def detach(tops):
    """The float decision, over a list of (hi, lo, name). Shared with measure()
    so --selftest exercises the real thing rather than a copy of it."""
    body = max(tops, key=lambda t: t[0] - t[1])
    bhi, blo = body[0], body[1]
    eps = 1e-4
    growing = True
    while growing:
        growing = False
        for hi, lo, _nm in tops:
            if lo <= bhi + eps and hi >= blo - eps:
                if hi > bhi + eps:
                    bhi, growing = hi, True
                if lo < blo - eps:
                    blo, growing = lo, True
    det = [t for t in tops if t[1] > bhi + eps or t[0] < blo - eps]
    top, floor = max(t[0] for t in tops), min(t[1] for t in tops)
    fig = bhi - blo
    return det, (((top - floor) - fig) / fig if fig else 0.0)


def selftest():
    """Four shapes, and the detector must get all four right.

    Case 1 is the defect: Peacemaker as he shipped before the exclude -- his
    body 1.51 m tall with a second figure's helmet floating above his head,
    the file 1.85 m from floor to helmet. Cases 2-4 are the three shapes that
    made the FIRST version of this check flag a body mesh as a floating prop,
    and every one of them must come back clean. A detector that only ever
    passes is not distinguishable from one that cannot fail, so this runs the
    failing case first.
    """
    cases = [
        ("peacemaker-with-helmet",
         [(1.850, 1.700, "helmet_on_second_skeleton"), (1.510, 0.0, "body")],
         True),
        ("judy -- tallest mesh is her face, attached",
         [(1.050, 0.760, "Judy_Face"), (0.980, 0.0, "Judy_Cloth"),
          (1.040, 0.800, "Judy_Eyelash")],
         False),
        ("lola -- tallest mesh IS the body",
         [(1.750, 0.0, "C038_SkelMesh"), (0.400, 0.0, "shoes")],
         False),
        ("adachi -- two meshes, one a flat sliver at the feet",
         [(1.800, 0.0, "body"), (0.020, 0.0, "shadow_plane")],
         False),
    ]
    ok = True
    for name, tops, want in cases:
        det, infl = detach(sorted(tops, reverse=True))
        got = bool(det) and infl > FLOAT
        mark = "ok  " if got == want else "FAIL"
        if got != want:
            ok = False
        print("  %s %-44s detached=%-2d inflation=%+6.1f%%  expected %s"
              % (mark, name, len(det), 100 * infl,
                 "FLOAT" if want else "clean"))
    print("  selftest: %s" % ("PASS" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            files.append(a)

    targets = {}
    tf = os.environ.get("HEIGHT_TARGETS", "")
    if tf and os.path.exists(tf):
        for line in open(tf, encoding="utf-8"):
            if "\t" in line:
                k, v = line.rstrip("\n").split("\t", 1)
                try:
                    targets[k.strip()] = float(v)
                except ValueError:
                    pass
        print("targets loaded: %d" % len(targets))
    else:
        print("no HEIGHT_TARGETS file -- running the float half only")

    print("%-34s %7s %7s %8s %7s  %s"
          % ("character", "height", "target", "off", "inflat", "flags"))
    nflag = nheight = ngap = 0
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        m = measure(p)
        if m is None:
            print("%-34s   no readable rendered mesh" % name[:34])
            continue
        flags = []
        tgt = targets.get(name)
        off = ""
        if tgt:
            d = (m["height"] - tgt) / tgt
            off = "%+.1f%%" % (100 * d)
            if abs(d) > TOL:
                flags.append("HEIGHT")
                nheight += 1
        frac = m["inflation"]
        if m["detached"] and frac > FLOAT:
            flags.append("FLOAT +%.0f%% (%s)"
                         % (100 * frac, ", ".join(d[2][:24] for d in m["detached"][:2])))
            ngap += 1
        elif m["detached"]:
            flags.append("detached, no inflation (%s)" % m["detached"][0][2][:24])
        if [f for f in flags if f.startswith(("HEIGHT", "FLOAT"))]:
            nflag += 1
        print("%-34s %7.3f %7s %8s %6.1f%%  %s"
              % (name[:34], m["height"], ("%.2f" % tgt) if tgt else "-",
                 off or "-", 100 * frac, ", ".join(flags)))
        if VERBOSE:
            for hi, lo, nm in m["tops"]:
                print("        %7.3f .. %7.3f  %s" % (lo, hi, nm))

    print("\n%d character(s): %d flagged -- %d off their documented height, "
          "%d inflated by a detached mesh by over %.0f%% of the body"
          % (len(files), nflag, nheight, ngap, 100 * FLOAT))


if __name__ == "__main__":
    main()
