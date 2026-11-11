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
            // Record every bone's local transform so we can log what the animator
            // changed. A finger mesh stretched into a long strip means a bone moved
            // or scaled, not just rotated.
            var before = new System.Collections.Generic.Dictionary<Transform, (Vector3, Vector3, Quaternion)>();
            foreach (var t in instance.GetComponentsInChildren<Transform>())
                before[t] = (t.localPosition, t.localScale, t.localRotation);
            var lh = animator.GetBoneTransform(HumanBodyBones.LeftHand);
            var restDist = new System.Collections.Generic.Dictionary<Transform, float>();
            if (lh != null)
                foreach (var t in lh.GetComponentsInChildren<Transform>())
                    restDist[t] = (t.position - lh.position).magnitude;
            animator.Rebind();
            animator.Update(animateSeconds);
            if (lh != null)
            {
                var far = new System.Collections.Generic.List<(float, string)>();
                foreach (var kv in restDist)
                {
                    float d1 = (kv.Key.position - lh.position).magnitude;
                    far.Add((Mathf.Abs(d1 - kv.Value), $"{kv.Key.name} (parent {(kv.Key.parent != null ? kv.Key.parent.name : "-")}): {kv.Value * 100f:F1}cm -> {d1 * 100f:F1}cm from hand"));
                }
                far.Sort((a, b) => b.Item1.CompareTo(a.Item1));
                Debug.Log($"[YARGCHAR] HANDDIST {name}: {far.Count} transforms under LeftHand");
                for (int i = 0; i < Mathf.Min(10, far.Count); i++)
                    Debug.Log($"[YARGCHAR] HANDDIST   {far[i].Item2}");
            }
            var rows = new System.Collections.Generic.List<(float, string)>();
            foreach (var kv in before)
            {
                var t = kv.Key;
                if (t == null) continue;
                var (p0, s0, r0) = kv.Value;
                float dp = (t.localPosition - p0).magnitude;
                float ds = (t.localScale - s0).magnitude;
                float dr = Quaternion.Angle(t.localRotation, r0);
                rows.Add((dp * 1000f + ds * 1000f + dr, $"{t.name}: dPos {dp * 1000f:F1}mm dScale {ds:F3} dRot {dr:F1}deg"));
            }
            rows.Sort((a, b) => b.Item1.CompareTo(a.Item1));
            for (int i = 0; i < Mathf.Min(14, rows.Count); i++)
                Debug.Log($"[YARGCHAR] ANIMDELTA {name}: {rows[i].Item2}");
        }

        if (animateSeconds <= 0f)
        {
            // Skin matrix = bone.localToWorld * bindpose. At rest, relative to the
            // renderer, it should be the identity. Report how far each bone is from
            // that, in position (mm) as well as rotation: bind_check.py only sees rotation.
            var rows2 = new System.Collections.Generic.List<(float, string)>();
            foreach (var smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                if (smr.sharedMesh == null) continue;
                var bp = smr.sharedMesh.bindposes;
                var bones = smr.bones;
                for (int i = 0; i < bones.Length && i < bp.Length; i++)
                {
                    if (bones[i] == null) continue;
                    var m = smr.transform.worldToLocalMatrix * bones[i].localToWorldMatrix * bp[i];
                    float mm = new Vector3(m.m03, m.m13, m.m23).magnitude * 1000f;
                    float deg = Quaternion.Angle(m.rotation, Quaternion.identity);
                    float sc = (m.lossyScale - Vector3.one).magnitude;
                    if (mm > 2f || deg > 2f || sc > 0.01f)
                        rows2.Add((mm + deg, $"{smr.name}/{bones[i].name}: {mm:F1}mm {deg:F1}deg scaleDev {sc:F3}"));
                }
            }
            rows2.Sort((a, b) => b.Item1.CompareTo(a.Item1));
            Debug.Log($"[YARGCHAR] SKINDEV {name}: {rows2.Count} bone/renderer pairs off");
            // One renderer only (the one that carries the hands), every finger bone, so the
            // thumbs do not crowd out the rest of the list.
            string only = null;
            foreach (var r in rows2) { only = r.Item2.Substring(0, r.Item2.IndexOf('/')); break; }
            var seen = new System.Collections.Generic.HashSet<string>();
            foreach (var r in rows2)
            {
                var slash = r.Item2.IndexOf('/');
                if (r.Item2.Substring(0, slash) != only && !r.Item2.StartsWith(only)) { }
                var bone = r.Item2.Substring(slash + 1);
                if (!seen.Add(bone)) continue;
                Debug.Log($"[YARGCHAR] SKINDEV {name}: {bone}");
            }
        }

        // Unity moves the bones on Animator.Update but does not re-skin the mesh in
        // an editor pass (the first animated renders showed a T-pose mesh around
        // moved bones). Bake each skinned mesh to a static one at the current pose
        // and render that instead.
        var baked = new System.Collections.Generic.List<GameObject>();
        var hidden = new System.Collections.Generic.List<SkinnedMeshRenderer>();
        if (animateSeconds > 0f)
        {
            foreach (var smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                if (!smr.enabled || smr.sharedMesh == null) continue;
                var m = new Mesh();
                smr.BakeMesh(m, true);
                {
                    // Vertices that carry a LEFT finger weight yet end up far from the left hand
                    // in the animated pose are the strips. Print every influence on them.
                    var lhand = animator.GetBoneTransform(HumanBodyBones.LeftHand);
                    var mesh = smr.sharedMesh;
                    var v1 = m.vertices;
                    var bn = smr.bones;
                    var bpv = mesh.GetBonesPerVertex();
                    var all = mesh.GetAllBoneWeights();
                    var handLocal = smr.transform.InverseTransformPoint(lhand.position);
                    int off = 0, bad = 0, maxInf = 0, printed = 0;
                    var cnt = new System.Collections.Generic.Dictionary<string, int>();
                    for (int i = 0; i < bpv.Length; i++)
                    {
                        int n = bpv[i];
                        maxInf = Mathf.Max(maxInf, n);
                        bool leftFinger = false;
                        for (int k = 0; k < n; k++)
                        {
                            var bnm = bn[all[off + k].boneIndex].name;
                            if (all[off + k].weight > 0.05f && bnm.Contains("_L_") &&
                                (bnm.Contains("Thumb") || bnm.Contains("Index") || bnm.Contains("Mid") || bnm.Contains("Ring") || bnm.Contains("Pinky")))
                                leftFinger = true;
                        }
                        if (leftFinger && (v1[i] - handLocal).magnitude > 0.20f)
                        {
                            bad++;
                            string line = "";
                            for (int k = 0; k < n; k++)
                            {
                                var bnm = bn[all[off + k].boneIndex].name;
                                line += $" {bnm}={all[off + k].weight:F2}";
                                cnt[bnm] = cnt.TryGetValue(bnm, out var c) ? c + 1 : 1;
                            }
                            if (printed++ < 6)
                                Debug.Log($"[YARGCHAR] STRIPV {name}/{smr.name} v{i} {(v1[i] - handLocal).magnitude * 100f:F0}cm from hand:{line}");
                        }
                        off += n;
                    }
                    Debug.Log($"[YARGCHAR] STRIPV {name}/{smr.name}: {mesh.vertexCount} verts, max influences per vertex {maxInf}, {bad} left-finger vertices >20cm from the hand");
                    foreach (var kv in cnt) if (bad > 0) Debug.Log($"[YARGCHAR] STRIPV   bone {kv.Key} on {kv.Value} of them");
                }
                var go = new GameObject("__baked_" + smr.name);
                go.transform.SetPositionAndRotation(smr.transform.position, smr.transform.rotation);
                go.AddComponent<MeshFilter>().sharedMesh = m;
                go.AddComponent<MeshRenderer>().sharedMaterials = smr.sharedMaterials;
                smr.enabled = false;
                hidden.Add(smr);
                baked.Add(go);
            }
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

        foreach (var face in new[] { ("back", -1f), ("front", 1f) })
        {
            // Whole body, for shading questions. An imported VRM instance can face either way
            // along Z, so render from both sides and let the picture say which is the front.
            var rt2 = new RenderTexture(800, 1000, 24);
            cam.targetTexture = rt2;
            cam.orthographicSize = 1.1f;
            var mid = instance.transform.position + Vector3.up * 0.95f;
            var look = instance.transform.forward * face.Item2;
            camGo.transform.position = mid - look * 3f;
            camGo.transform.rotation = Quaternion.LookRotation(look, Vector3.up);
            cam.Render();
            RenderTexture.active = rt2;
            var tb = new Texture2D(800, 1000, TextureFormat.RGB24, false);
            tb.ReadPixels(new Rect(0, 0, 800, 1000), 0, 0);
            tb.Apply();
            RenderTexture.active = null;
            File.WriteAllBytes(Path.Combine(dir, $"{name}_{(animateSeconds > 0f ? "anim" : "rest")}_body_{face.Item1}.png"), tb.EncodeToPNG());
            Object.DestroyImmediate(tb);
            cam.targetTexture = null;
            rt2.Release();
            Object.DestroyImmediate(rt2);
        }

        cam.targetTexture = null;
        rt.Release();
        Object.DestroyImmediate(rt);
        Object.DestroyImmediate(camGo);
        Object.DestroyImmediate(lightGo);
        foreach (var go in baked) Object.DestroyImmediate(go);
        foreach (var smr in hidden) smr.enabled = true;
    }
}
