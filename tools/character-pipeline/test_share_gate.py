# -*- coding: utf-8 -*-
"""Show the share gate FAILING before anyone trusts it.

    python test_share_gate.py

A gate that has never been seen to refuse anything has not been verified, and this project has
shipped several that could only ever pass. So this runs `capsule_contains.share_gate` over two
real artefacts with known, opposite answers:

  REFUSE  the three capsules I placed on Batman on 2026-11-21, read back out of
          character-backups/Batman.yargchar.58097723-capsules-engulf-arms.bak -- the file Jay
          saw when he said the cape was clipping through Batman's arms. They are scored against
          the RESTORED Batman, which carries only the colliders his author drew, because that is
          what place_collider.py sees before it writes.

  PASS    Miku's fitted 86.6 mm tie capsule, scored against her own authored colliders with
          itself excluded -- again, what the writer would have seen. It is the control, and
          without it a gate that refuses everything would look identical to a working one.

The backup is kept deliberately for this: it is the only artefact that reproduces the fault.
If it is ever deleted this test cannot run, and it says so rather than passing vacuously.
"""
import os
import sys

import capsule_contains as cc
import cloth_collide_installed as cci

CHARS = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\FatalException\YARG-FE"
                           r"\release\custom\characters")
BACKUPS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "..", "..", "character-backups")
BROKEN = os.path.join(BACKUPS, "Batman.yargchar.58097723-capsules-engulf-arms.bak")
BATMAN = os.path.join(CHARS, "Batman.yargchar")
MIKU = os.path.join(CHARS, "Miku.yargchar")

BAD_HOSTS = ("fml_un_L_clav", "fml_un_R_clav", "fml_un_C_spine_d")


def load(path, match=None):
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    garment = cc.cloth_bones(tf, go_tf, springs, joints, match)
    skin = cc.skin_vertices(path, tf, world, garment)
    shapes = cc.collider_shapes(tf, go_tf, colliders, world)
    step = max(1, len(skin) // 12000)
    return skin[::step], shapes


def main():
    fails = []
    for p in (BROKEN, BATMAN, MIKU):
        if not os.path.isfile(p):
            print("MISSING, so this test cannot run: %s" % p)
            return 2

    print("== REFUSE: the three capsules that put a cape around Batman's arms ==")
    bad_skin, bad_shapes = load(BROKEN, "cape")
    good_skin, good_shapes = load(BATMAN, "cape")
    good_hosts = set(v[0] for v in good_shapes.values())
    for h in BAD_HOSTS:
        if h in good_hosts:
            print("  SETUP WRONG: %s already carries a collider in the restored file, so the "
                  "comparison is not against authoring alone." % h)
            return 2
    seen = 0
    for _cp, (bn, cr, a, b, _ct) in bad_shapes.items():
        if bn not in BAD_HOSTS:
            continue
        seen += 1
        ok, msg = cc.share_gate(good_skin, good_shapes, a, b, cr)
        print("  %-18s r=%6.1f mm -> %s" % (bn, cr * 1000, "ACCEPTED" if ok else "refused"))
        if ok:
            fails.append("%s (r=%.1f mm) was ACCEPTED: %s" % (bn, cr * 1000, msg))
    if seen != len(BAD_HOSTS):
        fails.append("expected %d bad capsules in the backup, found %d -- the fixture does not "
                     "reproduce the fault, so a clean run here would mean nothing"
                     % (len(BAD_HOSTS), seen))

    print()
    print("== PASS: Miku's fitted 86.6 mm tie capsule, against her authored colliders ==")
    m_skin, m_shapes = load(MIKU)
    fitted = [(cp, v) for cp, v in m_shapes.items() if abs(v[1] - 0.0866) < 0.002]
    if len(fitted) != 1:
        fails.append("expected exactly one ~86.6 mm capsule on Miku, found %d -- the control is "
                     "not in place" % len(fitted))
    else:
        cp, (bn, cr, a, b, _ct) = fitted[0]
        authored = dict((k, v) for k, v in m_shapes.items() if k != cp)
        ok, msg = cc.share_gate(m_skin, authored, a, b, cr)
        print("  %-18s r=%6.1f mm -> %s" % (bn, cr * 1000, "accepted" if ok else "REFUSED"))
        print("      %s" % msg)
        if not ok:
            fails.append("Miku's verified tie capsule was REFUSED: %s" % msg)

    print()
    if fails:
        print("FAILED:")
        for f in fails:
            print("  - %s" % f)
        return 1
    print("The gate refuses all three capsules that broke Batman and accepts the one that")
    print("did not. It has been seen to fail, so a pass from it means something.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
