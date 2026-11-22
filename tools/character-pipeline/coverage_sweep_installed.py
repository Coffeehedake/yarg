# -*- coding: utf-8 -*-
"""How much of each installed character's body can its cloth actually collide with?

    python coverage_sweep_installed.py [file.yargchar ...] [--out PATH] [--limit N]

WHY. Batman had **69.1% of his body skin outside every collider** -- his whole belt and waist,
his chest, his feet, most of his hips -- and a cape that went through him. Three fixes aimed at
the radius of one capsule did nothing, because the problem was never a radius: two thirds of him
was not represented at all. The obvious question is whether that is a Batman problem or the
pipeline's, and nothing here has ever asked it.

WHAT IT REPORTS, per character: the number of spring chains and colliders, and the share of
body skin (garment bones excluded) that is inside no collider. A character with no spring chain
is reported too, with its coverage, because a character that gains a garment later inherits
whatever body it already has.

THIS IS A SURVEY AND IT WRITES NOTHING to any character. It is slow -- every file's meshes are
decoded and skinned -- so it prints as it goes and takes `--out` for a file.

A ZERO HERE WOULD BE A FINDING ONLY IF THE SWEEP IS PROVED TO HAVE RUN: each row carries its
vertex and collider counts, so a character that silently decoded nothing reads as `--` rather
than as a clean 0.0%.
"""
import os
import sys
import traceback

import capsule_contains as cc
import cloth_collide_installed as cci

CHARS = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\FatalException\YARG-FE"
                           r"\release\custom\characters")


def one(path):
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    garment = cc.cloth_bones(tf, go_tf, springs, joints)
    skin = cc.skin_vertices(path, tf, world, garment)
    shapes = cc.collider_shapes(tf, go_tf, colliders, world)
    if not skin:
        return (len(springs), len(shapes), 0, None)
    step = max(1, len(skin) // 4000)
    sample = skin[::step]
    out = sum(1 for _bn, q in sample
              if not any(cc.seg_dist(q, a, b) < r for _n, r, a, b, _c in shapes.values()))
    return (len(springs), len(shapes), len(skin), 100.0 * out / len(sample))


def main():
    # A flag's VALUE is not a positional. The first version of this took every argument that
    # did not start with "--" as a character file, so `--out <path>` fed the output path in as
    # a character: the sweep ran on one row called "cov" and reported it unmeasured. It was
    # only legible because the row prints "--" rather than a clean 0.0% when nothing decodes.
    takes_value = ("--out", "--limit")
    argv, skip = [], False
    for a in sys.argv[1:]:
        if skip:
            skip = False
            continue
        if a in takes_value:
            skip = True
            continue
        if not a.startswith("--"):
            argv.append(a)
    out_path = (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None)
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    files = argv or sorted(os.path.join(CHARS, f) for f in os.listdir(CHARS)
                           if f.lower().endswith(".yargchar"))
    if limit:
        files = files[:limit]

    lines = ["%-42s %7s %6s %8s %9s" % ("character", "chains", "cols", "verts", "uncovered")]
    lines.append("-" * 80)
    print(lines[0])
    print(lines[1])
    for p in files:
        nm = os.path.basename(p)[:-9]
        try:
            ch, co, nv, pc = one(p)
            row = ("%-42s %7d %6d %8d %8s" %
                   (nm[:42], ch, co, nv, ("%.1f%%" % pc) if pc is not None else "--"))
        except Exception as e:                                       # noqa: BLE001
            row = "%-42s  UNREAD: %s" % (nm[:42], str(e)[:30])
            traceback.print_exc(file=sys.stderr)
        print(row)
        sys.stdout.flush()
        lines.append(row)
    if out_path:
        open(out_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("\nwritten to %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
