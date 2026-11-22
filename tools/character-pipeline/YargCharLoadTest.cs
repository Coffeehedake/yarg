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

    // A field on one VRM version is a property on the next, and a reflected read that only
    // tries one of them returns null and reads as "this character has no spring bones".
    private static object Member(object obj, Type t, string name)
    {
        var f = t.GetField(name);
        if (f != null) return f.GetValue(obj);
        var p = t.GetProperty(name);
        if (p != null) return p.GetValue(obj, null);
        return null;
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

                // SPRING CHAINS LIVE ON Vrm10Instance.SpringBone.Springs, and nowhere else.
                //
                // This used to count every MonoBehaviour whose type name contained
                // "SpringBone", which is the JOINT, COLLIDER and COLLIDER-GROUP components --
                // 179 of them on Batman. That number is identical before and after a chain is
                // dropped, because dropping a chain removes a list entry and leaves the
                // components in the file, so the one column that was supposed to show a lost
                // chain could not show one. It also looked for a `RootBones` field, which
                // VRM10 does not have, so the joint count was 0 on every character ever run.
                //
                // Reflected rather than referenced so this still needs no VRM assembly, and
                // `springComponents` is kept BESIDE the real counts: the old number was not
                // wrong about anything except its name, and a count that silently changes
                // meaning between versions of this file is worse than one that is explained.
                int chains = 0, joints = 0, springComponents = 0;
                foreach (var mb in go.GetComponentsInChildren<MonoBehaviour>(true))
                {
                    if (mb == null) continue;
                    if (mb.GetType().Name.IndexOf("SpringBone", StringComparison.OrdinalIgnoreCase) >= 0)
                        springComponents++;
                }
                foreach (var mb in go.GetComponentsInChildren<MonoBehaviour>(true))
                {
                    if (mb == null || mb.GetType().Name != "Vrm10Instance") continue;
                    var springRoot = Member(mb, mb.GetType(), "SpringBone");
                    if (springRoot == null) continue;
                    if (!(Member(springRoot, springRoot.GetType(), "Springs")
                          is System.Collections.IEnumerable sp))
                        continue;
                    foreach (var s in sp)
                    {
                        if (s == null) continue;
                        chains++;
                        if (Member(s, s.GetType(), "Joints") is System.Collections.IEnumerable js)
                            foreach (var j in js) if (j != null) joints++;
                    }
                }

                // Animating it is part of the test: a rig that instantiates
                // and then throws on Rebind has not been shown to work.
                if (anim != null) { anim.Rebind(); anim.Update(0f); }

                Say(string.Format(
                    "{0}: OK  {1} bytes  {2} clips  {3} humanoid bones  {4} skinned meshes  "
                    + "{5} bones  {6} spring chains / {7} joints  ({8} spring components)  "
                    + "humanoid={9}",
                    label, bytes, clips, human, smrs.Length, bones.Count,
                    chains, joints, springComponents, isHuman));
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
