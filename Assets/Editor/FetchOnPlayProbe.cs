using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core.Song;
using YARG.Core.Song.Cache;

namespace YARG.Editor
{
    /// <summary>
    /// Asks whether ADR-004 increment 2 - "fetch a song when it is played" - actually needs
    /// YARG.Core changed, or whether the Unity layer can do it alone.
    /// </summary>
    /// <remarks>
    /// The ADR asserts it needs two YARG.Core seams, and that assertion was reasoned rather
    /// than measured. It is worth re-asking because the per-song badge, the same week, was
    /// recorded as "needs the Unity editor open" through four handoffs and turned out to be
    /// false of the feature.
    ///
    /// Increment 2 needs TWO things to be true, and only the second is in doubt:
    ///
    ///   1. A place in the Unity layer, after the song is chosen and before anything reads its
    ///      bytes, where async work can run. GameManager.Loading.Start is exactly that: it
    ///      holds a LoadingContext, and LoadChart/LoadAudio are queued onto it AFTERWARDS.
    ///      Established by reading, and stated as reading rather than measurement.
    ///
    ///   2. A SongEntry that exists while its file does NOT. Without this there is nothing to
    ///      fetch on play - the entry only exists because the file already does, and the whole
    ///      increment collapses into increment 1. THIS is what this probe measures.
    ///
    /// It prints what it finds rather than asserting a preferred answer. A probe written to
    /// confirm a hoped-for result is not evidence.
    /// </remarks>
    public static class FetchOnPlayProbe
    {
        public static void Run()
        {
            try
            {
                string corpus = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");
                string songs = Path.Combine(Path.GetTempPath(), "yarg-fetchonplay-songs");
                string state = Path.Combine(Path.GetTempPath(), "yarg-fetchonplay-state");
                string cache = Path.Combine(state, "songcache.bin");
                string bad = Path.Combine(state, "badsongs.txt");

                foreach (string d in new[] { songs, state })
                {
                    if (Directory.Exists(d)) Directory.Delete(d, true);
                    Directory.CreateDirectory(d);
                }

                // Only songs that survive a batchmode scan: this project has already been
                // caught picking corpus files by filename and losing them to the missing audio
                // backend.
                var usable = ScanFull(new List<string> { corpus }, cache, bad)
                    .Select(e => e.ActualLocation)
                    .Where(p => !string.IsNullOrEmpty(p) && p.EndsWith(".sng", StringComparison.OrdinalIgnoreCase))
                    .Take(2).ToList();
                if (usable.Count < 2)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: fewer than 2 corpus songs scan in batchmode");
                    EditorApplication.Exit(2);
                    return;
                }

                var planted = new List<string>();
                foreach (string src in usable)
                {
                    string dst = Path.Combine(songs, Path.GetFileName(src));
                    File.Copy(src, dst);
                    planted.Add(dst);
                }

                // ---- 1. a normal full scan, with the files present ----
                if (File.Exists(cache)) File.Delete(cache);
                var first = ScanFull(new List<string> { songs }, cache, bad);
                Debug.Log($"PROBE INFO: full scan with files present -> {first.Count} entries");
                if (first.Count != 2)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: the baseline scan did not find both songs");
                    EditorApplication.Exit(2);
                    return;
                }
                string vanishing = planted[0];
                string vanishingHash = first
                    .First(e => string.Equals(e.ActualLocation, vanishing, StringComparison.OrdinalIgnoreCase))
                    .Hash.ToString();
                Debug.Log($"PROBE INFO: the song about to be deleted hashes to {vanishingHash}");

                // ---- 2. delete one file, then QUICK scan ----
                // QuickScan only deserialises songcache.bin; it never walks the filesystem, and
                // falls through to a full scan only when it parses ZERO entries. So this asks
                // the real question: does the cache hand back an entry whose bytes are gone?
                File.Delete(vanishing);
                Debug.Log($"PROBE INFO: deleted {Path.GetFileName(vanishing)}; " +
                    $"{Directory.GetFiles(songs, "*.sng").Length} .sng left on disk");

                var quick = ScanQuick(new List<string> { songs }, cache, bad);
                Debug.Log($"PROBE INFO: QUICK scan after the delete -> {quick.Count} entries");

                var survivor = quick.FirstOrDefault(e => e.Hash.ToString() == vanishingHash);
                if (survivor != null)
                {
                    Debug.Log("PROBE FINDING: an entry SURVIVES a quick scan with its file gone.");
                    Debug.Log($"PROBE INFO:   its ActualLocation is still {survivor.ActualLocation}");
                    Debug.Log($"PROBE INFO:   File.Exists there: {File.Exists(survivor.ActualLocation)}");
                    Debug.Log("PROBE VERDICT: increment 2 has an entry to hang on. The Unity layer " +
                        "can materialise the file in GameManager.Loading.Start before LoadChart " +
                        "is queued, and YARG.Core need not change.");
                }
                else
                {
                    Debug.Log("PROBE FINDING: the entry is GONE after a quick scan.");
                    Debug.Log("PROBE VERDICT: an entry cannot outlive its file through the cache, " +
                        "so increment 2 needs entries from somewhere other than a scan - which is " +
                        "increment 3, or a YARG.Core seam. The ADR's assertion stands.");
                }

                // ---- 3. and what a FULL scan says about the same folder ----
                // The failure mode that matters for a player: a rescan is a normal thing to do,
                // and if it drops every unfetched song the feature is a trap rather than a
                // saving.
                if (File.Exists(cache)) File.Delete(cache);
                var again = ScanFull(new List<string> { songs }, cache, bad);
                Debug.Log($"PROBE INFO: FULL rescan after the delete -> {again.Count} entries " +
                    $"(was {first.Count} with both files present)");
                Debug.Log(again.Any(e => e.Hash.ToString() == vanishingHash)
                    ? "PROBE INFO:   the deleted song is somehow still there"
                    : "PROBE INFO:   the deleted song is gone from a full rescan, as expected");

                Debug.Log("PROBE RESULT: PASS");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError("PROBE FAIL: " + e);
                EditorApplication.Exit(1);
            }
        }

        private static List<SongEntry> ScanFull(List<string> folders, string cache, string bad)
        {
            var r = CacheHandler.RunScan(false, cache, bad, false, folders);
            return r.Entries.Values.SelectMany(x => x).ToList();
        }

        private static List<SongEntry> ScanQuick(List<string> folders, string cache, string bad)
        {
            var r = CacheHandler.RunScan(true, cache, bad, false, folders);
            return r.Entries.Values.SelectMany(x => x).ToList();
        }
    }
}
