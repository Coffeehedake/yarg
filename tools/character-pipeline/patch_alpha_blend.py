# -*- coding: utf-8 -*-
"""Turn a cutout material into a real alpha blend, in the INSTALLED .yargchar.

WHY THIS EXISTS RATHER THAN A REBUILD

`YargCharExporter.cs` used to give `_AlphaClip` to both `TransparentCutout`
and `Transparent`, so every authored alpha blend in the project shipped as a
hard threshold at 0.5. That is fixed in the exporter, and the proper remedy is
to rebuild the affected characters. For these six it is not available:

  * Sayuri, Alice Ivy and Gordon Freeman have NO source archive and NO `.vrm`
    on this machine. The archives lived in a session scratchpad that is gone.
  * Heels, Ariel and Alcina Dimitrescu have a `.vrm`, and all three are OLDER
    than what is installed. Measured with `identify_build.py`: Heels 84.6% and
    Ariel 89.7% name overlap with 0 length and 0 rotation mismatches, which is
    the signature of the same rig MINUS the ~20 spring bones the 11-11 chest
    rig added; Alcina's reads MATCH on the rig and still carries none of the
    two cutouts her 11-12 rebuild added. Exporting any of them would undo a
    newer fix to apply an older one.
  * And the bundle cannot be rebuilt through Unity: `BackgroundHelper.Export`
    on a prefab loaded from a bundle writes a 2,552-byte shell with no meshes.
    See `docs/character-models.md`.

So the change is made where the defect is: the two dozen numbers in the
installed material that say "threshold this" instead of "blend this". UnityPy
rewrites the serialized file directly, which is a different mechanism from
Unity's bundle builder and does not have its problem -- nothing needs an asset
path, because nothing is being rebuilt.

**That `identify_build.py` says MATCH for Alcina while her materials plainly
differ is worth keeping.** It compares the RIG -- names, bone lengths, rotation
angles -- and says so in its own header. A MATCH means "the same skeleton", not
"the same build". Her two cutouts are the counter-example.

WHAT IS CHANGED, per material

    _Surface            0 -> 1        opaque -> transparent
    _AlphaClip          1 -> 0        stop thresholding
    _AlphaToMask        1 -> 0        alpha-to-coverage is for cutouts
    _SrcBlend           1 -> 5        One -> SrcAlpha
    _DstBlend           0 -> 10       Zero -> OneMinusSrcAlpha
    _DstBlendAlpha      0 -> 10
    _ZWrite             1 -> 0        a blend must not write depth
    m_CustomRenderQueue 2450 -> 3000  after everything opaque
    m_ValidKeywords     -_ALPHATEST_ON  +_SURFACE_TYPE_TRANSPARENT
    stringTagMap        RenderType: TransparentCutout -> Transparent

The blend itself comes from the render state -- the shader's `Blend [_SrcBlend]
[_DstBlend]` and `ZWrite [_ZWrite]` read those floats -- and from `clip()` no
longer running. The keyword is set for consistency and is the one part that may
be inert: shader variants are stripped at build time, and if the bundle's copy
of URP/Lit has no `_SURFACE_TYPE_TRANSPARENT` variant Unity falls back to one
it has. **That is exactly why this has to be judged by a render and not by the
numbers coming back correct.**

    python patch_alpha_blend.py <file.yargchar> --out <new.yargchar> [options]

    --auto              choose the materials by measurement (below)
    --materials "A;B"   choose them by name
    --loss 0.20         with --auto: act on a cutout that loses more than this
                        share of its INK to the threshold
    --mode blend|cutoff what to do about it. Default `cutoff`. READ THE NEXT
                        SECTION BEFORE USING `blend`: it is measured not to
                        work on an already-built bundle.
    --keep 0.90         with `--mode cutoff`: lower _Cutoff until this share of
                        the ink survives the threshold
    --dry-run           say what would change and write nothing

`blend` DOES NOT WORK ON AN INSTALLED BUNDLE, AND THE RENDER IS WHY

Every number came back right. The material reads `_Surface 1`, `_AlphaClip 0`,
SrcAlpha/OneMinusSrcAlpha, `_ZWrite 0`, queue 3000, `RenderType Transparent`,
`_SURFACE_TYPE_TRANSPARENT` in its keywords -- and that keyword is in the
bundle's own copy of URP/Lit, so it is not obviously missing. The read-back
proved the other six of Gordon's materials byte-identical, and his clips,
controller, 52 humanoid bones, 30 fingers, 4 meshes, 5/5 visemes and 1.800 m
height all survived unchanged.

Rendered on the real podium, his lens went from a mostly-clipped pane you can
see his eyes through to **a solid opaque white rectangle covering both eyes**.
Worse than the defect. The leading explanation is that the variant carrying
`_SURFACE_TYPE_TRANSPARENT` was never compiled into this bundle -- no material
used it at build time -- and URP's `Alpha()` forces `alpha = 1.0` whenever that
keyword is not defined, so the patch removed the clipping and got nothing in
its place. The keyword appearing in `m_KeywordNames` does not contradict that:
that is the shader's keyword table, not its list of compiled variants.

So the blend fix belongs in the EXPORTER, where the shader is compiled with a
transparent material present, and a rebuild is the only way to get it. `blend`
is kept here because the measurement is worth being able to repeat.

`cutoff` is the mode that works on a bundle, because it changes nothing the
shader has to have a variant for: `_ALPHATEST_ON` stays on, the same compiled
path keeps running, and only the float it compares against moves. It cannot
give a feathered edge -- the result is still a hard cut -- but for an eyelash
losing 98.7% of itself to a 0.5 threshold, a hard-edged lash is the difference
between a lash and nothing.

HOW --auto DECIDES, and why it is not the two-valued test

The obvious rule is "flip it if the alpha is not a two-valued mask", and it
gets Alcina wrong. Her `CILIOS` eyelash map is 87.3% fully clear and 0.4% fully
solid, so clear+solid = 0.877 and it passes any sensible two-valued test -- yet
96% of it is below the 0.5 threshold, because the lashes themselves are
feathered and almost none of them is solid. The test that matters is not what
the texture looks like overall, it is **how much of the ink the threshold
throws away**:

    ink  = texels that are not fully clear
    lost = ink texels below _Cutoff
    flip if lost/ink > --loss

That leaves alone the cutouts where the threshold costs nothing -- Sayuri's
`Cloth` (0% lost), Alice Ivy's four hair materials (1%), both Bikinis -- which
matters, because turning a large nearly-opaque surface into a depth-writing-off
blend buys a sorting artifact in exchange for nothing.

THE LOSS RULE IS THE ONLY RULE, AND A SECOND ONE HAD TO BE WITHDRAWN

A "pane" rule looked obviously right alongside it: a texture with essentially
no extremes anywhere (clear + solid < 2%) is never a mask, which is exactly
how `build_vrm.py`'s own comment describes Gordon's lens. Run against the set,
it picked up **Alice Ivy's four hair materials** -- 99.8% of each map is
between the extremes -- and flipping those would have been a regression, not a
fix. Their alpha sits mostly just ABOVE the cutoff, so as a cutout the hair
draws solid and loses 1% of its ink at the edges; as a blend every one of those
mid values becomes real translucency and her scalp shows through her hair.

That is the thing to hold on to about this whole operation: **turning a cutout
into a blend makes everything between the extremes semi-transparent.** Where
the mid values are a feathered edge being destroyed, that is the fix. Where
they are antialiasing on an otherwise solid surface, it is a new defect. The
loss rule separates those two and the pane rule does not -- and the panes that
genuinely need blending (a lens, a cornea, a tear line) are below the cutoff
anyway, so the loss rule catches them for the right reason: 100% of their ink
is being thrown away.
"""
import io
import json
import os
import sys

