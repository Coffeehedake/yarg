// TEMPORARY build-tooling. Not part of the fork; delete after use.
// Renders close-ups of both hands of an imported character, inside Unity, after the
// exporter has retargeted the materials and attached the controller. This is the
// view the Blender import cannot give: Unity's own humanoid skinning and URP materials.
// Needs a real GPU context, so run Unity WITHOUT -nographics when passing -renderDir.
using System.IO;
using UnityEngine;

public static class YargCharHandRender
{
    public static void Render(GameObject instance, string name, string dir, float animateSeconds)
    {
        Directory.CreateDirectory(dir);
        var animator = instance.GetComponent<Animator>();
        if (animator == null || animator.avatar == null || !animator.avatar.isHuman) return;

        if (animateSeconds > 0f && animator.runtimeAnimatorController != null)
        {
            animator.Rebind();
            animator.Update(animateSeconds);
        }

        var lightGo = new GameObject("__renderlight");
        var light = lightGo.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.4f;
        lightGo.transform.rotation = Quaternion.Euler(40f, 150f, 0f);
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.6f);

        var camGo = new GameObject("__rendercam");
        var cam = camGo.AddComponent<Camera>();
        cam.orthographic = true;
        cam.orthographicSize = 0.4f;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.4f, 0.4f, 0.45f);
        cam.nearClipPlane = 0.01f;
        cam.farClipPlane = 5f;

        var rt = new RenderTexture(600, 600, 24);
        cam.targetTexture = rt;

        foreach (var side in new[] { ("L", HumanBodyBones.LeftHand), ("R", HumanBodyBones.RightHand) })
        {
            var hand = animator.GetBoneTransform(side.Item2);
            if (hand == null) continue;
            // Centre on the middle of the hand and fingers, not the wrist.
            var tip = hand.position;
            if (hand.childCount > 0)
            {
                var sum = Vector3.zero;
                foreach (Transform c in hand) sum += c.position;
                tip = (hand.position + sum / hand.childCount) * 0.5f;
            }

            Debug.Log($"[YARGCHAR] {name} {side.Item1} hand at {hand.position} root {instance.transform.position} fwd {instance.transform.forward} tip {tip}");
            var views = new[]
            {
                ("front", instance.transform.forward),
                ("side", instance.transform.right),
                ("top", Vector3.down),
            };
            foreach (var v in views)
            {
                var toCam = -v.Item2;
                camGo.transform.position = tip + toCam * 1f;
                camGo.transform.rotation = Quaternion.LookRotation(v.Item2,
                    v.Item1 == "top" ? instance.transform.forward : Vector3.up);
                cam.Render();
                RenderTexture.active = rt;
                var tex = new Texture2D(600, 600, TextureFormat.RGB24, false);
                tex.ReadPixels(new Rect(0, 0, 600, 600), 0, 0);
                tex.Apply();
                RenderTexture.active = null;
                var tag = animateSeconds > 0f ? "anim" : "rest";
                File.WriteAllBytes(Path.Combine(dir, $"{name}_{tag}_{side.Item1}_{v.Item1}.png"),
                    tex.EncodeToPNG());
                Object.DestroyImmediate(tex);
            }
        }

        cam.targetTexture = null;
        rt.Release();
        Object.DestroyImmediate(rt);
        Object.DestroyImmediate(camGo);
        Object.DestroyImmediate(lightGo);
    }
}
