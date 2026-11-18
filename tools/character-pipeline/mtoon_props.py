# -*- coding: utf-8 -*-
"""Did the MToon VALUES survive into a .yargchar, or only the shader NAME?

    python mtoon_props.py <a.yargchar> [<b.yargchar> ...]

WHY THE NAME IS NOT ENOUGH. `bundle_shaders.py` answers "what shader does this material use",
and on 2026-11-18 that check passed a character that rendered as a FLAT MAGENTA SILHOUETTE --
the bundle carried `VRM10/MToon10`, the built-in-pipeline variant, in a URP project. A bundle
can equally carry the RIGHT shader with every toon property sitting at its default, which
renders almost exactly like URP/Lit and would let "we preserved MToon" pass unchallenged.

So this reads the values. The one that decides whether anything is visibly toon at all is the
gap between `_Color` and `_ShadeColor`: MToon's shading IS that gap, and when it is zero the
character is a lit character wearing a toon shader.

Measured on our first preserved build (Aiko, all three materials):

    _ShadingToonyFactor 0.900   _ShadingShiftFactor -0.200   26 float + 6 colour properties
    _Color == _ShadeColor == (1,1,1)   delta 0.000

Both halves of that matter and they say opposite-looking things. The populated property block
is the preservation working. The zero delta is the CHARACTER having no shade colour to show --
which is why she renders correctly and still does not look toon, and why she is the wrong
subject to prove the feature on.

THE CONTROL IS THE PROPERTY COUNT, printed per material whether or not anything is found. A
material reporting zero colour and zero float properties was not read, and without that line a
failed parse and a genuinely default material print the same reassuring nothing -- which is the
exact failure that made an earlier sweep report "0 of 65 carry MToon" having read nothing.
"""
import os
import sys

import UnityPy

WANT = ["_Color", "_BaseColor", "_ShadeColor", "_RimColor", "_OutlineColor", "_MatcapColor",
        "_ShadingToonyFactor", "_ShadingShiftFactor", "_OutlineWidthFactor"]


def _pairs(entries):
    """m_Colors / m_Floats come back as dicts OR as tuples depending on the typetree."""
    out = {}
    for e in entries or []:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            k, v = e[0], e[1]
        elif isinstance(e, dict):
            k, v = e.get("first"), e.get("second")
        else:
            continue
        if isinstance(k, dict):
            k = k.get("name")
        if isinstance(k, str):
            out[k] = v
    return out


def report(path):
    print("=== %s" % os.path.splitext(os.path.basename(path))[0])
    try:
        env = UnityPy.load(path)
    except Exception as e:
        print("  LOAD FAILED: %s" % e)
        return
    seen = 0
    for obj in env.objects:
        if str(obj.type.name) != "Material":
            continue
        try:
            t = obj.read_typetree()
        except Exception as e:
            print("  material UNREADABLE: %s" % type(e).__name__)
            continue
        sp = t.get("m_SavedProperties") or {}
        cols = _pairs(sp.get("m_Colors"))
        floats = _pairs(sp.get("m_Floats"))
        seen += 1
        print("  material %s" % t.get("m_Name", "?"))
        print("    CONTROL: %d colour props, %d float props -- zeros mean the read failed, "
              "NOT that the material is plain" % (len(cols), len(floats)))
        for w in WANT:
            if w in cols and isinstance(cols[w], dict):
                c = cols[w]
                print("      %-22s (%.3f, %.3f, %.3f)"
                      % (w, c.get("r", 0), c.get("g", 0), c.get("b", 0)))
            elif w in floats:
                print("      %-22s %.3f" % (w, floats[w]))
        base = cols.get("_Color") or cols.get("_BaseColor")
        shade = cols.get("_ShadeColor")
        if isinstance(base, dict) and isinstance(shade, dict):
            d = max(abs(base.get(k, 0) - shade.get(k, 0)) for k in ("r", "g", "b"))
            print("      >> base-vs-shade max delta %.3f  %s"
                  % (d, "NO VISIBLE TOON RAMP on this material" if d < 0.02
                        else "a real shade ramp is present"))
    if seen == 0:
        print("  NO MATERIALS READ -- this result is about the probe, not about the bundle")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for p in sys.argv[1:]:
        report(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
