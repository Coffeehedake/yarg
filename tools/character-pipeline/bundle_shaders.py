# -*- coding: utf-8 -*-
"""What shader does each material in a .yargchar actually use, and does the bundle CARRY it?

    python bundle_shaders.py <a.yargchar> [<b.yargchar> ...]

WHY THIS EXISTS. Two conclusions on this project rested on the claim that "a bundle
references shaders it does not contain", and the claim is FALSE. It got into
`mtoon_sweep_installed.py`'s header as the stated reason for not reading the shader object,
and from there into the README, where it made "could we ship an MToon character ourselves?"
look like it depended on the GAME BUILD shipping MToon -- which it does not.

What actually happens is narrower and much easier to misread: `m_Name` on a Shader inside a
bundle comes back as an EMPTY STRING. An empty name was taken for an absent object. The real
name lives in `m_ParsedForm.m_Name`, and once you read that, every bundle measured carries
its shaders and every material resolves in-bundle:

    Hatsune Miku (Retry Now ver.)   3 shaders carried, 23 of 23 materials resolve
                                    -> VRM10/Universal Render Pipeline/MToon10
    Aiko (ours)                     3 shaders carried,  3 of  3 materials resolve
                                    -> Universal Render Pipeline/Lit

AN EMPTY STRING IS NOT A FAILED READ. That is the whole lesson, and it cost a wrong answer in
each direction -- first "no MToon anywhere" from a swallowed exception, then "we could never
ship MToon" from a premise that was never measured.

THE CONTROL IS THE TYPE HISTOGRAM, printed whether or not anything interesting is found. A
bundle with zero distinct object types was not read at all, and without that line a failed
load and a genuinely plain character print the same reassuring nothing. A material whose
shader PPtr points outside the bundle is NAMED as such rather than counted as resolved --
"points outside" and "resolved" must never collapse into one number, because that collapse is
exactly what this tool exists to undo.
"""
import collections
import os
import sys

import UnityPy


def shader_name(obj):
    """The name, from m_ParsedForm -- NOT m_Name, which is empty for a bundled Shader."""
    try:
        t = obj.read_typetree()
    except Exception as e:
        return "<typetree failed: %s>" % type(e).__name__
    pf = t.get("m_ParsedForm")
    if isinstance(pf, dict) and pf.get("m_Name"):
        return str(pf["m_Name"])
    if t.get("m_Name"):
        return str(t["m_Name"])
    return "<no name field>"


def report(path):
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        env = UnityPy.load(path)
    except Exception as e:
        print("%-38s LOAD FAILED: %s" % (name[:38], e))
        return
    types = collections.Counter()
    shaders = {}
    for obj in env.objects:
        types[str(obj.type.name)] += 1
        if str(obj.type.name) == "Shader":
            shaders[obj.path_id] = shader_name(obj)

    per_mat = collections.Counter()
    for obj in env.objects:
        if str(obj.type.name) != "Material":
            continue
        try:
            sid = obj.read().m_Shader.path_id
        except Exception:
            per_mat["<material's shader pointer unreadable>"] += 1
            continue
        per_mat[shaders.get(sid, "<points OUTSIDE this bundle (path_id %s)>" % sid)] += 1

    print("=== %s" % name)
    print("    CONTROL: %d objects, %d distinct types -- a zero here means the read failed, "
          "not that the bundle is empty" % (sum(types.values()), len(types)))
    print("    shaders CARRIED by this bundle: %d" % len(shaders))
    for n in sorted(shaders.values()):
        print("        %s" % n)
    for s, c in per_mat.most_common():
        print("    %3d material(s) -> %s" % (c, s))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for p in sys.argv[1:]:
        report(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
