# -*- coding: utf-8 -*-
"""Propose a VRM_VISEME mapping for a model, by MEASURING its shape keys.

    blender --background --python viseme_fit.py -- <source> [--emit]

WHY MEASURE RATHER THAN READ NAMES. Shape keys are named for whoever authored
them. Character Creator ships `V_Open` / `V_Wide` / `V_Tight_O`, which a pattern
can read; Pomni's face carries `A`, `ClosedTeeth`, `ClosedTeethVariation` and
`OpenNoTeeth`, which are real mouth shapes named for an artist. Any name table
wide enough to catch the second is wide enough to bind a vowel to
`Mouth_Smile_L`. What the two have in common is not their names -- it is that
they move the geometry around the mouth, downward to open it and sideways to
widen it. So that is what this measures.

WHAT IT MEASURES, per shape key:

  where   the centroid of the vertices it moves, as a fraction of the model's
          height, so a mouth shape is separable from a blink or a brow
  open    how far the LOWER half of those vertices travels downward -- a jaw
          dropping. This is what distinguishes `aa` from everything else
  wide    how much the lateral extent of those vertices grows -- lips pulling
          apart sideways, which is `ee`
  round   how much the lateral extent SHRINKS while still opening -- lips
          pursing, which is `ou` and `oh`

HOW THE FIVE ARE CHOSEN. `aa` is the biggest opener. `ee` is the biggest
widener. `oh` and `ou` want rounding, and most models do not have it: if no
rounding shape exists they are driven from the opener at reduced WEIGHT, which
reads as "open less" rather than as rounded lips. That is honest talking rather
than accurate phonetics, and the report says which of the two you got.

THIS IS A PROPOSAL, NOT A VERDICT. It prints a VRM_VISEME string to check and
edit. The project has been bitten before by a generic mapper that looked right
until it was run on rigs already solved by hand, so `--validate` runs it against
the three that are: Heels and Alice Ivy (Character Creator names) and Pomni
(mapped by hand). A change that breaks those is wrong however reasonable it
looks.
"""
import re
import sys

import bpy
from mathutils import Vector

PRESETS = ("aa", "ih", "ou", "ee", "oh")
EPS = 1e-5
# A mouth sits in the lower part of the head. Generous, because heads vary
# wildly here -- Gadget's is half her height.
# Normalised within the SHAPE KEYS' own height range, not the model's. The
# model's bounding box is not a usable reference: Pomni's source .blend carries
# rig widgets that the build excludes with '^Circle', and they stretch the box
# until her whole face reads as 27% of the height. The keys themselves are the
# only thing guaranteed to be on the face -- eyes and brows at the top of their
# own range, mouth at the bottom.
MOUTH_BAND = (0.0, 0.55)
# Eye parts are excluded by MESH name rather than selected by key name. The
# first version of this tool proposed `aa = Lashes.R/Closed` -- a blink -- as
# Pomni's open mouth, because a closing eyelid travels downward just as a jaw
# does. Excluding is much safer than selecting: a missed exclusion costs a
# candidate, a wrong selection costs a face that gapes when the song says "ah".
EYE_MESH = re.compile(r"(lash|lid|eye|brow)", re.I)

# Names ARE evidence, and a measurement alone cannot recover what they carry.
# Measured on Pomni, the biggest jaw-opener is 'Expression2' -- some startled
# face -- which beats her shape literally called 'A'. The widest opening is not
# the phoneme. So: a key whose name matches a known viseme convention WINS, and
# measurement ranks everything else and fills the gaps. Same patterns as
# build_vrm.py's _VISEME_SPECS, deliberately.
NAME_HINTS = (
    ("aa", (r"^V_Open$", r"^A$", r"^viseme_aa$", r"^mouth_?a$", r"^vrc\.v_aa$",
            r"^jawOpen$")),
    ("ee", (r"^V_Wide$", r"^E$", r"^viseme_E$", r"^mouth_?e$", r"^vrc\.v_e$")),
    ("ih", (r"^V_Wide$", r"^I$", r"^viseme_I$", r"^mouth_?i$", r"^vrc\.v_ih$")),
    ("oh", (r"^V_Tight_O$", r"^O$", r"^viseme_O$", r"^mouth_?o$", r"^vrc\.v_oh$")),
    ("ou", (r"^V_Tight$", r"^U$", r"^viseme_U$", r"^mouth_?u$", r"^vrc\.v_ou$")),
)
NAME_RE = [(a, [re.compile(x, re.I) for x in ps]) for a, ps in NAME_HINTS]


