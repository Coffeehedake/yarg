# -*- coding: utf-8 -*-
"""Re-rank the roster on DIRECTIONAL violation, subtracting the symmetric confound.

    python asymmetry_rank.py <part_overlap.json> [--top N]

WHY. `part_overlap.py` ranks on `aux_over_body` -- aux visible where the body is nearer. On
opaque characters that number has a baseline nobody has explained, and three candidate causes
remain: screen-space ambient occlusion, real cast shadows, and anti-aliasing at silhouette
edges. All three were going to need Unity time to test, and a null from any one would not clear
the others.

THE CONFOUNDS ARE SYMMETRIC AND THE FAULT IS NOT, which makes them separable with no new render
at all. SSAO, shadows and AA all change the shading of a surface THAT WAS ALREADY SHOWN, at a
boundary, regardless of which side is nearer -- so they should push `aux_over_body` and
`body_over_aux` up by similar amounts. A genuine draw-order fault is directional: blended aux
composites over nearer body, and not the reverse.

The evidence was already in two control numbers:

    AikoCONTROLBLEND (3x BLEND, broken)   forward 0.381922   reverse 0.107492   ratio 3.55
    Aiko             (opaque, fixed)      forward 0.005191   reverse 0.015033   ratio 0.35

**A clean character reads THREE TIMES MORE in the reverse direction than the forward one.** If
the probe measured only real draw-order faults, a clean opaque character would read near zero
both ways. Reverse exceeding forward where nothing is wrong is the confound, measured, in data
already collected.

So `asym = forward - reverse` keeps the directional part and subtracts whatever is symmetric.
It cannot prove the confound's identity and does not try to; it removes the component that any
symmetric process must contribute equally to.

READ THE RATIO ALONGSIDE THE DIFFERENCE, never alone: a ratio on two tiny numbers is noise with
a decimal point, which is why the absolute forward value and the overlap denominator stay in the
table.
"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    topn = 14
    args = sys.argv[1:]
    if "--top" in args:
        i = args.index("--top")
        topn = int(args[i + 1])
        del args[i:i + 2]

    run = json.load(open(args[0], "r", encoding="utf-8"))
    rows = []
    for ch in run.get("characters") or []:
        frames = ch.get("frames_data") or []
        fwd = [f["aux_over_body"] for f in frames if f.get("aux_over_body") is not None]
        rev = [f["body_over_aux"] for f in frames if f.get("body_over_aux") is not None]
        if not fwd or not rev:
            continue
        # Pair them per frame, so the subtraction is within-frame rather than across summaries.
        per = [(f.get("aux_over_body"), f.get("body_over_aux"), f.get("depth_overlap_px", 0))
               for f in frames
               if f.get("aux_over_body") is not None and f.get("body_over_aux") is not None]
        if not per:
            continue
        best = max(per, key=lambda t: t[0] - t[1])
        rows.append({
            "name": ch.get("name"),
            "fwd": best[0], "rev": best[1],
            "asym": best[0] - best[1],
            "overlap": best[2],
            "max_fwd": max(fwd),
        })

    if not rows:
        print("NO CHARACTER had both directions recorded. Nothing is ranked, and that is a")
        print("statement about the run, not about the roster.")
        return 1

    pos = [r for r in rows if r["asym"] > 0]
    neg = [r for r in rows if r["asym"] <= 0]

    print("=" * 78)
    print("DIRECTIONAL VIOLATION  (forward - reverse), %d characters" % len(rows))
    print("=" * 78)
    print("forward-dominant (asym > 0): %d" % len(pos))
    print("reverse-dominant (asym <= 0): %d   <- a symmetric process, not a draw-order fault"
          % len(neg))
    print()
    print("A draw-order fault can only be forward-dominant. A character that is reverse-dominant")
    print("is showing something non-directional, whatever else is true of it.")
    print()
    print("%-24s %10s %10s %10s %8s %7s" % ("character", "asym", "forward", "reverse", "overlap", "ratio"))
    for r in sorted(rows, key=lambda r: -r["asym"])[:topn]:
        ratio = (r["fwd"] / r["rev"]) if r["rev"] > 1e-9 else float("inf")
        print("%-24s %10.6f %10.6f %10.6f %8d %7s"
              % ((r["name"] or "?")[:24], r["asym"], r["fwd"], r["rev"], r["overlap"],
                 "inf" if ratio == float("inf") else "%.2f" % ratio))

    print()
    print("Bottom 5 (most reverse-dominant):")
    for r in sorted(rows, key=lambda r: r["asym"])[:5]:
        print("  %-24s asym %10.6f   forward %.6f  reverse %.6f"
              % ((r["name"] or "?")[:24], r["asym"], r["fwd"], r["rev"]))

    print()
    print("Rank change against the forward-only ranking:")
    by_fwd = [r["name"] for r in sorted(rows, key=lambda r: -r["max_fwd"])]
    by_asym = [r["name"] for r in sorted(rows, key=lambda r: -r["asym"])]
    for name in by_asym[:8]:
        print("  %-24s forward rank %2d -> asym rank %2d"
              % (name[:24], by_fwd.index(name) + 1, by_asym.index(name) + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
