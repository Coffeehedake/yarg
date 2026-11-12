# -*- coding: utf-8 -*-
"""collider_group_check, run against the INSTALLED .yargchar instead of a .vrm.

    python collider_group_check_installed.py <dir-of-yargchar | file ...>

WHY THIS EXISTS. `collider_group_check.py` reads `.vrm` files, and only 30 of
the 65 installed characters still have one on this machine. A sweep that reads
`.vrm` files therefore covers less than half the set and reports the other half
as clean BY NEVER LOOKING AT THEM. That is the same shape of hole this project
has already shipped once, so it is worth saying plainly: the earlier sweep
found three affected characters out of thirty, and had nothing at all to say
about the remaining thirty-five.

The fault it looks for was in `vrm_colliders.py`: the group was assembled by
keeping the element `sb.colliders.add()` returned and reading `.uuid` off it
later. `sb.colliders` is a Blender CollectionProperty and `.add()` may
reallocate, so those references went stale and the VRM add-on dropped every
group reference whose uuid did not resolve. The builder's log said "colliders:
10 in one group" while the exported file's group held SIX. It was not even
stable -- the same character built twice in one batch came out `[4..9]` once
and `[8, 9]` the next.

A COUNT PRINTED BY THE BUILDER IS NOT A MEASUREMENT OF WHAT REACHED THE FILE,
and a bundle is the last place the question can still be asked.

WHAT IS IN THE BUNDLE. The spring-bone configuration survives the Unity import
whole, as MonoBehaviours:

    Vrm10Instance.SpringBone.Springs[].ColliderGroups[]   -> group path_ids
    VRM10SpringBoneColliderGroup.Colliders[]              -> collider path_ids
    VRM10SpringBoneCollider                               -> the collider

so the same question the `.vrm` check asks of indices is asked here of
path_ids. Three distinct faults are separable in the bundle, and only the first
is visible in a `.vrm`:

  ORPHAN    a collider that no group lists -- it was measured, fitted, written
            into the file, and guards nothing
  DANGLING  a group listing a collider that is not in the file at all
  UNUSED    a group that exists and that no spring chain references

A character with no colliders at all is a different statement from a character
whose colliders are all grouped, and both are printed, because "found nothing"
and "examined nothing" look identical otherwise.

CGC_CONTROL=1 discards every group's membership before the check, so every
character that HAS colliders must come back orphaned. Run it that way once: a
check that has never been seen to fail has not been verified.
"""
import os
import re
import sys

import UnityPy

CONTROL = bool(os.environ.get("CGC_CONTROL"))

# Chest springs sit ON the torso and are deliberately given NO collider group
# -- handing them the torso capsule would push them out of the body they
# belong to. Same regex as vrm_colliders.CHEST and cloth_collide_installed.
#
# It has to be here too, and the reason is Alcina Dimitrescu: VRM_BREASTRIG
# gave her two chains and no hair chains, so her ONE collider group is
# referenced by nothing -- which is correct, and which this check called a
# fault until it learned to tell a chest chain from a hair chain. A check that
# reports a design decision as a defect teaches the reader to skim its output.
CHEST = r"(breast|bust|pectoral|boob)"


def read(path):
    """-> (colliders, groups, springs, names)

    colliders  {collider_path_id: gameobject_path_id}
    groups     {group_path_id: [collider_path_id, ...]}
    springs    [(spring name, [group_path_id, ...]), ...]
    names      {gameobject_path_id: name}
    """
    env = UnityPy.load(path)
    colliders = {}
    groups = {}
    springs = []
    names = {}
    for obj in env.objects:
        try:
            ty = obj.type.name
        except Exception:                                        # noqa: BLE001
            continue
        if ty == "GameObject":
            try:
                names[obj.path_id] = obj.read().m_Name
            except Exception:                                    # noqa: BLE001
                pass
            continue
        if ty != "MonoBehaviour":
            continue
        try:
            t = obj.read_typetree()
            cn = obj.read().m_Script.read().m_ClassName
        except Exception:                                        # noqa: BLE001
            # A MonoBehaviour whose script cannot be resolved is not a spring
            # bone component; skipping it is correct, and it is counted by the
            # caller only through the totals it never contributes to.
            continue
        if cn == "Vrm10Instance":
            sb = t.get("SpringBone", {}) or {}
            for s in sb.get("Springs", []) or []:
                springs.append((
                    s.get("Name", "?"),
                    [c["m_PathID"] for c in s.get("ColliderGroups", []) or []],
                ))
        elif cn == "VRM10SpringBoneCollider":
            colliders[obj.path_id] = (t.get("m_GameObject", {}) or {}).get(
                "m_PathID", 0)
        elif cn == "VRM10SpringBoneColliderGroup":
            groups[obj.path_id] = [c["m_PathID"]
                                   for c in (t.get("Colliders", []) or [])]
    return colliders, groups, springs, names


