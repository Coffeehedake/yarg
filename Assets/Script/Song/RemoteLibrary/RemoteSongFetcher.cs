#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Threading;
using Cysharp.Threading.Tasks;
using YARG.Core.Logging;
using YARG.Core.Song;
using YARG.Core.Song.Cache;
using YARG.Helpers;
using YARG.Settings;

namespace YARG.Song.RemoteLibrary
{
    /// <summary>
    /// Turns a song the server merely told us about into one this machine can play.
    /// </summary>
    /// <remarks>
    /// <para>
    /// A <see cref="RemoteSongEntry"/> browses but cannot be played: the code that reads .sng
    /// bytes into a chart lives on <c>SngEntry</c>, which is <c>internal sealed</c> in YARG.Core
    /// and unreachable from this assembly. Rather than reimplement it - a second .sng reader
    /// that could disagree with the first about what a song contains - this downloads the file
    /// and asks the REAL scanner to produce the entry, then plays that.
    /// </para>
    /// <para>
    /// The download is <see cref="SongServerSync.FetchOne"/>, reused rather than rewritten,
    /// because that one is already hardened against a server that truncates a body, serves a
    /// real archive under somebody else's hash, answers 500, or returns random bytes - all
    /// measured by <c>Editor/HostileServerProbe.cs</c>. A fresh downloader for the one-song case
    /// would have none of that and would look correct.
    /// </para>
    /// </remarks>
    public static class RemoteSongFetcher
    {
        /// <summary>
        /// Fetches a song's bytes if they are not already here, scans them, and returns the
        /// entry to play. Null means it could not be made playable, and the caller must not
        /// continue into the chart loader.
        /// </summary>
        public static UniTask<SongEntry?> Materialise(RemoteSongEntry remote,
            CancellationToken token)
        {
            string url = SettingsManager.Settings.SongServerUrl.Value;
            if (string.IsNullOrWhiteSpace(url))
            {
                YargLogger.LogWarning("Cannot fetch a server song: no song server is configured");
                return UniTask.FromResult<SongEntry?>(null);
            }
            return Materialise(url, remote, token);
        }

