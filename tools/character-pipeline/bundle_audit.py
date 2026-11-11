# What does each INSTALLED .yargchar actually contain?
#
# Three things the game needs that a render cannot show:
#   * an AnimatorController and AnimationClips -- without them the character
#     stands in its bind pose forever, however good the rig is
#   * humanoid bone coverage -- Unity retargets through the humanoid map, so a
#     bone that is not mapped is never driven by the game's animation
#   * FINGER bones in that map -- the documented "closed fists" complaints are
#     a hypothesis this can test: a hand with no mapped fingers cannot open
import collections
import os
import sys

import UnityPy

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Little")


def audit(path):
    env = UnityPy.load(path)
    c = collections.Counter()
    human = []
    for obj in env.objects:
        c[obj.type.name] += 1
        if obj.type.name != "Avatar":
            continue
        try:
            d = obj.read()
        except Exception:
            continue
        hd = getattr(d, "m_HumanDescription", None)
        for e in (getattr(hd, "m_Human", None) or []):
            hn = getattr(e, "m_HumanName", None)
            if hn:
                human.append(hn)
    fing = [h for h in human if any(f in h for f in FINGERS)]
    per = collections.Counter()
    for h in fing:
        for f in FINGERS:
            if f in h:
                per[f] += 1
    name = os.path.basename(path).replace(".yargchar", "")
    flags = []
    if c["AnimationClip"] == 0 or c["AnimatorController"] == 0:
        flags.append("NO ANIMATION")
    if not fing:
        flags.append("NO FINGERS MAPPED")
    elif len(per) <= 1:
        flags.append("ONLY %s MAPPED" % "/".join(sorted(per)))
    print("%-38s clips=%-2d ctrl=%-1d humanoid=%-3d fingers=%-2d (%s) meshes=%-3d%s"
          % (name[:38], c["AnimationClip"], c["AnimatorController"], len(human),
             len(fing), ",".join("%s%d" % (k[:2], v) for k, v in sorted(per.items())) or "-",
             c["Mesh"], "   <-- " + "; ".join(flags) if flags else ""))


def main():
    args = sys.argv[1:]
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.endswith(".yargchar")]
        else:
            files.append(a)
    for f in files:
        try:
            audit(f)
        except Exception as e:
            print("%-38s ERROR %s" % (os.path.basename(f)[:38], e))


if __name__ == "__main__":
    main()