def check(path):
    """-> (state, detail). ok / orphans / none / nosprings / error."""
    try:
        colliders, groups, springs, names = read(path)
    except Exception as e:                                       # noqa: BLE001
        return "error", "%s: %s" % (type(e).__name__, e)
    if CONTROL:
        groups = {g: [] for g in groups}
    if not colliders:
        return "none", "no colliders"
    if not springs:
        # Colliders and no spring chains at all. The colliders are inert, but
        # that is NOT this bug: nothing dropped a reference, there is simply
        # nothing in the file for a collider to push against. Whether such a
        # character SHOULD have chains is cloth_collide_installed.py's
        # question, and answering it here would report a build decision as a
        # fault -- which teaches the reader to skim the output.
        return "nosprings", ("%2d colliders in %d group(s), but no spring "
                             "chains at all" % (len(colliders), len(groups)))

    listed = set()
    dangling = []
    for g, members in groups.items():
        for c in members:
            if c in colliders:
                listed.add(c)
            else:
                dangling.append((g, c))
    orphans = [c for c in colliders if c not in listed]

    used_groups = set()
    for _nm, gl in springs:
        used_groups |= set(gl)
    unused = [g for g in groups if g not in used_groups]
    # A group nothing references is only a smell if a chain existed that COULD
    # have referenced it. Where every chain is a chest chain, nothing was meant
    # to -- see CHEST above.
    nonchest = [nm for nm, _gl in springs if not re.search(CHEST, nm, re.I)]
    by_design = bool(unused) and not nonchest

    def nm(c):
        return names.get(colliders.get(c, 0), "?")

    note = ""
    if by_design:
        note = ("; its %d group(s) are referenced by no chain, and every "
                "chain here is a chest chain, which is by design"
                % len(unused))
        unused = []

    if not orphans and not dangling and not unused:
        return "ok", ("%2d colliders in %d group(s), all grouped%s"
                      % (len(colliders), len(groups),
                         note or " and used"))
    bits = ["%2d colliders in %d group(s)" % (len(colliders), len(groups))]
    if orphans:
        bits.append("%d ORPHANED: %s"
                    % (len(orphans),
                       ", ".join(sorted(nm(c)[:20] for c in orphans))))
    if dangling:
        bits.append("%d DANGLING group reference(s)" % len(dangling))
    if unused:
        bits.append("%d group(s) no spring chain uses, though %d non-chest "
                    "chain(s) exist" % (len(unused), len(nonchest)))
    return "orphans", " -- ".join(bits)


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: collider_group_check_installed.py <dir|file ...>")
        return 2
    files = []
    for a in args:
        if os.path.isdir(a):
            files += [os.path.join(a, f) for f in sorted(os.listdir(a))
                      if f.lower().endswith(".yargchar")]
        else:
            files.append(a)
    tally = {"ok": 0, "orphans": 0, "none": 0, "nosprings": 0, "error": 0}
    # A line for EVERY file, the clean ones included.
    for p in sorted(files):
        state, detail = check(p)
        tally[state] += 1
        print("  %-34s %s"
              % (os.path.basename(p).replace(".yargchar", "")[:34], detail))
    print("\n%d bundle(s)%s: %d clean, %d WITH A FAULT, %d with colliders but "
          "no chains, %d with no colliders, %d unreadable"
          % (len(files), "  [CGC_CONTROL]" if CONTROL else "",
             tally["ok"], tally["orphans"], tally["nosprings"],
             tally["none"], tally["error"]))
    return 1 if (tally["orphans"] or tally["error"]) else 0


if __name__ == "__main__":
    sys.exit(main())
