using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core;
using YARG.Core.Song;
using YARG.Core.Song.Cache;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Asks whether a SongEntry built from server data - never scanned, with no file behind it -
    /// actually works, measured against the REAL library rather than one fabricated song.
    /// </summary>
    /// <remarks>
    /// Reading the source said this should be possible (see <see cref="RemoteSongEntry"/> for the
    /// accessibility argument, and for why ADR-004 says otherwise). Reading is not running. The
    /// repo's own rule is probe before you assert, especially about code you did not write, and
    /// the specific thing being guarded against here is a class that compiles, constructs, and
    /// then browses blank or loses its identity - which no compile error would catch.
    ///
    /// Input is the live catalogue, pulled from the server and saved to JSON, so a failure can be
    /// named per song. 609 real songs exercise cases no synthetic fixture would: missing albums,
    /// empty charters, non-ASCII names, songs with no vocals, songs with every part.
    ///
    /// It prints what it finds. A probe written to confirm a hoped-for result is not evidence.
    /// </remarks>
    public static class RemoteEntryProbe
    {
        private sealed class Failure
        {
            public string Song  = "";
            public string Check = "";
            public string Detail = "";
        }

        public static void Run()
        {
            try
            {
                string catalogPath = Environment.GetEnvironmentVariable("YARG_CATALOG_JSON") ?? "";
                if (!File.Exists(catalogPath))
                {
                    Debug.LogError($"PROBE INCONCLUSIVE: no catalogue at YARG_CATALOG_JSON ({catalogPath})");
                    EditorApplication.Exit(2);
                    return;
                }

                string outPath = Environment.GetEnvironmentVariable("YARG_PROBE_OUT")
                    ?? Path.Combine(Path.GetDirectoryName(catalogPath)!, "remote-entry-failures.txt");

                var root = JObject.Parse(File.ReadAllText(catalogPath));
                var songs = (JArray) root["songs"]!;
                Debug.Log($"PROBE INFO: catalogue holds {songs.Count} songs");

                var failures = new List<Failure>();
                var entries = new List<RemoteSongEntry>();
                var ratings = new Dictionary<uint, int>();

                foreach (var node in songs.OfType<JObject>())
                {
                    string label = Describe(node);

                    RemoteSongEntry entry;
                    try
                    {
                        // Production's own mapping, deliberately: a probe with its own copy of
                        // this would pass against a mapping the game never runs.
                        entry = RemoteCatalog.FromJson(node);
                    }
                    catch (Exception ex)
                    {
                        failures.Add(new Failure
                        {
                            Song = label, Check = "construct",
                            Detail = ex.GetType().Name + ": " + ex.Message
                        });
                        continue;
                    }

                    entries.Add(entry);
                    CheckOne(node, entry, label, failures, ratings);
                }

                Debug.Log($"PROBE INFO: {entries.Count} of {songs.Count} entries constructed");

                // ---- the whole set, not one song at a time -------------------------------------
                // Identity collisions and sort crashes only appear in aggregate, and both would
                // be invisible in a single-song test.
                CheckTheSet(entries, failures);

                // ---- does the container's own indexing accept them? ---------------------------
                // SongCache.Entries is the real merge point - FillContainers reads exactly this
                // dictionary - and it is a public mutable dictionary, so no YARG.Core change is
                // needed to put our entries in front of the game.
                try
                {
                    var cache = new SongCache();
                    foreach (var e in entries)
                    {
                        if (!cache.Entries.TryGetValue(e.Hash, out var list))
                        {
                            list = new List<SongEntry>();
                            cache.Entries.Add(e.Hash, list);
                        }
                        list.Add(e);
                    }
                    int total = cache.Entries.Values.Sum(l => l.Count);
                    Debug.Log($"PROBE INFO: merged into SongCache.Entries -> {cache.Entries.Count} " +
                        $"distinct hashes, {total} entries");
                    if (total != entries.Count)
                    {
                        failures.Add(new Failure
                        {
                            Song = "(whole set)", Check = "merge",
                            Detail = $"{entries.Count} entries went in, {total} came out"
                        });
                    }
                }
                catch (Exception ex)
                {
                    failures.Add(new Failure
                    {
                        Song = "(whole set)", Check = "merge",
                        Detail = ex.GetType().Name + ": " + ex.Message
                    });
                }

                // ---- report -------------------------------------------------------------------
                var report = new List<string>
                {
                    $"catalogue: {catalogPath}",
                    $"songs in catalogue: {songs.Count}",
                    $"entries constructed: {entries.Count}",
                    $"failures: {failures.Count}",
                    "ratings seen: " + string.Join(", ",
                        ratings.OrderBy(k => k.Key).Select(k => $"{k.Key}x{k.Value}")),
                    "",
                };
                report.AddRange(failures.Select(f => $"{f.Check}\t{f.Song}\t{f.Detail}"));
                File.WriteAllLines(outPath, report);
                Debug.Log($"PROBE INFO: failure list written to {outPath}");

                foreach (var group in failures.GroupBy(f => f.Check).OrderByDescending(g => g.Count()))
                {
                    Debug.Log($"PROBE FINDING: {group.Count()} x {group.Key}");
                    foreach (var f in group.Take(5))
                    {
                        Debug.Log($"PROBE INFO:     {f.Song} -> {f.Detail}");
                    }
                }

                if (failures.Count == 0)
                {
                    Debug.Log("PROBE VERDICT: every song in the live library became a working entry " +
                        "with no YARG.Core change. Identity, metadata, parts and sorting all hold.");
                    Debug.Log("PROBE RESULT: PASS");
                    EditorApplication.Exit(0);
                }
                else
                {
                    Debug.Log($"PROBE VERDICT: {failures.Count} failures across {entries.Count} entries; " +
                        "see the failure list.");
                    Debug.Log("PROBE RESULT: FAIL");
                    EditorApplication.Exit(1);
                }
            }
            catch (Exception e)
            {
                Debug.LogError("PROBE FAIL: " + e);
                EditorApplication.Exit(1);
            }
        }

        private static string Describe(JObject n) =>
            $"{(string?) n["artist"] ?? "?"} - {(string?) n["name"] ?? "?"} " +
            $"[{((string?) n["chart_hash"] ?? "").PadRight(8).Substring(0, 8)}]";

        private static void CheckOne(JObject n, RemoteSongEntry e, string label,
            List<Failure> failures, Dictionary<uint, int> ratings)
        {
            void Fail(string check, string detail) =>
                failures.Add(new Failure { Song = label, Check = check, Detail = detail });

            // Identity. The load-bearing one: if the hash does not round-trip, the client and the
            // server disagree about which song this is and nothing else reports it.
            string want = ((string?) n["chart_hash"] ?? "").ToLowerInvariant();
            string got = e.Hash.ToString().ToLowerInvariant();
            if (want != got)
            {
                Fail("identity", $"server said {want}, entry says {got}");
            }

            // The sort strings are private and only SetSortStrings fills them. An entry that
            // skips it carries correct metadata and browses as a blank row.
            if (string.IsNullOrEmpty(e.Name.Original))
            {
                Fail("sortstring-name", "Name is empty after SetSortStrings");
            }
            if (string.IsNullOrEmpty(e.Artist.Original))
            {
                Fail("sortstring-artist", "Artist is empty after SetSortStrings");
            }
            string wantName = (string?) n["name"] ?? "";
            if (!string.IsNullOrEmpty(wantName) && e.Name.Original != wantName)
            {
                Fail("name-mismatch", $"server said '{wantName}', entry says '{e.Name.Original}'");
            }

            // The instrument indexer is what the music library filters and groups on.
            //
            // NotImplementedException is deliberately NOT counted: upstream's indexer ends in
            // "_ => throw new NotImplementedException" and some enum members (Dj, and whatever
            // else is reserved but unmapped) land there for EVERY entry, scanned or not. Counting
            // it would report 609 failures that say nothing about this type.
            foreach (Instrument instrument in Enum.GetValues(typeof(Instrument)))
            {
                try
                {
                    _ = e[instrument];
                }
                catch (NotImplementedException)
                {
                    // upstream's own gap
                }
                catch (Exception ex)
                {
                    Fail("parts-indexer", $"{instrument}: {ex.GetType().Name}: {ex.Message}");
                }
            }

            // Parts must survive the trip, or songs silently stop matching instrument filters.
            if (n["parts"]?["five_fret_guitar"]?["difficulties"] is { } g)
            {
                byte wantMask = (byte) (int) g;
                byte gotMask = e[Instrument.FiveFretGuitar].SubTracks;
                if (gotMask != wantMask)
                {
                    Fail("parts-mismatch", $"five_fret_guitar mask {wantMask} became {gotMask}");
                }
            }

            try
            {
                var r = e.GetSongRating(false);
                uint key = (uint) r;
                ratings[key] = ratings.TryGetValue(key, out int c) ? c + 1 : 1;
                if (!Enum.IsDefined(typeof(SongRating), r))
                {
                    Fail("rating", $"rating {key} is not a defined SongRating");
                }
            }
            catch (Exception ex)
            {
                Fail("rating", ex.GetType().Name + ": " + ex.Message);
            }

            // The four cheap abstracts, and the downcast gauntlet.
            try
            {
                _ = e.SubType;
                _ = e.SortBasedLocation;
                _ = e.ActualLocation;
                _ = e.GetLastWriteTime();
            }
            catch (Exception ex)
            {
                Fail("abstract-members", ex.GetType().Name + ": " + ex.Message);
            }

            if (e is RBCONEntry)
            {
                Fail("downcast", "a RemoteSongEntry matched 'is RBCONEntry'");
            }
        }

        private static void CheckTheSet(List<RemoteSongEntry> entries, List<Failure> failures)
        {
            // Two songs sharing a chart hash is legal and expected - YARG's own cache is
            // hash -> List<SongEntry>. Two sharing a LOCATION is not: the container de-duplicates
            // on it, so a collision silently hides a song.
            var byLocation = entries.GroupBy(e => e.SortBasedLocation).Where(g => g.Count() > 1).ToList();
            foreach (var g in byLocation.Take(10))
            {
                failures.Add(new Failure
                {
                    Song = "(whole set)", Check = "location-collision",
                    Detail = $"{g.Count()} entries share {g.Key}"
                });
            }

            // Sorting is where a foreign entry is most likely to throw, because the comparers
            // reach into fields a scan would always have filled.
            try
            {
                var sorted = new List<SongEntry>(entries);
                sorted.Sort(new SongEntrySorting.MetadataComparer());
                Debug.Log($"PROBE INFO: MetadataComparer sorted {sorted.Count} entries; " +
                    $"first is '{sorted[0].Artist.Original} - {sorted[0].Name.Original}', " +
                    $"last is '{sorted[^1].Artist.Original} - {sorted[^1].Name.Original}'");
            }
            catch (Exception ex)
            {
                failures.Add(new Failure
                {
                    Song = "(whole set)", Check = "sort",
                    Detail = ex.GetType().Name + ": " + ex.Message
                });
            }
        }
    }
}
