"""For each .vrm: does it already have spring bones, and does its skeleton
contain hair/skirt/tail chains that could be sprung without re-rigging?"""
import json
import os
import re
import struct
import sys

PAT = re.compile(r"(hair|ponytail|pigtail|braid|bang|tail|skirt|dress|cloth|"
                 r"ribbon|scarf|cape|coat|tassel|fringe|antenna|hat|bell|horn|"
                 r"wing|feather)", re.I)


def load(path):
    d = open(path, "rb").read()
    off, js = 12, None
    while off < len(d):
        cl, ct = struct.unpack_from("<II", d, off)
        off += 8
        if ct == 0x4E4F534A:
            js = json.loads(d[off:off + cl].decode("utf-8"))
        off += cl
    return js


for path in sorted(sys.argv[1:]):
    try:
        js = load(path)
    except Exception as e:
        print("%-26s UNREADABLE %s" % (os.path.basename(path), e))
        continue
    nodes = js.get("nodes", [])
    names = [n.get("name") or "" for n in nodes]
    sb = js.get("extensions", {}).get("VRMC_springBone", {})
    springs = sb.get("springs", [])
    # humanoid bones must not be sprung
    hum = js.get("extensions", {}).get("VRMC_vrm", {}).get("humanoid", {}).get("humanBones", {})
    hum_nodes = {v.get("node") for v in hum.values() if isinstance(v, dict)}
    cand = sorted({names[i] for i in range(len(nodes))
                   if PAT.search(names[i]) and i not in hum_nodes})
    already = sum(len(s.get("joints", [])) for s in springs)
    print("%-26s springs=%-2d (%3d joints)  candidate bones=%-3d %s"
          % (os.path.basename(path), len(springs), already, len(cand),
             cand[:6] if cand else ""))
