# Which .vrm produced this installed .yargchar?
#
# "The built VRM is not necessarily what is installed" is a trap this project
# has already been caught by, and the obvious checks do not settle it:
# triangle and vertex counts are identical across a character's variants when
# what differs is the RIG, and UnityPy reports verts=0 for a .yargchar because
# the mesh data is not readable that way -- a limit of the reader, not a
# measurement, and exactly the kind of zero that looks like an answer.
#
# The rig IS readable. GameObject names survive in a bundle, and every bone's
# Transform carries m_LocalPosition and m_LocalRotation. That is enough to
# fingerprint a build, in three steps of increasing resolution:
#
#   1. SKELETON NAMES   catches a different rig family outright
#   2. BONE LENGTHS     catches a rescale
#   3. ROTATION ANGLES  catches a re-pose, which names and lengths cannot see
#
# Worked on Sonic, who had five candidate .vrm files all carrying 10,259 verts
# and the same four textures:
#
#   JunioSonic              0.0% name match   a different model entirely
#   withcols/Sonic          4.3% name match   the wrong-rig-family rebuild
#   SonicHD, SonicHD_nt    97.1%, Hips 0.518  ruled out on bone length
#   rollout/out, reg-Sonic,
#     SonicHD_fix          97.1%, Hips 0.5206, 34/34 rotations agree  <-- INSTALLED
#
# The two ruled-out ends are the controls: a comparison where nothing fails is
# not a comparison.
#
# Rotations are compared as ANGLE MAGNITUDE (2*acos|w|), which survives the
# Unity/glTF handedness difference where a raw quaternion does not.
#
# Usage:
#   python identify_build.py <installed.yargchar> <candidate.vrm> [more.vrm ...]
import json
import math
import os
import struct
import sys


def bundle_rig(path):
    import UnityPy
    env = UnityPy.load(path)
    objs = {}
    for obj in env.objects:
        try:
            objs[obj.path_id] = (obj.type.name, obj.read())
        except Exception:
            pass
    pos, rot = {}, {}
    for _pid, (ty, data) in objs.items():
        if ty != "Transform":
            continue
        go = getattr(data, "m_GameObject", None)
        nm = None
        if go is not None:
            try:
                nm = go.read().m_Name
            except Exception:
                nm = None
        if nm is None:
            continue
        lp = getattr(data, "m_LocalPosition", None)
        lr = getattr(data, "m_LocalRotation", None)
        if lp is not None:
            pos[nm] = round(math.sqrt(lp.x ** 2 + lp.y ** 2 + lp.z ** 2), 4)
        if lr is not None:
            w = min(1.0, max(-1.0, abs(getattr(lr, "w", 1.0))))
            rot[nm] = math.degrees(2 * math.acos(w))
    return pos, rot


def vrm_rig(path):
    d = open(path, "rb").read()
    off, g = 12, None
    while off < len(d):
        ln, ty = struct.unpack_from("<II", d, off)
        if ty == 0x4E4F534A:
            g = json.loads(d[off + 8:off + 8 + ln].decode("utf-8"))
        off += 8 + ln + ((4 - ln % 4) % 4)
    # Compare only names that identify ONE node.
    #
    # A glTF node name is not unique, and a VRM routinely reuses one: Pomni's
    # meshes are called `Arm.L`, `Leg.L`, `Eye.L` and so are her bones. The
    # mesh node sits at the origin with an identity rotation while the bone
    # carries the real transform, so whichever happened to be written last won
    # the dictionary -- and this reported her rebuild as differing from her
    # installed bundle at exactly those five names, with every real bone
    # identical to four decimal places. On that reading she was excluded from
    # the collider rollout twice as "the .vrm is not what is installed".
    #
    # An ambiguous name cannot be compared, so it is dropped and counted
    # rather than guessed at.
    pos, rot, dupe = {}, {}, set()
    for n in g["nodes"]:
        nm = n.get("name", "?")
        t = n.get("translation", [0, 0, 0])
        q = n.get("rotation", [0, 0, 0, 1])
        v = round(math.sqrt(sum(x * x for x in t)), 4)
        w = min(1.0, max(-1.0, abs(q[3])))
        r = math.degrees(2 * math.acos(w))
        if nm in pos and (pos[nm] != v or abs(rot[nm] - r) > 1e-6):
            dupe.add(nm)
        pos[nm], rot[nm] = v, r
    if dupe:
        print("  (%d name(s) are both a mesh and a bone here, so their VALUES "
              "are not compared: %s)"
              % (len(dupe), ", ".join(sorted(dupe)[:6])))
    # The names stay in `pos` so they still count toward the name overlap --
    # they ARE shared names, and dropping them outright pushed Pomni's score
    # from 92.5% to 87.1% and under the threshold, turning one wrong verdict
    # into another. Only the value comparison skips them.
    return pos, rot, dupe


def main():
    inst_pos, inst_rot = bundle_rig(sys.argv[1])
    print("installed: %s -- %d bones" % (os.path.basename(sys.argv[1]), len(inst_pos)))
    for p in sys.argv[2:]:
        if not os.path.exists(p):
            continue
        vp, vr, dupe = vrm_rig(p)
        shared = set(inst_pos) & set(vp)
        jac = 100.0 * len(shared) / max(len(set(inst_pos) | set(vp)), 1)
        cmpable = shared - dupe
        lbad = [n for n in cmpable if abs(vp[n] - inst_pos[n]) > 0.0005]
        rbad = [n for n in cmpable if abs(vr[n] - inst_rot.get(n, 0.0)) > 1.0]
        # A mismatch count over an EMPTY intersection is zero for the wrong
        # reason, and "0 mismatches" next to "0.0% names" is exactly the kind
        # of zero that reads as a pass. Say when there was nothing to compare.
        if not cmpable:
            print("  %-30s names=%5.1f%%  nothing in common -- not the same rig"
                  % (os.path.basename(p)[:30], jac))
            continue
        verdict = ("MATCH" if jac > 90 and not lbad and not rbad
                   else "differs")
        print("  %-30s names=%5.1f%%  compared=%-3d length-mismatch=%-3d "
              "rotation-mismatch=%-3d  %s"
              % (os.path.basename(p)[:30], jac, len(cmpable), len(lbad),
                 len(rbad), verdict))
        if rbad and len(rbad) <= 6:
            print("        rotations differ at: %s" % sorted(rbad))


if __name__ == "__main__":
    main()
