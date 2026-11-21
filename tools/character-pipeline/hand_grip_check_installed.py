# -*- coding: utf-8 -*-
"""Can the game's mic-grab animation reach a character's right hand at all?

    python hand_grip_check_installed.py <dir-of-yargchar>            # whole roster
    python hand_grip_check_installed.py <a.yargchar> [b.yargchar ...]

WHY THIS EXISTS. Jay reported on 2026-11-21 that Kronk's and Judy Hopps's right hands "aren't
set to a grip for the mic". The obvious reading -- that a grip animation failed to play -- is
wrong in both halves, and the game's own code says so:

  * `BackgroundManager.cs` NEVER POSES THE HAND. It instantiates the mic parented to
    `RightHand` and sets its position to `Lerp(RightThumbDistal, RightIndexProximal, 0.25)`.
    Wherever the fingers are, that is where the mic goes.
  * The closing of the fingers is a separate thing: the `Hold Microphone` layer of
    `Animations/Vocals/Default/DefaultController` plays `VoxMicGrab.anim` at weight 1, masked
    by `VocalsHandMask`. That clip carries **20 HUMANOID MUSCLE CURVES** -- `RightHand.Index.1
    Stretched` and so on, every joint of all five fingers -- and the mask enables exactly ONE
    body part, `RightFingers` (bit 8 of 13; the other twelve are 0, decoded rather than assumed).

A humanoid muscle curve does not address a transform. It addresses a SLOT IN THE AVATAR, and
Unity retargets it onto whatever bone that avatar binds to the slot. **An unmapped slot has
nothing to drive, so the muscle curve is discarded in silence and the finger does not move.**
That is the measurement this tool makes.

(The mask file also carries 123 hardcoded transform paths -- `Armature/Hips/Spine/Chest/
UpperChest/Shoulder_R/Arm_R/Elbow_R/Wrist_R/Index_0_R`. They match the stock YARG rig and no
custom one. They are authoring leftovers and they are NOT what runs: `m_Mask` is what a
humanoid layer reads. Do not "fix" a custom character by renaming its bones to match them.)

WHAT IS READ. `Avatar.m_HumanDescription.m_Human` is the editor-side map that survives into the
bundle: a list of `{m_BoneName, m_HumanName}` pairs. `m_HumanName` is Unity's slot name, so the
fifteen right-finger slots are exactly `Right Thumb Proximal` .. `Right Little Distal`. A slot
absent from that list is a slot the Avatar does not bind.

THE SIX THAT ARE NOT ABOUT THE GRIP AT ALL are reported separately, because missing one of them
is a worse fault than a limp hand and does not look like one. **What it costs depends on which
BUILD is running, so this tool reports the bones and names both outcomes rather than picking
one.** `AddMicrophoneToCharacter` is called from `LoadCharacter` on the line directly before
`SetLayer(newCharacter, "Venue")`:

  * BEFORE commit `0d3d4e4f` (2026-11-09): `GetBoneTransform` returns null rather than throwing,
    so the null escaped the `try` and surfaced at `rightThumbDistal.position` outside it. The
    throw left `LoadCharacter` before the `SetLayer`, the venue camera culls to Venue only, and
    a correctly loaded character was simply INVISIBLE -- in game, "a floating mic and no one
    holding it". Measured on Alastor.
  * AFTER it: the explicit null check returns cleanly, `SetLayer` still runs, and the character
    is drawn with NO MICROPHONE.

Neither shows up in the character-select podium, which does not go through `BackgroundManager`
at all -- so a character can look perfect there and be absent from the venue. Check the date on
the `Assembly-CSharp.dll` you are actually running before reading a row here as "invisible"
([[check-which-binary-ran]]).

READ THE POPULATION, NOT THE ROW. Fifteen of fifteen on one character means nothing until you
know what the other sixty-four read. If every character in the roster scores the same, this tool
is measuring itself and not them -- see `the-harness-needs-a-control`. Controls are any character
Jay has NOT reported: they are what makes a low score a finding.

Nothing is written.
"""
import os
import sys

import UnityPy

FINGERS = ["Thumb", "Index", "Middle", "Ring", "Little"]
JOINTS = ["Proximal", "Intermediate", "Distal"]


