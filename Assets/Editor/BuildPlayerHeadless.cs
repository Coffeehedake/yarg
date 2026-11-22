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

                // YARG_BUILD_DEVELOPMENT=1 makes a development build. It is not cosmetic: the fork
                // sets insecureHttpOption to DevelopmentOnly (docs/ADR-004), so a RELEASE build
                // refuses plain http:// - and a song server on a LAN is plain http. A release
                // build therefore reports "Insecure connection not allowed" for every
                // server it is pointed at, which looks like a network fault and is not one.
                var flags = BuildOptions.None;
                if (Environment.GetEnvironmentVariable("YARG_BUILD_DEVELOPMENT") == "1")
                {
                    flags |= BuildOptions.Development;
                    Debug.Log("BUILD INFO: development build (plain http allowed)");
                }

                // CORRECT THE EDITOR'S OWN STORED ARCHITECTURE, not just this build's.
                // `target` below pins x64 for anything built through here, but the File > Make
                // Test Build menu item takes its architecture from this setting instead, and on
                // 2026-11-21 that produced a 32-BIT player: every native plugin then failed to
                // load (bass, sqlite3, RtMidi, libusb) because they all live in Plugins/x86_64,
                // so the game came up with no audio, no score database, no input backend and
                // broken menus. The DLLs were present and correct; nothing could load them.
                // Setting it here costs nothing and stops the menu path repeating it.
                if (EditorUserBuildSettings.selectedStandaloneTarget != BuildTarget.StandaloneWindows64)
                {
                    Debug.Log("BUILD INFO: editor's standalone target was " +
                        $"{EditorUserBuildSettings.selectedStandaloneTarget}, setting it to " +
                        "StandaloneWindows64");
                    EditorUserBuildSettings.selectedStandaloneTarget = BuildTarget.StandaloneWindows64;
                }

                // AND THE ARCHITECTURE *WITHIN* THAT TARGET, which is a separate setting and is
                // what actually went wrong on 2026-11-21. Unity 6 keeps the Windows x86/x64/ARM64
                // choice in the editor's per-platform settings table rather than in the build
                // target, so Library/EditorUserBuildSettings.asset read
                //
                //     Win64   Architecture   x86
                //
                // while every build target in sight said StandaloneWindows64. BuildPlayer then
                // honoured both: it reported platform=StandaloneWindows64 and copied the win32
                // playback engine, producing a 32-bit player that could load none of the 64-bit
                // native plugins beside it. Four builds were spent looking for a missing or
                // broken Unity install; the install was complete and had built x64 from this
                // same project seventeen days earlier.
                //
                // That file is machine-local AND gitignored, so no amount of reading the repo
                // could show it, and a fresh clone elsewhere would behave differently for
                // reasons invisible to both. Hence pinned here rather than fixed by hand.
                foreach (string plat in new[] { "Win64", "Win" })
                {
                    string had = EditorUserBuildSettings.GetPlatformSettings(plat, "Architecture");
                    if (had != "x64")
                    {
                        Debug.Log($"BUILD INFO: {plat} Architecture was \"{had}\", setting it to x64");
                        EditorUserBuildSettings.SetPlatformSettings(plat, "Architecture", "x64");
                    }
                    Debug.Log($"BUILD INFO: {plat} Architecture = " +
                        $"{EditorUserBuildSettings.GetPlatformSettings(plat, "Architecture")}");
                }

                var options = new BuildPlayerOptions
                {
                    scenes = scenes,
                    locationPathName = output,
                    target = BuildTarget.StandaloneWindows64,
                    targetGroup = BuildTargetGroup.Standalone,
                    options = flags,
                };

                // SAY WHAT THE EDITOR ACTUALLY THINKS, unconditionally. Asking for Win64 and
                // getting a 32-bit player happened three times on 2026-11-21 -- with the target
                // pinned here, -buildTarget Win64 on the command line, the editor's stored
                // standalone target already x64, the win64 payload present and 64-bit, and a
                // clean output directory. Every guess at the cause was wrong because none of
                // these values was ever printed.
                Debug.Log($"BUILD INFO: activeBuildTarget={EditorUserBuildSettings.activeBuildTarget}, " +
                    $"selectedStandaloneTarget={EditorUserBuildSettings.selectedStandaloneTarget}, " +
                    $"standaloneBuildSubtarget={EditorUserBuildSettings.standaloneBuildSubtarget}, " +
                    $"requested={options.target}");

                var report = BuildPipeline.BuildPlayer(options);
                var summary = report.summary;
                Debug.Log($"BUILD INFO: report says platform={summary.platform}, " +
                    $"outputPath={summary.outputPath}");

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

                // READ THE ARCHITECTURE OFF THE PRODUCED FILE. Asking for x64 above and getting
                // x64 are different claims, and the gap between them cost an evening: a 32-bit
                // player ran, loaded none of its native plugins, and reported the damage as
                // DllNotFoundException for files that were present, correct and byte-identical
                // to a working build. Nothing in the build output said "32-bit" anywhere.
                string machine = PeMachine(output);
                Debug.Log($"BUILD INFO: {Path.GetFileName(output)} machine type {machine}");
                if (machine != "x64")
                {
                    Debug.LogError($"BUILD FAIL: produced a {machine} player. Everything in " +
                        "YARG_Data/Plugins/x86_64 is 64-bit, so this build would start and then " +
                        "fail to load bass, sqlite3, RtMidi and libusb - no audio, no scores, " +
                        "no input, broken menus.");
                    EditorApplication.Exit(1);
                    return;
                }

                // and the plugins it will need at runtime are actually beside it
                string pluginDir = Path.Combine(Path.GetDirectoryName(output),
                    Path.GetFileNameWithoutExtension(output) + "_Data", "Plugins", "x86_64");
                string[] needed = { "bass.dll", "sqlite3.dll", "yarg_audio.dll" };
                var absent = needed.Where(n => !File.Exists(Path.Combine(pluginDir, n))).ToArray();
                if (absent.Length > 0)
                {
                    Debug.LogError($"BUILD FAIL: {pluginDir} is missing " +
                        string.Join(", ", absent));
                    EditorApplication.Exit(1);
                    return;
                }
                Debug.Log($"BUILD INFO: {Directory.GetFiles(pluginDir, "*.dll").Length} native " +
                    "plugin(s) present beside the player");

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

        /// <summary>
        /// The PE header's machine type, read off the file itself rather than inferred from
        /// what the build was asked for.
        /// </summary>
        private static string PeMachine(string path)
        {
            try
            {
                using var fs = File.OpenRead(path);
                using var br = new BinaryReader(fs);
                fs.Position = 0x3C;
                int peOffset = br.ReadInt32();
                fs.Position = peOffset;
                if (br.ReadUInt32() != 0x00004550) return "not a PE file";   // "PE\0\0"
                ushort machine = br.ReadUInt16();
                return machine switch
                {
                    0x8664 => "x64",
                    0x014c => "x86 (32-bit)",
                    0xAA64 => "arm64",
                    _      => $"0x{machine:x4}",
                };
            }
            catch (Exception e)
            {
                return "unreadable (" + e.GetType().Name + ")";
            }
        }
    }
}
