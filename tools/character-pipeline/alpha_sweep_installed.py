# -*- coding: utf-8 -*-
"""alpha_sweep, run against the INSTALLED .yargchar instead of a .vrm.

`alpha_sweep.py` reads a `.vrm`, and 25 `.vrm` files survive on this machine,
covering about 22 of the 65 characters -- four of them are Iron Man variants.
And a `.vrm` being present is not sufficient either: `identify_build.py` has
twice caught one that is not the build that is installed. So the sweep that
found Miku's skirt, Peach's eyes, Alcina's eyelashes, Sayuri's lashes and
Heels' transparency had never been pointed at the other forty-odd, and silence
from a tool that never looked is not a clean result. Everything it needs is in
the bundle:

    Material.m_SavedProperties.m_Floats   _Surface, _AlphaClip, _Cutoff
    Material.m_SavedProperties.m_TexEnvs  _BaseMap / _MainTex
    Texture2D                             decodes to RGBA, so alpha is readable

THREE THINGS IT REPORTS, and they are different defects

  UNUSED    the material is OPAQUE and its base map carries meaningful alpha.
            That is the Peach/Alcina/Miku class: the opacity is in the file and
            nothing is honouring it, so a hair card or an eyelash plate draws
            as a solid slab.

  HARDCUT   the material is a CUTOUT and its alpha is a smooth gradient rather
            than a two-valued mask. A cutout thresholds at _Cutoff, so a soft
            alpha is not softened, it is BUTCHERED -- everything under the
            threshold vanishes and everything over it draws at full opacity.
            This is how Gordon Freeman's glasses ship: lens.png runs 0.153 to
            0.624, mean 0.330, against a cutoff of 0.5, so 79.3% of the lens is
            clipped away and the rest is solid. He is recorded as fixed.

  NOALPHA   a cutout whose base map has no alpha variation at all, which means
            the cutout is doing nothing and may be hiding a lost opacity map.

AN ALPHA CHANNEL IS NOT NECESSARILY AN OPACITY MAP, and this tool cannot tell

In a game rip it is as likely to be a specular or environment mask -- Source
engine's `$basealphaenvmapmask` packs exactly that. Gordon Freeman carries
three alpha channels of three different kinds: his lens is real opacity, and
`eye-iris-green.tga` and `onefreeman` are specular masks that, honoured, hide
his irises and erase his suit. So every row here is a CANDIDATE. The decision
needs a render, and `render_closeup.py` with RENDER_ONLY / RENDER_HIDE is how
this project has always made it.

MEASURED AT FULL RESOLUTION, on purpose. An earlier version of the .vrm sweep
measured a downscaled copy, and Blender's `image.scale()` is a filtered resize
that averages away exactly the two-valuedness the tier test depends on:
Alcina's CILIOS reads 0.875 solid at full resolution and 0.790 averaged, and
that gap was the difference between her eyelashes being flagged and not.

NOT UV-MASKED, and that is a real limitation, stated rather than hidden. The
.vrm sweep masks each measurement to the texels the material's own geometry
lands on, because two materials can sample different parts of one atlas and a
whole-image average then describes neither. Doing that here needs the UV
stream out of m_VertexData per submesh; until it does, a material sharing an
atlas can read as alpha-carrying because of a region it never samples. Treat a
hit on a shared atlas as weaker evidence, and check which image it names.

    python alpha_sweep_installed.py <dir-of-yargchar | file.yargchar ...>

    ALPHA_MIN=0.02      how much of the map must be non-solid to count at all
    ALPHA_MASK=0.90     solid+clear this fraction or more => a two-valued MASK
    ALPHA_VERBOSE=1     every material, not only the flagged ones
"""
import os
import sys

import numpy as np
import UnityPy

MIN = float(os.environ.get("ALPHA_MIN", "0.02"))
MASKY = float(os.environ.get("ALPHA_MASK", "0.90"))
VERBOSE = os.environ.get("ALPHA_VERBOSE", "") == "1"
CONTROL = os.environ.get("ALPHA_CONTROL", "") == "1"


def stats(img):
    a = np.asarray(img.convert("RGBA"), dtype=np.uint8)[:, :, 3].astype(np.float32)
    a /= 255.0
    clear = float((a < 0.02).mean())
    solid = float((a > 0.98).mean())
    return {
        "clear": clear,
        "solid": solid,
        "mid": 1.0 - clear - solid,
        "min": float(a.min()),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "a": a,
    }


def tier(s):
    """mask, soft, or flat -- the same two tiers alpha_sweep.py settled on."""
    if s["max"] - s["min"] < 0.01:
        return "flat"
    if s["clear"] + s["solid"] >= MASKY:
        return "mask"
    return "soft"


