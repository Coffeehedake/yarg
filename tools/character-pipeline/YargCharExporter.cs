// TEMPORARY build-tooling. Not part of the fork; delete after use.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using YARG.Helpers;
using YARG.Venue.Characters;

public static class YargCharExporter
{
    private const string WorkFolder = "Assets/__TempExport/Work";

    private static string Arg(string[] args, string name)
    {
        for (int i = 0; i < args.Length - 1; i++)
            if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        return null;
    }

    private static Texture GetAny(Material m, params string[] names)
    {
        foreach (var n in names)
            if (m.HasProperty(n) && m.GetTexture(n) != null)
                return m.GetTexture(n);
        return null;
    }

    // ---- Does this material's geometry HAVE a back face? -------------------
    //
    // Decided by MEASURING the triangles, not by reading the glTF doubleSided
    // flag. That flag is almost always true -- across the third-party sources
    // here, 60 materials true, 0 false, 5 absent -- because a Blender glTF
    // export writes `doubleSided = not use_backface_culling` and Blender
    // defaults that off. A field that is true because of an upstream default
    // is not a declaration, and on 2026-11-13 reading it as one nearly put the
    // whole roster double-sided. It is not read here, in either direction: an
    // ABSENT flag is equally just a different tool's default (Batman's rips),
    // so it cannot be trusted as a veto either.
    //
    // Two scale-invariant numbers per connected piece of surface, vertices
    // welded by position so a UV seam does not split a piece:
    //
    //   OPENNESS  boundary_length / sqrt(area). An edge used by one triangle
    //             is a boundary. A solid with a wrist hole scores near zero;
    //             a single-layer sheet is boundary all the way round. A flat
    //             disc is 2*sqrt(pi) = 3.5.
    //   SOLIDITY  |signed volume| / area^1.5 about the piece's own centroid.
    //             A sphere is 0.094, a limb-shaped cylinder 0.058, anything
    //             enclosing nothing is about 0. This is what separates a CAPE
    //             (large, few boundary edges for its area, but no volume) from
    //             a TORSO.
    //
    // BOTH must say sheet. Openness alone condemns every solid with a hole;
    // solidity alone condemns a closed paper-thin slab, which has a real back
    // face and culls perfectly well.
    //
    // Both ratios are dimensionless, so vertices are used in their own local
    // space and no transform is applied. That holds for uniform scale; a
    // non-uniformly scaled object would distort them, and none here is.
    //
    // A material spans pieces and _Cull is per material, so a material is
    // drawn double-sided when a meaningful share of its AREA sits in sheets.

    // Thresholds. Alastor is the one character whose sidedness was decided by
    // hand and shipped, so he is the test: Eyes.001 must come out double-sided
    // and Head.001 must not. See docs/reported-faults-2026-11-12.md.
    // Tuned against 3,971 connected pieces across the 37 characters that have a
    // `.vrm`, then sensitivity-tested rather than picked at one point:
    //
    //   OpenMin    the ROBUST one. Openness is strongly bimodal -- 822 pieces
    //              below 0.1 and a large mass above 3, with a sparse valley
    //              between -- and anything in 1.0..2.0 gives the IDENTICAL set
    //              of material verdicts. 1.5 sits mid-plateau.
    //   SolidMin   the SENSITIVE one, and the reason both tests are needed. It
    //              rejects pieces that are open but still voluminous (a hollow
    //              head shell with eye and mouth openings), which openness alone
    //              calls a sheet: dropping it names 93-147 of 265 materials and
    //              FAILS Alastor, whose Head.001 is single-sided on purpose.
    //              Solidity is not bimodal, so this cut is a judgement; 0.02
    //              gives 20 materials, 0.025 gives 31 and 0.03 gives 48. Err
    //              LOW. Culled is the status quo that ships 52 characters with
    //              no reported fault, and a wrongly double-sided material hides
    //              inverted winding instead of showing it.
    //
    // The test is Alastor, the only character whose sidedness was decided by
    // hand and shipped: Eyes.001 must come out double-sided and Head.001 must
    // not. These values reproduce that, and name 20 of 265 materials (7.5%) --
    // eyelashes, brows, hair cards and eye planes.
    private const float OpenMin = 1.5f;     // boundary/sqrt(area) above this: open
    private const float SolidMin = 0.02f;   // |V|/A^1.5 below this: encloses nothing
    private const float SheetAreaShare = 0.20f;
    private const int MinPieceFaces = 12;
    private const float WeldQuant = 10000f; // 0.1 mm

