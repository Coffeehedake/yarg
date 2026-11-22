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
            // DOES PENETRATION HAPPEN MID-GAP? Collision moves a spring JOINT and never the
            // sheet between two of them, so "add more chains" predicts that the deep vertices
            // are the ones FAR from any joint. That prediction is cheap to test and expensive
            // to assume: it is the whole justification for building ~100 new bones.
            string gapOut = Arg("-gapOut");

            // -useAnimator drives the character's OWN Animator (Attract, else Idle) instead of
            // sampling -clipPath. That is what the character-select podium does, and it is a
            // DIFFERENT ANIMATION from VoxIdle.anim -- which means every cape number produced
            // before this flag existed describes a clip nobody was looking at when the fault
            // was reported.
            bool useAnimator = Array.IndexOf(Environment.GetCommandLineArgs(),
                                             "-useAnimator") >= 0;

            // -zoneMatch splits the gap table by WHICH PART OF THE BODY is being penetrated.
            // Without it, "penetration happens far from a joint" is a statement about the whole
            // garment, and the fault actually being chased may be the exception: on Batman the
            // forearm-gauntlet contact is ~90 of ~2400 rows, 1.5% of the total, so the headline
            // table can be dominated entirely by penetration somewhere else.
            // RENDERING FROM INSIDE THE PROBE, because the alternative renderer drives the
            // character's own Animator with an Attract/Idle trigger while this samples
            // VoxIdle.anim directly. Those are different animations, so "frame 240" in a shot
            // taken that way would not be the frame measured here, and the picture would answer
            // a question nobody asked. Rendered from this loop the shot IS the measured moment:
            // same clip time, same spring state, same posed mesh.
            string shotDir = Arg("-shotDir");
            string shotBone = Arg("-shotBone");
            int shotRes = int.Parse(Arg("-shotRes", "900"), CultureInfo.InvariantCulture);
            // 0.42 m from a forearm fills the frame with skin. The question is whether the cape
            // crosses the limb, which needs the limb, the cape and the gap between them in one
            // picture.
            float shotDist = float.Parse(Arg("-shotDist", "0.95"), CultureInfo.InvariantCulture);
            var shotFrames = new HashSet<int>((Arg("-shotFrames", "") ?? "")
                .Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(x => int.Parse(x.Trim(), CultureInfo.InvariantCulture)));

            string[] zone = (Arg("-zoneMatch", "") ?? "")
                .Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(z => z.Trim().ToLowerInvariant())
                .Where(z => z.Length > 0)
                .ToArray();

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

                // THE SPRING BUFFER IS NEVER BUILT IN EDIT MODE, and this is why the first
                // version of this probe produced byte-identical numbers for two bundles that
                // differ by 41 colliders. Vrm10FastSpringboneRuntimeStandalone.InitializeAsync
                // reads, in full:
                //
                //     m_instance = instance;
                //     // NOTE: FastSpringBoneService は UnitTest などでは動作しない
                //     if (Application.isPlaying) await ConstructSpringBoneAsync(awaitCaller);
                //
                // so outside play mode Process(dt) steps an empty combiner and the cloth is
                // carried rigidly by its parent bones. ReconstructSpringBone() is the library's
                // own synchronous construction path and is on the interface.
                springs.ReconstructSpringBone();
                springs.Process(1f / fps);      // forces ReconstructIfDirty on the combiner

                int bufColliders = 0, bufLogics = 0, bufSprings = 0;
                if (springs is Vrm10FastSpringboneRuntimeStandalone st &&
                    st.m_bufferCombiner.Combined != null)
                {
                    bufColliders = st.m_bufferCombiner.Combined.Colliders.Length;
                    bufLogics = st.m_bufferCombiner.Combined.Logics.Length;
                    bufSprings = st.m_bufferCombiner.Combined.Springs.Length;
                }
                int sceneColliders = go.GetComponentsInChildren<VRM10SpringBoneCollider>().Length;
                Say(string.Format(
                    "spring buffer: {0} spring(s), {1} logic(s), {2} collider slot(s); the " +
                    "character carries {3} collider component(s)",
                    bufSprings, bufLogics, bufColliders, sceneColliders));
                if (bufLogics == 0 || bufColliders == 0)
                {
                    Say("REFUSED: the spring buffer is empty, so nothing would be simulated and " +
                        "any number below would describe cloth carried rigidly by its parent " +
                        "bones. That is exactly what this probe reported before the A/B caught " +
                        "it.");
                    return;
                }
                // NAME THE DRIVER, NOT JUST THE CLIP THAT HAPPENS TO BE LOADED. This line read
                // "clip VoxIdle (10.55s)" on the first -useAnimator run, where VoxIdle drove
                // nothing -- a label from the wrong animation on a report about another one,
                // which is exactly how two days of measurements came to describe a clip nobody
                // was watching.
                Say(string.Format("subject {0}, driven by {1}, spring runtime {2}",
                    Path.GetFileNameWithoutExtension(charPath),
                    useAnimator
                        ? "the character's OWN Animator (what the character-select podium plays)"
                        : string.Format(CultureInfo.InvariantCulture, "clip {0} ({1:0.00}s)",
                                        clip.name, clip.length),
                    springs.GetType().Name));

                var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>();
                if (smrs.Length == 0) { Say("REFUSED: no SkinnedMeshRenderer"); return; }

                // the live joint transforms, for the mid-gap test. Taken from the spring
                // definitions rather than by name, so a chain this pipeline invented is
                // counted exactly like one the author drew.
                var jointTf = new List<Transform>();
                foreach (var sp in vrm.SpringBone.Springs)
                    foreach (var jt in sp.Joints)
                        if (jt != null && jt.transform != null) jointTf.Add(jt.transform);
                if (gapOut != null && jointTf.Count == 0)
                {
                    Say("REFUSED: -gapOut was asked for and this character has no spring joints " +
                        "to measure distance to, so every reading would be a harness artefact.");
                    return;
                }

                float dt = 1f / fps;
                // settle: step the solver at the clip's first pose so the opening frames are
                // not a transient from instantiation being read as a finding
                Animator animator = null;
                float animClipLen = 0f;
                float animSpeed = 1f;
                if (useAnimator)
                {
                    animator = go.GetComponentInChildren<Animator>();
                    if (animator == null)
                    {
                        Say("REFUSED: -useAnimator was asked for and this character has no " +
                            "Animator, so every frame would be identical and the cape would " +
                            "read as perfectly still.");
                        Finish(log, outPath, 2);
                        return;
                    }
                    bool trig = false;
                    foreach (var pm in animator.parameters)
                    {
                        if (pm.type != AnimatorControllerParameterType.Trigger) continue;
                        if (pm.name == "Attract" || pm.name == "Idle")
                        {
                            animator.SetTrigger(pm.name);
                            Say("animator trigger: " + pm.name);
                            trig = true;
                            break;
                        }
                    }
                    if (!trig)
                    {
                        Say("NOTE: no Attract or Idle trigger on this Animator; it will run " +
                            "whatever its default state is. Say so rather than implying the " +
                            "podium animation was reproduced.");
                    }
                    animator.Rebind();
                    animator.Update(0f);
                    // What is actually playing, and for how long. Without this the window below
                    // is a number nobody has justified.
                    var info = animator.GetCurrentAnimatorClipInfo(0);
                    foreach (var ci in info)
                    {
                        if (ci.clip == null) continue;
                        if (ci.clip.length > animClipLen) animClipLen = ci.clip.length;
                        Say(string.Format(CultureInfo.InvariantCulture,
                            "animator layer 0 plays {0} ({1:0.00}s, weight {2:0.00})",
                            ci.clip.name, ci.clip.length, ci.weight));
                    }
                    if (info.Length == 0)
                    {
                        Say("NOTE: the Animator reports no clip on layer 0 at frame 0, so the "
                            + "coverage check below cannot run. Treat the window as unjustified.");
                    }
                    animSpeed = animator.speed <= 0f ? 1f : animator.speed;
                }
                else
                {
                    clip.SampleAnimation(go, 0f);
                }
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
                var jointPos = new List<Vector3>();
                var gapAll = new List<float>();
                var gapPen = new List<(float dist, float depth, string into)>();
                // The probe instantiates into whatever scene happens to be open, which has
                // no camera and no light of its own. Both are made here, because a render that
                // silently came out black would look exactly like a cape that is not clipping.
                Camera shotCam = null;
                Transform shotTarget = null;
                var shotMade = new List<string>();
                var shotBlank = new List<string>();
                var shotSame = new List<string>();
                var shotPrev = new Dictionary<string, string>();
                if (shotDir != null)
                {
                    Directory.CreateDirectory(shotDir);
                    var camGo = new GameObject("probe-cam");
                    shotCam = camGo.AddComponent<Camera>();
                    shotCam.clearFlags = CameraClearFlags.SolidColor;
                    shotCam.backgroundColor = new Color(0.12f, 0.13f, 0.15f, 1f);
                    shotCam.fieldOfView = 38f;
                    shotCam.nearClipPlane = 0.01f;
                    shotCam.farClipPlane = 50f;
                    // Two lights, from opposite sides. One directional light leaves the far side
                    // of a BLACK cape unlit against a dark background, which is the one thing
                    // this picture must not do.
                    var rigs = new[] { new Vector3(35f, -40f, 0f), new Vector3(15f, 150f, 0f) };
                    var power = new[] { 1.5f, 0.9f };
                    for (int li = 0; li < rigs.Length; li++)
                    {
                        var lgo = new GameObject("probe-light");
                        var lt = lgo.AddComponent<Light>();
                        lt.type = LightType.Directional;
                        lt.intensity = power[li];
                        lt.color = Color.white;
                        lgo.transform.rotation = Quaternion.Euler(rigs[li]);
                    }
                    if (!string.IsNullOrEmpty(shotBone))
                    {
                        shotTarget = go.GetComponentsInChildren<Transform>(true)
                            .FirstOrDefault(tr => tr.name.ToLowerInvariant()
                                                    .Contains(shotBone.ToLowerInvariant()));
                        if (shotTarget == null)
                        {
                            Say("REFUSED: -shotBone " + shotBone + " matches no transform on " +
                                "this character, so every close-up would be aimed at the origin " +
                                "and would show a clean cape by construction.");
                            Finish(log, outPath, 2);
                            return;
                        }
                        Say("shots aimed at " + shotTarget.name);
                    }
                }

                float worstOverall = 0f;
                string worstWhere = "";
                int sampled = 0;
                float heightSeen = 0f;
                int garmentSeen = 0, bodySeen = 0;

                for (int f = 0; f <= frames; f++)
                {
                    float t = f / fps;
                    if (useAnimator)
                    {
                        animator.Update(dt);
                    }
                    else
                    {
                        t = t % Mathf.Max(0.0001f, clip.length);
                        clip.SampleAnimation(go, t);
                    }
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

                    if (shotCam != null && shotFrames.Contains(f))
                    {
                        float h = Mathf.Max(1.0f, heightSeen);
                        var tags = new List<string>();
                        var ats = new List<Vector3>();
                        var looks = new List<Vector3>();
                        var fovs = new List<float>();
                        if (shotTarget != null)
                        {
                            Vector3 bp = shotTarget.position;
                            // Three directions, because one view cannot separate "the cape is
                            // through the fin" from "the cape is in front of the fin".
                            tags.Add("outboard");
                            ats.Add(bp + new Vector3(-shotDist, shotDist * 0.10f, 0f));
                            looks.Add(bp); fovs.Add(34f);
                            tags.Add("front");
                            ats.Add(bp + new Vector3(0f, shotDist * 0.10f, shotDist));
                            looks.Add(bp); fovs.Add(34f);
                            tags.Add("above");
                            ats.Add(bp + new Vector3(0f, shotDist, shotDist * 0.14f));
                            looks.Add(bp); fovs.Add(34f);
                        }
                        // THE WIDE VIEW IS FRAMED FROM THE SUBJECT'S OWN BOUNDS, not from the
                        // origin. Aimed at the origin it photographed the floor: every wide shot
                        // came back byte-identical across frames while the close-ups all
                        // differed, because the character is not at the origin and nothing in
                        // the picture was moving.
                        Vector3 lo = body[0].p, hi = body[0].p;
                        for (int bi2 = 1; bi2 < body.Count; bi2++)
                        {
                            lo = Vector3.Min(lo, body[bi2].p);
                            hi = Vector3.Max(hi, body[bi2].p);
                        }
                        Vector3 mid = (lo + hi) * 0.5f;
                        float reach = Mathf.Max(0.5f, (hi - lo).magnitude);
                        tags.Add("wide");
                        ats.Add(mid + new Vector3(reach * 0.55f, reach * 0.12f, reach * 1.05f));
                        looks.Add(mid); fovs.Add(40f);

                        for (int vi2 = 0; vi2 < tags.Count; vi2++)
                        {
                            shotCam.transform.position = ats[vi2];
                            shotCam.transform.LookAt(looks[vi2]);
                            shotCam.fieldOfView = fovs[vi2];
                            Color32[] px;
                            var png = Shoot(shotCam, shotRes, out px);
                            string nm = string.Format(CultureInfo.InvariantCulture,
                                "f{0:0000}-{1}.png", f, tags[vi2]);
                            File.WriteAllBytes(Path.Combine(shotDir, nm), png);
                            shotMade.Add(nm);
                            // IS THE SUBJECT EVEN IN FRAME? A near-empty picture is the failure
                            // that reads as good news, so it is counted rather than left to the
                            // eye: pixels differing from the background colour.
                            int lit = 0;
                            var bg = shotCam.backgroundColor;
                            int br = (int) (bg.r * 255f), bgg = (int) (bg.g * 255f),
                                bb2 = (int) (bg.b * 255f);
                            for (int pi = 0; pi < px.Length; pi++)
                            {
                                if (Mathf.Abs(px[pi].r - br) + Mathf.Abs(px[pi].g - bgg)
                                    + Mathf.Abs(px[pi].b - bb2) > 18) lit++;
                            }
                            float fill = 100f * lit / Mathf.Max(1, px.Length);
                            Say(string.Format(CultureInfo.InvariantCulture,
                                "  shot {0}  subject fills {1:0.0}% of frame", nm, fill));
                            if (fill < 2f)
                            {
                                shotBlank.Add(string.Format(CultureInfo.InvariantCulture,
                                    "{0} ({1:0.0}%)", nm, fill));
                            }
                            // A picture that is BYTE-IDENTICAL to the same view at a different
                            // frame is photographing something that is not moving, which on an
                            // animating character means it is not photographing the character.
                            // "Something is in frame" cannot catch that; only a comparison can.
                            string sig = System.Convert.ToBase64String(
                                System.Security.Cryptography.MD5.Create().ComputeHash(png));
                            if (shotPrev.TryGetValue(tags[vi2], out var was) && was == sig)
                            {
                                shotSame.Add(nm);
                            }
                            shotPrev[tags[vi2]] = sig;
                        }
                    }

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
                    // joint positions for this frame, read once rather than per vertex
                    if (gapOut != null)
                    {
                        jointPos.Clear();
                        foreach (var tr in jointTf) jointPos.Add(tr.position);
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

                        // THE CONTROL IS EVERY VERTEX, NOT ONLY THE DEEP ONES. "penetrating
                        // vertices sit 80 mm from a joint" says nothing until the same figure
                        // for the whole garment is beside it.
                        if (gapOut != null)
                        {
                            float dmin = float.MaxValue;
                            for (int k = 0; k < jointPos.Count; k++)
                            {
                                float d2 = (jointPos[k] - g.p).sqrMagnitude;
                                if (d2 < dmin) dmin = d2;
                            }
                            dmin = Mathf.Sqrt(dmin);
                            gapAll.Add(dmin);
                            if (depth > 0f) gapPen.Add((dmin, depth, b.bone));
                        }

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

                // THE SAMPLE WINDOW MUST COVER THE CLIP, and this is the check that was not
                // here when it mattered. Every arm measured on 2026-11-21 ran -frames 240 at
                // 60 fps against a 10.55 s (633 frame) clip, so it saw the first 38% of the
                // animation and reported a clean number. Arm C's peak read 125.1 mm over that
                // window and 275.0 mm over the whole clip -- its worst moment is at frame 520,
                // which no run reached -- and one arm's improvement changed SIGN when the rest
                // of the clip was included. A truncated window is not a sparse measurement, it
                // is a different measurement, and nothing said so.
                float covered = frames / Mathf.Max(0.0001f, fps);
                if (useAnimator)
                {
                    // The Animator DOES know what it is playing, so this check runs after all.
                    // It is the same check the 2026-11-21 retraction added for clip mode, and it
                    // exists because a window chosen for speed rode along as if it were the
                    // setup and cost two results their sign.
                    float need = animClipLen / Mathf.Max(0.0001f, animSpeed);
                    if (animClipLen <= 0f)
                    {
                        Say(string.Format(CultureInfo.InvariantCulture,
                            "COVERAGE: {0:0.00}s at {1:0} fps, against an Animator that named no "
                            + "clip. The coverage check could NOT run -- treat the window as "
                            + "unjustified rather than as passed.", covered, fps));
                    }
                    else if (covered < need * 0.98f)
                    {
                        fails.Add(string.Format(CultureInfo.InvariantCulture,
                            "-frames {0} at {1:0} fps covers {2:0.00}s of a {3:0.00}s animator "
                            + "state ({4:0}%). Sampling 38% of a clip on 2026-11-21 changed the "
                            + "SIGN of two results. Pass -frames {5} or more.",
                            frames, fps, covered, need, 100f * covered / need,
                            Mathf.CeilToInt(need * fps)));
                    }
                    else
                    {
                        Say(string.Format(CultureInfo.InvariantCulture,
                            "COVERAGE: {0:0.00}s of a {1:0.00}s animator state ({2:0}%).",
                            covered, need, 100f * covered / need));
                    }
                }
                else if (covered < clip.length * 0.98f)
                    fails.Add(string.Format(CultureInfo.InvariantCulture,
                        "-frames {0} at {1:0} fps covers {2:0.00}s of a {3:0.00}s clip ({4:0}%). " +
                        "The cape's largest excursions need not be in the part you sampled, so " +
                        "this cannot be compared with anything. Pass -frames {5:0} or more.",
                        frames, fps, covered, clip.length, 100f * covered / clip.length,
                        Mathf.Ceil(clip.length * fps)));

                // and enough samples WITHIN the window to catch an extreme
                if (sampled > 0 && sampled < 40)
                    fails.Add(string.Format(CultureInfo.InvariantCulture,
                        "only {0} frame(s) sampled. 13 samples of this clip put the peak at " +
                        "125.1 mm where 127 put it at 275.0 mm; a swinging garment needs dense " +
                        "sampling. Lower -every.", sampled));
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

                if (gapOut != null && gapAll.Count > 0)
                {
                    // Bin by distance to the nearest spring joint. The ALL column is the
                    // control: if the deep vertices are no further from a joint than the
                    // garment is on average, the sheet-between-joints story is wrong and more
                    // chains will not help, however reasonable the mechanism sounds.
                    float[] edges = { 0f, 0.02f, 0.04f, 0.06f, 0.08f, 0.10f, 0.15f, 9f };
                    var nAll = new int[edges.Length];
                    var nPen = new int[edges.Length];
                    var dSum = new float[edges.Length];
                    var dMax = new float[edges.Length];
                    int Bin(float d)
                    {
                        for (int i = 0; i < edges.Length; i++) if (d < edges[i]) return i;
                        return edges.Length - 1;
                    }
                    foreach (var d in gapAll) nAll[Bin(d)]++;
                    foreach (var (d, dep, _into) in gapPen)
                    {
                        int b = Bin(d);
                        nPen[b]++; dSum[b] += dep;
                        if (dep > dMax[b]) dMax[b] = dep;
                    }
                    var g = new StringBuilder();
                    g.AppendLine("dist_to_nearest_joint_mm,all_vertex_frames,penetrating," +
                                 "pct_penetrating,mean_depth_mm,max_depth_mm");
                    Say("mid-gap test -- distance from each garment vertex to its nearest " +
                        "spring joint:");
                    Say(string.Format("{0,-14} {1,10} {2,12} {3,8} {4,11} {5,10}",
                        "band (mm)", "all", "penetrating", "pct", "mean depth", "max depth"));
                    for (int i = 0; i < edges.Length; i++)
                    {
                        if (nAll[i] == 0 && nPen[i] == 0) continue;
                        string band = i == 0 ? "< 20"
                            : i == edges.Length - 1 ? ">= 150"
                            : string.Format("{0:0}-{1:0}", edges[i - 1] * 1000f, edges[i] * 1000f);
                        float pct = nAll[i] > 0 ? 100f * nPen[i] / nAll[i] : 0f;
                        float mean = nPen[i] > 0 ? dSum[i] / nPen[i] : 0f;
                        Say(string.Format(CultureInfo.InvariantCulture,
                            "{0,-14} {1,10} {2,12} {3,7:0.0}% {4,10:0.0} {5,9:0.0}",
                            band, nAll[i], nPen[i], pct, mean * 1000f, dMax[i] * 1000f));
                        g.AppendLine(string.Format(CultureInfo.InvariantCulture,
                            "{0},{1},{2},{3:0.00},{4:0.00},{5:0.00}",
                            band, nAll[i], nPen[i], pct, mean * 1000f, dMax[i] * 1000f));
                    }
                    File.WriteAllText(gapOut, g.ToString());
                    Say(string.Format(CultureInfo.InvariantCulture,
                        "{0} joint(s) measured against; {1} garment vertex-frames, {2} of them " +
                        "penetrating; wrote {3}",
                        jointTf.Count, gapAll.Count, gapPen.Count, gapOut));

                    // THE SAME TABLE FOR ONE ZONE ONLY. This is the measurement that decides
                    // whether more spring chains can reach a fault at all: a chain protects what
                    // comes near its joints, so if a zone's penetration sits at the same
                    // distances as the garment as a whole, more chains move it, and if it sits
                    // close to joints that already exist, they will not. The ALL column stays the
                    // control -- every garment vertex-frame, in the zone or not.
                    if (zone.Length > 0)
                    {
                        var zPen = new int[edges.Length];
                        var zSum = new float[edges.Length];
                        var zMax = new float[edges.Length];
                        int zTot = 0;
                        foreach (var (d, dep, into) in gapPen)
                        {
                            string lo = (into ?? "").ToLowerInvariant();
                            if (!zone.Any(k => lo.Contains(k))) continue;
                            int zb = Bin(d);
                            zPen[zb]++; zSum[zb] += dep; zTot++;
                            if (dep > zMax[zb]) zMax[zb] = dep;
                        }
                        string zonePath = gapOut.EndsWith(".csv", StringComparison.OrdinalIgnoreCase)
                            ? gapOut.Substring(0, gapOut.Length - 4) + "-zone.csv"
                            : gapOut + "-zone.csv";
                        var z = new StringBuilder();
                        z.AppendLine("dist_to_nearest_joint_mm,all_vertex_frames," +
                                     "zone_penetrating,pct_of_all,mean_depth_mm,max_depth_mm");
                        Say(string.Format(CultureInfo.InvariantCulture,
                            "zone test -- penetration into [{0}] only, by distance to the "
                            + "nearest spring joint ({1} of {2} penetrating vertex-frames):",
                            string.Join("|", zone), zTot, gapPen.Count));
                        Say(string.Format("{0,-14} {1,10} {2,12} {3,8} {4,11} {5,10}",
                            "band (mm)", "all", "zone pen", "pct", "mean depth", "max depth"));
                        for (int i = 0; i < edges.Length; i++)
                        {
                            if (nAll[i] == 0 && zPen[i] == 0) continue;
                            string band = i == 0 ? "< 20"
                                : i == edges.Length - 1 ? ">= 150"
                                : string.Format("{0:0}-{1:0}", edges[i - 1] * 1000f,
                                                edges[i] * 1000f);
                            float pct = nAll[i] > 0 ? 100f * zPen[i] / nAll[i] : 0f;
                            float mean = zPen[i] > 0 ? zSum[i] / zPen[i] : 0f;
                            Say(string.Format(CultureInfo.InvariantCulture,
                                "{0,-14} {1,10} {2,12} {3,7:0.00}% {4,10:0.0} {5,9:0.0}",
                                band, nAll[i], zPen[i], pct, mean * 1000f, zMax[i] * 1000f));
                            z.AppendLine(string.Format(CultureInfo.InvariantCulture,
                                "{0},{1},{2},{3:0.0000},{4:0.00},{5:0.00}",
                                band, nAll[i], zPen[i], pct, mean * 1000f, zMax[i] * 1000f));
                        }
                        if (zTot == 0)
                        {
                            Say("REFUSED to draw a conclusion from the zone table: no penetrating"
                                + " vertex-frame matched [" + string.Join("|", zone) + "], so"
                                + " this is a spelling result and not a measurement. Check the"
                                + " into_body_bone column of the -out CSV for the real names.");
                        }
                        File.WriteAllText(zonePath, z.ToString());
                        Say("wrote " + zonePath);
                    }
                }
                if (shotDir != null)
                {
                    Say(string.Format("wrote {0} shot(s) to {1}", shotMade.Count, shotDir));
                    if (shotMade.Count == 0)
                    {
                        Say("REFUSED: -shotDir was given and no frame matched -shotFrames, so " +
                            "nothing was rendered. The frames have to be ones this run SAMPLES: " +
                            "with -every " + every + " that means multiples of " + every + ".");
                    }
                    else if (shotSame.Count > 0)
                    {
                        Say("WARNING: " + shotSame.Count + " shot(s) are byte-identical to the " +
                            "same view at an earlier frame -- " + string.Join(", ", shotSame) +
                            ". On an animating character that means the camera is pointed at " +
                            "something static, not at the subject. Do not read those as frames " +
                            "where nothing is happening.");
                    }
                    else if (shotBlank.Count > 0)
                    {
                        Say("WARNING: " + shotBlank.Count + " of " + shotMade.Count + " shot(s) " +
                            "are nearly empty -- " + string.Join(", ", shotBlank) + ". Those " +
                            "show no subject and must not be read as a clean cape.");
                    }
                }
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
                    bool isGarment = false;
                    foreach (var m in match)
                        if (bone.IndexOf(m, StringComparison.OrdinalIgnoreCase) >= 0)
                            { isGarment = true; break; }
                    if (isGarment)
                    {
                        garment.Add((p, bone));
                    }
                    else
                    {
                        // The height check is a check on the SPACE the vertices are in, so it
                        // must be taken over the body alone. Taken over everything it is the
                        // bounding box of the character plus whatever the cloth is doing, and
                        // the same Batman then measured 1.886 m in one run and 2.025 m in
                        // another purely because his cape flew higher. A self-check that moves
                        // with the thing it is checking is not a check.
                        if (p.y < lo) lo = p.y;
                        if (p.y > hi) hi = p.y;
                        body.Add((p, n, bone));
                    }
                }
                UnityEngine.Object.DestroyImmediate(baked);
            }
            if (hi > lo) height = Mathf.Max(height, hi - lo);
        }

        /// <summary>
        /// Render the camera to a PNG and hand back the pixels, so the caller can check the
        /// picture is not empty. Same method as YargCharAnim's, which has produced real shots
        /// out of this project before.
        /// </summary>
        private static byte[] Shoot(Camera cam, int res, out Color32[] px)
        {
            var rt = new RenderTexture(res, res, 24, RenderTextureFormat.ARGB32);
            var old = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            tex.Apply();
            RenderTexture.active = null;
            cam.targetTexture = old;
            px = tex.GetPixels32();
            var png = tex.EncodeToPNG();
            UnityEngine.Object.DestroyImmediate(tex);
            rt.Release();
            UnityEngine.Object.DestroyImmediate(rt);
            return png;
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
