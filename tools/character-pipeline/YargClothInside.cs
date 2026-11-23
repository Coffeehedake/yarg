// HAS THIS CLOTH VERTEX CROSSED FROM OUTSIDE THE BODY TO INSIDE IT?
// Lives in tools/ for reference only; copy into a SCRATCH COPY of the Unity project.
//
//   Unity -batchmode -quit -projectPath <scratch> -executeMethod YargClothInside.Run
//         -yargchars "<path.yargchar>|<Name>" -outDir <out>
//         [-frames 1] [-step 0.125] [-warmup 1.0] [-yaw 0]
//         [-pushArm 0.00]        <-- the synthetic positive, swept across magnitudes
//         [-maxDepth 0.25]       <-- the nearest-surface search cutoff, reported not hidden
//
// ===================================================================================
// WHY THIS EXISTS, AND WHAT IT REPLACES
// ===================================================================================
//
// YargClothPenetration.cs asked the question in SCREEN SPACE: a fault pixel was one where cloth
// was on the ray, body was on the ray, the body was NEARER, and the gap between them was smaller
// than a drape distance. That instrument FAILED ITS OWN CONTROLS, and the way it failed is the
// reason this file is written differently rather than written again.
//
// Measured on Power Girl, 2026-11-22, displacing her upper arm 0 -> 40 mm:
//
//      armPush   fault px @5mm   @10mm   @20mm   @40mm   @80mm
//      0.000           397       709     1254    1921    6419
//      0.005           395       706     1254    1914    6481
//      0.010           396       710     1255    1923    6555
//      0.020           397       716     1258    1916    6591
//      0.040           398       712     1269    1821    6461
//
// Flat at every drape width, while the arm demonstrably moved (motion_px 155,656 -> 158,660).
// Two defects, and the second is the one that matters here:
//
//   1. THE DENOMINATOR WAS NEAR-TAUTOLOGICAL. "Draped" was defined as "body nearer and close",
//      and a fault as "draped AND the body is visible". With opaque materials a nearer body IS a
//      visible body, so the ratio approached 1 by construction. It measured the definition.
//
//   2. PROXIMITY GOES BLIND EXACTLY WHERE THE FAULT IS WORST. As a deltoid emerges FURTHER
//      through a mantle, the gap between arm and cloth GROWS, so those pixels leave the drape
//      window instead of entering it. The condition that correctly excluded a cape hanging
//      behind a chest also excludes a limb that has fully broken through. It catches the instant
//      of emergence and loses the emerged state -- a false negative that SCALES WITH SEVERITY,
//      which is strictly worse than the false positive it replaced, because it fails silently on
//      the bad cases.
//
// THE DESIGN RULE THAT COMES OUT OF THAT: the quantity must be MONOTONE IN SEVERITY BY
// CONSTRUCTION. "Is this cloth vertex inside the body" is: the deeper a limb comes through, the
// more cloth vertices are enclosed and the deeper they sit. There is no window to fall out of.
//
// And no render is needed to answer it. A body outside its garment is visible from whichever
// direction the garment faces, so the geometric answer is sufficient; screen space only added a
// camera, a depth shader, a pipeline dependency and three ways to be wrong.
//
// ===================================================================================
// WHAT IT MEASURES
// ===================================================================================
//
// For every cloth vertex, in WORLD space, on a pose the Animator produced:
//
//     nearest point on the BODY SURFACE  ->  unsigned distance
//     sign of (vertex - nearest) . N     ->  inside (negative) or outside (positive)
//
// N is the AREA-WEIGHTED VERTEX PSEUDONORMAL of the body mesh, interpolated barycentrically at
// the nearest point. Not the face normal: when the nearest point lands on an edge or a vertex --
// which is most of them on a dense mesh -- a single face's normal is one of two or more equally
// valid answers, and the choice decides the sign. The area-weighted vertex normal is the standard
// fix (Baerentzen & Aanaes) and is EXACT for a closed surface, which is why this file measures
// whether the body mesh is closed instead of assuming it (control A below).
//
// AGAINST THE REAL BODY MESH, NOT CAPSULES, and that substitution is now measured rather than
// assumed. A sibling session measured the authored spring colliders against the skin they stand
// for, rest pose, on the bundle:
//
//      fml_un_L_clav   radius 94.4 mm, nearest skin at 38.7 mm  ->  stands 55.7 mm proud
//      fml_un_R_clav   radius 94.7 mm, nearest skin at 43.9 mm  ->  stands 50.8 mm proud
//      heel 67 mm, loarm 29 mm, upleg 15 mm, uparm 10 mm proud
//
// So anything within a ~5 cm shell of that joint was being counted as penetration WITHOUT
// TOUCHING THE BODY. That is the mechanism behind fml_un_L_clav owning 21.7% of all recorded
// cape-into-body contact, and it is why a yoke resting correctly on a collarbone read as a
// fault. A surface does not have that failure mode. (That measurement itself nearly came out
// with the opposite sign -- it was a left/right SYMMETRY control that caught it, which is the
// reason control E exists below.)
//
// THE DENOMINATOR IS MEASURED INDEPENDENTLY OF THE NUMERATOR. Numerator: cloth vertices whose
// signed offset is negative. Denominator: ALL cloth vertices. Neither term is derived from the
// other, and neither is a condition on the other. That is the specific thing the previous
// instrument got wrong.
//
// NO THRESHOLD DECIDES A VERDICT. Depth bands (0/2/5/10/20/40 mm) are all printed side by side,
// as `facing_check` prints its bands, so a reader sets the line rather than this file. The one
// cutoff that exists -- the nearest-surface search radius, default 250 mm -- is a performance
// bound, and the count it excluded and the deepest reading found are both printed so it cannot
// discard data silently. If the deepest reading ever approaches the cutoff, the cutoff is wrong
// and the output says so out loud.
//
// ===================================================================================
// THE CONTROLS, AND WHY EACH ONE IS A DIFFERENT ANIMAL
// ===================================================================================
//
// The rule being applied: a control is required exactly when the NULL RESULT and the BROKEN
// INSTRUMENT produce IDENTICAL OUTPUT. "0 cloth vertices inside the body" is what a clean
// character looks like AND what a dead probe looks like AND what a character whose under-garment
// body geometry was DELETED BY ITS AUTHOR looks like. Three causes, one number. So:
//
//   A  CLOSEDNESS (the precondition).  Share of welded body edges shared by exactly two
//      triangles. The pseudonormal sign is exact for a closed surface and undefined for a sheet.
//      If the body half comes back as an open shell, the sign is not evidence and this says so
//      BEFORE any count is printed. This measures the precondition directly rather than
//      cross-checking the conclusion, which is the cheaper and stronger of the two.
//
//   B  BODY PRESENCE.  Median and max nearest-body distance over all cloth vertices, and how
//      many had no body triangle within the cutoff at all. These characters are authored with
//      the skin under a garment sometimes modelled and sometimes deleted; where it is deleted
//      every cloth vertex is trivially outside and the clean reading means nothing. This is the
//      number that separates "nothing is inside the body" from "there is no body there".
//
//   C  NEGATIVE.  Power Girl at rest. Her cape is (a) PARENTED under her clavicles -- measured,
//      not assumed -- and she is the character this project treats as correctly built.
//
//   D  POSITIVE, SWEPT ACROSS MAGNITUDES.  -pushArm displaces both upper arms outward along
//      (arm - chest), re-applied after every anim.Update because the Animator rewrites bone
//      transforms every frame. The count must RISE, and KEEP RISING.
//
//      THE SWEEP IS THE POINT, not the single positive. A synthetic fault at ONE magnitude came
//      back 397 against a clean 397 and read as "no response", which is indistinguishable from a
//      plumbing fault and is exactly how it would have been debugged. FIVE magnitudes is what
//      turned it into "the response runs backwards". A design whose central claim is monotonicity
//      and which is tested at one magnitude has its central property unmeasured.
//
//   E  SYMMETRY.  At rest, on a symmetric character, paired left/right regions must agree. This
//      is a free second opinion on the SIGN, from a direction that shares no code with it: a
//      pseudonormal bug, a welding bug or a winding bug has no reason to be symmetric.
//
// A failure filter gets a negative control too, and more than an ordinary measurement does,
// because its false positives look like diligence. The last launcher grepped logs for `FATAL`
// and matched the `FatalException` in every install path -- a false positive written up that
// morning and reimplemented that afternoon. Sentinels here are prefixed `[INSIDE]` for that
// reason, and any pattern that greps for trouble is to be run against a known-good log first.
//
// ===================================================================================
// WHERE IT HAS TO RUN, AND WHY IT IS NOT A PYTHON PASS
// ===================================================================================
//
// Inside Unity, in the loop where the posed vertices already exist. The shoulder yoke is RIGIDLY
// SKINNED -- its bones are on no spring chain -- so its animated position is pure skinning and
// needs no solver. But the POSE still has to come from Unity's humanoid retargeter: this project
// measured that sampling a clip directly and letting the Animator retarget it through the Avatar
// give different results, with 0 of 120 shared frames matching. A Python pass over the bundle
// would have to reinvent retargeting to get the pose, and would get a different one.
//
// THE BODY/CLOTH SPLIT IS THE AVATAR'S, NOT A NAME MATCH, and is byte-for-byte the split
// YargClothPenetration used (Power Girl: bodyTris=23449 clothTris=35761) so the two instruments
// are comparable on the same frames. Triangles whose three vertices are all dominantly weighted
// to a HUMANOID bone are body; everything else is cloth, hair and props. Batman's cape bones are
// all non-humanoid, so his cape falls out of the humanoid map rather than out of a string match
// on "cape" -- his rig also carries fml_un_L_capeClav_a and fml_un_L_samurai_claviclePad_1, and a
// name matcher on this project has already found bones an earlier run of itself invented.
//
// WHAT A NEGATIVE OFFSET IS NOT. It is not automatically a defect. A shirt's inner layer, a
// collar lining, a sock top and a waistband are authored inside the skin on purpose, and the
// geometric test is RIGHT about them. This file therefore reports per region and per depth band
// and compares characters against each other; it does not pronounce. Same standing as the
// helmet at 100% face occlusion and the mouth lining at negative volume already written up in
// the README -- the instrument is correct and the geometry is correct.
//
// Nothing here writes to any character, bundle or project asset.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Unity.Collections;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using YARG.ContentBrowser.CharacterSelect;
using YARG.Helpers;
using YARG.Helpers.Extensions;

