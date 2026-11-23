// Measures the fault a player actually sees: BODY GEOMETRY EMERGING THROUGH CLOTH THAT IS DRAPED
// ON IT. Lives in tools/ for reference only; copy into a SCRATCH COPY of the Unity project.
//
//   Unity -batchmode -quit -projectPath <scratch> -executeMethod YargClothPenetration.Run
//         -yargchars "<path.yargchar>|<Name>" -shotDir <out>
//         [-frames 8] [-step 0.125] [-warmup 1.0] [-res 720] [-yaw 0]
//         [-drape 0.02] [-pushCloth 0.00]      <-- pushCloth is the synthetic positive
//
// ===================================================================================
// WHY NOT THE OBVIOUS TEST
// ===================================================================================
//
// The obvious instrument is: render the character, render it with the cape hidden, render the
// cape alone, and count pixels where the cape covers but the body is what you see. THAT TEST
// FLAGS THE WHOLE TORSO. A cape hangs BEHIND its wearer, so from the game camera a cape-only
// pass sits behind most of the silhouette -- chest, abdomen, legs -- and the body correctly wins
// every one of those pixels. The count comes back enormous and is almost entirely the cape being
// correctly behind a chest.
//
// The error underneath it is assuming a cape ENCLOSES a body. It does not: it covers the back
// and the shoulders and not the chest, so there is no "cloth before skin" rule to lean on and no
// way to get "where should the cloth be outside" from the cape's screen extent.
//
// PROXIMITY IS THE MISSING HALF. Where cloth is DRAPED on a body the two surfaces are
// millimetres apart; where a cape merely hangs behind a chest they are tens of centimetres
// apart. So:
//
//     fault pixel  =  cloth is on this ray
//                     AND body is on this ray
//                     AND the body is NEARER
//                     AND the surfaces are CLOSER than the drape distance
//
// That says where the cloth was supposed to be outside without naming a region, and it never
// asks whether cloth is inside a capsule -- which is what made the previous generation of cape
// instruments wrong for a yoke resting on a shoulder, since a yoke is inside the shoulder
// capsule BY DESIGN.
//
// -drape IS A THRESHOLD AND IS TREATED AS ONE. The count is reported at several values. If the
// answer moves with it, that is a finding about the instrument and must be said rather than
// averaged away or split down the middle.
//
// ===================================================================================
// THE CONTROLS, ALL FOUR, AND WHY EACH EXISTS
// ===================================================================================
//
//   SAME FRAME     Three renders of a moving character are three moments unless something pins
//                  them. The full and body-only passes must be pixel-identical EVERYWHERE THE
//                  CLOTH IS ABSENT; if they are not, the frames drifted and the difference is
//                  the drift.
//   NOT FROZEN     ...but that check also passes when both passes are static, because a frozen
//                  animator gives identical images for the wrong reason. So the full pass must
//                  also DIFFER between frames. A static floor once passed a presence check at
//                  43% fill.
//   DREW SOMETHING Cloth-only and body-only pixel counts are reported per frame. A cloth pass
//                  that renders nothing and a cloth that covers nothing are the same image.
//   NO PAINT       Every mask comes from a difference between passes or from the depth pass.
//                  Never from a colour chosen by this tool: a character wearing the marker
//                  colour turns the instrument into a measurement of their costume.
//
// THE BODY/CLOTH SPLIT IS THE AVATAR'S, NOT A NAME MATCH. Triangles dominantly weighted to a
// HUMANOID bone are the body; everything else is cloth, hair and props. Batman's cape bones are
// all non-humanoid, so the cape falls out of the humanoid map rather than out of a string match
// on "cape" -- his rig also contains fml_un_L_capeClav_a and fml_un_L_samurai_claviclePad_1, and
// a name matcher on this project has already found bones an earlier run of itself invented. The
// aux half's bone histogram is logged so a reader can see what else landed in it.
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

public static class YargClothPenetration
{
    private const int DIFF = 16;
    private const double NO_GEOM = 0.999;
    private static readonly double[] DRAPES = { 0.005, 0.010, 0.020, 0.040, 0.080 };

