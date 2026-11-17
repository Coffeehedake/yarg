# -*- coding: utf-8 -*-
"""Where the GEOMETRY's own centreline is, fitted without using any bone.

    python mesh_mirror_installed.py <file.yargchar ...> [--control]

`half_body_check_installed.py` says The Mandalorian is two half-skeletons
37.2 mm apart -- every lower pair centred at -18.5 mm and every upper pair at
+18.7 mm. It cannot say WHICH half is in the wrong place, because every number
it has comes from the bones. Correcting him needs the one thing the bones
cannot supply: where his body actually is.

So this fits a mirror PLANE to the skinned world vertex cloud. For a candidate
plane x = c the cloud is reflected through it and every reflected point asked
for its nearest neighbour in the original; the MEDIAN of those distances is the
score, and the c that minimises it is the plane the geometry is symmetric
about. No bone enters the fit, no axis convention is assumed and no left/right
labelling is needed -- which is the point, after a mirror check built on
negating a local X turned out to be unsound in exactly the cases it reported.

A percentile, not a minimum or a maximum: one vertex at a seam must not set the
answer. A median also survives the parts that are NOT mirror-symmetric -- a
holstered pistol, a single pauldron -- as long as they are a minority of the
cloud, and the printed residual says whether that held.

**It samples the SURFACE, not the vertices.** Nearest-neighbour distance
between two vertex clouds has a floor set by the tessellation, and the first
version of this ran on vertices alone: Spartan Mark V, whose mesh is mirrored
vertex for vertex, read 0.00 mm, and The Mandalorian read 23 mm on a curve so
flat it said nothing -- 23.25 at the optimum against 24.19 five millimetres
away. That is a low-poly mesh being measured with a ruler made of its own edge
length, and it cannot distinguish "not symmetric" from "coarsely triangulated".
Sampling each triangle in proportion to its area puts the floor at the sampling
spacing instead, which is a number this tool chooses rather than inherits.

The upper and lower clouds are fitted SEPARATELY, split by which bone dominates
each vertex, so the two halves can be compared against their own bone
centrelines. Three readings are then possible and they mean different things:

  * both planes agree with their own half's bones -- the GEOMETRY is in two
    halves too, and the character was authored that way;
  * both planes land on one line while the bones straddle it -- the geometry is
    one body and both bone halves are displaced from it, which is a rig fault
    and correctable;
  * one agrees and one does not -- only that half is wrong.

**The residual curve is printed either side of the optimum.** A mirror fit on a
roughly tubular body is weakly determined, and a flat curve means the answer is
noise however confident the minimum looks. Sharpness is the difference between
a measurement and a number.

`--control` adds Spartan Mark V, whose halves are square in his own bundle
(0.0 mm on every pair, every axis): his two fitted planes must land on each
other and on his bones. An instrument that cannot return the right answer for
him says nothing about anybody else.

Everything is measured in the REST pose of the file that ships. Nothing is
written.
"""
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

import cloth_collide_installed as cci
import patch_springs as ps
import UnityPy

CONTROL = ("Spartan Mark V", )
LOWER = ("LeftUpperLeg", "RightUpperLeg")
UPPER = ("Spine", "Chest", "UpperChest", "Neck", "Head",
         "LeftShoulder", "RightShoulder", "LeftUpperArm", "RightUpperArm")


def triangles(mt):
    """(n, 3) vertex indices for every triangle in the mesh, or None."""
    raw = mt.get("m_IndexBuffer")
    if raw is None:
        return None
    buf = bytes(raw) if not isinstance(raw, bytes) else raw
    fmt = mt.get("m_IndexFormat")
    if fmt is None:
        fmt = 0 if mt.get("m_Use16BitIndices", 1) else 1
    dt = np.dtype("<u2") if int(fmt) == 0 else np.dtype("<u4")
    wide = dt.itemsize
    out = []
    for sm in (mt.get("m_SubMeshes") or []):
        if int(sm.get("topology", 0)) != 0:      # 0 = Triangles
            continue
        n = int(sm.get("indexCount", 0))
        fb = int(sm.get("firstByte", 0))
        if n < 3 or fb + n * wide > len(buf):
            continue
        idx = np.frombuffer(buf[fb:fb + n * wide], dtype=dt).astype(np.int64)
        idx = idx + int(sm.get("baseVertex", 0) or 0)
        out.append(idx[:n - n % 3].reshape(-1, 3))
    if not out:
        return None
    return np.concatenate(out)


