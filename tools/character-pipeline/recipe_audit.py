# -*- coding: utf-8 -*-
"""Which installed characters have NO recipe recorded anywhere in README.md?

    python recipe_audit.py [README.md] [characters-dir]

WHY THIS EXISTS, and why it is not a grep. The build logs that recipes were harvested from are
GONE -- 43 logs survive on this machine, 19 carry an `ARGV:` line, and they name three
characters, all built in the last three days. Nothing survives from the window the 2026-11-15
recipe archaeology drew on, and `recipes.py` / `findrecipe.py` are not in this folder either.
**So the recipe table in README.md is now the only surviving record of how these characters were
built**, and knowing which rows are MISSING is worth more than it used to be.

A naive `grep "^| <name> |"` gets this wrong, and got it wrong three times in one afternoon --
reporting Sayuri, Link and Judy Hopps as having malformed or missing recipes when all three are
recorded and correct:

  * `| Sayuri / Aiko | cc_base / mixamo | 1.70 | ...`   TWO characters share one row
  * `| Link (OoT) | linkoot | 1.65 | ...`               the key is QUALIFIED
  * Judy Hopps was fine; the grep matched a row in a DIFFERENT table that happens to start
    with her name, and read `2 | 1 | 0` as a rig and a height.

This file already records the same shape of mistake -- *"absence as a property of the world. Two
tables in one file, and the one that was searched is the one that did not have it."* So this
tool splits compound keys, strips qualifiers, and REQUIRES a plausible rig and height before it
believes a row is a recipe at all. A row it cannot parse is reported as unparsed, never as
absent, because those are opposite findings.
"""
import io
import os
import re
import sys

README = sys.argv[1] if len(sys.argv) > 1 else "README.md"
CHARS = sys.argv[2] if len(sys.argv) > 2 else (
    os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\FatalException\YARG-FE"
                       r"\release\custom\characters"))

RIG = re.compile(r"^\*{0,2}[a-z_][a-z_0-9]*\*{0,2}$")


def keys(cell):
    """'Sayuri / Aiko' -> ['Sayuri','Aiko']; 'Link (OoT)' -> ['Link (OoT)','Link']."""
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


def main():
    installed = sorted(f[:-9] for f in os.listdir(CHARS) if f.endswith(".yargchar"))
    found, unparsed, recovered = {}, [], {}
    for ln, line in enumerate(io.open(README, encoding="utf-8"), 1):
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 3:
            continue
        # A RECOVERED row is an inference measured out of a bundle, not a record. It is
        # counted separately and ON PURPOSE -- it happened to be excluded anyway, because
        # its values are italicised and float('*1.84*') raises, but relying on that would
        # mean un-italicising a row silently changed what this audit reports.
        if len(c) > 3 and "RECOVERED" in c[3]:
            for n in keys(c[0]):
                recovered.setdefault(n, (c[1].strip("*` "), c[2].strip("*` "), ln))
            continue
        names, rigs, h = keys(c[0]), [r.strip("*` ") for r in re.split(r"\s*/\s*", c[1])], c[2]
        if not names or not all(RIG.match(r or "") for r in rigs):
            continue
        try:
            float(h.split("/")[0].strip())
        except ValueError:
            # a row that LOOKS like a recipe but whose height will not parse is worth seeing
            if len(names) and names[0] in installed and len(c) > 3:
                unparsed.append((ln, c[0], c[1], c[2]))
            continue
        for i, n in enumerate(names):
            found.setdefault(n, []).append((ln, rigs[min(i, len(rigs) - 1)], h))

    missing = [n for n in installed if n not in found]
    rec_only = [n for n in missing if n in recovered]
    none_at_all = [n for n in missing if n not in recovered]
    print("installed characters      : %d" % len(installed))
    print("with a RECORDED recipe    : %d" % (len(installed) - len(missing)))
    print("with a RECOVERED row only : %d  (inferred from the bundle, not a record)"
          % len(rec_only))
    print("with NOTHING              : %d" % len(none_at_all))
    if rec_only:
        print()
        for n in rec_only:
            r, h, ln = recovered[n]
            print("  RECOVERED  %-28s %-14s %-6s  (line %d)" % (n, r, h, ln))
    if none_at_all:
        print()
        for n in none_at_all:
            print("  NOTHING    %s" % n)
    if unparsed:
        print()
        print("rows that look like a recipe but whose height would not parse (UNPARSED, which")
        print("is NOT the same as missing -- look at them before trusting either column):")
        for ln, a, b, c3 in unparsed:
            print("  line %-6d %s | %s | %s" % (ln, a[:28], b[:18], c3[:18]))
    print()
    print("Compound keys and qualified names are split, so 'Sayuri / Aiko' and 'Link (OoT)'")
    print("both resolve. A plain grep for '^| <name> |' finds neither, and reports a recorded")
    print("recipe as missing -- which, with the build logs gone, would read as unrecoverable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
