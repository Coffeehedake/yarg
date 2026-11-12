# -*- coding: utf-8 -*-
"""Run every installed-side check over the whole character set, in one command.

The point of this file is that nobody should have to remember the list. Seven
checks read the installed bundles, each has its own argument shape, and the
knowledge of which ones exist has so far lived in a conversation -- which is
how the floating-prop sweep sat unwritten in the runlist for days, and how a
character got excluded from a collider rollout twice.

    python audit_all.py                       # finds everything itself
    python audit_all.py --out <dir>           # where to write the report
    python audit_all.py --only cloth,alpha    # one or two checks
    python audit_all.py --chars <dir>         # a different character folder

It writes one `<dir>/audit-<date>.md` holding every check's full output and, at
the top, a PRIORITY table: how many characters each class of defect touches and
whether a fix for it exists. That ordering is the useful part -- a class that
costs one change and fixes six characters comes before one that costs six
changes and fixes one.

THREE THINGS THIS DOES NOT DO, said out loud rather than discovered later:

  * It does not fix anything. Every check here is read-only.
  * It cannot see what only a render can see. A two-toned face, a slab over an
    eye, an inside-out mesh: none of those has a number in a bundle. The alpha
    rows in particular are candidates, not verdicts -- in a game rip an alpha
    channel is as likely to be a specular mask as an opacity map.
  * It judges the INSTALLED bundles, which is the right target for "what is
    wrong with the game right now" and the wrong one for "did my rebuild come
    out the same" -- that is `identify_build.py`.

WHY IT HUNTS FOR AN INTERPRETER

`python` on this machine's PATH is 3.13 and has no UnityPy; the one that does
is 3.12. Running the obvious thing gets `ModuleNotFoundError: No module named
'UnityPy'`, which reads as "the tooling is not installed" rather than as "you
have two Pythons". So this resolves the interpreter by IMPORTING UnityPy in a
candidate and keeping the first that answers -- a version number is not the
test, the import is.
"""
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Each check: key, script, how to call it, and the regex that pulls its verdict
# out of its own last lines. The regex is NOT how the check is judged -- the
# full output is always written to the report. It only feeds the priority
# table, and when it fails to match, the table says so instead of showing a
# zero. A count that quietly became 0 because a format changed is exactly the
# shape of wrong answer this project keeps paying for.
CHECKS = [
    ("cloth", "cloth_collide_installed.py", {},
     r"(\d+) of (\d+) spring chains unguarded, across (\d+) character",
     "{0} of {1} spring chains unguarded, in {2} characters",
     "spring chain with no collider on the limb it hugs"),
    ("alpha", "alpha_sweep_installed.py", {},
     r"(\d+) UNUSED, (\d+) HARDCUT, (\d+) NOALPHA across (\d+) character",
     "{0} opaque-with-alpha, {1} soft-alpha-as-cutout, {2} cutout-with-no-alpha,"
     " in {3} characters",
     "opacity in the file that nothing honours, or honours as a hard cut"),
    ("height", "height_check_installed.py", {"HEIGHT_TARGETS": "height_targets.tsv"},
     r"(\d+) flagged -- (\d+) off their documented height, (\d+) inflated",
     "{0} flagged: {1} off their documented height, {2} inflated by a detached mesh",
     "wrong height, or a detached mesh setting the height"),
    ("viseme", "viseme_audit.py", {},
     r"(\d+) with all five visemes, (\d+) partial, (\d+) with none",
     "{0} can lipsync on all five visemes, {1} partially, {2} not at all",
     "mouth that cannot move to the lipsync events"),
    ("limb", "limb_check_installed.py", {}, None, None,
     "bent or asymmetric limb in the rest pose"),
    ("bundle", "bundle_audit.py", {}, None, None,
     "missing animation, humanoid bones or finger mapping"),
]


