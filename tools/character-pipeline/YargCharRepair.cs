// A .yargchar can be opened and edited here. IT CANNOT BE WRITTEN BACK, and
// this file's own run is what established that.
//
// The header used to open "PROOF: a .yargchar can be opened, modified and
// written back out, with no source file anywhere." That was written before the
// probe ran, and the probe disproved the second half: BackgroundHelper.Export
// reported success, exited 0, and wrote **2,552 bytes against the original's
// 6,357,076** -- an AssetBundle and a TextAsset, with 0 GameObjects, 0 meshes,
// 0 materials and no Avatar. The bundle builder packs from the AssetDatabase,
// and a prefab instantiated from a LOADED bundle references runtime objects
// with no asset path, so there is nothing on disk for it to pack. It packs
// nothing and reports OK; the file SIZE was the only thing that gave it away.
//
// The claim is left here in full because a stale claim in a header is exactly
// the kind that survives being read -- and three characters' only possible
// repair route hangs off it. The measurement is in
// docs/character-models.md, "A .yargchar can be opened and edited in the
// editor. It cannot be written back."
//
// What IS true: AssetBundle.LoadFromFile gives back the character prefab, it
// instantiates and edits like any other GameObject, and the podium shot
// harness in this same folder relies on exactly that every time it runs. Only
// the export is unavailable. Making it available would mean serialising those
// runtime meshes, materials, textures and the avatar back into project assets
// first, which is a far larger job than "edit it in the editor".
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
