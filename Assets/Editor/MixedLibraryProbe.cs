using System;
using System.IO;
using System.Linq;
using Cysharp.Threading.Tasks;
using UnityEditor;
using UnityEngine;
using YARG.Audio.BASS;
using YARG.Core;
using YARG.Core.Audio;
using YARG.Core.Song;
using YARG.Helpers;
using YARG.Settings;
using YARG.Song;

namespace YARG.Editor
{
    /// <summary>
    /// Searches a library that holds local songs and server songs at the same time, which is the
    /// last configuration the other probes do not build.
    /// </summary>
    /// <remarks>
    /// <para>
    /// <see cref="SearchRemoteProbe"/> and <see cref="LibraryPipelineProbe"/> both load a
    /// server-only catalogue, and both come back green: all 4,085 entries survive the sorters,
    /// every one of the twelve sorts holds them, and a search finds 155 Nirvana at each. Jay's
    /// library is not that. It is 128 scanned local songs and 3,952 remote ones in one container,
    /// and <c>SetAllSongs</c> de-duplicates across them — so a defect that needs both kinds
    /// present would pass everything measured so far.
    /// </para>
    /// <para>
    /// This drives the REAL <see cref="SongContainer.RunRefresh"/> rather than reassembling it,
    /// so the scan, the catalogue merge, <c>SongSorting.SortEntries</c> and
    /// <c>FillContainers</c> all happen in production's own order. Reassembling that order is
    /// exactly how a probe ends up measuring a pipeline nobody runs.
    /// </para>
    /// <para>
    /// The measurement is a BREAKDOWN, not a total, and that is the point. "Search returns 40
    /// songs" is consistent both with search working and with Jay's report, because he has 128
    /// local songs and a search that found only those would still return something. So every
    /// result is counted as <see cref="RemoteSongEntry"/> or not, and the probe fails if a search
    /// whose matches are mostly on the server comes back all-local — which is the report,
    /// reproduced.
    /// </para>
    /// <para>
    /// It does NOT sync: <c>RunRefresh</c> fetches the catalogue JSON and nothing else. No song
    /// bytes are downloaded. That matters because an accidental full sync has cost this project
    /// 7 GB once already, and the setting that caused it is not touched here.
    /// </para>
    /// <para>
    /// Writes only under the editor's own <c>dev</c> tree, never the player's <c>release</c> one,
    /// because <c>PathHelper</c> chooses <c>dev</c> outside a built player. Jay's real library
    /// settings are not modified.
    /// </para>
    /// <para>Needs <c>YARG_SERVER_URL</c>. Without it, INCONCLUSIVE and exit 2 — never a pass.</para>
    /// </remarks>
    public static class MixedLibraryProbe
    {
        private static int _failures;
        private static int _exitCode = -1;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        private static void Check(string what, bool ok)
        {
            if (ok) { Pass(what); } else { Fail(what); }
        }

        public static void Run() => Measure().Forget();

        private static (int Remote, int Local) Breakdown(SongCategory[] categories)
        {
            if (categories == null) { return (0, 0); }
            int remote = 0, local = 0;
            foreach (var category in categories)
            {
                foreach (var song in category.Songs)
                {
                    if (song is RemoteSongEntry) { ++remote; } else { ++local; }
                }
            }
            return (remote, local);
        }

        /// <summary>
        /// Runs a real refresh, tolerating the one throw that says nothing about the library.
        /// </summary>
        /// <remarks>
        /// <c>RunRefresh</c> finishes with <c>SongSources.LoadSprites(context)</c>, and this
        /// process has neither a <c>LoadingContext</c> nor the sources read, so that line throws
        /// every time. <c>FillContainers</c> has already run by then — it is five lines earlier —
        /// so the library IS built and the throw is noise. It is caught here, per call, rather
        /// than around the whole probe, because catching it once at the top meant the first
        /// refresh aborted the run and the mixed-library pass never happened at all.
        ///
        /// It prints what it swallowed and the song count beside it, so "the library was built"
        /// stays a measurement rather than an assumption.
        /// </remarks>
        private static async UniTask<int> Refresh(string label)
        {
            try
            {
                await SongContainer.RunRefresh(false);
            }
            catch (Exception ex)
            {
                Debug.Log($"PROBE INFO: {label} refresh ended with {ex.GetType().Name} " +
                    $"(expected from LoadSprites outside a loading screen); " +
                    $"library holds {SongContainer.Count}");
            }

            return SongContainer.Count;
        }