def sample_surface(P, tri, lab, per_m2=400000.0, rng=None):
    """Points scattered over the triangles, density proportional to area."""
    rng = rng or np.random.default_rng(0)
    A, B, C = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    want = area * per_m2
    n = rng.poisson(np.clip(want, 0.0, 1e6)).astype(np.int64)
    keep = n > 0
    if not keep.any():
        return np.zeros((0, 3)), np.zeros(0, dtype=lab.dtype)
    rep = np.repeat(np.nonzero(keep)[0], n[keep])
    u = rng.random(len(rep))
    v = rng.random(len(rep))
    flip = u + v > 1.0
    u[flip], v[flip] = 1.0 - u[flip], 1.0 - v[flip]
    a, b, c = A[rep], B[rep], C[rep]
    pts = a + u[:, None] * (b - a) + v[:, None] * (c - a)
    # A triangle's label is its majority vertex label; ties go to vertex 0,
    # which only matters on the handful of triangles that span the waist.
    tl = lab[tri[rep, 0]].copy()
    same = (lab[tri[rep, 1]] == lab[tri[rep, 2]])
    tl[same] = lab[tri[rep, 1]][same]
    return pts, tl


def skinned_cloud(path):
    """Skinned world vertices, plus the dominant bone's path id per vertex."""
    human, tf, go_tf, springs, joints, colliders, groups, world = cci.read(path)
    env = UnityPy.load(path)
    meshes, smrs = {}, []
    for o in env.objects:
        if o.type.name == "Mesh":
            meshes[o.path_id] = o.read_typetree()
        elif o.type.name == "SkinnedMeshRenderer":
            smrs.append(o.read_typetree())

    pts, dom, tris, base, parts = [], [], [], 0, []
    for r in smrs:
        mt = meshes.get((r.get("m_Mesh") or {}).get("m_PathID"))
        if mt is None:
            continue
        got = ps.decode(mt)
        bones = [b["m_PathID"] for b in (r.get("m_Bones") or [])]
        bind = [ps.mat4(m) for m in (mt.get("m_BindPose") or [])]
        if got is None or not bones or len(bind) != len(bones):
            continue
        V, W, I = got
        M = np.array([ps.mul(ps.trs(*world(b)), bind[i])
                      for i, b in enumerate(bones)],
                     dtype=np.float64).reshape(len(bones), 3, 4)
        v = np.asarray(V, dtype=np.float64)
        w = np.asarray(W, dtype=np.float64)
        idx = np.asarray(I, dtype=np.int64).clip(0, len(bones) - 1)
        v4 = np.concatenate([v, np.ones((len(v), 1))], axis=1)
        out = np.zeros((len(v), 3))
        for k in range(w.shape[1]):
            Mk = M[idx[:, k]]
            out += w[:, k, None] * np.einsum("nij,nj->ni", Mk, v4)
        # An unweighted vertex skins to the origin, which would drag both the
        # fit and any triangle touching it. Keep the array dense so triangle
        # indices stay valid, and drop the triangles instead.
        ok = w.sum(axis=1) > 1e-6
        best = idx[np.arange(len(v)), w.argmax(axis=1)]
        tri = triangles(mt)
        if tri is not None and len(tri):
            tri = tri[(tri >= 0).all(axis=1) & (tri < len(v)).all(axis=1)]
            tri = tri[ok[tri].all(axis=1)]
            if len(tri):
                tris.append(tri + base)
        pts.append(np.where(ok[:, None], out, np.nan))
        dom.append(np.asarray([bones[j] for j in best], dtype=np.int64))
        parts.append((mt.get("m_Name") or "?", base, base + len(v),
                      (tri + base) if tri is not None and len(tri) else None))
        base += len(v)
    if not pts:
        return None
    P = np.concatenate(pts)
    T = np.concatenate(tris) if tris else None
    return P, np.concatenate(dom), T, parts, human, tf, world