    /// Measure, per material, how much of its area sits in open sheet pieces.
    private static Dictionary<Material, float> SheetShareByMaterial(GameObject root)
    {
        var area = new Dictionary<Material, double>();
        var sheet = new Dictionary<Material, double>();

        foreach (var r in root.GetComponentsInChildren<Renderer>(true))
        {
            Mesh mesh = r is SkinnedMeshRenderer smr ? smr.sharedMesh
                : r.GetComponent<MeshFilter>() != null ? r.GetComponent<MeshFilter>().sharedMesh
                : null;
            if (mesh == null) continue;
            if (!mesh.isReadable)
            {
                // Say so. A silent skip here is the worst outcome available: the
                // material measures as 0% sheet, comes out culled like everything
                // else, and the whole feature does nothing on that character with
                // no sign in the log that it did not run.
                Debug.LogWarning($"[YARGCHAR] sidedness: mesh '{mesh.name}' is not readable, "
                                 + "its materials cannot be measured and will stay culled");
                continue;
            }

            var verts = mesh.vertices;
            // Weld by quantised position: the import splits vertices at UV seams,
            // and an unwelded seam reads as a boundary, which would make every
            // textured solid look like a sheet.
            var weld = new int[verts.Length];
            // Keyed on the three quantised coordinates themselves, NOT on a hash
            // of them. A hash collision here would weld two vertices that are
            // nowhere near each other, joining pieces that do not touch and
            // destroying exactly the boundary count this is here to measure --
            // and it would do it silently, on one character, at random.
            var keyToId = new Dictionary<(long, long, long), int>(verts.Length);
            for (int v = 0; v < verts.Length; v++)
            {
                var key = ((long)Mathf.Round(verts[v].x * WeldQuant),
                           (long)Mathf.Round(verts[v].y * WeldQuant),
                           (long)Mathf.Round(verts[v].z * WeldQuant));
                if (!keyToId.TryGetValue(key, out var id)) { id = keyToId.Count; keyToId[key] = id; }
                weld[v] = id;
            }

            // Connected pieces are found across the WHOLE mesh, every submesh at
            // once, and only then is each piece's area split between the materials
            // on it. Doing it per submesh instead would cut a piece wherever one
            // material meets another and count that cut as BOUNDARY -- so a face
            // material on a closed head, bordered by a scalp material, would read
            // as an open sheet and be drawn double-sided. Same reason the Blender
            // side welds across materials.
            var mats = r.sharedMaterials;
            var faceMat = new List<Material>();
            var faceTri = new List<int>();
            for (int sub = 0; sub < mesh.subMeshCount; sub++)
            {
                var mat = sub < mats.Length ? mats[sub] : null;
                var tris = mesh.GetTriangles(sub);
                for (int t = 0; t + 2 < tris.Length; t += 3)
                {
                    faceMat.Add(mat);
                    faceTri.Add(tris[t]); faceTri.Add(tris[t + 1]); faceTri.Add(tris[t + 2]);
                }
            }
            int faceCount = faceMat.Count;
            if (faceCount == 0) continue;

            var edgeFaces = new Dictionary<long, List<int>>(faceCount * 3);
            for (int f = 0; f < faceCount; f++)
                for (int e = 0; e < 3; e++)
                {
                    int a = weld[faceTri[f * 3 + e]], b = weld[faceTri[f * 3 + (e + 1) % 3]];
                    long key = a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a;
                    if (!edgeFaces.TryGetValue(key, out var lst)) edgeFaces[key] = lst = new List<int>(2);
                    lst.Add(f);
                }

            var parent = new int[faceCount];
            for (int f = 0; f < faceCount; f++) parent[f] = f;
            int Find(int x) { while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
            void Union(int x, int y) { int rx = Find(x), ry = Find(y); if (rx != ry) parent[rx] = ry; }
            foreach (var kv in edgeFaces)
                for (int k = 1; k < kv.Value.Count; k++) Union(kv.Value[0], kv.Value[k]);

            var pieceArea = new Dictionary<int, double>();
            var pieceCentroid = new Dictionary<int, Vector3>();
            var pieceFaces = new Dictionary<int, int>();
            var faceArea = new double[faceCount];
            for (int f = 0; f < faceCount; f++)
            {
                Vector3 p0 = verts[faceTri[f * 3]], p1 = verts[faceTri[f * 3 + 1]], p2 = verts[faceTri[f * 3 + 2]];
                double a = 0.5 * Vector3.Cross(p1 - p0, p2 - p0).magnitude;
                faceArea[f] = a;
                int rt = Find(f);
                pieceArea.TryGetValue(rt, out var pa); pieceArea[rt] = pa + a;
                pieceCentroid.TryGetValue(rt, out var pc);
                pieceCentroid[rt] = pc + (p0 + p1 + p2) / 3f * (float)a;
                pieceFaces.TryGetValue(rt, out var pf); pieceFaces[rt] = pf + 1;
            }
            foreach (var key in new List<int>(pieceCentroid.Keys))
                pieceCentroid[key] = pieceCentroid[key] / (float)Math.Max(pieceArea[key], 1e-12);

            var pieceVol = new Dictionary<int, double>();
            for (int f = 0; f < faceCount; f++)
            {
                int rt = Find(f);
                var c = pieceCentroid[rt];
                Vector3 p0 = verts[faceTri[f * 3]] - c, p1 = verts[faceTri[f * 3 + 1]] - c, p2 = verts[faceTri[f * 3 + 2]] - c;
                pieceVol.TryGetValue(rt, out var pv);
                pieceVol[rt] = pv + Vector3.Dot(p0, Vector3.Cross(p1, p2)) / 6.0;
            }

            var pieceBoundary = new Dictionary<int, double>();
            foreach (var kv in edgeFaces)
            {
                if (kv.Value.Count != 1) continue;   // shared by two faces: interior
                int f = kv.Value[0], rt = Find(f);
                int a2 = (int)(kv.Key >> 32), b2 = (int)(kv.Key & 0xffffffffL);
                float len = 0f;
                for (int e = 0; e < 3; e++)
                {
                    int va = weld[faceTri[f * 3 + e]], vb = weld[faceTri[f * 3 + (e + 1) % 3]];
                    if ((va == a2 && vb == b2) || (va == b2 && vb == a2))
                        len = (verts[faceTri[f * 3 + e]] - verts[faceTri[f * 3 + (e + 1) % 3]]).magnitude;
                }
                pieceBoundary.TryGetValue(rt, out var pb); pieceBoundary[rt] = pb + len;
            }

            // Which pieces are sheets, then attribute every face's area to its own
            // material -- a piece can carry several.
            var sheetPiece = new Dictionary<int, bool>();
            foreach (var kv in pieceArea)
            {
                double a = kv.Value;
                if (a <= 0 || pieceFaces[kv.Key] < MinPieceFaces) { sheetPiece[kv.Key] = false; continue; }
                pieceBoundary.TryGetValue(kv.Key, out var bl);
                pieceVol.TryGetValue(kv.Key, out var vol);
                double openness = bl / Math.Sqrt(a);
                double solidity = Math.Abs(vol) / Math.Pow(a, 1.5);
                sheetPiece[kv.Key] = openness > OpenMin && solidity < SolidMin;
            }
            for (int f = 0; f < faceCount; f++)
            {
                var mat = faceMat[f];
                if (mat == null) continue;
                int rt = Find(f);
                if (pieceFaces[rt] < MinPieceFaces) continue;
                area.TryGetValue(mat, out var ma); area[mat] = ma + faceArea[f];
                if (sheetPiece[rt]) { sheet.TryGetValue(mat, out var ms); sheet[mat] = ms + faceArea[f]; }
            }
        }

        var share = new Dictionary<Material, float>();
        foreach (var kv in area)
        {
            sheet.TryGetValue(kv.Key, out var s);
            share[kv.Key] = (float)(s / Math.Max(kv.Value, 1e-12));
        }
        return share;
    }

    public static void ExportAll()
    {
        int failures = 0;
        try
        {
            var args = Environment.GetCommandLineArgs();
            var list = Arg(args, "-vrmList");
            var outDir = Arg(args, "-outDir");
            if (string.IsNullOrEmpty(list) || string.IsNullOrEmpty(outDir))
            {
                Debug.LogError("[YARGCHAR] missing -vrmList or -outDir");
                EditorApplication.Exit(1);
                return;
            }
            Directory.CreateDirectory(outDir);

            foreach (var entry in list.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(entry)) continue;
                var bits = entry.Split('|');
                var vrmPath = bits[0].Trim();
                var outName = bits.Length > 1 ? bits[1].Trim() : Path.GetFileNameWithoutExtension(vrmPath);
                var outPath = Path.Combine(outDir, outName + ".yargchar");
                Debug.Log($"[YARGCHAR] ===== {outName} =====");

                try
                {
                    if (!File.Exists(vrmPath))
                    {
                        Debug.LogError($"[YARGCHAR] {outName}: vrm missing");
                        failures++;
                        continue;
                    }

                    if (!AssetDatabase.IsValidFolder(WorkFolder))
                        AssetDatabase.CreateFolder("Assets/__TempExport", "Work");

                    var assetPath = WorkFolder + "/" + Path.GetFileName(vrmPath);
                    File.Copy(vrmPath, assetPath, true);
                    AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
                    AssetDatabase.Refresh();

                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
                    if (prefab == null)
                    {
                        Debug.LogError($"[YARGCHAR] {outName}: did not import as a GameObject");
                        failures++;
                        continue;
                    }

                    var instance = (GameObject) PrefabUtility.InstantiatePrefab(prefab);
                    PrefabUtility.UnpackPrefabInstance(instance, PrefabUnpackMode.Completely,
                        InteractionMode.AutomatedAction);
                    instance.name = outName.Replace(" ", "");

                    var animator = instance.GetComponent<Animator>();
                    bool human = animator != null && animator.avatar != null && animator.avatar.isHuman;
                    bool valid = animator != null && animator.avatar != null && animator.avatar.isValid;
                    Debug.Log($"[YARGCHAR] {outName}: avatar human={human} valid={valid}");

                    // A humanoid avatar and a controller are not enough: the mesh
                    // only follows the skeleton if it is a SkinnedMeshRenderer.
                    // Pomni shipped with a valid avatar, a controller, 6/6 grip
                    // bones and every mesh STATIC, and so could not move at all.
                    int skinned = instance.GetComponentsInChildren<SkinnedMeshRenderer>(true).Length;
                    int statics = 0;
                    foreach (var mr in instance.GetComponentsInChildren<MeshRenderer>(true))
                        if (mr.GetComponent<MeshFilter>() != null && mr.GetComponent<MeshFilter>().sharedMesh != null)
                            statics++;
                    Debug.Log($"[YARGCHAR] {outName}: renderers skinned={skinned} static={statics}");
                    if (skinned == 0)
                        Debug.LogError($"[YARGCHAR] {outName}: NO skinned meshes - this character cannot animate");

                    int gripOk = 0;
                    if (animator != null)
                        foreach (var b in new[]
                                 {
                                     HumanBodyBones.RightHand, HumanBodyBones.RightThumbDistal,
                                     HumanBodyBones.RightIndexProximal, HumanBodyBones.RightIndexIntermediate,
                                     HumanBodyBones.RightLittleProximal, HumanBodyBones.RightLittleDistal
                                 })
                            if (animator.GetBoneTransform(b) != null) gripOk++;
                    Debug.Log($"[YARGCHAR] {outName}: mic-grip bones {gripOk}/6");

                    var urp = Shader.Find("Universal Render Pipeline/Lit");
                    // One verdict per MATERIAL, measured across EVERY renderer that
                    // uses it, before the conversion loop below -- that loop dedupes
                    // by material, so it only ever sees the first renderer's share
                    // of a material's geometry and could not decide this itself.
                    var sheetShare = SheetShareByMaterial(instance);
                    var remapped = new Dictionary<Material, Material>();
                    int fixedCount = 0;
                    int cutoutCount = 0;
                    int blendCount = 0;
                    foreach (var r in instance.GetComponentsInChildren<Renderer>(true))
                    {
                        var mats = r.sharedMaterials;
                        for (int i = 0; i < mats.Length; i++)
                        {
                            var src = mats[i];
                            if (src == null) continue;
                            if (remapped.TryGetValue(src, out var done)) { mats[i] = done; continue; }
                            if (urp == null || src.shader == urp) continue;

                            var baseMap = GetAny(src, "_BaseMap", "_MainTex");
                            var normal = GetAny(src, "_BumpMap", "_NormalMap");
                            var mr = GetAny(src, "_MetallicGlossMap");
                            var emis = GetAny(src, "_EmissionMap", "_EmissiveTex");
                            var col = src.HasProperty("_BaseColor") ? src.GetColor("_BaseColor")
                                : src.HasProperty("_Color") ? src.GetColor("_Color") : Color.white;

                            var nm = new Material(urp) { name = src.name + "_urp" };
                            if (baseMap != null) { nm.SetTexture("_BaseMap", baseMap); nm.SetTexture("_MainTex", baseMap); }
                            nm.SetColor("_BaseColor", col);
                            // A fresh URP/Lit culls back faces, and the Standard material it
                            // was imported as has no cull property to carry the source's
                            // intent, so single-sided sheets -- a hair fringe, an ear, an eye
                            // plane -- vanish from the side their normals face away from.
                            // Alastor's mask showed through his fringe that way. The decision
                            // is MEASURED from the geometry by SheetShareByMaterial above, per
                            // material; see the comment on it for why the file's own
                            // doubleSided flag is not read.
                            // YARG_CULL_OFF_MATERIALS / YARG_CULL_ON_MATERIALS override it
                            // either way, for a judgement the measurement gets wrong.
                            sheetShare.TryGetValue(src, out var share);
                            bool doubleSided = share >= SheetAreaShare;
                            var cullOff = Environment.GetEnvironmentVariable("YARG_CULL_OFF_MATERIALS");
                            var cullOn = Environment.GetEnvironmentVariable("YARG_CULL_ON_MATERIALS");
                            string why = doubleSided ? "measured sheet" : "measured solid";
                            if (!string.IsNullOrEmpty(cullOff) && Array.IndexOf(cullOff.Split(';'), src.name) >= 0)
                            { doubleSided = true; why = "forced by YARG_CULL_OFF_MATERIALS"; }
                            else if (!string.IsNullOrEmpty(cullOn) && Array.IndexOf(cullOn.Split(';'), src.name) >= 0)
                            { doubleSided = false; why = "forced by YARG_CULL_ON_MATERIALS"; }
                            if (doubleSided) nm.SetFloat("_Cull", 0f);
                            Debug.Log($"[YARGCHAR] {outName}: sidedness {src.name} "
                                      + $"sheet-area {share * 100f:F1}% -> "
                                      + (doubleSided ? "DOUBLE-SIDED" : "culled") + $" ({why})");
                            // A flat toon character does not want URP's default shine: the sky
                            // reflection and specular on every sheet read as a cool purple tint and
                            // blown-out highlights (Alastor in game). Name the materials to flatten.
                            var noShine = Environment.GetEnvironmentVariable("YARG_NO_SHINE_MATERIALS");
                            if (!string.IsNullOrEmpty(noShine) && (noShine == "*" || Array.IndexOf(noShine.Split(';'), src.name) >= 0))
                            {
                                nm.SetFloat("_Smoothness", 0f);
                                nm.SetFloat("_Metallic", 0f);
                                nm.SetFloat("_SpecularHighlights", 0f);
                                nm.SetFloat("_EnvironmentReflections", 0f);
                                nm.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
                                nm.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
                            }
                            // An untextured near-black material is an outline shell. URP/Lit
                            // gives it a specular sheen that shows as pale lines along edges
                            // (Alastor's fingers), so strip the shine.
                            if (baseMap == null && col.maxColorComponent < 0.1f)
                            {
                                // The shell is a slightly larger copy of the body, so it shadows the body.
                                if (Environment.GetEnvironmentVariable("YARG_SHELL_NO_SHADOW") == "1")
                                    nm.SetShaderPassEnabled("ShadowCaster", false);
                                nm.SetFloat("_Smoothness", 0f);
                                nm.SetFloat("_Metallic", 0f);
                                nm.SetFloat("_SpecularHighlights", 0f);
                                nm.SetFloat("_EnvironmentReflections", 0f);
                                nm.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
                                nm.EnableKeyword("_ENVIRONMENTREFLECTIONS_OFF");
                            }
                            if (normal != null) { nm.SetTexture("_BumpMap", normal); nm.EnableKeyword("_NORMALMAP"); }
                            if (mr != null)
                            {
                                nm.SetTexture("_MetallicGlossMap", mr);
                                nm.EnableKeyword("_METALLICSPECGLOSSMAP");
                                nm.SetFloat("_Metallic", 1f);
                            }
                            if (emis != null)
                            {
                                nm.SetTexture("_EmissionMap", emis);
                                nm.EnableKeyword("_EMISSION");
                                nm.SetColor("_EmissionColor", Color.white);
                            }
                            // Hair, eyelashes and lace are alpha-cut cards. Building a
                            // fresh URP material throws that away and they turn into
                            // opaque slabs, so carry the source's RenderType across.
                            //
                            // ALPHA TESTING AND ALPHA BLENDING ARE NOT THE SAME THING,
                            // and this branch used to treat them as one. `Transparent`
                            // and `TransparentCutout` both got `_AlphaClip`, so every
                            // genuinely blended material in the project shipped as a
                            // hard threshold at 0.5. Measured over the installed set on
                            // 2026-11-12: of 396 URP/Lit materials in the 59 characters
                            // this pipeline built, 40 were cutouts and **not one** was
                            // blended. The single transparent material anywhere in the
                            // 65 belongs to Adachi Rei, a downloaded MToon bundle we
                            // did not build.
                            //
                            // Gordon Freeman is the measured cost. `VRM_BLEND_MATERIALS=
                            // "lens"` was added for him and the builder did its half
                            // correctly -- his `.vrm` carries alphaMode BLEND. Then this
                            // ran, and `lens.png`'s alpha (0.153 to 0.624, mean 0.330)
                            // met a 0.5 threshold: **79.3% of the lens is clipped away
                            // and the remaining 21% draws fully opaque**. His glasses are
                            // not glass, they are a speckled mask -- and he is recorded
                            // in the README as fixed, because the render that confirmed
                            // the fix was of the VRM and not of the bundle.
                            //
                            // A cutout cannot express "uniformly 33% opaque". There is no
                            // value of _Cutoff that does. So the two cases are separated
                            // and `Transparent` now gets URP's transparent surface. The
                            // cutout path below is UNCHANGED, deliberately: the 40
                            // materials that work today must not move.
                            var rt = src.GetTag("RenderType", false, "");
                            if (rt == "Transparent")
                            {
                                nm.SetFloat("_Surface", 1f);     // 0 Opaque, 1 Transparent
                                nm.SetFloat("_Blend", 0f);       // 0 Alpha, 1 Premultiply...
                                nm.SetFloat("_SrcBlend", (float) UnityEngine.Rendering.BlendMode.SrcAlpha);
                                nm.SetFloat("_DstBlend", (float) UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                                nm.SetFloat("_SrcBlendAlpha", (float) UnityEngine.Rendering.BlendMode.One);
                                nm.SetFloat("_DstBlendAlpha", (float) UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
                                nm.SetFloat("_ZWrite", 0f);
                                nm.SetFloat("_AlphaClip", 0f);
                                nm.DisableKeyword("_ALPHATEST_ON");
                                nm.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                                // The shader reads RenderType from the tag, and a URP
                                // material built from scratch carries the Lit default.
                                nm.SetOverrideTag("RenderType", "Transparent");
                                nm.renderQueue = 3000;           // after everything opaque
                                blendCount++;
                            }
                            else if (rt == "TransparentCutout")
                            {
                                nm.SetFloat("_AlphaClip", 1f);
                                nm.EnableKeyword("_ALPHATEST_ON");
                                nm.SetFloat("_Cutoff", src.HasProperty("_Cutoff") ? src.GetFloat("_Cutoff") : 0.5f);
                                nm.renderQueue = 2450;
                                cutoutCount++;
                            }
                            AssetDatabase.CreateAsset(nm, WorkFolder + "/" + outName.Replace(" ", "") + "_" + fixedCount + ".mat");
                            remapped[src] = nm;
                            mats[i] = nm;
                            fixedCount++;
                        }
                        r.sharedMaterials = mats;
                    }
                    AssetDatabase.SaveAssets();
                    Debug.Log($"[YARGCHAR] {outName}: retargeted {fixedCount} materials to URP/Lit ({cutoutCount} alpha-cut, {blendCount} alpha-blended)");

                    var character = instance.GetComponent<VRMCharacter>() ?? instance.AddComponent<VRMCharacter>();
                    character.Type = VenueCharacter.CharacterType.Vocals;
                    character.UseCustomAnimations = false;

                    if (animator != null && animator.runtimeAnimatorController == null)
                    {
                        var ctrl = AssetDatabase.LoadAssetAtPath<RuntimeAnimatorController>(
                            "Assets/Resources/Animations/Vocals/Default/DefaultController.controller");
                        if (ctrl != null) animator.runtimeAnimatorController = ctrl;
                        Debug.Log($"[YARGCHAR] {outName}: controller {(ctrl != null ? ctrl.name : "NOT FOUND")}");
                    }

                    // Opt-in: render both hands inside Unity instead of exporting.
                    // Run WITHOUT -nographics. See YargCharHandRender.cs.
                    var renderDir = Arg(args, "-renderDir");
                    if (!string.IsNullOrEmpty(renderDir))
                    {
                        YargCharHandRender.Render(instance, outName.Replace(" ", ""), renderDir, 0f);
                        YargCharHandRender.Render(instance, outName.Replace(" ", ""), renderDir, 0.5f);
                        Debug.Log($"[YARGCHAR] {outName}: hands rendered to {renderDir}");
                        continue;
                    }

                    BackgroundHelper.Export(instance, BackgroundHelper.ExportType.Character,
                        Array.Empty<string>(), outPath);

                    if (File.Exists(outPath))
                        Debug.Log($"[YARGCHAR] {outName}: OK {new FileInfo(outPath).Length} bytes");
                    else
                    {
                        Debug.LogError($"[YARGCHAR] {outName}: no file produced");
                        failures++;
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError($"[YARGCHAR] {outName}: EXCEPTION {e}");
                    failures++;
                }
                finally
                {
                    if (AssetDatabase.IsValidFolder(WorkFolder)) AssetDatabase.DeleteAsset(WorkFolder);
                }
            }
            Debug.Log($"[YARGCHAR] ALL DONE, failures={failures}");
        }
        catch (Exception e)
        {
            Debug.LogError("[YARGCHAR] FATAL: " + e);
            failures++;
        }
        finally
        {
            EditorApplication.Exit(failures == 0 ? 0 : 1);
        }
    }
}
