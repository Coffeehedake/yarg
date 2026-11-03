#nullable enable

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using YARG.Core.Logging;
using YARG.Helpers;

namespace YARG.Song.RemoteLibrary
{
    /// <summary>
    /// Bounds the size of <see cref="PathHelper.ServerCachePath"/>, the folder that keeps songs
    /// fetched one at a time because somebody played them.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Browsing the server library (<c>BrowseServerLibrary</c>) makes every song on the server
    /// playable without mirroring it, and a song is kept once it has been played. Nothing removed
    /// them, so the cache grew one song at a time toward the size of the whole server — which is
    /// the exact outcome browsing exists to avoid.
    /// </para>
    /// <para>
    /// <b>Why this may delete when <see cref="SongServerSync"/> deliberately never does.</b> That
    /// refusal is about the MIRROR, which is a library somebody chose to download and may be the
    /// only copy of; its comment says getting it wrong "costs somebody their library". The cache
    /// is a different thing: nobody asked for any particular song in it, each one arrived as a
    /// side effect of pressing play, and each can be fetched again. The two folders are separate
    /// on disk and this touches only the cache. It never looks at <c>ServerLibrary</c>, and it
    /// never looks at a song folder the player added themselves.
    /// </para>
    /// <para>
    /// <b>Eviction costs latency, and — unlike the server's pack cache — it CAN cost data.</b> The
    /// server-side cache re-packs an evicted archive from a folder still on its own disk, so the
    /// bytes are never really gone. Here the source is someone else's machine. If the server has
    /// dropped the song in the meantime, an evicted copy was the last one. That is the honest
    /// difference, it is why the default bound is generous rather than tight, and it is why a
    /// song is never evicted while it is the one being played.
    /// </para>
    /// <para>
    /// <b>Access time is tracked here rather than read from the filesystem, and that is measured
    /// rather than preferred.</b> Windows last-access updates are "System Managed" and can be off
    /// entirely, but that is not the reason: <see cref="SongContainer"/> adds the cache to the
    /// scanned directories, so a library refresh READS every <c>.sng</c> in it and resets every
    /// atime to the same moment. The filesystem's own signal is destroyed by our own scanner on
    /// each scan, so it cannot order anything. <see cref="RecordPlayed"/> keeps the order instead,
    /// in one small file outside the song folders so no scanner ever sees it.
    /// </para>
    /// </remarks>
    public static class ServerCacheBudget
    {
        /// <summary>One cached song, as the chooser needs to see it.</summary>
        public readonly struct Entry
        {
            public readonly string Hash;
            public readonly long Bytes;

            /// <summary>Unix seconds. Older sorts first; 0 means "never recorded".</summary>
            public readonly long PlayedAt;

            public Entry(string hash, long bytes, long playedAt)
            {
                Hash = hash;
                Bytes = bytes;
                PlayedAt = playedAt;
            }
        }

        /// <summary>The access index, beside the song folders rather than inside one.</summary>
        private const string IndexFileName = "played.index";

        /// <summary>
        /// Scratch files <see cref="RemoteSongFetcher"/> writes at the cache root. They are not
        /// songs and must never be mistaken for one by a sweep.
        /// </summary>
        private static readonly string[] NotSongFolders = { "scan.bin", "scan-badsongs.txt", IndexFileName };

        /// <summary>
        /// Chooses which songs to evict, oldest-played first, until the total fits
        /// <paramref name="maxBytes"/>. Returns them in the order they should go.
        /// </summary>
        /// <remarks>
        /// Pure, and public, so a probe can measure the decision without a disk, a server or a
        /// game. The thing being protected is somebody's songs and the mechanism is arithmetic
        /// over sizes and timestamps; a compile cannot tell a correct comparison from a reversed
        /// one, and neither can a run that happens to evict something.
        ///
        /// <paramref name="maxBytes"/> of zero or less means unbounded and chooses nothing.
        /// A protected hash is never chosen, even if that leaves the cache over budget — being
        /// over budget is recoverable and deleting the song now playing is not.
        /// </remarks>
        public static List<string> ChooseEvictions(IReadOnlyList<Entry> entries, long maxBytes,
            IReadOnlyCollection<string>? protect = null)
        {
            var chosen = new List<string>();
            if (entries == null || entries.Count == 0 || maxBytes <= 0)
            {
                return chosen;
            }

            long total = 0;
            foreach (var e in entries)
            {
                total += e.Bytes;
            }

            if (total <= maxBytes)
            {
                return chosen;
            }

            var isProtected = protect == null
                ? new HashSet<string>(StringComparer.OrdinalIgnoreCase)
                : new HashSet<string>(protect, StringComparer.OrdinalIgnoreCase);

            // Oldest played first. A song with no recorded play (PlayedAt 0) sorts oldest, which
            // is right: it is either from before this index existed or was fetched and abandoned.
            // Hash breaks ties so the order is total and a probe can assert on it.
            var ordered = entries
                .Where(e => !isProtected.Contains(e.Hash))
                .OrderBy(e => e.PlayedAt)
                .ThenBy(e => e.Hash, StringComparer.Ordinal)
                .ToList();

            foreach (var e in ordered)
            {
                if (total <= maxBytes)
                {
                    break;
                }

                chosen.Add(e.Hash);
                total -= e.Bytes;
            }

            return chosen;
        }

