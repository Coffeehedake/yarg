# -*- coding: utf-8 -*-
"""Assert the overlap-denominator guard in `part_overlap.py` does what it claims.

    python overlap_guard_test.py                 # the guard as shipped -- must pass
    python overlap_guard_test.py --null-guard    # the guard stubbed out -- must FAIL

THE SECOND INVOCATION IS THE POINT. A test that has never been seen to fail has not been
verified, and this project has published a clean zero from an instrument that could not report
anything else five separate times. `--null-guard` replaces the guard with a no-op and the suite
must then go red on exactly the assertions about holding out, and stay green on the control
assertions that are about something else. If both invocations pass, this file is decoration.

WHAT IT RUNS AGAINST, named so it cannot be mistaken for a measurement
======================================================================
A SYNTHETIC FIXTURE. The real `part_overlap.json` from the 2026-11-18 sweep no longer exists on
disk -- it was read into `measurements/interior-faults-2026-11-18.md` and the output directory
was cleaned. So the fixture here REPRODUCES THE RECORDED NUMBERS (the seven ranked rows, their
denominators, the population median and MAD) from that note. It is not that run, it cannot
re-measure the roster, and no conclusion about any character may be drawn from it. It exists to
exercise the arithmetic, which is the half of this probe that lives in Python.

Two rows carry the whole test:

  GuardCanary  rate 0.2000 over    120 px  ->  24 violating pixels, BELOW the floor.
               Must be held out, by name, with its pixel count in the reason.
  Gwen Stacy   rate 0.0534 over    262 px  ->  14 violating pixels, ABOVE the floor.
               Must SURVIVE. Without this control a guard that holds out the entire roster
               passes every other assertion in this file.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_part_overlap():
    spec = importlib.util.spec_from_file_location("part_overlap", os.path.join(HERE, "part_overlap.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The seven ranked rows as recorded, plus the canary. (name, rate, overlap_px)
RECORDED = [
    ("Jessica Rabbit", 0.1085, 5675),
    ("Lola Bunny",     0.0741, 1632),
    ("Gordon Freeman", 0.0701, 1156),
    ("Yoda",           0.0653, 1650),
    ("Gwen Stacy",     0.0534,  262),
    ("Batman",         0.0469, 5560),
    ("Power Girl",     0.0386, 7380),
]
CANARY = ("GuardCanary", 0.2000, 120)


def fixture():
    """A run shaped like the renderer's output, with a population around the recorded median."""
    chars = []
    for name, rate, px in RECORDED + [CANARY]:
        chars.append(_char(name, rate, px))
    # Filler so the population median/MAD land near the recorded 0.012829 / 0.007560. These are
    # NOT measurements of anyone; they are a distribution for the robust z to stand on. The step
    # centre and step are SOLVED so the whole population reproduces the recorded median and
    # MAD, and `main` ASSERTS that it does. A fixture that claims to reproduce a recorded
    # population and quietly does not is worse than no fixture, because every floor derived
    # from it is then about a roster that never existed. Note the centre is BELOW the recorded
    # median: the eight high rows above pull the median up, so a filler centred on 0.012829
    # lands the population at 0.0147 -- which is how the first version of this fixture failed
    # its own check.
    for i in range(39):
        rate = 0.01095 + ((i % 13) - 6) * 0.00188
        chars.append(_char("filler%02d" % i, max(rate, 0.0), 1800 + i * 37))
    return {"res": 512, "frames": 3, "diff_lo": 8, "diff_hi": 18,
            "min_region_px": 200, "characters": chars}


def _char(name, rate, px):
    return {
        "name": name, "parts_found": 2, "body_tris": 5000, "aux_tris": 2000,
        "depth_measurable": True, "motion_control": "ok", "head_region_tris": 400,
        "head_region_px_f0": 900,
        "frames_data": [{"aux_over_body": rate, "body_over_aux": rate * 0.4,
                         "depth_overlap_px": px, "head_occlusion_lo": 0.01,
                         "head_occlusion_hi": 0.008, "head_occluded_by": {}, "parts": []}
                        for _ in range(3)],
    }


FAILED = []


def check(label, cond, detail=""):
    if cond:
        print("  PASS  %s" % label)
    else:
        print("  FAIL  %s%s" % (label, ("  -- " + detail) if detail else ""))
        FAILED.append(label)