import numpy as np
import UnityPy

# Shared with the sweep on purpose, so the two can never disagree about what a
# material's alpha is doing.
from alpha_sweep_installed import stats

BLEND_FLOATS = {
    "_Surface": 1.0,
    "_AlphaClip": 0.0,
    "_AlphaToMask": 0.0,
    "_SrcBlend": 5.0,          # UnityEngine.Rendering.BlendMode.SrcAlpha
    "_DstBlend": 10.0,         # OneMinusSrcAlpha
    "_SrcBlendAlpha": 1.0,     # One
    "_DstBlendAlpha": 10.0,    # OneMinusSrcAlpha
    "_ZWrite": 0.0,
}


def material_rows(env):
    """Every material, with its floats, its base map and that map's alpha."""
    tex = {o.path_id: o for o in env.objects if o.type.name == "Texture2D"}
    rows = []
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        tt = obj.read_typetree()
        sp = tt.get("m_SavedProperties", {}) or {}
        fl = {a: b for a, b in sp.get("m_Floats", [])}
        tv = {a: (b.get("m_Texture") or {}).get("m_PathID")
              for a, b in sp.get("m_TexEnvs", [])}
        pid = tv.get("_BaseMap") or tv.get("_MainTex")
        s = None
        if pid in tex:
            try:
                s = stats(tex[pid].read().image)
            except Exception:
                s = None
        rows.append({"obj": obj, "tt": tt, "name": tt.get("m_Name", "?"),
                     "floats": fl, "stats": s})
    return rows