public static class YargClothInside
{
    // Every band is printed. None of them gates anything.
    private static readonly double[] BANDS = { 0.000, 0.002, 0.005, 0.010, 0.020, 0.040 };

    // Welding quantum: 0.01 mm. Duplicated vertices at a UV seam would otherwise each receive
    // only part of the incident faces, and the pseudonormal would then be wrong exactly along
    // the seams -- which is where a garment edge most often sits.
    private const float WELD = 1e-5f;

    private static string Arg(string[] a, string n)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], n, StringComparison.OrdinalIgnoreCase)) return a[i + 1];
        return null;
    }

    private static string F6(double d) { return d.ToString("0.000000", CultureInfo.InvariantCulture); }
    private static string F3(double d) { return d.ToString("0.000", CultureInfo.InvariantCulture); }

    // ---------------------------------------------------------------------------------------
    // The body surface: a welded, world-space triangle soup carrying area-weighted vertex
    // normals and a humanoid region label per triangle.
    // ---------------------------------------------------------------------------------------
    private sealed class Surface
    {
        public readonly List<Vector3> V = new List<Vector3>();
        public readonly List<Vector3> N = new List<Vector3>();
        public readonly List<int> T = new List<int>();          // 3 per triangle
        public readonly List<int> Region = new List<int>();     // 1 per triangle
        private readonly Dictionary<long, int> _weld = new Dictionary<long, int>();

        private static long Key(Vector3 p)
        {
            // 21 bits per axis at 0.01 mm covers +-10 m, which is four times the tallest
            // character here. Quantising rather than hashing the float means two vertices
            // written 0.0000001 apart by the skinning weld together.
            long x = (long) Mathf.Round(p.x / WELD) + 1048576;
            long y = (long) Mathf.Round(p.y / WELD) + 1048576;
            long z = (long) Mathf.Round(p.z / WELD) + 1048576;
            return (x << 42) ^ (y << 21) ^ z;
        }

        public int Add(Vector3 p)
        {
            var k = Key(p);
            if (_weld.TryGetValue(k, out var i)) return i;
            i = V.Count;
            _weld[k] = i;
            V.Add(p);
            N.Add(Vector3.zero);
            return i;
        }

        /// `humanVote` is how many of the three vertices are dominantly weighted to a humanoid
        /// bone, 0..3. Kept per triangle rather than collapsed to a boolean because the two
        /// candidate SPLITS need different things from it: the weight split wants vote == 3 per
        /// triangle, and the component split wants the vote SUMMED over a whole connected piece.
        public readonly List<int> HumanVote = new List<int>();

        // WHICH MATERIAL EACH TRIANGLE CAME FROM, which is the only thing in the file that can
        // say what a piece IS. A piece at humanoid_share 0.000 with ~2,200 triangles is equally
        // consistent with a boot, a glove, a hair clump and a shoulder pad, and a control run
        // against hair comes back flat for a reason indistinguishable from the flat already in
        // hand. Names are printed IN FULL and never truncated: three of Scott Hall's materials
        // share their first fourteen characters -- Mouth, Teeth and Tongue -- so a truncated
        // column cannot say which piece a verdict is about.
        public readonly List<int> Mat = new List<int>();

        /// The bone that drives this triangle, by name-table id. See VertDomBone.
        public readonly List<int> Bone = new List<int>();

        public void AddTriangle(Vector3 a, Vector3 b, Vector3 c, int region, int humanVote, int mat,
                                int bone = -1)
        {
            int ia = Add(a), ib = Add(b), ic = Add(c);
            if (ia == ib || ib == ic || ia == ic) return;   // degenerate after welding
            T.Add(ia); T.Add(ib); T.Add(ic);
            Region.Add(region);
            HumanVote.Add(humanVote);
            Mat.Add(mat);
            Bone.Add(bone);
            // Area-weighted: the cross product's LENGTH is twice the area, so accumulating the
            // un-normalised cross product weights each face by its own area without a second
            // pass. Large faces should dominate a vertex normal; a fan of slivers should not.
            var n = Vector3.Cross(b - a, c - a);
            N[ia] += n; N[ib] += n; N[ic] += n;
        }

        public void Finish()
        {
            for (int i = 0; i < N.Count; i++)
            {
                var n = N[i];
                N[i] = n.sqrMagnitude > 1e-20f ? n.normalized : Vector3.zero;
            }
        }

        public int TriCount { get { return T.Count / 3; } }

        /// A new Surface holding only the triangles `keep` accepts, re-welded and with its vertex
        /// normals re-accumulated from THOSE TRIANGLES ONLY. That last part is the reason this is
        /// a rebuild and not a mask: a garment triangle sharing a welded vertex with the skin
        /// would otherwise contribute to the skin's pseudonormal and bend the sign near every
        /// seam, which is precisely where a garment edge sits.
        public Surface Subset(Func<int, bool> keep)
        {
            var s = new Surface();
            for (int t = 0; t < TriCount; t++)
            {
                if (!keep(t)) continue;
                s.AddTriangle(V[T[t * 3]], V[T[t * 3 + 1]], V[T[t * 3 + 2]],
                              Region[t], HumanVote[t], Mat[t], Bone[t]);
            }
            s.Finish();
            return s;
        }

        /// The distinct welded vertices used by the triangles `keep` accepts.
        public List<Vector3> VertsOf(Func<int, bool> keep)
        {
            var seen = new HashSet<int>();
            var outv = new List<Vector3>();
            for (int t = 0; t < TriCount; t++)
            {
                if (!keep(t)) continue;
                for (int e = 0; e < 3; e++)
                    if (seen.Add(T[t * 3 + e])) outv.Add(V[T[t * 3 + e]]);
            }
            return outv;
        }

        /// CONTROL A. Share of edges shared by exactly two triangles. 1.0 is a closed surface,
        /// on which the pseudonormal sign is exact; far below it means a sheet, and a sheet has
        /// no inside for any vertex to be on the wrong side of.
        public void Closedness(out double share, out int edges, out int manifold)
        {
            var count = new Dictionary<long, int>();
            for (int t = 0; t < T.Count; t += 3)
                for (int e = 0; e < 3; e++)
                {
                    int u = T[t + e], v = T[t + (e + 1) % 3];
                    long lo = Math.Min(u, v), hi = Math.Max(u, v);
                    long k = (lo << 32) | hi;
                    count.TryGetValue(k, out var c);
                    count[k] = c + 1;
                }
            edges = count.Count;
            manifold = 0;
            foreach (var kv in count) if (kv.Value == 2) manifold++;
            share = edges > 0 ? (double) manifold / edges : 0.0;
        }

        // CONTROL A, PART TWO -- and this is the part that turns a failed precondition into a
        // usable instrument instead of a dead one.
        //
        // A whole-surface closedness of 0.887 does not say WHERE the 11% of boundary is. Two very
        // different shapes give that one number: a single closed body with a few holes punched in
        // it, and a heap of disconnected patches none of which has an interior. The first can
        // still be asked an inside/outside question; the second cannot, at any level of care.
        //
        // So: split the body into connected components across MANIFOLD EDGES ONLY -- edges shared
        // by exactly two triangles -- and ask each one separately whether it has any boundary at
        // all. Joining across a non-manifold edge would merge a patch tucked inside another
        // surface into its host and report a superset as closed; measured on Pomni, the same
        // mistake turned a 168-face piece into a 992-face one.
        //
        // A component with ZERO boundary edges is closed, exactly and by definition, so "closed"
        // here is not a threshold I chose. Those components are the only ones on which the sign
        // of the offset is a statement about geometry rather than about where the surface happens
        // to stop.
        public int[] Comp;
        public readonly Dictionary<int, int> CompTris = new Dictionary<int, int>();
        public readonly Dictionary<int, int> CompBoundary = new Dictionary<int, int>();

        public void Components()
        {
            int n = TriCount;
            Comp = new int[n];
            var parent = new int[n];
            for (int i = 0; i < n; i++) parent[i] = i;

            Func<int, int> find = null;
            find = x => { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; };

            var inc = new Dictionary<long, List<int>>();
            for (int t = 0; t < n; t++)
                for (int e = 0; e < 3; e++)
                {
                    int u = T[t * 3 + e], v = T[t * 3 + (e + 1) % 3];
                    long lo = Math.Min(u, v), hi = Math.Max(u, v);
                    long k = (lo << 32) | hi;
                    if (!inc.TryGetValue(k, out var l)) { l = new List<int>(2); inc[k] = l; }
                    l.Add(t);
                }
            foreach (var kv in inc)
                if (kv.Value.Count == 2)
                {
                    int a = find(kv.Value[0]), b = find(kv.Value[1]);
                    if (a != b) parent[a] = b;
                }

            for (int t = 0; t < n; t++)
            {
                int c = find(t);
                Comp[t] = c;
                CompTris.TryGetValue(c, out var ct);
                CompTris[c] = ct + 1;
            }
            foreach (var kv in inc)
            {
                if (kv.Value.Count == 2) continue;
                // A non-manifold or boundary edge counts against every component touching it.
                var seen = new HashSet<int>();
                foreach (var t in kv.Value)
                {
                    int c = Comp[t];
                    if (!seen.Add(c)) continue;
                    CompBoundary.TryGetValue(c, out var bc);
                    CompBoundary[c] = bc + 1;
                }
            }
        }

        public bool IsClosed(int comp)
        {
            CompBoundary.TryGetValue(comp, out var b);
            return b == 0;
        }
    }

    // ---------------------------------------------------------------------------------------
    // Uniform grid over the body triangles. Nearest-surface queries only.
    // ---------------------------------------------------------------------------------------
    private sealed class Grid
    {
        private readonly Surface _s;
        private readonly Vector3 _lo;
        private readonly float _cell;
        private readonly int _nx, _ny, _nz;
        private readonly List<int>[] _bins;

        public Grid(Surface s, int target)
        {
            _s = s;
            var lo = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
            var hi = new Vector3(float.MinValue, float.MinValue, float.MinValue);
            foreach (var v in s.V) { lo = Vector3.Min(lo, v); hi = Vector3.Max(hi, v); }
            _lo = lo - Vector3.one * 1e-3f;
            var ext = hi - lo + Vector3.one * 2e-3f;
            float longest = Mathf.Max(ext.x, Mathf.Max(ext.y, ext.z));
            _cell = Mathf.Max(longest / Mathf.Max(4, target), 1e-4f);
            _nx = Mathf.Max(1, Mathf.CeilToInt(ext.x / _cell));
            _ny = Mathf.Max(1, Mathf.CeilToInt(ext.y / _cell));
            _nz = Mathf.Max(1, Mathf.CeilToInt(ext.z / _cell));
            _bins = new List<int>[_nx * _ny * _nz];
            for (int t = 0; t < s.TriCount; t++)
            {
                var a = s.V[s.T[t * 3]]; var b = s.V[s.T[t * 3 + 1]]; var c = s.V[s.T[t * 3 + 2]];
                var tl = Vector3.Min(a, Vector3.Min(b, c));
                var th = Vector3.Max(a, Vector3.Max(b, c));
                int x0 = Cx(tl.x, _nx), x1 = Cx(th.x, _nx);
                int y0 = Cy(tl.y, _ny), y1 = Cy(th.y, _ny);
                int z0 = Cz(tl.z, _nz), z1 = Cz(th.z, _nz);
                for (int x = x0; x <= x1; x++)
                    for (int y = y0; y <= y1; y++)
                        for (int z = z0; z <= z1; z++)
                        {
                            int i = (x * _ny + y) * _nz + z;
                            if (_bins[i] == null) _bins[i] = new List<int>(4);
                            _bins[i].Add(t);
                        }
            }
        }

        public float Cell { get { return _cell; } }

        private int Cx(float v, int n) { return Mathf.Clamp((int) ((v - _lo.x) / _cell), 0, n - 1); }
        private int Cy(float v, int n) { return Mathf.Clamp((int) ((v - _lo.y) / _cell), 0, n - 1); }
        private int Cz(float v, int n) { return Mathf.Clamp((int) ((v - _lo.z) / _cell), 0, n - 1); }

        /// Nearest point on the surface. Returns false when nothing lies within `cutoff`.
        /// `point` comes back as well as `dist`, because the SIGN needs the direction from the
        /// surface to the vertex and a distance alone cannot give it.
        public bool Nearest(Vector3 p, float cutoff, out float dist, out Vector3 point,
                            out Vector3 normal, out int tri)
        {
            dist = float.MaxValue; point = p; normal = Vector3.zero; tri = -1;
            int cx = Cx(p.x, _nx), cy = Cy(p.y, _ny), cz = Cz(p.z, _nz);
            int maxRing = Mathf.CeilToInt(cutoff / _cell) + 1;
            float best = float.MaxValue;
            Vector3 bestN = Vector3.zero, bestQ = p; int bestT = -1;

            for (int r = 0; r <= maxRing; r++)
            {
                // A cell at Chebyshev ring r cannot be nearer than (r-1)*cell, so once the best
                // found beats that bound no further ring can improve on it. Conservative by one
                // ring on purpose -- the cheap version of this stops one ring early and misses.
                if (r > 1 && best <= (r - 1) * _cell) break;

                for (int x = cx - r; x <= cx + r; x++)
                {
                    if (x < 0 || x >= _nx) continue;
                    for (int y = cy - r; y <= cy + r; y++)
                    {
                        if (y < 0 || y >= _ny) continue;
                        for (int z = cz - r; z <= cz + r; z++)
                        {
                            if (z < 0 || z >= _nz) continue;
                            // shell only: skip the interior already scanned at smaller r
                            int cheb = Mathf.Max(Mathf.Abs(x - cx),
                                       Mathf.Max(Mathf.Abs(y - cy), Mathf.Abs(z - cz)));
                            if (cheb != r) continue;
                            var bin = _bins[(x * _ny + y) * _nz + z];
                            if (bin == null) continue;
                            for (int bi = 0; bi < bin.Count; bi++)
                            {
                                int t = bin[bi];
                                var a = _s.V[_s.T[t * 3]];
                                var b = _s.V[_s.T[t * 3 + 1]];
                                var c = _s.V[_s.T[t * 3 + 2]];
                                Vector3 q; float u, v2, w;
                                ClosestOnTriangle(p, a, b, c, out q, out u, out v2, out w);
                                float d = (p - q).magnitude;
                                if (d >= best) continue;
                                best = d;
                                bestT = t;
                                bestQ = q;
                                // Barycentric blend of the welded vertex pseudonormals. At an
                                // edge or a vertex -- most hits on a dense mesh -- this is the
                                // average of every incident face rather than a coin-flip between
                                // two of them.
                                var n = _s.N[_s.T[t * 3]] * u
                                      + _s.N[_s.T[t * 3 + 1]] * v2
                                      + _s.N[_s.T[t * 3 + 2]] * w;
                                if (n.sqrMagnitude <= 1e-20f) n = Vector3.Cross(b - a, c - a);
                                bestN = n.sqrMagnitude > 1e-20f ? n.normalized : Vector3.zero;
                            }
                        }
                    }
                }
            }
            if (bestT < 0 || best > cutoff) return false;
            dist = best; point = bestQ; normal = bestN; tri = bestT;
            return true;
        }
    }

    /// Ericson, Real-Time Collision Detection, 5.1.5 -- with the barycentric coordinates kept,
    /// because they are what lets the normal be interpolated instead of chosen.
    private static void ClosestOnTriangle(Vector3 p, Vector3 a, Vector3 b, Vector3 c,
                                          out Vector3 q, out float u, out float v, out float w)
    {
        Vector3 ab = b - a, ac = c - a, ap = p - a;
        float d1 = Vector3.Dot(ab, ap), d2 = Vector3.Dot(ac, ap);
        if (d1 <= 0f && d2 <= 0f) { q = a; u = 1f; v = 0f; w = 0f; return; }

        Vector3 bp = p - b;
        float d3 = Vector3.Dot(ab, bp), d4 = Vector3.Dot(ac, bp);
        if (d3 >= 0f && d4 <= d3) { q = b; u = 0f; v = 1f; w = 0f; return; }

        float vc = d1 * d4 - d3 * d2;
        if (vc <= 0f && d1 >= 0f && d3 <= 0f)
        {
            float t = d1 / (d1 - d3);
            q = a + ab * t; u = 1f - t; v = t; w = 0f; return;
        }

        Vector3 cp = p - c;
        float d5 = Vector3.Dot(ab, cp), d6 = Vector3.Dot(ac, cp);
        if (d6 >= 0f && d5 <= d6) { q = c; u = 0f; v = 0f; w = 1f; return; }

        float vb = d5 * d2 - d1 * d6;
        if (vb <= 0f && d2 >= 0f && d6 <= 0f)
        {
            float t = d2 / (d2 - d6);
            q = a + ac * t; u = 1f - t; v = 0f; w = t; return;
        }

        float va = d3 * d6 - d5 * d4;
        if (va <= 0f && (d4 - d3) >= 0f && (d5 - d6) >= 0f)
        {
            float t = (d4 - d3) / ((d4 - d3) + (d5 - d6));
            q = b + (c - b) * t; u = 0f; v = 1f - t; w = t; return;
        }

        float denom = 1f / (va + vb + vc);
        v = vb * denom; w = vc * denom; u = 1f - v - w;
        q = a + ab * v + ac * w;
    }

    // ---------------------------------------------------------------------------------------
    // The split. Identical in rule to YargClothPenetration.IsHumanVert, extended to return WHICH
    // humanoid bone, so a verdict can name a region instead of only a character. A vertex whose
    // dominant bone is a non-humanoid twist bone is NOT body, exactly as before -- that is what
    // makes the triangle counts comparable between the two instruments.
    // ---------------------------------------------------------------------------------------
    private static int[] VertRegion(SkinnedMeshRenderer smr, Dictionary<Transform, int> human)
    {
        var mesh = smr.sharedMesh;
        var res = new int[mesh.vertexCount];
        for (int i = 0; i < res.Length; i++) res[i] = -1;
        var bones = smr.bones;
        if (bones == null || bones.Length == 0) return res;

        var boneRegion = new Dictionary<int, int>();
        for (int i = 0; i < bones.Length; i++)
            if (bones[i] != null && human.TryGetValue(bones[i], out var r)) boneRegion[i] = r;
        if (boneRegion.Count == 0) return res;

        var per = mesh.GetBonesPerVertex();
        var w = mesh.GetAllBoneWeights();
        try
        {
            int c = 0;
            for (int v = 0; v < mesh.vertexCount && v < per.Length; v++)
            {
                int n = per[v];
                float best = -1f; int bb = -1;
                for (int k = 0; k < n; k++)
                {
                    var bw = w[c + k];
                    if (bw.weight > best) { best = bw.weight; bb = bw.boneIndex; }
                }
                c += n;
                if (bb >= 0 && boneRegion.TryGetValue(bb, out var r)) res[v] = r;
            }
        }
        finally
        {
            if (per.IsCreated) per.Dispose();
            if (w.IsCreated) w.Dispose();
        }
        return res;
    }

    /// WHICH BONE DRIVES EACH VERTEX, by name, humanoid or not.
    ///
    /// This replaces locating a piece by the humanoid bone nearest its centroid, which failed on
    /// Jinx: her braids run from her head to her ankles, so each 12,000-triangle braid reported as
    /// being over LeftUpperLeg, and the roster ranking built on that counted hair as garment. The
    /// bone that DRIVES a piece is the author's own declaration and does not care how far the
    /// piece hangs -- a braid is weighted to hair bones under Head at any length, a legging to the
    /// leg. Distance is a guess about a piece; weight is a statement about it.
    ///
    /// The earlier caution stands and does not bite here: a weight test measures what DRIVES a
    /// triangle rather than what it IS, and what drives it is exactly the question being asked.
    private static int[] VertDomBone(SkinnedMeshRenderer smr, List<string> names,
                                     Dictionary<string, int> index)
    {
        var mesh = smr.sharedMesh;
        var res = new int[mesh.vertexCount];
        for (int i = 0; i < res.Length; i++) res[i] = -1;
        var bones = smr.bones;
        if (bones == null || bones.Length == 0) return res;
        var ids = new int[bones.Length];
        for (int i = 0; i < bones.Length; i++)
        {
            if (bones[i] == null) { ids[i] = -1; continue; }
            var nm = bones[i].name;
            if (!index.TryGetValue(nm, out var id))
            {
                id = names.Count; index[nm] = id; names.Add(nm);
            }
            ids[i] = id;
        }
        var per = mesh.GetBonesPerVertex();
        var w = mesh.GetAllBoneWeights();
        try
        {
            int c = 0;
            for (int v = 0; v < mesh.vertexCount && v < per.Length; v++)
            {
                int cnt = per[v];
                float best = -1f; int bb = -1;
                for (int k = 0; k < cnt; k++)
                {
                    var bw = w[c + k];
                    if (bw.weight > best) { best = bw.weight; bb = bw.boneIndex; }
                }
                c += cnt;
                if (bb >= 0 && bb < ids.Length) res[v] = ids[bb];
            }
        }
        finally
        {
            if (per.IsCreated) per.Dispose();
            if (w.IsCreated) w.Dispose();
        }
        return res;
    }

    /// True for each vertex dominantly weighted to one of `targets` OR to any bone beneath one of
    /// them in the transform hierarchy. Descendants are included because pushing a lower leg also
    /// carries the foot, and skin near the ankle is weighted to the foot.
    private static bool[] VertDrivenBy(SkinnedMeshRenderer smr, HashSet<Transform> targets)
    {
        var mesh = smr.sharedMesh;
        var res = new bool[mesh.vertexCount];
        var bones = smr.bones;
        if (bones == null || bones.Length == 0 || targets.Count == 0) return res;
        var hit = new bool[bones.Length];
        for (int i = 0; i < bones.Length; i++)
        {
            var t = bones[i];
            int guard = 0;
            while (t != null && guard++ < 200)
            {
                if (targets.Contains(t)) { hit[i] = true; break; }
                t = t.parent;
            }
        }
        var per = mesh.GetBonesPerVertex();
        var w = mesh.GetAllBoneWeights();
        try
        {
            int c = 0;
            for (int v = 0; v < mesh.vertexCount && v < per.Length; v++)
            {
                int cnt = per[v];
                float best = -1f; int bb = -1;
                for (int k = 0; k < cnt; k++)
                {
                    var bw = w[c + k];
                    if (bw.weight > best) { best = bw.weight; bb = bw.boneIndex; }
                }
                c += cnt;
                if (bb >= 0 && bb < hit.Length) res[v] = hit[bb];
            }
        }
        finally
        {
            if (per.IsCreated) per.Dispose();
            if (w.IsCreated) w.Dispose();
        }
        return res;
    }

    /// Region -1 is real under the component split and is not an error: a body-labelled piece
    /// keeps all of its triangles, and some of those have no humanoid vertex to name them.
    private static string RegionLabel(List<string> names, int r)
    {
        return r >= 0 && r < names.Count ? names[r] : "(non-humanoid)";
    }

    private static double Median(List<float> xs)
    {
        if (xs.Count == 0) return double.NaN;
        xs.Sort();
        int m = xs.Count / 2;
        return xs.Count % 2 == 1 ? xs[m] : 0.5 * (xs[m - 1] + xs[m]);
    }

    public static void Run()
    {
        int failures = 0;
        var json = new StringBuilder();
        string outDir = null;
        try
        {
            var args = Environment.GetCommandLineArgs();
            var list = Arg(args, "-yargchars");
            outDir = Arg(args, "-outDir") ?? Arg(args, "-shotDir");
            Directory.CreateDirectory(outDir);
            int frames = int.TryParse(Arg(args, "-frames"), out var ff) ? ff : 1;
            float step = float.TryParse(Arg(args, "-step"), out var ss) ? ss : 0.125f;
            float warmup = float.TryParse(Arg(args, "-warmup"), out var ww) ? ww : 1.0f;
            float yaw = float.TryParse(Arg(args, "-yaw"), out var yy) ? yy : 0f;
            float pushArm = float.TryParse(Arg(args, "-pushArm"), out var pa) ? pa : 0f;
            // WHICH BONE THE SYNTHETIC POSITIVE MOVES, and along what.
            //
            // The upper arms were the right choice while the question was a deltoid through a
            // mantle. They are the WRONG choice on Power Girl once her sleeve turns out to be the
            // same connected shell as her deltoid: there is no separable garment over that bone,
            // so no displacement of it can push anything through anything, and the control comes
            // back flat for a reason that has nothing to do with the instrument.
            //
            // So the bone is an argument. A control needs a separable garment piece -- one at
            // humanoid_share 0.000 -- sitting over a bone the idle actually moves.
            //
            // `radial` keeps the committed arm behaviour, (bone - chest) normalised, so the
            // earlier numbers stay comparable. `x`/`y`/`z` push along a world axis signed by which
            // side of the hips the bone sits on, so both sides move OUTWARD rather than both
            // moving left. For a boot over a shin, lateral is the honest analogue of a deltoid
            // through a mantle; radial on a lower leg points mostly downward and would drive it
            // through the sole instead of the wall.
            var pushBones = (Arg(args, "-pushBones") ?? "LeftUpperArm,RightUpperArm")
                            .Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries);
            string pushAxis = (Arg(args, "-pushAxis") ?? "radial").ToLowerInvariant();
            float cutoff = float.TryParse(Arg(args, "-maxDepth"), out var md) ? md : 0.25f;
            int gridTarget = int.TryParse(Arg(args, "-grid"), out var gt) ? gt : 48;
            // INVENTORY MODE: the piece table and the idle bone travel, and NOT the two
            // measurement passes. It exists because choosing a control character is a different
            // question from measuring one, and it needs none of the expensive part.
            //
            // The question it answers, for every character on the roster: is there a SEPARABLE
            // garment piece -- humanoid_share 0.000, a shell of its own -- sitting over a bone
            // the idle actually moves? Power Girl has none. Her five separable pieces are all
            // hair at y=1.56..1.68 nearest Head, her costume is fused into two half-skin shells,
            // and the only thing her idle moves appreciably is her left hand (fingers travelling
            // 270-296 mm over six frames). So the arm control could never have worked on her, and
            // a lower-leg control would have been run against hair and come back flat for a
            // reason indistinguishable from the flat already in hand.
            bool inventory = Arg(args, "-inventory") != null;

            EditorSceneManager.OpenScene("Assets/Scenes/CharacterSelect.unity", OpenSceneMode.Single);
            var dm = UnityEngine.Object.FindFirstObjectByType<CharacterDisplayManager>();
            var so = new SerializedObject(dm);
            var podiumPrefab = so.FindProperty("_displayPrefab").objectReferenceValue as GameObject;
            var selected = so.FindProperty("_selectedLocation").objectReferenceValue as Transform;

            Debug.Log($"[INSIDE] frames={frames} warmup={warmup} yaw={yaw} pushArm={pushArm}m " +
                      $"cutoff={cutoff}m grid={gridTarget}");

            json.Append("{\n  \"push_arm\": ").Append(F6(pushArm))
                .Append(",\n  \"cutoff\": ").Append(F6(cutoff))
                .Append(",\n  \"characters\": [\n");
            bool first = true;

            foreach (var entry in list.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(entry)) continue;
                var bits = entry.Split('|');
                var file = bits[0].Trim();
                var name = bits.Length > 1 ? bits[1].Trim() : Path.GetFileNameWithoutExtension(file);
                GameObject podiumGo = null;
                AssetBundle bundle = null;
                if (!first) json.Append(",\n");
                first = false;
                json.Append("    {\n      \"name\": \"").Append(name).Append("\",\n");

                try
                {
                    podiumGo = (GameObject) PrefabUtility.InstantiatePrefab(podiumPrefab, selected);
                    podiumGo.transform.localPosition = Vector3.zero;
                    podiumGo.SetActive(true);
                    var podium = podiumGo.GetComponent<Podium>();

                    bundle = AssetBundle.LoadFromFile(file);
                    if (bundle == null) throw new Exception("could not load " + file);
                    var prefab = bundle.LoadAsset<GameObject>(
                        BackgroundHelper.CHARACTER_PREFAB_PATH.ToLowerInvariant());
                    if (prefab == null) throw new Exception("no character prefab");
                    var ch = UnityEngine.Object.Instantiate(prefab, podium.CharacterLocation);
                    ch.transform.SetParent(podium.CharacterLocation, false);
                    ch.transform.localPosition = Vector3.zero;
                    ch.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
                    ch.SetActive(true);
                    try
                    {
                        var vc = ch.GetComponent<YARG.Venue.Characters.VRMCharacter>();
                        if (vc != null) { vc.Initialize(); vc.SetPreviewIdle(); }
                    }
                    catch (Exception e)
                    {
                        Debug.Log($"[INSIDE] {name}: VRM init skipped: {e.GetType().Name}");
                    }

                    // The humanoid map IS the split, and it is also the region naming.
                    var anim = ch.GetComponent<Animator>();
                    var human = new Dictionary<Transform, int>();
                    var regionName = new List<string>();
                    if (anim != null)
                    {
                        if (anim.HasParameter("Attract")) anim.SetTrigger("Attract");
                        else if (anim.HasParameter("Idle")) anim.SetTrigger("Idle");
                        anim.Rebind();
                        anim.Update(warmup);
                        if (anim.isHuman)
                            foreach (HumanBodyBones hb in Enum.GetValues(typeof(HumanBodyBones)))
                            {
                                if (hb == HumanBodyBones.LastBone) continue;
                                var t = anim.GetBoneTransform(hb);
                                if (t == null || human.ContainsKey(t)) continue;
                                human[t] = regionName.Count;
                                regionName.Add(hb.ToString());
                            }
                    }
                    if (human.Count == 0)
                        Debug.LogWarning($"[INSIDE] {name}: no humanoid map -- body and cloth cannot " +
                                         "be separated, so this character is UNMEASURED rather than clean.");

                    var perFrame = new List<string>();
                    int bodyTris = 0, clothTris = 0, clothVerts = 0;
                    // A SEPARABLE GARMENT OVER A BONE THE IDLE NEVER MOVES IS NOT A CONTROL
                    // EITHER -- the synthetic displacement would be the only motion in the scene,
                    // which tests the probe against a pose the game never shows. So record, per
                    // humanoid bone, how far it travels across the sampled frames with NO
                    // synthetic push applied, and print it beside the pieces.
                    var boneStart = new Dictionary<Transform, Vector3>();
                    var boneTravel = new Dictionary<Transform, float>();
                    var matNames = new List<string>();
                    var matIndex = new Dictionary<string, int>();

                    for (int f = 0; f < frames; f++)
                    {
                        if (f > 0 && anim != null) anim.Update(step);

                        foreach (var kv in human)
                        {
                            var pos = kv.Key.position;
                            if (!boneStart.ContainsKey(kv.Key)) boneStart[kv.Key] = pos;
                            float tv = (pos - boneStart[kv.Key]).magnitude;
                            boneTravel.TryGetValue(kv.Key, out var ov);
                            if (tv > ov) boneTravel[kv.Key] = tv;
                        }

                        // ================================================================
                        // THE SUBJECT-MOVED GUARD
                        // ================================================================
                        //
                        // A displacement control that silently fails to displace anything
                        // produces a flat table, and a flat table is indistinguishable from a
                        // clean character. Three runs were lost to that tonight. So the harness
                        // asserts its own forcing rather than assuming it:
                        //
                        //   pushed_verts    skin vertices driven by the pushed bone or its
                        //                   descendants -- 0 means the bone drives no geometry
                        //   pushed_travel   how far they actually moved, which must be about the
                        //                   push distance. A rigid translation that keeps growing
                        //                   cannot produce an effect that SATURATES, and Jinx's
                        //                   did (42.24 -> 40.57 -> 40.19 -> 40.15 -> 40.11 ->
                        //                   40.07 mm), which was the tell that the forcing never
                        //                   reached the measured quantity
                        //   pushed_on_body  how many of them lie ON the body surface being
                        //                   queried. This is the one that catches Jinx: her leg
                        //                   vertices exist and moved, and NONE of them was in the
                        //                   body surface, because her legs were labelled cloth.
                        //                   The body moved past the cloth rather than through it
                        //
                        // Requires baking twice: once before the push as a reference, once after.
                        // That is the cost of a run being able to state that it measured anything.
                        //
                        // ORDER IS LOAD-BEARING AND WAS WRONG ONCE. The reference bake must happen
                        // BEFORE the displacement is applied; with the push block above it, both
                        // bakes were post-push, travel read 0.000mm on every character, and the
                        // guard refused the case it was built to pass. The push is applied just
                        // below this loop for that reason -- do not move it back up.
                        var refWorld = new Dictionary<SkinnedMeshRenderer, Vector3[]>();
                        var pushTargets = new HashSet<Transform>();
                        if (Math.Abs(pushArm) > 1e-6f && anim != null && anim.isHuman)
                        {
                            foreach (var bn in pushBones)
                            {
                                HumanBodyBones hb2;
                                if (!Enum.TryParse(bn.Trim(), true, out hb2)) continue;
                                var bt = anim.GetBoneTransform(hb2);
                                if (bt != null) pushTargets.Add(bt);
                            }
                            foreach (var smr0 in ch.GetComponentsInChildren<SkinnedMeshRenderer>())
                            {
                                if (!smr0.enabled || smr0.sharedMesh == null) continue;
                                var b0 = new Mesh();
                                smr0.BakeMesh(b0, true);
                                var m0 = Matrix4x4.TRS(smr0.transform.position,
                                                       smr0.transform.rotation, Vector3.one);
                                var v0 = b0.vertices;
                                var w0 = new Vector3[v0.Length];
                                for (int i = 0; i < v0.Length; i++) w0[i] = m0.MultiplyPoint3x4(v0[i]);
                                refWorld[smr0] = w0;
                            }
                        }

                        // After Update, before baking: the Animator rewrites bone transforms every
                        // frame, so the displacement has to be re-applied each frame or it
                        // silently only affects frame 0. That mistake was made and caught once
                        // already on this probe family.
                        if (Math.Abs(pushArm) > 1e-6f && anim != null && anim.isHuman)
                        {
                            var chest = anim.GetBoneTransform(HumanBodyBones.UpperChest)
                                        ?? anim.GetBoneTransform(HumanBodyBones.Chest)
                                        ?? anim.GetBoneTransform(HumanBodyBones.Spine);
                            var hips = anim.GetBoneTransform(HumanBodyBones.Hips);
                            foreach (var bn in pushBones)
                            {
                                HumanBodyBones hb;
                                if (!Enum.TryParse(bn.Trim(), true, out hb))
                                {
                                    if (f == 0)
                                        Debug.LogError($"[INSIDE] {name}: -pushBones named '{bn}', " +
                                                       "which is not a HumanBodyBones value -- the " +
                                                       "positive control did NOT move.");
                                    continue;
                                }
                                var t = anim.GetBoneTransform(hb);
                                if (t == null)
                                {
                                    if (f == 0)
                                        Debug.LogError($"[INSIDE] {name}: {hb} is not in this rig's " +
                                                       "humanoid map -- the positive control did NOT move.");
                                    continue;
                                }
                                Vector3 dir;
                                if (pushAxis == "radial")
                                {
                                    if (chest == null) continue;
                                    dir = (t.position - chest.position).normalized;
                                }
                                else
                                {
                                    var axis = pushAxis == "y" ? Vector3.up
                                             : pushAxis == "z" ? Vector3.forward : Vector3.right;
                                    var o = hips != null ? hips.position : Vector3.zero;
                                    float side = Vector3.Dot(t.position - o, axis);
                                    dir = axis * (side < 0f ? -1f : 1f);
                                }
                                t.position += dir * pushArm;
                            }
                        }


                        // Every bone AT OR BENEATH a pushed bone, by name, so a triangle can
                        // be asked whether the body being displaced is what drives it.
                        var pushedBoneNames = new HashSet<string>();
                        foreach (var pt in pushTargets)
                            foreach (var tr in pt.GetComponentsInChildren<Transform>())
                                pushedBoneNames.Add(tr.name);

                        var surf = new Surface();
                        var pushedWorld = new List<Vector3>();
                        var pushedTravel = new List<float>();
                        // THE FIFTH NUMBER, and on this evidence the only one that decides whether
                        // a bone can host the control at all.
                        //
                        // cloth_over_push came back NON-ZERO on both subjects -- Jinx 10,838,
                        // Power Girl 2,234 under the weight split -- while both tables stayed
                        // flat. So "there is cloth over the limb" is not the condition either.
                        // The cloth over a limb is usually SKINNED TO THAT LIMB, so it travels
                        // with the push and nothing ever changes side. A fault needs the body to
                        // move and the garment to STAY, which is exactly what spring-driven cloth
                        // does in the game and what rigidly-skinned cloth never does.
                        //
                        // So: vertices NOT driven by the pushed bone, which stayed put while the
                        // bone moved its full distance, and which sit near that bone. That is the
                        // population a displacement control can actually cross. Zero means this
                        // bone cannot host the control on this character, whatever else is true.
                        int staticNearPush = 0, movingNearPush = 0;
                        var boneNames = new List<string>();
                        var boneIndex = new Dictionary<string, int>();
                        bodyTris = clothTris = 0;
                        // WHICH RENDERERS THE TWO HALVES COME FROM, because that decides whether
                        // the local-to-world convention below can hurt the answer at all. Body and
                        // cloth taken from ONE renderer share one transform, so a wrong convention
                        // displaces them TOGETHER and every relative reading survives it. The
                        // convention only becomes load-bearing when the halves come from DIFFERENT
                        // renderers sitting at different transforms -- so the log says, rather than
                        // my being satisfied that the previous probe's renders "looked right",
                        // which is a screenshot read and has misled this project before.
                        var smrLog = new StringBuilder();

                        foreach (var smr in ch.GetComponentsInChildren<SkinnedMeshRenderer>())
                        {
                            if (!smr.enabled || smr.sharedMesh == null) continue;
                            int bBefore = bodyTris, cBefore = clothTris;
                            var baked = new Mesh();
                            smr.BakeMesh(baked, true);
                            // BakeMesh writes the renderer's LOCAL space and `useScale:true` has
                            // already applied the transform's scale, so the remaining conversion
                            // to world is position and rotation only -- NOT the full localToWorld,
                            // which would apply the scale a second time.
                            var toWorld = Matrix4x4.TRS(smr.transform.position,
                                                        smr.transform.rotation, Vector3.one);
                            var bv = baked.vertices;
                            var reg = VertRegion(smr, human);
                            var dom = VertDomBone(smr, boneNames, boneIndex);
                            var world = new Vector3[bv.Length];
                            for (int i = 0; i < bv.Length; i++) world[i] = toWorld.MultiplyPoint3x4(bv[i]);

                            for (int s = 0; s < baked.subMeshCount; s++)
                            {
                                var tri = baked.GetTriangles(s);
                                // Submesh s is drawn with sharedMaterials[s]. Guarded because a
                                // renderer may carry fewer materials than it has submeshes.
                                var sm = smr.sharedMaterials;
                                string mname = smr.name + " / " +
                                    ((sm != null && s < sm.Length && sm[s] != null)
                                     ? sm[s].name : "<none>");
                                int matId;
                                if (!matIndex.TryGetValue(mname, out matId))
                                {
                                    matId = matNames.Count;
                                    matIndex[mname] = matId;
                                    matNames.Add(mname);
                                }
                                for (int i = 0; i + 2 < tri.Length; i += 3)
                                {
                                    int i0 = tri[i], i1 = tri[i + 1], i2 = tri[i + 2];
                                    if (i0 >= reg.Length || i1 >= reg.Length || i2 >= reg.Length) continue;
                                    int vote = (reg[i0] >= 0 ? 1 : 0) + (reg[i1] >= 0 ? 1 : 0)
                                             + (reg[i2] >= 0 ? 1 : 0);
                                    if (vote == 3) bodyTris++; else clothTris++;
                                    // EVERY triangle goes in, body and garment alike, because both
                                    // candidate splits are derived from this one accumulation
                                    // further down. Region is the first vertex's humanoid bone
                                    // where there is one -- enough to name a neighbourhood, and
                                    // not pretending to a precision a per-triangle vote would not
                                    // have either.
                                    int rg = reg[i0] >= 0 ? reg[i0]
                                           : (reg[i1] >= 0 ? reg[i1] : reg[i2]);
                                    surf.AddTriangle(world[i0], world[i1], world[i2], rg, vote,
                                                     matId, dom[i0]);
                                }
                            }
                            // The guard's measurement, per renderer.
                            if (refWorld.Count > 0 && refWorld.TryGetValue(smr, out var w0))
                            {
                                var driven = VertDrivenBy(smr, pushTargets);
                                for (int i = 0; i < world.Length && i < w0.Length
                                                && i < driven.Length; i++)
                                {
                                    float tv = (world[i] - w0[i]).magnitude;
                                    if (driven[i])
                                    {
                                        pushedWorld.Add(world[i]);
                                        pushedTravel.Add(tv);
                                        continue;
                                    }
                                    // Not driven by the pushed bone. Is it NEAR it, and did it
                                    // stay put? 250 mm of the joint is generous on purpose -- this
                                    // is a census of what a control could cross, not a verdict,
                                    // and both the static and the moving counts are printed so the
                                    // reader sees the split rather than a filtered half of it.
                                    float nd = float.MaxValue;
                                    foreach (var pt in pushTargets)
                                    {
                                        float dd = (pt.position - world[i]).magnitude;
                                        if (dd < nd) nd = dd;
                                    }
                                    if (nd > 0.25f) continue;
                                    if (tv < 0.25f * Math.Abs(pushArm)) staticNearPush++;
                                    else movingNearPush++;
                                }
                            }

                            var tp = smr.transform.position;
                            smrLog.Append("\n          ").Append(smr.name)
                                  .Append("  body=").Append(bodyTris - bBefore)
                                  .Append(" cloth=").Append(clothTris - cBefore)
                                  .Append(" at (").Append(F3(tp.x)).Append(", ").Append(F3(tp.y))
                                  .Append(", ").Append(F3(tp.z)).Append(")")
                                  .Append(" rot=").Append(F3(smr.transform.rotation.eulerAngles.y))
                                  .Append(" scale=").Append(F3(smr.transform.lossyScale.x));
                        }
                        surf.Finish();
                        if (f == 0) Debug.Log($"[INSIDE] {name}: renderers{smrLog}");

                        // =======================================================================
                        // THE TWO CANDIDATE SPLITS, MEASURED SIDE BY SIDE ON ONE FRAME
                        // =======================================================================
                        //
                        // The first sweep of this probe ran the WEIGHT split -- a triangle is body
                        // when all three of its vertices are dominantly weighted to a humanoid
                        // bone -- which is the split every instrument in this project has used.
                        // It produced a monotone, correctly-localised response to a displaced arm
                        // and an UNUSABLE ZERO POINT, because control A came back:
                        //
                        //      parts=231  closed=0  (0/23449 tris, 0.000% of the body)
                        //
                        // Not one closed piece in the whole body half. The cause is the split
                        // itself and not the character: a per-TRIANGLE weight test cuts the skin
                        // apart along every weight boundary, so a waistband, a collar, a glove cuff
                        // and a hairline each punch a hole in the body, and what is left is the skin
                        // SHREDDED into 231 patches with 4,209 boundary edges. A patch has no
                        // interior, so "inside or outside" has no answer on it, and the 220 mm
                        // "depth" the first sweep reported on an upper arm roughly 90 mm thick is
                        // what an unanswerable question looks like when you answer it anyway.
                        //
                        // THE COMPONENT SPLIT asks the same question of whole connected pieces:
                        // label each piece body or garment by the weight majority OVER THE PIECE,
                        // and keep it intact either way. A shell stays a shell. The weight test
                        // moves from deciding geometry to only naming it.
                        //
                        // BOTH are measured in the same run on the same frame, because the
                        // difference between them is a result in its own right -- the first sweep
                        // established the response, so what is at issue now is only the zero point
                        // and that is exactly what changing the split moves.
                        surf.Components();
                        var compVote = new Dictionary<int, int>();
                        var compTri = new Dictionary<int, int>();
                        for (int t = 0; t < surf.TriCount; t++)
                        {
                            int c = surf.Comp[t];
                            compVote.TryGetValue(c, out var cv); compVote[c] = cv + surf.HumanVote[t];
                            compTri.TryGetValue(c, out var ct); compTri[c] = ct + 1;
                        }
                        // Majority over the piece. Not a tuned number: a piece is skin or it is
                        // not, and anything that lands near half would be a piece the authoring
                        // does not separate, which this would then report as such rather than
                        // silently assigning.
                        var bodyComp = new HashSet<int>();
                        int ambiguous = 0;
                        foreach (var kv in compTri)
                        {
                            double share = compVote[kv.Key] / (3.0 * kv.Value);
                            if (share > 0.5) bodyComp.Add(kv.Key);
                            if (share > 0.2 && share < 0.8) ambiguous++;
                        }
                        Debug.Log($"[INSIDE] {name} f{f}: whole mesh parts={compTri.Count} " +
                                  $"body-labelled={bodyComp.Count} mixed-weight(0.2..0.8)={ambiguous}");
                        // WHY THE TWO SPLITS DISAGREE, measured rather than asserted.
                        // The suspicion to test: bone weights describe what MOVES a piece of
                        // geometry, not what it IS, and a fitted garment is skinned to the same
                        // humanoid bones as the skin beneath it. If that is right, a leotard or a
                        // sleeve comes back with a humanoid share near 1.0 and the component split
                        // labels it BODY -- which would merge the garment into the thing it is
                        // supposed to be tested against, and would show up as a dead response
                        // exactly in the deep bands. So: per piece, the share, the label, and how
                        // many of its triangles the WEIGHT split would have called body.
                        var byTris = new List<KeyValuePair<int, int>>(compTri);
                        byTris.Sort((x, y) => y.Value.CompareTo(x.Value));
                        for (int ci = 0; ci < byTris.Count && ci < 10; ci++)
                        {
                            int c = byTris[ci].Key, n = byTris[ci].Value;
                            double share = compVote[c] / (3.0 * n);
                            int allHuman = 0;
                            for (int t = 0; t < surf.TriCount; t++)
                                if (surf.Comp[t] == c && surf.HumanVote[t] == 3) allHuman++;
                            var mh = new Dictionary<int, int>();
                            for (int t = 0; t < surf.TriCount; t++)
                                if (surf.Comp[t] == c)
                                {
                                    mh.TryGetValue(surf.Mat[t], out var mc);
                                    mh[surf.Mat[t]] = mc + 1;
                                }
                            var mlist = new List<KeyValuePair<int, int>>(mh);
                            mlist.Sort((x, y) => y.Value.CompareTo(x.Value));
                            var msb = new StringBuilder();
                            for (int mi = 0; mi < mlist.Count && mi < 3; mi++)
                                msb.Append(mi > 0 ? " + " : "").Append(matNames[mlist[mi].Key])
                                   .Append("(").Append(mlist[mi].Value).Append(")");
                            // WHERE THE PIECE IS, because its NAME cannot say what it is.
                            //
                            // The bundle exporter renames every material to <Character>_N, and on
                            // Power Girl pieces 3, 4, 5, 6 and 7 all come back as
                            // "mesh1 / PowerGirl_3" -- one name over five separate shells. The
                            // authored names exist only in the .vrm, and mapping those back by
                            // position is the numeric-suffix trap that already cost a near-miss on
                            // Scott Hall. So identity comes from GEOMETRY, which is in the file in
                            // front of me: the piece's height range, and which humanoid bone its
                            // centroid is nearest. A boot sits at ankle height over a lower leg; a
                            // hair clump sits at head height over the head. That distinction is
                            // the whole question for choosing a control bone, and it needs no name.
                            var cen = Vector3.zero;
                            float ylo = float.MaxValue, yhi = float.MinValue;
                            int cn = 0;
                            for (int t = 0; t < surf.TriCount; t++)
                            {
                                if (surf.Comp[t] != c) continue;
                                for (int e = 0; e < 3; e++)
                                {
                                    var v = surf.V[surf.T[t * 3 + e]];
                                    cen += v; cn++;
                                    if (v.y < ylo) ylo = v.y;
                                    if (v.y > yhi) yhi = v.y;
                                }
                            }
                            if (cn > 0) cen /= cn;
                            string nearBone = "?";
                            float nearD = float.MaxValue;
                            foreach (var kv in human)
                            {
                                float dd = (kv.Key.position - cen).magnitude;
                                if (dd < nearD) { nearD = dd; nearBone = regionName[kv.Value]; }
                            }
                            Debug.Log($"[INSIDE] {name} f{f}:   piece {ci} tris={n,6} " +
                                      $"share={F3(share)} -> {(share > 0.5 ? "BODY " : "cloth")}  " +
                                      $"y={F3(ylo)}..{F3(yhi)}  nearest={nearBone}@{F3(nearD * 1000)}mm  " +
                                      $"wsplit_body={allHuman,6}  mats={msb}");
                        }

                        if (frames > 1)
                        {
                            var mv = new List<KeyValuePair<Transform, float>>(boneTravel);
                            mv.Sort((x, y) => y.Value.CompareTo(x.Value));
                            var tsb = new StringBuilder();
                            for (int bi = 0; bi < mv.Count && bi < 10; bi++)
                                tsb.Append("\n          ").Append(regionName[human[mv[bi].Key]])
                                   .Append(" ").Append(F3(mv[bi].Value * 1000)).Append("mm");
                            Debug.Log($"[INSIDE] {name} f{f}: idle bone travel over {frames} " +
                                      $"frames, largest first{tsb}");
                        }

                        if (inventory)
                        {
                            // One line per character that a reader can rank on: how much
                            // separable garment there is, and where it sits.
                            int sepPieces = 0, sepTris = 0, sepOverLimb = 0;
                            var overBones = new HashSet<string>();
                            foreach (var kv in compTri)
                            {
                                double sh = compVote[kv.Key] / (3.0 * kv.Value);
                                if (sh > 1e-9) continue;
                                sepPieces++; sepTris += kv.Value;
                                var pc = Vector3.zero; int pn = 0;
                                for (int t = 0; t < surf.TriCount; t++)
                                {
                                    if (surf.Comp[t] != kv.Key) continue;
                                    for (int e = 0; e < 3; e++) { pc += surf.V[surf.T[t * 3 + e]]; pn++; }
                                }
                                if (pn == 0) continue;
                                pc /= pn;
                                // THE DRIVING BONE, by majority over the piece's triangles. The
                                // centroid-proximity version of this line is what ranked Jinx's
                                // braids as garment over her legs; a braid is driven by hair bones
                                // however far it hangs. Reported as the author's bone NAME so a
                                // reader can see "hair" or "skirt" and is not taking my word for
                                // a category.
                                var bh = new Dictionary<int, int>();
                                for (int t = 0; t < surf.TriCount; t++)
                                {
                                    if (surf.Comp[t] != kv.Key) continue;
                                    if (surf.Bone[t] < 0) continue;
                                    bh.TryGetValue(surf.Bone[t], out var bc);
                                    bh[surf.Bone[t]] = bc + 1;
                                }
                                string nb = "?";
                                int bbest = -1;
                                foreach (var b in bh) if (b.Value > bbest) { bbest = b.Value; nb = boneNames[b.Key]; }
                                overBones.Add(nb);
                            }
                            var obs = new List<string>(overBones); obs.Sort();
                            // NO over_non_head COLUMN. The previous one counted any hair
                            // hanging below the head as garment-over-limb, for all 65 characters,
                            // and the ranking built on it was withdrawn. The driving-bone names
                            // are printed raw instead, with no category derived from them, because
                            // three derived categories in one evening were all wrong.
                            Debug.Log($"[INVENTORY] {name}: parts={compTri.Count} " +
                                      $"separable_pieces={sepPieces} separable_tris={sepTris} " +
                                      $"driving_bones=[{string.Join(" ", obs)}]");
                            perFrame.Add("{\"frame\": " + f + ", \"inventory\": true" +
                                         ", \"separable_pieces\": " + sepPieces +
                                         ", \"separable_tris\": " + sepTris +
                                         ", \"over_non_head\": " + sepOverLimb + "}");
                            continue;
                        }

                        var splitNames = new[] { "WEIGHT", "COMPONENT" };
                        for (int sp = 0; sp < 2; sp++)
                        {
                            string splitLabel = splitNames[sp];
                            Surface body;
                            List<Vector3> cloth;
                            if (sp == 0)
                            {
                                body = surf.Subset(t => surf.HumanVote[t] == 3);
                                cloth = surf.VertsOf(t => surf.HumanVote[t] != 3);
                            }
                            else
                            {
                                body = surf.Subset(t => bodyComp.Contains(surf.Comp[t]));
                                cloth = surf.VertsOf(t => !bodyComp.Contains(surf.Comp[t]));
                            }
                            clothVerts = cloth.Count;

                        // ---- CONTROL A: is the body a closed surface at all? ------------------
                        double closed; int edges, manifold;
                        body.Closedness(out closed, out edges, out manifold);
                        body.Components();

                        bool measurable = human.Count > 0 && body.TriCount > 0 && clothVerts > 0;
                        if (!measurable)
                        {
                            Debug.LogWarning($"[INSIDE] {name} frame {f} {splitLabel}: UNMEASURED " +
                                             $"(humanoid={human.Count} bodyTris={body.TriCount} " +
                                             $"clothVerts={clothVerts})");
                            perFrame.Add("{\"frame\": " + f + ", \"split\": \"" + splitLabel +
                                         "\", \"measurable\": false}");
                            continue;
                        }

                        var surfRef = body;
                        var grid = new Grid(body, gridTarget);

                        // ---- THE GUARD, asserted against THIS split's body surface -----------
                        if (Math.Abs(pushArm) > 1e-6f)
                        {
                            int onBody = 0;
                            for (int i = 0; i < pushedWorld.Count; i++)
                            {
                                float gd; Vector3 gq, gn; int gt2;
                                // 1 mm: a vertex OF the body surface sits on it to within the
                                // welding quantum, so this asks membership and not nearness.
                                if (grid.Nearest(pushedWorld[i], 0.001f, out gd, out gq, out gn, out gt2))
                                    onBody++;
                            }
                            var tcopy = new List<float>(pushedTravel);
                            double medTravel = Median(tcopy);
                            Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: GUARD pushed_verts=" +
                                      $"{pushedWorld.Count} pushed_travel={F3(medTravel * 1000)}mm " +
                                      $"(asked {F3(pushArm * 1000)}mm) pushed_on_body={onBody}");
                            Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: GUARD " +
                                      $"static_near_push={staticNearPush} " +
                                      $"moving_near_push={movingNearPush}");
                            if (staticNearPush == 0)
                                Debug.LogWarning($"[INSIDE] {name} f{f} {splitLabel}: NOTHING THIS " +
                                                 "BONE CAN CROSS -- every vertex near the pushed " +
                                                 "bone that it does not drive travels WITH it, so a " +
                                                 "flat result was guaranteed before the run and is " +
                                                 "not evidence about the instrument.");
                            bool moved = pushedWorld.Count > 0 && medTravel > 0.5 * pushArm;
                            if (!moved)
                                Debug.LogError($"[INSIDE] {name} f{f} {splitLabel}: GUARD REFUSED -- " +
                                               "the pushed bone drives no geometry, or it did not " +
                                               "move. This run measured NOTHING and its table must " +
                                               "not be read as a null.");
                            else if (onBody == 0)
                                Debug.LogError($"[INSIDE] {name} f{f} {splitLabel}: GUARD REFUSED -- " +
                                               $"{pushedWorld.Count} vertices driven by the pushed " +
                                               "bone moved correctly and NONE of them is on the body " +
                                               "surface, so the body moved PAST the cloth rather " +
                                               "than through it. Flat is expected here and is not a " +
                                               "null. This is the Jinx failure.");
                            if (!moved || onBody == 0)
                            {
                                perFrame.Add("{\"frame\": " + f + ", \"split\": \"" + splitLabel +
                                             "\", \"measurable\": false, \"guard\": \"refused\"" +
                                             ", \"pushed_verts\": " + pushedWorld.Count +
                                             ", \"pushed_on_body\": " + onBody + "}");
                                continue;
                            }
                        }

                        // ---- the measurement ------------------------------------------------
                        var dists = new List<float>(clothVerts);   // nearest distance, every vertex
                        var depths = new List<float>();            // depth of the inside ones
                        int noBody = 0, inside = 0, flatNormal = 0;
                        // THE FOURTH ASSERTION, and the one that was missing.
                        //
                        // The guard establishes that the forcing LANDED: the pushed bone drives
                        // geometry, that geometry moved the full distance, and it is part of the
                        // body surface being queried. All three hold on Jinx -- 40.000mm of
                        // 40.000mm asked, 8,164 vertices on the body surface -- and her count
                        // still does not move. So the three are NECESSARY AND NOT SUFFICIENT.
                        // (They also corrected me: I read her flat as her legs being absent from
                        // the body surface, and the guard's own numbers say they are in it.)
                        //
                        // What they do not establish is that there was ANYTHING TO CROSS.
                        // Displacing a shin through a body surface carrying no garment moves a
                        // great deal of geometry and crosses nothing. That is a true negative and
                        // it reads exactly like a blind instrument.
                        //
                        // This counts cloth vertices whose nearest body triangle is driven by the
                        // pushed bone: how much cloth sits over the thing being pushed. It needs
                        // no garment-versus-hair discrimination, which is why it is preferable to
                        // the angular measure I was about to build -- a braid hanging beside a leg
                        // is not OVER the leg here, because its nearest body triangle is whatever
                        // it actually rests against. Zero means flat was guaranteed in advance.
                        int clothOverPush = 0, insideOverPush = 0;
                        // The same count restricted to vertices whose nearest body triangle lies
                        // in a component with NO boundary edge -- the only vertices on which the
                        // sign means what the docstring says it means.
                        int insideClosed = 0, nearClosed = 0;
                        float deepestClosed = 0f;
                        // PER COMPONENT, because the strict definition of closed turned out to be
                        // the wrong exactness. Part 0 of the component split is a 23,572-triangle
                        // shell with FOUR boundary edges out of 59,341 -- closed for every
                        // practical purpose -- and a boolean "zero boundary edges" threw it out
                        // with the sheets, leaving the closed-parts line reporting on 491 of
                        // 15,030 vertices. So the counts are attributed to the piece that earned
                        // them and printed beside that piece's boundary count, and the reader
                        // draws the line instead of this file drawing it in the dark.
                        var nearByComp = new Dictionary<int, int>();
                        var insideByComp = new Dictionary<int, int>();
                        float deepest = 0f;
                        var bandCount = new int[BANDS.Length];
                        var insideByRegion = new Dictionary<int, int>();
                        var deepestByRegion = new Dictionary<int, float>();

                        for (int i = 0; i < cloth.Count; i++)
                        {
                            float d; Vector3 q, nrm; int tri;
                            if (!grid.Nearest(cloth[i], cutoff, out d, out q, out nrm, out tri))
                            {
                                // No body surface within the cutoff. Counted and reported, never
                                // folded into "outside" -- that is the difference between "this
                                // vertex is outside the body" and "there is no body here".
                                noBody++;
                                continue;
                            }
                            dists.Add(d);
                            bool overPush = pushedBoneNames.Count > 0 && surfRef.Bone[tri] >= 0
                                            && surfRef.Bone[tri] < boneNames.Count
                                            && pushedBoneNames.Contains(boneNames[surfRef.Bone[tri]]);
                            if (overPush) clothOverPush++;
                            int ncomp = surfRef.Comp[tri];
                            nearByComp.TryGetValue(ncomp, out var nbc); nearByComp[ncomp] = nbc + 1;
                            bool onClosed = surfRef.IsClosed(ncomp);
                            if (onClosed) nearClosed++;
                            if (nrm == Vector3.zero) { flatNormal++; continue; }

                            // THE WHOLE TEST, one line: which side of the body surface is this
                            // cloth vertex on?
                            //   positive  it sits on the outward side -- correct
                            //   negative  it has CROSSED to the inward side
                            // The direction is from the nearest surface point TO the vertex, so
                            // the sign is a statement about that pair and not about an origin, a
                            // camera or a bounding volume.
                            float signed = Vector3.Dot(cloth[i] - q, nrm);
                            if (signed >= 0f) continue;
                            inside++;
                            if (overPush) insideOverPush++;
                            // Depth is the true distance to the surface, not the projection of it.
                            // Where the nearest point is an edge or a vertex the projection is
                            // shorter than the distance, and reporting the shorter one would make
                            // deep penetrations at creases read as shallow.
                            float depth = d;
                            depths.Add(depth);
                            if (depth > deepest) deepest = depth;
                            insideByComp.TryGetValue(ncomp, out var ibc); insideByComp[ncomp] = ibc + 1;
                            if (onClosed)
                            {
                                insideClosed++;
                                if (depth > deepestClosed) deepestClosed = depth;
                            }
                            for (int b = 0; b < BANDS.Length; b++)
                                if (depth > BANDS[b]) bandCount[b]++;
                            int rg = surfRef.Region[tri];
                            insideByRegion.TryGetValue(rg, out var rc);
                            insideByRegion[rg] = rc + 1;
                            deepestByRegion.TryGetValue(rg, out var rd);
                            if (depth > rd) deepestByRegion[rg] = depth;
                        }

                        // ---- report ---------------------------------------------------------
                        double medDist = Median(dists);
                        double medDepth = Median(depths);
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: CONTROL A closedness={F3(closed)} " +
                                  $"({manifold}/{edges} edges shared by two triangles)");
                        // The components, largest first, each saying whether it has any boundary.
                        var comps = new List<KeyValuePair<int, int>>(surfRef.CompTris);
                        comps.Sort((x, y) => y.Value.CompareTo(x.Value));
                        int closedComps = 0, closedTris = 0;
                        foreach (var kv in comps)
                            if (surfRef.IsClosed(kv.Key)) { closedComps++; closedTris += kv.Value; }
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: CONTROL A parts={comps.Count} " +
                                  $"closed={closedComps} ({closedTris}/{surfRef.TriCount} tris, " +
                                  $"{F3(100.0 * closedTris / Math.Max(1, surfRef.TriCount))}% of the body)");
                        for (int ci = 0; ci < comps.Count && ci < 8; ci++)
                        {
                            surfRef.CompBoundary.TryGetValue(comps[ci].Key, out var bnd);
                            nearByComp.TryGetValue(comps[ci].Key, out var nb);
                            insideByComp.TryGetValue(comps[ci].Key, out var ib);
                            Debug.Log($"[INSIDE] {name} f{f} {splitLabel}:   part {ci} tris={comps[ci].Value,6} " +
                                      $"boundary_edges={bnd,5} {(bnd == 0 ? "CLOSED" : "open  ")} " +
                                      $"near={nb,6} inside={ib,6}");
                        }
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: CONTROL B median nearest={F3(medDist * 1000)}mm " +
                                  $"beyond-cutoff={noBody}/{clothVerts} zero-normal={flatNormal}");
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: bodyTris={bodyTris} clothTris={clothTris} " +
                                  $"clothVerts={clothVerts} INSIDE={inside} " +
                                  $"frac={F6(clothVerts > 0 ? (double) inside / clothVerts : 0)} " +
                                  $"medDepth={F3(medDepth * 1000)}mm deepest={F3(deepest * 1000)}mm");
                        if (pushedBoneNames.Count > 0)
                        {
                            // With the results rather than with the guard, because it decides what
                            // the verdict MEANS rather than whether there is one.
                            Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: cloth_over_push=" +
                                      $"{clothOverPush} inside_over_push={insideOverPush}");
                            if (clothOverPush == 0)
                                Debug.LogWarning($"[INSIDE] {name} f{f} {splitLabel}: NOTHING TO " +
                                                 "CROSS -- no cloth vertex sits over the bone being " +
                                                 "pushed, so a flat result was guaranteed in advance " +
                                                 "and is not evidence about the instrument. Pick a " +
                                                 "different bone or a different character.");
                        }
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: ON CLOSED PARTS ONLY  near={nearClosed} " +
                                  $"inside={insideClosed} " +
                                  $"frac={F6(nearClosed > 0 ? (double) insideClosed / nearClosed : 0)} " +
                                  $"deepest={F3(deepestClosed * 1000)}mm");
                        var bandStr = new StringBuilder();
                        for (int b = 0; b < BANDS.Length; b++)
                            bandStr.Append(b > 0 ? "  " : "").Append(">").Append(F3(BANDS[b] * 1000))
                                   .Append("mm=").Append(bandCount[b]);
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: depth bands  {bandStr}");
                        if (deepest > cutoff * 0.8f)
                            Debug.LogWarning($"[INSIDE] {name} f{f} {splitLabel}: deepest reading {F3(deepest * 1000)}mm " +
                                             $"is within 20% of the {F3(cutoff * 1000)}mm search cutoff -- " +
                                             "the cutoff is too small and these counts are a FLOOR, not a count.");

                        // regions, worst first
                        var regs = new List<KeyValuePair<int, int>>(insideByRegion);
                        regs.Sort((x, y) => y.Value.CompareTo(x.Value));
                        for (int ri = 0; ri < regs.Count && ri < 12; ri++)
                        {
                            deepestByRegion.TryGetValue(regs[ri].Key, out var rdp);
                            Debug.Log($"[INSIDE] {name} f{f} {splitLabel}:   region " +
                                      $"{RegionLabel(regionName, regs[ri].Key),-18} " +
                                      $"inside={regs[ri].Value,6} deepest={F3(rdp * 1000)}mm");
                        }

                        // ---- CONTROL E: left/right symmetry ---------------------------------
                        int pairs = 0, agreeing = 0;
                        for (int r = 0; r < regionName.Count; r++)
                        {
                            var rn = regionName[r];
                            if (!rn.StartsWith("Left")) continue;
                            int other = regionName.IndexOf("Right" + rn.Substring(4));
                            if (other < 0) continue;
                            insideByRegion.TryGetValue(r, out var lc);
                            insideByRegion.TryGetValue(other, out var rc2);
                            if (lc == 0 && rc2 == 0) continue;
                            pairs++;
                            double rel = Math.Abs(lc - rc2) / (double) Math.Max(1, Math.Max(lc, rc2));
                            if (rel <= 0.30) agreeing++;
                            else
                                Debug.Log($"[INSIDE] {name} f{f} {splitLabel}:   ASYMMETRIC {rn}={lc} " +
                                          $"vs Right{rn.Substring(4)}={rc2} (rel {F3(rel)})");
                        }
                        Debug.Log($"[INSIDE] {name} f{f} {splitLabel}: CONTROL E symmetry {agreeing}/{pairs} " +
                                  "left-right pairs agree within 30%" +
                                  (pairs == 0 ? "  -- NO PAIRS, so this control said nothing" : ""));

                        var fj = new StringBuilder();
                        fj.Append("{\"frame\": ").Append(f)
                          .Append(", \"split\": \"").Append(splitLabel).Append("\"")
                          .Append(", \"measurable\": true")
                          .Append(", \"closedness\": ").Append(F6(closed))
                          .Append(", \"body_tris\": ").Append(bodyTris)
                          .Append(", \"cloth_tris\": ").Append(clothTris)
                          .Append(", \"cloth_verts\": ").Append(clothVerts)
                          .Append(", \"inside\": ").Append(inside)
                          .Append(", \"parts\": ").Append(comps.Count)
                          .Append(", \"closed_parts\": ").Append(closedComps)
                          .Append(", \"closed_tris\": ").Append(closedTris)
                          .Append(", \"near_closed\": ").Append(nearClosed)
                          .Append(", \"inside_closed\": ").Append(insideClosed)
                          .Append(", \"deepest_closed_m\": ").Append(F6(deepestClosed))
                          .Append(", \"beyond_cutoff\": ").Append(noBody)
                          .Append(", \"zero_normal\": ").Append(flatNormal)
                          .Append(", \"median_nearest_m\": ").Append(F6(double.IsNaN(medDist) ? 0 : medDist))
                          .Append(", \"median_depth_m\": ").Append(F6(double.IsNaN(medDepth) ? 0 : medDepth))
                          .Append(", \"deepest_m\": ").Append(F6(deepest))
                          .Append(", \"sym_pairs\": ").Append(pairs)
                          .Append(", \"sym_agree\": ").Append(agreeing)
                          .Append(", \"bands\": [");
                        for (int b = 0; b < BANDS.Length; b++)
                            fj.Append(b > 0 ? ", " : "").Append(bandCount[b]);
                        fj.Append("], \"regions\": {");
                        for (int ri = 0; ri < regs.Count; ri++)
                            fj.Append(ri > 0 ? ", " : "").Append('"').Append(RegionLabel(regionName, regs[ri].Key))
                              .Append("\": ").Append(regs[ri].Value);
                        fj.Append("}}");
                        perFrame.Add(fj.ToString());
                        }   // end of the two candidate splits
                    }

                    json.Append("      \"frames\": [\n        ")
                        .Append(string.Join(",\n        ", perFrame))
                        .Append("\n      ]\n    }");
                }
                catch (Exception e)
                {
                    failures++;
                    Debug.LogError($"[INSIDE] {name}: FAILED {e.GetType().Name}: {e.Message}");
                    json.Append("      \"error\": \"").Append(e.GetType().Name).Append("\"\n    }");
                }
                finally
                {
                    if (bundle != null) bundle.Unload(true);
                    if (podiumGo != null) UnityEngine.Object.DestroyImmediate(podiumGo);
                }
            }

            json.Append("\n  ]\n}\n");
            File.WriteAllText(Path.Combine(outDir, "inside.json"), json.ToString());
            Debug.Log("[INSIDE] THE FULL PASS COMPLETED");
        }
        catch (Exception e)
        {
            Debug.LogError($"[INSIDE] run failed {e.GetType().Name}: {e}");
            failures++;
        }
        EditorApplication.Exit(failures > 0 ? 1 : 0);
    }
}
