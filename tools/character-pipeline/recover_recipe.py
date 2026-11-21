# -*- coding: utf-8 -*-
"""Recover rig family and height for characters whose recipe is gone, and PROVE it first.

    python recover_recipe.py [README.md] [characters-dir]

WHY. Ten characters this pipeline built have no recipe recorded anywhere -- Baby Groot, both
Clone Troopers, Doom Slayer, Iron Man Mark 85, K-2SO, Kaiser Aufhaenger, Skeleton Mage, Spartan
Mark V, Spider-Man -- and the build logs that recipes were harvested from are gone from this
machine. Doom Slayer is the sharp case: he is recorded as one of eight that rebuilt cleanly and
SHIPPED on 2026-11-14, from a recipe that now exists nowhere.

Two of the three things a build needs are still readable out of the installed bundle. This does
not invent the third.

HOW IT IS VALIDATED, and this is the whole point. **Fifty characters have BOTH a recipe and a
bundle.** They are labelled data. So the signatures are learned from them and then scored
against them, and the accuracy is printed before any recovered row is offered:

  rig family   learned from the bone names of the 50, then classified back. Every
               disagreement is printed by name, because an aggregate accuracy hides exactly
               the cases a reader needs.
  height       measured from the skinned mesh and compared against the recorded figure on
               all 50, giving a real error bar rather than an assumed one.

The 2026-11-15 cross-check did this for twelve characters and agreed with the written table to
the centimetre on all twelve. Fifty is a stronger test of the same method, and if the method
does NOT reproduce the fifty then nothing here is offered for the ten.

WHAT IS NOT RECOVERABLE, stated so a partial recipe is never mistaken for a whole one: the
source archive and path, exclude regexes, `VRM_TEX` maps, hairrig arguments and every `VRM_*`
switch. None of those leave a readable trace in the bundle. A recovered row is rig and height
ONLY, and is marked as such.
"""
import io
import math
import os
import re
import sys
from collections import Counter

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

README = sys.argv[1] if len(sys.argv) > 1 else "README.md"
CHARS = sys.argv[2] if len(sys.argv) > 2 else (
    os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\FatalException\YARG-FE"
                       r"\release\custom\characters"))
RIG = re.compile(r"^\*{0,2}[a-z_][a-z_0-9]*\*{0,2}$")


def keys(cell):
    out = []
    for part in re.split(r"\s*/\s*", cell.strip()):
        part = part.strip("*` ")
        if not part:
            continue
        out.append(part)
        bare = re.sub(r"\s*\(.*?\)\s*$", "", part).strip()
        if bare and bare != part:
            out.append(bare)
    return out


def recipes():
    out = {}
    for line in io.open(README, encoding="utf-8"):
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 3:
            continue
        names = keys(c[0])
        rigs = [r.strip("*` ") for r in re.split(r"\s*/\s*", c[1])]
        # THE HEIGHT COLUMN IS COMPOUND TOO. '| Joker / Miku | maxbiped | 1.85 / 1.58 |'
        # splits the name and the rig but the height as well, and taking [0] for both gave
        # Miku Joker's height -- a 277 mm error that showed up as the worst in the whole
        # validation set and was entirely this parser's.
        hs = [x.strip() for x in re.split(r"\s*/\s*", c[2])]
        if not names or not all(RIG.match(r or "") for r in rigs):
            continue
        try:
            heights = [float(x) for x in hs]
        except ValueError:
            continue
        for i, n in enumerate(names):
            out.setdefault(n, (rigs[min(i, len(rigs) - 1)],
                               heights[min(i, len(heights) - 1)]))
    return out


def tokens(name):
    """Bone-name tokens that could carry a rig family's fingerprint."""
    n = name.lower()
    out = set()
    if ":" in n:
        out.add("ns:" + n.split(":")[0])
    for m in re.findall(r"[a-z]+", n):
        if len(m) >= 3:
            out.add(m)
    for pre in ("def-", "mch-", "org-", "bip01", "valvebiped", "cc_base", "rp_"):
        if n.startswith(pre):
            out.add("pre:" + pre)
    return out