def should_flip(row, loss):
    """Measurement, and the reason, as a string -- or None to leave it alone."""
    fl, s = row["floats"], row["stats"]
    if fl.get("_AlphaClip") != 1.0:
        return None
    if s is None:
        return None
    cut = fl.get("_Cutoff", 0.5)
    a = s["a"]
    ink = a >= 0.02
    nink = int(ink.sum())
    if not nink:
        return None
    lost = float((a[ink] < cut).mean())
    if lost > loss:
        return ("the threshold throws away %.1f%% of the ink (%.1f%% of the "
                "whole map is clear, %.1f%% is between the extremes)"
                % (100 * lost, 100 * s["clear"], 100 * s["mid"]))
    return None


def lower_cutoff(row, keep, absolute=None):
    """Move _Cutoff down until `keep` of the ink survives it.

    The chosen value is the (1-keep) quantile of the ink's alpha, clamped to a
    floor: a cutoff at or below 0.02 is not a cutout any more, it is an opaque
    card with the fully-clear texels still punched out, and for a hair atlas
    that is the whole card.
    """
    a = row["stats"]["a"]
    ink = a[a >= 0.02]
    if not ink.size:
        return None
    import numpy as _np
    val = (absolute if absolute is not None
           else float(_np.quantile(ink, max(0.0, 1.0 - keep))))
    val = max(0.03, min(0.5, val))
    # A CUTOFF MAY NEVER ERASE THE MATERIAL. --cutoff-to is one number applied
    # to several materials, and a material whose alpha never reaches it draws
    # nothing at all -- which is the defect this tool exists to undo, arrived
    # at from the other side. Heels' tear line is the case: its alpha tops out
    # around 0.05, so the 0.16 that suits her eyelash and her hair would
    # delete it. Capped at 90% of the material's own maximum, and the caller
    # is told when the cap bit.
    hi = float(a.max())
    capped = False
    if val > hi * 0.9:
        val, capped = max(0.03, hi * 0.9), True
    row["_capped"] = capped
    tt = row["tt"]
    sp = tt["m_SavedProperties"]
    floats = []
    for pair in sp["m_Floats"]:
        k, v = pair[0], pair[1]
        nv = val if k == "_Cutoff" else v
        floats.append((k, nv) if isinstance(pair, tuple) else [k, nv])
    sp["m_Floats"] = floats
    row["obj"].save_typetree(tt)
    return val


