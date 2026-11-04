using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Audio.BASS;
using YARG.Core.Audio;
using YARG.Helpers;
using YARG.Settings;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Plays server-cut previews through the game's own decoder, and checks the right PATH was
    /// taken for each kind of song.
    /// </summary>
    /// <remarks>
    /// <para>
    /// ADR-009's standard is the real client, whose decoder is BASS. This calls
    /// <c>RemoteSongEntry.LoadPreviewAudio</c> - the production path, the one the music library
    /// calls when a song is highlighted - against the live server.
    /// </para>
    /// <para>
    /// <b>Counting channels is the whole point now.</b> A multi-stem song must come back as a
    /// MIXER WITH MANY CHANNELS, because the game previews a song by mixing every stem and the
    /// server's single-clip guess was digital silence for 908 of 3,860 songs. A mixer that merely
    /// decodes is not evidence the mixing happened: the old single-clip path also returns a
    /// perfectly good one-channel mixer, and it would pass every assertion about length.
    /// </para>
    /// <para>
    /// So each case names the path it must take, and the single-stem and ships-its-own-preview
    /// cases are the controls. Without them "channels &gt; 1" could be satisfied by a change that
    /// made everything mix, which would waste 5 MB on songs that need 713 KB.
    /// </para>
    /// <para>
    /// Needs <c>YARG_CATALOG_JSON</c> and <c>YARG_SERVER_URL</c>. Without them it reports
    /// INCONCLUSIVE and exits 2 rather than passing, because a probe that silently skips reports
    /// success for a feature nobody measured.
    /// </para>
    /// </remarks>
    public static class RemotePreviewProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        private static void Check(string what, bool ok)
        {
            if (ok) { Pass(what); } else { Fail(what); }
        }

        public static void Run()
        {
            try
            {
                string catalogPath = Environment.GetEnvironmentVariable("YARG_CATALOG_JSON") ?? "";
                string server = Environment.GetEnvironmentVariable("YARG_SERVER_URL") ?? "";
                if (!File.Exists(catalogPath) || string.IsNullOrWhiteSpace(server))
                {
                    Debug.LogError("PROBE INCONCLUSIVE: need YARG_CATALOG_JSON and YARG_SERVER_URL");
                    EditorApplication.Exit(2);
                    return;
                }

                PathHelper.Init();

                // Nothing is played aloud; BASS is initialised because it is the thing under
                // test. Every VolumeSetting also calls GlobalAudioHandler on construction, so a
                // settings container cannot exist without it either.
                GlobalAudioHandler.Initialize<BassAudioManager>();

                try
                {
                    SettingsManager.LoadSettings();
                }
                catch (Exception)
                {
                    var prop = typeof(SettingsManager).GetProperty(nameof(SettingsManager.Settings),
                        BindingFlags.Public | BindingFlags.Static);
                    prop?.SetValue(null, new SettingsManager.SettingContainer());
                }

                if (SettingsManager.Settings == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: no settings container");
                    EditorApplication.Exit(2);
                    return;
                }

                SettingsManager.Settings.SongServerUrl.Value = server;
                Debug.Log($"PROBE INFO: server {server}");

                var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
                if (songs.Count == 0)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: the catalogue is empty");
                    EditorApplication.Exit(2);
                    return;
                }

                bool sawMulti = false, sawSingle = false;

                foreach (var row in songs.OfType<JObject>())
                {
                    int stemCount = (row["assets"]?["stems"] as JArray)?.Count ?? 0;
                    bool ownPreview = row["assets"]?["preview_audio"]?["name"] != null;
                    bool shouldMix = stemCount > 1 && !ownPreview;

                    var entry = RemoteCatalog.FromJson(row);
                    Debug.Log($"PROBE INFO: {entry.Artist} - {entry.Name}  " +
                        $"{stemCount} stems, ships own preview {ownPreview}, " +
                        $"expect {(shouldMix ? "MIXED" : "single clip")}");

                    Check("the song has no bytes on this disk, so this is the remote path",
                        !entry.IsMaterialised);

                    var started = DateTime.UtcNow;
                    var mixer = entry.LoadPreviewAudio(1.0f, false);
                    var took = (DateTime.UtcNow - started).TotalMilliseconds;

                    if (mixer == null)
                    {
                        Fail($"LoadPreviewAudio returned null for {entry.Name}");
                        continue;
                    }

                    using (mixer)
                    {
                        double length = mixer.Length;
                        int channels = mixer.Channels.Count;
                        Debug.Log($"PROBE INFO: BASS decoded it in {took:F0} ms, " +
                            $"length {length:F2}s, {channels} channel(s)");

                        // A decoder handed rubbish can still hand back an empty stream, and that
                        // would satisfy "returned a mixer" perfectly well.
                        Check($"{entry.Name}: the clip has real length, not zero", length > 1.0);
                        Check($"{entry.Name}: and it is about the preview window",
                            length > 5.0 && length < 90.0);

                        if (shouldMix)
                        {
                            sawMulti = true;
                            // THE measurement. One channel here means the server chose a stem
                            // and the client accepted it - which is the defect, not the fix.
                            Check($"{entry.Name}: mixed MANY channels from {stemCount} stems " +
                                $"(got {channels})", channels > 1);
                        }
                        else
                        {
                            sawSingle = true;
                            // The control. If this also mixes, every song pays 5 MB for a
                            // preview that needs 713 KB.
                            Check($"{entry.Name}: stayed on the single-clip path " +
                                $"(got {channels} channel)", channels == 1);
                        }
                    }
                }

                Check("the catalogue covered a multi-stem song", sawMulti);
                Check("the catalogue covered a single-clip song as a control", sawSingle);

                // A hash the server does not have must answer null, not a mixer. Without this,
                // a LoadPreviewAudio that returned some cached or default audio for anything
                // would pass everything above.
                var missing = RemoteSongFetcher.DownloadPreview(server,
                    "0000000000000000000000000000000000000000");
                Check("a song the server does not have yields no preview", missing == null);
                missing?.Dispose();

                var missingStem = RemoteSongFetcher.DownloadStemPreview(server,
                    "0000000000000000000000000000000000000000", "guitar");
                Check("nor does an unknown song's stem", missingStem == null);
                missingStem?.Dispose();

                Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
                EditorApplication.Exit(_failures == 0 ? 0 : 1);
            }
            catch (Exception ex)
            {
                Debug.LogError("PROBE FAIL: " + ex);
                EditorApplication.Exit(1);
            }
        }
    }
}
