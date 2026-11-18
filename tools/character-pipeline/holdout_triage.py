# -*- coding: utf-8 -*-
"""Split `part_overlap.py`'s held-out characters into SOUND and HIDING, by their materials.

    python holdout_triage.py <part_overlap.json | names.txt> <installed-characters-dir>

THE FIRST ARGUMENT MAY BE A NAME LIST, and that is not a convenience. The 2026-11-18
`part_overlap.json` was read into `measurements/interior-faults-2026-11-18.md` and then deleted
with its output directory, so the ONLY surviving record of which 19 characters were held out is
that prose. A tool whose single input no longer exists cannot re-verify its own published
result, which is how a measurement quietly becomes a recollection. One name per line, `#` for
comments; the file is detected by not parsing as JSON.

THE POSITIVE CONTROL IS NOW THE TOOL'S, NOT THE OPERATOR'S. "No transparency anywhere" and "a
reader that always says no" are the same output, and the first run of this triage was only worth
anything because a human remembered to point it at a known-blended bundle first. That bundle no
longer exists. So the control is built in and taken from data that does: the roster's alpha
CUTOUTS, where the same code path reads a real `1.0` out of the same `m_Floats` dict. A reader
that finds `_AlphaClip == 1.0` on dozens of materials is demonstrably not blind to
`_Surface == 1.0`. The tool REFUSES TO REPORT A CLEAN VERDICT if that control finds nothing, and
it counts `_Surface` key PRESENCE separately, because a field that is absent reads the same as a
field that is zero.

WHY THIS EXISTS: THE HOLD-OUT CRITERION IS ON THE WRONG AXIS.

`YargCharParts.cs` splits a character into a body half (triangles dominantly weighted to a
humanoid bone) and an aux half (everything else), then looks for aux drawn in front of a nearer
body. A character whose every triangle sits on a humanoid bone has an EMPTY aux half, so the
depth-order test is held out. Nineteen of sixty-five landed there.

That reason is derived from RIGGING. The fault is a property of MATERIALS. Aiko's bug was that
`alphaMode: BLEND` does not write depth, so geometry behind her head composited over it -- and
none of that requires the hair to move. **Rigid hair weighted hard to `Head`, on a blended
material, fails in exactly the same way and is exactly as invisible to the bone-based split.**
So "held out" does not mean "rigid, therefore safe"; it means "my split had nothing to put in
the aux half", which is a statement about the split and not about the character.

THE TRIAGE, which is a read and not a rebuild:

  SOUND   the character carries NO non-depth-writing material. With nothing drawing out of
          depth order, no draw-order fault can exist on it whatever its rigging. The hold-out
          is then provably safe rather than merely unexamined.

  HIDING  it carries one or more. The hold-out is concealing a fault this probe cannot see, and
          that character needs a MATERIAL-based split rather than a bone-based one.

Read from the installed bundle, the same way `alpha_sweep_installed.py` does it:

    Material.m_SavedProperties.m_Floats   _Surface   1.0 == Transparent in URP
                                          _AlphaClip 1.0 == cutout (alpha-tested, DOES write depth)

A CUTOUT IS NOT A HAZARD HERE and is counted separately: alpha testing discards fragments but
the ones it keeps write depth normally, which is precisely why forcing Aiko's hair from BLEND to
cutout or to opaque cured her. Only `_Surface == 1` puts a material in the transparent queue.

The long-run fix this measurement argues for is to define the aux half by MATERIAL -- triangles
whose material does not write depth -- rather than by bone. That is the population the fault can
actually occur in, and it would have no hold-outs of this kind at all.
"""
import json
import os
import sys

try:
    import UnityPy
except ImportError:
    UnityPy = None


def materials_of(path):
    """Every material in a bundle, as (name, surface, alphaclip). Raises if it cannot be read.

    `surface`/`alphaclip` are None when the KEY IS ABSENT, which is a different fact from 0.0
    and the two must not be collapsed -- an absent field reads as "opaque" to any caller that
    treats a missing key as a zero.
    """
    env = UnityPy.load(path)
    out = []
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        d = obj.read_typetree()
        sp = d.get("m_SavedProperties") or {}
        fl = {k: v for k, v in (sp.get("m_Floats") or [])}
        out.append((d.get("m_Name", "?"), fl.get("_Surface"), fl.get("_AlphaClip")))
    return out


def held_names(path):
    """The held-out names, from a part_overlap.json OR a plain name list.

    Detected by whether it parses as JSON, so neither form needs a flag and a truncated or
    corrupt JSON cannot be silently read as a one-line name list.
    """
    text = open(path, "r", encoding="utf-8").read()
    try:
        run = json.loads(text)
    except ValueError:
        names = [ln.split("#")[0].strip() for ln in text.splitlines()]
        return [n for n in names if n], "name list %s" % os.path.basename(path)
    out = []
    for ch in run.get("characters") or []:
        # The hold-out condition this triage is about: measurable in principle, but the
        # bone-based split produced no aux half.
        if ch.get("aux_tris", 0) == 0 and not ch.get("error") and ch.get("parts_found", 0) > 0:
            out.append(ch.get("name"))
    return out, "part_overlap.json %s" % os.path.basename(path)


