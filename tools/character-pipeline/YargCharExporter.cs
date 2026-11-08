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
                            var rt = src.GetTag("RenderType", false, "");
                            if (rt == "TransparentCutout" || rt == "Transparent")
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
                    Debug.Log($"[YARGCHAR] {outName}: retargeted {fixedCount} materials to URP/Lit ({cutoutCount} alpha-cut)");

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