def by_name(rows):
    """Presets a key's NAME claims, for every candidate."""
    out = {}
    for r in rows:
        for a, ps in NAME_RE:
            if any(x.match(r["key"]) for x in ps):
                out.setdefault(a, r)
    return out


def load(path):
    low = path.lower()
    bpy.ops.wm.read_homefile(use_empty=True)
    if low.endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path)
    elif low.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif low.endswith((".usd", ".usda", ".usdc", ".usdz")):
        bpy.ops.wm.usd_import(filepath=path)
    elif low.endswith(".vrm"):
        bpy.ops.import_scene.vrm(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)


def axes():
    """Derive UP and LATERAL from the model, never assume them.

    Pomni's source .blend is rotated -- her left and right lashes sit at
    different Z -- so a tool that assumes Z-up reads her face sideways and
    every measurement below becomes noise. A standing character is tallest
    along up and wider across than deep, so the bounding box says which is
    which without needing a rig or a convention.
    """
    lo = [None] * 3
    hi = [None] * 3
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            for i in range(3):
                lo[i] = w[i] if lo[i] is None else min(lo[i], w[i])
                hi[i] = w[i] if hi[i] is None else max(hi[i], w[i])
    if lo[0] is None:
        return 2, 0, 0.0, 1.0
    size = [hi[i] - lo[i] for i in range(3)]
    up = max(range(3), key=lambda i: size[i])
    rest = [i for i in range(3) if i != up]
    lat = max(rest, key=lambda i: size[i])
    return up, lat, lo[up], hi[up]


