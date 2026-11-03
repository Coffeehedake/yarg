using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Helpers;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Checks the rule that decides which fetched songs get deleted when the server cache goes
    /// over its budget.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Written 2026-11-02 with the budget itself. Browsing the server library keeps every song
    /// it plays, nothing removed them, and the cache grew toward the size of the whole server —
    /// which is what browsing exists to avoid. The fix deletes files, so it gets a probe before
    /// it gets trusted.
    /// </para>
    /// <para>
    /// It measures <see cref="ServerCacheBudget.ChooseEvictions"/>, which is pure, rather than
    /// the sweep that calls it. That is not a convenience: the decision is arithmetic over sizes
    /// and timestamps, a compile cannot tell a correct comparison from a reversed one, and a run
    /// that deletes SOMETHING looks identical to a run that deletes the right thing. The disk
    /// half is a few lines of Directory.Delete around this answer.
    /// </para>
    /// <para>
    /// The cases that matter are the ones where being wrong costs somebody a song they wanted:
    /// evicting more than the budget needs, evicting the newest instead of the oldest, and
    /// evicting a protected song — which during a real sweep is the one being played.
    /// </para>
    /// </remarks>
    public static class ServerCacheBudgetProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        private static void Check(string what, bool ok)
        {
            if (ok) { Pass(what); } else { Fail(what); }
        }

        private const long MB = 1024L * 1024L;

        /// <summary>Five songs of 10 MB each, played oldest-first in name order.</summary>
        private static List<ServerCacheBudget.Entry> Cache()
        {
            return new List<ServerCacheBudget.Entry>
            {
                new("aaa", 10 * MB, 1000),
                new("bbb", 10 * MB, 2000),
                new("ccc", 10 * MB, 3000),
                new("ddd", 10 * MB, 4000),
                new("eee", 10 * MB, 5000),
            };
        }

        public static void Run()
        {
            _failures = 0;
            var cache = Cache();
            Debug.Log("PROBE INFO: 5 songs, 10 MB each, 50 MB total, played aaa oldest to eee newest");

            // Under budget: nothing should go. The failure this catches is a sweep that always
            // evicts something because it ran.
            Check("a cache inside its budget loses nothing",
                ServerCacheBudget.ChooseEvictions(cache, 50 * MB).Count == 0);
            Check("and nothing goes when the budget is far above it",
                ServerCacheBudget.ChooseEvictions(cache, 500 * MB).Count == 0);

            // Zero is the documented "no limit", and it is the default-off path: if this ever
            // chose anything, turning the limit off would delete the library.
            Check("a budget of zero means no limit and evicts nothing",
                ServerCacheBudget.ChooseEvictions(cache, 0).Count == 0);
            Check("a negative budget evicts nothing rather than everything",
                ServerCacheBudget.ChooseEvictions(cache, -1).Count == 0);

            // 35 MB over 50 MB needs two gone, and it must be the two LEAST recently played.
            var two = ServerCacheBudget.ChooseEvictions(cache, 35 * MB);
            Check("going 15 MB over evicts exactly the two it needs to", two.Count == 2);
            Check("and they are the two played longest ago, oldest first",
                two.SequenceEqual(new[] { "aaa", "bbb" }));

            // One byte over: the minimum, not a round number of songs.
            var one = ServerCacheBudget.ChooseEvictions(cache, 50 * MB - 1);
            Check("going one byte over evicts one song, not more",
                one.Count == 1 && one[0] == "aaa");

            // The protection that matters: during a sweep this is the song being played.
            var protectedOldest = ServerCacheBudget.ChooseEvictions(
                cache, 35 * MB, new[] { "aaa" });
            Check("a protected song is never chosen, even when it is the oldest",
                !protectedOldest.Contains("aaa"));
            Check("and the next-oldest go instead",
                protectedOldest.SequenceEqual(new[] { "bbb", "ccc" }));

            // Protecting so much that the budget cannot be met must not start taking protected
            // songs anyway. Over budget is recoverable; deleting the playing song is not.
            var allProtected = ServerCacheBudget.ChooseEvictions(
                cache, 10 * MB, cache.Select(e => e.Hash).ToList());
            Check("when everything is protected it gives up rather than evicting anyway",
                allProtected.Count == 0);

            // A song with no recorded play sorts oldest. It is either pre-index or was fetched
            // and never played, and both are the best thing to lose first.
            var withUnplayed = new List<ServerCacheBudget.Entry>(cache)
            {
                new("zzz", 10 * MB, 0),
            };
            var unplayedFirst = ServerCacheBudget.ChooseEvictions(withUnplayed, 50 * MB);
            Check("a song that was never played is evicted before any that was",
                unplayedFirst.Count == 1 && unplayedFirst[0] == "zzz");

            // Sizes differ in reality; the loop must stop on BYTES, not on a song count.
            var mixed = new List<ServerCacheBudget.Entry>
            {
                new("big", 100 * MB, 1000),
                new("sml", 1 * MB, 2000),
                new("med", 20 * MB, 3000),
            };
            var freed = ServerCacheBudget.ChooseEvictions(mixed, 21 * MB);
            Check("one big eviction is enough when it frees enough bytes",
                freed.SequenceEqual(new[] { "big" }));

            // An empty cache must not throw or invent work.
            Check("an empty cache chooses nothing",
                ServerCacheBudget.ChooseEvictions(new List<ServerCacheBudget.Entry>(), 1).Count == 0);

            CheckDiskRoundTrip();

            Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
            EditorApplication.Exit(_failures == 0 ? 0 : 1);
        }

        /// <summary>
        /// Drives the real sweep against the real cache folder, on planted songs only.
        /// </summary>
        /// <remarks>
        /// The checks above measure the DECISION. This measures the half that touches a disk:
        /// that <c>Survey</c> finds planted folders and their sizes, that the index written by
        /// <c>RecordPlayed</c> is read back and orders them, that <c>Directory.Delete</c>
        /// actually removes the chosen one, and that the ones it did not choose survive. A
        /// chooser that is right and a sweep that deletes the wrong folder would both pass
        /// everything above this line.
        ///
        /// Ordering comes from a song with NO recorded play sorting oldest, rather than from
        /// sleeping between writes: planting three and recording a play for two of them makes
        /// the third the one that must go, with no dependence on the clock's resolution.
        ///
        /// Plants into the real cache under an unmistakable prefix and removes only what it
        /// planted, so a cache with real songs in it is left as it was found.
        /// </remarks>
        private static void CheckDiskRoundTrip()
        {
            string root = PathHelper.ServerCachePath;
            if (string.IsNullOrEmpty(root))
            {
                Debug.Log("PROBE SKIP: no server cache path, the disk half is NOT measured");
                return;
            }

            // 40 hex characters like a real chart hash, so nothing treats these as odd, but
            // starting with a run of 'f' that no real hash here begins with.
            string[] planted =
            {
                "ffffffff0000000000000000000000000000aaa1",
                "ffffffff0000000000000000000000000000bbb2",
                "ffffffff0000000000000000000000000000ccc3",
            };

            try
            {
                Directory.CreateDirectory(root);
                foreach (string hash in planted)
                {
                    string folder = Path.Combine(root, hash);
                    Directory.CreateDirectory(folder);
                    // 2 MB each, so the arithmetic below is in whole megabytes.
                    File.WriteAllBytes(Path.Combine(folder, hash + ".sng"), new byte[2 * MB]);
                }

                // Two have been played; the first never has, so it is the one that must go.
                ServerCacheBudget.RecordPlayed(planted[1]);
                ServerCacheBudget.RecordPlayed(planted[2]);

                var survey = ServerCacheBudget.Survey();
                var mine = survey.Where(e => planted.Contains(e.Hash)).ToList();
                Check("the sweep sees all three planted songs", mine.Count == 3);
                Check("and measures their bytes", mine.All(e => e.Bytes == 2 * MB));
                Check("and the unplayed one has no recorded play time",
                    mine.Any(e => e.Hash == planted[0] && e.PlayedAt == 0));

                // Budget: everything that is already there, plus two of the three planted. That
                // leaves exactly one to remove and cannot touch a real song, because every real
                // song is newer than a never-played one only if it has been played - so protect
                // them all by name instead of trusting that.
                long others = survey.Where(e => !planted.Contains(e.Hash)).Sum(e => e.Bytes);
                var protect = survey.Where(e => !planted.Contains(e.Hash)).Select(e => e.Hash).ToList();
                var result = ServerCacheBudget.Enforce(others + 4 * MB, protect);

                Check("it evicted exactly one song", result.Evicted == 1);
                Check("the never-played one is gone from disk",
                    !Directory.Exists(Path.Combine(root, planted[0])));
                Check("the two that were played are still there",
                    Directory.Exists(Path.Combine(root, planted[1])) &&
                    Directory.Exists(Path.Combine(root, planted[2])));
                Check("and it reports the bytes it freed", result.BytesFreed == 2 * MB);

                var after = ServerCacheBudget.Survey();
                Check("a second sweep at the same budget removes nothing more",
                    ServerCacheBudget.Enforce(others + 4 * MB, protect).Evicted == 0);
                Check("and the survey no longer lists the evicted song",
                    after.All(e => e.Hash != planted[0]));

                Debug.Log($"PROBE INFO: disk round trip - evicted {result.Evicted}, " +
                    $"skipped {result.Skipped}, freed {result.BytesFreed} bytes");
            }
            catch (System.Exception ex)
            {
                Fail("the disk round trip threw: " + ex.Message);
            }
            finally
            {
                foreach (string hash in planted)
                {
                    try
                    {
                        string folder = Path.Combine(root, hash);
                        if (Directory.Exists(folder))
                        {
                            Directory.Delete(folder, true);
                        }
                    }
                    catch (System.Exception)
                    {
                        // Nothing useful to do; the next run plants over it.
                    }
                }
            }
        }
    }
}
