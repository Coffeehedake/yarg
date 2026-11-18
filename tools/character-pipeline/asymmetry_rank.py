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

AND THE DENOMINATOR IS NOW GUARDED, not merely printed. The paragraph above identified the
hazard and then left it to the reader, which is half a defence: `asym` is a difference of two
fractions over the SAME overlap region, so it inherits that region's quantisation exactly as
`aux_over_body` does -- a row at 262 px moves by 1/262 per pixel in each direction. The floor
comes from `part_overlap.overlap_floor`, the same derivation the primary ranking uses. Held-out
rows are printed by name with their pixel count and the rank each held ungated, and
`--no-overlap-guard` reproduces the ungated table.

THE TWO TOOLS CAN STILL DISAGREE ABOUT A GIVEN ROW, and that is not a bug to be papered over.
Same derivation, different input: the floor is `ceil(1/MAD)` of the quantity being RANKED, and
`asym` has a tighter spread than `aux_over_body` -- on the 2026-11-18 fixture the primary
ranking derives 200 px and this one 222 px. So a row at 210 px is rankable there and held out
here. That is the derivation doing its job, because 210 px really does carry a coarser
quantisation relative to the asym scale than to the forward one. Do NOT reconcile them by
hardcoding one number into both; the disagreement is information about the two scales, and a
shared constant would be a third threshold nobody derived.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from part_overlap import overlap_floor, robust_z  # noqa: E402  sibling import, NOT run with -I


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
    guard = "--no-overlap-guard" not in args
    args = [a for a in args if a != "--no-overlap-guard"]

    run = json.load(open(args[0], "r", encoding="utf-8"))
    min_region = int(run.get("min_region_px") or 200)
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

    # ------------------------------------------------------------ the denominator guard
    # `asym` is a difference of two fractions over ONE overlap region, so it carries that
    # region's quantisation twice over. Same floor, same derivation as the primary ranking, so
    # the two tools cannot disagree about which rows are rankable.
    ungated_order = [r["name"] for r in sorted(rows, key=lambda r: -r["asym"])]
    held, floor, derivation = [], 0, "guard DISABLED by --no-overlap-guard"
    if guard:
        mad = robust_z([r["asym"] for r in rows])[2] if len(rows) > 2 else 0.0
        floor, derivation = overlap_floor(mad, min_region)
        held = [r for r in rows if r["overlap"] < floor]
        rows = [r for r in rows if r["overlap"] >= floor]
        if not rows:
            print("EVERY CHARACTER was held out by the %d px denominator floor. That is a" % floor)
            print("statement about this run's overlap regions, not about the roster, and the")
            print("ranking below would have been entirely noise. Re-run --no-overlap-guard to")
            print("see what was removed.")
            for r in held:
                print("  %-24s overlap %d px" % ((r["name"] or "?")[:24], r["overlap"]))
            return 1

    print("overlap denominator guard: %s" % ("ON" if guard else "OFF (--no-overlap-guard)"))
    print("  %s" % derivation)
    if guard:
        # The removed rows WITH THE RANK EACH HELD UNGATED. Removing rows cannot reorder the
        # survivors, so a column of rank shifts would flag every row below a removal as
        # "moved" without one of them having changed place -- these lines are the whole change.
        print("  HELD OUT -- unmeasured, NOT reverse-dominant and NOT clean: %d" % len(held))
        for r in sorted(held, key=lambda r: ungated_order.index(r["name"])
                        if r["name"] in ungated_order else 10 ** 6):
            rank = ungated_order.index(r["name"]) + 1 if r["name"] in ungated_order else 0
            flag = "  <- IT HELD THE TOP RANK" if rank == 1 else ""
            print("    ungated rank %2d  %-24s overlap %d px < %d (asym would have read %+.6f)%s"
                  % (rank, (r["name"] or "?")[:24], r["overlap"], floor, r["asym"], flag))
        if not held:
            print("    (none -- every row's denominator clears the floor, so this ranking is")
            print("     identical to --no-overlap-guard)")
    print()

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
