using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using YARG.Core.Song.Cache;

namespace Editor
{
    /// <summary>
    /// Scans one folder with YARG's own scanner and prints the verdict for every song.
    /// </summary>
    /// <remarks>
    /// A control, not a feature. When the song-server mirror's smoke test found the scanner
    /// rejecting songs, the obvious conclusion - "the mirror produces archives YARG will not
    /// take" - had an equally plausible rival: the corpus is synthetic, its audio is
    /// zero-filled, and the same songs might be rejected as loose folders too. Those two
    /// have completely different fixes, and nothing measured so far could tell them apart.
    ///
    /// So this runs the identical scanner over the identical songs in their ORIGINAL form.
    /// Whatever it says, the comparison is what makes either claim honest.
    ///
    ///   set YARG_SCAN_FOLDER=C:\some\library
    ///   "Unity.exe" -batchmode -nographics -projectPath &lt;project&gt; ^
    ///       -executeMethod Editor.ScanFolderProbe.Run -logFile &lt;log&gt;
    /// </remarks>
    public static class ScanFolderProbe
    {
        public static void Run()
        {
            try
            {
                string folder = Environment.GetEnvironmentVariable("YARG_SCAN_FOLDER");
                if (string.IsNullOrWhiteSpace(folder) || !Directory.Exists(folder))
                {
                    Console.WriteLine($"[SCAN] FAIL - YARG_SCAN_FOLDER not set or missing: {folder}");
                    EditorApplication.Exit(1);
                    return;
                }

                string scratch = Path.Combine(Path.GetTempPath(), "yarg-scanprobe");
                Directory.CreateDirectory(scratch);
                string cachePath = Path.Combine(scratch, "songcache.bin");
                string badSongsPath = Path.Combine(scratch, "badsongs.txt");
                foreach (string stale in new[] { cachePath, badSongsPath })
                {
                    if (File.Exists(stale))
                    {
                        File.Delete(stale);
                    }
                }

                var cache = CacheHandler.RunScan(false, cachePath, badSongsPath, false,
                    new List<string> { folder });

                int found = 0;
                foreach (var entries in cache.Entries.Values)
                {
                    found += entries.Count;
                }

                Console.WriteLine($"[SCAN] folder={folder}");
                Console.WriteLine($"[SCAN] accepted={found} distinctHashes={cache.Entries.Count}");
                if (File.Exists(badSongsPath))
                {
                    Console.WriteLine("[SCAN] badsongs.txt:");
                    Console.WriteLine(File.ReadAllText(badSongsPath));
                }
                else
                {
                    Console.WriteLine("[SCAN] no badsongs.txt - nothing was refused");
                }

                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Console.WriteLine($"[SCAN] FAIL - {e}");
                EditorApplication.Exit(1);
            }
        }
    }
}