def audit(path):
    env = UnityPy.load(path)
    tex, shaders = {}, {}
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            tex[obj.path_id] = obj
        elif obj.type.name == "Shader":
            try:
                t = obj.read_typetree()
                shaders[obj.path_id] = (t.get("m_ParsedForm", {}) or {}).get(
                    "m_Name") or t.get("m_Name") or "?"
            except Exception:
                shaders[obj.path_id] = "?"

    rows = []
    for obj in env.objects:
        if obj.type.name != "Material":
            continue
        tt = obj.read_typetree()
        sp = tt.get("m_SavedProperties", {}) or {}
        fl = {k: v for k, v in sp.get("m_Floats", [])}
        tv = {k: (v.get("m_Texture") or {}).get("m_PathID")
              for k, v in sp.get("m_TexEnvs", [])}
        sh = shaders.get((tt.get("m_Shader") or {}).get("m_PathID"), "?")

        # MToon carries its transparency in its own properties, not in URP's.
        # Saying so beats guessing: the six community-downloaded bundles are
        # all MToon and must not be judged by a property they do not have.
        if "_Surface" not in fl:
            rows.append({"name": tt.get("m_Name", "?"), "shader": sh,
                         "mode": "mtoon", "tier": "?", "flag": ""})
            continue

        cutout = fl.get("_AlphaClip") == 1.0
        transp = fl.get("_Surface") == 1.0
        cut = fl.get("_Cutoff", 0.5)
        if CONTROL:
            cutout, transp = False, False
        mode = "blend" if transp else ("cutout" if cutout else "opaque")

        pid = tv.get("_BaseMap") or tv.get("_MainTex")
        if pid not in tex:
            rows.append({"name": tt.get("m_Name", "?"), "shader": sh,
                         "mode": mode, "tier": "-", "flag": "",
                         "note": "no base map"})
            continue
        try:
            s = stats(tex[pid].read().image)
            texname = tex[pid].read().m_Name
        except Exception as e:
            rows.append({"name": tt.get("m_Name", "?"), "shader": sh,
                         "mode": mode, "tier": "?", "flag": "",
                         "note": "undecodable: %s" % e})
            continue

        tr = tier(s)
        flag = ""
        if mode == "opaque" and tr != "flat" and (1.0 - s["solid"]) > MIN:
            flag = "UNUSED"
        elif mode == "cutout" and tr == "soft":
            # When the WHOLE texture is under the threshold the material cannot
            # draw a single texel, and that needs no render to establish -- it
            # is arithmetic on the cutoff. Say so separately, because "100%
            # clipped" and "invisible" are the same fact and only one of them
            # reads as serious.
            clipped = 100 * float((s["a"] < cut).mean())
            if s["max"] < cut:
                flag = ("INVISIBLE alpha max %.3f < cutoff %.2f"
                        % (s["max"], cut))
            else:
                # One decimal, because %.0f printed Heels' eyelashes as
                # "100% clipped" when the real figure is 99.6 -- and "100%"
                # is a claim of total invisibility that the INVISIBLE test
                # above had already, correctly, refused to make. A rounded
                # number that reads as an absolute is the same mistake as a
                # count in a comment being read as a measurement.
                flag = "HARDCUT %.1f%% clipped" % clipped
        elif mode == "cutout" and tr == "flat":
            flag = "NOALPHA"
        rows.append({"name": tt.get("m_Name", "?"), "shader": sh, "mode": mode,
                     "tier": tr, "flag": flag, "tex": texname,
                     "clear": s["clear"], "solid": s["solid"],
                     "mid": s["mid"], "mean": s["mean"]})
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            files.append(a)

    if CONTROL:
        print("ALPHA_CONTROL=1: every material is treated as opaque, so every "
              "material carrying any alpha must flag UNUSED.\n")

    totals = {"UNUSED": 0, "HARDCUT": 0, "NOALPHA": 0}
    hit_chars = set()
    nmat = nmtoon = 0
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        rows = audit(p)
        nmat += len(rows)
        nmtoon += sum(1 for r in rows if r["mode"] == "mtoon")
        flagged = [r for r in rows if r["flag"]]
        for r in flagged:
            totals[r["flag"].split()[0]] += 1
            hit_chars.add(name)
        counts = {}
        for r in rows:
            counts[r["mode"]] = counts.get(r["mode"], 0) + 1
        print("%-34s %s" % (name[:34], " ".join(
            "%s=%d" % (k, counts[k]) for k in sorted(counts))
            + ("   %d flagged" % len(flagged) if flagged else "")))
        for r in (rows if VERBOSE else flagged):
            if r["flag"] or VERBOSE:
                print("    %-22s %-7s %-5s clear=%.3f solid=%.3f mid=%.3f  %s  %s"
                      % (r["name"][:22], r["mode"], r["tier"],
                         r.get("clear", -1), r.get("solid", -1), r.get("mid", -1),
                         r["flag"] or r.get("note", ""), r.get("tex", "")))

    print("\n%d character(s), %d materials (%d MToon, judged separately): "
          "%d UNUSED, %d HARDCUT, %d NOALPHA across %d character(s)"
          % (len(files), nmat, nmtoon, totals["UNUSED"], totals["HARDCUT"],
             totals["NOALPHA"], len(hit_chars)))
    print("Every row is a CANDIDATE. An alpha channel in a game rip is as "
          "likely to be a specular mask as an opacity map; confirm with a "
          "render before changing anything.")


if __name__ == "__main__":
    main()
