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
