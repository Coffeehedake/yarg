# -*- coding: utf-8 -*-
"""Is the depth-order ranking a FAULT ranking, or mostly a TRANSPARENCY ranking?

    python transparency_vs_violation.py <part_overlap.json> <installed-dir> <known-transparent.yargchar>

THE QUESTION. `part_overlap.py` ranks characters by the fraction of the body/hair overlap where
the aux half is drawn in front of a nearer body half. 44 of 46 show some violation and the tail
is offered as the finding. But a character scoring high is equally consistent with two readings:

    (a) it has a draw-order FAULT, which is what the probe claims to measure;
    (b) it simply carries MORE non-depth-writing material than its neighbours.

A fully-blended character scores high under both, so the real-artefact positive control cannot
separate them -- and neither can the top row, since a dress is exactly the sort of garment
likely to be blended. If (b) dominates, every row has to be read as "fault per unit of
transparent material" rather than raw.

THE CONTROL COMES FIRST AND IT IS NOT OPTIONAL. "No character carries a transparent material"
and "my material reader cannot see transparency" produce the same output. So this takes a bundle
KNOWN to be transparent and refuses to report anything until it has found transparency in it.
That check exists because a sibling triage of mine returned "19 of 19 provably safe", which is
either a real result or a reader that always says no.
"""
import json
import os
import sys

try:
    import UnityPy
except ImportError:
    UnityPy = None


def materials_of(path):
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


def spearman(xs, ys):
    """Rank correlation, written out rather than imported: no scipy dependency for 46 rows."""
    n = len(xs)
    if n < 3:
        return None

    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
    return num / (dx * dy) if dx and dy else None


def main():
    if len(sys.argv) < 4 or UnityPy is None:
        print(__doc__)
        if UnityPy is None:
            print("\nUnityPy not importable -- NOTHING was read. A statement about this "
                  "environment, not a result.")
        return 2

    run = json.load(open(sys.argv[1], "r", encoding="utf-8"))
    chars_dir, known = sys.argv[2], sys.argv[3]

    # ---------------------------------------------------------------- the control, first
    print("=" * 78)
    print("CONTROL: can this reader see transparency at all?")
    print("=" * 78)
    try:
        kmats = materials_of(known)
    except Exception as e:
        print("  FAILED to read the known-transparent bundle: %s: %s" % (type(e).__name__, e))
        print("  Nothing below would mean anything. Stopping.")
        return 1
    ktrans = [m for m in kmats if m[1] == 1.0]
    print("  %s: %d materials, %d with _Surface == 1" % (os.path.basename(known), len(kmats), len(ktrans)))
    for m in ktrans:
        print("      transparent: %s" % m[0])
    if not ktrans:
        print("  CONTROL FAILED -- found NO transparency in a bundle known to be fully blended.")
        print("  Every 'no transparent material' verdict elsewhere is about this reader.")
        return 1
    print("  CONTROL PASSED -- the reader detects transparency, so a zero elsewhere is a zero.")

    # ---------------------------------------------------------------- the population
    rows = []
    unread = []
    for ch in run.get("characters") or []:
        name = ch.get("name")
        frames = ch.get("frames_data") or []
        viol = [f["aux_over_body"] for f in frames if f.get("aux_over_body") is not None]
        path = os.path.join(chars_dir, (name or "") + ".yargchar")
        if not os.path.isfile(path):
            unread.append((name, "no bundle"))
            continue
        try:
            mats = materials_of(path)
        except Exception as e:
            unread.append((name, "%s: %s" % (type(e).__name__, e)))
            continue
        ntrans = len([m for m in mats if m[1] == 1.0])
        rows.append({
            "name": name, "mats": len(mats), "ntrans": ntrans,
            "frac_trans": (float(ntrans) / len(mats)) if mats else 0.0,
            "viol": max(viol) if viol else None,
            "aux_tris": ch.get("aux_tris", 0),
        })

    measured = [r for r in rows if r["viol"] is not None]
    print()
    print("=" * 78)
    print("TRANSPARENT MATERIALS vs DEPTH-ORDER VIOLATION, %d measured characters" % len(measured))
    print("=" * 78)
    with_t = [r for r in measured if r["ntrans"] > 0]
    without = [r for r in measured if r["ntrans"] == 0]
    print("carry >=1 transparent material: %d" % len(with_t))
    print("carry none:                     %d" % len(without))

    def summarise(label, group):
        if not group:
            print("  %-28s (none)" % label)
            return
        v = sorted(r["viol"] for r in group)
        med = v[len(v) // 2]
        print("  %-28s n=%2d  median violation %.6f  max %.6f" % (label, len(group), med, v[-1]))

    summarise("with transparent material", with_t)
    summarise("without any", without)

    if with_t and without:
        vw = sorted(r["viol"] for r in with_t)
        vo = sorted(r["viol"] for r in without)
        print()
        print("  IF THE RANKING WERE MOSTLY A TRANSPARENCY RANKING, the first group would sit")
        print("  far above the second. Median %.6f against %.6f." % (vw[len(vw) // 2], vo[len(vo) // 2]))

    rho = spearman([r["frac_trans"] for r in measured], [r["viol"] for r in measured])
    rho2 = spearman([float(r["ntrans"]) for r in measured], [r["viol"] for r in measured])
    print()
    print("Spearman rank correlation against violation:")
    print("  share of materials transparent : %s" % ("%.3f" % rho if rho is not None else "n/a"))
    print("  count of transparent materials : %s" % ("%.3f" % rho2 if rho2 is not None else "n/a"))
    print()
    print("  Read it as: |rho| near 1 means the ranking is largely explained by how much")
    print("  non-depth-writing material a character carries, and every row should be read as")
    print("  fault PER UNIT of transparent material. Near 0 means the ranking stands on its own.")

    print()
    print("Top 10 by violation, with their transparency:")
    print("  %-24s %10s %6s %7s" % ("character", "violation", "trans", "of mats"))
    for r in sorted(measured, key=lambda r: -r["viol"])[:10]:
        print("  %-24s %10.6f %6d %7d" % (r["name"][:24], r["viol"], r["ntrans"], r["mats"]))

    if unread:
        print()
        print("COULD NOT READ (not counted either way): %d" % len(unread))
        for n, w in unread[:8]:
            print("  %-24s %s" % ((n or "?")[:24], w))
    return 0


if __name__ == "__main__":
    sys.exit(main())