def flip(row):
    """Rewrite one material's render state, preserving each container's type.

    The typetree hands pairs back as tuples in some places and lists in
    others, and UnityPy writes back what it is given -- so each pair is rebuilt
    as whatever it already was rather than normalised to one shape.
    """
    tt = row["tt"]
    sp = tt["m_SavedProperties"]
    floats = []
    for pair in sp["m_Floats"]:
        k, v = pair[0], pair[1]
        nv = BLEND_FLOATS.get(k, v)
        floats.append((k, nv) if isinstance(pair, tuple) else [k, nv])
    sp["m_Floats"] = floats

    kw = [k for k in (tt.get("m_ValidKeywords") or []) if k != "_ALPHATEST_ON"]
    if "_SURFACE_TYPE_TRANSPARENT" not in kw:
        kw.append("_SURFACE_TYPE_TRANSPARENT")
    tt["m_ValidKeywords"] = kw
    tt["m_CustomRenderQueue"] = 3000

    tags = tt.get("stringTagMap")
    if tags:
        newtags = []
        for pair in tags:
            k, v = pair[0], pair[1]
            if k == "RenderType" and v == "TransparentCutout":
                v = "Transparent"
            newtags.append((k, v) if isinstance(pair, tuple) else [k, v])
        tt["stringTagMap"] = newtags
    row["obj"].save_typetree(tt)


