// Which bones does the spring RUNTIME actually move?
//
// Three earlier versions of this reported 0 bones moved for Gadget Hackwrench
// and Harq Alkahana, whose springs are known to work, so each was a statement
// about the harness and not about any character. What they were missing comes
// from YARG's own VRMCharacter:
//
//   * the runtime must be INITIALISED, and the initialiser is async. In batch
//     mode there is no frame loop to finish it, so UniGLTF's ImmediateCaller
//     has to drive it.
//   * SetModelLevel must be called. It carries stopSpringBoneWriteback, and
//     without the call nothing is written back to the transforms at all.
//   * and the way to deflect a chain is the EXTERNAL FORCE that SetWind sets,
//     not shoving the root about: wind pushes every chain directly, where root
//     motion only moves what has inertia to lag.
//
// Displacement is measured RELATIVE TO THE ROOT, so a character that merely
// moves does not read as a character whose hair moves. The control is the
// whole point: until a known-good character registers motion, a zero here
// means nothing.
//
//   Unity.exe -batchmode -quit -projectPath <scratch> \
//     -executeMethod YargSpringProbe.Run -logFile <log> \
//     -yargchars "<path>|<Name>;..." -out <report.txt> [-bones "a,b,c"]
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using UniGLTF.SpringBoneJobs.Blittables;
using UnityEditor;
using UnityEngine;

public static class YargSpringProbe
{
    private static string Arg(string name, string fallback = null)
    {
        var a = Environment.GetCommandLineArgs();
        for (int i = 0; i < a.Length - 1; i++)
        {
            if (a[i] == name) return a[i + 1];
        }
        return fallback;
    }

