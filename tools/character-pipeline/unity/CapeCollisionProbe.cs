using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UniGLTF;
using UnityEditor;
using UnityEngine;
using UniVRM10;

namespace YARG.Editor
{
    /// <summary>
    /// Measures where a character's cloth actually GOES, by running the real animation through
    /// the real spring solver and reporting how far it penetrates the body.
    /// </summary>
    /// <remarks>
    /// WHY THIS EXISTS. Jay, after five failed fixes to Batman's cape: "we need a better tool
    /// for you to be able to analyze the collisions, since you can't see the animations."
    /// Every other tool in this pipeline reads the REST POSE out of the bundle. The bundle's
    /// rest pose is a T-pose; the game poses the character and simulates the cloth; and every
    /// conclusion drawn from the file all day was about a pose no player ever sees. The fixes
    /// were then graded by eye, off single frames of a moving thing, by the person who wanted
    /// a particular answer -- which produced one retraction of its own.
    ///
    /// WHAT IT DOES NOT DO, deliberately: it does not reimplement anything. `VoxIdle.anim` is
    /// 372 HUMANOID MUSCLE curves ("Chest Front-Back", "Left Arm Down-Up"), so turning it into
    /// bone rotations is Unity's humanoid retargeter, and a hand-rolled version of that would
    /// disagree with the engine somewhere nobody could see. This folder has already shipped a
    /// checker that was blind to its own library's tolerance. So: Unity samples the clip,
    /// UniVRM's own `Vrm10FastSpringboneRuntimeStandalone.Process(dt)` steps the cloth -- the
    /// same `UpdateFastSpringBoneJob` the notes have been quoting -- and this only measures.
    ///
    /// It runs in EDIT mode and needs no play mode, because that `Process(float deltaTime)` is
    /// a synchronous step with an explicit timestep rather than something a central service
    /// ticks.
    ///
    /// HOW IT MEASURES. Each sampled frame, every SkinnedMeshRenderer is baked to its posed
    /// geometry and split into GARMENT and BODY by the bone each vertex is weighted to -- the
    /// same rule the Python tools use, and the one whose absence once inflated a 4% reading to
    /// 63.5%. Body vertices go into a uniform grid. For each garment vertex the nearest body
    /// vertex is found and the penetration is
    ///
    ///     depth = -dot(garmentVertex - bodyVertex, bodyNormal)
    ///
    /// positive meaning the garment is behind the body's surface, i.e. INSIDE it. That is a
    /// nearest-VERTEX approximation of a signed distance field and it is stated as one: near a
    /// sharp edge it can be wrong by the local triangle size. It is not trying to resolve a
    /// millimetre, it is trying to answer "is an arm through this cape", and an arm is 200 mm.
    ///
    /// THE HARNESS CHECKS ITSELF BEFORE REPORTING, because a probe that reports zero for
    /// everything looks exactly like a clean result and this project produced five such zeros
    /// in one afternoon. It refuses to print a table unless: the character's baked height is
    /// plausible (1.0-2.5 m, which catches a local/world space mistake), some garment geometry
    /// was found, some body geometry was found, and the cloth actually MOVED between the first
    /// and last sampled frame. Each of those failures is reported as a failure, never as 0.0.
    /// </remarks>
    public static class CapeCollisionProbe
    {
        private const float CELL = 0.05f;   // grid cell, metres