    private static int ProbeLayer = 30;

    private static string Arg(string[] a, string n)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], n, StringComparison.OrdinalIgnoreCase)) return a[i + 1];
        return null;
    }

    private sealed class Part
    {
        public GameObject Go;
        public MeshRenderer Mr;
        public bool IsBody;
    }

    private static readonly List<SkinnedMeshRenderer> Disabled = new List<SkinnedMeshRenderer>();
    private static readonly Dictionary<int, Material> DepthMats = new Dictionary<int, Material>();

    private static int PickProbeLayer()
    {
        for (int i = 30; i >= 8; i--)
            if (string.IsNullOrEmpty(LayerMask.LayerToName(i))) return i;
        throw new Exception("no unnamed layer free for the depth pass");
    }

    private static int CullOf(Material m)
    {
        if (m == null) return 2;
        if (m.HasProperty("_Cull")) return Mathf.RoundToInt(m.GetFloat("_Cull"));
        if (m.HasProperty("_M_CullMode")) return Mathf.RoundToInt(m.GetFloat("_M_CullMode"));
        return 2;
    }

    private static Material DepthMatFor(Material src, Shader sh)
    {
        int c = CullOf(src);
        if (!DepthMats.TryGetValue(c, out var m))
        {
            m = new Material(sh);
            m.SetFloat("_Cull", c);
            DepthMats[c] = m;
        }
        return m;
    }

    private static Color32[] Shoot(Camera cam, int res, out byte[] png)
    {
        var rt = new RenderTexture(res, res, 24, RenderTextureFormat.ARGB32);
        var old = cam.targetTexture;
        cam.targetTexture = rt;
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(res, res, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, res, res), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        cam.targetTexture = old;
        var px = tex.GetPixels32();
        png = tex.EncodeToPNG();
        UnityEngine.Object.DestroyImmediate(tex);
        rt.Release();
        UnityEngine.Object.DestroyImmediate(rt);
        return px;
    }

    private static double[] ShootDepth(Camera cam, int res, Shader sh, IEnumerable<Part> group)
    {
        var saved = new List<KeyValuePair<Part, Material[]>>();
        foreach (var p in group)
        {
            var orig = p.Mr.sharedMaterials;
            saved.Add(new KeyValuePair<Part, Material[]>(p, orig));
            int n = Math.Max(1, orig.Length);
            var mats = new Material[n];
            for (int i = 0; i < n; i++) mats[i] = DepthMatFor(i < orig.Length ? orig[i] : null, sh);
            p.Mr.sharedMaterials = mats;
        }
        var rt = new RenderTexture(res, res, 24, RenderTextureFormat.ARGB32);
        var oldT = cam.targetTexture; var oldF = cam.clearFlags;
        var oldB = cam.backgroundColor; var oldM = cam.cullingMask;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.white;
        cam.cullingMask = 1 << ProbeLayer;
        cam.targetTexture = rt;
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(res, res, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, res, res), 0, 0);
        tex.Apply();
        RenderTexture.active = null;
        cam.targetTexture = oldT; cam.clearFlags = oldF;
        cam.backgroundColor = oldB; cam.cullingMask = oldM;
        var px = tex.GetPixels32();
        UnityEngine.Object.DestroyImmediate(tex);
        rt.Release();
        UnityEngine.Object.DestroyImmediate(rt);
        foreach (var kv in saved) kv.Key.Mr.sharedMaterials = kv.Value;

        var d = new double[px.Length];
        for (int i = 0; i < px.Length; i++)
            d[i] = (px[i].r / 255.0) + (px[i].g / 255.0) / 255.0 + (px[i].b / 255.0) / 65025.0;
        return d;
    }

    private static int Differing(Color32[] a, Color32[] b, bool[] where, bool want)
    {
        int n = 0;
        for (int i = 0; i < a.Length; i++)
        {
            if (where != null && where[i] != want) continue;
            int dd = Math.Abs(a[i].r - b[i].r) + Math.Abs(a[i].g - b[i].g) + Math.Abs(a[i].b - b[i].b);
            if (dd > DIFF) n++;
        }
        return n;
    }

    private static bool[] IsHumanVert(SkinnedMeshRenderer smr, HashSet<Transform> human)
    {
        var mesh = smr.sharedMesh;
        var res = new bool[mesh.vertexCount];
        var bones = smr.bones;
        if (bones == null || bones.Length == 0) return res;
        var idx = new HashSet<int>();
        for (int i = 0; i < bones.Length; i++)
            if (bones[i] != null && human.Contains(bones[i])) idx.Add(i);
        if (idx.Count == 0) return res;
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
                if (bb >= 0 && idx.Contains(bb)) res[v] = true;
            }
        }
        finally
        {
            if (per.IsCreated) per.Dispose();
            if (w.IsCreated) w.Dispose();
        }
        return res;
    }

    private static Mesh Filter(Mesh src, bool[] keepVert, bool side)
    {
        var m = new Mesh();
        m.indexFormat = src.vertexCount > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16;
        m.vertices = src.vertices;
        var nr = src.normals; if (nr != null && nr.Length == src.vertexCount) m.normals = nr;
        var uv = src.uv; if (uv != null && uv.Length == src.vertexCount) m.uv = uv;
        m.subMeshCount = src.subMeshCount;
        for (int s = 0; s < src.subMeshCount; s++)
        {
            var t = src.GetTriangles(s);
            var keep = new List<int>(t.Length);
            for (int i = 0; i + 2 < t.Length; i += 3)
            {
                bool all = keepVert[t[i]] && keepVert[t[i + 1]] && keepVert[t[i + 2]];
                if (all == side) { keep.Add(t[i]); keep.Add(t[i + 1]); keep.Add(t[i + 2]); }
            }
            m.SetTriangles(keep, s, false);
        }
        m.RecalculateBounds();
        return m;
    }

    private static GameObject MakeGo(string name, Mesh m, SkinnedMeshRenderer src, Material[] mats)
    {
        var go = new GameObject(name);
        go.transform.SetPositionAndRotation(src.transform.position, src.transform.rotation);
        go.layer = ProbeLayer;
        go.AddComponent<MeshFilter>().sharedMesh = m;
        var mr = go.AddComponent<MeshRenderer>();
        mr.sharedMaterials = mats;
        mr.shadowCastingMode = ShadowCastingMode.Off;
        mr.receiveShadows = false;
        return go;
    }

    private static string F6(double d) { return d.ToString("0.000000", CultureInfo.InvariantCulture); }

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
            int res = int.TryParse(Arg(args, "-res"), out var rr) ? rr : 720;
            int frames = int.TryParse(Arg(args, "-frames"), out var ff) ? ff : 8;
            float step = float.TryParse(Arg(args, "-step"), out var ss) ? ss : 0.125f;
            float warmup = float.TryParse(Arg(args, "-warmup"), out var ww) ? ww : 1.0f;
            float yaw = float.TryParse(Arg(args, "-yaw"), out var yy) ? yy : 0f;
            float pushCloth = float.TryParse(Arg(args, "-pushCloth"), out var pc) ? pc : 0f;
            // THE PRIMARY SYNTHETIC POSITIVE: displace the UPPER ARM, not the garment.
            //
            // Pushing the cloth reproduces the APPEARANCE; moving the limb reproduces the
            // MECHANISM. An instrument keyed to garment displacement would pass a cloth-push
            // control and still be blind to a deltoid swinging through a mantle, which is the
            // only fault anyone has reported.
            //
            // UPPER ARM AND NOT SHOULDER, and that is specific to the subject: Power Girl is the
            // character whose cape FOLLOWS her shoulders -- 44% of her cape bones are parented
            // beneath her clavicles. Displace her shoulder and a large part of her cape travels
            // with it, so the emergence partly cancels itself. The upper arm sits below the
            // clavicle where no cape bone hangs, so the deltoid moves and the cape does not --
            // Batman's situation reproduced on the rig that is supposed to be immune to it.
            float pushArm = float.TryParse(Arg(args, "-pushArm"), out var pa) ? pa : 0f;

            QualitySettings.antiAliasing = 0;
            int hi = Array.IndexOf(QualitySettings.names, "High");
            if (hi >= 0) QualitySettings.SetQualityLevel(hi, true);

            EditorSceneManager.OpenScene("Assets/Scenes/CharacterSelect.unity", OpenSceneMode.Single);
            var dm = UnityEngine.Object.FindFirstObjectByType<CharacterDisplayManager>();
            var so = new SerializedObject(dm);
            var podiumPrefab = so.FindProperty("_displayPrefab").objectReferenceValue as GameObject;
            var selected = so.FindProperty("_selectedLocation").objectReferenceValue as Transform;
            var cam = Camera.main;

            var rp = GraphicsSettings.currentRenderPipeline;
            Debug.Log($"[CLOTH] pipeline={(rp == null ? "BUILT-IN" : rp.GetType().Name)} res={res} " +
                      $"frames={frames} pushCloth={pushCloth}m pushArm={pushArm}m");
            ProbeLayer = PickProbeLayer();
            cam.cullingMask |= (1 << ProbeLayer);
            var depthShader = Shader.Find("Hidden/YargPartDepth");
            if (depthShader == null)
            {
                Debug.LogError("[CLOTH] Hidden/YargPartDepth NOT FOUND -- no depth pass, so no test.");
                EditorApplication.Exit(1);
                return;
            }
            DepthMats.Clear();

            json.Append("{\n  \"res\": ").Append(res).Append(",\n  \"push_cloth\": ").Append(F6(pushCloth))
                .Append(",\n  \"characters\": [\n");
            bool first = true;

            foreach (var entry in list.Split(';'))
            {
                if (string.IsNullOrWhiteSpace(entry)) continue;
                var bits = entry.Split('|');
                var file = bits[0].Trim();
                var name = bits.Length > 1 ? bits[1].Trim() : Path.GetFileNameWithoutExtension(file);
                var safe = name.Replace(" ", "");
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
                    if (podium.Light != null) podium.Light.color = Color.white;

                    bundle = AssetBundle.LoadFromFile(file);
                    if (bundle == null) throw new Exception("could not load " + file);
                    var prefab = bundle.LoadAsset<GameObject>(BackgroundHelper.CHARACTER_PREFAB_PATH.ToLowerInvariant());
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
                    catch (Exception e) { Debug.Log($"[CLOTH] {name}: VRM init skipped: {e.GetType().Name}"); }

                    var anim = ch.GetComponent<Animator>();
                    var human = new HashSet<Transform>();
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
                                if (t != null) human.Add(t);
                            }
                    }
                    if (human.Count == 0)
                        Debug.LogWarning($"[CLOTH] {name}: no humanoid map -- body and cloth cannot be " +
                                         "separated, so this character is UNMEASURED rather than clean.");

                    var perFrame = new List<string>();
                    Color32[] prevFull = null;
                    int motion = 0;
                    int bodyTris = 0, clothTris = 0;

                    for (int f = 0; f < frames; f++)
                    {
                        if (f > 0 && anim != null) anim.Update(step);

                        // After Update, before baking: the animator rewrites bone transforms every
                        // frame, so the displacement has to be re-applied each time or it silently
                        // only affects frame 0.
                        if (Math.Abs(pushArm) > 1e-6f && anim != null && anim.isHuman)
                        {
                            var chest = anim.GetBoneTransform(HumanBodyBones.UpperChest)
                                        ?? anim.GetBoneTransform(HumanBodyBones.Chest)
                                        ?? anim.GetBoneTransform(HumanBodyBones.Spine);
                            foreach (var hb in new[] { HumanBodyBones.LeftUpperArm, HumanBodyBones.RightUpperArm })
                            {
                                var t = anim.GetBoneTransform(hb);
                                if (t == null || chest == null) continue;
                                var dir = (t.position - chest.position).normalized;
                                t.position += dir * pushArm;
                            }
                        }

                        var parts = new List<Part>();
                        Disabled.Clear();
                        bodyTris = clothTris = 0;
                        foreach (var smr in ch.GetComponentsInChildren<SkinnedMeshRenderer>())
                        {
                            if (!smr.enabled || smr.sharedMesh == null) continue;
                            var baked = new Mesh();
                            smr.BakeMesh(baked, true);
                            var hv = IsHumanVert(smr, human);
                            var bm = Filter(baked, hv, true);
                            var cm = Filter(baked, hv, false);
                            int bt = 0, ct = 0;
                            for (int s = 0; s < bm.subMeshCount; s++) bt += bm.GetTriangles(s).Length / 3;
                            for (int s = 0; s < cm.subMeshCount; s++) ct += cm.GetTriangles(s).Length / 3;
                            bodyTris += bt; clothTris += ct;
                            if (bt > 0) parts.Add(new Part { Go = MakeGo("__body_" + smr.name, bm, smr, smr.sharedMaterials), IsBody = true });
                            if (ct > 0) parts.Add(new Part { Go = MakeGo("__cloth_" + smr.name, cm, smr, smr.sharedMaterials), IsBody = false });
                            smr.enabled = false;
                            Disabled.Add(smr);
                        }
                        foreach (var p in parts) p.Mr = p.Go.GetComponent<MeshRenderer>();
                        var body = parts.FindAll(p => p.IsBody);
                        var cloth = parts.FindAll(p => !p.IsBody);

                        // THE SYNTHETIC POSITIVE: push the cloth AWAY from the camera so the body
                        // emerges through it. Same mechanism as a shoulder poking through a mantle
                        // -- body outside cloth, surfaces close -- built on a character that is not
                        // the one being judged.
                        if (Math.Abs(pushCloth) > 1e-6f)
                            foreach (var p in cloth)
                                p.Go.transform.position += cam.transform.forward * pushCloth;

                        void Only(IEnumerable<Part> on)
                        {
                            foreach (var p in parts) p.Mr.enabled = false;
                            foreach (var p in on) p.Mr.enabled = true;
                        }

                        Only(parts);
                        var F = Shoot(cam, res, out var fpng);
                        Only(body);
                        var B = Shoot(cam, res, out _);
                        Only(cloth);
                        var C = Shoot(cam, res, out _);
                        Only(Array.Empty<Part>());
                        var E = Shoot(cam, res, out _);

                        Only(body);
                        var dBody = ShootDepth(cam, res, depthShader, body);
                        Only(cloth);
                        var dCloth = ShootDepth(cam, res, depthShader, cloth);

                        int clothPx = Differing(C, E, null, true);
                        int bodyPx = Differing(B, E, null, true);

                        // CONTROL: full and body-only must agree wherever the cloth is absent.
                        var clothAbsent = new bool[dCloth.Length];
                        for (int i = 0; i < dCloth.Length; i++) clothAbsent[i] = dCloth[i] >= NO_GEOM;
                        int drift = Differing(F, B, clothAbsent, true);

                        if (prevFull != null) motion += Differing(prevFull, F, null, true);
                        prevFull = F;

                        var counts = new int[DRAPES.Length];
                        var denom = new int[DRAPES.Length];
                        bool[] worst = null;
                        for (int di = 0; di < DRAPES.Length; di++)
                        {
                            var mask = new bool[dBody.Length];
                            for (int i = 0; i < dBody.Length; i++)
                            {
                                if (dBody[i] >= NO_GEOM || dCloth[i] >= NO_GEOM) continue;
                                double gap = dCloth[i] - dBody[i];
                                if (gap <= 0) continue;                       // cloth is in front: fine
                                if (gap * cam.farClipPlane > DRAPES[di]) continue;  // not draped
                                denom[di]++;
                                int dd = Math.Abs(F[i].r - B[i].r) + Math.Abs(F[i].g - B[i].g) + Math.Abs(F[i].b - B[i].b);
                                if (dd <= DIFF) { counts[di]++; if (di == 2) { if (worst == null) worst = new bool[dBody.Length]; worst[i] = true; } }
                            }
                        }

                        var sb = new StringBuilder();
                        for (int di = 0; di < DRAPES.Length; di++)
                        {
                            if (di > 0) sb.Append(", ");
                            sb.Append("{\"drape\": ").Append(F6(DRAPES[di]))
                              .Append(", \"fault_px\": ").Append(counts[di])
                              .Append(", \"draped_px\": ").Append(denom[di])
                              .Append(", \"frac\": ").Append(denom[di] > 0 ? F6((double) counts[di] / denom[di]) : "null")
                              .Append("}");
                        }
                        perFrame.Add("        {\"frame\": " + f + ", \"cloth_px\": " + clothPx +
                                     ", \"body_px\": " + bodyPx + ", \"drift_px\": " + drift +
                                     ", \"drapes\": [" + sb + "]}");

                        if (f == 0)
                            File.WriteAllBytes(Path.Combine(outDir, $"{safe}_f000_full.png"), fpng);
                        if (worst != null && f == frames / 2)
                        {
                            var tex = new Texture2D(2, 2);
                            tex.LoadImage(fpng);
                            var px = tex.GetPixels32();
                            for (int i = 0; i < px.Length && i < worst.Length; i++)
                                if (worst[i]) px[i] = new Color32(255, 40, 0, 255);
                            tex.SetPixels32(px); tex.Apply();
                            File.WriteAllBytes(Path.Combine(outDir, $"{safe}_f{f:000}_penetration.png"), tex.EncodeToPNG());
                            UnityEngine.Object.DestroyImmediate(tex);
                        }

                        foreach (var p in parts) UnityEngine.Object.DestroyImmediate(p.Go);
                        foreach (var smr in Disabled) if (smr != null) smr.enabled = true;
                    }

                    bool measurable = human.Count > 0 && bodyTris > 0 && clothTris > 0;
                    Debug.Log($"[CLOTH] {name}: bodyTris={bodyTris} clothTris={clothTris} " +
                              $"measurable={measurable} motion={motion}px");
                    if (motion == 0 && frames > 1)
                    {
                        Debug.LogError($"[CLOTH] {name}: THE FULL PASS NEVER CHANGED across {frames} frames. " +
                                       "A frozen animator makes the same-frame check pass for the wrong " +
                                       "reason, so every number here is about the harness.");
                        failures++;
                    }
                    if (!measurable)
                        Debug.LogWarning($"[CLOTH] {name}: UNMEASURED, not clean -- " +
                                         (human.Count == 0 ? "no humanoid map. " : "") +
                                         (clothTris == 0 ? "no non-humanoid geometry, so no cloth. " : "") +
                                         (bodyTris == 0 ? "no humanoid geometry. " : ""));

                    json.Append("      \"measurable\": ").Append(measurable ? "true" : "false")
                        .Append(",\n      \"body_tris\": ").Append(bodyTris)
                        .Append(",\n      \"cloth_tris\": ").Append(clothTris)
                        .Append(",\n      \"motion_px\": ").Append(motion)
                        .Append(",\n      \"frames_data\": [\n").Append(string.Join(",\n", perFrame))
                        .Append("\n      ]\n    }");
                    Debug.Log($"[CLOTH] {name}: done");
                }
                catch (Exception e)
                {
                    Debug.LogError($"[CLOTH] {name}: {e}");
                    failures++;
                    json.Append("      \"measurable\": false,\n      \"error\": \"")
                        .Append(e.GetType().Name).Append("\",\n      \"frames_data\": []\n    }");
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
            Debug.LogError("[CLOTH] FATAL: " + e);
            failures++;
        }
        finally
        {
            try
            {
                if (outDir != null && json.Length > 0)
                    File.WriteAllText(Path.Combine(outDir, "cloth_penetration.json"), json.ToString());
            }
            catch (Exception e) { Debug.LogError("[CLOTH] json: " + e); }
            EditorApplication.Exit(failures == 0 ? 0 : 1);
        }
    }
}
