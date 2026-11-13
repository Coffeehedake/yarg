# -*- coding: utf-8 -*-
"""Draw a material double-sided again, in the INSTALLED .yargchar.

    python patch_cull_off.py <in.yargchar> (--all | --materials "A;B") [--out X]
        [--dry-run]

WHY THIS EXISTS, AND WHY IT EXPLAINS SEVERAL REPORTED FAULTS AT ONCE.

Every `.vrm` this pipeline writes marks its materials **`doubleSided: true`** --
measured: Miku 1 of 1, Killer Clown 4 of 4, Pomni 13 of 13, Heels 21 of 21,
Peach 16 of 16. The exporter cannot carry that across, and says so itself:

    // A fresh URP/Lit culls back faces. The source materials are Standard,
    // which has no cull property to read, so the glTF doubleSided flag is
    // [lost]. YARG_CULL_OFF_MATERIALS draws just those materials
    // double-sided; everything else stays culled.

So the escape hatch has to be named per material, per build, and almost nobody
ever has. Across the 65 installed characters: **398 materials at `_Cull 2`
(single-sided) and exactly ONE at 0.**

Thin, single-layer geometry -- hair ribbons, skirt panels, capes, lashes -- has
no back face to fall back on, so from the wrong side it simply is not drawn.
That reads as "missing pieces", or as hair "clipping through" a hat when what
you are really seeing is the near surface culled away.

AND IT IS WHY NO RENDER HERE EVER CAUGHT IT. Blender honours `doubleSided`, so
a render of the `.vrm` shows a character that is whole. The bundle the game
loads is a different object. Measured on Miku, whose whole character is one
material: rendered from her `.vrm` her twintails are continuous ribbons;
rendered with culling forced on -- which is what the bundle does -- they break
into pieces, exactly as reported.

THE REAL FIX IS IN THE EXPORTER, which should read `doubleSided` out of the
`.vrm` and set `_Cull` from it rather than needing a list. This edits the
bundle in place, which is the same UnityPy route `patch_alpha_blend.py` and
`patch_alpha_cutout.py` take, and it does not need a rebuild.

`--all` IS DEFENSIBLE HERE and not a shortcut: the source declares every one of
these materials double-sided, so turning culling off restores what the model
asked for rather than inventing something. It costs a little fill rate, and on
a closed solid mesh it changes nothing visible because the back faces are
hidden by the front ones anyway.
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
    do_all = "--all" in argv
    dry = "--dry-run" in argv
    if not named and not do_all:
        print("ABORT: pass --all or --materials. This tool does not guess.")
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
        if not do_all and name not in named:
            continue
        sp = tt["m_SavedProperties"]
        fl = {a: b for a, b in sp["m_Floats"]}
        if "_Cull" not in fl:
            # An MToon material has no _Cull float at all; it carries its own
            # double-sided flag inside the VRM extension. Saying so beats
            # silently doing nothing.
            skipped.append("%s (no _Cull float -- MToon?)" % name)
            continue
        if fl.get("_Cull") == 0.0:
            skipped.append("%s (already double-sided)" % name)
            continue
        floats = []
        for pair in sp["m_Floats"]:
            k, v = pair[0], pair[1]
            nv = 0.0 if k == "_Cull" else v
            floats.append((k, nv) if isinstance(pair, tuple) else [k, nv])
        sp["m_Floats"] = floats
        obj.save_typetree(tt)
        done.append(name)

    print("  double-sided: %d material(s)%s"
          % (len(done), (" -- " + ", ".join(done[:8])) if done else ""))
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