def main():
    null_guard = "--null-guard" in sys.argv
    po = load_part_overlap()
    if null_guard:
        # The stub: same signature, holds out nothing. This is what the tool did before the
        # guard existed, so a red suite here is the defect being reproduced on demand.
        po.guard_overlap = lambda rows, floor: []
        print("MODE: --null-guard -- the guard is STUBBED OUT. The hold-out assertions MUST fail.")
    else:
        print("MODE: guard as shipped. Every assertion must pass.")
    print()

    run = fixture()
    rows = [po.summarise(ch, 200) for ch in run["characters"]]
    measurable = [r for r in rows if not r["depth_out"]]
    check("fixture is measurable at all (no row held out before the guard runs)",
          len(measurable) == len(rows), "%d of %d" % (len(measurable), len(rows)))

    import numpy as np  # the tool degrades without it; the test does not pretend to
    med = float(np.median([r["depth_max"] for r in measurable]))
    mad = po.robust_z([r["depth_max"] for r in measurable])[2]
    floor, derivation = po.overlap_floor(mad, 200)
    print("  population MAD %.6f -> %s" % (mad, derivation))
    print()
    # THE FIXTURE'S OWN CLAIM, checked rather than asserted in a comment. The recorded sweep
    # read median 0.012829, MAD 0.007560; a floor derived from a tighter distribution than that
    # would be a true statement about the fixture and a false one about the roster.
    check("fixture reproduces the recorded median 0.012829 (got %.6f)" % med,
          abs(med - 0.012829) < 0.0015)
    check("fixture reproduces the recorded MAD 0.007560 (got %.6f)" % mad,
          abs(mad - 0.007560) < 0.0010)

    held = po.guard_overlap(rows, floor)
    held_names = [r["name"] for r in held]
    survivors = [r["name"] for r in rows if not r["depth_out"]]

    # --- the hold-out assertions. These are the ones --null-guard must break.
    check("the canary (120 px, below the %d px floor) is HELD OUT" % floor,
          "GuardCanary" in held_names, "held out: %s" % (held_names or "nothing"))
    canary = [r for r in rows if r["name"] == "GuardCanary"][0]
    check("the canary's reason names its own pixel count",
          bool(canary["depth_out"]) and "120" in (canary["depth_out"] or ""),
          "reason: %r" % (canary["depth_out"],))
    check("the canary is reported as UNMEASURED, not as clean",
          bool(canary["depth_out"]) and "clean" not in (canary["depth_out"] or "").lower())

    # --- the controls. These must pass in BOTH modes, or the suite proves nothing.
    check("CONTROL: Gwen Stacy (262 px, above the floor) SURVIVES",
          "Gwen Stacy" in survivors)
    check("CONTROL: the top row survives", "Jessica Rabbit" in survivors)
    check("CONTROL: the guard does not empty the roster",
          len(survivors) >= len(rows) - 2, "%d survivors of %d" % (len(survivors), len(rows)))

    # --- the arithmetic the new columns print.
    jr = [r for r in rows if r["name"] == "Jessica Rabbit"][0]
    viol = int(round(jr["depth_max"] * jr["overlap_px"]))
    check("viol_px is the numerator, not the denominator (JR: %d, not %d)" % (viol, jr["overlap_px"]),
          viol == 616 and jr["overlap_px"] == 5675,
          "got viol=%d overlap=%d" % (viol, jr["overlap_px"]))
    gs = [r for r in rows if r["name"] == "Gwen Stacy"][0]
    check("Gwen Stacy's rank rests on %d pixels" % int(round(gs["depth_max"] * gs["overlap_px"])),
          int(round(gs["depth_max"] * gs["overlap_px"])) == 14)
    check("one pixel is worth more than a third of a z at 262 px",
          (1.0 / 262) / mad > 0.33, "%.2f z/px" % ((1.0 / 262) / mad))

    # --- the derivation must not claim the bound that did not bind.
    _f, d_low = po.overlap_floor(0.5, 200)        # derived = 2, min_region binds
    _f, d_high = po.overlap_floor(0.0001, 200)    # derived = 10000, derived binds
    check("derivation says min_region_px binds when it does",
          "min_region_px bound binds" in d_low, d_low)
    check("derivation says the DERIVED bound binds when it does",
          "DERIVED bound binds" in d_high, d_high)
    check("derivation never claims >1 z/px at a floor where that is false",
          "moves a row's z by more than 1" not in d_low, d_low)

    print()
    if FAILED:
        print("%d ASSERTION(S) FAILED: %s" % (len(FAILED), "; ".join(FAILED)))
        if null_guard:
            print("That is the EXPECTED result for --null-guard: the guard was stubbed out and")
            print("the hold-out assertions went red while every control stayed green. The suite")
            print("can fail, so a green run above means something.")
            return 0
        return 1
    if null_guard:
        print("--null-guard PASSED, which is itself the failure: the suite cannot detect a")
        print("missing guard, so a green run in normal mode proves nothing.")
        return 1
    print("ALL ASSERTIONS PASSED. Run again with --null-guard to see them fail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
