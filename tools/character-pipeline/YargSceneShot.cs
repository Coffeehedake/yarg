// Lives in tools/ for reference only. Copy it into a SCRATCH COPY of the Unity project, never into
// the real project's Assets (it is an editor script that opens scenes and instantiates prefabs).
// Opens the game's real CharacterSelect scene, puts the real podium prefab in the selected slot,
// loads a .yargchar bundle onto it exactly the way CharacterDisplayManager does, and renders a
// frame through the scene's own camera with the game's renderer settings.
//
//   Unity -batchmode -projectPath <scratch> -executeMethod YargSceneShot.Run
//         -yargchars "<path.yargchar>|<Name>;<path2>|<Name2>" -shotDir <out> [-res 2560] [-yaws "0;35;-35;180"]
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using YARG.ContentBrowser.CharacterSelect;
using YARG.Helpers;
using YARG.Helpers.Extensions;

public static class YargSceneShot
{
    private static string Arg(string[] a, string n)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], n, StringComparison.OrdinalIgnoreCase)) return a[i + 1];
        return null;
    }

    // Unity moves bones on Animator.Update but does not re-skin in an editor pass, so bake each
    // skinned mesh to a static copy at the current pose and hide the original.
    private static readonly List<SkinnedMeshRenderer> Disabled = new List<SkinnedMeshRenderer>();

    private static List<GameObject> Bake(GameObject root)
    {
        var baked = new List<GameObject>();
        Disabled.Clear();
        foreach (var smr in root.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            if (!smr.enabled || smr.sharedMesh == null) continue;
            var m = new Mesh();
            smr.BakeMesh(m, true);
            var go = new GameObject("__baked_" + smr.name);
            go.transform.SetPositionAndRotation(smr.transform.position, smr.transform.rotation);
            go.layer = smr.gameObject.layer;
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = smr.sharedMaterials;
            mr.shadowCastingMode = smr.shadowCastingMode;
            mr.receiveShadows = smr.receiveShadows;
            smr.enabled = false;
            Disabled.Add(smr);
            baked.Add(go);
        }
        return baked;
    }

    public static void Run()
    {
        int failures = 0;
        try
        {
            var args = Environment.GetCommandLineArgs();
            var list = Arg(args, "-yargchars");
            var outDir = Arg(args, "-shotDir");
            Directory.CreateDirectory(outDir);
            int res = int.TryParse(Arg(args, "-res"), out var rr) ? rr : 1280;
            var yawList = (Arg(args, "-yaws") ?? "0").Split(';');

            // The game ships a Low and a High pipeline asset; the High one has SSAO.
            int high = Array.IndexOf(QualitySettings.names, "High");
            Debug.Log($"[SHOT] quality levels: {string.Join(", ", QualitySettings.names)}; current {QualitySettings.GetQualityLevel()}; High={high}");
            if (high >= 0) QualitySettings.SetQualityLevel(high, true);

            EditorSceneManager.OpenScene("Assets/Scenes/CharacterSelect.unity", OpenSceneMode.Single);
            var dm = UnityEngine.Object.FindFirstObjectByType<CharacterDisplayManager>();
            var so = new SerializedObject(dm);
            var podiumPrefab = so.FindProperty("_displayPrefab").objectReferenceValue as GameObject;
            var selected = so.FindProperty("_selectedLocation").objectReferenceValue as Transform;
            var cam = Camera.main;
            Debug.Log($"[SHOT] podium prefab={(podiumPrefab ? podiumPrefab.name : "NULL")} selected={(selected ? selected.name : "NULL")} camera={(cam ? cam.name : "NULL")}");

            foreach (var entry in list.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(entry)) continue;
                var bits = entry.Split('|');
                var file = bits[0].Trim();
                var name = bits.Length > 1 ? bits[1].Trim() : Path.GetFileNameWithoutExtension(file);
                try
                {
                    var podiumGo = (GameObject) PrefabUtility.InstantiatePrefab(podiumPrefab, selected);
                    podiumGo.transform.localPosition = Vector3.zero;
                    podiumGo.SetActive(true);
                    var podium = podiumGo.GetComponent<Podium>();
                    if (podium.Light != null) podium.Light.color = Color.white;

                    var bundle = AssetBundle.LoadFromFile(file);
                    if (bundle == null) throw new Exception("could not load " + file);
                    var prefab = bundle.LoadAsset<GameObject>(BackgroundHelper.CHARACTER_PREFAB_PATH.ToLowerInvariant());
                    if (prefab == null) throw new Exception("no character prefab in bundle");

                    var ch = UnityEngine.Object.Instantiate(prefab, podium.CharacterLocation);
                    ch.transform.SetParent(podium.CharacterLocation, false);
                    ch.transform.localPosition = Vector3.zero;
                    ch.SetActive(true);

                    // What the game's preview does, best effort: it may need play mode.
                    try
                    {
                        var vc = ch.GetComponent<YARG.Venue.Characters.VRMCharacter>();
                        if (vc != null) { vc.Initialize(); vc.SetPreviewIdle(); }
                    }
                    catch (Exception e) { Debug.Log($"[SHOT] {name}: VRMCharacter init skipped: {e.GetType().Name}: {e.Message}"); }

                    var anim = ch.GetComponent<Animator>();
                    if (anim != null)
                    {
                        if (anim.HasParameter("Attract")) anim.SetTrigger("Attract");
                        else if (anim.HasParameter("Idle")) anim.SetTrigger("Idle");
                        anim.Rebind();
                        anim.Update(1.0f);
                    }
                    foreach (var yawText in yawList)
                    {
                        float yaw = float.Parse(yawText);
                        ch.transform.localRotation = Quaternion.Euler(0f, yaw, 0f);
                        var baked = Bake(ch);

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
                        File.WriteAllBytes(Path.Combine(outDir, $"{name.Replace(" ", "")}_yaw{yaw:0}_podium.png"), tex.EncodeToPNG());
                        UnityEngine.Object.DestroyImmediate(tex);
                        rt.Release();
                        UnityEngine.Object.DestroyImmediate(rt);

                        foreach (var g in baked) UnityEngine.Object.DestroyImmediate(g);
                        foreach (var smr in Disabled) if (smr != null) smr.enabled = true;
                    }
                    UnityEngine.Object.DestroyImmediate(podiumGo);
                    bundle.Unload(true);
                    Debug.Log($"[SHOT] {name}: rendered");
                }
                catch (Exception e)
                {
                    Debug.LogError($"[SHOT] {name}: {e}");
                    failures++;
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError("[SHOT] FATAL: " + e);
            failures++;
        }
        finally
        {
            EditorApplication.Exit(failures == 0 ? 0 : 1);
        }
    }
}
