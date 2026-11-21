# -*- coding: utf-8 -*-
"""Is every installed character still an AssetBundle? The one check UnityPy cannot make.

    python container_check_installed.py [file-or-dir ...]

WHY THIS EXISTS, and it is the cheapest useful tool in this folder. On 2026-11-21 two installed
characters were on disk as bare SerializedFiles instead of `UnityFS` AssetBundles, because
`patch_chain_collider.py` and `place_collider.py` called `af.save()` -- the SerializedFile inside
the bundle -- rather than `env.file.save()`, the bundle itself. Miku sat in that state for four
hours after her tie fix was applied, reported and "verified"; Batman for six minutes.

**EVERY CHECKER IN THIS PROJECT PASSED ON BOTH OF THEM.** `cloth_collide_installed.py`,
`collider_group_check_installed.py`, `hand_grip_check_installed.py`, the lot. They all read
through UnityPy, and UnityPy opens a bare SerializedFile quite happily -- it is a container it
supports. `AssetBundle.LoadFromFile`, which is what the game calls, does not. So the fault was
invisible to the whole verification chain while being fatal to the thing the chain exists to
protect, and the only visible symptom was a file size: 1,350,684 bytes grown to 3,804,432.

That is why this tool reads BYTES and does not import UnityPy at all. A check implemented with
the same library as the thing it checks cannot see the library's own tolerance.

It also prints sizes, because the second symptom is a size that moved by a factor rather than by
a few hundred bytes. A collider and a group are small; a 2.8x or 6.6x change means the container
or its compression changed underneath.
"""
import os
import sys

MAGIC = b"UnityFS"
CHARS = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\FatalException\YARG-FE"
                           r"\release\custom\characters")


def targets(argv):
    if not argv:
        argv = [CHARS]
    out = []
    for a in argv:
        if os.path.isdir(a):
            out += [os.path.join(a, f) for f in sorted(os.listdir(a))
                    if f.endswith(".yargchar")]
        else:
            out.append(a)
    return out


def main():
    files = targets(sys.argv[1:])
    if not files:
        print("no .yargchar found -- that is a fact about the path, not a clean result.")
        return 2
    bad = []
    for p in files:
        try:
            with open(p, "rb") as fh:
                head = fh.read(len(MAGIC))
            size = os.path.getsize(p)
        except OSError as exc:
            bad.append((p, "unreadable: %s" % exc, 0))
            continue
        if head != MAGIC:
            bad.append((p, "starts %r, not 'UnityFS' -- NOT AN ASSETBUNDLE"
                        % head[:8], size))
    print("%d installed character(s) checked by their first %d bytes"
          % (len(files), len(MAGIC)))
    if not bad:
        print("all %d carry the UnityFS AssetBundle header." % len(files))
        print()
        print("That is the whole result. It says nothing about their contents -- the other")
        print("tools in this folder do that -- and the contents say nothing about this,")
        print("which is the point: a bundle this check rejects would pass all of them.")
        return 0
    for p, why, size in bad:
        print("  FAULT  %-44s %10d bytes  %s" % (os.path.basename(p), size, why))
    print()
    print("%d of %d are NOT loadable by AssetBundle.LoadFromFile. Restore each from"
          % (len(bad), len(files)))
    print("character-backups and re-apply whatever change produced it with a tool that")
    print("saves env.file, not the assets file inside it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
