using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core.Chart;
using YARG.Core.Song;
using YARG.Helpers;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Asks whether a song the game only knows about from the server can actually be PLAYED.
    /// </summary>
    /// <remarks>
    /// <para>
    /// <c>RemoteEntryProbe</c> established that server data becomes a browsable entry. That says
    /// nothing about playing one: a <see cref="RemoteSongEntry"/> returns null from every loader
    /// by design. The claim under test here is the fetch path - download the .sng, let the REAL
    /// scanner produce an entry from it, and get a chart out the other side.
    /// </para>
    /// <para>
    /// The decisive check is <c>LoadChart() != null</c> on the entry that comes back. Anything
    /// less - that a file downloaded, that a scan returned something - would pass just as well
    /// for a song that cannot be played, which is the exact failure this is here to catch.
    /// </para>
    /// <para>
    /// Audio is NOT checked. This harness has no audio backend, and this repo has already once
    /// written up a difference between two builds that was really the missing backend. Audio is
    /// for the real game run, and is reported as unproven rather than assumed.
    /// </para>
    /// </remarks>
    public static class RemotePlaybackProbe
    {
        private static int _failures;

        public static void Run()
        {
            Measure().Forget();
        }

        private static async UniTaskVoid Measure()
        {
            try
            {
                PathHelper.Init();

                string catalogPath = Environment.GetEnvironmentVariable("YARG_CATALOG_JSON") ?? "";
                string server = Environment.GetEnvironmentVariable("YARG_SERVER_URL") ?? "";
                if (!File.Exists(catalogPath) || string.IsNullOrWhiteSpace(server))
                {
                    UnityEngine.Debug.LogError("PROBE INCONCLUSIVE: need YARG_CATALOG_JSON and YARG_SERVER_URL");
                    EditorApplication.Exit(2);
                    return;
                }

                UnityEngine.Debug.Log($"PROBE INFO: cache lives at {PathHelper.ServerCachePath}");

                var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
                var sample = songs.OfType<JObject>().Take(3).ToList();

                foreach (var row in sample)
                {
                    string label = $"{(string) row["artist"]} - {(string) row["name"]}";
                    string wantHash = ((string) row["chart_hash"] ?? "").ToLowerInvariant();

                    // Cold: nothing on disk for this song yet (unless an earlier run left it).
                    string folder = Path.Combine(PathHelper.ServerCachePath, wantHash);
                    if (Directory.Exists(folder))
                    {
                        Directory.Delete(folder, true);
                    }

                    var entry = await Fetch(server, row, label, "COLD");
                    if (entry == null)
                    {
                        continue;
                    }

                    // The one that matters. A scan that returned an entry proves the bytes were
                    // a song; only this proves it is a song that can be played.
                    var sw = Stopwatch.StartNew();
                    SongChart chart = null;
                    try
                    {
                        chart = entry.LoadChart();
                    }
                    catch (Exception ex)
                    {
                        Fail($"{label}: LoadChart threw {ex.GetType().Name}: {ex.Message}");
                        continue;
                    }
                    sw.Stop();

                    if (chart == null)
                    {
                        Fail($"{label}: LoadChart returned null - fetched but not playable");
                        continue;
                    }

                    UnityEngine.Debug.Log($"PROBE INFO:   chart loaded in {sw.ElapsedMilliseconds} ms, " +
                        $"resolution {chart.Resolution}, {chart.Sections.Count} section(s), " +
                        $"{chart.GlobalEvents.Count} global event(s)");

                    // Warm: a DIFFERENT entry object for the same song, so the in-memory
                    // shortcut cannot be what answers. This is the on-disk cache being used.
                    await Fetch(server, row, label, "WARM");
                }

                UnityEngine.Debug.Log(_failures == 0
                    ? "PROBE VERDICT: songs the game held only as server metadata were fetched, " +
                      "scanned and produced real charts. Fetch-on-play works."
                    : $"PROBE VERDICT: {_failures} failure(s); fetch-on-play is not proven.");
                UnityEngine.Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : "PROBE RESULT: FAIL");
                EditorApplication.Exit(_failures == 0 ? 0 : 1);
            }
            catch (Exception e)
            {
                UnityEngine.Debug.LogError("PROBE FAIL: " + e);
                EditorApplication.Exit(1);
            }
        }

        private static async UniTask<SongEntry> Fetch(string server, JObject row, string label, string stage)
        {
            var remote = RemoteCatalog.FromJson(row);
            string wantHash = remote.Hash.ToString().ToLowerInvariant();

            var sw = Stopwatch.StartNew();
            SongEntry entry;
            try
            {
                entry = await RemoteSongFetcher.Materialise(server, remote, CancellationToken.None);
            }
            catch (Exception ex)
            {
                Fail($"{label} [{stage}]: Materialise threw {ex.GetType().Name}: {ex.Message}");
                return null;
            }
            sw.Stop();

            if (entry == null)
            {
                Fail($"{label} [{stage}]: could not be materialised");
                return null;
            }

            // It must come back as a REAL entry. Handing back the remote one would mean the
            // fetch silently did nothing and every loader would still return null.
            if (entry is RemoteSongEntry)
            {
                Fail($"{label} [{stage}]: still a RemoteSongEntry after materialising");
                return null;
            }

            string gotHash = entry.Hash.ToString().ToLowerInvariant();
            if (gotHash != wantHash)
            {
                Fail($"{label} [{stage}]: asked for {wantHash}, got {gotHash}");
                return null;
            }

            UnityEngine.Debug.Log($"PROBE INFO: {stage} {label} -> {entry.GetType().Name} " +
                $"in {sw.ElapsedMilliseconds} ms at {entry.ActualLocation}");
            return entry;
        }

        private static void Fail(string message)
        {
            _failures++;
            UnityEngine.Debug.Log("PROBE FINDING: " + message);
        }
    }
}
