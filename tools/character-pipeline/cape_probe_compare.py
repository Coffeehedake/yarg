# -*- coding: utf-8 -*-
"""Compare CapeCollisionProbe runs, splitting GAUNTLET from the rest of the body.

    python cape_probe_compare.py <run.csv> [<run.csv> ...]

WHY THIS IS A FILE IN THE REPO AND NOT A SCRATCH SCRIPT. Every cape conclusion on this character
came out of an ad-hoc version of this comparison, and two of those conclusions had to be
retracted. The arithmetic is three lines; the part worth keeping is the GUARDS around it, which
are what the retractions were about:

  * **It refuses to compare runs of unequal coverage.** The probe's own default window covers
    28% of this clip, and sampling 38% of it on 2026-11-21 changed the sign of two results and
    produced a 40 mm severity ceiling that does not exist at full coverage. The probe now refuses
    a partial window, but a comparison can still line up two runs sampled differently, and the
    numbers look fine when it does.
  * **It states the SPLIT, because the single total hid which half moved.** The `blade*` bones
    parent through `fml_un_?_loarm`, so cape-into-blade is the cape passing through Batman's
    forearm gauntlets -- the fault Jay reported, in those words. A lever that fixes the torso and
    not the arms is a different answer from one that does both, and gravity 0.30 turned out to be
    exactly that: -37% overall, -29% at the gauntlets.
  * **It prints garment travel beside every result.** A cape that barely moves cannot clip, so
    "penetration fell" is only good news if travel did not collapse with it. Travel is the price
    tag on every one of these floats and it belongs in the same table as the benefit.

DEPTH-WEIGHTED, not a count: `sum(vertices * depth_mm)` over every row. A count of penetrating
vertices rose 1.7x on one arm while the vertex counts under it FELL 19%, because the tool had
moved its own denominator; weighting by depth and reporting the peak beside it is what made that
visible. The peak alone is one vertex on one frame and is noisy; the weighted total alone cannot
see a single limb buried to the elbow. Read both.
"""
import collections
import csv
import os
import re
import sys

GAUNTLET_BONES = ("blade",)


def die(msg):
    print("REFUSED: %s" % msg)
    sys.exit(1)


def load_rows(path):
    rows = []
    with open(path, newline="") as f:
        rdr = csv.DictReader(f)
        need = {"frame", "garment_bone", "into_body_bone", "vertices", "depth_mm"}
        missing = need - set(rdr.fieldnames or [])
        if missing:
            die("%s is missing column(s) %s -- is this a CapeCollisionProbe -out file?"
                % (os.path.basename(path), sorted(missing)))
        for r in rdr:
            rows.append((int(r["frame"]), r["garment_bone"], r["into_body_bone"],
                         int(r["vertices"]), float(r["depth_mm"])))
    return rows


def load_meta(csv_path):
    """Coverage and travel, read out of the run's Unity log rather than assumed."""
    stem = csv_path[:-4] if csv_path.lower().endswith(".csv") else csv_path
    meta = {"sampled": None, "clip_s": None, "travel_mm": None, "log": None}
    for cand in (stem + ".unity.log", stem + ".log"):
        if not os.path.isfile(cand):
            continue
        meta["log"] = cand
        txt = open(cand, "r", errors="replace").read()
        m = re.search(r"sampled (\d+) frame\(s\)", txt)
        if m:
            meta["sampled"] = int(m.group(1))
        m = re.search(r"clip \S+ \(([\d.]+)s\)", txt)
        if m:
            meta["clip_s"] = float(m.group(1))
        m = re.search(r"garment moved ([\d.]+) mm", txt)
        if m:
            meta["travel_mm"] = float(m.group(1))
        break
    return meta


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not paths:
        print(__doc__)
        return 2
    for p in paths:
        if not os.path.isfile(p):
            die("no such file: %s" % p)

    metas = {p: load_meta(p) for p in paths}

    # THE GUARD THAT EARNS THIS FILE. Unequal coverage is not a sparser measurement of the same
    # thing, it is a measurement of a different stretch of the animation.
    sampled = {p: m["sampled"] for p, m in metas.items()}
    known = [v for v in sampled.values() if v]
    if len(paths) > 1 and known:
        if len(set(known)) != 1:
            print("REFUSED: these runs do not cover the same animation.")
            for p in paths:
                print("    %-30s sampled %s frame(s)"
                      % (os.path.basename(p)[:30], sampled[p] or "unknown (no log beside it)"))
            print("  A truncated window changes which extremes exist, so these numbers are not")
            print("  comparable. Re-run the short arm(s) with the same -frames/-every.")
            sys.exit(1)
        if len(known) != len(paths):
            print("WARNING: %d of %d runs have no log beside them, so their coverage is "
                  "unverified." % (len(paths) - len(known), len(paths)))

    print("%-26s %9s %8s   %9s %8s   %9s %8s   %8s"
          % ("", "ALL dw", "peak", "GAUNTLET", "peak", "body", "peak", "travel"))
    base = None
    for p in paths:
        rows = load_rows(p)

        def agg(sel):
            s = [r for r in rows if sel(r)]
            return (sum(r[3] * r[4] for r in s), max((r[4] for r in s), default=0.0))

        is_g = lambda r: any(k in r[2].lower() for k in GAUNTLET_BONES)   # noqa: E731
        adw, apk = agg(lambda r: True)
        gdw, gpk = agg(is_g)
        bdw, bpk = agg(lambda r: not is_g(r))
        tv = metas[p]["travel_mm"]
        name = os.path.basename(p).replace(".csv", "")[:26]
        print("%-26s %9.0f %6.1fmm   %9.0f %6.1fmm   %9.0f %6.1fmm   %6s"
              % (name, adw, apk, gdw, gpk, bdw, bpk,
                 ("%.0fmm" % tv) if tv else "n/a"))
        if base is None:
            base = (adw, gdw, bdw, tv)
        elif base[0] and base[1]:
            d = lambda new, old: ("%+.0f%%" % (100.0 * (new - old) / old)) if old else "n/a"  # noqa: E731
            print("%-26s %9s %8s   %9s %8s   %9s %8s   %8s"
                  % ("  vs first:", d(adw, base[0]), "", d(gdw, base[1]), "",
                     d(bdw, base[2]), "", d(tv, base[3]) if (tv and base[3]) else ""))

    if known:
        m = metas[paths[0]]
        cov = ""
        if m["clip_s"]:
            cov = " of a %.2fs clip" % m["clip_s"]
        print("\nall runs sampled %d frame(s)%s" % (known[0], cov))

    # Where the gauntlet contact sits along the chains, since that is what decides whether a
    # float can reach it at all: a float holds a joint near its rest direction, so it is only
    # a lever where the rest pose already clears the body.
    rows = load_rows(paths[-1])
    per_joint = collections.Counter()
    for fr, gb, bb, nv, dp in rows:
        if any(k in bb.lower() for k in GAUNTLET_BONES):
            per_joint[gb] += nv * dp
    if per_joint:
        tot = sum(per_joint.values()) or 1.0
        print("gauntlet contact in %s, by garment bone:"
              % os.path.basename(paths[-1]).replace(".csv", ""))
        for bone, v in per_joint.most_common(6):
            print("    %-30s %5.1f%%" % (bone[:30], 100.0 * v / tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