        public static void Run()
        {
            string charPath = Arg("-charPath");
            string clipPath = Arg("-clipPath",
                "Assets/Resources/Animations/Vocals/Default/VoxIdle.anim");
            string outPath = Arg("-out", Path.Combine(Path.GetTempPath(), "cape-probe.csv"));
            // COMMA-SEPARATED, because a character's cloth is not always one
            // naming family. The first control run matched only "J_Sec" on Miku,
            // which left her HAIR -- a separate spring garment named
            // user_VRoid_...HairJoint-... -- classified as BODY, so her skirt
            // touching her hair was reported as 82 mm of body penetration. The
            // probe was right and the split was wrong.
            string[] match = (Arg("-garmentMatch", "cape") ?? "")
                .Split(',').Select(x => x.Trim()).Where(x => x.Length > 0).ToArray();
            int frames = int.Parse(Arg("-frames", "180"), CultureInfo.InvariantCulture);
            int every = int.Parse(Arg("-every", "10"), CultureInfo.InvariantCulture);
            float fps = float.Parse(Arg("-fps", "60"), CultureInfo.InvariantCulture);

            var log = new StringBuilder();
            void Say(string s) { Debug.Log("[CapeProbe] " + s); log.AppendLine(s); }

            if (string.IsNullOrEmpty(charPath) || !File.Exists(charPath))
            {
                Say("REFUSED: -charPath missing or not a file: " + charPath);
                Finish(log, outPath, 2);
                return;
            }

            var bundle = AssetBundle.LoadFromFile(charPath);
            if (bundle == null)
            {
                Say("REFUSED: AssetBundle.LoadFromFile returned null for " + charPath +
                    " -- this is the loader the GAME uses, so a null here is the game failing " +
                    "to load the character, not a probe problem.");
                Finish(log, outPath, 2);
                return;
            }

            GameObject prefab = bundle.LoadAllAssets<GameObject>().FirstOrDefault();
            if (prefab == null)
            {
                Say("REFUSED: no GameObject in the bundle");
                bundle.Unload(true);
                Finish(log, outPath, 2);
                return;
            }

            var go = UnityEngine.Object.Instantiate(prefab);
            go.name = "probe-subject";
            try
            {
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
                if (clip == null)
                {
                    Say("REFUSED: no AnimationClip at " + clipPath);
                    return;
                }
                var vrm = go.GetComponentInChildren<Vrm10Instance>();
                if (vrm == null)
                {
                    Say("REFUSED: no Vrm10Instance on this character, so it has no spring bones " +
                        "this probe can step");
                    return;
                }

                // touching Runtime constructs it, and with no provider component that means
                // Vrm10FastSpringboneRuntimeStandalone -- the synchronous path
                var runtime = vrm.Runtime;
                var springs = runtime.SpringBone;
                Say(string.Format("subject {0}, clip {1} ({2:0.00}s), spring runtime {3}",
                    Path.GetFileNameWithoutExtension(charPath), clip.name, clip.length,
                    springs.GetType().Name));

                var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>();
                if (smrs.Length == 0) { Say("REFUSED: no SkinnedMeshRenderer"); return; }

                float dt = 1f / fps;
                // settle: step the solver at the clip's first pose so the opening frames are
                // not a transient from instantiation being read as a finding
                clip.SampleAnimation(go, 0f);
                for (int i = 0; i < 60; i++) springs.Process(dt);

                var rows = new List<string>();
                var firstTails = new List<Vector3>();
                var lastTails = new List<Vector3>();
                // PENETRATION AT REST IS AUTHORED AND MUST BE SUBTRACTED. The
                // control proved this: Miku reads 103 mm of hair INSIDE her head
                // and 72 mm of skirt inside her hips, and both are correct
                // authoring -- a VRoid scalp sits inside the hair cap by design,
                // and a skirt's inner surface sits inside the hip. An absolute
                // depth therefore cannot tell a fault from a garment that is
                // simply attached. What is a fault is cloth going FURTHER in than
                // it rests, so every depth below is measured against this
                // vertex's own settled baseline.
                float[] baseline = null;
                float worstOverall = 0f;
                string worstWhere = "";
                int sampled = 0;
                float heightSeen = 0f;
                int garmentSeen = 0, bodySeen = 0;

                for (int f = 0; f <= frames; f++)
                {
                    float t = (f / fps) % Mathf.Max(0.0001f, clip.length);
                    clip.SampleAnimation(go, t);
                    springs.Process(dt);

                    if (f % every != 0) continue;
                    sampled++;

                    var garment = new List<(Vector3 p, string bone)>();
                    // baseline is keyed by position in this list, which is
                    // stable: the same renderers, the same meshes, the same
                    // vertex order every frame.
                    var body = new List<(Vector3 p, Vector3 n, string bone)>();
                    CollectPosed(smrs, match, garment, body, ref heightSeen);
                    garmentSeen = Mathf.Max(garmentSeen, garment.Count);
                    bodySeen = Mathf.Max(bodySeen, body.Count);
                    if (garment.Count == 0 || body.Count == 0) continue;

                    if (firstTails.Count == 0)
                        firstTails = garment.Select(g => g.p).ToList();
                    lastTails = garment.Select(g => g.p).ToList();

                    var grid = BuildGrid(body);
                    if (baseline == null)
                    {
                        baseline = new float[garment.Count];
                        for (int i = 0; i < garment.Count; i++)
                        {
                            baseline[i] = Nearest(grid, body, garment[i].p, out int b0)
                                ? -Vector3.Dot(garment[i].p - body[b0].p, body[b0].n)
                                : 0f;
                        }
                        int nz = 0; float bmax = 0f;
                        foreach (var v in baseline)
                            if (v > 0f) { nz++; if (v > bmax) bmax = v; }
                        Debug.Log(string.Format(CultureInfo.InvariantCulture,
                            "[CapeProbe] baseline at frame {0}: {1} of {2} garment vertices are " +
                            "already inside the body at rest, deepest {3:0.0} mm",
                            f, nz, baseline.Length, bmax * 1000f));
                        continue;   // the baseline frame is not itself a reading
                    }
                    var per = new Dictionary<string, (int n, float worst, string into)>();
                    for (int gi = 0; gi < garment.Count; gi++)
                    {
                        var g = garment[gi];
                        if (!Nearest(grid, body, g.p, out int bi)) continue;
                        var b = body[bi];
                        float raw = -Vector3.Dot(g.p - b.p, b.n);
                        float rest = gi < baseline.Length ? baseline[gi] : 0f;
                        float depth = raw - Mathf.Max(0f, rest);
                        if (depth <= 0f) continue;
                        per.TryGetValue(g.bone, out var cur);
                        if (cur.n == 0) cur = (0, 0f, b.bone);
                        cur.n++;
                        if (depth > cur.worst) { cur.worst = depth; cur.into = b.bone; }
                        per[g.bone] = cur;
                        if (depth > worstOverall)
                        {
                            worstOverall = depth;
                            worstWhere = string.Format("{0} into {1} at frame {2}",
                                g.bone, b.bone, f);
                        }
                    }
                    foreach (var kv in per.OrderByDescending(k => k.Value.worst))
                    {
                        rows.Add(string.Format(CultureInfo.InvariantCulture,
                            "{0},{1:0.000},{2},{3},{4},{5:0.00}",
                            f, t, kv.Key, kv.Value.into, kv.Value.n, kv.Value.worst * 1000f));
                    }
                }

                // ---- the harness checks itself before it reports anything
                var fails = new List<string>();
                if (heightSeen < 1.0f || heightSeen > 2.5f)
                    fails.Add(string.Format(CultureInfo.InvariantCulture,
                        "baked height is {0:0.000} m, which is not a character -- the posed " +
                        "vertices are probably in the wrong space", heightSeen));
                if (garmentSeen == 0)
                    fails.Add("no vertex is weighted to a bone matching '" + string.Join(",", match) +
                              "' -- nothing was measured as garment");
                if (bodySeen == 0) fails.Add("no body geometry was found");
                if (sampled == 0) fails.Add("no frame was sampled");
                float moved = 0f;
                for (int i = 0; i < Mathf.Min(firstTails.Count, lastTails.Count); i++)
                    moved = Mathf.Max(moved, Vector3.Distance(firstTails[i], lastTails[i]));
                if (firstTails.Count > 0 && moved < 0.001f)
                    fails.Add(string.Format(CultureInfo.InvariantCulture,
                        "the garment moved {0:0.00} mm between the first and last sampled " +
                        "frame -- the simulation is not running, so a clean result here would " +
                        "mean nothing", moved * 1000f));

                Say(string.Format(CultureInfo.InvariantCulture,
                    "sampled {0} frame(s); height {1:0.000} m; garment {2} verts; body {3} " +
                    "verts; garment moved {4:0.0} mm across the run",
                    sampled, heightSeen, garmentSeen, bodySeen, moved * 1000f));

                if (fails.Count > 0)
                {
                    Say("UNMEASURED, and that is not a clean result:");
                    foreach (var x in fails) Say("  - " + x);
                    Finish(log, outPath, 1);
                    return;
                }

                Say(string.Format(CultureInfo.InvariantCulture,
                    "deepest penetration {0:0.0} mm ({1})", worstOverall * 1000f,
                    string.IsNullOrEmpty(worstWhere) ? "none" : worstWhere));
                var csv = new StringBuilder();
                csv.AppendLine("frame,time,garment_bone,into_body_bone,vertices,depth_mm");
                foreach (var r in rows) csv.AppendLine(r);
                File.WriteAllText(outPath, csv.ToString());
                Say("wrote " + rows.Count + " row(s) to " + outPath);
                Finish(log, outPath, 0);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
                bundle.Unload(true);
            }
        }