def read_bundle(path):
    """(set of bone-name tokens, height in metres) or (None, None)."""
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    toks = Counter()
    for _pid, rec in tf.items():
        nm = rec.get("name")
        if nm:
            toks.update(tokens(nm))
    env = UnityPy.load(path)
    tt, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            tt[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())
    ys = []
    for r in smrs:
        mt = tt.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
        if got is None or not bones or len(bind) != len(bones):
            continue
        V, W, I = got
        skin = [ps.mul(ps.trs(*world(b)), bind[i]) for i, b in enumerate(bones)]
        for vi in range(0, len(V), 7):          # stride: height needs extremes, not every vertex
            best, bw = None, -1.0
            for k in range(len(W[vi])):
                w, bi = W[vi][k], I[vi][k]
                if w > bw and w > 0 and bi < len(skin):
                    bw, best = w, bi
            if best is not None:
                ys.append(ps.xform(skin[best], V[vi])[1])
    return set(toks), ((max(ys) - min(ys)) if ys else None)


def main():
    rec = recipes()
    installed = sorted(f[:-9] for f in os.listdir(CHARS) if f.endswith(".yargchar"))
    data = {}
    for n in installed:
        try:
            data[n] = read_bundle(os.path.join(CHARS, n + ".yargchar"))
        except Exception as exc:                                    # noqa: BLE001
            print("UNREADABLE %-26s %s: %s" % (n, type(exc).__name__, exc))
    labelled = [n for n in data if n in rec and data[n][0]]
    unlabelled = [n for n in data if n not in rec]

    # ---- learn a signature per rig family from the labelled set
    fam_tokens, fam_n = {}, Counter()
    for n in labelled:
        f = rec[n][0]
        fam_n[f] += 1
        fam_tokens.setdefault(f, Counter()).update(data[n][0])
    # a token is characteristic if it appears in most members of one family and few others
    total = Counter()
    for f, c in fam_tokens.items():
        for t in c:
            total[t] += 1
    sig = {}
    for f, c in fam_tokens.items():
        sig[f] = {t: c[t] / fam_n[f] for t in c
                  if c[t] / fam_n[f] >= 0.8 and total[t] <= 3}

    def classify(toks):
        best, score = None, 0.0
        for f, s in sig.items():
            if not s:
                continue
            hit = sum(w for t, w in s.items() if t in toks) / sum(s.values())
            if hit > score:
                best, score = f, hit
        return best, score

    # ---- VALIDATE on the labelled set before offering anything
    right, wrong = 0, []
    for n in labelled:
        got, sc = classify(data[n][0])
        if got == rec[n][0]:
            right += 1
        else:
            wrong.append((n, rec[n][0], got, sc))
    print("=" * 78)
    print("VALIDATION on the %d characters that have BOTH a recipe and a bundle" % len(labelled))
    print("=" * 78)
    print("rig family recovered correctly: %d of %d (%.0f%%)"
          % (right, len(labelled), 100.0 * right / max(1, len(labelled))))
    for n, want, got, sc in wrong:
        print("    WRONG  %-26s recorded %-14s recovered %-14s (%.2f)"
              % (n[:26], want, got or "-", sc))

    hs = [(n, data[n][1], rec[n][1]) for n in labelled if data[n][1]]
    errs = sorted(abs(m - w) for _n, m, w in hs)
    print()
    print("height recovered on %d: median error %.3f m, p90 %.3f m, max %.3f m"
          % (len(hs), errs[len(errs)//2], errs[min(len(errs)-1, int(len(errs)*0.9))], errs[-1]))
    worst = sorted(hs, key=lambda t: -abs(t[1] - t[2]))[:5]
    for n, m, w in worst:
        print("    worst  %-26s measured %.3f  recorded %.3f  (%+.3f)" % (n[:26], m, w, m - w))

    ok = right / max(1, len(labelled)) >= 0.90 and errs[len(errs)//2] <= 0.05
    print()
    if not ok:
        print("THE METHOD DOES NOT REPRODUCE THE FIFTY, so nothing is offered for the ten.")
        print("Recovered values would be indistinguishable from recorded ones in the table,")
        print("and this table is now the only record there is.")
        return 1

    print("=" * 78)
    print("RECOVERED -- rig and height ONLY. Source, excludes, VRM_* switches and hairrig")
    print("arguments are NOT recoverable from a bundle and are not guessed.")
    print("=" * 78)
    print("%-26s %-16s %8s %8s" % ("character", "rig (confidence)", "height", ""))
    for n in sorted(unlabelled):
        toks, h = data[n]
        f, sc = classify(toks)
        print("%-26s %-16s %8s  %s"
              % (n[:26], "%s (%.2f)" % (f or "-", sc), ("%.2f" % h) if h else "-",
                 "LOW CONFIDENCE" if sc < 0.6 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
