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
    /// Plays a server-cut preview through the game's own decoder.
    /// </summary>
    /// <remarks>
    /// <para>
    /// This is the measurement ADR-009 named and could not take. The cutter was verified against
    /// real encoders' CRCs, the clip was decoded by VLC's libvorbis and a person listened to one
    /// - but the ADR's own standard is the REAL CLIENT, whose decoder is BASS, and nothing had
    /// put a clip in front of it. "VLC played it" and "YARG will play it" are different claims.
    /// </para>
    /// <para>
    /// So this calls <c>RemoteSongEntry.LoadPreviewAudio</c> - the production path, the same one
    /// the music library calls when a song is highlighted - against the live server, and asks
    /// BASS whether what came back is audio.
    /// </para>
    /// <para>
    /// A mixer that is merely non-null is not enough: a decoder handed rubbish can still produce
    /// an empty stream. The length is checked against the window the server was asked for,
    /// because a clip of zero seconds would satisfy every other assertion here.
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

                // The entry reads the URL from settings, exactly as it does in a real game.
                SettingsManager.Settings.SongServerUrl.Value = server;
                Debug.Log($"PROBE INFO: server {server}");

                var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
                var row = songs.OfType<JObject>().FirstOrDefault();
                if (row == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: the catalogue is empty");
                    EditorApplication.Exit(2);
                    return;
                }

                var entry = RemoteCatalog.FromJson(row);
                Debug.Log($"PROBE INFO: {entry.Artist} - {entry.Name}  chart {entry.ChartHash}");
                Check("the song has no bytes on this disk, so this is the remote path",
                    !entry.IsMaterialised);

                // ---- the measurement -------------------------------------------------------
                var started = DateTime.UtcNow;
                var mixer = entry.LoadPreviewAudio(1.0f, false);
                var took = (DateTime.UtcNow - started).TotalMilliseconds;

                Check("LoadPreviewAudio returned a mixer", mixer != null);
                if (mixer == null)
                {
                    Debug.LogError("PROBE RESULT: FAIL - BASS would not decode the server's clip");
                    EditorApplication.Exit(1);
                    return;
                }

                using (mixer)
                {
                    double length = mixer.Length;
                    Debug.Log($"PROBE INFO: BASS decoded it in {took:F0} ms, length {length:F2}s, " +
                        $"{mixer.Channels.Count} channel set(s)");

                    // A decoder handed rubbish can still hand back an empty stream, and that
                    // would satisfy "returned a mixer" perfectly well.
                    Check("the clip has real length, not zero", length > 1.0);
                    Check("and it is about the preview window rather than the whole song",
                        length > 5.0 && length < 90.0);
                    Check("it has at least one channel", mixer.Channels.Count > 0);
                }

                // ---- the negative control --------------------------------------------------
                // A hash the server does not have must answer null, not a mixer. Without this,
                // a LoadPreviewAudio that returned some cached or default audio for anything
                // would pass everything above.
                var missing = RemoteSongFetcher.DownloadPreview(server,
                    "0000000000000000000000000000000000000000");
                Check("a song the server does not have yields no preview", missing == null);
                missing?.Dispose();

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