def label(dom, human, tf):
    """lower / upper / other per vertex, by rig DESCENT and not by name."""
    name_pid = {}
    for pid, n in tf.items():
        if n.get("name"):
            name_pid.setdefault(n["name"], pid)

    def pids(keys):
        out = set()
        for k in keys:
            bn = cci.hname(human, k)
            if bn and bn in name_pid:
                out.add(name_pid[bn])
        return out

    lo_roots, up_roots = pids(LOWER), pids(UPPER)
    memo = {}

    def cls(pid):
        if pid in memo:
            return memo[pid]
        chain, cur, seen, ans = [], pid, set(), "other"
        while cur and cur in tf and cur not in seen:
            seen.add(cur)
            if cur in memo:
                ans = memo[cur]
                break
            if cur in lo_roots:
                ans = "lower"
                break
            if cur in up_roots:
                ans = "upper"
                break
            chain.append(cur)
            cur = tf[cur]["f"]
        for c in chain:
            memo[c] = ans
        memo[pid] = ans
        return ans

    return np.asarray([cls(int(p)) for p in dom])


def fit(P, lo=-0.15, hi=0.15):
    """The plane x = c the cloud is most nearly symmetric about, and its score.

    Scored by the MEDIAN nearest-neighbour distance of the reflected cloud.
    """
    if len(P) < 200:
        return None
    # The TREE keeps every sample -- it sets the residual floor, and thinning
    # it is thinning the ruler. Only the QUERY set is subsampled, which costs
    # precision in the mean and nothing in the floor.
    tree = cKDTree(P)
    q = P if len(P) <= 20000 else P[
        np.random.default_rng(0).choice(len(P), 20000, replace=False)]

    def score(c):
        Q = q.copy()
        Q[:, 0] = 2.0 * c - Q[:, 0]
        return float(np.median(tree.query(Q, k=1, workers=-1)[0]))

    cs = np.arange(lo, hi + 1e-9, 0.002)
    sc = [score(float(c)) for c in cs]
    c0 = float(cs[int(np.argmin(sc))])
    fine = np.arange(c0 - 0.002, c0 + 0.002 + 1e-9, 0.0001)
    sf = [score(float(c)) for c in fine]
    best = float(fine[int(np.argmin(sf))])
    return best, score(best), score


