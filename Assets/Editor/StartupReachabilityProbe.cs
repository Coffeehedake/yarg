using System;
using System.Diagnostics;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEditor;
using UnityEngine;
using YARG.Song.RemoteLibrary;
using Debug = UnityEngine.Debug;

namespace YARG.Editor
{
    /// <summary>
    /// Measures how long the startup sync takes to give up on a server that is not there.
    /// </summary>
    /// <remarks>
    /// The startup path is default-on, so this number is paid on every launch by every
    /// player whose server is off, asleep, or on the other side of a dropped link. It is
    /// asserted nowhere else: the settings probe can only check that the timeout is passed,
    /// not that anything honours it, and UnityWebRequest.timeout has its own reputation.
    ///
    /// The address is 192.0.2.1 - TEST-NET-1, reserved by RFC 5737 and guaranteed not to be
    /// routable. That is deliberately NOT a closed port on localhost: a refused connection
    /// returns immediately and would pass this test while proving nothing. An unroutable
    /// address hangs, which is what an unplugged Pi actually does.
    /// </remarks>
    public static class StartupReachabilityProbe
    {
        private const string Unreachable = "http://192.0.2.1:8099";

        /// <summary>Generous: this is a ceiling that catches a 30 s regression, not a benchmark.</summary>
        private const double CeilingSeconds = 12.0;

        public static void Run()
        {
            Measure().Forget();
        }

        /// <summary>
        /// Reads the status of a real server and prints what it found, so the settings row's
        /// numbers can be checked against the server's own answer rather than trusted.
        /// </summary>
        /// <remarks>
        /// Separate entry point because it needs a reachable server. YARG_SONG_SERVER
        /// overrides the address.
        /// </remarks>
        public static void RunAgainstServer()
        {
            MeasureAgainstServer().Forget();
        }

        private static async UniTaskVoid MeasureAgainstServer()
        {
            int exitCode = 1;

            try
            {
                string url = Environment.GetEnvironmentVariable("YARG_SONG_SERVER");
                if (string.IsNullOrWhiteSpace(url))
                {
                    url = "http://vault2:8099";
                }

                // The override rather than SettingsManager.Settings, which is null outside a
                // running game - and whose null reference is swallowed by the fire-and-forget
                // call in Describe(), which is how the first version of this probe passed
                // without ever reaching the code it claimed to test.
                SongServerStatus.Invalidate();
                await SongServerStatus.Refresh(url);

                string described = SongServerStatus.Describe();
                Debug.Log($"PROBE INFO: state={SongServerStatus.Current} " +
                    $"songs={SongServerStatus.Songs} problems={SongServerStatus.ServerProblems}");
                Debug.Log($"PROBE INFO: row reads '{described}'");

                if (SongServerStatus.Current != SongServerStatus.State.Reachable)
                {
                    Debug.LogError($"PROBE FAIL: {url} was not reachable: {SongServerStatus.Error}");
                }
                else if (SongServerStatus.Songs <= 0)
                {
                    Debug.LogError("PROBE FAIL: reachable but reported no songs");
                }
                else if (!described.Contains(SongServerStatus.Songs.ToString()))
                {
                    Debug.LogError($"PROBE FAIL: the row does not show the song count: '{described}'");
                }
                else
                {
                    Debug.Log("PROBE PASS: status row reports a real server's own numbers");
                    exitCode = 0;
                }
            }
            catch (Exception e)
            {
                Debug.LogError("PROBE FAIL: probe itself threw: " + e);
            }

            Debug.Log(exitCode == 0 ? "PROBE RESULT: PASS" : "PROBE RESULT: FAIL");
            EditorApplication.Exit(exitCode);
        }

        private static async UniTaskVoid Measure()
        {
            int exitCode = 1;

            try
            {
                string destination = System.IO.Path.Combine(
                    System.IO.Path.GetTempPath(), "yarg-reachability-probe");

                var stopwatch = Stopwatch.StartNew();
                try
                {
                    await SongServerSync.Sync(Unreachable, destination, null, CancellationToken.None,
                        listTimeoutSeconds: SongServerSync.STARTUP_REACHABILITY_TIMEOUT_SECONDS);

                    Debug.LogError("PROBE FAIL: an unroutable address reported success");
                }
                catch (Exception e)
                {
                    stopwatch.Stop();
                    double seconds = stopwatch.Elapsed.TotalSeconds;

                    Debug.Log($"PROBE INFO: gave up after {seconds:F1}s with: {e.Message}");

                    if (seconds > CeilingSeconds)
                    {
                        Debug.LogError($"PROBE FAIL: took {seconds:F1}s to give up on an " +
                            $"unreachable server, ceiling is {CeilingSeconds:F0}s. Every launch " +
                            "pays this on a frozen loading screen.");
                    }
                    else
                    {
                        Debug.Log($"PROBE PASS: gave up on an unreachable server in {seconds:F1}s");
                        exitCode = 0;
                    }
                }
            }
            catch (Exception e)
            {
                Debug.LogError("PROBE FAIL: probe itself threw: " + e);
            }

            Debug.Log(exitCode == 0 ? "PROBE RESULT: PASS" : "PROBE RESULT: FAIL");
            EditorApplication.Exit(exitCode);
        }
    }
}
