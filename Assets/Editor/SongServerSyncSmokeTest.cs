using System;
using System.IO;
using UnityEditor;
using YARG.Song.RemoteLibrary;

namespace Editor
{
    /// <summary>
    /// Runs a real sync against a real song server and reports whether it worked.
    /// </summary>
    /// <remarks>
    /// This exists because "it compiles" is not evidence that it works, and this project has
    /// been bitten more than once by a green that came from something other than the thing
    /// under test. It talks to an actual server over an actual network and verifies the
    /// chart hash of every file it wrote, so a pass means the mirror really does produce
    /// songs the scanner would accept.
    ///
    /// Run it from the command line - note NO -quit, because the work is asynchronous and
    /// the editor must stay alive to pump it; the test exits the process itself:
    ///
    ///   set YARG_SONG_SERVER=http://your-server:8099
    ///   "Unity.exe" -batchmode -nographics -projectPath &lt;project&gt; ^
    ///       -executeMethod Editor.SongServerSyncSmokeTest.Run -logFile &lt;log&gt;
    ///
    /// Exit code 0 means every song the server offered arrived and verified.
    /// </remarks>
    public static class SongServerSyncSmokeTest
    {
        private const string SERVER_ENV = "YARG_SONG_SERVER";

        [MenuItem("YARG/Debug/Song Server Sync Smoke Test", false, 400)]
        public static void RunFromMenu()
        {
            Run();
        }

        public static void Run()
        {
            string server = Environment.GetEnvironmentVariable(SERVER_ENV);
            if (string.IsNullOrWhiteSpace(server))
            {
                Fail($"{SERVER_ENV} is not set; nothing to test against.");
                return;
            }

            // A scratch folder, not PathHelper.ServerLibraryPath: a test that writes into the
            // real library would make its own second run meaningless.
            string destination = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");

            Console.WriteLine($"[SMOKE] server={server}");
            Console.WriteLine($"[SMOKE] destination={destination}");

            RunAsync(server, destination);
        }

        private static async void RunAsync(string server, string destination)
        {
            try
            {
                var result = await SongServerSync.Sync(server, destination);

                Console.WriteLine($"[SMOKE] {result}");
                foreach (var (hash, reason) in result.Failures)
                {
                    Console.WriteLine($"[SMOKE] FAILED {hash}: {reason}");
                }

                if (result.ServerTotal == 0)
                {
                    Fail("the server reported an empty library, so this run proved nothing");
                    return;
                }

                if (result.Failures.Count > 0)
                {
                    Fail($"{result.Failures.Count} song(s) could not be synced");
                    return;
                }

                // Idempotence is the property that makes this safe to run on every launch,
                // so it is asserted rather than assumed: a second pass must download nothing.
                var second = await SongServerSync.Sync(server, destination);
                if (second.Downloaded.Count != 0)
                {
                    Fail($"second run downloaded {second.Downloaded.Count} song(s); sync is not idempotent");
                    return;
                }

                int onDisk = Directory.GetFiles(destination, "*.sng").Length;
                if (onDisk != second.AlreadyHad)
                {
                    Fail($"{onDisk} .sng on disk but inventory counted {second.AlreadyHad}");
                    return;
                }

                Console.WriteLine($"[SMOKE] PASS - {onDisk} songs mirrored and verified, " +
                    "second run downloaded nothing");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Fail(e.ToString());
            }
        }

        private static void Fail(string message)
        {
            Console.WriteLine($"[SMOKE] FAIL - {message}");
            EditorApplication.Exit(1);
        }
    }
}
