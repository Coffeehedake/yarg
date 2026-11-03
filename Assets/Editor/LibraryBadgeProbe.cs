using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core.Song.Cache;
using YARG.Helpers;
using YARG.Menu.MusicLibrary;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Checks that the song list marks songs that came from the server, and only those.
    /// </summary>
    /// <remarks>
    /// The badge could not be verified at all as long as it lived inside SongViewType's
    /// instance methods, because constructing one needs a MusicLibraryMenu and that needs a
    /// scene. Pulling the decision into a static took it from "looks right" to "measurable",
    /// which is the whole reason it is shaped that way.
    ///
    /// What makes this a real test rather than a restatement of the code: the entries are
    /// produced by YARG.Core's own scanner walking two REAL folders on disk - the game's
    /// actual mirror path and an ordinary songs folder - so the thing under test is asked
    /// about SongEntry objects built exactly the way the game builds them, including whatever
    /// ActualLocation really ends up being. A hand-made entry would prove only that the string
    /// comparison works.
    /// </remarks>
    public static class LibraryBadgeProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        public static void Run()
        {
            _failures = 0;
            string mirror = PathHelper.ServerLibraryPath;
            var planted = new List<string>();
            string ordinary = Path.Combine(Path.GetTempPath(), "yarg-badge-ordinary");

            try
            {
                string corpus = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");
                if (!Directory.Exists(corpus))
                {
                    Debug.LogError("PROBE FAIL: no corpus at " + corpus);
                    EditorApplication.Exit(1);
                    return;
                }

                // Pick the songs by SCANNING the corpus first, not by taking the first four
                // filenames. Batchmode has no working audio backend, so a song whose song.ini
                // omits song_length is refused with "Corruption of either the ini file or
                // chart/mid file" - the scanner measures length from the audio, LoadAudio
                // throws, and the message names neither the real cause nor the real file. That
                // is the harness trap this project retracted a published claim over, and the
                // first version of this probe walked straight into it: two of its four songs
                // vanished and the failure looked like the badge.
                var sources = Scan(new List<string> { corpus })
                    .Select(e => e.ActualLocation)
                    .Where(p => !string.IsNullOrEmpty(p) &&
                        p.EndsWith(".sng", StringComparison.OrdinalIgnoreCase))
                    .OrderBy(p => p, StringComparer.Ordinal)
                    .ToList();
                Debug.Log($"PROBE INFO: {sources.Count} of " +
                    $"{Directory.GetFiles(corpus, "*.sng").Length} corpus songs scan in batchmode");

                if (sources.Count < 4)
                {
                    // Inconclusive, not failed - the same exit ScanFolderProbe uses when it
                    // cannot decode audio. Reporting this as a red badge test would be a lie
                    // about which thing was measured.
                    Debug.LogError("PROBE INCONCLUSIVE: fewer than 4 corpus songs survive a " +
                        "batchmode scan, so there is nothing to compare");
                    EditorApplication.Exit(2);
                    return;
                }

                // Two songs into the REAL mirror folder, two into an ordinary one. Same bytes,
                // different locations - so the only thing that can distinguish them is the
                // signal the badge claims to use.
                Directory.CreateDirectory(mirror);
                if (Directory.Exists(ordinary))
                {
                    Directory.Delete(ordinary, true);
                }
                Directory.CreateDirectory(ordinary);

                for (int i = 0; i < 2; i++)
                {
                    string dst = Path.Combine(mirror, Path.GetFileName(sources[i]));
                    if (!File.Exists(dst))
                    {
                        File.Copy(sources[i], dst);
                        planted.Add(dst);
                    }
                }
                for (int i = 2; i < 4; i++)
                {
                    File.Copy(sources[i], Path.Combine(ordinary, Path.GetFileName(sources[i])));
                }

                Debug.Log($"PROBE INFO: mirror={mirror}");
                Debug.Log($"PROBE INFO: ordinary={ordinary}");

                Debug.Log($"PROBE INFO: mirror holds {Directory.GetFiles(mirror, "*.sng").Length} .sng, " +
                    $"ordinary holds {Directory.GetFiles(ordinary, "*.sng").Length} .sng");

                var entries = Scan(new List<string> { mirror, ordinary });
                Debug.Log($"PROBE INFO: {entries.Count} entries scanned across both folders");
                foreach (var e in entries)
                {
                    Debug.Log($"PROBE INFO:   entry at {e.ActualLocation}");
                }

                var mirrored = entries.Where(MirroredSongs.IsMirrored).ToList();
                var local = entries.Where(e => !MirroredSongs.IsMirrored(e)).ToList();

                if (mirrored.Count == 0 || local.Count == 0)
                {
                    Fail($"the test cannot mean anything: {mirrored.Count} mirrored and " +
                        $"{local.Count} local entries were scanned, and it needs both");
                }
                else
                {
                    Pass($"{mirrored.Count} mirrored and {local.Count} local entries to compare");
                }

                // ---- the badge appears on exactly the mirrored ones ----
                int badged = 0, wrongly = 0;
                foreach (var e in mirrored)
                {
                    string text = SongViewType.WithServerBadge("ARTIST", e);
                    if (text.Contains(SongViewType.BadgeMarkup)) { badged++; }
                }
                foreach (var e in local)
                {
                    string text = SongViewType.WithServerBadge("ARTIST", e);
                    if (text.Contains(SongViewType.BadgeMarkup)) { wrongly++; }
                    else if (text != "ARTIST")
                    {
                        Fail($"a local song's text was altered: '{text}'");
                    }
                }

                if (badged != mirrored.Count)
                {
                    Fail($"{mirrored.Count - badged} of {mirrored.Count} mirrored songs are unmarked");
                }
                else
                {
                    Pass($"all {mirrored.Count} mirrored songs carry the badge");
                }

                if (wrongly > 0)
                {
                    Fail($"{wrongly} of {local.Count} songs the player owns were marked as the server's");
                }
                else
                {
                    Pass($"none of the {local.Count} local songs were marked");
                }

                // ---- the original text survives intact ----
                // A badge that mangles the artist name is worse than no badge, and appending
                // INSIDE the formatting is exactly how that happens.
                var sample = mirrored.First();
                string decorated = SongViewType.WithServerBadge("<color=#ffffff>Björk</color>", sample);
                if (!decorated.StartsWith("<color=#ffffff>Björk</color>", StringComparison.Ordinal))
                {
                    Fail("the artist text is no longer intact at the start: " + decorated);
                }
                else
                {
                    Pass("the badge is appended after the formatted text, leaving it untouched");
                }

                // ---- a song BROWSED from the server, holding no bytes on this machine ----
                // The badge and the "server:" filter both shipped BEFORE RemoteSongEntry
                // existed, so neither has ever been asked about the one song that is most
                // obviously the server's: one the player can see and has not downloaded.
                // Built through RemoteCatalog.FromJson - production's own mapping, against a
                // real catalogue - because a hand-made entry would only prove that a string
                // comparison works.
                CheckBrowsedEntries();

                // ---- a null entry must not throw ----
                // GetSecondaryText runs for every visible row on every frame of a scroll; an
                // exception there is a menu that stops drawing rather than a message anyone
                // reads.
                try
                {
                    string safe = SongViewType.WithServerBadge("ARTIST", null);
                    if (safe != "ARTIST")
                    {
                        Fail("a null entry produced a badge: " + safe);
                    }
                    else
                    {
                        Pass("a null entry is left alone rather than throwing");
                    }
                }
                catch (Exception e)
                {
                    Fail("a null entry threw: " + e.Message);
                }
            }
            catch (Exception e)
            {
                Fail("probe threw: " + e);
            }
            finally
            {
                // Only what this probe put there. The mirror is a real folder the game owns and
                // may already hold the player's synced songs.
                foreach (string p in planted)
                {
                    try { File.Delete(p); } catch { /* reported below by what is left */ }
                }
                try { if (Directory.Exists(ordinary)) Directory.Delete(ordinary, true); } catch { }
                Debug.Log($"PROBE INFO: removed {planted.Count} planted file(s) from the mirror");
            }

            Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
            EditorApplication.Exit(_failures == 0 ? 0 : 1);
        }

        /// <summary>
        /// Asks whether an un-downloaded server song is treated as the server's.
        /// </summary>
        /// <remarks>
        /// Skipped rather than failed when no catalogue is available: this probe's other
        /// checks need only two folders on disk, and making all of them depend on a reachable
        /// server would mean the badge stops being verifiable the moment vault2 is asleep.
        /// </remarks>
        private static void CheckBrowsedEntries()
        {
            string catalogPath = Environment.GetEnvironmentVariable("YARG_CATALOG_JSON") ?? "";
            if (!File.Exists(catalogPath))
            {
                Debug.Log("PROBE SKIP: no catalogue at YARG_CATALOG_JSON, so browsed-song " +
                    "behaviour was NOT measured");
                return;
            }

            var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
            var remote = songs.OfType<JObject>().Select(RemoteCatalog.FromJson).ToList();
            if (remote.Count == 0)
            {
                Fail("the catalogue parsed to zero remote entries, so nothing was measured");
                return;
            }

            Debug.Log($"PROBE INFO: {remote.Count} browsed entries built from the catalogue");
            Debug.Log($"PROBE INFO:   first one's ActualLocation is {remote[0].ActualLocation}");

            int marked = 0, kept = 0, wronglyLocal = 0;
            foreach (var e in remote)
            {
                if (SongViewType.WithServerBadge("ARTIST", e).Contains(SongViewType.BadgeMarkup))
                {
                    marked++;
                }

                // The filter half of the same question. A player who types "server:yes" to see
                // what the server has, and is shown only what they already downloaded, has been
                // answered the opposite of what they asked.
                if (MirroredSongs.Matches(e, MirroredSongs.Want.Mirrored))
                {
                    kept++;
                }

                // And the other direction, because a filter that keeps everything under both
                // answers is not a filter. "server:no" means "things I own", and a song with
                // no bytes on this machine is not one of them.
                if (MirroredSongs.Matches(e, MirroredSongs.Want.NotMirrored))
                {
                    wronglyLocal++;
                }
            }

            if (marked != remote.Count)
            {
                Fail($"{remote.Count - marked} of {remote.Count} songs browsed FROM the server " +
                    "carry no server badge");
            }
            else
            {
                Pass($"all {remote.Count} browsed songs carry the badge");
            }

            if (kept != remote.Count)
            {
                Fail($"\"server:yes\" hides {remote.Count - kept} of {remote.Count} songs that " +
                    "exist only on the server");
            }
            else
            {
                Pass($"\"server:yes\" keeps all {remote.Count} browsed songs");
            }

            if (wronglyLocal > 0)
            {
                Fail($"\"server:no\" still shows {wronglyLocal} of {remote.Count} songs this " +
                    "machine holds no bytes of");
            }
            else
            {
                Pass($"\"server:no\" excludes all {remote.Count} browsed songs");
            }
        }

        private static List<YARG.Core.Song.SongEntry> Scan(List<string> folders)
        {
            string scratch = Path.Combine(Path.GetTempPath(), "yarg-badge-probe");
            Directory.CreateDirectory(scratch);
            string cache = Path.Combine(scratch, "songcache.bin");
            string bad = Path.Combine(scratch, "badsongs.txt");
            foreach (string stale in new[] { cache, bad })
            {
                if (File.Exists(stale)) File.Delete(stale);
            }

            var result = CacheHandler.RunScan(false, cache, bad, false, folders);
            if (File.Exists(bad))
            {
                string text = File.ReadAllText(bad).Trim();
                if (text.Length > 0)
                {
                    Debug.Log("PROBE INFO: badsongs.txt says: " + text.Replace("\r\n", " | "));
                }
            }
            return result.Entries.Values.SelectMany(x => x).ToList();
        }
    }
}