        private static void CollectPosed(SkinnedMeshRenderer[] smrs, string[] match,
            List<(Vector3, string)> garment, List<(Vector3, Vector3, string)> body,
            ref float height)
        {
            float lo = float.MaxValue, hi = float.MinValue;
            foreach (var smr in smrs)
            {
                if (smr.sharedMesh == null) continue;
                var baked = new Mesh();
                smr.BakeMesh(baked, true);
                var verts = baked.vertices;
                var norms = baked.normals;
                var weights = smr.sharedMesh.boneWeights;
                var bones = smr.bones;
                var l2w = smr.transform.localToWorldMatrix;
                for (int i = 0; i < verts.Length; i++)
                {
                    var p = l2w.MultiplyPoint3x4(verts[i]);
                    var n = i < norms.Length
                        ? l2w.MultiplyVector(norms[i]).normalized : Vector3.up;
                    string bone = "?";
                    if (i < weights.Length)
                    {
                        int bi = weights[i].boneIndex0;
                        if (bi >= 0 && bi < bones.Length && bones[bi] != null)
                            bone = bones[bi].name;
                    }
                    if (p.y < lo) lo = p.y;
                    if (p.y > hi) hi = p.y;
                    bool isGarment = false;
                    foreach (var m in match)
                        if (bone.IndexOf(m, StringComparison.OrdinalIgnoreCase) >= 0)
                            { isGarment = true; break; }
                    if (isGarment)
                        garment.Add((p, bone));
                    else
                        body.Add((p, n, bone));
                }
                UnityEngine.Object.DestroyImmediate(baked);
            }
            if (hi > lo) height = Mathf.Max(height, hi - lo);
        }