def slots(side):
    return ["%s %s %s" % (side, f, j) for f in FINGERS for j in JOINTS]


RIGHT = slots("Right")
LEFT = slots("Left")

# The six BackgroundManager.cs demands before it will finish loading the character.
REQUIRED_SIX = ["RightHand", "Right Thumb Distal", "Right Little Distal",
                "Right Little Proximal", "Right Index Intermediate", "Right Index Proximal"]

# The two the mic position is actually interpolated between (RightHand is only the parent).
MIC_BONES = ["Right Thumb Distal", "Right Index Proximal"]


def human_map(path):
    """{m_HumanName: m_BoneName} from the bundle's Avatar, or None if it has no Avatar."""
    env = UnityPy.load(path)
    for o in env.objects:
        if o.type.name != "Avatar":
            continue
        tt = o.read_typetree()
        hd = tt.get("m_HumanDescription") or {}
        rows = hd.get("m_Human") or []
        return dict((r.get("m_HumanName"), r.get("m_BoneName")) for r in rows)
    return None


def measure(path):
    m = human_map(path)
    if m is None:
        return None
    return {
        "total": len(m),
        "right": [s for s in RIGHT if s in m],
        "right_missing": [s for s in RIGHT if s not in m],
        "left": [s for s in LEFT if s in m],
        "missing_req": [b for b in REQUIRED_SIX if b not in m],
        "mic_ok": all(b in m for b in MIC_BONES),
    }


def short(slot):
    """'Right Index Proximal' -> 'Index.Prox', for a table that has to fit."""
    parts = slot.split()
    return "%s.%s" % (parts[1], parts[2][:4])


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            paths.append(a)
    if not paths:
        print("no .yargchar found in %s" % args)
        return 2

    rows, broken = [], []
    for p in paths:
        name = os.path.basename(p)[:-9]
        try:
            r = measure(p)
        except Exception as exc:                                    # noqa: BLE001
            broken.append((name, "%s: %s" % (type(exc).__name__, exc)))
            continue
        if r is None:
            broken.append((name, "no Avatar object in the bundle"))
            continue
        rows.append((name, r))

    print("%-28s %5s %7s %7s  %s" % ("character", "bones", "R.fing", "L.fing", "flags"))
    print("-" * 86)
    for name, r in sorted(rows, key=lambda t: (len(t[1]["right"]), t[0])):
        flags = []
        if r["missing_req"]:
            flags.append("NO MIC (and INVISIBLE pre-0d3d4e4f): no %s"
                         % ", ".join(r["missing_req"]))
        elif not r["right"]:
            flags.append("NO right-finger slots -- VoxMicGrab cannot move this hand")
        elif len(r["right"]) < 15:
            flags.append("partial: no " + ", ".join(short(s) for s in r["right_missing"]))
        print("%-28s %5d  %4d/15  %4d/15  %s"
              % (name[:28], r["total"], len(r["right"]), len(r["left"]), "; ".join(flags)))

    n = len(rows)
    full = [r for _, r in rows if len(r["right"]) == 15]
    none_ = [r for _, r in rows if not r["right"]]
    part = [r for _, r in rows if 0 < len(r["right"]) < 15]
    print()
    print("POPULATION: %d read; %d bind all 15 right-finger slots, %d partial, %d none."
          % (n, len(full), len(part), len(none_)))
    if n and len(full) == n:
        print()
        print("EVERY character scores 15/15. That is a UNIFORM reading, so this tool has not")
        print("distinguished anybody and cannot support a claim about any one of them. Either")
        print("no grip fault is of this kind, or the read is wrong. Do not report the 15/15 of")
        print("a character whose hand is visibly open as though it cleared him.")
    if n and len(none_) == n:
        print()
        print("EVERY character scores 0/15, which is this tool failing and not 65 broken rigs.")
    if broken:
        print()
        for name, why in broken:
            print("UNREADABLE  %-26s %s" % (name[:26], why))
    print()
    print("A score here is about what the AVATAR BINDS, not about how the hand looks. A fully")
    print("mapped hand can still sit open if the clip is not playing; an unmapped one cannot")
    print("close at all. Only the second is this tool's business.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