        /// <summary>
        /// As above, against an explicitly given server.
        /// </summary>
        /// <remarks>
        /// Split out so this can be measured without a settings file: an editor probe reaches a
        /// real server with it, and the thing it then exercises is the production path rather
        /// than a copy of it. Public rather than internal for exactly that reason - the editor
        /// probes compile into a separate assembly, so internal would not reach them.
        /// </remarks>
        public static async UniTask<SongEntry?> Materialise(string serverUrl,
            RemoteSongEntry remote, CancellationToken token)
        {
            // Before the early return on purpose. A song played twice in one session takes the
            // fast path below, and if the play were only recorded after it, the second play
            // would leave the song looking as stale as it did before anyone touched it.
            ServerCacheBudget.RecordPlayed(remote.ChartHash);

            // Played before in this session: the scanner has already answered for these bytes.
            if (remote.MaterialisedEntry != null)
            {
                return remote.MaterialisedEntry;
            }

            string root = serverUrl.Trim().TrimEnd('/');
            string hash = remote.ChartHash;
            string folder = Path.Combine(PathHelper.ServerCachePath, hash);
            string file = Path.Combine(folder, hash + ".sng");

            try
            {
                Directory.CreateDirectory(folder);

                if (!File.Exists(file))
                {
                    long bytes = await SongServerSync.FetchOne(root, hash, folder, token);
                    YargLogger.LogFormatInfo("Fetched {0} ({1} bytes) from the song server", hash, bytes);
                }

                // One directory holding one file, so this costs the same whether it is the first
                // song cached or the five hundredth.
                var entry = await UniTask.RunOnThreadPool(() => ScanOne(folder, remote.Hash));

                if (entry == null)
                {
                    YargLogger.LogWarning($"Fetched {hash} but the scanner did not produce that song");
                    return null;
                }

                remote.Materialise(entry);

                // After the song is in hand, never before: a sweep that ran first could evict
                // the very bytes this call is about to return. The hash just fetched is passed
                // as protected for the same reason, which is the hazard the server's pack cache
                // had to add a counter for after measuring it happen.
                EnforceBudget(hash);
                return entry;
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (Exception ex)
            {
                YargLogger.LogWarning($"Could not fetch {hash} from the song server: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Brings the fetch cache back within its configured budget, if it has one.
        /// </summary>
        /// <remarks>
        /// Protects the song just fetched and the song currently loaded. The second is belt and
        /// braces: a file open for playback cannot be deleted on Windows anyway, so the sweep
        /// would skip it — but relying on an OS behaviour to protect a player's audio is not a
        /// policy, it is a coincidence that holds on one platform.
        /// </remarks>
        /// <summary>
        /// Downloads a song's preview clip, blocking until it has it.
        /// </summary>
        /// <remarks>
        /// <para>
        /// Blocking is correct here rather than a compromise. <c>PreviewContext</c> calls
        /// <c>LoadPreviewAudio</c> inside <c>await Task.Run(..., token)</c> - a thread-pool
        /// thread, never the main one - so there is no frame to stall, and the alternative
        /// would be making an abstract YARG.Core loader async for one subclass.
        /// </para>
        /// <para>
        /// <see cref="HttpClient"/> rather than <c>UnityWebRequest</c> for the same reason in
        /// reverse: UnityWebRequest needs the player loop and does not work off the main thread.
        /// <c>DiscordController</c> already uses HttpClient in this project.
        /// </para>
        /// <para>
        /// Scrolling a library does not flood the server: <c>PreviewContext</c> waits
        /// <c>delaySeconds</c> before loading anything and cancels if the selection moves on.
        /// </para>
        /// <para>
        /// Returns null rather than throwing on any failure. A preview that does not play is a
        /// missing nicety; an exception out of a loader is a broken library screen.
        /// </para>
        /// </remarks>
        public static MemoryStream? DownloadPreview(string serverUrl, string chartHash)
        {
            if (string.IsNullOrWhiteSpace(serverUrl) || string.IsNullOrWhiteSpace(chartHash))
            {
                return null;
            }

            var url = serverUrl.TrimEnd('/') + "/song/" + chartHash.ToLowerInvariant() + "/preview.ogg";
            try
            {
                using var response = PreviewClient.GetAsync(url).GetAwaiter().GetResult();
                if (!response.IsSuccessStatusCode)
                {
                    // 415 is the server saying it cannot cut this song's audio yet - mp3 and wav
                    // are not implemented. Expected, and not worth an error-level line every time
                    // somebody highlights one of those songs.
                    YargLogger.LogFormatInfo("No preview for {0}: the server answered {1}",
                        chartHash, (int) response.StatusCode);
                    return null;
                }

                var bytes = response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult();
                if (bytes == null || bytes.Length == 0)
                {
                    YargLogger.LogFormatWarning("The preview for {0} came back empty", chartHash);
                    return null;
                }

                // Owned by the mixer once it is handed over; disposed by the caller when the
                // mixer refuses it.
                return new MemoryStream(bytes, writable: false);
            }
            catch (Exception ex)
            {
                YargLogger.LogWarning(
                    $"Could not fetch a preview for {chartHash}: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// One client for every preview, with a short timeout.
        /// </summary>
        /// <remarks>
        /// A new HttpClient per request exhausts sockets under exactly this usage - one call per
        /// song somebody lingers on - and the timeout is short because a preview that has not
        /// arrived in a few seconds has already missed its moment.
        /// </remarks>
        private static readonly HttpClient PreviewClient = new()
        {
            Timeout = TimeSpan.FromSeconds(8),
        };

        private static void EnforceBudget(string justFetched)
        {
            try
            {
                int gb = SettingsManager.Settings.ServerCacheBudgetGb.Value;
                if (gb <= 0)
                {
                    return;
                }

                var protect = new List<string> { justFetched };
                var playing = GlobalVariables.State.CurrentSong;
                if (playing != null)
                {
                    protect.Add(playing.Hash.ToString());
                }

                ServerCacheBudget.Enforce((long) gb * 1024L * 1024L * 1024L, protect);
            }
            catch (Exception ex)
            {
                // A cache that is too big is a worse day than a song that would not start.
                YargLogger.LogWarning($"Could not enforce the server cache budget: {ex.Message}");
            }
        }

        /// <summary>
        /// Scans the one folder this song was downloaded into and returns the entry whose chart
        /// hash is the one that was asked for.
        /// </summary>
        /// <remarks>
        /// Keyed on the hash rather than "whatever the scan found", and that is the whole point.
        /// The scanner's result is a dictionary FROM chart hash, so asking for the expected key
        /// is both the lookup and the check: bytes that turn out to be a different song simply
        /// are not there, and this returns null instead of quietly playing something else and
        /// filing the score under the wrong song.
        /// </remarks>
        private static SongEntry? ScanOne(string folder, HashWrapper want)
        {
            // Scratch paths, deliberately shared and overwritten: this is the scanner's own
            // bookkeeping for a single-song scan, not a library cache anyone reads back.
            string cache = Path.Combine(PathHelper.ServerCachePath, "scan.bin");
            string bad = Path.Combine(PathHelper.ServerCachePath, "scan-badsongs.txt");

            var result = CacheHandler.RunScan(false, cache, bad, false, new List<string> { folder });

            if (result.Entries.TryGetValue(want, out var entries) && entries.Count > 0)
            {
                return entries[0];
            }
            return null;
        }
    }
}
