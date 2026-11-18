# -*- coding: utf-8 -*-
"""Rank a roster by INTERIOR faults -- a character's own geometry drawn over itself wrongly.

    python part_overlap.py <part_overlap.json | dir> [more...] [--top N]
    python part_overlap.py --monotonic <push0.json> <push1.json> ...   # the positive control

`anim_sweep.py` ranks the roster on the SILHOUETTE and says in its own docstring that it is
blind to anything interior: "hair across a face, or a hand through a skirt, leaves the outline
unchanged and will NOT appear here at any rank." The only character fault ever actually
reported to us was "her hair goes over her face". This reads the other half.

`YargCharParts.cs` renders and produces the JSON; this does the arithmetic, the ranking and the
control gates. The split is deliberate: a mistake in the arithmetic is then a two-second fix
rather than another Unity run.

=======================================================================================
TWO MEASUREMENTS, AND THE FIRST IS THE ONE THAT MEANS SOMETHING
=======================================================================================

1. DEPTH-ORDER VIOLATION -- `aux_over_body`. The fraction of the pixels where body and
   hair/cloth overlap on screen at which the hair/cloth half is VISIBLE while the body is
   GEOMETRICALLY NEARER. Depth comes from a geometry-only pass that no material can influence;
   visibility comes from ablation renders with the real materials. The disagreement between the
   two IS the fault:

       Aiko's hair drew over her face because its material sat in the transparent queue, which
       does not write depth, so hair BEHIND her head was composited on top of it.

   A FRINGE DOES NOT ENTER THIS NUMBER. Hair correctly in front of a forehead is nearer than
   the face, so it is drawn in front legitimately and the test ignores it. That is the whole
   reason this measurement exists and the face-region one below is kept only as a secondary.

   `body_over_aux` is the same violation seen from the other side and is reported beside it.

2. FACE-REGION OCCLUSION -- `head_occlusion`. The fraction of the head region covered by
   anything else. Kept because it is the measurement the task asked for and it needs no depth
   pass, but it CANNOT TELL A FRINGE FROM A FAULT, and on this roster's rigs it is weak for a
   second reason: the head region is the triangles dominantly weighted to the humanoid
   Head/Jaw/eye bones, and on the mixamo-retargeted rigs here the FACE IS WEIGHTED TO NECK.
   Aiko's fixed build has 1,065 Head-dominant vertices covering 243 px at 512; her pre-fix
   build has THREE and no head triangles at all. A rig that cannot be resolved is reported as
   unmeasured, never as clean.

Both are FRACTIONS, NEVER COUNTS. A count is not comparable between a 1.9 m character and a
0.9 m one rendered at the same resolution, and this roster has Groot and Yoda on it.

NO THRESHOLD IS INVENTED. There is no prior for how much of this is normal, so the POPULATION
sets the scale via a robust z (median and MAD, so a handful of genuinely broken characters
cannot inflate the yardstick meant to catch them), and the tail is what gets looked at.

=======================================================================================
AND A FRACTION NEEDS A DENOMINATOR BIG ENOUGH TO CARRY IT
=======================================================================================

Being a fraction is what makes these numbers comparable across a 1.9 m character and a 0.9 m
one. It is also how a row gets to the top of the ranking on fourteen pixels. `Gwen Stacy`
ranked FIFTH on this roster at 0.0534 over an overlap region of 262 px -- 14 violating pixels,
and one pixel either way would have moved her 0.5 of a z. The denominator is not shown by the
rate and the reader has no way to recover it, which is exactly how the top row's `5675` was
read as a count of violations by the person who wrote the column.

So the ranked table now carries THREE things next to every rate, and the guard is derived from
the population rather than chosen:

  * `viol_px`, the COUNT behind the rate. A fraction and its numerator side by side cannot be
    mistaken for one another.
  * `z/px`, what ONE pixel is worth in the units the ranking is done in -- `(1/overlap_px)/MAD`.
    A row at 0.5 is a row whose rank is three pixels wide.
  * A HOLD-OUT below `overlap_floor()`, named with its reason like every other hold-out, never
    silently dropped. The floor is the denominator at which one pixel moves a row's z by a
    whole unit, i.e. `ceil(1/MAD)` -- below it the rate is quantised more coarsely than the
    scale it is being ranked on, so it cannot be ranked at all. It is held at no less than the
    run's own `min_region_px`, because this test should not guard its denominator more weakly
    than the face-region test below already guards its own.

The floor comes FROM the population it then filters, so it is derived twice: once on everything
measured, once on what survives, and the output says whether the second pass moved it. One pass
and a report, never a silent loop. `--no-overlap-guard` reproduces the ungated ranking, and the
gated run prints the rank changes against it, so the guard can never quietly be the thing doing
the work.

=======================================================================================
THE CONTROL GATES, WHICH PRINT BEFORE ANY RESULT
=======================================================================================

"No character on the roster has an interior fault" and "the probe never ran" produce the same
zeros, and this project has published the second as the first more than once -- five spring
probes reading zero for every character, five builds whose collider step threw a swallowed
ModuleNotFoundError into a log nobody searched for failures. The first version of THIS tool
reported a 13,572-pixel head region on a character with zero head triangles, because its mask
was a brightness test and the podium is brightly lit; it then passed its own "did we look at a
face" gate on the strength of that number. So nothing here reports a clean roster until it has
said, in numbers:

  * how many characters each test LOOKED AT, with the two tests gated SEPARATELY -- a character
    can be measurable for one and not the other, and one verdict covering both reports a
    character as clean on a test that never ran;
  * every held-out character named individually, with its reason;
  * whether the verdict moves between the two diff thresholds -- if it does, the cutoff is
    doing the work;
  * and `--monotonic`, which takes a series of renders with one part pushed progressively
    toward the camera and asserts the number RISES. A probe that cannot be made to report a
    fault on demand has no demonstrated power to report one at all.
"""
import json
import math
import os
import sys

