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
                            // A fresh URP/Lit culls back faces. The source materials are Standard,
                            // which has no cull property to read, so the glTF doubleSided flag is
                            // lost on import and single-sided sheets (a hair fringe, an ear, an eye
                            // plane) vanish from the side their normals face away from: Alastor's mask
                            // showed through his fringe. YARG_CULL_OFF_MATERIALS="Head.001;Eyes.001"
                            // draws just those materials double-sided; everything else stays culled.
                            // Double-sided everywhere tints the lighting, so name them, do not blanket.
                            var cullOff = Environment.GetEnvironmentVariable("YARG_CULL_OFF_MATERIALS");
                            if (!string.IsNullOrEmpty(cullOff) && Array.IndexOf(cullOff.Split(';'), src.name) >= 0)
                                nm.SetFloat("_Cull", 0f);
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
                            Debug.Log($"[YARGCHAR] {outName}: material {src.name} cull={nm.GetFloat("_Cull")}");
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