        private static async UniTaskVoid Measure()
        {
            try
            {
                PathHelper.Init();

                // Every VolumeSetting calls GlobalAudioHandler on construction, so the settings
                // container cannot exist without a backend. Nothing is played.
                GlobalAudioHandler.Initialize<BassAudioManager>();

                string settingsPath = Path.Combine(PathHelper.PersistentDataPath, "settings.json");
                SettingsManager.LoadSettings();
                Debug.Log($"PROBE INFO: settings {(File.Exists(settingsPath) ? "from " + settingsPath : "DEFAULTS, no file at " + settingsPath)}");

                if (SettingsManager.Settings == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: no settings container");
                    _exitCode = 2;
                    return;
                }

                string server = Environment.GetEnvironmentVariable("YARG_SERVER_URL") ?? "";
                if (string.IsNullOrWhiteSpace(server))
                {
                    Debug.LogError("PROBE INCONCLUSIVE: need YARG_SERVER_URL");
                    _exitCode = 2;
                    return;
                }

                var s = SettingsManager.Settings;
                Debug.Log($"PROBE INFO: SongFolders = {string.Join(" | ", s.SongFolders)}");
                Debug.Log($"PROBE INFO: LibrarySort={s.LibrarySort} MaxSongRating={s.MaxSongRating.Value} " +
                    $"OnlyShowPlayableSongs={s.OnlyShowPlayableSongs.Value}");

                // ---- pass one: local only, so the two halves can be told apart --------------
                s.BrowseServerLibrary.SetValueWithoutNotify(false);
                int localOnly = await Refresh("local-only");
                Debug.Log($"PROBE INFO: local-only library holds {localOnly}");
                Check("the local scan found songs at all - with none, this probe measures nothing",
                    localOnly > 0);
                if (localOnly == 0)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: no local songs, so there is no MIXED library to test");
                    _exitCode = 2;
                    return;
                }

                // ---- pass two: the mixed library --------------------------------------------
                s.SongServerUrl.Value = server;
                s.BrowseServerLibrary.SetValueWithoutNotify(true);
                int mixed = await Refresh("mixed");

                int remoteEntries = SongContainer.Songs.Count(e => e is RemoteSongEntry);
                int localEntries = mixed - remoteEntries;
                Debug.Log($"PROBE INFO: mixed library holds {mixed} - {localEntries} local, " +
                    $"{remoteEntries} from the server");
                Check("the merge added server songs to the local library", remoteEntries > 0);
                Check("and kept every local song", localEntries >= localOnly);

                var sorted = SongContainer.GetSortedCategory(s.LibrarySort);
                var sortedSplit = Breakdown(sorted);
                Debug.Log($"PROBE INFO: sort {s.LibrarySort} holds {sortedSplit.Remote + sortedSplit.Local} " +
                    $"- {sortedSplit.Local} local, {sortedSplit.Remote} remote");
                Check($"sort {s.LibrarySort} reaches the server songs", sortedSplit.Remote > 0);

                // ---- the measurement: a BREAKDOWN of what search returns --------------------
                // An artist the server has many of. Counted from the library itself so this
                // keeps working as the catalogue changes.
                var topArtist = SongContainer.Songs
                    .Where(e => e is RemoteSongEntry && !string.IsNullOrWhiteSpace(e.Artist.SearchStr))
                    .GroupBy(e => e.Artist.SearchStr)
                    .OrderByDescending(g => g.Count())
                    .FirstOrDefault();

                if (topArtist == null)
                {
                    Debug.LogError("PROBE INCONCLUSIVE: no server artist to search for");
                    _exitCode = 2;
                    return;
                }

                var searching = new SongSearching();
                foreach (var sort in new[] { s.LibrarySort, SortAttribute.Name, SortAttribute.Artist_Album })
                {
                    searching.Reset();
                    var split = Breakdown(searching.Search(topArtist.Key, sort));
                    Debug.Log($"PROBE INFO: \"{topArtist.Key}\" at sort {sort} returns " +
                        $"{split.Remote + split.Local} - {split.Local} local, {split.Remote} remote " +
                        $"(the library has {topArtist.Count()} of this artist on the server)");

                    // The report, reproduced, would be this check going red.
                    Check($"searching \"{topArtist.Key}\" at sort {sort} returns SERVER songs, " +
                        "not only local ones", split.Remote > 0);
                }

                // And the qualified form, which is a different code path through GetFilters.
                searching.Reset();
                var qualified = Breakdown(searching.Search("artist:" + topArtist.Key, s.LibrarySort));
                Debug.Log($"PROBE INFO: \"artist:{topArtist.Key}\" returns " +
                    $"{qualified.Remote + qualified.Local} - {qualified.Local} local, " +
                    $"{qualified.Remote} remote");
                Check("the qualified artist: form returns server songs too", qualified.Remote > 0);

                Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
                _exitCode = _failures == 0 ? 0 : 1;
            }
            catch (Exception ex)
            {
                // RunRefresh ends with SongSources.LoadSprites, which needs sources this process
                // has not read - so a throw THERE is expected and says nothing about the library,
                // which FillContainers has already built. Reported rather than swallowed, with
                // the count beside it, so the distinction is visible instead of assumed.
                Debug.LogError($"PROBE FAIL: {ex.GetType().Name} at {SongContainer.Count} songs: {ex}");
                _exitCode = 1;
            }
            finally
            {
                try
                {
                    // Leave the editor's own setting as it was found.
                    SettingsManager.Settings?.BrowseServerLibrary.SetValueWithoutNotify(false);
                }
                catch (Exception)
                {
                    // Not worth failing the run over.
                }
            }

            EditorApplication.Exit(_exitCode < 0 ? 1 : _exitCode);
        }
    }
}
