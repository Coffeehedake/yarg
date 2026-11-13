# -*- coding: utf-8 -*-
"""Turn an OPAQUE material into a cutout, in the INSTALLED .yargchar.

    python patch_alpha_cutout.py <in.yargchar> --materials "Shrek_1" [--out X]
        [--cutoff 0.5] [--dry-run]

WHY THIS AND NOT A REBUILD. Shrek's `t_Shrek_alpha_c` is a real opacity map --
40.8% clear and 0.0% mid-tones under its own UVs, on a 238-vertex card, and
honouring it gives his tunic the ragged hem it should have. `honour_alpha.py`
produces exactly that in a `.vrm`. The trouble is what else comes with it: a
Blender round trip, and Shrek has never had one. Measured against his installed
bundle, the round-tripped file differs on **60 bone orientations** at arbitrary
angles -- 5, 7, 11, 12, 15 degrees and up -- with every bone POSITION identical.

That is not the documented benign signature. A round trip that normalises bone
ROLL produces exact 90s and 180s on bones whose roll is arbitrary, which is
what Sayuri's 25 and Jessica Rabbit's 31 were. A spread across the whole range
is a different thing, and trading a verified-identical rig for a frayed hem is
not a trade worth making on a character nobody can check in game today.

So change the one material instead. A bundle cannot be REBUILT by Unity --
`BackgroundHelper.Export` on a prefab loaded from a bundle writes a 2,552-byte
shell -- but it CAN be rewritten by UnityPy, which edits the serialized file in
place. `patch_alpha_blend.py` does the opposite conversion the same way and
this is its sibling.

THE STATE IS COPIED, NOT INVENTED. Every value below was read out of a material
that is already a working cutout in an installed bundle (Heels' `Heels_17`,
her high heels). Writing what the pipeline itself produces is the only way to
be sure the result is the same kind of object:

    _AlphaClip            0 -> 1
    _AlphaToMask          - -> 1
    m_CustomRenderQueue  -1 -> 2450
    m_ValidKeywords          +_ALPHATEST_ON
    stringTagMap             RenderType: TransparentCutout

`_Surface` 0, `_SrcBlend` 1, `_DstBlend` 0, `_ZWrite` 1 and `_Cutoff` 0.5 are
already right on an opaque material and are left alone -- a cutout IS an opaque
surface that clips, which is exactly why it has none of a blend's sorting cost.

IT PRINTS A FINGERPRINT OF EVERY OTHER MATERIAL BEFORE AND AFTER, because a
write that reports success says nothing about what it wrote.
"""
import json
import os
import shutil
import sys

import UnityPy

# Read from Heels_17, a working cutout in an installed bundle. Do not edit
# these to taste; re-measure a real cutout and copy it again.
CUTOUT_FLOATS = {
    "_AlphaClip": 1.0,
    "_AlphaToMask": 1.0,
}
CUTOUT_QUEUE = 2450
CUTOUT_KEYWORD = "_ALPHATEST_ON"
CUTOUT_TAG = ("RenderType", "TransparentCutout")


def fingerprint(env):
    """Everything about every material, so the read-back can prove what did
    NOT change."""
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


def patch(tt, cutoff):
    sp = tt["m_SavedProperties"]
    floats = []
    seen = set()
    for pair in sp["m_Floats"]:
        k, v = pair[0], pair[1]
        seen.add(k)
        nv = CUTOUT_FLOATS.get(k, v)
        if k == "_Cutoff":
            nv = cutoff
        floats.append((k, nv) if isinstance(pair, tuple) else [k, nv])
    # A property the material does not carry has to be ADDED, not skipped:
    # _AlphaToMask is absent on an opaque URP/Lit material and present at 1.0
    # on every cutout, and leaving it out is a cutout that does not anti-alias.
    for k, v in CUTOUT_FLOATS.items():
        if k not in seen:
            floats.append([k, v])
    sp["m_Floats"] = floats

    kw = list(tt.get("m_ValidKeywords") or [])
    if CUTOUT_KEYWORD not in kw:
        kw.append(CUTOUT_KEYWORD)
    kw = [k for k in kw if k != "_SURFACE_TYPE_TRANSPARENT"]
    tt["m_ValidKeywords"] = sorted(kw)
    tt["m_CustomRenderQueue"] = CUTOUT_QUEUE

    tags = list(tt.get("stringTagMap") or [])
    tags = [t for t in tags if t[0] != "RenderType"]
    tags.append(list(CUTOUT_TAG))
    tt["stringTagMap"] = tags
    return tt


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2

    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    src = argv[0]
    out = opt("--out") or (os.path.splitext(src)[0] + ".cutout.yargchar")
    cutoff = float(opt("--cutoff", "0.5"))
    named = [x.strip() for x in (opt("--materials") or "").split(";")
             if x.strip()]
    dry = "--dry-run" in argv
    if not named:
        print("ABORT: --materials is required. This tool does not guess which "
              "material should become a cutout -- alpha_sweep_installed.py "
              "names the candidates and only a render settles them.")
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
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        tt = obj.read_typetree()
        if tt.get("m_Name") not in named:
            continue
        fl = {a: b for a, b in tt.get("m_SavedProperties", {})
              .get("m_Floats", [])}
        if fl.get("_AlphaClip") == 1.0:
            print("  %s is already a cutout -- left alone" % tt["m_Name"])
            continue
        if fl.get("_Surface") == 1.0:
            print("ABORT: %s is a BLEND, not opaque. Turning a blend into a "
                  "cutout is a different decision and this tool will not make "
                  "it quietly." % tt["m_Name"])
            return 2
        obj.save_typetree(patch(tt, cutoff))
        done.append(tt["m_Name"])

    if not done:
        print("nothing to do")
        return 2
    print("  cutout: %s  (cutoff %.2f, queue %d, +%s)"
          % (", ".join(done), cutoff, CUTOUT_QUEUE, CUTOUT_KEYWORD))

    if dry:
        print("  --dry-run: nothing written")
        return 0

    # packer="original" keeps the bundle's own compression. A plain save()
    # writes it UNCOMPRESSED: Shrek went from 2,231,724 bytes to 8,768,715, a
    # four-fold file for a one-material change. patch_alpha_blend.py has
    # always passed this; copying the call is cheaper than rediscovering why.
    with open(out, "wb") as f:
        f.write(env.file.save(packer="original"))
    print("  wrote %s (%d bytes)" % (out, os.path.getsize(out)))

    # READ IT BACK. Prove the intended material changed and that NOTHING else
    # did -- the whole point of editing a bundle in place rather than rebuilding
    # it is that the rest is untouched, and that is a claim to check.
    after = fingerprint(UnityPy.load(out))
    changed = [n for n in before if before.get(n) != after.get(n)]
    gone = [n for n in before if n not in after]
    added = [n for n in after if n not in before]
    print("  read-back: %d material(s), %d changed (%s), %d gone, %d added"
          % (len(after), len(changed), ", ".join(sorted(changed)) or "-",
             len(gone), len(added)))
    bad = sorted(set(changed) - set(done)) + gone + added
    if bad:
        print("  WARNING: unexpected difference on %s -- do not install this"
              % ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