try:
    import numpy as np
except ImportError:
    np = None


def robust_z(vals):
    """Median/MAD, so a few broken characters cannot inflate the scale that should catch them."""
    v = np.asarray(vals, dtype=float)
    med = np.median(v)
    mad = np.median(np.abs(v - med))
    if mad == 0:
        return np.zeros_like(v), med, 0.0
    return 0.6745 * (v - med) / mad, med, mad


def overlap_floor(mad, min_region_px):
    """The smallest denominator a RATE can be ranked over. DERIVED from the population.

    Returns (floor_px, derivation) -- the second is the sentence the output prints, because a
    threshold whose origin is not stated beside it becomes a magic number within a week.

    One pixel of a fraction over N px is worth 1/N. The ranking is done in robust-z units,
    whose unit IS the MAD. So when 1/N exceeds the MAD, a single pixel moves the row by more
    than a whole z and the rate is quantised more coarsely than the scale ranking it. That is
    not a noisy measurement, it is an unrankable one, and `ceil(1/MAD)` is where it starts.

    Held at no less than `min_region_px`, the floor the FACE-REGION test already applies to its
    own region at the same resolution -- it held out Lola Bunny at 172 px. A test that guards
    one denominator at 200 px and the other at nothing is inconsistent in the direction that
    flatters the result.

    WITHOUT numpy there is no MAD, so there is no derived part: the floor is `min_region_px`
    alone and the derivation says so rather than implying a calculation happened.
    """
    if not mad or mad <= 0.0:
        return int(min_region_px), ("floor = min_region_px %d px (no MAD available, so NOTHING "
                                    "was derived -- this is the face-region floor reused, not a "
                                    "population result)" % int(min_region_px))
    derived = int(math.ceil(1.0 / mad))
    mr = int(min_region_px)
    floor = max(derived, mr)
    # THE SENTENCE MUST NOT OVERSTATE THE BOUND THAT DID NOT BIND. "below the floor one pixel
    # is worth more than a z" is only true of the DERIVED floor; when min_region_px is the
    # higher of the two, a pixel at the floor is worth 1/(floor*MAD) of a z and saying
    # otherwise is a reason contradicting its own number -- the defect fixed two tests down.
    if derived >= mr:
        why = ("the DERIVED bound binds. Below %d px one pixel moves a row's z by more than 1, "
               "so the rate is quantised more coarsely than the scale ranking it." % floor)
    else:
        why = ("the min_region_px bound binds and the derived one (%d px) is NOT doing the work "
               "-- at the floor one pixel is worth %.2f of a z, which is coarse but rankable. "
               "This floor is the face-region test's, reused for consistency; the population "
               "would have allowed a weaker one." % (derived, (1.0 / floor) / mad))
    return floor, ("floor = %d px = max(ceil(1/MAD) = %d, min_region_px = %d); %s"
                   % (floor, derived, mr, why))


