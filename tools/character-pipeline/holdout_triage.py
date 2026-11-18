# -*- coding: utf-8 -*-
"""Split `part_overlap.py`'s held-out characters into SOUND and HIDING, by their materials.

    python holdout_triage.py <part_overlap.json> <installed-characters-dir>

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
    """Every material in a bundle, as (name, surface, alphaclip). Raises if it cannot be read."""
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


def main():
    if len(sys.argv) < 3 or UnityPy is None:
        print(__doc__)
        if UnityPy is None:
            print("\nUnityPy is not importable, so NOTHING was read. That is a statement about "
                  "this environment, not a clean result.")
        return 2

    run = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    chars_dir = sys.argv[2]

    held = []
    for ch in run.get("characters") or []:
        # The hold-out condition this triage is about: measurable in principle, but the
        # bone-based split produced no aux half.
        if ch.get("aux_tris", 0) == 0 and not ch.get("error") and ch.get("parts_found", 0) > 0:
            held.append(ch.get("name"))

    print("=" * 78)
    print("HELD OUT of the depth-order test for having NO AUX HALF: %d" % len(held))
    print("=" * 78)
    if not held:
        print("none -- nothing to triage")
        return 0

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
