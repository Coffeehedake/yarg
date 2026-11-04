using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core;
using YARG.Core.Song;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Asks whether the library's search finds a song the server published and this machine does
    /// not hold.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Jay reported on 2026-11-03 that with the server library browsing, the list showed all
    /// 4,080 songs and typing in the search box returned "only local songs". Reading the code
    /// narrowed it and eliminated two suspects but could not close it:
    /// </para>
    /// <list type="bullet">
    /// <item><description>
    /// The <c>server:</c> mirror filter is not it. With no <c>server:</c> term
    /// <c>MirroredSongs.ExtractWant</c> returns <c>Want.Either</c> and
    /// <c>ApplyMirrorFilter</c> hands the list straight back.
    /// </description></item>
    /// <item><description>
    /// A stale <c>SongSearching._baseList</c> is not it either, or not on its own.
    /// <c>MusicLibraryMenu.SortFilter</c> builds the UNSEARCHED list through the very same
    /// <c>_searchField.Search(...)</c> call, so the 4,080 Jay saw came out of
    /// <c>_baseList</c> — the remote entries were in it.
    /// </description></item>
    /// </list>
    /// <para>
    /// What is left is the predicate: the unqualified query goes to
    /// <c>SongSearching.UnspecifiedSearch</c>, which reads <c>Name.SearchStr</c> and
    /// <c>Artist.SearchStr</c> and ranks inside a <c>Parallel.ForEach</c>. That is the half no
    /// existing probe touches — <c>RemoteEntryProbe</c> checks those strings are non-empty per
    /// song, which is not the same as asking whether a search returns the song.
    /// </para>
    /// <para>
    /// So this drives the REAL <see cref="SongSearching"/> over entries built by the REAL
    /// <c>RemoteCatalog.FromJson</c>, with the catalogue of 4,085 songs the live server
    /// publishes. It reaches the search by reflecting <c>_sortTitles</c> and <c>_sortArtists</c>
    /// into <c>SongContainer</c> rather than by running <c>FillContainers</c>, deliberately:
    /// <c>FillContainers</c> wants localisation, the filters menu and a settings container, none
    /// of which exists in batchmode and none of which is under test. The question here is
    /// narrow — given a sorted list that DOES hold remote entries, does search return them?
    /// </para>
    /// <para>
    /// A probe that only asserts the hoped-for result is not evidence, so the negative control is
    /// built in and fails the run if it goes the wrong way: a query no song can match must
    /// return nothing. If the nonsense query returned songs, the probe is measuring nothing and
    /// its green would be worthless.
    /// </para>
    /// <para>Needs <c>YARG_CATALOG_JSON</c>. Without it, INCONCLUSIVE and exit 2 — never a pass.</para>
    /// </remarks>
    public static class SearchRemoteProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        private static void Check(string what, bool ok)
        {
            if (ok) { Pass(what); } else { Fail(what); }
        }

        private static int Total(SongCategory[] categories)
        {
            return categories == null ? -1 : categories.Sum(c => c.Songs.Length);
        }

        private static void SetContainerField(string name, SongCategory[] value)
        {
            var field = typeof(SongContainer).GetField(name,
                BindingFlags.NonPublic | BindingFlags.Static);
            if (field == null)
            {
                throw new Exception($"SongContainer.{name} is gone - this probe reaches it by " +
                    "reflection and cannot measure anything without it");
            }
            field.SetValue(null, value);
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

                var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
                var entries = new List<RemoteSongEntry>(songs.Count);
                foreach (var node in songs.OfType<JObject>())
                {
                    // Production's own mapping. A probe with its own copy of it would pass
                    // against a mapping the game never runs.
                    entries.Add(RemoteCatalog.FromJson(node));
                }

                Debug.Log($"PROBE INFO: {entries.Count} remote entries built from {songs.Count} " +
                    "catalogue rows");
                Check("every catalogue row became an entry", entries.Count == songs.Count);

                // Grouped by first letter, the way a titles sort really looks, because
                // SearchSongs walks categories and a single-category list would not exercise
                // that walk.
                var byLetter = entries
                    .GroupBy(e => string.IsNullOrEmpty(e.Name.SortStr)
                        ? "?"
                        : e.Name.SortStr.Substring(0, 1).ToUpperInvariant())
                    .OrderBy(g => g.Key, StringComparer.Ordinal)
                    .Select(g => new SongCategory(g.Key, g.Cast<SongEntry>().ToArray(), g.Key))
                    .ToArray();

                Debug.Log($"PROBE INFO: {byLetter.Length} categories, {Total(byLetter)} songs");

                SetContainerField("_sortTitles", byLetter);
                SetContainerField("_sortArtists", byLetter);

                var sorted = SongContainer.GetSortedCategory(SortAttribute.Name);
                Check($"the container hands back all {entries.Count} songs",
                    Total(sorted) == entries.Count);

                // ---- the browse case: no query at all ----------------------------------------
                var searching = new SongSearching();
                int browsed = Total(searching.Search("", SortAttribute.Name));
                Debug.Log($"PROBE INFO: an empty query returns {browsed}");
                Check("browsing with no query shows every song", browsed == entries.Count);

                // ---- the negative control, FIRST -------------------------------------------
                // Proved before any green below is believed. A search that cannot discriminate
                // would return everything for this too, and then "a real artist returns songs"
                // would mean nothing.
                searching.Reset();
                int nonsense = Total(searching.Search("qzzxwvjjkk", SortAttribute.Name));
                Debug.Log($"PROBE INFO: a nonsense query returns {nonsense}");
                Check("a query no song can match returns nothing", nonsense == 0);

                // YARG_PROBE_SELFTEST=1 inverts that one expectation, so the run can be WATCHED
                // going red before its green is trusted. A pass from a probe whose failure
                // channel has never been seen to work is indistinguishable from a probe that
                // cannot fail.
                if (Environment.GetEnvironmentVariable("YARG_PROBE_SELFTEST") == "1")
                {
                    Check("SELFTEST: this check is wrong on purpose and must fail",
                        nonsense == entries.Count);
                }

                // ---- the measurement --------------------------------------------------------
                // Artists the catalogue actually has, counted from the catalogue itself rather
                // than hardcoded, so this keeps working when the library changes.
                var topArtists = entries
                    .GroupBy(e => e.Artist.SearchStr)
                    .Where(g => !string.IsNullOrWhiteSpace(g.Key))
                    .OrderByDescending(g => g.Count())
                    .Take(3)
                    .ToList();

                foreach (var artist in topArtists)
                {
                    searching.Reset();
                    int unqualified = Total(searching.Search(artist.Key, SortAttribute.Name));
                    Debug.Log($"PROBE INFO: \"{artist.Key}\" (unqualified) returns {unqualified}, " +
                        $"catalogue has {artist.Count()}");
                    Check($"an unqualified search for \"{artist.Key}\" finds server songs",
                        unqualified > 0);

                    searching.Reset();
                    int qualified = Total(searching.Search("artist:" + artist.Key, SortAttribute.Name));
                    Debug.Log($"PROBE INFO: \"artist:{artist.Key}\" returns {qualified}, " +
                        $"catalogue has {artist.Count()}");
                    Check($"artist:\"{artist.Key}\" finds server songs", qualified > 0);
                }

                // Names too, since the unqualified search ranks on name and artist together and
                // a defect could live in either.
                var firstNamed = entries.FirstOrDefault(e => !string.IsNullOrWhiteSpace(e.Name.SearchStr));
                if (firstNamed != null)
                {
                    searching.Reset();
                    int byName = Total(searching.Search(firstNamed.Name.SearchStr, SortAttribute.Name));
                    Debug.Log($"PROBE INFO: the title \"{firstNamed.Name.SearchStr}\" returns {byName}");
                    Check("searching a server song's own title finds it", byName > 0);
                }

                // The one search that SHOULD distinguish them, and the one Jay's report would
                // also explain if it were inverted.
                searching.Reset();
                int mirrored = Total(searching.Search("server:yes", SortAttribute.Name));
                Debug.Log($"PROBE INFO: \"server:yes\" returns {mirrored}");
                Check("server:yes keeps the server's songs", mirrored == entries.Count);

                searching.Reset();
                int notMirrored = Total(searching.Search("server:no", SortAttribute.Name));
                Debug.Log($"PROBE INFO: \"server:no\" returns {notMirrored}");
                Check("server:no hides them all, there being nothing local here",
                    notMirrored == 0);

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