    public static void Run()
    {
        var list = Arg("-yargchars");
        var outPath = Arg("-out");
        var wanted = (Arg("-bones") ?? "").Split(',')
            .Select(x => x.Trim()).Where(x => x.Length > 0).ToArray();
        var sb = new StringBuilder();
        void Say(string s) { Debug.Log("[SPRING] " + s); sb.AppendLine(s); }

        foreach (var entry in (list ?? "").Split(';').Where(x => x.Trim().Length > 0))
        {
            var bits = entry.Split('|');
            var file = bits[0];
            var name = bits.Length > 1 ? bits[1] : Path.GetFileNameWithoutExtension(file);
            AssetBundle bundle = null;
            GameObject ch = null;
            try
            {
                bundle = AssetBundle.LoadFromFile(file);
                if (bundle == null) { Say(name + ": bundle would not load"); continue; }
                var prefab = bundle.LoadAsset<GameObject>("assets/_character.prefab");
                if (prefab == null) { Say(name + ": no prefab"); continue; }
                ch = UnityEngine.Object.Instantiate(prefab);
                ch.SetActive(true);
                ch.transform.position = Vector3.zero;

                Component inst = null;
                foreach (var c in ch.GetComponents<Component>())
                {
                    if (c != null && c.GetType().Name == "Vrm10Instance") { inst = c; break; }
                }
                if (inst == null) { Say(name + ": no Vrm10Instance"); continue; }

                object runtime = inst.GetType().GetProperty("Runtime").GetValue(inst);
                object spring = runtime.GetType().GetProperty("SpringBone").GetValue(runtime);

                // 1. InitializeAsync sets m_instance and then builds the
                //    buffers ONLY `if (Application.isPlaying)`, which is false
                //    in a batch-mode editor. That one line is why every
                //    earlier version of this read zero for every character,
                //    including two whose springs work.
                var callerT = AppDomain.CurrentDomain.GetAssemblies()
                    .SelectMany(a => { try { return a.GetTypes(); } catch { return new Type[0]; } })
                    .FirstOrDefault(t => t.Name == "ImmediateCaller");
                var init = spring.GetType().GetMethod("InitializeAsync");
                if (init != null && callerT != null)
                {
                    var task = init.Invoke(spring, new object[] { inst, Activator.CreateInstance(callerT) });
                    var aw = task.GetType().GetMethod("GetAwaiter").Invoke(task, null);
                    var res = aw.GetType().GetMethod("GetResult");
                    if (res != null) res.Invoke(aw, null);
                }

                // 2. ReconstructSpringBone() is public, runs ConstructSpringBoneAsync
                //    through an ImmediateCaller and has no isPlaying guard, so
                //    it builds the buffers here.
                var recon = spring.GetType().GetMethod("ReconstructSpringBone");
                object built = recon != null ? recon.Invoke(spring, null) : null;
                Say(string.Format("{0}: ReconstructSpringBone -> {1}", name,
                                  built == null ? "no such method" : built.ToString()));

                // 3. model level AFTER the buffer exists -- SetModelLevel tests
                //    `m_bufferCombiner.Combined is FastSpringBoneCombinedBuffer`
                //    and silently does nothing before then, which is the second
                //    reason the earlier runs were quiet.
                var setModel = spring.GetType().GetMethod("SetModelLevel");
                // A STILL run claims that any displacement is a collider
                // ejecting a joint. That was FALSE while the wind blew in a
                // still run too: a 14 m/s external force swings every chain,
                // and Hatsune Miku read a 1748 mm "ejection" that was her
                // twintails in the wind. So a still run gets NO wind unless
                // -wind is passed explicitly, and the figure is printed either
                // way so the reader can see which run this was.
                var stillRun = Arg("-still") != null;
                var windArg = Arg("-wind");
                var wa = (windArg ?? (stillRun ? "0,0,0" : "14,0,6")).Split(',');
                var wind = new Vector3(float.Parse(wa[0]), float.Parse(wa[1]), float.Parse(wa[2]));
                var level = new BlittableModelLevel(externalForce: wind,
                    stopSpringBoneWriteback: false, supportsScalingAtRuntime: false);
                if (setModel != null)
                    setModel.Invoke(spring, new object[] { ((Component) inst).transform, level });
                Say(string.Format("{0}: wind {1}, writeback ON", name, wind));

                var all = ch.GetComponentsInChildren<Transform>(true);
                var pick = wanted.Length > 0
                    ? all.Where(t => wanted.Contains(t.name)).ToArray() : all;
                var before = pick.ToDictionary(t => t,
                    t => ch.transform.InverseTransformPoint(t.position));

                // The character has to MOVE. With gravity 0 and no effective
                // external force, a chain at rest correctly stays at rest, so
                // a still character makes every bone read rigid whether its
                // chains work or not. Spring bones react to their root being
                // carried about, so carry it about: that is what an idle
                // animation on a podium does.
                var proc = spring.GetType().GetMethod("Process", new[] { typeof(float) });
                float maxSeen = 0f;
                var peak = new Dictionary<Transform, float>();
                foreach (var kv in before) peak[kv.Key] = 0f;
                var rootStart = ch.transform.position;
                // -still 1 holds the character PERFECTLY still and lets the
                // solver settle. That measures a different thing from the
                // shake, and a thing nothing else can see: a joint that
                // starts inside a collider is EJECTED to its surface on the
                // first frames, so with no motion at all its displacement is
                // the overlap. A still run should read ~0 mm for every bone;
                // anything it reports is the collider pushing geometry away
                // from where the model was authored, permanently.
                var still = stillRun;
                if (still) Say(string.Format("{0}: STILL run -- no root motion and "
                    + "wind {1}, so any displacement is a collider ejecting a joint",
                    name, wind));
                for (int i = 0; i < 240; i++)
                {
                    if (!still)
                        ch.transform.position = rootStart
                            + new Vector3(Mathf.Sin(i * 0.25f) * 0.30f, 0f, 0f);
                    // STRAIGHT LINE, not an ellipse. A circular shake is
                    // chiral: it reaches one side of the character before the
                    // other, so the two tails deflect by different amounts
                    // however symmetric the rig is, and the harness invents an
                    // asymmetry to report.
                    if (proc != null) proc.Invoke(spring, new object[] { 1f / 60f });
                    // PEAK, not final: a chain that swings and settles back
                    // reads zero at the end, which is the same number a rigid
                    // one gives.
                    foreach (var kv in before)
                    {
                        if (kv.Key == null) continue;
                        var d = (ch.transform.InverseTransformPoint(kv.Key.position)
                                 - kv.Value).magnitude * 1000f;
                        if (d > peak[kv.Key]) peak[kv.Key] = d;
                        if (d > maxSeen) maxSeen = d;
                    }
                }
                ch.transform.position = rootStart;
                Say(string.Format("{0}: peak deflection during {1} {2:0.00} mm",
                                  name, still ? "a STILL run (should be ~0)" : "motion",
                                  maxSeen));

                var moved = new List<KeyValuePair<float, string>>();
                foreach (var kv in peak)
                {
                    if (kv.Key == null) continue;
                    moved.Add(new KeyValuePair<float, string>(kv.Value, kv.Key.name));
                }
                moved.Sort((a, b) => b.Key.CompareTo(a.Key));
                int alive = moved.Count(m => m.Key > 1f);
                Say(string.Format("{0}: {1} of {2} bone(s) moved more than 1 mm",
                                  name, alive, moved.Count));
                // Always show the top of the distribution, not only what clears
                // a threshold: "0 bones over 1 mm" reads the same whether the
                // chains are rigid or merely stiff, and those are different
                // answers.
                int shown = 0;
                foreach (var m in moved)
                {
                    if (wanted.Length == 0 && shown >= 12) break;
                    shown++;
                    Say(string.Format("        {0,-40} {1,9:0.000} mm{2}", m.Value, m.Key,
                                      m.Key > 1f ? "" : (m.Key > 0.001f ? "   (barely)" : "   <-- RIGID")));
                }
            }
            catch (Exception e)
            {
                Say(name + ": " + e.GetType().Name + ": " + e.Message
                    + (e.InnerException != null ? " / " + e.InnerException.Message : ""));
            }
            finally
            {
                if (ch != null) UnityEngine.Object.DestroyImmediate(ch);
                if (bundle != null) bundle.Unload(true);
            }
        }

        if (outPath != null) File.WriteAllText(outPath, sb.ToString());
        EditorApplication.Exit(0);
    }
}
