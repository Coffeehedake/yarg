// TEMPORARY build-tooling. Not part of the fork; delete after use.
//
// Builds a minimal "character test stage" .yarground.
//
// WHY THIS EXISTS. A custom .yargchar is only ever shown if the VENUE supplies
// a slot for it. BackgroundManager.LoadCharacter bails on its first line:
//
//     if (!HasCharacter(venueRoot, VenueCharacter.CharacterType.Vocals))
//         return false;
//
// and then places the custom character into the PARENT of the placeholder it
// found, destroying the placeholder. Lipsync additionally needs a
// CharacterManager somewhere under the venue root. None of the community
// venues on Nexus carries any of that -- they predate the feature -- so a
// character can be installed, correct, and still never appear.
//
// The podium browser in Content Browser -> Character Select renders a
// .yargchar directly and does run the spring simulation, so it covers
// colliders, hair, textures and proportions. What it cannot show is a
// character PERFORMING: lipsync, blink, the animation controller. That is what
// this stage is for.
//
// Deliberately plain: a floor, two cameras, one light, the managers, and the
// vocalist slot. Nothing decorative, because anything that looks wrong on this
// stage is the character's fault, not the venue's.
//
// Run:
//   Unity.exe -batchmode -nographics -quit -projectPath <fork> \
//     -executeMethod YargVenueExporter.ExportTestStage -outDir <dir>

using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using YARG.Helpers;
using YARG.Venue;
using YARG.Venue.Characters;

public static class YargVenueExporter
{
    private const string VENUE_LAYER = "Venue";

    private static string Arg(string[] args, string name)
    {
        for (int i = 0; i < args.Length - 1; i++)
            if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        return null;
    }

    /// Private [SerializeField] members cannot be assigned directly, and these
    /// wirings are exactly the ones a venue breaks without, so a miss is an
    /// error rather than a silent null.
    private static bool SetPrivate(UnityEngine.Object target, string field, UnityEngine.Object value)
    {
        var so = new SerializedObject(target);
        var p = so.FindProperty(field);
        if (p == null)
        {
            Debug.LogError($"[YARGVENUE] {target.GetType().Name} has no serialized field '{field}'");
            return false;
        }
        p.objectReferenceValue = value;
        so.ApplyModifiedPropertiesWithoutUndo();
        return true;
    }

    private static void SetLayerRecursive(GameObject go, int layer)
    {
        go.layer = layer;
        foreach (Transform t in go.transform)
            SetLayerRecursive(t.gameObject, layer);
    }

