# -*- coding: utf-8 -*-
"""Which INSTALLED characters can actually lipsync, read from the bundle.

Every VRM declares all 18 preset expressions whether or not anything is wired
to them, so a file always LOOKS lipsync-capable. The distinction that matters
is declared versus BOUND: an expression with no `MorphTargetBindings` moves
nothing. `viseme_fit.py` answers this for a source model; this answers it for
the thing the game loads, which is the only version that can be wrong.

    python viseme_audit.py <dir-of-yargchar | file.yargchar ...>

Reports the five lipsync visemes (aa, ih, ee, ou, oh) and blink separately,
because a character with blink and no visemes is the common shape here and
reads as "the mouth never moves" rather than as "nothing works".
"""
import collections
import os
import sys

import UnityPy

VISEMES = ("aa", "ih", "ee", "ou", "oh")


def audit(path):
    env = UnityPy.load(path)
    bound = {}
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            t = obj.read_typetree()
            cn = obj.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            continue
        if cn != "VRM10Expression":
            continue
        nm = (t.get("m_Name") or "").lower()
        n = len(t.get("MorphTargetBindings") or [])
        if n:
            bound[nm] = bound.get(nm, 0) + n

    name = os.path.basename(path).replace(".yargchar", "")
    got = [v for v in VISEMES if v in bound]
    blink = "blink" in bound
    extra = sorted(set(bound) - set(VISEMES) - {"blink"})
    verdict = ("%d/5 visemes" % len(got)) if got else "NO VISEMES"
    print("%-34s %-14s blink=%-3s %s%s"
          % (name[:34], verdict, "yes" if blink else "NO",
             ",".join(got) or "-",
             "   +" + ",".join(extra) if extra else ""))
    return len(got), blink


def main():
    files = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.endswith(".yargchar")]
        else:
            files.append(a)
    tally = collections.Counter()
    nb = 0
    for f in files:
        try:
            n, blink = audit(f)
        except Exception as e:                                   # noqa: BLE001
            print("%-34s ERROR %s" % (os.path.basename(f)[:34], e))
            continue
        tally[n] += 1
        nb += 1 if blink else 0
    tot = sum(tally.values())
    print("")
    print("%d character(s): %d with all five visemes, %d partial, %d with none; "
          "%d can blink"
          % (tot, tally[5], sum(v for k, v in tally.items() if 0 < k < 5),
             tally[0], nb))


main()
