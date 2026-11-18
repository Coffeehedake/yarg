// Measures INTERIOR faults: a character's own geometry drawn in front of another part of itself
// when it should not be -- hair over a face, a hand through a skirt. Lives in tools/ for reference
// only; copy it into a SCRATCH COPY of the Unity project, never into the real project's Assets.
//
//   Unity -batchmode -quit -projectPath <scratch> -executeMethod YargCharParts.Run
//         -yargchars "<path.yargchar>|<Name>" -shotDir <out>
//         [-frames 6] [-step 0.125] [-warmup 1.0] [-res 512] [-yaw 0]
//         [-breakAux 1] [-pushZ 0.05]     <-- the synthetic positive control; see YargNoDepth.shader
//
// Needs Hidden/YargPartDepth (YargPartDepth.shader) beside it, and Hidden/YargNoDepth for the
// control. Both are reported as MISSING rather than skipped, because a run that quietly dropped
// its best measurement would still print a full-looking table.
//
// WHY THIS EXISTS, AND WHAT IT IS NOT. `anim_sweep.py` ranks the roster on the SILHOUETTE and
// says in its own docstring that it cannot see anything interior: "the outline is identical
// whether or not the hair is in front of her eyes." The one fault ever actually reported to us on
// a character was "her hair goes over her face". So the clean sweep could not have found the only
// fault class we have evidence of. This tool is that hole.
//
// ===================================================================================
// THE MEASUREMENT, and why it is ablation rather than the obvious thing
// ===================================================================================
//
// The obvious implementation is an ID pass: re-render every part in a flat unique colour and read
// which part owns each pixel. THAT WOULD BE BLIND TO THE FAULT WE ARE HUNTING. Aiko's hair drew
// over her face because her hair material was in the transparent queue, which does not write
// depth, so hair GEOMETRICALLY BEHIND her head was composited on top of it. Swap in a flat opaque
// material and depth is written correctly, the hair is properly hidden, and the probe reports a
// clean face on a character that is visibly broken. A probe whose own render fixes the bug cannot
// see the bug.
//
// So visibility is established by ABLATION, with every material left exactly as the character
// ships it:
//
//   F        render everything.
//   F\P      render everything except part P.
//   visible(P) = pixels where F differs from F\P. That is where P is visibly contributing,
//              under the real render queues, the real blend modes and the real depth behaviour.
//   solo(P)  render P by itself -> where P OCCUPIES the screen at all.
//   covered(P) = solo(P) minus visible(P) -> P is there, and something else is being drawn over it.
//
//   occlusion(P) = |covered(P)| / |solo(P)|       A FRACTION, NEVER A COUNT. A count is not
//                                                 comparable between a 1.9 m character and a
//                                                 0.9 m one at the same resolution, and this
//                                                 roster has Groot and Yoda on it.
//
// Both halves of a violation are reported, because they are the same event seen from either side:
// the face being covered, and the hair showing where it should have been hidden.
//
// THE FACE REGION COMES FROM THE HUMANOID MAP, NOT FROM A RECTANGLE. It is the triangles whose
// vertices are dominantly weighted to Head/Jaw/LeftEye/RightEye as the Avatar reports them. A
// fixed rectangle, or "the top third of the silhouette", breaks on a character who is short,
// kneeling, or tilting their head -- and hair bones are never humanoid bones, so weighting is
// what separates hair from face rather than any guess about position.
//
// ===================================================================================
// THE CONTROLS. A zero from this tool must not look like the tool never running
// ===================================================================================
//
// This project has read a harness's own silence as a finding about the subject more than once --
// five spring probes reading zero for every character, five builds whose collider step had thrown
// a swallowed ModuleNotFoundError. So:
//
//   * -breakAux/-pushZ is a SYNTHETIC POSITIVE: it gives the hair/cloth half a no-ZWrite
//     transparent material and pushes it AWAY from the camera by a known distance, so more of it
//     sits behind the body while still drawing. The violation must rise with the distance. A probe
//     that cannot be made to report a fault on demand has no demonstrated power to report one.
//
//     IT PUSHES BACKWARD, AND THAT IS THE WHOLE POINT. The first version of this control pushed a
//     part TOWARD the camera, which is a case the depth test is built to ignore -- hair in front of
//     a face really is in front of it. That control returns a zero that looks like a broken probe,
//     so the likely next move is "fixing" a correct instrument until it reports the lookalike. It
//     would also have PASSED under the face-region measurement, which is what makes it dangerous
//     rather than merely useless. A control has to reproduce the MECHANISM, not the appearance.
//   * Every per-character line states what was FOUND, not only what was measured: parts, frames,
//     head-region pixels. "0 parts found" and "0.0000 occlusion" print differently and are
//     different verdicts.
//   * A head region smaller than MIN_REGION_PX is reported as TOO SMALL TO MEASURE rather than as
//     a fraction. At 512 px a 0.9 m character's face is a few hundred pixels and a fraction over
//     it is noise wearing a decimal point.
//   * Every number is reported at TWO diff thresholds. If the verdict moves between them the
//     threshold is doing the work, and the log says so instead of letting one cutoff decide.
//   * The frame-to-frame motion control from YargCharAnim is kept: identical frames are
//     indistinguishable from a character correctly standing still.
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

public static class YargCharParts
{
    // A pixel counts as "changed" when the summed absolute RGB difference exceeds this. Edge
    // pixels of a removed mesh blend against what is behind them, so a very low cutoff counts
    // antialiasing as geometry. Reported at both values so the cutoff cannot quietly decide.
    private const int DIFF_LO = 16;
    private const int DIFF_HI = 48;

    // Below this many pixels a region's occlusion fraction is not a measurement.
    private const int MIN_REGION_PX = 200;

    // The layer the baked probe geometry lives on, so the depth pass can cull to it and see the
    // character WITHOUT the podium, the backdrop or the song title. Chosen at runtime from the
    // unnamed layers, because hard-coding 31 would silently collide the day YARG starts using it.
    private static int ProbeLayer = 31;

    private static int PickProbeLayer()
    {
        // FROM 30 DOWN, NOT 31. `1 << 31` sets the sign bit of a C# int, so `cullingMask = 1 << 31`
        // is int.MinValue and the depth pass rendered NOTHING -- body 0 px, aux 0 px, on a
        // character plainly visible in the ordinary render a few lines earlier. The |= that adds
        // the layer to the mask works fine with bit 31; it is the assignment that does not.
        for (int i = 30; i >= 8; i--)
            if (string.IsNullOrEmpty(LayerMask.LayerToName(i))) return i;
        throw new Exception("no unnamed layer free for the depth pass; every layer 8-31 is named. " +
                            "Refusing to borrow a named one, which would render the wrong objects.");
    }

