"""Read the humanoid map out of a .vrm -- the FILE, not a log.

A build log carries the VRM add-on's own "Generated mappings:" block, which is
the add-on guessing at a structure it does not understand and has nothing to do
with what the build assigned. It maps hands to shins. Reading it as ours is a
five-minute panic; the file is the only thing that settles it.
"""
import json
import struct
import sys

path = sys.argv[1]
with open(path, "rb") as fh:
    magic, ver, total = struct.unpack("<III", fh.read(12))
    if magic != 0x46546C67:
        raise SystemExit("not a glb/vrm")
    js = None
    while fh.tell() < total:
        ln, ty = struct.unpack("<II", fh.read(8))
        data = fh.read(ln)
        if ty == 0x4E4F534A:
            js = json.loads(data.decode("utf-8"))
            break
g = js
names = [n.get("name", "?") for n in g.get("nodes", [])]
ext = g.get("extensions", {})
hb = None
for key in ("VRMC_vrm", "VRM"):
    if key in ext:
        h = ext[key].get("humanoid", {})
        hb = h.get("humanBones", h.get("humanBones", None))
        break
if hb is None:
    raise SystemExit("no humanoid extension found; extensions: %s" % list(ext))
if isinstance(hb, list):                       # VRM 0.x
    rows = [(b.get("bone"), names[b["node"]]) for b in hb if "node" in b]
else:                                          # VRM 1.0
    rows = [(k, names[v["node"]]) for k, v in hb.items() if "node" in v]
print("%s: %d humanoid bones" % (path.split("/")[-1], len(rows)))
order = ("hips spine chest upperChest neck head "
         "leftShoulder leftUpperArm leftLowerArm leftHand "
         "rightShoulder rightUpperArm rightLowerArm rightHand "
         "leftUpperLeg leftLowerLeg leftFoot leftToes "
         "rightUpperLeg rightLowerLeg rightFoot rightToes").split()
d = dict(rows)
for k in order:
    if k in d:
        print("   %-16s %s" % (k, d[k]))
rest = [k for k in sorted(d) if k not in order]
print("   (+%d finger bones: %s ...)" % (len(rest), ", ".join(rest[:4])))
