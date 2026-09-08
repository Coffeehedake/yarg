using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core.Song;
using YARG.Core.Song.Cache;
using Debug = UnityEngine.Debug;

namespace YARG.Editor
{
    /// <summary>
    /// Asks what a mirrored song actually looks like to the library, before anything is built
    /// to mark one.
    /// </summary>
    /// <remarks>
    /// The question this answers: YARG already has a <c>folder:</c> search filter, and it
    /// matches on PLAYLIST rather than on path. If a mirrored song's playlist is already the
    /// mirror folder's name, then filtering the mirror is a feature this fork already has and
    /// half of any "mark server songs" work is unnecessary — which is exactly the shape of
    /// mistake that cost this project a redundant chart check.
    ///
    /// Prints rather than asserts. It exists to find out, not to confirm.
    /// </remarks>
    public static class MirrorIdentityProbe
    {
        public static void Run()
        {
            try
            {
                string mirror = Environment.GetEnvironmentVariable("YARG_MIRROR_DIR");
                if (string.IsNullOrWhiteSpace(mirror))
                {
                    mirror = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");
                }

                if (!Directory.Exists(mirror))
                {
                    Debug.LogError($"PROBE FAIL: no mirror at {mirror}; run the smoke test first");
                    EditorApplication.Exit(1);
                    return;
                }

                Debug.Log($"PROBE INFO: scanning {mirror}");

                string scratch = Path.Combine(Path.GetTempPath(), "yarg-mirror-identity");
                Directory.CreateDirectory(scratch);
                string cachePath = Path.Combine(scratch, "songcache.bin");
                string badSongs = Path.Combine(scratch, "badsongs.txt");
                foreach (string stale in new[] { cachePath, badSongs })
                {
                    if (File.Exists(stale))
                    {
                        File.Delete(stale);
                    }
                }

                var cache = CacheHandler.RunScan(false, cachePath, badSongs, false,
                    new List<string> { mirror });

                var all = cache.Entries.Values.SelectMany(x => x).ToList();
                Debug.Log($"PROBE INFO: {all.Count} entries scanned");

                foreach (var entry in all.Take(4))
                {
                    Debug.Log($"PROBE INFO: playlist='{entry.Playlist}' source='{entry.Source}' " +
                        $"actualLocation='{entry.ActualLocation}' " +
                        $"sortLocation='{entry.SortBasedLocation}'");
                }

                // The two candidate signals, counted rather than eyeballed.
                string mirrorName = new DirectoryInfo(mirror).Name;
                int byPlaylist = all.Count(e =>
                    string.Equals(e.Playlist.ToString(), mirrorName, StringComparison.OrdinalIgnoreCase));
                int byPath = all.Count(e =>
                    e.ActualLocation != null &&
                    e.ActualLocation.Replace('\\', '/')
                        .StartsWith(mirror.Replace('\\', '/'), StringComparison.OrdinalIgnoreCase));

                Debug.Log($"PROBE INFO: playlist == '{mirrorName}' for {byPlaylist}/{all.Count}");
                Debug.Log($"PROBE INFO: ActualLocation under the mirror for {byPath}/{all.Count}");

                Debug.Log(byPlaylist == all.Count
                    ? "PROBE VERDICT: playlist already identifies mirrored songs - 'folder:' filtering works today"
                    : "PROBE VERDICT: playlist does NOT identify mirrored songs - path is the signal");

                Debug.Log("PROBE RESULT: PASS");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("PROBE FAIL: " + e);
                EditorApplication.Exit(1);
            }
        }
    }
}
