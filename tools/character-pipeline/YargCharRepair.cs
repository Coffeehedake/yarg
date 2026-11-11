// PROOF: a .yargchar can be opened, modified and written back out, with no
// source file anywhere.
//
// "No source located" has been treated as terminal for three characters.
// It is not. A .yargchar IS a Unity AssetBundle: AssetBundle.LoadFromFile
// gives back the character prefab, it can be instantiated and edited like any
// other GameObject, and BackgroundHelper.Export(GameObject, ...) writes a new
// bundle. The podium shot harness in this same folder already does the first
// half of that every time it runs.
//
// This probe does the whole round trip on Kasane Teto, whose bundle is the one
// of 66 with no AnimatorController and no AnimationClip, and reports what it
// found before and after.
using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using YARG.Helpers;

public static class YargCharRepair
{
    private static string Arg(string[] a, string n)
    {
        for (int i = 0; i < a.Length - 1; i++)
            if (string.Equals(a[i], n, StringComparison.OrdinalIgnoreCase)) return a[i + 1];
        return null;
    }

    public static void Run()
    {
        try
        {
            var args = Environment.GetCommandLineArgs();
            var src = Arg(args, "-src");
            var dst = Arg(args, "-dst");
            Debug.Log($"[REPAIR] src={src}");

            var bundle = AssetBundle.LoadFromFile(src);
            if (bundle == null) { Debug.LogError("[REPAIR] could not load bundle"); EditorApplication.Exit(1); return; }

            var names = bundle.GetAllAssetNames();
            Debug.Log($"[REPAIR] assets in bundle: {names.Length}");
            GameObject prefab = null;
            foreach (var n in names)
            {
                var go = bundle.LoadAsset<GameObject>(n);
                if (go != null) { prefab = go; Debug.Log($"[REPAIR] prefab asset: {n}"); break; }
            }
            if (prefab == null) { Debug.LogError("[REPAIR] no GameObject in bundle"); EditorApplication.Exit(1); return; }

            var inst = UnityEngine.Object.Instantiate(prefab);
            inst.name = prefab.name;

            var anim = inst.GetComponent<Animator>();
            Debug.Log($"[REPAIR] BEFORE: animator={(anim != null)} " +
                      $"controller={(anim != null && anim.runtimeAnimatorController != null ? anim.runtimeAnimatorController.name : "NULL")} " +
                      $"avatar={(anim != null && anim.avatar != null ? (anim.avatar.isHuman ? "human" : "non-human") : "NULL")}");

            var ctrl = Resources.Load<RuntimeAnimatorController>("Animations/Vocals/Default/DefaultController");
            if (ctrl == null) { Debug.LogError("[REPAIR] default controller not found"); EditorApplication.Exit(1); return; }
            if (anim != null) anim.runtimeAnimatorController = ctrl;
            Debug.Log($"[REPAIR] AFTER : controller={(anim != null && anim.runtimeAnimatorController != null ? anim.runtimeAnimatorController.name : "NULL")}");

            Directory.CreateDirectory(Path.GetDirectoryName(dst));
            BackgroundHelper.Export(inst, BackgroundHelper.ExportType.Character, Array.Empty<string>(), dst);

            if (!File.Exists(dst)) { Debug.LogError("[REPAIR] export produced no file"); EditorApplication.Exit(1); return; }
            Debug.Log($"[REPAIR] OK wrote {new FileInfo(dst).Length} bytes to {dst}");
            EditorApplication.Exit(0);
        }
        catch (Exception e)
        {
            Debug.LogError($"[REPAIR] {e}");
            EditorApplication.Exit(1);
        }
    }
}
