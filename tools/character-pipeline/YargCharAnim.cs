// Renders a character as a SEQUENCE OF FRAMES through its own animation clip, so a fault that
// only appears in motion can be seen and measured. Lives in tools/ for reference only; copy it
// into a SCRATCH COPY of the Unity project, never into the real project's Assets.
//
//   Unity -batchmode -quit -projectPath <scratch> -executeMethod YargCharAnim.Run
//         -yargchars "<path.yargchar>|<Name>" -shotDir <out>
//         [-frames 12] [-step 0.125] [-warmup 1.0] [-res 720] [-yaw 0]
//
// WHY THIS EXISTS. YargSceneShot calls anim.Update(1.0f) ONCE and renders the pose it lands in.
// That is one settled frame, and a static render has already cleared a character that was broken:
// the bind pose never reads the humanoid map, so a rig whose hips sit at floor level looks
// perfect standing still and only comes apart once something re-poses it about a displaced axis.
// Hair and cloth are worse, because a spring chain at rest tells you nothing about a chain that
// is being swung.
//
// THE HARNESS NEEDS A CONTROL, AND IT IS BUILT IN RATHER THAN LEFT TO THE CALLER. If the Animator
// does not actually advance, every frame comes out identical -- which on screen is indistinguishable
// from a character that correctly stands still, and five spring probes on this project once read
// zero for every character because the harness, not the subject, was what was being measured. So
// this tool measures its OWN frame-to-frame change and says so in the log: per-frame moved-pixel
// counts, and a loud FAILED line if the sequence never moves. A zero here is then a finding about
// the harness, not a finding about the character.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using YARG.ContentBrowser.CharacterSelect;
using YARG.Helpers;
using YARG.Helpers.Extensions;

