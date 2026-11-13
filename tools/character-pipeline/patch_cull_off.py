# -*- coding: utf-8 -*-
"""Change a NAMED material's back-face culling in the INSTALLED .yargchar.

    python patch_cull_off.py <in.yargchar> --materials "A;B" [--on] [--out X]
        [--dry-run]

Default draws the named materials DOUBLE-SIDED (`_Cull` 2 -> 0). `--on` is the
inverse (0 -> 2) and exists so a flip is reversible without a backup.

NAME THEM. DO NOT BLANKET. The exporter has said so in its own comment since
Alastor was built -- "Double-sided everywhere tints the lighting, so name them,
do not blanket" -- and on 2026-11-13 this tool was used with an `--all` flag
against twelve characters anyway, on an argument that does not hold. The flag is
gone. What follows is why, so it is not re-derived into existence.

THE ARGUMENT THAT FAILED. Every `.vrm` measured for the twelve reported
characters declared `doubleSided: true`, with not one false, while the installed
set had 398 materials culled and one not. That was read as the exporter losing a
deliberate signal. Two measurements say otherwise:

  1. THE PIPELINE DOES NOT LOSE IT. Batman's source GLB omits `doubleSided`
     (glTF defaults it false) and `Batman.vrm` omits it too -- 2 materials,
     0 true. `BatmanNoT.vrm` and `bat-regress.vrm` the same. So "every .vrm
     this pipeline writes is double-sided" was false; it was true only of the
     twelve characters looked at, and generalised from there.

  2. THE SOURCES ARE NOT DECLARING ANYTHING. Across the third-party sources on
     hand: 60 materials true, 0 false, 5 absent. A Blender glTF export writes
     `doubleSided = not use_backface_culling`, and Blender defaults that to
     off, so a model exported by someone who never touched the setting comes
     out `true`. A field that is almost always true because of a default
     upstream carries very little, and nothing like enough to flip a roster on.

An unbroken run of one value across every measurement is the signature of a
default, not of a declaration -- and the way to tell them apart is a control,
which is what Batman is here.

WHAT IS ACTUALLY TRUE. Culling does break thin single-layer geometry, and Miku's
twintails measurably come apart under it. But "this material renders wrong when
culled" has two causes and they want opposite fixes:

  - OPEN SHEETS (hair cards, a cape, a skirt panel, lashes) have no back face.
    They genuinely need `_Cull 0`, named here.
  - A CLOSED PIECE THAT IS INSIDE-OUT needs its winding fixed, not its culling
    disabled. `VRM_ORIENT_CONSISTENT` does that at build time.

Double-siding the second kind HIDES the bug rather than fixing it, and that has
already happened once on this roster: Alastor's eyes were inverted, 0% facing
the front, and the note records them as "hidden by the double-sided material".
`facing_check.py` separates the two -- a closed piece has a signed volume and an
open sheet does not -- so run it before naming anything here.

AND IT COSTS. Double-sided doubles the fragments rasterised for that material,
lights back faces with normals pointing the wrong way (the "tints the lighting"
in the exporter comment), and makes a blended material show its own interior.
On a rhythm game drawing four characters and a crowd, that is not free.
"""
import json
import os
import sys

import UnityPy


def fingerprint(env):
    out = {}
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        tt = obj.read_typetree()
        sp = tt.get("m_SavedProperties", {}) or {}
        out[tt.get("m_Name", "?")] = json.dumps({
            "floats": sorted((a, round(float(b), 6))
                             for a, b in sp.get("m_Floats", [])),
            "kw": sorted(tt.get("m_ValidKeywords") or []),
            "q": tt.get("m_CustomRenderQueue"),
            "tags": str(tt.get("stringTagMap")),
        }, sort_keys=True)
    return out


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2

    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    src = argv[0]
    out = opt("--out") or (os.path.splitext(src)[0] + ".cull0.yargchar")
    named = [x.strip() for x in (opt("--materials") or "").split(";")
             if x.strip()]
    cull_on = "--on" in argv
    want = 2.0 if cull_on else 0.0
    dry = "--dry-run" in argv
    if not named:
        print("ABORT: --materials is required. There is no --all: a blanket "
              "flip was tried on 2026-11-13 and the measurement behind it did "
              "not hold. Run facing_check.py and name the open sheets.")
        return 2

    env = UnityPy.load(src)
    before = fingerprint(env)
    missing = [n for n in named if n not in before]
    if missing:
        print("ABORT: no material named %s in %s (it has: %s)"
              % (", ".join(missing), os.path.basename(src),
                 ", ".join(sorted(before))))
        return 2

    done = []
    skipped = []
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        tt = obj.read_typetree()
        name = tt.get("m_Name", "?")
        if name not in named:
            continue
        sp = tt["m_SavedProperties"]
        fl = {a: b for a, b in sp["m_Floats"]}
        if "_Cull" not in fl:
            # An MToon material has no _Cull float at all; it carries its own
            # double-sided flag inside the VRM extension. Saying so beats
            # silently doing nothing.
            skipped.append("%s (no _Cull float -- MToon?)" % name)
            continue
        if fl.get("_Cull") == want:
            skipped.append("%s (already %s)"
                           % (name, "culled" if cull_on else "double-sided"))
            continue
        floats = []
        for pair in sp["m_Floats"]:
            k, v = pair[0], pair[1]
            nv = want if k == "_Cull" else v
            floats.append((k, nv) if isinstance(pair, tuple) else [k, nv])
        sp["m_Floats"] = floats
        obj.save_typetree(tt)
        done.append(name)

    print("  %s: %d material(s)%s"
          % ("back-face culled" if cull_on else "double-sided", len(done),
             (" -- " + ", ".join(done[:8])) if done else ""))
    if skipped:
        print("  left alone: %d (%s)" % (len(skipped), "; ".join(skipped[:4])))
    if not done:
        print("nothing to do")
        return 2
    if dry:
        print("  --dry-run: nothing written")
        return 0

    # packer="original" keeps the bundle's own compression; a plain save()
    # writes it uncompressed and quadruples the file.
    with open(out, "wb") as f:
        f.write(env.file.save(packer="original"))
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))

    after = fingerprint(UnityPy.load(out))
    changed = [n for n in before if before.get(n) != after.get(n)]
    gone = [n for n in before if n not in after]
    added = [n for n in after if n not in before]
    print("  read-back: %d material(s), %d changed, %d gone, %d added"
          % (len(after), len(changed), len(gone), len(added)))
    bad = sorted(set(changed) - set(done)) + gone + added
    if bad:
        print("  WARNING: unexpected difference on %s -- do not install this"
              % ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
