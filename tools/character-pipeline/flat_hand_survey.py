# -*- coding: utf-8 -*-
"""For each flat-handed installed character, did its SOURCE have knuckle bend to lose?

    python flat_hand_survey.py <downloads-dir> <scratch-dir> [name ...]

WHY. 42 of 65 installed characters read 0.0 degrees of knuckle bend. That is the roster norm and
says nothing on its own -- a hand is flat either because the author posed it flat, or because
the build flattened it. **Only the SOURCE separates those two**, and acting on the bundle alone
would mean rebuilding 42 characters to chase a model's own geometry.

Elite Terrorist is the worked case: his source carries 28.6 degrees and his bundle carried 0.0,
and recovering it needed `VRM_KEEP_REST_FINGERS=1` AND `VRM_EXPORT_POSE=rest` together.

WHAT A SOURCE IS, AND WHAT IT IS NOT. The ~25 `.vrm` under `Documents/YARG-Characters` are this
pipeline's OWN BUILD OUTPUTS. Measuring one answers "what did that build produce", not "what did
the author author", and a build that flattened the hand produces a flat `.vrm` every time. So
this reads the original download archives only.

AMBIGUITY IS MEASURED, NOT GUESSED AND NOT SKIPPED. Several characters have more than one
plausible archive -- Harley Quinn three, Prix three, Power Girl two, Sonic two, Judy two. This
file records that Iron Man had four candidate sources separable only by texture size, and that
the newest file is not the source, so picking one would produce a number indistinguishable from
a measurement.

**So every candidate is measured and all of them are printed.** If they agree, which one is
genuinely the source does not matter for this question and the answer stands; if they disagree,
that is said plainly and the character stays open. An earlier version of this tool skipped
ambiguous characters entirely, which turned ten of the forty-two into a silent gap.

NESTED ARCHIVES ARE UNPACKED. Ten archives hold their model inside a SECOND archive --
`the-rock.zip` contains `source/The_Rock.7z`, `peach-ssb4.zip` contains `source/model.zip`. The
first version did not recurse and reported all ten as "no model inside", which reads as a
missing source and was really a missing feature.

Each archive is extracted into its OWN EMPTY DIRECTORY and the model path is passed to Blender
as an argument, because a downloaded archive is untrusted input. The extraction is deleted
afterwards. Nothing in the repo or the install directory is touched.
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile

BLENDER = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, "knuckle_bend_source.py")

# character -> the archive(s) in Downloads that plausibly hold its source. More than one entry
# means AMBIGUOUS: reported, not measured.
MAP = {
    "Alastor": ["alastor.zip"],
    "Baby Groot": ["baby-groot-re-edited-textures.zip", "Baby Groot.fbx"],
    "Batman": ["batman-multiversus.zip", "batman__multiversus.glb"],
    "Chibi Rem": ["chibi-rem-confession.zip"],
    "Clone Trooper 501st": ["clone-trooper-phase2-501st.zip"],
    "Clone Trooper Shiny": ["clone-trooper-phase1-shiny-updated.zip"],
    "Gwen Stacy": ["gwen-stacy-downloadable.zip"],
    "Harley Quinn": ["harley-quinn-animated.zip", "harley-quinn-fbx-to-daz-studio.zip",
                     "harley-queen-more-like.zip"],
    "Iron Man Mark 85": ["iron-man-mark-85-rigged.zip"],
    "Jessica Rabbit": ["jessica-rabbit.zip", "jessica_rabbit.glb"],
    "Jinx": ["jinx-lowpoly-fanmodel.zip"],
    "Judy Hopps": ["judy-hopps-zootopia.zip", "judy-hopps-not-game-ready.zip"],
    "K-2SO": ["free-droide-de-seguridad-k-2so-by-oscar-creativo.zip"],
    "Killer Clown": ["killer-clown-v2-balatro-style.zip"],
    "Link": ["link-from-oot-smash-bros-interpretation.zip"],
    "Lola Bunny": ["lola-bunny-updated-multiversus.zip", "lola_bunny_updated__multiversus.glb"],
    "Mario": ["mario-n64-era.zip"],
    "Miku": ["hatsune-miku.zip"],
    "Peach": ["peach-ssb4.zip"],
    "Pepsiman": ["pepsiman.zip"],
    "Power Girl": ["power-girl.zip", "injustice-2-power-girl.zip"],
    "Prix": ["prix.zip", "prix (1).zip", "prix.glb"],
    "Sayuri": ["sayuri-dans.zip"],
    "Shrek": ["shrek-pocket-shrek-and-animations.zip"],
    "Skeleton Mage": ["animated-skeleton-casts-spell-with-hands.zip"],
    "Skibidi Toilet": ["skibidi-toilet-rigged.zip"],
    "Sonic": ["sonic-hd.zip", "junio-sonic-legacy.zip"],
    "Sophia": ["sophia-animated-003-animated-3d-woman.zip"],
    "Spartan Mark V": ["halo-mk-v-model.zip"],
    "Spider-Man": ["the-amazing-spider-man-2-rigged-model.zip"],
    "Spider-Man PS": ["spider-man-playstation-rigged.zip"],
    "Tenna": ["tenna-deltarune.zip"],
    "The Mandalorian": ["Mando_for_mixamo.fbx", "fortnite-the-mandalorianbaby-yoda.zip"],
    "The Rock": ["the-rock.zip"],
    "Vegeta": ["vegeta.zip"],
    "Yoda": ["yoda.zip"],
}

# Flat characters with NO archive found in Downloads at all. Named so the survey's coverage is
# visible rather than implied by absence.
NO_SOURCE = ["Aiko", "Kronk", "Mickey Mouse", "Peacemaker", "Vigilante", "Yui Suzukaze"]

MODEL_RE = re.compile(r"\.(fbx|glb|gltf|blend)$", re.I)
ARC_RE = re.compile(r"\.(zip|7z)$", re.I)


def _safe_members(names):
    """Refuse traversal and absolute entries. A downloaded archive is untrusted input."""
    return [n for n in names
            if n.startswith(("/", "\\")) or ".." in n.replace("\\", "/").split("/")
            or re.match(r"^[A-Za-z]:", n)]


def unpack(arc, dest):
    """Extract one archive. Returns an error string, or None."""
    try:
        if arc.lower().endswith(".zip"):
            with zipfile.ZipFile(arc) as z:
                bad = _safe_members(z.namelist())
                if bad:
                    return "%d traversal entr(ies), refused" % len(bad)
                z.extractall(dest)
        else:
            import py7zr
            with py7zr.SevenZipFile(arc, "r") as z:
                bad = _safe_members(z.getnames())
                if bad:
                    return "%d traversal entr(ies), refused" % len(bad)
                z.extractall(dest)
    except Exception as exc:                                        # noqa: BLE001
        return "%s: %s" % (type(exc).__name__, exc)
    return None


def unpack_deep(arc, dest, depth=2):
    """Extract, then extract any archive that extraction produced, to `depth` levels."""
    err = unpack(arc, dest)
    if err:
        return err
    for _ in range(depth):
        inner = [os.path.join(dp, f)
                 for dp, _d, fs in os.walk(dest) for f in fs if ARC_RE.search(f)]
        if not inner:
            break
        for i, p in enumerate(inner):
            sub = os.path.join(os.path.dirname(p), "_x%d" % i)
            os.makedirs(sub, exist_ok=True)
            unpack(p, sub)
            try:
                os.remove(p)        # so the next pass does not re-extract it forever
            except OSError:
                pass
    return None


def biggest_model(root):
    best, size = None, -1
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if not MODEL_RE.search(f):
                continue
            p = os.path.join(dirpath, f)
            try:
                s = os.path.getsize(p)
            except OSError:
                continue
            if s > size:
                best, size = p, s
    return best


def measure(model, timeout):
    try:
        r = subprocess.run([BLENDER, "--background", "--python", PROBE, "--", model],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "blender timed out after %ds" % timeout
    out = r.stdout
    m = re.search(r"WORST knuckle bend: right (\S+), left (\S+)", out)
    if not m:
        bad = [l for l in out.splitlines() if "NO ARMATURE" in l or "UNSUPPORTED" in l]
        return None, (bad[0].strip() if bad else "no WORST line in blender output")
    return (m.group(1), m.group(2)), None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    dl, scratch = sys.argv[1], sys.argv[2]
    only = set(sys.argv[3:])
    os.makedirs(scratch, exist_ok=True)

    rows, missing, failed = [], [], []
    for name in sorted(MAP):
        if only and name not in only:
            continue
        cands = [c for c in MAP[name] if os.path.isfile(os.path.join(dl, c))]
        if not cands:
            missing.append((name, MAP[name][0]))
            continue
        # EVERY candidate is measured. Agreement makes the ambiguity irrelevant;
        # disagreement is the finding.
        for ci, cand in enumerate(cands):
            arc = os.path.join(dl, cand)
            work = os.path.join(scratch, "%s_%d" % (re.sub(r"[^A-Za-z0-9]+", "_", name), ci))
            if os.path.isdir(work):
                shutil.rmtree(work, ignore_errors=True)
            os.makedirs(work)
            try:
                if ARC_RE.search(arc):
                    err = unpack_deep(arc, work)
                    if err:
                        failed.append((name, "%s: %s" % (cand, err)))
                        continue
                    model = biggest_model(work)
                else:
                    model = os.path.join(work, os.path.basename(arc))
                    shutil.copy2(arc, model)
                if model is None:
                    failed.append((name, "%s: no .fbx/.glb/.gltf/.blend inside, "
                                         "even after unpacking nested archives" % cand))
                    continue
                vals, err = measure(model, 600)
                if err:
                    failed.append((name, "%s: %s" % (cand, err)))
                else:
                    rows.append((name, vals[0], vals[1], os.path.basename(model),
                                 cand, len(cands)))
                    print("  measured %-22s right %-7s left %-7s  [%s]"
                          % (name, vals[0], vals[1], cand), flush=True)
            finally:
                shutil.rmtree(work, ignore_errors=True)

    print()
    print("=" * 94)
    print("SOURCE knuckle bend for installed characters whose HANDS READ FLAT (0.0 in the bundle)")
    print("=" * 94)
    print("%-20s %7s %7s  %-26s %s" % ("character", "src R", "src L", "model file", "archive"))
    print("-" * 94)
    by_char = {}
    for name, r, l, model, arc, ncand in rows:
        by_char.setdefault(name, []).append((r, l, model, arc, ncand))
    damaged, disputed, flat, unmeasured_chars = [], [], [], []
    order = sorted(by_char, key=lambda n: -max(max(_f(x[0]), _f(x[1])) for x in by_char[n]))
    for name in order:
        entries = by_char[name]
        for r, l, model, arc, _n in entries:
            print("%-20s %7s %7s  %-26s %s" % (name, r, l, model[:26], arc[:28]))
        # A FINGER THAT COULD NOT BE MEASURED PRINTS "-", AND _f RETURNS -1.0 FOR IT.
        # Letting that fall through to the "< 5.0" branch files an UNMEASURED character under
        # "authored flat, nothing to fix" -- which is the exact confusion this tool's own
        # docstring warns about, committed by the tool. Six characters were reported as
        # authored flat on the first widened run when every one of their fingers was a dash.
        worsts = [max(_f(r), _f(l)) for r, l, _m, _a, _n in entries]
        if max(worsts) < 0.0:
            unmeasured_chars.append(name)
            print("%-20s ^^ NO FINGER MEASURABLE in any candidate -- UNMEASURED, which is NOT"
                  " the same as flat" % "")
            continue
        if len(entries) > 1 and (max(worsts) - min(worsts)) >= 5.0:
            disputed.append(name)
            print("%-20s ^^ CANDIDATES DISAGREE by %.1f deg -- source not established, left open"
                  % ("", max(worsts) - min(worsts)))
        elif max(worsts) >= 5.0:
            damaged.append(name)
            print("%-20s ^^ SOURCE HAS BEND the bundle lost%s"
                  % ("", " (all %d candidates agree)" % len(entries) if len(entries) > 1 else ""))
        else:
            flat.append(name)
    print()
    print("%d character(s) read over %d candidate file(s): %d carry 5.0+ deg their bundle has"
          % (len(by_char), len(rows), len(damaged)))
    print("lost, %d were AUTHORED FLAT, %d have candidates that disagree, %d had NO finger"
          % (len(flat), len(disputed), len(unmeasured_chars)))
    print("measurable at all.")
    if damaged:
        print("  lost bend : " + ", ".join(damaged))
    if flat:
        print("  authored flat (nothing to fix): " + ", ".join(flat))
    if disputed:
        print("  source disputed: " + ", ".join(disputed))
    if unmeasured_chars:
        print("  UNMEASURED (not flat): " + ", ".join(unmeasured_chars))
    print()
    print("A source reading ~0 means the model was AUTHORED with a flat hand. Nothing was lost")
    print("and no rebuild helps -- that is the character, not a defect. And a VERY large figure")
    print("is not a stronger finding: Sayuri's 120.1 deg is a clenched fist from a frozen dance")
    print("frame, where flattening was probably correct.")
    if missing:
        print()
        print("NO ARCHIVE FOUND for: %s" % ", ".join(n for n, _ in missing))
    if NO_SOURCE and not only:
        print()
        print("FLAT BUT NOT IN THE MAP AT ALL (no plausible archive in Downloads): %s"
              % ", ".join(NO_SOURCE))
    if failed:
        print()
        for name, why in failed:
            print("UNMEASURED  %-22s %s" % (name, why))
    print()
    acc = len(by_char) + len(missing) + len({n for n, _w in failed} - set(by_char))         + len(NO_SOURCE)
    print("COVERAGE: %d characters measured, %d archive missing, %d unreadable, %d with no "
          "candidate at all = %d of the 42 flat characters accounted for."
          % (len(by_char), len(missing),
             len({n for n, _w in failed} - set(by_char)), len(NO_SOURCE), acc))
    print("Every one is named above rather than left out, because a survey that does not say")
    print("what it skipped reads as a clean sweep.")
    return 0


def _f(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return -1.0


if __name__ == "__main__":
    sys.exit(main())