        private static Dictionary<long, List<int>> BuildGrid(List<(Vector3 p, Vector3 n, string bone)> body)
        {
            var grid = new Dictionary<long, List<int>>();
            for (int i = 0; i < body.Count; i++)
            {
                long k = Key(body[i].p);
                if (!grid.TryGetValue(k, out var l)) grid[k] = l = new List<int>();
                l.Add(i);
            }
            return grid;
        }

        private static long Key(Vector3 p)
        {
            long x = (long) Mathf.Floor(p.x / CELL) + 4096;
            long y = (long) Mathf.Floor(p.y / CELL) + 4096;
            long z = (long) Mathf.Floor(p.z / CELL) + 4096;
            return (x << 40) | (y << 20) | z;
        }

        private static bool Nearest(Dictionary<long, List<int>> grid,
            List<(Vector3 p, Vector3 n, string bone)> body, Vector3 q, out int best)
        {
            best = -1;
            float bd = float.MaxValue;
            for (int r = 1; r <= 3 && best < 0; r++)   // widen until something is found
            {
                for (int dx = -r; dx <= r; dx++)
                for (int dy = -r; dy <= r; dy++)
                for (int dz = -r; dz <= r; dz++)
                {
                    long k = Key(q + new Vector3(dx * CELL, dy * CELL, dz * CELL));
                    if (!grid.TryGetValue(k, out var l)) continue;
                    foreach (int i in l)
                    {
                        float d = (body[i].p - q).sqrMagnitude;
                        if (d < bd) { bd = d; best = i; }
                    }
                }
            }
            return best >= 0;
        }

        private static string Arg(string name, string fallback = null)
        {
            var a = Environment.GetCommandLineArgs();
            for (int i = 0; i < a.Length - 1; i++)
                if (string.Equals(a[i], name, StringComparison.OrdinalIgnoreCase))
                    return a[i + 1];
            return fallback;
        }

        private static void Finish(StringBuilder log, string outPath, int code)
        {
            try
            {
                File.WriteAllText(Path.ChangeExtension(outPath, ".log"), log.ToString());
            }
            catch (Exception) { /* the console still has it */ }
            EditorApplication.Exit(code);
        }
    }
}