def guard_overlap(rows, floor):
    """Hold out rows whose denominator is below the floor. Returns the rows it held out.

    A hold-out, NOT a drop: it writes `depth_out`, which is the same field every other
    unmeasurable reason uses, so the character is printed by name under "HELD OUT -- unmeasured,
    NOT clean" with the pixel count that disqualified it. A cutoff that removes rows without
    naming them is how a sweep came to split dark characters in half and invent three faults.
    """
    held = []
    for r in rows:
        if r["depth_out"]:
            continue
        if r["overlap_px"] < floor:
            r["depth_out"] = ("overlap denominator %d px < the %d px floor -- a rate over this "
                              "many pixels cannot be ranked (see overlap_floor)"
                              % (r["overlap_px"], floor))
            held.append(r)
    return held


def load(paths):
    """Accept files or directories; a directory contributes its part_overlap.json."""
    runs = []
    for p in paths:
        if os.path.isdir(p):
            cand = os.path.join(p, "part_overlap.json")
            if os.path.isfile(cand):
                runs.append((cand, json.load(open(cand, "r", encoding="utf-8"))))
            else:
                print("  no part_overlap.json in %s -- SKIPPED (this is not a clean result)" % p)
        elif os.path.isfile(p):
            runs.append((p, json.load(open(p, "r", encoding="utf-8"))))
        else:
            print("  %s does not exist -- SKIPPED (this is not a clean result)" % p)
    return runs