    private static string Arg(string[] a, string n)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], n, StringComparison.OrdinalIgnoreCase)) return a[i + 1];
        return null;
    }

    private sealed class Part
    {
        public string Name;
        public GameObject Go;
        public MeshRenderer Mr;
        public bool IsHeadProbe;       // the duplicate head geometry: solo renders only
        public bool IsParentMinusHead; // the head's own renderer with the head triangles removed
        public bool IsHum;             // triangles dominantly weighted to HUMANOID bones: the body
        public bool IsAux;             // everything else: hair, cloth, props -- the spring-driven half
    }

    // Decoded from Hidden/YargPartDepth: eye distance over the far plane, 24 bits. >= NO_GEOM means
    // the pass never wrote that pixel, which is the validity mask.
    private const double NO_GEOM = 0.999;

    private static double[] DecodeDepth(Color32[] px)
    {
        var d = new double[px.Length];
        for (int i = 0; i < px.Length; i++)
        {
            d[i] = (px[i].r / 255.0)
                 + (px[i].g / 255.0) / 255.0
                 + (px[i].b / 255.0) / 65025.0;
        }
        return d;
    }

    // ---------------------------------------------------------------------------------------
    // Rendering
    // ---------------------------------------------------------------------------------------

    private static Color32[] Shoot(Camera cam, int res, out byte[] png)
    {
        var rt = new RenderTexture(res, res, 24, RenderTextureFormat.ARGB32);
        var oldTarget = cam.targetTexture;
        cam.targetTexture = rt;
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        cam.targetTexture = oldTarget;
        var px = tex.GetPixels32();
        png = tex.EncodeToPNG();
        UnityEngine.Object.DestroyImmediate(tex);
        rt.Release();
        UnityEngine.Object.DestroyImmediate(rt);
        return px;
    }

    // The GEOMETRY pass, by MATERIAL OVERRIDE AND A PRIVATE LAYER -- deliberately not by
    // Camera.RenderWithShader.
    //
    // RenderWithShader(shader, "") is the obvious way to do this and it SILENTLY RENDERED PART OF
    // THE CHARACTER AND NOT THE REST. Measured on Aiko: the podium, the backdrop and her head came
    // out with valid depth while her torso and legs were never rasterised at all, so the pass
    // reported 3,666 "body" pixels on a character filling a quarter of the frame, and 0 aux pixels
    // against 2,987 aux triangles. A pass that drops geometry by some property of the original
    // material is the worst possible instrument for a question about materials -- it fails exactly
    // where the subject is interesting.
    //
    // So nothing is left to a replacement-shader rule here. The materials are swapped for the depth
    // material explicitly, the camera is culled to a layer only the baked parts live on (which also
    // removes the podium and backdrop entirely, so no furniture reference is needed), and the frame
    // goes through the SAME cam.Render() path as every other render in this tool.
    // One depth material per CULL MODE, built on demand and reused. At most three ever exist.
    private static readonly Dictionary<int, Material> DepthMats = new Dictionary<int, Material>();
    private static readonly Dictionary<int, int> CullSeen = new Dictionary<int, int>();

    // A material's own cull mode. URP keeps it in `_Cull`; MToon keeps it in `_M_CullMode`.
    // Default Back (2), which is URP Lit's own default -- NOT Off, because Off is the setting
    // that produced the bias this exists to remove.
    private static int CullOf(Material src)
    {
        if (src == null) return 2;
        if (src.HasProperty("_Cull")) return Mathf.RoundToInt(src.GetFloat("_Cull"));
        if (src.HasProperty("_M_CullMode")) return Mathf.RoundToInt(src.GetFloat("_M_CullMode"));
        return 2;
    }

    private static Material DepthMatFor(Material src, Shader depthShader)
    {
        int cull = CullOf(src);
        CullSeen[cull] = CullSeen.TryGetValue(cull, out var c) ? c + 1 : 1;
        if (!DepthMats.TryGetValue(cull, out var m))
        {
            m = new Material(depthShader);
            m.SetFloat("_Cull", cull);
            DepthMats[cull] = m;
        }
        return m;
    }

    private static double[] ShootDepthOf(Camera cam, int res, Shader depthShader,
                                         IEnumerable<Part> group, int layer)
    {
        var saved = new List<KeyValuePair<Part, Material[]>>();
        foreach (var p in group)
        {
            if (p == null) continue;
            var orig = p.Mr.sharedMaterials;
            saved.Add(new KeyValuePair<Part, Material[]>(p, orig));
            int n = Math.Max(1, orig.Length);
            var mats = new Material[n];
            // EACH SUBMESH GETS THE DEPTH MATERIAL CARRYING ITS OWN SOURCE MATERIAL'S CULL MODE,
            // so the geometry pass sees the same faces the renderer does.
            for (int i = 0; i < n; i++)
                mats[i] = DepthMatFor(i < orig.Length ? orig[i] : null, depthShader);
            p.Mr.sharedMaterials = mats;
        }

        var rt = new RenderTexture(res, res, 24, RenderTextureFormat.ARGB32);
        var oldTarget = cam.targetTexture;
        var oldFlags = cam.clearFlags;
        var oldBg = cam.backgroundColor;
        var oldMask = cam.cullingMask;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.white;   // decodes to >= NO_GEOM: "nothing was drawn here"
        cam.cullingMask = 1 << layer;
        cam.targetTexture = rt;
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(res, res, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, res, res), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        cam.targetTexture = oldTarget;
        cam.clearFlags = oldFlags;
        cam.backgroundColor = oldBg;
        cam.cullingMask = oldMask;
        var px = tex.GetPixels32();
        UnityEngine.Object.DestroyImmediate(tex);
        rt.Release();
        UnityEngine.Object.DestroyImmediate(rt);

        foreach (var kv in saved) kv.Key.Mr.sharedMaterials = kv.Value;
        return DecodeDepth(px);
    }

    // The character and nothing else, with its REAL materials: the camera is culled to the probe
    // layer, so the podium, the backdrop and the song title are absent.
    //
    // THIS EXISTS BECAUSE THE PODIUM IS NOT DETERMINISTIC. Its emissive ring renders purple in one
    // instantiation and cyan in another, which is recorded in the project README after it
    // dominated a whole-frame band analysis. My draw-order check compared two full-frame renders
    // and read that flicker as a property of the CHARACTER -- it reported ~1,890 px of difference
    // and I had already written the interpretation "this character has a transparent material
    // whose sort order changes when the mesh is split". The same character gave 0, then 1,899,
    // then 0 across three runs, and a measurement that changes when nothing changed is the
    // furniture, not the subject.
    private static Color32[] ShootLayerOnly(Camera cam, int res, int layer, out byte[] png)
    {
        var oldMask = cam.cullingMask;
        var oldFlags = cam.clearFlags;
        var oldBg = cam.backgroundColor;
        cam.cullingMask = 1 << layer;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.black;
        var px = Shoot(cam, res, out png);
        cam.cullingMask = oldMask;
        cam.clearFlags = oldFlags;
        cam.backgroundColor = oldBg;
        return px;
    }

    private static bool[] DiffMask(Color32[] a, Color32[] b, int cutoff, out int count)
    {
        var m = new bool[a.Length];
        count = 0;
        for (int i = 0; i < a.Length; i++)
        {
            int d = Math.Abs(a[i].r - b[i].r) + Math.Abs(a[i].g - b[i].g) + Math.Abs(a[i].b - b[i].b);
            if (d > cutoff) { m[i] = true; count++; }
        }
        return m;
    }

    private static int CountAnd(bool[] a, bool[] b, bool negateB)
    {
        int n = 0;
        for (int i = 0; i < a.Length; i++)
            if (a[i] && (negateB ? !b[i] : b[i])) n++;
        return n;
    }

    // ---------------------------------------------------------------------------------------
    // Mesh surgery: split a baked mesh into "head triangles" and "everything else"
    // ---------------------------------------------------------------------------------------
    //
    // Vertices are copied WHOLE and only the index buffers are filtered, so no index remapping can
    // go wrong; unreferenced vertices cost memory and nothing else. Submesh count and the material
    // array are preserved exactly, because a submesh that silently shifts by one repaints a
    // character in another character's materials. A submesh may come out empty, which is fine.
    private static Mesh FilterTriangles(Mesh src, bool[] isHeadVert, bool keepHeadSide)
    {
        var m = new Mesh();
        m.indexFormat = src.vertexCount > 65000
            ? UnityEngine.Rendering.IndexFormat.UInt32
            : UnityEngine.Rendering.IndexFormat.UInt16;
        m.vertices = src.vertices;
        var nrm = src.normals; if (nrm != null && nrm.Length == src.vertexCount) m.normals = nrm;
        var uv = src.uv; if (uv != null && uv.Length == src.vertexCount) m.uv = uv;
        var uv2 = src.uv2; if (uv2 != null && uv2.Length == src.vertexCount) m.uv2 = uv2;
        var tan = src.tangents; if (tan != null && tan.Length == src.vertexCount) m.tangents = tan;
        var col = src.colors32; if (col != null && col.Length == src.vertexCount) m.colors32 = col;

        m.subMeshCount = src.subMeshCount;
        for (int s = 0; s < src.subMeshCount; s++)
        {
            var tris = src.GetTriangles(s);
            var keep = new List<int>(tris.Length);
            for (int t = 0; t + 2 < tris.Length; t += 3)
            {
                int a = tris[t], b = tris[t + 1], c = tris[t + 2];
                // STRICTLY head: all three vertices. A triangle straddling the boundary therefore
                // lands in the "everything else" half, so the two halves together still draw every
                // triangle exactly once and F == headOnly + parentMinusHead by construction.
                bool allHead = isHeadVert[a] && isHeadVert[b] && isHeadVert[c];
                if (allHead == keepHeadSide) { keep.Add(a); keep.Add(b); keep.Add(c); }
            }
            m.SetTriangles(keep, s, false);
        }
        m.RecalculateBounds();
        return m;
    }

    // Dominant bone per vertex, via the modern weight API so a vertex with more than four
    // influences is not silently truncated. Used for two different partitions: the head region,
    // and body-versus-everything-else.
    private static bool[] HeadVertices(SkinnedMeshRenderer smr, HashSet<Transform> headBones, out int nHead)
    {
        nHead = 0;
        var mesh = smr.sharedMesh;
        var res = new bool[mesh.vertexCount];
        var bones = smr.bones;
        if (bones == null || bones.Length == 0) return res;

        var headIdx = new HashSet<int>();
        for (int i = 0; i < bones.Length; i++)
            if (bones[i] != null && headBones.Contains(bones[i])) headIdx.Add(i);
        if (headIdx.Count == 0) return res;

        var perVertex = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            int cursor = 0;
            for (int v = 0; v < mesh.vertexCount && v < perVertex.Length; v++)
            {
                int n = perVertex[v];
                float best = -1f; int bestBone = -1;
                for (int k = 0; k < n; k++)
                {
                    var bw = weights[cursor + k];
                    if (bw.weight > best) { best = bw.weight; bestBone = bw.boneIndex; }
                }
                cursor += n;
                if (bestBone >= 0 && headIdx.Contains(bestBone)) { res[v] = true; nHead++; }
            }
        }
        finally
        {
            if (perVertex.IsCreated) perVertex.Dispose();
            if (weights.IsCreated) weights.Dispose();
        }
        return res;
    }

    // WHICH BONES ACTUALLY CARRY THIS MESH. Without this, a character whose face is not weighted
    // to the humanoid Head bone is simply "not measurable", which is true but useless -- it does
    // not say whether the rig is unusual, mis-mapped, or broken. Aiko's pre-fix bundle has THREE
    // vertices dominantly weighted to Head against 1,065 in her fixed one, and a histogram is the
    // difference between reporting that and shrugging at it.
    private static void LogBoneHistogram(SkinnedMeshRenderer smr, string who)
    {
        var mesh = smr.sharedMesh;
        var bones = smr.bones;
        if (mesh == null || bones == null || bones.Length == 0) return;
        var counts = new int[bones.Length];
        var perVertex = mesh.GetBonesPerVertex();
        var weights = mesh.GetAllBoneWeights();
        try
        {
            int cursor = 0;
            for (int v = 0; v < mesh.vertexCount && v < perVertex.Length; v++)
            {
                int n = perVertex[v];
                float best = -1f; int bestBone = -1;
                for (int k = 0; k < n; k++)
                {
                    var bw = weights[cursor + k];
                    if (bw.weight > best) { best = bw.weight; bestBone = bw.boneIndex; }
                }
                cursor += n;
                if (bestBone >= 0 && bestBone < counts.Length) counts[bestBone]++;
            }
        }
        finally
        {
            if (perVertex.IsCreated) perVertex.Dispose();
            if (weights.IsCreated) weights.Dispose();
        }
        var idx = new List<int>();
        for (int i = 0; i < counts.Length; i++) idx.Add(i);
        idx.Sort((a, b) => counts[b].CompareTo(counts[a]));
        var sb = new StringBuilder();
        for (int i = 0; i < idx.Count && i < 10; i++)
        {
            if (counts[idx[i]] == 0) break;
            if (i > 0) sb.Append(", ");
            sb.Append(bones[idx[i]] != null ? bones[idx[i]].name : "<null>").Append("=").Append(counts[idx[i]]);
        }
        Debug.Log($"[PARTS] {who}: {smr.name} dominant-bone histogram ({mesh.vertexCount} verts, " +
                  $"{bones.Length} bones), top 10: {sb}");
    }

    private static Material FlatMaterial()
    {
        // Which shader exists depends on the render pipeline, so probe rather than assume, and say
        // which one answered. An unlit flat colour is wanted so the solo mask does not depend on
        // where the podium light happens to be pointing.
        // THE URP ONE FIRST. This list used to lead with "Unlit/Color", which EXISTS in a URP
        // project -- Shader.Find returns it happily -- and draws nothing or draws wrong, because
        // it is a built-in-pipeline shader. "The shader was found" and "the shader renders" are
        // different claims, and only the second one is worth anything.
        string[] candidates =
        {
            "Universal Render Pipeline/Unlit",
            "HDRP/Unlit",
            "Unlit/Color",
            "Sprites/Default",
            "Hidden/Internal-Colored",
        };
        foreach (var c in candidates)
        {
            var sh = Shader.Find(c);
            if (sh == null) continue;
            var mat = new Material(sh);
            if (mat.HasProperty("_Color")) mat.SetColor("_Color", Color.magenta);
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", Color.magenta);
            if (mat.HasProperty("_UnlitColor")) mat.SetColor("_UnlitColor", Color.magenta);
            Debug.Log($"[PARTS] flat mask shader = {c}");
            return mat;
        }
        throw new Exception("no unlit shader found for the solo-mask pass; tried " + string.Join(", ", candidates));
    }

    // ---------------------------------------------------------------------------------------

    private static readonly List<SkinnedMeshRenderer> Disabled = new List<SkinnedMeshRenderer>();

    private static List<Part> Concat(List<Part> a, List<Part> b)
    {
        var r = new List<Part>(a.Count + b.Count);
        r.AddRange(a);
        r.AddRange(b);
        return r;
    }

    private static int CountTris(Mesh m)
    {
        int t = 0;
        for (int s = 0; s < m.subMeshCount; s++) t += m.GetTriangles(s).Length / 3;
        return t;
    }

    private static List<Part> Bake(GameObject root, Transform[] headBoneList,
                                   HashSet<Transform> humanoidBones, Material flat,
                                   out int headRegionTris, out string headNote,
                                   out int bodyTris, out int auxTris,
                                   bool diagnose = false, string who = "")
    {
        bodyTris = 0;
        auxTris = 0;
        var parts = new List<Part>();
        Disabled.Clear();
        headRegionTris = 0;
        headNote = "no head geometry found";

        var headBones = new HashSet<Transform>();
        foreach (var t in headBoneList) if (t != null) headBones.Add(t);

        // Pick the ONE renderer that carries the most head-weighted vertices. A character whose
        // face and body are one mesh is the normal case, not the exception, so per-renderer
        // granularity alone would never isolate a face.
        SkinnedMeshRenderer headSmr = null;
        bool[] headVerts = null;
        int bestHeadVerts = 0;
        var smrs = root.GetComponentsInChildren<SkinnedMeshRenderer>();
        foreach (var smr in smrs)
        {
            if (!smr.enabled || smr.sharedMesh == null) continue;
            if (diagnose) LogBoneHistogram(smr, who);
            if (headBones.Count == 0) continue;
            var hv = HeadVertices(smr, headBones, out int nh);
            if (nh > bestHeadVerts) { bestHeadVerts = nh; headSmr = smr; headVerts = hv; }
        }
        if (diagnose && headBones.Count == 0)
            Debug.LogWarning($"[PARTS] {who}: no humanoid Head/Jaw/eye bones from the Avatar at all. " +
                             "There is no face region to measure and no zero here is about the character.");

        foreach (var smr in smrs)
        {
            if (!smr.enabled || smr.sharedMesh == null) continue;
            var baked = new Mesh();
            smr.BakeMesh(baked, true);

            bool isHeadCarrier = ReferenceEquals(smr, headSmr) && headVerts != null && bestHeadVerts > 0;

            if (isHeadCarrier)
            {
                // Three objects from one renderer: the whole thing (for F), the thing minus the
                // head triangles (for F-without-head), and the head triangles on their own in a
                // flat colour (for the head's solo footprint).
                var whole = MakeGo("__p_" + smr.name, baked, smr, smr.sharedMaterials);
                parts.Add(new Part { Name = smr.name, Go = whole, Mr = whole.GetComponent<MeshRenderer>() });

                var minus = FilterTriangles(baked, headVerts, false);
                var minusGo = MakeGo("__pminus_" + smr.name, minus, smr, smr.sharedMaterials);
                parts.Add(new Part
                {
                    Name = smr.name + "#minusHead", Go = minusGo,
                    Mr = minusGo.GetComponent<MeshRenderer>(), IsParentMinusHead = true,
                });

                var headOnly = FilterTriangles(baked, headVerts, true);
                int tris = 0;
                for (int s = 0; s < headOnly.subMeshCount; s++) tris += headOnly.GetTriangles(s).Length / 3;
                headRegionTris = tris;
                var flats = new Material[headOnly.subMeshCount];
                for (int i = 0; i < flats.Length; i++) flats[i] = flat;
                var headGo = MakeGo("__phead_" + smr.name, headOnly, smr, flats);
                parts.Add(new Part
                {
                    Name = "HEAD", Go = headGo, Mr = headGo.GetComponent<MeshRenderer>(),
                    IsHeadProbe = true,
                });
                headNote = $"head region from {smr.name}: {bestHeadVerts} verts, {tris} tris, " +
                           $"bones {string.Join("/", DescribeBones(headBoneList))}";
            }
            else
            {
                var go = MakeGo("__p_" + smr.name, baked, smr, smr.sharedMaterials);
                parts.Add(new Part { Name = smr.name, Go = go, Mr = go.GetComponent<MeshRenderer>() });
            }

            // THE PARTITION THE DEPTH TEST USES, and it is the Avatar that draws the line rather
            // than any bone name. Triangles dominantly weighted to a HUMANOID bone are the body;
            // everything else is hair, cloth and props -- the spring-driven half. That split works
            // on a rig whose face is weighted to Neck instead of Head, which is what Aiko's is,
            // and it needs no name matching: a name matcher on this project once "found" bones an
            // earlier run of itself had invented.
            if (humanoidBones.Count > 0)
            {
                var humVerts = HeadVertices(smr, humanoidBones, out _);
                var humMesh = FilterTriangles(baked, humVerts, true);
                var auxMesh = FilterTriangles(baked, humVerts, false);
                int ht = CountTris(humMesh), at = CountTris(auxMesh);
                bodyTris += ht;
                auxTris += at;
                if (ht > 0)
                {
                    var g = MakeGo("__hum_" + smr.name, humMesh, smr, smr.sharedMaterials);
                    parts.Add(new Part
                    {
                        Name = smr.name + "#body", Go = g,
                        Mr = g.GetComponent<MeshRenderer>(), IsHum = true,
                    });
                }
                if (at > 0)
                {
                    var g = MakeGo("__aux_" + smr.name, auxMesh, smr, smr.sharedMaterials);
                    parts.Add(new Part
                    {
                        Name = smr.name + "#aux", Go = g,
                        Mr = g.GetComponent<MeshRenderer>(), IsAux = true,
                    });
                }
            }

            smr.enabled = false;
            Disabled.Add(smr);
        }
        return parts;
    }

    private static IEnumerable<string> DescribeBones(Transform[] bones)
    {
        foreach (var b in bones) if (b != null) yield return b.name;
    }

    private static GameObject MakeGo(string name, Mesh m, SkinnedMeshRenderer src, Material[] mats)
    {
        var go = new GameObject(name);
        go.transform.SetPositionAndRotation(src.transform.position, src.transform.rotation);
        // The probe layer, not the source renderer's -- the depth pass culls to it. The camera's
        // mask has this layer ADDED for the whole run, so the ordinary renders are unaffected.
        go.layer = ProbeLayer;
        go.AddComponent<MeshFilter>().sharedMesh = m;
        var mr = go.AddComponent<MeshRenderer>();
        mr.sharedMaterials = mats;
        // SHADOWS OFF, both ways. Ablation asks "did removing this change the picture"; a mesh that
        // casts a shadow onto another part changes the picture without being visible there, which
        // would be counted as the part showing through. Turning shadows off makes the difference
        // mean visibility and nothing else. It also means these renders are not the game's look.
        mr.shadowCastingMode = ShadowCastingMode.Off;
        mr.receiveShadows = false;
        return go;
    }

    // A number nobody can look at is how this project once shipped a flawless mechanism for a
    // fault that did not exist. Every non-zero verdict gets a picture with the offending pixels
    // painted, so checking it by eye costs one click.
    private static void Paint(string outDir, string file, byte[] png, bool[] mask, Color32 colour)
    {
        try
        {
            var tex = new Texture2D(2, 2);
            tex.LoadImage(png);
            var px = tex.GetPixels32();
            for (int i = 0; i < px.Length && i < mask.Length; i++)
                if (mask[i]) px[i] = colour;
            tex.SetPixels32(px);
            tex.Apply();
            File.WriteAllBytes(Path.Combine(outDir, file), tex.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(tex);
        }
        catch (Exception e) { Debug.LogError("[PARTS] could not paint " + file + ": " + e.Message); }
    }

    // A depth map, contrast-stretched over the range that actually contains geometry, so it can be
    // LOOKED AT. Encoded depth is near-black everywhere when the far plane is 1000 m and the
    // subject is 5 m away, which is indistinguishable from an empty render by eye.
    private static byte[] DepthPng(double[] d, int res)
    {
        double lo = 9, hi = -9;
        foreach (var v in d) if (v < NO_GEOM) { if (v < lo) lo = v; if (v > hi) hi = v; }
        var span = hi - lo;
        var tex = new Texture2D(res, res, TextureFormat.RGB24, false);
        var px = new Color32[d.Length];
        for (int i = 0; i < d.Length; i++)
        {
            if (d[i] >= NO_GEOM) { px[i] = new Color32(0, 0, 60, 255); continue; }   // no geometry
            byte g = (byte) (span > 1e-9 ? 255.0 * (1.0 - (d[i] - lo) / span) : 255);
            px[i] = new Color32(g, g, g, 255);
        }
        tex.SetPixels32(px);
        tex.Apply();
        var png = tex.EncodeToPNG();
        UnityEngine.Object.DestroyImmediate(tex);
        return png;
    }

    private static string J(string s)
    {
        return "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }

    private static string F4(double d)
    {
        return d.ToString("0.000000", CultureInfo.InvariantCulture);
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
            outDir = Arg(args, "-shotDir");
            Directory.CreateDirectory(outDir);
            int res = int.TryParse(Arg(args, "-res"), out var rr) ? rr : 512;
            int frames = int.TryParse(Arg(args, "-frames"), out var ff) ? ff : 6;
            float step = float.TryParse(Arg(args, "-step"), out var ss) ? ss : 0.125f;
            float warmup = float.TryParse(Arg(args, "-warmup"), out var ww) ? ww : 1.0f;
            float yaw = float.TryParse(Arg(args, "-yaw"), out var yy) ? yy : 0f;
            float pushZ = float.TryParse(Arg(args, "-pushZ"), out var pz) ? pz : 0f;
            // -breakAux turns the synthetic control on: the aux half gets a no-ZWrite transparent
            // material and is pushed |pushZ| metres AWAY from the camera. See YargNoDepth.shader
            // for why the control has to break the depth write rather than move geometry forward.
            bool breakAux = (Arg(args, "-breakAux") ?? "0") != "0";

            Debug.Log($"[PARTS] frames={frames} step={step}s warmup={warmup}s res={res} yaw={yaw} " +
                      $"diffLo={DIFF_LO} diffHi={DIFF_HI} minRegion={MIN_REGION_PX} " +
                      $"breakAux={breakAux} pushZ={pushZ}m");

            int high = Array.IndexOf(QualitySettings.names, "High");
            if (high >= 0) QualitySettings.SetQualityLevel(high, true);
            // Crisp masks. MSAA blends a removed mesh's edge into what is behind it, which turns
            // every silhouette edge into a thin band of "changed" pixels.
            QualitySettings.antiAliasing = 0;

            EditorSceneManager.OpenScene("Assets/Scenes/CharacterSelect.unity", OpenSceneMode.Single);
            var dm = UnityEngine.Object.FindFirstObjectByType<CharacterDisplayManager>();
            var so = new SerializedObject(dm);
            var podiumPrefab = so.FindProperty("_displayPrefab").objectReferenceValue as GameObject;
            var selected = so.FindProperty("_selectedLocation").objectReferenceValue as Transform;
            var cam = Camera.main;
            var flat = FlatMaterial();

            // The geometry pass. Its ABSENCE is reported rather than silently skipped: without it
            // there is no depth-order test, and a run that quietly dropped its best measurement
            // would still print a full-looking table.
            // WHICH PIPELINE, stated up front. Every shader decision in this tool depends on it,
            // and getting it wrong does not raise an error -- it renders nothing, or renders
            // something that can be decoded into a convincing fiction.
            var rp = UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline;
            Debug.Log($"[PARTS] render pipeline = {(rp == null ? "BUILT-IN (no RP asset)" : rp.GetType().Name)}");

            ProbeLayer = PickProbeLayer();
            cam.cullingMask |= (1 << ProbeLayer);
            Debug.Log($"[PARTS] probe layer = {ProbeLayer}, added to the camera mask");

            var depthShader = Shader.Find("Hidden/YargPartDepth");
            DepthMats.Clear();   // materials are built per cull mode, on demand
            if (depthShader == null)
                Debug.LogError("[PARTS] Hidden/YargPartDepth NOT FOUND. The depth-order test cannot " +
                               "run, so fringe and fault cannot be told apart in this run. Copy " +
                               "YargPartDepth.shader into Assets/__Shot/ of the scratch project.");
            else
                Debug.Log("[PARTS] depth shader found: Hidden/YargPartDepth");

            Material noDepth = null;
            if (breakAux)
            {
                var ndS = Shader.Find("Hidden/YargNoDepth");
                if (ndS == null)
                    throw new Exception("-breakAux was asked for but Hidden/YargNoDepth is missing, so " +
                                        "the synthetic control cannot be constructed. Refusing to run a " +
                                        "control that would silently measure nothing.");
                noDepth = new Material(ndS);
                Debug.Log("[PARTS] SYNTHETIC CONTROL ACTIVE: aux half forced to a no-ZWrite transparent " +
                          $"material and pushed {Math.Abs(pushZ)} m AWAY from the camera. These numbers " +
                          "are about the probe, not about the character.");
            }

            json.Append("{\n  \"res\": ").Append(res)
                .Append(",\n  \"frames\": ").Append(frames)
                .Append(",\n  \"diff_lo\": ").Append(DIFF_LO)
                .Append(",\n  \"diff_hi\": ").Append(DIFF_HI)
                .Append(",\n  \"min_region_px\": ").Append(MIN_REGION_PX)
                // What was ACTUALLY pushed, not a flag that was merely passed. -pushPart used to
                // exist and selected a part by name; after the redesign it did nothing, and a flag
                // that silently does nothing is worse than no flag, so it is gone.
                .Append(",\n  \"push_part\": ").Append(J(breakAux ? "aux (no-ZWrite, pushed away)" : null))
                .Append(",\n  \"push_z\": ").Append(F4(pushZ))
                .Append(",\n  \"break_aux\": ").Append(breakAux ? "true" : "false")
                .Append(",\n  \"characters\": [\n");
            bool firstChar = true;

            foreach (var entry in list.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(entry)) continue;
                var bits = entry.Split('|');
                var file = bits[0].Trim();
                var name = bits.Length > 1 ? bits[1].Trim() : Path.GetFileNameWithoutExtension(file);
                var safe = name.Replace(" ", "");
                GameObject podiumGo = null;
                AssetBundle bundle = null;
                if (!firstChar) json.Append(",\n");
                firstChar = false;
                json.Append("    {\n      \"name\": ").Append(J(name)).Append(",\n");

                try
                {
                    podiumGo = (GameObject) PrefabUtility.InstantiatePrefab(podiumPrefab, selected);
                    podiumGo.transform.localPosition = Vector3.zero;
                    podiumGo.SetActive(true);
                    var podium = podiumGo.GetComponent<Podium>();
                    if (podium.Light != null) podium.Light.color = Color.white;

                    bundle = AssetBundle.LoadFromFile(file);
                    if (bundle == null) throw new Exception("could not load " + file);
                    var prefab = bundle.LoadAsset<GameObject>(BackgroundHelper.CHARACTER_PREFAB_PATH.ToLowerInvariant());
                    if (prefab == null) throw new Exception("no character prefab in bundle");

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
                        Debug.Log($"[PARTS] {name}: VRMCharacter init skipped: {e.GetType().Name}: {e.Message}");
                    }

                    var anim = ch.GetComponent<Animator>();
                    Transform[] headBones = Array.Empty<Transform>();
                    var humanoidBones = new HashSet<Transform>();
                    if (anim == null)
                    {
                        Debug.LogWarning($"[PARTS] {name}: NO ANIMATOR -- frames identical by construction, " +
                                         "and no humanoid map, so there is no head region to measure. " +
                                         "This is a statement about the character, not a control failure.");
                    }
                    else
                    {
                        if (anim.HasParameter("Attract")) anim.SetTrigger("Attract");
                        else if (anim.HasParameter("Idle")) anim.SetTrigger("Idle");
                        anim.Rebind();
                        anim.Update(warmup);
                        headBones = new[]
                        {
                            anim.GetBoneTransform(HumanBodyBones.Head),
                            anim.GetBoneTransform(HumanBodyBones.Jaw),
                            anim.GetBoneTransform(HumanBodyBones.LeftEye),
                            anim.GetBoneTransform(HumanBodyBones.RightEye),
                        };
                        // EVERY humanoid bone the Avatar maps. This is the line between "body" and
                        // "hair, cloth and props" for the depth test, and it is drawn by the rig's
                        // own humanoid description rather than by matching bone names.
                        if (anim.isHuman)
                        {
                            foreach (HumanBodyBones hb in Enum.GetValues(typeof(HumanBodyBones)))
                            {
                                if (hb == HumanBodyBones.LastBone) continue;
                                var t = anim.GetBoneTransform(hb);
                                if (t != null) humanoidBones.Add(t);
                            }
                        }
                        else
                        {
                            Debug.LogWarning($"[PARTS] {name}: Animator is NOT humanoid, so there is no " +
                                             "humanoid map to split body from hair. The depth-order test " +
                                             "cannot run on this character and will be reported as " +
                                             "unmeasured rather than clean.");
                        }
                    }

                    var perFrame = new List<string>();
                    Color32[] prevFull = null;
                    var moved = new List<int>();
                    int partsFound = 0, headPx0 = 0, headTris = 0, bodyTris = 0, auxTris = 0;
                    string headNote = "";
                    double worstHeadOcc = -1; int worstFrame = -1;
                    byte[] worstPng = null; bool[] worstCovered = null;
                    double worstDepth = -1; int worstDepthFrame = -1;
                    byte[] worstDepthPng = null; bool[] worstViolation = null;
                    int splitDiff = -1;   // -1 == the split check never ran

                    for (int f = 0; f < frames; f++)
                    {
                        if (f > 0 && anim != null) anim.Update(step);
                        var parts = Bake(ch, headBones, humanoidBones, flat, out headTris, out headNote,
                                         out bodyTris, out auxTris, f == 0, name);

                        // `real` is the character exactly as it ships: the WHOLE renderers only.
                        // The head probe, the minus-head copy and the body/aux split are all
                        // duplicates of geometry already in those renderers, so letting any of
                        // them into the full render would draw the same triangles twice at the
                        // same depth and z-fight.
                        var real = new List<Part>();
                        var hums = new List<Part>();
                        var auxes = new List<Part>();
                        Part headProbe = null, minusHead = null;
                        foreach (var p in parts)
                        {
                            if (p.IsHeadProbe) headProbe = p;
                            else if (p.IsParentMinusHead) minusHead = p;
                            else if (p.IsHum) hums.Add(p);
                            else if (p.IsAux) auxes.Add(p);
                            else real.Add(p);
                        }
                        partsFound = real.Count;

                        void Only(IEnumerable<Part> on)
                        {
                            foreach (var p in parts) p.Mr.enabled = false;
                            foreach (var p in on) if (p != null) p.Mr.enabled = true;
                        }

                        // ================= THE SPLIT IS CHECKED BEFORE IT IS TRUSTED =============
                        // Every measurement below rests on hum + aux adding back up to the whole
                        // character. If FilterTriangles drops a triangle or emits one twice, every
                        // number is quietly wrong and nothing else here would notice. So render the
                        // character both ways on frame 0 and compare: the two must agree to the
                        // pixel. A comparison script on this project once reported two textures
                        // missing from a file that contained both, so the check gets a number
                        // rather than a verdict.
                        Only(real);
                        var full = Shoot(cam, res, out var fullPng);
                        if (hums.Count + auxes.Count > 0)
                        {
                            if (f == 0)
                            {
                                // Character-only on both sides, so the podium's non-deterministic
                                // emissive ring cannot be counted as a difference between them.
                                Only(real);
                                var wholeOnly = ShootLayerOnly(cam, res, ProbeLayer, out _);
                                Only(Concat(hums, auxes));
                                var splitOnly = ShootLayerOnly(cam, res, ProbeLayer, out _);
                                DiffMask(wholeOnly, splitOnly, DIFF_LO, out splitDiff);

                                // TWO BLANK RENDERS AGREE PERFECTLY. Without this, "conservation
                                // OK" is exactly what a layer-cull that renders nothing produces,
                                // and the check would certify the partition by failing to draw it.
                                int litPx = 0;
                                foreach (var c in wholeOnly) if (c.r > 8 || c.g > 8 || c.b > 8) litPx++;
                                if (litPx == 0)
                                {
                                    Debug.LogError($"[PARTS] {name}: LAYER-ONLY RENDER IS BLANK -- the probe " +
                                        $"layer ({ProbeLayer}) shows nothing, so the conservation check " +
                                        "compared two empty frames and its agreement means nothing.");
                                    failures++;
                                }
                                else Debug.Log($"[PARTS] {name}: layer-only render has {litPx} lit px");

                                if (splitDiff > 0)
                                    Debug.LogWarning($"[PARTS] {name}: CONSERVATION CHECK -- whole-renderer " +
                                        $"and body+aux renders of the CHARACTER ALONE differ by {splitDiff} " +
                                        "px. Either the triangle filter is losing or duplicating geometry, " +
                                        "or this character has a transparent material whose sort order " +
                                        "changes when the mesh is split into two objects. Both are real; " +
                                        "this check cannot tell them apart, so treat the depth numbers as " +
                                        "provisional and look at the character.");
                                else
                                    Debug.Log($"[PARTS] {name}: conservation OK -- whole == body+aux to the " +
                                              "pixel, character alone");
                            }
                            // F STAYS THE WHOLE-RENDERER RENDER, and every ablation below compares
                            // one object against one object, so per-object transparency sorting is
                            // identical on both sides of each difference.
                            //
                            // WHAT THIS CHECK FIRST TOLD ME WAS THE PODIUM. It compared two FULL
                            // FRAMES, and the podium's emissive ring is NOT DETERMINISTIC -- it
                            // renders purple in one instantiation and cyan in another, which is
                            // recorded in the project README after it dominated someone else's
                            // whole-frame analysis. So it reported ~1,890 px of difference, and I had
                            // already written the conclusion: "this character has a transparent
                            // material whose sort order changes when the mesh is split". The tell was
                            // that the SAME character read 0, then 1,899, then 0 across three runs.
                            // A measurement that changes when nothing changed is the furniture.
                            // It now renders the character alone, on the probe layer.
                            Only(real);
                        }

                        // THE SYNTHETIC POSITIVE CONTROL, and it has to break the DEPTH WRITE
                        // rather than move geometry forward. Hair pushed toward the camera is
                        // legitimately in front and the depth test correctly ignores it; validating
                        // against that would be validating against a case the probe is meant to
                        // pass over. So: give the aux half a no-ZWrite transparent material -- which
                        // is what alphaMode BLEND does -- and push it BACKWARD. Each step puts more
                        // of it behind the body while it still draws, and the violation must grow.
                        if (breakAux && auxes.Count > 0)
                        {
                            foreach (var p in auxes)
                            {
                                var mats = new Material[p.Mr.sharedMaterials.Length == 0
                                    ? 1 : p.Mr.sharedMaterials.Length];
                                for (int i = 0; i < mats.Length; i++) mats[i] = noDepth;
                                p.Mr.sharedMaterials = mats;
                                if (Math.Abs(pushZ) > 1e-6f)
                                    p.Go.transform.position += cam.transform.forward * Math.Abs(pushZ);
                            }
                            // F must now be taken from the split, or it would not contain the
                            // broken, moved hair at all and visibility would contradict depth.
                            Only(Concat(hums, auxes));
                            full = Shoot(cam, res, out fullPng);
                        }

                        if (f == 0 || f == frames - 1)
                            File.WriteAllBytes(Path.Combine(outDir, $"{safe}_f{f:000}_full.png"), fullPng);
                        if (prevFull != null) { DiffMask(prevFull, full, 24, out int mv); moved.Add(mv); }
                        prevFull = full;

                        // THE EMPTY FRAME -- podium, background and song title with no character at
                        // all. Every mask below is a difference against THIS, never a brightness
                        // cutoff.
                        //
                        // The first version of this tool took the head's solo mask with a
                        // brightness test, and the podium is brightly lit, so it reported a head
                        // region of 13,572 px on a character whose head region contained ZERO
                        // triangles. It then passed its own "did we look at a face" gate on the
                        // strength of that number. anim_sheet.py had already recorded the same
                        // mistake one layer out -- "largest connected component" returning a
                        // character WELDED TO THE FURNITURE -- and this is that mistake again,
                        // committed by the tool written to catch what that one could not see.
                        Only(Array.Empty<Part>());
                        var emptyPx = Shoot(cam, res, out _);

                        var fparts = new List<string>();

                        // ---- the head region -------------------------------------------------
                        double headOccLo = -1, headOccHi = -1;
                        int headSolo = 0, headCovLo = 0, headCovHi = 0;
                        var attribution = new Dictionary<string, int>();
                        if (headProbe != null && minusHead != null)
                        {
                            Only(new[] { headProbe });
                            var soloPx = Shoot(cam, res, out _);
                            var soloMask = DiffMask(emptyPx, soloPx, DIFF_LO, out headSolo);
                            if (f == 0) headPx0 = headSolo;

                            // Everything, but with the head triangles taken out of their own
                            // renderer: swap the whole head-carrier for the minus-head copy. What
                            // changes between this and F is where the head was visibly showing.
                            var noHead = new List<Part>();
                            foreach (var p in real)
                            {
                                if (p.Name + "#minusHead" == minusHead.Name) continue;
                                noHead.Add(p);
                            }
                            noHead.Add(minusHead);
                            Only(noHead);
                            var noHeadPx = Shoot(cam, res, out _);

                            var visLo = DiffMask(full, noHeadPx, DIFF_LO, out _);
                            var visHi = DiffMask(full, noHeadPx, DIFF_HI, out _);
                            headCovLo = CountAnd(soloMask, visLo, true);
                            headCovHi = CountAnd(soloMask, visHi, true);
                            if (headSolo >= MIN_REGION_PX)
                            {
                                headOccLo = (double) headCovLo / headSolo;
                                headOccHi = (double) headCovHi / headSolo;
                            }

                            // WHO is in front. For each other part, remove it and see whether the
                            // covered pixels come back; that names the occluder instead of leaving
                            // "something covers her face" as the whole finding.
                            var covered = new bool[soloMask.Length];
                            for (int i = 0; i < covered.Length; i++) covered[i] = soloMask[i] && !visLo[i];
                            if (headCovLo > 0)
                            {
                                // THE SINGLE-RENDERER CASE, which is the normal one. Aiko's hair,
                                // face and body are ONE SkinnedMeshRenderer, so no per-part ablation
                                // can name her hair as the occluder -- there is no hair part to
                                // remove. What CAN be named is her own non-head geometry, which is
                                // exactly the Aiko complaint: her own non-face triangles drawn over
                                // her face.
                                Only(new[] { minusHead });
                                var nhPx = Shoot(cam, res, out _);
                                var nhMask = DiffMask(emptyPx, nhPx, DIFF_LO, out _);
                                int nh = CountAnd(covered, nhMask, false);
                                if (nh > 0) attribution[minusHead.Name] = nh;

                                foreach (var q in real)
                                {
                                    if (q.Name + "#minusHead" == minusHead.Name) continue; // the carrier itself
                                    var without = new List<Part>();
                                    foreach (var p in real) if (!ReferenceEquals(p, q)) without.Add(p);
                                    Only(without);
                                    var qpx = Shoot(cam, res, out _);
                                    var qvis = DiffMask(full, qpx, DIFF_LO, out _);
                                    int n = CountAnd(covered, qvis, false);
                                    if (n > 0) attribution[q.Name] = n;
                                }
                            }

                            if (headOccLo > worstHeadOcc)
                            {
                                worstHeadOcc = headOccLo; worstFrame = f;
                                worstPng = fullPng; worstCovered = covered;
                            }
                        }

                        // ---- THE DEPTH-ORDER TEST, which is the one that can tell a fringe from
                        // ---- a fault ----------------------------------------------------------
                        //
                        // A face-region occlusion fraction cannot distinguish hair correctly drawn
                        // in front of a forehead from hair wrongly drawn over an eye: both are
                        // "something of hers is in front of her face". This can, because the fault
                        // has a signature a fringe does not -- the geometry is drawn in FRONT of a
                        // surface it is actually BEHIND.
                        //
                        //   depth from the geometry pass (no material can change it)
                        //   visibility from ablation with the real materials
                        //   violation = aux is VISIBLE where the body is NEARER
                        //
                        // A fringe is nearer than the face, so it never enters the numerator.
                        int depthDenom = 0, auxOverBody = 0, bodyOverAux = 0, humValid = 0, auxValid = 0;
                        double auxOverFrac = -1, bodyOverFrac = -1;
                        bool[] violation = null;
                        if (depthShader != null && hums.Count > 0 && auxes.Count > 0)
                        {
                            double eps = 0.003 / Math.Max(cam.farClipPlane, 0.001f); // 3 mm

                            // Only(...) first: ShootDepthOf swaps materials for the group it is
                            // given, but anything else still enabled on the probe layer would
                            // render with its own material and pollute the depth map.
                            if (f == 0) CullSeen.Clear();
                            Only(hums);
                            var dHum = ShootDepthOf(cam, res, depthShader, hums, ProbeLayer);
                            Only(auxes);
                            var dAux = ShootDepthOf(cam, res, depthShader, auxes, ProbeLayer);

                            // Visibility of each half, with the real materials, by removing it.
                            Only(hums);                  // == everything except the aux half
                            var pxNoAux = Shoot(cam, res, out _);
                            var visAux = DiffMask(full, pxNoAux, DIFF_LO, out _);
                            Only(auxes);                 // == everything except the body half
                            var pxNoHum = Shoot(cam, res, out _);
                            var visHum = DiffMask(full, pxNoHum, DIFF_LO, out _);

                            violation = new bool[dHum.Length];
                            for (int i = 0; i < dHum.Length; i++)
                            {
                                // The depth pass is culled to the probe layer, so the podium and the
                                // backdrop are not in these maps at all and nothing has to be
                                // subtracted back out. Anything nearer than the far clear is this
                                // character.
                                bool vh = dHum[i] < NO_GEOM;
                                bool va = dAux[i] < NO_GEOM;
                                if (vh) humValid++;
                                if (va) auxValid++;
                                if (!vh || !va) continue;
                                depthDenom++;                       // an ordering decision exists here
                                if (dHum[i] < dAux[i] - eps && visAux[i]) { auxOverBody++; violation[i] = true; }
                                else if (dAux[i] < dHum[i] - eps && visHum[i]) bodyOverAux++;
                            }
                            if (depthDenom > 0)
                            {
                                auxOverFrac = (double) auxOverBody / depthDenom;
                                bodyOverFrac = (double) bodyOverAux / depthDenom;
                            }
                            if (f == 0)
                            {
                                // WHY THE DEPTH PASS SAW WHAT IT SAW, in numbers, because the first
                                // run of it reported "body 3345 px, aux 0 px, overlap 0 px" and a
                                // single count cannot say whether that is the shader, the validity
                                // test, or the character.
                                int gH = 0, gA = 0;
                                double minH = 9, maxH = -9;
                                for (int i = 0; i < dHum.Length; i++)
                                {
                                    if (dHum[i] < NO_GEOM) { gH++; if (dHum[i] < minH) minH = dHum[i]; if (dHum[i] > maxH) maxH = dHum[i]; }
                                    if (dAux[i] < NO_GEOM) gA++;
                                }
                                // WHICH CULL MODES WERE ACTUALLY FOUND. If every material reports
                                // the same one, the per-material change is a NO-OP on this
                                // character and any movement in its numbers came from somewhere
                                // else -- which is a thing to know before crediting the change.
                                var cullBits = new List<string>();
                                foreach (var kv in CullSeen)
                                    cullBits.Add((kv.Key == 0 ? "Off" : kv.Key == 1 ? "Front" : "Back")
                                                 + "=" + kv.Value);
                                Debug.Log($"[PARTS] {name}: cull modes in use: " +
                                          (cullBits.Count > 0 ? string.Join(", ", cullBits) : "none") +
                                          (CullSeen.Count <= 1 ? "  (SINGLE MODE -- per-material cull is a no-op here)" : ""));
                                Debug.Log($"[PARTS] {name}: depth diag -- pixels with geometry: " +
                                          $"body {gH}, aux {gA}; body depth range " +
                                          $"{minH:0.000000}..{maxH:0.000000}; far {cam.farClipPlane}");
                                Paint(outDir, $"{safe}_depth_body.png", DepthPng(dHum, res), new bool[0], default);
                                Paint(outDir, $"{safe}_depth_aux.png", DepthPng(dAux, res), new bool[0], default);

                                // THE HARNESS CONTROL FOR THIS PASS. RenderWithShader is a no-op
                                // outside the built-in render pipeline, and a silent no-op here
                                // would make every character read as having no depth violation --
                                // five probes on this project once read zero for every character
                                // for exactly this kind of reason.
                                if (humValid == 0 && auxValid == 0)
                                {
                                    Debug.LogError($"[PARTS] {name}: DEPTH PASS PRODUCED NO GEOMETRY. " +
                                        "Hidden/YargPartDepth wrote nothing for either half, so every " +
                                        "depth-order number below is about this pass and not about the " +
                                        "character. First thing to check is the render pipeline logged at " +
                                        "startup: a built-in-pipeline shader assigned as a material under " +
                                        "URP draws nothing at all, and says nothing about it.");
                                    failures++;
                                }
                                else
                                {
                                    Debug.Log($"[PARTS] {name}: depth pass OK -- body {humValid} px, " +
                                              $"aux {auxValid} px, overlap {depthDenom} px, eps {eps:0.######}");
                                }
                            }
                            if (auxOverFrac > worstDepth)
                            {
                                worstDepth = auxOverFrac; worstDepthFrame = f;
                                worstDepthPng = fullPng; worstViolation = violation;
                            }
                        }

                        // ---- every other part, both halves of the violation -------------------
                        foreach (var p in real)
                        {
                            Only(new[] { p });
                            var soloPx = Shoot(cam, res, out _);
                            var soloMask = DiffMask(emptyPx, soloPx, DIFF_LO, out int soloN);

                            var without = new List<Part>();
                            foreach (var q in real) if (!ReferenceEquals(q, p)) without.Add(q);
                            Only(without);
                            var wpx = Shoot(cam, res, out _);
                            var vis = DiffMask(full, wpx, DIFF_LO, out int visN);

                            int cov = CountAnd(soloMask, vis, true);
                            string occ = soloN >= MIN_REGION_PX
                                ? F4((double) cov / soloN)
                                : "null";
                            fparts.Add("{" + $"\"part\": {J(p.Name)}, \"solo_px\": {soloN}, " +
                                       $"\"visible_px\": {visN}, \"covered_px\": {cov}, \"occlusion\": {occ}" + "}");
                        }

                        var attr = new StringBuilder("{");
                        bool fa = true;
                        foreach (var kv in attribution)
                        {
                            if (!fa) attr.Append(", ");
                            fa = false;
                            attr.Append(J(kv.Key)).Append(": ").Append(kv.Value);
                        }
                        attr.Append("}");

                        perFrame.Add("        {" +
                            $"\"frame\": {f}, " +
                            $"\"depth_overlap_px\": {depthDenom}, " +
                            $"\"depth_body_px\": {humValid}, \"depth_aux_px\": {auxValid}, " +
                            $"\"aux_over_body_px\": {auxOverBody}, \"body_over_aux_px\": {bodyOverAux}, " +
                            $"\"aux_over_body\": {(auxOverFrac < 0 ? "null" : F4(auxOverFrac))}, " +
                            $"\"body_over_aux\": {(bodyOverFrac < 0 ? "null" : F4(bodyOverFrac))}, " +
                            $"\"head_solo_px\": {headSolo}, " +
                            $"\"head_covered_lo\": {headCovLo}, \"head_covered_hi\": {headCovHi}, " +
                            $"\"head_occlusion_lo\": {(headOccLo < 0 ? "null" : F4(headOccLo))}, " +
                            $"\"head_occlusion_hi\": {(headOccHi < 0 ? "null" : F4(headOccHi))}, " +
                            $"\"head_occluded_by\": {attr}, " +
                            $"\"parts\": [{string.Join(", ", fparts)}]" + "}");

                        foreach (var p in parts) UnityEngine.Object.DestroyImmediate(p.Go);
                        foreach (var smr in Disabled) if (smr != null) smr.enabled = true;
                    }

                    // The worst frame, with the covered pixels painted, because a number nobody can
                    // look at is how this project shipped a flawless mechanism for a fault that did
                    // not exist.
                    if (worstPng != null && worstCovered != null && worstHeadOcc > 0)
                        Paint(outDir, $"{safe}_WORST_f{worstFrame:000}_faceoccluded.png",
                              worstPng, worstCovered, new Color32(255, 0, 255, 255));
                    if (worstDepthPng != null && worstViolation != null && worstDepth > 0)
                        Paint(outDir, $"{safe}_WORST_f{worstDepthFrame:000}_depthviolation.png",
                              worstDepthPng, worstViolation, new Color32(0, 255, 0, 255));

                    int total = 0, deadPairs = 0;
                    foreach (var m in moved) { total += Math.Max(m, 0); if (m == 0) deadPairs++; }
                    string control;
                    if (anim == null)
                        control = "no_animator";
                    else if (moved.Count > 0 && total == 0)
                    {
                        control = "FAILED";
                        Debug.LogError($"[PARTS] {name}: CONTROL FAILED -- an Animator IS present and NOT ONE " +
                                       "PIXEL changed across the sequence. These frames say nothing about the " +
                                       "character; do not read the occlusion numbers from them.");
                        failures++;
                    }
                    else control = "ok";

                    // WHAT WAS FOUND, not only what was measured. "0 parts" must not read as
                    // "0 occlusion". headTris is in this gate because the first version of the
                    // gate passed on a character with ZERO head triangles, on the strength of a
                    // head-region pixel count that was really the podium.
                    bool looked = partsFound > 0 && headTris > 0 && headPx0 >= MIN_REGION_PX;
                    // The depth test has its OWN measurability gate, because it needs something
                    // different from the face test: two non-empty halves of the mesh and a working
                    // geometry pass. A character can be measurable for one and not the other, and
                    // collapsing the two into one verdict would report a character as clean on a
                    // test that never ran.
                    bool depthMeasurable = depthShader != null && bodyTris > 0 && auxTris > 0;
                    Debug.Log($"[PARTS] {name}: parts={partsFound} headRegionPx={headPx0} headTris={headTris} " +
                              $"bodyTris={bodyTris} auxTris={auxTris} depthMeasurable={depthMeasurable} " +
                              $"frames={frames} control={control} looked={looked} | {headNote}");
                    if (!depthMeasurable)
                        Debug.LogWarning($"[PARTS] {name}: NO DEPTH-ORDER TEST -- " +
                                         (depthShader == null ? "the depth shader is missing. " : "") +
                                         (auxTris == 0
                                             ? "every triangle is weighted to a humanoid bone, so there is " +
                                               "no hair/cloth half to be drawn in the wrong order. " : "") +
                                         (bodyTris == 0
                                             ? "no triangle is weighted to a humanoid bone, so there is no " +
                                               "body half to be drawn over. " : "") +
                                         "Unmeasured, NOT clean.");
                    if (!looked)
                        Debug.LogWarning($"[PARTS] {name}: DID NOT LOOK AT A FACE -- " +
                                         (partsFound == 0 ? "no renderers. " : "") +
                                         (headTris == 0
                                             ? "NO HEAD TRIANGLES: nothing in this mesh is dominantly " +
                                               "weighted to the humanoid Head/Jaw/eye bones, so there is " +
                                               "no face region to occlude. See the bone histogram above " +
                                               "-- this is a statement about the RIG. " : "") +
                                         (headTris > 0 && headPx0 < MIN_REGION_PX
                                             ? $"head region {headPx0} px < {MIN_REGION_PX}. " : "") +
                                         "Any zero below is about this probe, not about the character.");

                    json.Append("      \"parts_found\": ").Append(partsFound)
                        .Append(",\n      \"body_tris\": ").Append(bodyTris)
                        .Append(",\n      \"aux_tris\": ").Append(auxTris)
                        .Append(",\n      \"depth_measurable\": ").Append(depthMeasurable ? "true" : "false")
                        .Append(",\n      \"split_check_diff_px\": ").Append(splitDiff)
                        .Append(",\n      \"head_region_px_f0\": ").Append(headPx0)
                        .Append(",\n      \"head_region_tris\": ").Append(headTris)
                        .Append(",\n      \"head_note\": ").Append(J(headNote))
                        .Append(",\n      \"motion_control\": ").Append(J(control))
                        .Append(",\n      \"moved_px\": [").Append(string.Join(",", moved)).Append("]")
                        .Append(",\n      \"looked\": ").Append(looked ? "true" : "false")
                        .Append(",\n      \"error\": null")
                        .Append(",\n      \"frames_data\": [\n").Append(string.Join(",\n", perFrame))
                        .Append("\n      ]\n    }");

                    Debug.Log($"[PARTS] {name}: done");
                }
                catch (Exception e)
                {
                    Debug.LogError($"[PARTS] {name}: {e}");
                    failures++;
                    json.Append("      \"parts_found\": 0,\n      \"head_region_px_f0\": 0,\n")
                        .Append("      \"looked\": false,\n      \"error\": ")
                        .Append(J(e.GetType().Name + ": " + e.Message))
                        .Append(",\n      \"frames_data\": []\n    }");
                }
                finally
                {
                    if (podiumGo != null) UnityEngine.Object.DestroyImmediate(podiumGo);
                    if (bundle != null) bundle.Unload(true);
                }
            }
            json.Append("\n  ]\n}\n");
        }
        catch (Exception e)
        {
            Debug.LogError("[PARTS] FATAL: " + e);
            failures++;
        }
        finally
        {
            try
            {
                if (outDir != null && json.Length > 0)
                    File.WriteAllText(Path.Combine(outDir, "part_overlap.json"), json.ToString());
            }
            catch (Exception e) { Debug.LogError("[PARTS] could not write json: " + e); }
            EditorApplication.Exit(failures == 0 ? 0 : 1);
        }
    }
}
