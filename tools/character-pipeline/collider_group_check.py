# Does every collider in a .vrm actually reach the group that guards the chains?
#
#   python collider_group_check.py <dir-or-file> [more ...]
#
# WHY THIS EXISTS. vrm_colliders.py used to build its group by keeping the
# element `sb.colliders.add()` returned and reading `.uuid` off it later.
# `sb.colliders` is a Blender CollectionProperty and `.add()` may reallocate, so
# those references went stale; the VRM add-on then dropped every group reference
# whose uuid did not resolve.
#
# The builder's own log said "colliders: 10 in one group" while the exported
# file's group held SIX. Sayuri's was `[4, 5, 6, 7, 8, 9]` -- her head, hip and
# left arm were measured, fitted, written into the file and guarded nothing. It
# was not even stable: the same character built twice in one batch came out
# `[4..9]` once and `[8, 9]` the next.
#
# A COUNT PRINTED BY THE BUILDER IS NOT A MEASUREMENT OF WHAT REACHED THE FILE.
# That is what this reads instead. The bug is fixed, so a clean run is the
# expected result; it is kept because the failure was silent, plausible and
# invisible to every other check in the project.
#
# Three of the 30 .vrm files behind an installed character were affected when
# this was written -- Alcina, Pomni, the Xenomorph, four orphans each, always
# the head/spine and the left arm. All three were rebuilt.
import json
import os
import struct
import sys


def read_gltf_json(path):
    with open(path, "rb") as f:
        magic, _ver, total = struct.unpack("<III", f.read(12))
        if magic != 0x46546C67:
            raise ValueError("not a GLB/VRM")
        while f.tell() < total:
            length, kind = struct.unpack("<II", f.read(8))
            data = f.read(length)
            if kind == 0x4E4F534A:
                return json.loads(data.decode("utf-8"))
    raise ValueError("no JSON chunk")


def check(path):
    """-> (state, detail). state is one of ok / orphans / none / error."""
    try:
        js = read_gltf_json(path)
    except Exception as e:                    # noqa: BLE001
        return "error", "%s: %s" % (type(e).__name__, e)
    names = [n.get("name", "?") for n in js.get("nodes", [])]
    sb = js.get("extensions", {}).get("VRMC_springBone", {}) or {}
    cols = sb.get("colliders", [])
    if not cols:
        return "none", "no colliders"
    inside = set()
    for g in sb.get("colliderGroups", []):
        inside |= set(g.get("colliders", []))
    missing = sorted(set(range(len(cols))) - inside)
    if not missing:
        return "ok", "%2d colliders, all grouped" % len(cols)
    orphaned = []
    for i in missing:
        node = cols[i].get("node")
        orphaned.append(names[node] if node is not None
                        and node < len(names) else "?")
    return "orphans", ("%2d colliders, %2d grouped -- %d ORPHANED: %s"
                       % (len(cols), len(inside), len(missing),
                          ", ".join(n[:20] for n in orphaned)))


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: collider_group_check.py <dir-or-file> [more ...]")
        return 2
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".vrm")]
        else:
            files.append(a)
    tally = {"ok": 0, "orphans": 0, "none": 0, "error": 0}
    # A line for EVERY file, including the ones with nothing to say. A sweep
    # that finds nothing and a sweep that examined nothing look identical
    # otherwise, and this project has already shipped one of those.
    for p in sorted(files):
        state, detail = check(p)
        tally[state] += 1
        print("  %-28s %s" % (os.path.basename(p)[:28], detail))
    print("\n%d file(s): %d all-grouped, %d WITH ORPHANS, %d with no "
          "colliders, %d unreadable"
          % (len(files), tally["ok"], tally["orphans"], tally["none"],
             tally["error"]))
    return 1 if (tally["orphans"] or tally["error"]) else 0


if __name__ == "__main__":
    sys.exit(main())