def read_control(chars_dir, skip):
    """THE BUILT-IN POSITIVE CONTROL, strongest form available.

    Returns (surface_hits, surface_chars, cutout_hits, key_present, scanned).

    THE BEST CONTROL IS THE FIELD AND VALUE ACTUALLY UNDER TEST, and on this roster it exists:
    `_Surface == 1.0` is carried by materials on several NON-held-out characters, so this code
    path can be shown finding exactly the thing whose absence it is about to report. That is
    strictly better than the fallback below, which was all this tool had when the known-blended
    control bundle was deleted -- it demonstrated the reader could pull *a* 1.0 out of
    `m_Floats`, by reading a different key.

    So the gate is: `_Surface == 1.0` found in the reference set, or failing that `_AlphaClip ==
    1.0`, or failing both, refuse. `key_present` is counted apart from any VALUE because a
    reader pointed at bundles that never carry the key reports every character opaque while
    measuring nothing at all.
    """
    surf_hits, surf_chars, cut, key_present, scanned = 0, [], 0, 0, 0
    for fn in sorted(os.listdir(chars_dir)):
        if not fn.endswith(".yargchar") or fn[:-9] in skip:
            continue
        try:
            mats = materials_of(os.path.join(chars_dir, fn))
        except Exception:
            continue
        scanned += 1
        n_surf = 0
        for _n, s, a in mats:
            if a == 1.0:
                cut += 1
            if s is not None:
                key_present += 1
            if s == 1.0:
                n_surf += 1
        surf_hits += n_surf
        if n_surf:
            surf_chars.append((fn[:-9], n_surf))
    return surf_hits, surf_chars, cut, key_present, scanned


def main():
    if len(sys.argv) < 3 or UnityPy is None:
        print(__doc__)
        if UnityPy is None:
            print("\nUnityPy is not importable, so NOTHING was read. That is a statement about "
                  "this environment, not a clean result.")
        return 2

    chars_dir = sys.argv[2]
    held, source = held_names(sys.argv[1])

    print("=" * 78)
    print("HELD OUT of the depth-order test for having NO AUX HALF: %d   (from %s)"
          % (len(held), source))
    print("=" * 78)
    if not held:
        print("none -- nothing to triage")
        return 0

    # --------------------------------------------------------------- the control, FIRST
    surf_hits, surf_chars, cut, key_present, scanned = read_control(chars_dir, set(held))
    print()
    print("POSITIVE CONTROL -- read this before the verdict, because a reader that always says")
    print("'no transparency' produces the same output as a clean roster.")
    print("  scanned %d NON-held-out bundles as the reference set" % scanned)
    print("  materials with _Surface == 1.0 (THE FIELD UNDER TEST):   %d on %d characters"
          % (surf_hits, len(surf_chars)))
    print("  materials with _AlphaClip == 1.0 (fallback control):     %d" % cut)
    print("  materials where the _Surface KEY IS PRESENT at all:      %d" % key_present)
    if key_present == 0:
        print()
        print("CONTROL FAILED. The _Surface key is ABSENT from every material read, so 'not")
        print("transparent' here means 'the field was never there' -- which is a fact about")
        print("these bundles' material format, not about their draw order. REFUSING TO TRIAGE.")
        return 1
    if surf_hits:
        print("  CONTROL PASSED, in its strongest form: this code path found _Surface == 1.0 on")
        print("  %s." % ", ".join("%s (%d)" % (n, k) for n, k in surf_chars[:6]))
        print("  So a hold-out reading zero is a fact about that character, not about the reader.")
    elif cut:
        print("  CONTROL PASSED ON THE FALLBACK ONLY: no _Surface == 1.0 exists anywhere in the")
        print("  reference set, so the reader is shown pulling a real 1.0 out of the same dict")
        print("  via _AlphaClip instead. WEAKER -- it does not exercise the field under test.")
    else:
        print()
        print("CONTROL FAILED. This code path did not read a single 1.0 out of any bundle's")
        print("m_Floats, so it has NOT been shown able to report one. Every verdict below would")
        print("be about the reader. REFUSING TO TRIAGE.")
        return 1

    sound, hiding, unread = [], [], []
    for name in sorted(held):
        path = os.path.join(chars_dir, name + ".yargchar")
        if not os.path.isfile(path):
            unread.append((name, "no bundle at %s" % path))
            continue
        try:
            mats = materials_of(path)
        except Exception as e:
            # AN UNREADABLE BUNDLE IS NOT A SAFE ONE. It goes in its own list, never in SOUND.
            unread.append((name, "%s: %s" % (type(e).__name__, e)))
            continue
        transparent = [m for m in mats if m[1] == 1.0]
        cutout = [m for m in mats if m[2] == 1.0]
        row = (name, len(mats), transparent, cutout)
        (hiding if transparent else sound).append(row)

    print()
    print("SOUND -- no material in the transparent queue, so no draw-order fault can exist")
    print("        on them whatever their rigging. These hold-outs are provably safe.")
    for name, n, _t, cut in sorted(sound):
        extra = "  (%d cutout, which DOES write depth)" % len(cut) if cut else ""
        print("  %-24s %d materials%s" % (name[:24], n, extra))
    print("  total: %d" % len(sound))

    print()
    print("HIDING -- carries non-depth-writing material(s). The bone-based hold-out is")
    print("         concealing a fault this probe cannot see. Needs a material-based split.")
    for name, n, t, _c in sorted(hiding):
        print("  %-24s %d materials, %d transparent: %s"
              % (name[:24], n, len(t), ", ".join(m[0] for m in t)[:60]))
    print("  total: %d" % len(hiding))

    if unread:
        print()
        print("COULD NOT READ -- these are NOT sound, they are unknown:")
        for name, why in unread:
            print("  %-24s %s" % (name[:24], why))
        print("  total: %d" % len(unread))

    print()
    print("%d of %d hold-outs are provably safe; %d conceal a possible fault; %d unknown."
          % (len(sound), len(held), len(hiding), len(unread)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