public static class YargCharAnim
{
    private static string Arg(string[] a, string n)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], n, StringComparison.OrdinalIgnoreCase)) return a[i + 1];
        return null;
    }

    // Unity moves bones on Animator.Update but does not re-skin in an editor pass, so each frame
    // must be baked to a static copy at the pose of that frame. Skipping this renders the BIND
    // pose every time and the sequence looks frozen -- which is the exact false negative the
    // control below exists to catch.
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

    private static byte[] Shoot(Camera cam, int res, out Color32[] px)
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
        px = tex.GetPixels32();
        var png = tex.EncodeToPNG();
        UnityEngine.Object.DestroyImmediate(tex);
        rt.Release();
        UnityEngine.Object.DestroyImmediate(rt);
        return png;
    }

    // How many pixels differ from the previous frame, above a threshold that ignores dither and
    // light flicker. This is the control: it is a statement about whether the HARNESS moved.
    private static int Moved(Color32[] a, Color32[] b)
    {
        if (a == null || b == null || a.Length != b.Length) return -1;
        int n = 0;
        for (int i = 0; i < a.Length; i++)
        {
            int d = Math.Abs(a[i].r - b[i].r) + Math.Abs(a[i].g - b[i].g) + Math.Abs(a[i].b - b[i].b);
            if (d > 24) n++;
        }
        return n;
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
            int res = int.TryParse(Arg(args, "-res"), out var rr) ? rr : 720;
            int frames = int.TryParse(Arg(args, "-frames"), out var ff) ? ff : 12;
            float step = float.TryParse(Arg(args, "-step"), out var ss) ? ss : 0.125f;
            float warmup = float.TryParse(Arg(args, "-warmup"), out var ww) ? ww : 1.0f;
            float yaw = float.TryParse(Arg(args, "-yaw"), out var yy) ? yy : 0f;
            Debug.Log($"[ANIM] frames={frames} step={step}s warmup={warmup}s res={res} yaw={yaw}");

            int high = Array.IndexOf(QualitySettings.names, "High");
            if (high >= 0) QualitySettings.SetQualityLevel(high, true);

            EditorSceneManager.OpenScene("Assets/Scenes/CharacterSelect.unity", OpenSceneMode.Single);
            var dm = UnityEngine.Object.FindFirstObjectByType<CharacterDisplayManager>();
            var so = new SerializedObject(dm);
            var podiumPrefab = so.FindProperty("_displayPrefab").objectReferenceValue as GameObject;
            var selected = so.FindProperty("_selectedLocation").objectReferenceValue as Transform;
            var cam = Camera.main;

            foreach (var entry in list.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(entry)) continue;
                var bits = entry.Split('|');
                var file = bits[0].Trim();
                var name = bits.Length > 1 ? bits[1].Trim() : Path.GetFileNameWithoutExtension(file);
                var safe = name.Replace(" ", "");
                try
                {
                    var podiumGo = (GameObject) PrefabUtility.InstantiatePrefab(podiumPrefab, selected);
                    podiumGo.transform.localPosition = Vector3.zero;
                    podiumGo.SetActive(true);
                    var podium = podiumGo.GetComponent<Podium>();
                    // -light r,g,b forces the podium light to a COLOUR instead of white.
                    // White is the default because it is neutral for geometry work, but it is
                    // also the least discriminating possible setting for a LIT-versus-UNLIT
                    // question: under uniform white, a lit material and an unlit one converge.
                    // A strongly coloured light separates them with no statistics at all --
                    // an honoured unlit material ignores it, a lit one takes the colour.
                    if (podium.Light != null)
                    {
                        var lc = Arg(args, "-light");
                        if (lc != null)
                        {
                            var p3 = lc.Split(',');
                            podium.Light.color = new Color(float.Parse(p3[0]), float.Parse(p3[1]), float.Parse(p3[2]));
                        }
                        else podium.Light.color = Color.white;
                    }

                    var bundle = AssetBundle.LoadFromFile(file);
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
                    catch (Exception e) { Debug.Log($"[ANIM] {name}: VRMCharacter init skipped: {e.GetType().Name}: {e.Message}"); }

                    var anim = ch.GetComponent<Animator>();
                    if (anim == null)
                    {
                        // Not a failure of the render -- a statement about the character. Say which.
                        Debug.LogWarning($"[ANIM] {name}: NO ANIMATOR. Nothing can animate; frames would be identical by construction.");
                    }
                    else
                    {
                        if (anim.HasParameter("Attract")) anim.SetTrigger("Attract");
                        else if (anim.HasParameter("Idle")) anim.SetTrigger("Idle");
                        anim.Rebind();
                        // Settle the spring chains first, so frame 0 is a pose the solver agrees
                        // with rather than the instantiate pose. Otherwise frame 0 -> 1 carries the
                        // whole settle and swamps the motion we came to look at.
                        anim.Update(warmup);
                    }

                    Color32[] prev = null;
                    var moved = new List<int>();
                    for (int f = 0; f < frames; f++)
                    {
                        if (f > 0 && anim != null) anim.Update(step);
                        var baked = Bake(ch);
                        Color32[] px;
                        var png = Shoot(cam, res, out px);
                        File.WriteAllBytes(Path.Combine(outDir, $"{safe}_f{f:000}.png"), png);
                        if (prev != null) moved.Add(Moved(prev, px));
                        prev = px;
                        foreach (var g in baked) UnityEngine.Object.DestroyImmediate(g);
                        foreach (var smr in Disabled) if (smr != null) smr.enabled = true;
                    }

                    // THE CONTROL, reported as a number rather than left to the eye.
                    int total = 0, deadPairs = 0;
                    foreach (var m in moved) { total += Math.Max(m, 0); if (m == 0) deadPairs++; }
                    Debug.Log($"[ANIM] {name}: per-frame moved px = {string.Join(",", moved)}");
                    if (anim == null)
                    {
                        // A STATEMENT ABOUT THE CHARACTER, NOT ABOUT THE HARNESS, and the two must
                        // not share a verdict. With no Animator the frames are identical BY
                        // CONSTRUCTION -- that is a correct reading of a character that cannot
                        // animate, not a broken measurement, and counting it as a failure across a
                        // roster sweep would bury the real control failures in false alarms.
                        Debug.Log($"[ANIM] {name}: NO ANIMATOR -- {frames} identical frames, as expected. " +
                                  "Not a control failure. Nothing here can be read as motion either way.");
                    }
                    else if (moved.Count > 0 && total == 0)
                    {
                        Debug.LogError($"[ANIM] {name}: CONTROL FAILED -- an Animator IS present, {frames} frames, and " +
                                       "NOT ONE PIXEL changed. It did not advance, so these frames say nothing about " +
                                       "the character. Do not read them as 'it stands still'.");
                        failures++;
                    }
                    else
                    {
                        Debug.Log($"[ANIM] {name}: CONTROL OK -- motion present in {moved.Count - deadPairs} of {moved.Count} frame pairs, {total} px total");
                    }

                    UnityEngine.Object.DestroyImmediate(podiumGo);
                    bundle.Unload(true);
                    Debug.Log($"[ANIM] {name}: {frames} frames written");
                }
                catch (Exception e)
                {
                    Debug.LogError($"[ANIM] {name}: {e}");
                    failures++;
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError("[ANIM] FATAL: " + e);
            failures++;
        }
        finally
        {
            EditorApplication.Exit(failures == 0 ? 0 : 1);
        }
    }
}