    private static GameObject Child(GameObject parent, string name, Vector3 pos)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent.transform, false);
        go.transform.localPosition = pos;
        return go;
    }

    private static Camera MakeCamera(GameObject venue, string name, Vector3 pos, Vector3 lookAt,
                                     YARG.Venue.VenueCamera.CameraManager mgr, YARG.Venue.VenueCamera.CameraManager.CameraLocation loc, int layer)
    {
        var go = Child(venue, name, pos);
        var cam = go.AddComponent<Camera>();
        cam.cullingMask = 1 << layer;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.08f, 0.08f, 0.10f);
        cam.nearClipPlane = 0.05f;

        // The wiki is explicit about this one: a venue camera must not carry an
        // AudioListener, or it fights the game's own.
        var listener = go.GetComponent<AudioListener>();
        if (listener != null)
            UnityEngine.Object.DestroyImmediate(listener);

        go.transform.LookAt(lookAt);

        // The wiki asks for post-processing on, and the volume mask limited to
        // the Venue layer, or venue effects bleed onto the note highway.
        var urp = cam.GetUniversalAdditionalCameraData();
        if (urp != null)
        {
            urp.renderPostProcessing = true;
            urp.volumeLayerMask = 1 << layer;
        }

        var vc = go.AddComponent<YARG.Venue.VenueCamera.VenueCamera>();
        vc.CameraLocation = loc;
        vc.Camera = cam;
        SetPrivate(vc, "_cameraManager", mgr);
        return cam;
    }

    public static void ExportTestStage()
    {
        try
        {
            var args = Environment.GetCommandLineArgs();
            var outDir = Arg(args, "-outDir");
            if (string.IsNullOrEmpty(outDir))
            {
                Debug.LogError("[YARGVENUE] missing -outDir");
                EditorApplication.Exit(1);
                return;
            }
            Directory.CreateDirectory(outDir);

            int layer = LayerMask.NameToLayer(VENUE_LAYER);
            if (layer < 0)
            {
                Debug.LogError($"[YARGVENUE] this project has no '{VENUE_LAYER}' layer");
                EditorApplication.Exit(1);
                return;
            }

            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // The root MUST be named "Venue" per the venue-creation wiki.
            var venue = new GameObject("Venue");
            var bbm = venue.AddComponent<BundleBackgroundManager>();

            var charMgr = Child(venue, "CharacterManager", Vector3.zero)
                          .AddComponent<CharacterManager>();
            var camMgr = Child(venue, "CameraManager", Vector3.zero)
                         .AddComponent<YARG.Venue.VenueCamera.CameraManager>();
            Child(venue, "LightManager", Vector3.zero).AddComponent<LightManager>();

            // Both managers need to be pointed back at the venue root.
            SetPrivate(charMgr, "_venue", venue);
            SetPrivate(camMgr, "_venue", venue);

            // CameraManager._profile is a [SerializeField] VolumeProfile the
            // VENUE has to supply. Leaving it null threw on the first build:
            //
            //   NullReferenceException
            //     CameraManager.InitializePostProcessing() PostProcessing.cs:76
            //     CameraManager.OnChartLoaded()            CameraManager.cs:229
            //
            // CameraManager.cs:229 reaches _profile.TryGet<Bloom>() with no
            // null check, even though line 131 right above it computes
            // `_volumeSet = _profile != null`. The throw aborts the rest of
            // OnChartLoaded, so camera cuts never initialise either.
            const string PROFILE = "Assets/Authoring/Venue/Unique/VenueProfile.asset";
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(PROFILE);
            if (profile == null)
            {
                Debug.LogError($"[YARGVENUE] could not load {PROFILE}");
                EditorApplication.Exit(1);
                return;
            }
            SetPrivate(camMgr, "_profile", profile);

            // A floor, so the character is not floating in a void and so the
            // light has something to fall on.
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Floor";
            floor.transform.SetParent(venue.transform, false);
            floor.transform.localScale = new Vector3(8f, 0.2f, 8f);
            floor.transform.localPosition = new Vector3(0f, -0.1f, 0f);

            // On the +Z side, with the cameras, so the face is lit rather than
            // rim-lit from behind.
            var lightGo = Child(venue, "KeyLight", new Vector3(2f, 4f, 3f));
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.2f;
            light.transform.LookAt(new Vector3(0f, 1.2f, 0f));
            lightGo.AddComponent<VenueLight>();

            // THE POINT OF THE WHOLE FILE. The custom character is instantiated
            // into this placeholder's PARENT, so the anchor is what positions
            // it -- the placeholder itself is destroyed.
            var anchor = Child(venue, "VocalistAnchor", Vector3.zero);
            var vocalist = Child(anchor, "VocalistPlaceholder", Vector3.zero);
            vocalist.AddComponent<Animator>();
            var vcChar = vocalist.AddComponent<VenueCharacter>();
            vcChar.Type = VenueCharacter.CharacterType.Vocals;

            // Cameras sit on +Z looking back toward the origin.
            //
            // The first build put them on -Z and the vocalist showed his BACK.
            // LoadCharacter does Instantiate(character, existingParent), which
            // keeps the prefab's own world transform rather than adopting the
            // anchor's -- so rotating VocalistAnchor is not reliably able to
            // turn him round. Moving the cameras to the side he already faces
            // is, and it works whatever the character's own rotation is.
            var stageCam = MakeCamera(venue, "StageCamera", new Vector3(0f, 1.6f, 3.2f),
                                      new Vector3(0f, 1.1f, 0f), camMgr,
                                      YARG.Venue.VenueCamera.CameraManager.CameraLocation.Stage, layer);
            MakeCamera(venue, "VocalsCamera", new Vector3(-0.6f, 1.5f, 1.4f),
                       new Vector3(0f, 1.45f, 0f), camMgr,
                       YARG.Venue.VenueCamera.CameraManager.CameraLocation.Vocals, layer);

            // "DO NOT CHANGE the name of this!" says BundleBackgroundManager --
            // the field really is lowercase `mainCamera`.
            if (!SetPrivate(bbm, "mainCamera", stageCam))
            {
                Debug.LogError("[YARGVENUE] could not assign the main camera");
                EditorApplication.Exit(1);
                return;
            }

            SetLayerRecursive(venue, layer);

            var outPath = Path.Combine(outDir, "Character Test Stage.yarground");
            Debug.Log($"[YARGVENUE] exporting to {outPath}");
            BackgroundHelper.Export(venue, BackgroundHelper.ExportType.Background,
                                    Array.Empty<string>(), outPath);

            if (!File.Exists(outPath))
            {
                Debug.LogError("[YARGVENUE] export produced no file");
                EditorApplication.Exit(1);
                return;
            }
            Debug.Log($"[YARGVENUE] OK {new FileInfo(outPath).Length} bytes");
            EditorApplication.Exit(0);
        }
        catch (Exception e)
        {
            Debug.LogError($"[YARGVENUE] {e}");
            EditorApplication.Exit(1);
        }
    }
}
