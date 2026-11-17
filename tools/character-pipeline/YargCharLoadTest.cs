// Does this .yargchar actually LOAD, and does it carry what the one it
// replaces carried?
//
//   Unity.exe -batchmode -nographics -quit -projectPath <scratch> \
//     -logFile <log> -executeMethod YargCharLoadTest.Run \
//     -yargchars "<path>|<Label>;<path>|<Label>" -out <report.txt>
//
// This is the acceptance check before an install. Every measurement this
// project makes on a bundle is made by reading its bytes with UnityPy, and a
// file can read perfectly and still fail in the engine -- a missing shader, an
// Avatar that is not humanoid, a prefab that throws on Instantiate. So the
// last check before replacing a working character is to make Unity itself open
// it, build the humanoid rig and walk the hierarchy.
//
// It prints the counts that a rebuild is most likely to lose silently:
// animation clips, humanoid bone mappings, skinned renderers, total bones, and
// VRM spring chains and joints. Run it on the OLD bundle and the NEW one in
// the same invocation and compare -- a count that drops is the question to
// answer before anything is installed.
//
// Written 2026-11-17 to replace a version that lived only inside a scratch
// Unity project and was deleted with it. It belongs in this folder, under
// version control, like the exporter beside it.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class YargCharLoadTest
{
    private static string Arg(string name, string fallback = null)
    {
        var a = Environment.GetCommandLineArgs();
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], name, StringComparison.OrdinalIgnoreCase))
                return a[i + 1];
        return fallback;
    }

    public static void Run()
    {
        var list = Arg("-yargchars");
        var outPath = Arg("-out");
        var sb = new StringBuilder();
        int failed = 0;

        void Say(string s) { Debug.Log("[LOADTEST] " + s); sb.AppendLine(s); }

        foreach (var pair in (list ?? "").Split(';').Where(p => p.Length > 0))
        {
            var bits = pair.Split('|');
            var path = bits[0];
            var label = bits.Length > 1 ? bits[1] : Path.GetFileNameWithoutExtension(path);
            AssetBundle bundle = null;
            GameObject go = null;
            try
            {
                if (!File.Exists(path)) { Say(label + ": FAILED -- no file at " + path); failed++; continue; }
                var bytes = new FileInfo(path).Length;
                bundle = AssetBundle.LoadFromFile(path);
                if (bundle == null) { Say(label + ": FAILED -- bundle would not load"); failed++; continue; }

                var prefab = bundle.LoadAllAssets<GameObject>().FirstOrDefault();
                if (prefab == null) { Say(label + ": FAILED -- no GameObject in bundle"); failed++; continue; }

                go = (GameObject) UnityEngine.Object.Instantiate(prefab);
                var anim = go.GetComponentInChildren<Animator>();
                var smrs = go.GetComponentsInChildren<SkinnedMeshRenderer>(true);
                var bones = new HashSet<Transform>();
                foreach (var smr in smrs)
                    foreach (var b in smr.bones)
                        if (b != null) bones.Add(b);

                int clips = bundle.LoadAllAssets<AnimationClip>().Length;
                int human = 0;
                bool isHuman = anim != null && anim.isHuman;
                if (isHuman)
                    foreach (HumanBodyBones hb in Enum.GetValues(typeof(HumanBodyBones)))
                        if (hb != HumanBodyBones.LastBone && anim.GetBoneTransform(hb) != null)
                            human++;

                // VRM spring chains are MonoBehaviours in these bundles; count
                // them and their joints by type name so this needs no
                // reference to the VRM assembly.
                int chains = 0, joints = 0;
                foreach (var mb in go.GetComponentsInChildren<MonoBehaviour>(true))
                {
                    if (mb == null) continue;
                    var tn = mb.GetType().Name;
                    if (tn.IndexOf("SpringBone", StringComparison.OrdinalIgnoreCase) < 0) continue;
                    chains++;
                    var f = mb.GetType().GetField("RootBones") ?? mb.GetType().GetField("rootBones");
                    if (f != null && f.GetValue(mb) is System.Collections.IEnumerable roots)
                        foreach (var r in roots)
                            if (r is Transform t) joints += t.GetComponentsInChildren<Transform>(true).Length;
                }

                // Animating it is part of the test: a rig that instantiates
                // and then throws on Rebind has not been shown to work.
                if (anim != null) { anim.Rebind(); anim.Update(0f); }

                Say(string.Format(
                    "{0}: OK  {1} bytes  {2} clips  {3} humanoid bones  {4} skinned meshes  "
                    + "{5} bones  {6} spring chains / {7} joints  humanoid={8}",
                    label, bytes, clips, human, smrs.Length, bones.Count,
                    chains, joints, isHuman));
            }
            catch (Exception e)
            {
                Say(label + ": FAILED -- " + e.GetType().Name + ": " + e.Message);
                failed++;
            }
            finally
            {
                if (go != null) UnityEngine.Object.DestroyImmediate(go);
                if (bundle != null) bundle.Unload(true);
            }
        }

        Say("ALL DONE, failed=" + failed);
        if (outPath != null) File.WriteAllText(outPath, sb.ToString());
        EditorApplication.Exit(failed == 0 ? 0 : 1);
    }
}
