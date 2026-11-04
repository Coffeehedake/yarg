using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Audio.BASS;
using YARG.Core;
using YARG.Core.Audio;
using YARG.Core.Song;
using YARG.Core.Song.Cache;
using YARG.Helpers;
using YARG.Menu.MusicLibrary;
using YARG.Settings;
using YARG.Song;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Drives the real sort-and-fill pipeline over a catalogue of server songs and asks whether
    /// the containers the library search reads actually end up holding them.
    /// </summary>
    /// <remarks>
    /// <para>
    /// This exists because <see cref="SearchRemoteProbe"/> came back green and therefore moved
    /// the question rather than answering it. That probe injected <c>_sortTitles</c> directly and
    /// proved the SEARCH is fine: 4,085 server entries in, 155 hits for "nirvana",
    /// <c>server:yes</c> 4085 and <c>server:no</c> 0. So if a real game's search returns only
    /// local songs, the containers did not hold the remote ones, and the only code between the
    /// merge and those containers is <c>SongSorting.SortEntries</c> and
    /// <c>SongContainer.FillContainers</c> — exactly the two things the other probe stepped over.
    /// </para>
    /// <para>
    /// That gap is not hypothetical, and it is the same gap that hid the last defect. Upstream's
    /// Sort by Date Added threw on a <see cref="RemoteSongEntry"/> inside a <c>Parallel.For</c>;
    /// the AggregateException killed <c>SortEntries</c>, <c>FillContainers</c> never ran, and the
    /// library silently kept the songs it already had while the log said "3952 entries merged"
    /// four lines above the stack trace. A second filter of that shape anywhere in the sorters
    /// would present exactly as "search only finds local songs".
    /// </para>
    /// <para>
    /// So the measurement is a comparison, not a single number: <c>SongContainer.Count</c> counts
    /// what the merge produced, and the sorted categories count what search can reach. The two
    /// agreeing is the only thing that says the pipeline kept everything. A probe that printed
    /// one of them would pass on the defect.
    /// </para>
    /// <para>
    /// It runs the sorters through reflection because <c>SortEntries</c> is <c>internal</c> to
    /// Assembly-CSharp and <c>FillContainers</c> is <c>private</c> — the editor assembly is a
    /// different assembly, so neither is reachable by name. Reflection here is not a shortcut
    /// past an API; it is the only way to put the production code under measurement at all, and
    /// the probe fails loudly if a member it needs has been renamed rather than quietly
    /// measuring nothing.
    /// </para>
    /// <para>
    /// Real settings are loaded when they will load, because the sorters consult several of them
    /// (<c>MaxSongRating</c>, <c>UnratedSongRating</c>, <c>CensorMatureContent</c>) and defaults
    /// would be a different experiment from Jay's. Which of the two it got is printed, so a
    /// result is never read as being about settings it was not run with.
    /// </para>
    /// <para>Needs <c>YARG_CATALOG_JSON</c>. Without it, INCONCLUSIVE and exit 2 — never a pass.</para>
    /// </remarks>
    public static class LibraryPipelineProbe
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

        private static FieldInfo ContainerField(string name)
        {
            var field = typeof(SongContainer).GetField(name,
                BindingFlags.NonPublic | BindingFlags.Static);
            if (field == null)
            {
                throw new Exception($"SongContainer.{name} is gone - this probe reaches it by " +
                    "reflection and measures nothing without it");
            }
            return field;
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

                PathHelper.Init();

                // Every VolumeSetting invokes its callback on construction and those reach
                // GlobalAudioHandler, so a settings container cannot exist in a process with no
                // audio backend. Nothing is played; nothing is heard.
                GlobalAudioHandler.Initialize<BassAudioManager>();

                string settingsSource;
                try
                {
                    SettingsManager.LoadSettings();
                    settingsSource = "Jay's own settings.json";
                }
                catch (Exception ex)
                {
                    Debug.Log("PROBE INFO: LoadSettings failed (" + ex.GetType().Name +
                        "), falling back to a default container");
                    var prop = typeof(SettingsManager).GetProperty(nameof(SettingsManager.Settings),
                        BindingFlags.Public | BindingFlags.Static);
                    prop?.SetValue(null, new SettingsManager.SettingContainer());
                    settingsSource = "DEFAULTS, not Jay's settings";
                }

                if (SettingsManager.Settings == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: no settings container, and the sorters read settings");
                    EditorApplication.Exit(2);
                    return;
                }

                var s = SettingsManager.Settings;
                Debug.Log($"PROBE INFO: settings come from {settingsSource}");
                Debug.Log($"PROBE INFO: LibrarySort={s.LibrarySort} MaxSongRating={s.MaxSongRating.Value} " +
                    $"UnratedSongRating={s.UnratedSongRating.Value} " +
                    $"CensorMatureContent={s.CensorMatureContent.Value} " +
                    $"AllowDuplicateSongs={s.AllowDuplicateSongs.Value} " +
                    $"BrowseServerLibrary={s.BrowseServerLibrary.Value}");

                // ---- build the cache the merge would have produced ---------------------------
                var songs = (JArray) JObject.Parse(File.ReadAllText(catalogPath))["songs"]!;
                var cache = new SongCache();
                int built = 0;
                foreach (var node in songs.OfType<JObject>())
                {
                    var entry = RemoteCatalog.FromJson(node);
                    if (!cache.Entries.TryGetValue(entry.Hash, out var list))
                    {
                        cache.Entries.Add(entry.Hash, list = new List<SongEntry>());
                    }
                    list.Add(entry);
                    ++built;
                }

                Debug.Log($"PROBE INFO: {built} entries in {cache.Entries.Count} distinct hashes");

                ContainerField("_songCache").SetValue(null, cache);

                // ---- the real sorters, the real fill ----------------------------------------
                var sortedField = ContainerField("_sortedSongs");
                object sortedSongs = sortedField.GetValue(null);

                var sortEntries = typeof(SongSorting).GetMethod("SortEntries",
                    BindingFlags.NonPublic | BindingFlags.Static)
                    ?? typeof(SongSorting).GetMethod("SortEntries",
                        BindingFlags.Public | BindingFlags.Static);
                if (sortEntries == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: SongSorting.SortEntries not found");
                    EditorApplication.Exit(2);
                    return;
                }

                bool sorted = false;
                try
                {
                    sortEntries.Invoke(null, new[] { (object) cache, sortedSongs });
                    sorted = true;
                }
                catch (TargetInvocationException ex)
                {
                    // The shape of the last defect, named rather than swallowed: anything that
                    // throws per-entry inside the sorters arrives here as an AggregateException
                    // and costs the whole library.
                    Fail("SortEntries threw: " + (ex.InnerException ?? ex));
                }

                Check("the sorters ran without throwing", sorted);

                bool filled = false;
                if (sorted)
                {
                    var fill = typeof(SongContainer).GetMethod("FillContainers",
                        BindingFlags.NonPublic | BindingFlags.Static);
                    if (fill == null)
                    {
                        Debug.LogError("PROBE INCONCLUSIVE: SongContainer.FillContainers not found");
                        EditorApplication.Exit(2);
                        return;
                    }

                    try
                    {
                        fill.Invoke(null, null);
                        filled = true;
                    }
                    catch (TargetInvocationException ex)
                    {
                        Fail("FillContainers threw: " + (ex.InnerException ?? ex));
                    }
                }

                Check("FillContainers ran without throwing", filled);
                if (!filled)
                {
                    Debug.Log($"PROBE RESULT: FAIL ({_failures})");
                    EditorApplication.Exit(1);
                    return;
                }

                // ---- the comparison that is the whole point ---------------------------------
                int count = SongContainer.Count;
                Debug.Log($"PROBE INFO: SongContainer.Count = {count}");
                Check($"the container kept all {built} merged songs", count == built);

                // Every sort the library offers, because the player's sort decides which
                // container search reads, and one broken sort would be invisible from another.
                var interesting = new[]
                {
                    SortAttribute.Name, SortAttribute.Artist, SortAttribute.Album,
                    SortAttribute.Genre, SortAttribute.Charter, SortAttribute.Source,
                    SortAttribute.Year, SortAttribute.SongLength, SortAttribute.DateAdded,
                    SortAttribute.Artist_Album, SortAttribute.Folder, SortAttribute.Subgenre,
                };

                foreach (var sort in interesting)
                {
                    int total;
                    try
                    {
                        total = Total(SongContainer.GetSortedCategory(sort));
                    }
                    catch (Exception ex)
                    {
                        Fail($"GetSortedCategory({sort}) threw: {ex.GetType().Name}: {ex.Message}");
                        continue;
                    }

                    Debug.Log($"PROBE INFO: sort {sort} holds {total}");
                    Check($"sort {sort} reaches every song", total == built);
                }

                // ---- and the search, at the sort the player is actually on -------------------
                var topArtist = JObject.Parse(File.ReadAllText(catalogPath))["songs"]!
                    .OfType<JObject>()
                    .GroupBy(n => ((string) n["artist"] ?? "").ToLowerInvariant())
                    .Where(g => !string.IsNullOrWhiteSpace(g.Key))
                    .OrderByDescending(g => g.Count())
                    .First();

                var searching = new SongSearching();
                int hits = Total(searching.Search(topArtist.Key, s.LibrarySort));
                Debug.Log($"PROBE INFO: searching \"{topArtist.Key}\" at sort {s.LibrarySort} " +
                    $"returns {hits}, catalogue has {topArtist.Count()}");
                Check($"a search at the player's own sort finds server songs", hits > 0);

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