        /// <summary>Records that a song was played, so the chooser can order by it.</summary>
        public static void RecordPlayed(string chartHash)
        {
            if (string.IsNullOrEmpty(chartHash))
            {
                return;
            }

            try
            {
                var index = ReadIndex();
                index[chartHash] = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                WriteIndex(index);
            }
            catch (Exception ex)
            {
                // Losing the order costs eviction quality, never data: the chooser falls back to
                // treating unrecorded songs as oldest. Not worth failing a play over.
                YargLogger.LogWarning($"Could not record the server cache play order: {ex.Message}");
            }
        }

        /// <summary>Everything currently in the cache, with sizes and play times.</summary>
        public static List<Entry> Survey()
        {
            var entries = new List<Entry>();
            string root = PathHelper.ServerCachePath;
            if (string.IsNullOrEmpty(root) || !Directory.Exists(root))
            {
                return entries;
            }

            var index = ReadIndex();
            foreach (string folder in Directory.EnumerateDirectories(root))
            {
                string hash = Path.GetFileName(folder);
                if (NotSongFolders.Contains(hash, StringComparer.OrdinalIgnoreCase))
                {
                    continue;
                }

                long bytes = 0;
                try
                {
                    foreach (string f in Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories))
                    {
                        bytes += new FileInfo(f).Length;
                    }
                }
                catch (Exception)
                {
                    // A folder that cannot be measured is one that should not be evicted either.
                    continue;
                }

                entries.Add(new Entry(hash, bytes, index.TryGetValue(hash, out long at) ? at : 0));
            }

            return entries;
        }

        /// <summary>What an enforcement run did.</summary>
        public readonly struct Result
        {
            public readonly int Evicted;
            public readonly int Skipped;
            public readonly long BytesFreed;
            public readonly long BytesAfter;

            public Result(int evicted, int skipped, long bytesFreed, long bytesAfter)
            {
                Evicted = evicted;
                Skipped = skipped;
                BytesFreed = bytesFreed;
                BytesAfter = bytesAfter;
            }
        }

        /// <summary>
        /// Brings the cache within <paramref name="maxBytes"/>, never touching a protected hash.
        /// </summary>
        /// <remarks>
        /// A folder whose files are open cannot be removed on Windows. That is not an error here:
        /// it is skipped and counted, exactly as the server's pack cache does, and the next run
        /// will get it. The alternative — forcing it — would be deleting a file something is
        /// reading.
        /// </remarks>
        public static Result Enforce(long maxBytes, IReadOnlyCollection<string>? protect = null)
        {
            var entries = Survey();
            var chosen = ChooseEvictions(entries, maxBytes, protect);
            if (chosen.Count == 0)
            {
                return new Result(0, 0, 0, entries.Sum(e => e.Bytes));
            }

            var sizes = entries.ToDictionary(e => e.Hash, e => e.Bytes, StringComparer.OrdinalIgnoreCase);
            int evicted = 0, skipped = 0;
            long freed = 0;

            foreach (string hash in chosen)
            {
                string folder = Path.Combine(PathHelper.ServerCachePath, hash);
                try
                {
                    Directory.Delete(folder, true);
                    evicted++;
                    freed += sizes.TryGetValue(hash, out long b) ? b : 0;
                }
                catch (Exception ex)
                {
                    skipped++;
                    YargLogger.LogWarning($"Server cache: could not evict {hash}: {ex.Message}");
                }
            }

            if (evicted > 0)
            {
                var index = ReadIndex();
                foreach (string hash in chosen)
                {
                    index.Remove(hash);
                }

                WriteIndex(index);
                YargLogger.LogFormatInfo("Server cache: evicted {0} song(s), freed {1} bytes", evicted, freed);
            }

            return new Result(evicted, skipped, freed, entries.Sum(e => e.Bytes) - freed);
        }

        // ------------------------------------------------------------------
        // The access index: "<hash> <unix seconds>" per line.
        //
        // Deliberately not JSON and deliberately not inside a song folder. A stray file in a
        // folder the scanner walks is a question nobody wants to answer later, and a line-based
        // format means a truncated write costs one song's order rather than all of it.
        // ------------------------------------------------------------------

        private static Dictionary<string, long> ReadIndex()
        {
            var index = new Dictionary<string, long>(StringComparer.OrdinalIgnoreCase);
            string root = PathHelper.ServerCachePath;
            if (string.IsNullOrEmpty(root))
            {
                return index;
            }

            string path = Path.Combine(root, IndexFileName);
            if (!File.Exists(path))
            {
                return index;
            }

            try
            {
                foreach (string line in File.ReadAllLines(path))
                {
                    int sp = line.IndexOf(' ');
                    if (sp <= 0)
                    {
                        continue;
                    }

                    if (long.TryParse(line.AsSpan(sp + 1), NumberStyles.Integer,
                            CultureInfo.InvariantCulture, out long at))
                    {
                        index[line.Substring(0, sp)] = at;
                    }
                }
            }
            catch (Exception ex)
            {
                YargLogger.LogWarning($"Could not read the server cache play order: {ex.Message}");
            }

            return index;
        }

        private static void WriteIndex(Dictionary<string, long> index)
        {
            string root = PathHelper.ServerCachePath;
            if (string.IsNullOrEmpty(root))
            {
                return;
            }

            Directory.CreateDirectory(root);
            var lines = index.Select(kv => kv.Key + " " + kv.Value.ToString(CultureInfo.InvariantCulture));
            File.WriteAllLines(Path.Combine(root, IndexFileName), lines);
        }
    }
}
