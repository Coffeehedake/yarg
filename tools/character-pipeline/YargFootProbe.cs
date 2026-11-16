// Does the Animator PRESERVE a humanoid bone's position, or recompute it?
//
// This decides patch-versus-rebuild for Jessica Rabbit, whose left leg sits
// 92.4 mm below her right. Master Chief established that a mapped humanoid
// bone's rest ROTATION is discarded at runtime -- the Animator retargets from
// the Avatar, and writing all four rest structures did not survive. If the
// same is true of POSITIONS then patching her bundle is pointless and the fix
// has to happen in the build.
//
// But the yaw probe's hip-distance line hinted otherwise: both Mando and
// Spartan reported identical hip offsets before and after Rebind. That is a
// DISTANCE from the hips root, though, which cannot see a change that moves
// a whole chain. This asks for the world heights directly.
//
// Prints each leg bone's world Y at instantiate and after Rebind + Update, so
// a difference of zero means positions survive and a bundle patch is viable.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class YargFootProbe
{
    private static string Arg(string name)
    {
        var a = Environment.GetCommandLineArgs();
        for (int i = 0; i < a.Length - 1; i++)
            if (a[i] == name) return a[i + 1];
        return null;
    }

    private static readonly HumanBodyBones[] Want =
    {
        HumanBodyBones.LeftUpperLeg, HumanBodyBones.RightUpperLeg,
        HumanBodyBones.LeftLowerLeg, HumanBodyBones.RightLowerLeg,
        HumanBodyBones.LeftFoot, HumanBodyBones.RightFoot,
        HumanBodyBones.LeftToes, HumanBodyBones.RightToes,
        HumanBodyBones.LeftUpperArm, HumanBodyBones.RightUpperArm,
    };

    public static void Run()
    {
        var list = Arg("-yargchars");
        var outPath = Arg("-out");
        var sb = new StringBuilder();
        void Say(string s) { Debug.Log("[FOOT] " + s); sb.AppendLine(s); }

        foreach (var path in (list ?? "").Split(';').Where(p => p.Length > 0))
        {
            var name = Path.GetFileNameWithoutExtension(path);
            var bundle = AssetBundle.LoadFromFile(path);
            if (bundle == null) { Say(name + ": bundle would not load"); continue; }
            try
            {
                var prefab = bundle.LoadAllAssets<GameObject>().FirstOrDefault();
                if (prefab == null) { Say(name + ": no prefab"); continue; }
                var go = (GameObject) UnityEngine.Object.Instantiate(prefab);
                var anim = go.GetComponentInChildren<Animator>();
                if (anim == null || !anim.isHuman)
                {
                    Say(name + ": no humanoid Animator");
                    UnityEngine.Object.DestroyImmediate(go);
                    continue;
                }

                var before = new Dictionary<HumanBodyBones, float>();
                foreach (var b in Want)
                {
                    var t = anim.GetBoneTransform(b);
                    if (t != null) before[b] = t.position.y;
                }

                anim.Rebind();
                anim.Update(0f);

                Say(name + ":");
                Say(string.Format("    {0,-16} {1,10} {2,10} {3,10}",
                                  "bone", "before", "after", "moved mm"));
                foreach (var b in Want)
                {
                    var t = anim.GetBoneTransform(b);
                    if (t == null || !before.ContainsKey(b)) continue;
                    float a = t.position.y, bf = before[b];
                    Say(string.Format("    {0,-16} {1,10:0.0000} {2,10:0.0000} {3,10:0.00}",
                                      b, bf, a, (a - bf) * 1000f));
                }
                var lf = anim.GetBoneTransform(HumanBodyBones.LeftFoot);
                var rf = anim.GetBoneTransform(HumanBodyBones.RightFoot);
                if (lf != null && rf != null)
                    Say(string.Format("    foot height difference: {0:0.00} mm after Rebind",
                                      (rf.position.y - lf.position.y) * 1000f));
                UnityEngine.Object.DestroyImmediate(go);
            }
            finally { bundle.Unload(true); }
        }

        if (outPath != null) File.WriteAllText(outPath, sb.ToString());
        EditorApplication.Exit(0);
    }
}
