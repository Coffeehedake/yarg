using System;
using System.IO;
using System.Reflection;
using System.Linq;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Audio.BASS;
using YARG.Core.Audio;
using YARG.Helpers;
using YARG.Settings;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Asks whether the cache budget is actually enforced by the code that fetches songs, as
    /// opposed to being correct in isolation.
    /// </summary>
    /// <remarks>
    /// <para>
    /// <c>ServerCacheBudgetProbe</c> establishes two things: that the eviction DECISION is right,
    /// and that a sweep driven directly removes the folder it chose. Neither says the sweep is
    /// ever reached. The budget is read from a setting inside <c>RemoteSongFetcher</c> and called
    /// after a successful fetch; a hook that was never wired, or a setting read that returned the
    /// default, would leave both of those probes passing and the cache growing forever — which is
    /// the exact defect this whole feature exists to stop.
    /// </para>
    /// <para>
    /// So this drives the real <see cref="RemoteSongFetcher.Materialise"/> against a real server
    /// with a real over-budget cache, and asks what happened to the disk afterwards.
    /// </para>
    /// <para>
    /// The cache is pushed over budget with sparse filler rather than a gigabyte of real
    /// downloads: <c>SetLength</c> on NTFS reports the full length to <c>FileInfo.Length</c>,
    /// which is what <c>Survey</c> measures, without writing the bytes. The filler is what the
    /// sweep should take; the song just fetched is what it must not.
    /// </para>
    /// <para>
    /// Needs <c>YARG_CATALOG_JSON</c> and <c>YARG_SERVER_URL</c>. Without them it reports
    /// INCONCLUSIVE and exits 2 rather than passing, because a probe that silently skips is a
    /// probe that reports success for a feature nobody measured.
    /// </para>
    /// </remarks>
    public static class ServerCacheIntegrationProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        private static void Check(string what, bool ok)
        {
            if (ok) { Pass(what); } else { Fail(what); }
        }

        private const long MB = 1024L * 1024L;
        private const long GB = 1024L * MB;

        /// <summary>Budget used for the run. One gigabyte, the smallest the setting allows.</summary>
        private const int BudgetGb = 1;

        private const string FillerPrefix = "eeeeeeee";

        private static int CountFiller(string root)
        {
            return Directory.EnumerateDirectories(root)
                .Count(d => Path.GetFileName(d).StartsWith(FillerPrefix, StringComparison.Ordinal));
        }

        public static void Run() => Measure().Forget();

        /// <summary>
        /// Set instead of exiting inline. <c>EditorApplication.Exit</c> terminates the process
        /// immediately, so a <c>finally</c> below it never runs - which is exactly what happened
        /// on the first attempt, leaving 1.2 GB of filler on disk for the next run to trip over.
        /// </summary>
        private static int _exitCode = -1;

        private static async UniTaskVoid Measure()
        {
            string planted = null;
            int? restoreBudget = null;
            try
            {
                PathHelper.Init();

                // SettingsManager.Settings is null outside a running game - SettingsRowProbe
                // documents the same thing and works around it with reflection. Here the point
                // IS the production read, so the container is built rather than bypassed.
                //
                // Worth knowing on its own: because it is null in batchmode, the budget never
                // runs in a headless context at all. EnforceBudget catches the resulting
                // NullReferenceException and logs a warning, which is right for a process with
                // no player - but it means no amount of headless running would ever have
                // exercised this path, which is why this probe builds the container.
                //
                // Built DIRECTLY rather than through SettingsManager.LoadSettings(), which was
                // tried first and threw GlobalAudioHandler.NotInitializedException: loading
                // settings applies audio settings. The constructor skips the file read and the
                // migration, neither of which is under test.
                //
                // The audio backend still has to come up first, though, and that was the second
                // surprise: constructing the container ALONE also threw, because every
                // VolumeSetting invokes its callback on construction and those call
                // GlobalAudioHandler. So the settings container cannot exist in a process with
                // no audio - which is why ScanFolderProbe initialises BASS the same way, and why
                // no probe here can test anything that reads a setting without doing this first.
                // Nothing is played, so nothing is heard.
                GlobalAudioHandler.Initialize<BassAudioManager>();

                if (SettingsManager.Settings == null)
                {
                    var prop = typeof(SettingsManager).GetProperty(nameof(SettingsManager.Settings),
                        BindingFlags.Public | BindingFlags.Static);
                    prop?.SetValue(null, new SettingsManager.SettingContainer());
                }

                Check("the settings container is available", SettingsManager.Settings != null);
                if (SettingsManager.Settings == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: settings would not load");
                    _exitCode = 2;
                    return;
                }

                restoreBudget = SettingsManager.Settings.ServerCacheBudgetGb.Value;

                string catalogPath = Environment.GetEnvironmentVariable("YARG_CATALOG_JSON") ?? "";
                string server = Environment.GetEnvironmentVariable("YARG_SERVER_URL") ?? "";
                if (!File.Exists(catalogPath) || string.IsNullOrWhiteSpace(server))
                {
                    Debug.LogError("PROBE INCONCLUSIVE: need YARG_CATALOG_JSON and YARG_SERVER_URL");
                    _exitCode = 2;
                    return;
                }

                string root = PathHelper.ServerCachePath;
                Directory.CreateDirectory(root);
                Debug.Log($"PROBE INFO: cache at {root}, budget {BudgetGb} GB");

                SettingsManager.Settings.ServerCacheBudgetGb.Value = BudgetGb;
                Check($"the budget setting reads back as {BudgetGb}",
                    SettingsManager.Settings.ServerCacheBudgetGb.Value == BudgetGb);

                // Pick a song that is NOT already cached, so the fetch is a real one and the
                // sweep that follows it is the one this probe is about.
                var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
                JObject row = null;
                foreach (var candidate in songs.OfType<JObject>())
                {
                    string h = ((string) candidate["chart_hash"] ?? "").ToLowerInvariant();
                    if (h.Length == 40 && !Directory.Exists(Path.Combine(root, h)))
                    {
                        row = candidate;
                        break;
                    }
                }

                if (row == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: every catalogue song is already cached");
                    _exitCode = 2;
                    return;
                }

                // Push the cache over budget. Sparse, so this costs no real disk and no download.
                long before = ServerCacheBudget.Survey().Sum(e => e.Bytes);
                long need = (long) BudgetGb * GB + 200 * MB - before;
                int fillers = (int) Math.Max(1, need / (50 * MB)) + 1;
                for (int i = 0; i < fillers; i++)
                {
                    string hash = FillerPrefix + i.ToString("x8").PadLeft(32, '0');
                    string folder = Path.Combine(root, hash);
                    Directory.CreateDirectory(folder);
                    using var fs = new FileStream(Path.Combine(folder, hash + ".sng"),
                        FileMode.Create, FileAccess.Write);
                    fs.SetLength(50 * MB);
                }

                long over = ServerCacheBudget.Survey().Sum(e => e.Bytes);
                int fillersBefore = CountFiller(root);
                Debug.Log($"PROBE INFO: planted {fillers} filler song(s), {fillersBefore} present; " +
                    $"cache is now {over / MB} MB");
                Check("the cache really is over budget before the fetch",
                    over > (long) BudgetGb * GB);

                // The real production path. This is what the whole probe exists to reach.
                var remote = RemoteCatalog.FromJson(row);
                planted = remote.Hash.ToString().ToLowerInvariant();
                string label = $"{(string) row["artist"]} - {(string) row["name"]}";

                var entry = await RemoteSongFetcher.Materialise(server, remote, CancellationToken.None);
                Check($"the song fetched ({label})", entry != null);

                long after = ServerCacheBudget.Survey().Sum(e => e.Bytes);
                Debug.Log($"PROBE INFO: cache after the fetch is {after / MB} MB");

                // The point of the probe.
                Check("the fetch brought the cache back within budget",
                    after <= (long) BudgetGb * GB);
                Check("the song that was just fetched survived its own sweep",
                    Directory.Exists(Path.Combine(root, planted)));

                int fillersLeft = CountFiller(root);
                Check("the filler was what got evicted", fillersLeft < fillersBefore);
                Debug.Log($"PROBE INFO: filler went from {fillersBefore} to {fillersLeft}");

                Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
                _exitCode = _failures == 0 ? 0 : 1;
            }
            catch (Exception ex)
            {
                Debug.LogError("PROBE FAIL: " + ex);
                _exitCode = 1;
            }
            finally
            {
                try
                {
                    if (restoreBudget.HasValue && SettingsManager.Settings != null)
                    {
                        SettingsManager.Settings.ServerCacheBudgetGb.Value = restoreBudget.Value;
                    }
                }
                catch (Exception)
                {
                    // Not worth failing the run over.
                }

                // Leave the cache as it was found, minus whatever the sweep legitimately took.
                try
                {
                    string root = PathHelper.ServerCachePath;
                    if (!string.IsNullOrEmpty(root) && Directory.Exists(root))
                    {
                        foreach (string d in Directory.EnumerateDirectories(root)
                                     .Where(d => Path.GetFileName(d)
                                         .StartsWith(FillerPrefix, StringComparison.Ordinal))
                                     .ToList())
                        {
                            Directory.Delete(d, true);
                        }
                    }
                }
                catch (Exception)
                {
                    // Nothing useful to do here; the next run plants over it.
                }
            }

            EditorApplication.Exit(_exitCode < 0 ? 1 : _exitCode);
        }
    }
}
