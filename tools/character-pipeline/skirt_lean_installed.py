# -*- coding: utf-8 -*-
"""Skirt lean: skinned centroid X per height band, for each installed bundle given.

    python skirt_lean_installed.py <a.yargchar> [b.yargchar ...]

A garment that hangs straight has a centroid X that barely moves with height; one rotated with
the pelvis drifts sideways as it descends, and fans wider the lower it goes. Jessica Rabbit is
the measured case: shipped she drifts +24 mm over her whole drop, and with her Hips levelled to
cure a 92.4 mm buried shoe she drifts -155 mm and sits 200-390 mm across. That is the cost the
2026-11-16 closure named as "a twisted pelvis", in millimetres.

Run it from this directory, or with this directory on PYTHONPATH -- it imports two siblings.
Nothing is written.
"""
# Skirt lean: centroid X per height band, skinned, for each bundle given.
# A garment that hangs straight has a centroid X that barely moves with height;
# one rotated with the pelvis drifts sideways as it descends.
import sys, os
import cloth_collide_installed as cci, patch_springs as ps, UnityPy
for path in sys.argv[1:]:
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    env = UnityPy.load(path)
    tt, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh": tt[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer": smrs.append(o.read_typetree())
    best = None
    for r in smrs:
        mt = tt.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None: continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
        if got is None or not bones or len(bind) != len(bones): continue
        V,W,I = got
        skin = [ps.mul(ps.trs(*world(b)), bind[i]) for i,b in enumerate(bones)]
        pts=[]
        for vi in range(len(V)):
            b2,bw=None,-1.0
            for k in range(len(W[vi])):
                if W[vi][k]>bw and W[vi][k]>0 and I[vi][k]<len(skin): bw,b2=W[vi][k],I[vi][k]
            if b2 is None: continue
            pts.append(ps.xform(skin[b2], V[vi]))
        nm = mt.get("m_Name") or "?"
        low = [p for p in pts if p[1] < 0.6]
        if len(low) > 3000 and (best is None or len(low) > len(best[1])):
            best = (nm, low)
    if best is None:
        print("%-16s no large low mesh found" % os.path.basename(path)[:16]); continue
    nm, low = best
    print("%-16s mesh %-12s %d verts below y=0.6" % (os.path.basename(path)[:16], nm[:12], len(low)))
    for lo,hi in ((0.0,0.15),(0.15,0.3),(0.3,0.45),(0.45,0.6)):
        band=[p for p in low if lo<=p[1]<hi]
        if band:
            print("    y %.2f-%.2f  n=%5d  centroid X %+7.1f mm" % (lo,hi,len(band),
                  1000.0*sum(p[0] for p in band)/len(band)))