def fit_yaw(P, half=0.02, step=0.5):
    """The best mirror plane when the plane is allowed to TURN, not just slide.

    A character standing a few degrees off the camera axis has NO plane
    `x = c` that mirrors him, so the sliding fit above degrades to a flat
    curve with a large residual -- which looks exactly like a mesh that is not
    symmetric, and must not be read as one. Here the plane's normal is
    `(cos t, 0, sin t)` and both the angle and the offset are fitted, so a
    turned body is measured rather than mistaken for an asymmetric one.
    """
    if len(P) < 200:
        return None
    tree = cKDTree(P)
    q = P if len(P) <= 8000 else P[
        np.random.default_rng(0).choice(len(P), 8000, replace=False)]

    def score(t, c):
        n = np.array([np.cos(np.radians(t)), 0.0, np.sin(np.radians(t))])
        Q = q - 2.0 * (q @ n - c)[:, None] * n
        return float(np.median(tree.query(Q, k=1, workers=-1)[0]))

    ts = np.arange(-15.0, 15.0 + 1e-9, step)
    cs = np.arange(-0.15, 0.15 + 1e-9, 0.005)
    best = (1e9, 0.0, 0.0)
    for t in ts:
        for c in cs:
            s = score(float(t), float(c))
            if s < best[0]:
                best = (s, float(t), float(c))
    s0, t0, c0 = best
    for t in np.arange(t0 - step, t0 + step + 1e-9, 0.1):
        for c in np.arange(c0 - 0.005, c0 + 0.005 + 1e-9, 0.0005):
            s = score(float(t), float(c))
            if s < s0:
                s0, t0, c0 = s, float(t), float(c)
    return t0, c0, s0, score


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    files = list(args)
    if "--control" in sys.argv[1:]:
        base = os.path.dirname(os.path.abspath(files[0]))
        for n in CONTROL:
            p = os.path.join(base, n + ".yargchar")
            if os.path.exists(p) and p not in files:
                files.append(p)

    for f in files:
        name = os.path.basename(f)[:-9]
        got = skinned_cloud(f)
        if got is None:
            print("%s -- nothing skinned could be decoded" % name)
            continue
        P, dom, T, parts, human, tf, world = got
        lab = label(dom, human, tf)
        print("")
        print("%s -- %d skinned vertices (%d lower, %d upper, %d other)"
              % (name, len(P), (lab == "lower").sum(), (lab == "upper").sum(),
                 (lab == "other").sum()))
        if T is None or not len(T):
            print("  NO TRIANGLES could be read -- falling back to vertices, "
                  "whose residual floor is this mesh's own edge length")
            S, slab = P[~np.isnan(P[:, 0])], lab[~np.isnan(P[:, 0])]
        else:
            S, slab = sample_surface(P, T, lab)
            print("  %d triangles -> %d surface samples (%d lower, %d upper, "
                  "%d other)" % (len(T), len(S), (slab == "lower").sum(),
                                 (slab == "upper").sum(),
                                 (slab == "other").sum()))

        name_pid = {}
        for pid, n in tf.items():
            if n.get("name"):
                name_pid.setdefault(n["name"], pid)

        def bone_centre(keys):
            xs = []
            for k in keys:
                bn = cci.hname(human, k)
                if bn and bn in name_pid:
                    xs.append(world(name_pid[bn])[0][0])
            return (sum(xs) / len(xs)) if xs else None

        bc = {"lower": bone_centre(LOWER),
              "upper": bone_centre(("LeftUpperArm", "RightUpperArm"))}

        for half in ("lower", "upper", "all"):
            Q = S if half == "all" else S[slab == half]
            r = fit(Q)
            if r is None:
                print("  %-6s too few vertices (%d) to fit" % (half, len(Q)))
                continue
            c, s, score = r
            b = bc.get(half)
            tail = ""
            if b is not None:
                tail = ("   bones say %+.2f mm   plane - bones %+.2f mm"
                        % (b * 1000, (c - b) * 1000))
            print("  %-6s %6d verts   mirror plane x = %+8.2f mm   "
                  "median residual %6.2f mm%s"
                  % (half, len(Q), c * 1000, s * 1000, tail))
            curve = "   ".join("%+d:%.2f" % (d, score(c + d / 1000.0) * 1000)
                               for d in (-20, -10, -5, 0, 5, 10, 20))
            print("         residual at c%+d..%+d mm: %s" % (-20, 20, curve))

        # Per mesh. A character wearing a cape on one shoulder, a bandolier
        # across his chest and a holster on one thigh is NOT mirror-symmetric
        # as a whole, and a whole-body fit on him is a weighted average of the
        # parts that are and the parts that are not. A helmet is symmetric; a
        # cape is not; and each one says so itself in its own residual. Read
        # the parts whose residual is near the control's floor and ignore the
        # rest -- that is the whole reason this breakdown exists.
        print("  per mesh, sharpest first "
              "(trust a part whose residual is small AND whose curve climbs):")
        rows = []
        for mname, lo, hi, tri in parts:
            if tri is None or len(tri) < 50:
                continue
            Q, _ = sample_surface(P, tri, lab)
            r = fit(Q)
            if r is None:
                continue
            c, s, score = r
            climb = min(score(c - 0.005), score(c + 0.005)) - s
            rows.append((climb, mname, hi - lo, len(Q), c, s))
        for climb, mname, nv, ns, c, s in sorted(rows, reverse=True):
            print("    %-22s %6d verts %8d samples   x = %+8.2f mm   "
                  "residual %6.2f mm   climbs %+5.2f mm at +-5"
                  % (mname[:22], nv, ns, c * 1000, s * 1000, climb * 1000))

        if "--yaw" in sys.argv[1:]:
            print("  letting the plane TURN as well as slide:")
            for mname, lo, hi, tri in parts:
                if tri is None or len(tri) < 50:
                    continue
                Q, _ = sample_surface(P, tri, lab, per_m2=60000.0)
                r = fit_yaw(Q)
                if r is None:
                    continue
                t, c, s, score = r
                flat = score(0.0, c)
                print("    %-22s turned %+6.2f deg   offset %+8.2f mm along "
                      "its own normal   residual %6.2f mm   "
                      "(%6.2f mm if the plane is held square)"
                      % (mname[:22], t, c * 1000, s * 1000, flat * 1000))
    return 0


if __name__ == "__main__":
    sys.exit(main())
