using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace YARG.Editor
{
    /// <summary>
    /// Builds a standalone player from batchmode.
    /// </summary>
    /// <remarks>
    /// The fork already has <c>Editor/MakeTestBuild.cs</c>, and it cannot be used here: it calls
    /// <c>BuildPlayerWindow.DefaultBuildMethods.GetBuildPlayerOptions</c>, which asks the editor
    /// where to put the build. In batchmode there is nobody to ask. So this is a second entry
    /// point rather than a change to that one — the menu items keep working exactly as upstream
    /// wrote them, and nothing about an interactive build changes.
    ///
    /// The scenes come from EditorBuildSettings rather than a hardcoded list, so a scene added to
    /// the project cannot be silently missing from a build made this way.
    ///
    /// IT EXITS NON-ZERO WHEN THE BUILD FAILS, and that is the whole reason to write it rather
    /// than shelling out to Unity and hoping. BuildPipeline.BuildPlayer returns a report instead
    /// of throwing, so a build that produced nothing at all still leaves the process exiting 0
    /// unless somebody reads the result. A build system that cannot go red is not a build system.
    /// </remarks>
    public static class BuildPlayerHeadless
    {
        public static void Run()
        {
            try
            {
                string output = Environment.GetEnvironmentVariable("YARG_BUILD_OUTPUT");
                if (string.IsNullOrWhiteSpace(output))
                {
                    output = Path.Combine(Path.GetTempPath(), "yarg-build", "YARG.exe");
                }

                var scenes = EditorBuildSettings.scenes
                    .Where(s => s.enabled)
                    .Select(s => s.path)
                    .ToArray();
                if (scenes.Length == 0)
                {
                    Debug.LogError("BUILD FAIL: no enabled scenes in EditorBuildSettings");
                    EditorApplication.Exit(1);
                    return;
                }

                Debug.Log($"BUILD INFO: {scenes.Length} scene(s), first is {scenes[0]}");
                Debug.Log($"BUILD INFO: output {output}");

                Directory.CreateDirectory(Path.GetDirectoryName(output));

                var options = new BuildPlayerOptions
                {
                    scenes = scenes,
                    locationPathName = output,
                    target = BuildTarget.StandaloneWindows64,
                    targetGroup = BuildTargetGroup.Standalone,
                    options = BuildOptions.None,
                };

                var report = BuildPipeline.BuildPlayer(options);
                var summary = report.summary;

                Debug.Log($"BUILD INFO: result {summary.result}");
                Debug.Log($"BUILD INFO: {summary.totalSize / (1024 * 1024)} MB, " +
                    $"{summary.totalTime.TotalMinutes:F1} min, " +
                    $"{summary.totalErrors} error(s), {summary.totalWarnings} warning(s)");

                // Every step that reported an error, named. A summary count tells you the build
                // is broken; it does not tell you which part of it to look at.
                foreach (var step in report.steps)
                {
                    foreach (var msg in step.messages)
                    {
                        if (msg.type == LogType.Error || msg.type == LogType.Exception)
                        {
                            Debug.Log($"BUILD ERROR [{step.name}]: {msg.content}");
                        }
                    }
                }

                if (summary.result != BuildResult.Succeeded)
                {
                    Debug.LogError($"BUILD FAIL: {summary.result}");
                    EditorApplication.Exit(1);
                    return;
                }

                // Asserted rather than trusted: a "succeeded" report with no executable on disk
                // is the failure this whole file exists to make impossible.
                if (!File.Exists(output))
                {
                    Debug.LogError($"BUILD FAIL: reported success but {output} does not exist");
                    EditorApplication.Exit(1);
                    return;
                }

                var dir = new DirectoryInfo(Path.GetDirectoryName(output));
                long bytes = dir.GetFiles("*", SearchOption.AllDirectories).Sum(f => f.Length);
                Debug.Log($"BUILD INFO: {output} exists, tree is {bytes / (1024 * 1024)} MB");

                // Unity can return Succeeded WITH errors, and the first real run did exactly
                // that: three "RenderTexture.Create failed" from -nographics, alongside
                // "Build Finished, Result: Success". Reporting that as a clean PASS would be
                // the same shape of lie this file exists to prevent - a green that has not
                // been earned. So it is named, the count is in the result line, and judging
                // whether those errors matter is left to whoever reads it.
                if (summary.totalErrors > 0)
                {
                    Debug.Log($"BUILD RESULT: PASS WITH {summary.totalErrors} ERROR(S) " +
                        "- read the BUILD ERROR lines above before trusting this build");
                }
                else
                {
                    Debug.Log("BUILD RESULT: PASS");
                }
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("BUILD FAIL: threw " + e);
                EditorApplication.Exit(1);
            }
        }
    }
}
