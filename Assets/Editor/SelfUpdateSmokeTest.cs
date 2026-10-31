using System;
using UnityEditor;
using YARG.Integration.SelfUpdate;

namespace Editor
{
    /// <summary>
    /// Checks the decisions the updater makes before it is allowed near a network.
    /// </summary>
    /// <remarks>
    /// Everything here is pure: version parsing, manifest validation and the newer-than rule.
    /// Those are the parts that decide whether the game replaces itself, and they are worth
    /// pinning precisely because a bug in them is quiet - an updater that thinks it is always
    /// up to date looks exactly like an updater with nothing to do.
    ///
    ///   "Unity.exe" -batchmode -nographics -quit -projectPath &lt;project&gt; ^
    ///       -executeMethod Editor.SelfUpdateSmokeTest.Run -logFile &lt;log&gt;
    ///
    /// Exit code 0 means every case held.
    /// </remarks>
    public static class SelfUpdateSmokeTest
    {
        private static int _failures;

        [MenuItem("YARG/Debug/Self Update Smoke Test", false, 401)]
        public static void RunFromMenu()
        {
            Run();
        }

        public static void Run()
        {
            Console.WriteLine("[SMOKE] self-update");

            // --- version parsing -------------------------------------------------------
            Check("parses what BuildGitCommitVersion writes",
                BuildIdentity.TryParse("dev b4180 (679f00d3)", out var id)
                && id.Branch == "dev" && id.Build == 4180 && id.Commit == "679f00d3");

            Check("tolerates surrounding whitespace",
                BuildIdentity.TryParse("  dev b1 (abc)  \n", out _));

            // The hardcoded fallback GlobalVariables uses when no define is set. If this ever
            // parses, the updater would compare against a constant and never see an update.
            Check("refuses the hardcoded 'v0.15' fallback",
                !BuildIdentity.TryParse("v0.15", out _));

            Check("refuses empty", !BuildIdentity.TryParse("", out _));
            Check("refuses a missing build number", !BuildIdentity.TryParse("dev (abc1234)", out _));

            // --- manifest validation ---------------------------------------------------
            const string good = @"{""branch"":""dev"",""build"":4181,""commit"":""a1b2c3d"",
                ""url"":""http://example/x.zip"",
                ""sha256"":""0000000000000000000000000000000000000000000000000000000000000000"",
                ""size"":123}";

            Check("accepts a complete manifest",
                UpdateManifest.TryParse(good, out var m, out _) && m.Build == 4181);

            Check("refuses a manifest with no hash",
                !UpdateManifest.TryParse(
                    @"{""branch"":""dev"",""build"":4181,""url"":""http://example/x.zip""}",
                    out _, out _));

            Check("refuses a short hash",
                !UpdateManifest.TryParse(
                    @"{""branch"":""dev"",""build"":4181,""url"":""http://e/x.zip"",""sha256"":""abc""}",
                    out _, out _));

            Check("refuses a manifest with no url",
                !UpdateManifest.TryParse(
                    @"{""branch"":""dev"",""build"":4181,
                       ""sha256"":""0000000000000000000000000000000000000000000000000000000000000000""}",
                    out _, out _));

            Check("refuses something that is not JSON",
                !UpdateManifest.TryParse("<html>404</html>", out _, out _));

            // --- the newer-than rule ---------------------------------------------------
            BuildIdentity.TryParse("dev b4180 (679f00d3)", out var self);
            UpdateManifest.TryParse(good, out var newer, out _);
            Check("4181 is newer than 4180", newer.IsNewerThan(self));

            UpdateManifest.TryParse(good.Replace("4181", "4180"), out var same, out _);
            Check("the same build is not newer", !same.IsNewerThan(self));

            UpdateManifest.TryParse(good.Replace("4181", "4179"), out var older, out _);
            Check("an older build is not newer", !older.IsNewerThan(self));

            // A server that changes what it publishes must never walk a machine onto another
            // branch, however high the number.
            UpdateManifest.TryParse(good.Replace(@"""dev""", @"""main"""), out var otherBranch, out _);
            Check("another branch is never an update", !otherBranch.IsNewerThan(self));

            // An unknown local build cannot be compared with anything.
            Check("an unknown build is never out of date", !newer.IsNewerThan(default));

            Console.WriteLine(_failures == 0
                ? "[SMOKE] RESULT: PASS"
                : $"[SMOKE] RESULT: FAIL ({_failures} case(s))");
            EditorApplication.Exit(_failures == 0 ? 0 : 1);
        }

        private static void Check(string what, bool ok)
        {
            Console.WriteLine($"[SMOKE] {(ok ? "pass" : "FAIL")}  {what}");
            if (!ok)
            {
                _failures++;
            }
        }
    }
}
