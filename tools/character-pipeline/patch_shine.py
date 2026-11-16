# -*- coding: utf-8 -*-
"""Turn URP's default shine OFF in an installed .yargchar, in place.

    python patch_shine.py <in.yargchar> [material;material|*] [--smoothness S]
        [--out X] [--dry-run]

The same change the exporter's `YARG_NO_SHINE_MATERIALS` makes, for the bundles
that will not be rebuilt: `_Smoothness`, `_Metallic`, `_SpecularHighlights` and
`_EnvironmentReflections` to zero, plus the two keywords
`_SPECULARHIGHLIGHTS_OFF` and `_ENVIRONMENTREFLECTIONS_OFF`. THE KEYWORDS ARE
THE PART THAT MATTERS at runtime -- URP/Lit branches on them and the floats are
what the material inspector uses to set them, so a patch that wrote only the
floats would look right in a dump and change nothing in the game.

Alastor is the live reference for the target state, the one character of 65
built with the switch on, and his values are what this writes.

Sophia, reported 2026-11-15 as shiny, is the reason it exists -- and the
measurement behind her is worth stating because it changes what the fix means.
Her material state is NOT unusual. She is one material, URP/Lit, `_Smoothness`
0.50 with specular highlights and sky reflections on, one base map and nothing
else: no normal map, no metallic/gloss map. That 0.50 is URP/Lit's OWN DEFAULT,
and **27 of the 65 installed characters are in exactly that state**. Her albedo
is not an outlier either (12.7% of it above 0.80 luminance, against Gwen
Stacy's 79%), and her base map is sRGB like all 57 that have one.

So the shine is not a defect of hers; it is the pipeline's default, and she is
the character on whom it shows, because a uniform plastic specular over
photoscanned skin and denim reads as wrong in a way it does not on Shrek or
Mickey Mouse. That is a judgement about appearance, and the project has already
made it once for Alastor and written it down. It is applied here per character
on report, NOT swept across the 27: smoothness 0 is matte, the editor is
recorded as a poor guide to how the shine looks in game, and blanketing a
roster on the strength of a tool default is the mistake a previous session
nearly made with `doubleSided`.

`--smoothness S` writes S instead of 0 if matte skin turns out to look dead;
the keywords still go on, since specular and reflections are the sky tint.

Verification is a full read-back, as in patch_springs.py: every object's state
is fingerprinted before and after, and anything differing that was not named is
a reason NOT to install the result.
"""
import os
import sys

import UnityPy

from patch_springs import fingerprint

FLOATS = ("_Smoothness", "_Metallic", "_SpecularHighlights",
          "_EnvironmentReflections")
KEYWORDS = ("_SPECULARHIGHLIGHTS_OFF", "_ENVIRONMENTREFLECTIONS_OFF")
EPS = 1e-6


def main():
    # Walked rather than searched, so that a flag's VALUE can never be
    # mistaken for a positional argument -- `--smoothness 0.2` used to leave
    # "0.2" in the positional list, where it became the material filter.
    args = sys.argv[1:]
    dry, out, smooth, rest = False, None, 0.0, []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dry-run":
            dry = True
        elif a == "--out" and i + 1 < len(args):
            i += 1
            out = args[i]
        elif a == "--smoothness" and i + 1 < len(args):
            i += 1
            smooth = float(args[i])
        elif a.startswith("--"):
            print("unknown option %r" % a)
            return 2
        else:
            rest.append(a)
        i += 1
    if not rest:
        print(__doc__)
        return 2
    src = rest[0]
    want = set(rest[1].split(";")) if len(rest) > 1 else {"*"}
    out = out or src
    target = dict((k, 0.0) for k in FLOATS)
    target["_Smoothness"] = smooth

    env = UnityPy.load(src)
    before = fingerprint(env)
    done, skipped, seen = [], [], 0
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        seen += 1
        tt = obj.read_typetree()
        nm = tt.get("m_Name") or "?"
        if "*" not in want and nm not in want:
            continue
        sp = tt.get("m_SavedProperties") or {}
        floats = sp.get("m_Floats") or []
        # m_ValidKeywords is what the URP shader branches on in this Unity
        # version; m_ShaderKeywords is the older field and is carried along
        # when it exists, so the two cannot disagree.
        kwf = ("m_ValidKeywords" if "m_ValidKeywords" in tt
               else "m_ShaderKeywords")
        kw = list(tt.get(kwf) or [])
        changes = []
        newfl = []
        for a, b in floats:
            if a in target and abs(float(b) - target[a]) > EPS:
                changes.append("%s %.3f->%.3f" % (a, float(b), target[a]))
                newfl.append((a, target[a]))
            else:
                newfl.append((a, b))
        have = set(a for a, _b in newfl)
        for a in sorted(target):
            if a not in have:
                changes.append("%s (absent)->%.3f" % (a, target[a]))
                newfl.append((a, target[a]))
        addkw = [k for k in KEYWORDS if k not in kw]
        if addkw:
            changes.append("keywords +%s" % ",".join(addkw))
            kw = sorted(kw + addkw)
        if not changes:
            skipped.append(nm)
            continue
        sp["m_Floats"] = newfl
        tt["m_SavedProperties"] = sp
        tt[kwf] = kw
        if isinstance(tt.get("m_ShaderKeywords"), str):
            # the legacy field is a space-joined string on some versions
            tt["m_ShaderKeywords"] = " ".join(kw)
        obj.save_typetree(tt)
        done.append((nm, changes))

    print("%s: %d material(s), %d named by %r"
          % (os.path.basename(src), seen,
             len(done) + len(skipped), ";".join(sorted(want))))
    for nm, changes in done:
        print("  %-26s %s" % (nm[:26], "; ".join(changes)))
    for nm in skipped:
        print("  %-26s already flat" % nm[:26])
    if not done:
        print("nothing to do")
        return 2
    if dry:
        print("  --dry-run: nothing written")
        return 0

    data = env.file.save(packer="original")
    after = fingerprint(UnityPy.load(data))
    changed = [k for k in before if before.get(k) != after.get(k)]
    gone = [k for k in before if k not in after]
    added = [k for k in after if k not in before]
    expect = len(done)
    print("  read-back: %d object(s) readable, %d changed (expected %d), "
          "%d gone, %d added" % (len(after), len(changed), expect, len(gone),
                                 len(added)))
    for k in sorted(changed):
        print("    %s" % k)
    if len(changed) != expect or gone or added:
        print("  WARNING: the read-back does not match what was asked for -- "
              "nothing was written")
        return 1
    with open(out, "wb") as f:
        f.write(data)
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