def describe(env):
    """A fingerprint of everything, so the read-back can prove what did NOT
    change. A write that reports success says nothing about what it wrote."""
    by_type, mats = {}, {}
    for o in env.objects:
        by_type[o.type.name] = by_type.get(o.type.name, 0) + 1
        if o.type.name == "Material":
            tt = o.read_typetree()
            mats[tt.get("m_Name", "?")] = json.dumps({
                "f": sorted((a, round(float(b), 6))
                            for a, b in tt["m_SavedProperties"]["m_Floats"]),
                "kw": sorted(tt.get("m_ValidKeywords") or []),
                "q": tt.get("m_CustomRenderQueue"),
                "tags": str(tt.get("stringTagMap")),
            }, sort_keys=True)
    return by_type, mats


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2

    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    src = argv[0]
    out = opt("--out") or (os.path.splitext(src)[0] + ".blend-patched.yargchar")
    loss = float(opt("--loss", "0.20"))
    named = [x.strip() for x in (opt("--materials") or "").split(";") if x.strip()]
    auto = "--auto" in argv
    dry = "--dry-run" in argv
    mode = opt("--mode", "cutoff")
    keep = float(opt("--keep", "0.90"))
    # An absolute cutoff, instead of a share of the ink to keep.
    #
    # Measured on Heels: her eyelash wanted --keep 0.45 and her two hair
    # materials wanted 0.90, and those land at 0.165 and 0.157 -- the same
    # number from opposite ends. A share of the ink is the right way to
    # DISCOVER a value; once found, the value itself travels better between
    # materials than the share does. Rendered at 0.16 her lash is a fine dark
    # line and her hair is fuller; at the 0.039 that --keep 0.90 chose for the
    # lash alone, the faint fringe draws at full opacity and reads as a heavy
    # red rim around the eye. One character is one data point, so this is an
    # option and not a default.
    cutoff_to = opt("--cutoff-to")
    cutoff_to = float(cutoff_to) if cutoff_to else None
    if mode not in ("blend", "cutoff"):
        print("ABORT: --mode must be blend or cutoff")
        return 2
    if not auto and not named:
        print("ABORT: pass --auto or --materials. Refusing to guess.")
        return 2

    env = UnityPy.load(src)
    before_types, before_mats = describe(env)
    rows = material_rows(env)
    print("%s: %d materials" % (os.path.basename(src), len(rows)))

    chosen = []
    for r in rows:
        if named:
            if r["name"] in named:
                chosen.append((r, "named on the command line"))
        else:
            why = should_flip(r, loss)
            if why:
                chosen.append((r, why))
    if not chosen:
        print("  nothing to change")
        return 0
    for r, why in chosen:
        print("  %-24s %s: %s"
              % (r["name"][:24],
                 "cutout -> blend" if mode == "blend" else "cutoff too high",
                 why))
    if dry:
        print("  --dry-run, nothing written")
        return 0

    picked = {}
    for r, _why in chosen:
        if mode == "blend":
            flip(r)
        else:
            val = lower_cutoff(r, keep, cutoff_to)
            if val is None:
                print("  ABORT: %s has no ink to keep" % r["name"])
                return 1
            picked[r["name"]] = val
            # The OLD value, read from the material, not the 0.5 default --
            # these tools chain, and a second pass over an already-lowered
            # cutout printed "0.50 -> 0.165" when it was really 0.039 -> 0.165.
            a0 = r["stats"]["a"]
            ink0 = a0[a0 >= 0.02]
            kept = float((ink0 >= val).mean()) if ink0.size else 0.0
            print("  %-24s _Cutoff %.3f -> %.3f (keeps %.0f%% of the ink)%s"
                  % (r["name"][:24], r["floats"].get("_Cutoff", 0.5), val,
                     100 * kept,
                     "  [capped: its alpha peaks at %.3f]" % r["stats"]["max"]
                     if r.get("_capped") else ""))
    data = env.file.save(packer="original")
    tmp = out + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)

    # READ IT BACK. The patch is only done when the file on disk says so, and
    # when everything that was NOT targeted is provably untouched.
    #
    # The bytes are read off the disk and parsed from memory rather than
    # loading the path: UnityPy keeps the file it loads OPEN, and on Windows
    # that made the move fail with "being used by another process" after the
    # verification had already passed -- a successful patch reported as a
    # crash. Reading the file and parsing the buffer verifies the same bytes
    # and holds no handle.
    env2 = UnityPy.load(io.BytesIO(open(tmp, "rb").read()))
    after_types, after_mats = describe(env2)
    ok = True
    if before_types != after_types:
        print("  ABORT: object counts changed: %s -> %s"
              % (before_types, after_types))
        ok = False
    want = {r["name"] for r, _ in chosen}
    for name, sig in before_mats.items():
        changed = after_mats.get(name) != sig
        if name in want and not changed:
            print("  ABORT: %s was targeted and did not change" % name)
            ok = False
        if name not in want and changed:
            print("  ABORT: %s changed and was not targeted" % name)
            ok = False
    for name in want:
        fl = {a: b for a, b in
              json.loads(after_mats.get(name, "{}")).get("f", [])} if name in after_mats else {}
        if mode == "blend":
            if fl.get("_Surface") != 1.0 or fl.get("_AlphaClip") != 0.0:
                print("  ABORT: %s did not come back as a blend (%s)" % (name, fl))
                ok = False
        else:
            # The cutout path must still be the cutout path -- the whole point
            # of this mode is that no shader variant changes.
            if fl.get("_AlphaClip") != 1.0 or fl.get("_Surface") != 0.0:
                print("  ABORT: %s stopped being a cutout (%s)" % (name, fl))
                ok = False
            if abs(fl.get("_Cutoff", -1) - picked[name]) > 1e-6:
                print("  ABORT: %s cutoff came back %s, wanted %.3f"
                      % (name, fl.get("_Cutoff"), picked[name]))
                ok = False
    if not ok:
        os.remove(tmp)
        print("  nothing written")
        return 1

    os.replace(tmp, out)
    print("  wrote %s (%d bytes, original %d) -- %d material(s) flipped, "
          "%d verified unchanged"
          % (out, os.path.getsize(out), os.path.getsize(src), len(want),
             len(before_mats) - len(want)))
    if mode == "blend":
        print("  WARNING: `blend` is MEASURED NOT TO WORK on an installed "
              "bundle -- Gordon's lens came back a solid white pane. See the "
              "header. Render before installing, and expect to discard this.")
    else:
        print("  Render before installing. The edge will be hard, not "
              "feathered; what this buys is the geometry existing at all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