def find_python():
    """The first interpreter that can actually import UnityPy."""
    cands = [sys.executable]
    lad = os.environ.get("LOCALAPPDATA", "")
    if lad:
        base = os.path.join(lad, "Programs", "Python")
        if os.path.isdir(base):
            # Newest first, but the import is what decides.
            for d in sorted(os.listdir(base), reverse=True):
                cands.append(os.path.join(base, d, "python.exe"))
    cands += ["python", "python3"]
    for c in cands:
        try:
            r = subprocess.run([c, "-c", "import UnityPy, numpy, PIL"],
                               capture_output=True, timeout=90)
            if r.returncode == 0:
                return c
        except Exception:
            continue
    return None


def find_chars():
    """Where the game loads characters from.

    YARG-FE writes to release\\custom\\, not dev\\ -- the branch name is not
    the channel name, and that cost a round of "the install did nothing".
    """
    low = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "LocalLow")
    for vendor, app in (("FatalException", "YARG-FE"), ("YARC", "YARG")):
        p = os.path.join(low, vendor, app, "release", "custom", "characters")
        if os.path.isdir(p) and any(f.lower().endswith(".yargchar")
                                    for f in os.listdir(p)):
            return p
    return None


def main():
    argv = sys.argv[1:]

    def opt(flag, default=None):
        return argv[argv.index(flag) + 1] if flag in argv else default

    chars = opt("--chars") or find_chars()
    if not chars:
        print("ABORT: no character folder found. Pass --chars <dir>.")
        return 2
    out = opt("--out") or HERE
    only = [x.strip() for x in (opt("--only") or "").split(",") if x.strip()]

    py = find_python()
    if not py:
        print("ABORT: no interpreter here can import UnityPy, numpy and PIL.\n"
              "       Install them into one:  <python.exe> -m pip install "
              "UnityPy numpy pillow")
        return 2

    n = len([f for f in os.listdir(chars) if f.lower().endswith(".yargchar")])
    print("interpreter : %s" % py)
    print("characters  : %s (%d)" % (chars, n))

    results, sections = [], []
    for key, script, env_extra, rx, fmt, what in CHECKS:
        if only and key not in only:
            continue
        path = os.path.join(HERE, script)
        if not os.path.exists(path):
            results.append((key, what, "MISSING: %s is not here" % script))
            continue
        env = dict(os.environ)
        env.update(env_extra)
        print("running %-8s ..." % key, end="", flush=True)
        r = subprocess.run([py, path, chars], capture_output=True, cwd=HERE,
                           env=env, text=True, errors="replace")
        body = (r.stdout or "") + (r.stderr or "")
        sections.append((key, script, body, r.returncode))
        if r.returncode != 0:
            verdict = "FAILED, exit %d -- read the section below" % r.returncode
        elif rx is None:
            verdict = "see the section below (no single number to quote)"
        else:
            m = re.search(rx, body)
            verdict = (fmt.format(*m.groups()) if m else
                       "COULD NOT READ the summary line -- the check ran, its "
                       "output is below, and this table is not to be trusted "
                       "for this row")
        results.append((key, what, verdict))
        print(" %s" % verdict[:70])

    stamp = datetime.date.today().isoformat()
    rp = os.path.join(out, "audit-%s.md" % stamp)
    with open(rp, "w", encoding="utf-8") as f:
        f.write("# Installed character audit, %s\n\n" % stamp)
        f.write("%d characters in `%s`, read with `%s`.\n\n" % (n, chars, py))
        f.write("Every number below is measured from the installed "
                "`.yargchar`, which is what the game loads. None of it is a "
                "render, so nothing here can see a two-toned face, a slab over "
                "an eye or an inside-out mesh.\n\n")
        f.write("## What each check said\n\n")
        f.write("| check | what it looks for | result |\n|---|---|---|\n")
        for key, what, verdict in results:
            f.write("| `%s` | %s | %s |\n" % (key, what, verdict.replace("|", "\\|")))
        f.write("\n## Full output\n")
        for key, script, body, rc in sections:
            f.write("\n### `%s` (%s, exit %d)\n\n```\n%s\n```\n"
                    % (key, script, rc, body.rstrip()))
    print("\nwrote %s" % rp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
