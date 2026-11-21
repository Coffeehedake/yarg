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

AMBIGUITY IS REPORTED, NEVER RESOLVED BY GUESSING. Several characters have more than one
plausible archive -- Harley Quinn three, Prix three, Power Girl two, Sonic two, Judy two. This
file already records that Iron Man had four candidate sources and only texture SIZE could
separate them, and that the newest file is not the source. A character with more than one
candidate is printed as AMBIGUOUS and not measured; picking one would produce a number that
looks exactly like a measurement.

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

    rows, amb, missing, failed = [], [], [], []
    for name in sorted(MAP):
        if only and name not in only:
            continue
        cands = [c for c in MAP[name] if os.path.isfile(os.path.join(dl, c))]
        if not cands:
            missing.append((name, MAP[name][0]))
            continue
        if len(cands) > 1:
            amb.append((name, cands))
            continue
        arc = os.path.join(dl, cands[0])
        work = os.path.join(scratch, re.sub(r"[^A-Za-z0-9]+", "_", name))
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        try:
            if arc.lower().endswith(".zip"):
                with zipfile.ZipFile(arc) as z:
                    bad = [n for n in z.namelist()
                           if n.startswith(("/", "\\")) or ".." in n or re.match(r"^[A-Za-z]:", n)]
                    if bad:
                        failed.append((name, "archive has %d traversal entr(ies), refused"
                                       % len(bad)))
                        shutil.rmtree(work, ignore_errors=True)
                        continue
                    z.extractall(work)
                model = biggest_model(work)
            else:
                model = os.path.join(work, os.path.basename(arc))
                shutil.copy2(arc, model)
            if model is None:
                failed.append((name, "no .fbx/.glb/.gltf/.blend inside"))
                continue
            vals, err = measure(model, 420)
            if err:
                failed.append((name, err))
            else:
                rows.append((name, vals[0], vals[1], os.path.basename(model),
                             os.path.basename(arc)))
                print("  measured %-22s right %-6s left %-6s" % (name, vals[0], vals[1]),
                      flush=True)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    print()
    print("=" * 94)
    print("SOURCE knuckle bend for installed characters whose HANDS READ FLAT (0.0 in the bundle)")
    print("=" * 94)
    print("%-22s %8s %8s  %s" % ("character", "src R", "src L", "model file"))
    print("-" * 94)
    damaged = []
    for name, r, l, model, _arc in sorted(rows, key=lambda t: -max(_f(t[1]), _f(t[2]))):
        flag = ""
        if max(_f(r), _f(l)) >= 5.0:
            flag = "  <== SOURCE HAS BEND, the build destroyed it"
            damaged.append(name)
        print("%-22s %8s %8s  %s%s" % (name, r, l, model[:36], flag))
    print()
    print("%d measured; %d have 5.0+ degrees of authored bend their bundle has lost."
          % (len(rows), len(damaged)))
    if damaged:
        print("  " + ", ".join(damaged))
    print()
    print("A source reading ~0 means the model was AUTHORED with a flat hand. Nothing was lost")
    print("and no rebuild helps -- that is the character, not a defect.")
    if amb:
        print()
        print("AMBIGUOUS, NOT MEASURED -- more than one candidate archive, and this project has")
        print("already picked a wrong source once by name and date:")
        for name, cands in amb:
            print("  %-22s %s" % (name, ", ".join(cands)))
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
    print("COVERAGE: %d measured, %d ambiguous, %d archive missing, %d unreadable, %d with no "
          "candidate at all = %d of the 42 flat characters accounted for."
          % (len(rows), len(amb), len(missing), len(failed), len(NO_SOURCE),
             len(rows) + len(amb) + len(missing) + len(failed) + len(NO_SOURCE)))
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