def _med(xs):
    return sorted(xs)[len(xs) // 2] if xs else None


def _static(r):
    return r.get("motion") == "no_animator"


def summarise(ch, min_region=200):
    """Per-character numbers, plus a separate reason for each test that could not run."""
    frames = ch.get("frames_data") or []

    depth = [f["aux_over_body"] for f in frames if f.get("aux_over_body") is not None]
    rdepth = [f["body_over_aux"] for f in frames if f.get("body_over_aux") is not None]
    overlap = [f.get("depth_overlap_px", 0) for f in frames]
    head_lo = [f["head_occlusion_lo"] for f in frames if f.get("head_occlusion_lo") is not None]
    head_hi = [f["head_occlusion_hi"] for f in frames if f.get("head_occlusion_hi") is not None]

    attribution = {}
    for f in frames:
        for k, v in (f.get("head_occluded_by") or {}).items():
            attribution[k] = attribution.get(k, 0) + int(v)

    worst_part = (None, None)
    for f in frames:
        for p in f.get("parts") or []:
            occ = p.get("occlusion")
            if occ is None:
                continue
            if worst_part[1] is None or occ > worst_part[1]:
                worst_part = (p.get("part"), occ)

    # Reasons are per-test, and the shared ones come first so they are not repeated.
    shared = None
    if ch.get("error"):
        shared = "ERROR: %s" % ch["error"]
    elif ch.get("parts_found", 0) == 0:
        shared = "no renderers found -- nothing was rendered"
    elif ch.get("motion_control") == "FAILED":
        shared = "motion control FAILED -- animator present but not one pixel moved"

    depth_out = shared
    if not depth_out:
        if ch.get("motion_control") == "no_animator":
            depth_out = "no animator -- no humanoid map, so body cannot be split from hair"
        elif not ch.get("depth_measurable", False):
            if ch.get("aux_tris", 0) == 0:
                depth_out = ("every triangle is weighted to a humanoid bone -- no hair/cloth half "
                             "exists to be drawn in the wrong order")
            elif ch.get("body_tris", 0) == 0:
                depth_out = "no triangle is weighted to a humanoid bone -- no body half to be drawn over"
            else:
                depth_out = "depth pass unavailable (shader missing?)"
        elif not depth:
            depth_out = "depth overlap region empty -- the two halves never overlap on screen"

    head_out = shared
    if not head_out:
        if ch.get("motion_control") == "no_animator":
            head_out = ("no animator -- no humanoid map, so no head region exists and no frame "
                        "produced a measurement")
        elif ch.get("head_region_tris", 0) == 0:
            head_out = ("no head triangles -- nothing is dominantly weighted to the humanoid "
                        "Head/Jaw/eye bones (this rig's face is on another bone)")
        elif not head_lo:
            # A REASON MUST NOT CONTRADICT ITS OWN NUMBER. This branch used to assert "head region
            # below the minimum pixel count (2400 px at f0)" against a minimum of 200, because it
            # was the catch-all for "no frame produced a measurement" and assumed the only possible
            # cause. A held-out character is already one nobody will look at twice; giving it a
            # self-contradictory explanation is how a hold-out gets dismissed as noise.
            px = ch.get("head_region_px_f0", 0)
            if px < min_region:
                head_out = "head region %d px < the %d px minimum" % (px, min_region)
            else:
                head_out = ("head region found (%d px) but no frame produced a measurement -- "
                            "reason unknown, which is itself worth looking at" % px)

    return {
        "name": ch.get("name"),
        "depth_out": depth_out,
        "head_out": head_out,
        "shared_out": shared,
        "motion": ch.get("motion_control"),
        "parts_found": ch.get("parts_found", 0),
        "body_tris": ch.get("body_tris", 0),
        "aux_tris": ch.get("aux_tris", 0),
        "head_px": ch.get("head_region_px_f0", 0),
        "head_note": ch.get("head_note", ""),
        "frames": len(frames),
        "overlap_px": max(overlap) if overlap else 0,
        "depth_max": max(depth) if depth else None,
        "depth_med": _med(depth),
        "rdepth_max": max(rdepth) if rdepth else None,
        "max_lo": max(head_lo) if head_lo else None,
        "med_lo": _med(head_lo),
        "max_hi": max(head_hi) if head_hi else None,
        "attribution": attribution,
        "worst_part": worst_part,
    }


def monotonic(paths):
    """THE POSITIVE CONTROL. Push a part toward the camera and the number must rise with it."""
    runs = load(paths)
    rows = []
    for path, run in runs:
        for ch in run.get("characters") or []:
            s = summarise(ch, int(run.get("min_region_px") or 200))
            rows.append((float(run.get("push_z") or 0.0), run.get("push_part"), s, os.path.basename(path)))
    rows.sort(key=lambda r: r[0])

    print("=" * 78)
    print("POSITIVE CONTROL: synthetic occlusion must RISE with the pushed distance")
    print("=" * 78)
    print("%-9s %-14s %-18s %12s %12s %10s"
          % ("push_z", "pushed part", "character", "depth_viol", "face_occ", "overlap_px"))
    series_d, series_f = [], []
    for z, part, s, _src in rows:
        d = "unmeasured" if s["depth_max"] is None else "%.6f" % s["depth_max"]
        o = "unmeasured" if s["max_lo"] is None else "%.6f" % s["max_lo"]
        print("%-9.4f %-14s %-18s %12s %12s %10d"
              % (z, (part or "-")[:14], (s["name"] or "?")[:18], d, o, s["overlap_px"]))
        if s["depth_out"]:
            print("          depth held out: %s" % s["depth_out"])
        else:
            series_d.append((z, s["depth_max"]))
        if s["head_out"]:
            print("          face  held out: %s" % s["head_out"])
        else:
            series_f.append((z, s["max_lo"]))

    def verdict(series, label):
        print()
        if len(series) < 2:
            print("%s: INCONCLUSIVE -- fewer than two measurable points. That is a statement about"
                  % label)
            print("  this control run, and the test stays UNVALIDATED.")
            return 2
        rises = all(series[i + 1][1] >= series[i][1] - 1e-9 for i in range(len(series) - 1))
        grew = series[-1][1] > series[0][1]
        print("%s points: %s" % (label, ", ".join("%.3fm->%.6f" % (z, o) for z, o in series)))
        print("  monotonic non-decreasing: %s" % rises)
        print("  rose overall: %s (by %.6f)" % (grew, series[-1][1] - series[0][1]))
        if grew and rises:
            print("  PASSED -- the test reports more fault as more fault is introduced, so a zero")
            print("  from it is a statement about the character.")
            return 0
        print("  FAILED -- until this passes, every zero is a statement about the probe.")
        return 1

    rc_d = verdict(series_d, "DEPTH-ORDER")
    rc_f = verdict(series_f, "FACE-REGION")
    print()
    if rc_d == 0:
        print("The depth-order test is VALIDATED. That is the one the roster verdict rests on.")
    else:
        print("The depth-order test is NOT validated. Do not report a clean roster from it.")
    return rc_d


def main():
    args = list(sys.argv[1:])
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--monotonic":
        return monotonic(args[1:])

    topn = 12
    if "--top" in args:
        i = args.index("--top")
        topn = int(args[i + 1])
        del args[i:i + 2]
    # The ungated run, kept so the guard's effect is always checkable against it rather than
    # taken on trust. Everything the guard removes is still printed, by name, with its number.
    guard = "--no-overlap-guard" not in args
    args = [a for a in args if a != "--no-overlap-guard"]

    runs = load(args)
    if not runs:
        print("NOTHING LOADED. That is a failure of this invocation, not a clean roster.")
        return 2

    rows = []
    meta = runs[0][1]
    for _, run in runs:
        for ch in run.get("characters") or []:
            rows.append(summarise(ch, int(run.get("min_region_px") or 200)))

    f_ok = [r for r in rows if not r["head_out"]]
    f_out = [r for r in rows if r["head_out"]]

    # ---------------------------------------------------------------- the denominator guard
    # This runs BEFORE the control gates print, so a character held out for a denominator too
    # small to rank appears in the same named hold-out list as every other unmeasurable one.
    min_region = int(meta.get("min_region_px") or 200)
    ungated = [r for r in rows if not r["depth_out"]]
    ungated_order = [r["name"] for r in sorted(ungated, key=lambda r: -r["depth_max"])]
    floor, derivation, floor_pass2, held = 0, "guard DISABLED by --no-overlap-guard", None, []
    mad1 = 0.0
    if guard:
        v1 = [r["depth_max"] for r in ungated]
        mad1 = robust_z(v1)[2] if (np is not None and len(v1) > 2) else 0.0
        floor, derivation = overlap_floor(mad1, min_region)
        held = guard_overlap(rows, floor)
        # SECOND PASS. The floor came from a population that included the rows it just removed,
        # so re-derive it on what survived and SAY whether it moved. One pass and a report: a
        # loop that settles silently is a cutoff choosing its own survivors.
        surv = [r["depth_max"] for r in rows if not r["depth_out"]]
        mad2 = robust_z(surv)[2] if (np is not None and len(surv) > 2) else 0.0
        floor_pass2 = overlap_floor(mad2, min_region)[0]

    d_ok = [r for r in rows if not r["depth_out"]]
    d_out = [r for r in rows if r["depth_out"]]

    print("=" * 78)
    print("CONTROL GATES -- read these before any result below")
    print("=" * 78)
    print("render: res=%s frames=%s diff lo=%s hi=%s, min head region=%s px"
          % (meta.get("res"), meta.get("frames"), meta.get("diff_lo"),
             meta.get("diff_hi"), meta.get("min_region_px")))
    print("characters in run:                  %d" % len(rows))
    print("overlap denominator guard:          %s" % ("ON" if guard else "OFF (--no-overlap-guard)"))
    print("  %s" % derivation)
    if guard:
        print("  held out by the guard:            %d of %d otherwise-measurable"
              % (len(held), len(ungated)))
        if floor_pass2 != floor:
            print("  SECOND PASS MOVED THE FLOOR: %d px -> %d px on the surviving population."
                  % (floor, floor_pass2))
            print("  The floor is NOT re-applied at the new value. It is reported because a floor")
            print("  that moves when its own filtering is undone is a floor partly chosen by the")
            print("  rows it removed; re-run with --no-overlap-guard and compare before trusting")
            print("  the tail of this ranking.")
        else:
            print("  second pass on the surviving population re-derives the SAME floor (%d px)" % floor)
    print("DEPTH-ORDER test looked at:         %d   (held out %d)" % (len(d_ok), len(d_out)))
    print("FACE-REGION test looked at:         %d   (held out %d)" % (len(f_ok), len(f_out)))
    if d_out:
        print()
        print("HELD OUT of the DEPTH-ORDER test -- unmeasured, NOT clean:")
        for r in sorted(d_out, key=lambda x: x["name"] or ""):
            print("  %-24s %s" % ((r["name"] or "?")[:24], r["depth_out"]))
    if f_out:
        print()
        print("HELD OUT of the FACE-REGION test -- unmeasured, NOT clean:")
        for r in sorted(f_out, key=lambda x: x["name"] or ""):
            print("  %-24s %s" % ((r["name"] or "?")[:24], r["head_out"]))
    if not d_ok and not f_ok:
        print()
        print("NO CHARACTER WAS MEASURED BY EITHER TEST. Every zero here is about the probe.")
        return 1

    # ------------------------------------------------------------------ depth order, primary
    print()
    print("=" * 78)
    print("1. DEPTH-ORDER VIOLATION, ranked. Fraction of the body/hair overlap where hair or")
    print("   cloth is VISIBLE while the body is NEARER. A fringe does NOT appear here.")
    print("=" * 78)
    if d_ok:
        vals = [r["depth_max"] for r in d_ok]
        mad_rank = 0.0
        if np is not None and len(vals) > 2:
            z, med, mad = robust_z(vals)
            mad_rank = float(mad)
            print("population: median %.6f, MAD %.6f (no fixed threshold is invented)" % (med, mad))
            for r, zz in zip(d_ok, z):
                r["z"] = float(zz)
        else:
            for r in d_ok:
                r["z"] = float("nan")
        d_ok.sort(key=lambda r: r["depth_max"], reverse=True)
        print()
        print("`viol_px` is the COUNT behind the rate; `overlap_px` is the DENOMINATOR, not a")
        print("count of anything wrong. `z/px` is what ONE pixel is worth in z -- at 0.5, this")
        print("row's position is three pixels wide.")
        print()
        print("%-22s %10s %10s %6s %8s %10s %6s %9s"
              % ("character", "worst", "median", "z", "viol_px", "overlap_px", "z/px", "reverse"))
        for r in d_ok[:topn]:
            rv = "-" if r["rdepth_max"] is None else "%.6f" % r["rdepth_max"]
            viol = int(round(r["depth_max"] * r["overlap_px"]))
            # In the SAME MAD the `z` column is expressed in, so the two are readable together.
            zpx = ((1.0 / r["overlap_px"]) / mad_rank) if (mad_rank > 0 and r["overlap_px"]) else None
            print("%-22s %10.6f %10.6f %6.1f %8d %10d %6s %9s"
                  % ((r["name"] or "?")[:22], r["depth_max"], r["depth_med"] or 0.0,
                     r["z"], viol, r["overlap_px"],
                     "-" if zpx is None else "%.2f" % zpx, rv))

        # WHAT THE GUARD CHANGED, against the ranking taken before it ran. Without this the
        # guard is unfalsifiable from its own output: a tidy table says nothing about whether
        # the cutoff or the data produced the order.
        if guard:
            gated_order = [r["name"] for r in d_ok]
            print()
            if not held:
                print("GUARD CHANGED NOTHING: no character's denominator was below the floor, so")
                print("this ranking is identical to --no-overlap-guard. The guard is here for the")
                print("next run, not this one.")
            else:
                # IT REPORTS THE REMOVALS, NOT A COLUMN OF RANK SHIFTS. Dropping rows cannot
                # reorder the rows that remain -- the sort key is unchanged -- so every
                # survivor below a removal shifts up by one and a "moved" marker fires on all
                # of them. The first version of this block printed exactly that: nine rows
                # flagged as moved, not one of which had changed place relative to any other,
                # which is a signal that teaches a reader to ignore it. What a reader cannot
                # get anywhere else is WHERE the removed rows sat, because a guard that
                # quietly removed the TOP of the ranking is the one case that changes the
                # conclusion rather than tidying it.
                print("WHAT THE GUARD REMOVED, with the rank each held in the ungated ranking.")
                print("Removal cannot reorder the survivors, so these rows ARE the whole change:")
                for r in sorted(held, key=lambda r: ungated_order.index(r["name"])
                                if r["name"] in ungated_order else 10 ** 6):
                    rank = ungated_order.index(r["name"]) + 1 if r["name"] in ungated_order else 0
                    viol = int(round(r["depth_max"] * r["overlap_px"]))
                    flag = "   <- THE GUARD REMOVED THE TOP ROW" if rank == 1 else ""
                    print("  ungated rank %2d  %-22s %.6f over %d px = %d violating px%s"
                          % (rank, (r["name"] or "?")[:22], r["depth_max"],
                             r["overlap_px"], viol, flag))
                print("Re-run with --no-overlap-guard to see them back in place.")
        nz = [r for r in d_ok if r["depth_max"] > 0]
        print()
        print("characters with ANY depth-order violation: %d of %d measured" % (len(nz), len(d_ok)))
        if not nz:
            print("  Every measured character reads EXACTLY ZERO. That is only a finding if the")
            print("  positive control passed -- run --monotonic and read its verdict first.")
    else:
        print("  no character was measurable by this test")

    # ------------------------------------------------------------------ face region, secondary
    print()
    print("=" * 78)
    print("2. FACE-REGION OCCLUSION, ranked. SECONDARY: a fringe reads the same as a fault.")
    print("=" * 78)
    if f_ok:
        moved = [r for r in f_ok
                 if r["max_lo"] is not None and r["max_hi"] is not None
                 and r["max_lo"] > 0.02 and r["max_hi"] < 0.5 * r["max_lo"]]
        print("threshold sensitivity: %d of %d lose more than half their occlusion between diff>%s"
              % (len(moved), len(f_ok), meta.get("diff_lo")))
        print("  and diff>%s -- for those the cutoff is doing the work:" % meta.get("diff_hi"))
        if moved:
            for r in moved[:10]:
                print("    %-24s lo=%.4f hi=%.4f" % ((r["name"] or "?")[:24], r["max_lo"], r["max_hi"]))
        else:
            print("    (none -- the verdicts are not an artefact of the cutoff)")
        f_ok.sort(key=lambda r: r["max_lo"], reverse=True)
        print()
        print("%-24s %9s %9s %8s  %s" % ("character", "worst", "median", "head_px", "occluded by"))
        for r in f_ok[:topn]:
            occl = ", ".join("%s:%d" % (k, v) for k, v in
                             sorted(r["attribution"].items(), key=lambda kv: -kv[1])[:3]) or "-"
            print("%-24s %9.4f %9.4f %8d  %s"
                  % ((r["name"] or "?")[:24], r["max_lo"], r["med_lo"] or 0.0, r["head_px"], occl))
    else:
        print("  no character was measurable by this test")

    print()
    print("3. Other parts occluded by the character's own geometry (the 'hand through a skirt'")
    print("   half), worst part per character:")
    # A character whose bundle failed to load, or whose animator never advanced, has frames that
    # say NOTHING -- so its per-part numbers must not appear here. This list used to be built from
    # every row, which printed a tidy occlusion figure for a character held out two sections above
    # for having no usable frames at all.
    bypart = sorted((r for r in rows if r["worst_part"][1] is not None and not r["shared_out"]),
                    key=lambda r: -r["worst_part"][1])
    if bypart:
        for r in bypart[:topn]:
            # A character with no Animator is NOT a broken measurement -- its frames are identical
            # by construction, which is a correct reading of something that cannot animate. But a
            # figure taken from one settled pose is weaker evidence than one taken across motion,
            # since a static render has already cleared a character that was broken on this
            # project. So it is included and labelled, not silently mixed in.
            tag = " (static: no animator)" if r["name"] and _static(r) else ""
            print("  %-24s %-28s %.4f%s" % ((r["name"] or "?")[:24], (r["worst_part"][0] or "?")[:28],
                                            r["worst_part"][1], tag))
    else:
        print("  (nothing measurable -- most characters on this roster are a SINGLE renderer, so")
        print("   there are no sibling parts to ablate against each other)")

    print()
    print("=" * 78)
    print("WHAT THIS STILL CANNOT SEE -- say it rather than let the output imply otherwise")
    print("=" * 78)
    print("""  * SELF-OCCLUSION WITHIN ONE HALF is invisible. The depth test compares the body half
    against the hair/cloth half, so hair drawn over other hair, or an arm through a torso,
    does not appear. Both halves are single groups, not per-bone parts.
  * HAIR RIGIDLY WEIGHTED TO A HUMANOID BONE COUNTS AS BODY. Where an author weighted hair to
    Head or Neck rather than to a spring chain, it is inside the body half and cannot violate
    against it. Such a character reads cleaner than it is, and the bone histogram in the log
    is what shows it.
  * ONE CAMERA, ONE YAW PER RUN. Geometry hidden from this angle is untested; run again with
    another -yaw.
  * A 3 mm EPSILON. Surfaces closer together than that are treated as coincident, so skin-tight
    cloth is deliberately not flagged.
  * NOTHING ABOUT WHETHER A VIOLATION IS VISIBLE TO A PLAYER. A two-pixel violation at the back
    of a head is a true positive and not worth fixing; ranking exists for that reason, and the
    painted _WORST_*.png is there so the judgement is made by eye and not by a threshold.
  * SHADOWS ARE OFF in these renders, so this is not the game's look. Ablation asks "did
    removing this change the picture", and a cast shadow changes it without the part being
    visible there.
  * A HELD-OUT CHARACTER IS UNMEASURED, NOT CLEAN.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