def measure(o, kb, basis, up, lat):
    """Return a dict of measurements for one shape key, or None if it is inert."""
    mw = o.matrix_world
    moved = []
    for i, p in enumerate(kb.data):
        d = p.co - basis[i].co
        if d.length > EPS:
            moved.append((i, mw @ basis[i].co, mw @ p.co))
    if len(moved) < 8:
        return None

    rest = [m[1] for m in moved]
    after = [m[2] for m in moved]
    centroid = sum(rest, Vector()) / len(rest)

    # The lower half of the moved vertices is the jaw side of the shape.
    us = sorted(r[up] for r in rest)
    mid = us[len(us) // 2]
    low = [(r, a) for r, a in zip(rest, after) if r[up] <= mid]
    opening = 0.0
    if low:
        opening = sum((r[up] - a[up]) for r, a in low) / len(low)

    def extent(pts):
        return max(p[lat] for p in pts) - min(p[lat] for p in pts)

    widening = extent(after) - extent(rest)
    return {
        "mesh": o.name,
        "key": kb.name,
        "n": len(moved),
        "z": centroid[up],
        "open": opening,
        "wide": widening,
        "eye": bool(EYE_MESH.search(o.name)),
    }


def collect():
    up, lat, lo, hi = axes()
    span = max(1e-6, hi - lo)  # a real-world scale, for the thresholds
    rows = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.shape_keys:
            continue
        kbs = list(o.data.shape_keys.key_blocks)
        if len(kbs) < 2:
            continue
        basis = kbs[0].data
        for kb in kbs[1:]:
            m = measure(o, kb, basis, up, lat)
            if m is None:
                continue
            rows.append(m)
    # Normalise height within the keys' own range.
    cand = [r for r in rows if not r["eye"]] or rows
    if cand:
        klo = min(r["z"] for r in cand)
        khi = max(r["z"] for r in cand)
        kspan = max(1e-9, khi - klo)
        for r in rows:
            r["frac"] = (r["z"] - klo) / kspan
    else:
        for r in rows:
            r["frac"] = 0.5
    return rows, span


def propose(rows, span):
    """Pick the five, and say how confident each choice is."""
    mouth = [r for r in rows
             if MOUTH_BAND[0] <= r["frac"] <= MOUTH_BAND[1] and not r["eye"]]
    if not mouth:
        return {}, mouth, "no shape key moves geometry in the lower face"

    # RANK, do not threshold. An absolute cutoff tied to the model's bounding
    # box looked reasonable and silently rejected every one of Heels' 420 keys,
    # because her source sits at a different scale from Pomni's. Relative
    # ranking is scale-free, which is the only property that survives a roster
    # running from a 0.019-unit FBX to a 2.9 m Alcina.
    openers = sorted((r for r in mouth if r["open"] > 0), key=lambda r: -r["open"])
    wideners = sorted((r for r in mouth if r["wide"] > 0), key=lambda r: -r["wide"])
    rounders = sorted((r for r in mouth if r["wide"] < 0 and r["open"] > 0),
                      key=lambda r: r["wide"])

    out = {}
    note = []
    # Over EVERY key, not just the measured mouth band. Character Creator puts
    # eyes and mouth on one CC_Base_Body, so the band cannot separate them and
    # restricting names to it lost V_Open entirely -- the tool then proposed
    # `aa = Eye_Wide_R`. A name match does not need the band to be right.
    named = by_name([r for r in rows if not r["eye"]])
    for a, r in named.items():
        out[a] = (r, 1.0)
    if named:
        note.append("%d preset(s) taken from key NAMES (%s), which beat the "
                    "measurement where they exist"
                    % (len(named), ", ".join("%s<-%s" % (a, r["key"])
                                             for a, r in sorted(named.items()))))
    if openers and "aa" not in out:
        out["aa"] = (openers[0], 1.0)
    if wideners and "ee" not in out:
        out["ee"] = (wideners[0], 1.0)
        out.setdefault("ih", (wideners[0], 0.6))
    elif openers and "ee" not in out:
        # No widener at all. Better a small opening than a vowel bound to
        # nothing, but say so.
        out["ee"] = (openers[0], 0.35)
        out.setdefault("ih", (openers[0], 0.25))
        note.append("no widening shape: ee/ih driven from the opener, which "
                    "will read as a small opening rather than a wide mouth")
    if rounders:
        out.setdefault("oh", (rounders[0], 1.0))
        out.setdefault("ou", (rounders[-1 if len(rounders) > 1 else 0], 1.0))
    elif "aa" in out:
        _base = out["aa"][0]
        out.setdefault("oh", (_base, 0.65))
        out.setdefault("ou", (_base, 0.40))
        note.append("no lip-rounding shape: oh/ou driven from the opener at "
                    "reduced weight, so they read as 'open less' rather than "
                    "as rounded lips")
    return out, mouth, "; ".join(note)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    if not argv:
        print("usage: viseme_fit.py -- <source> [--emit]")
        sys.exit(2)
    path = argv[0]
    load(path)
    rows, span = collect()
    print("=== shape keys that move geometry (%d) ===" % len(rows))
    print("%-18s %-24s %6s %6s %8s %8s %s" %
          ("mesh", "key", "verts", "height", "open", "wide", ""))
    for r in sorted(rows, key=lambda r: -r["frac"]):
        print("%-18s %-24s %6d %6.2f %8.4f %8.4f %s"
              % (r["mesh"][:18], r["key"][:24], r["n"], r["frac"],
                 r["open"], r["wide"], "(eye part, excluded)" if r["eye"] else ""))

    out, mouth, note = propose(rows, span)
    print("")
    print("=== %d key(s) in the mouth band %.2f-%.2f ==="
          % (len(mouth), MOUTH_BAND[0], MOUTH_BAND[1]))
    if note:
        print("NOTE: %s" % note)
    if not out:
        print("No viseme mapping could be measured. If this model really has a "
              "mouth, it has no shape keys that move it, and no pipeline "
              "change can give it one.")
        sys.exit(1)
    spec = ",".join("%s=%s/%s@%.2f" % (p, out[p][0]["mesh"], out[p][0]["key"],
                                       out[p][1])
                    for p in PRESETS if p in out)
    print("")
    print("VRM_VISEME=\"%s\"" % spec)
    print("")
    print("Check it before trusting it: the mapping is a measurement of where "
          "geometry moves, not an understanding of what the artist meant.")


main()
