#nullable enable
using System;
using System.IO;
using YARG.Core;
using YARG.Core.Audio;
using YARG.Core.Chart;
using YARG.Core.IO;
using YARG.Core.Song;
using YARG.Core.Venue;

namespace YARG.Song
{
    /// <summary>
    /// A song the server knows about and this machine may not hold a single byte of.
    /// </summary>
    /// <remarks>
    /// This is ADR-004 increment 3, and the ADR says it cannot be done without a new YARG.Core
    /// API. That claim was reasoned, not measured, and it is wrong. It was reached by looking at
    /// <c>SngEntry</c> and <c>UnpackedIniEntry</c>, which really are <c>internal sealed</c> with
    /// private constructors and really are unreachable - <c>InternalsVisibleTo</c> names only
    /// ChartDump, the unit tests and the benchmarks, not this assembly. The mistake was stopping
    /// there. The BASE class is the door:
    ///
    ///   - <c>SongEntry</c> is <c>public abstract</c> with a <c>protected</c> constructor, so it
    ///     can be subclassed from here.
    ///   - <c>_metadata</c>, <c>_parts</c>, <c>_hash</c>, <c>_settings</c>, <c>_parsedYear</c> and
    ///     <c>_yearAsNumber</c> are all <c>protected</c>, so they can be filled.
    ///   - <c>SetSortStrings()</c> is <c>protected</c>, and it derives Name/Artist/Album/Genre/
    ///     Charter/Source/Playlist - which are <c>private</c> with getters only - from
    ///     <c>_metadata</c>. Without it a subclass can carry metadata and still browse blank.
    ///   - every loader is <c>public abstract</c>, so fetching is ours to define.
    ///
    /// Two things follow that are worth stating because they are easy to lose:
    ///
    /// <c>Serialize</c> is <c>internal virtual</c>, so an entry of this type CANNOT be written
    /// into <c>songcache.bin</c>. That is not a limitation to work around, it is the repo's
    /// "never generate songcache.bin" rule being enforced by the type system instead of by
    /// discipline. These entries are re-supplied by the server at every launch, and the cache
    /// stays exactly what it is: a record of local files.
    ///
    /// Every downcast in both assemblies is <c>is RBCONEntry</c> - a pattern test with a
    /// fallthrough, never a cast that throws - so an entry of a type upstream has never seen
    /// takes the else branch everywhere instead of crashing.
    ///
    /// Loading is deliberately NOT implemented here. The bytes of a <c>.sng</c> cannot be turned
    /// into a chart by this class, because the code that does that lives on <c>SngEntry</c> and
    /// is unreachable for the same accessibility reason that started all this. The intended route
    /// is to materialise the <c>.sng</c> and let a real scan produce a real entry for playback,
    /// at the seam in <c>GameManager.Loading.Start</c> that ADR-004 already measured. Until that
    /// exists these return null rather than pretending.
    /// </remarks>
    public sealed class RemoteSongEntry : SongEntry
    {
        private readonly string   _chartHash;
        private readonly string   _packageHash;
        private readonly DateTime _lastWrite;

        /// <summary>
        /// The real, scanned entry for this song once its bytes have been fetched.
        /// </summary>
        /// <remarks>
        /// This class deliberately never becomes playable itself. Turning .sng bytes into a
        /// chart is <c>SngEntry</c>'s job and that class is unreachable from here, so the fetch
        /// path scans the downloaded file and keeps the entry the scanner produced. Holding it
        /// means a song played twice is only scanned once.
        /// </remarks>
        private SongEntry? _materialised;

        /// <summary>The chart hash as the server publishes it. Song identity, and nothing else.</summary>
        public string ChartHash => _chartHash;

        public string PackageHash => _packageHash;

        public bool IsMaterialised => _materialised != null;

        /// <summary>The scanned entry to actually play, or null if it has not been fetched.</summary>
        public SongEntry? MaterialisedEntry => _materialised;

        public override EntryType SubType => EntryType.Sng;

        // A location has to be unique and stable, because the container sorts and de-duplicates
        // on it. There is no path until the song is fetched, so the identity stands in - it is
        // the one thing about a remote song that never changes.
        public override string SortBasedLocation => "server://" + _chartHash;

        public override string ActualLocation => _materialised?.ActualLocation ?? "server://" + _chartHash;

        public override DateTime GetLastWriteTime() => _lastWrite;

        /// <summary>
        /// The server's own timestamp, or the downloaded file's once there is one.
        /// </summary>
        /// <remarks>
        /// The base implementation is <c>File.GetLastWriteTime(ActualLocation)</c>, and
        /// <see cref="ActualLocation"/> here is the synthetic <c>server://&lt;hash&gt;</c> for a
        /// song with no bytes on this disk. Windows resolves that against the working directory
        /// and throws <c>IOException: The filename, directory name, or volume label syntax is
        /// incorrect</c>.
        ///
        /// That is not hypothetical. Upstream's #1721 added Sort by Date Added, which calls this
        /// for every entry inside a <c>Parallel.For</c>; the throw became an AggregateException
        /// that killed <c>SongSorting.SortEntries</c>, so <c>FillContainers</c> never ran and the
        /// library silently kept only the songs it had before the catalogue was merged. The log
        /// said <i>"3952 entries merged"</i> immediately above the stack trace, so the merge was
        /// working perfectly and the library still showed 128 songs.
        ///
        /// This is the seam ADR-004 warns about generally: a <see cref="RemoteSongEntry"/> has no
        /// file, so every base method that reaches for one has to be overridden, and a new caller
        /// upstream can turn a dormant one into a crash without touching our code at all.
        /// </remarks>
        public override DateTime GetLastModifiedTime() => _materialised?.GetLastModifiedTime() ?? _lastWrite;

        private RemoteSongEntry(string chartHash, string packageHash, DateTime lastWrite)
        {
            _chartHash = chartHash;
            _packageHash = packageHash;
            _lastWrite = lastWrite;
        }

        /// <summary>
        /// Builds an entry from what the server already computed.
        /// </summary>
        /// <remarks>
        /// The caller supplies the structs rather than JSON, so this class carries no dependency
        /// on the wire format and the mapping stays testable on its own.
        /// </remarks>
        public static RemoteSongEntry Create(
            string         chartHash,
            string         packageHash,
            SongMetadata   metadata,
            AvailableParts parts,
            LoaderSettings settings,
            string         parsedYear,
            int            yearAsNumber,
            DateTime       lastWrite)
        {
            if (string.IsNullOrWhiteSpace(chartHash))
            {
                throw new ArgumentException("a remote song with no chart hash has no identity", nameof(chartHash));
            }

            var entry = new RemoteSongEntry(chartHash, packageHash, lastWrite)
            {
                _metadata = metadata,
                _parts = parts,
                _settings = settings,
                _parsedYear = parsedYear,
                _yearAsNumber = yearAsNumber,
            };

            // HashWrapper.FromString is the whole reason identity survives this round trip: the
            // server publishes SHA1(chart bytes) as hex and this parses the same 20 bytes back.
            // If this ever stops agreeing with the server, every client disagrees about every
            // song and nothing else in the system will say so.
            entry._hash = HashWrapper.FromString(chartHash);

            // Without this the entry has metadata and browses as blank, because the sort strings
            // are private and are only ever derived here. Removing this one call was the probe's
            // negative control: 609 entries still constructed, still merged, still sorted into
            // 609 distinct hashes, and every row in the library was empty. Nothing else in the
            // system notices, which is why the probe checks it per song.
            entry.SetSortStrings();
            return entry;
        }

        /// <summary>
        /// Records the scanned entry produced from this song's fetched bytes.
        /// </summary>
        /// <remarks>
        /// The caller must have checked that <paramref name="real"/> carries the same chart hash.
        /// Identity is the one thing a song cannot be wrong about: attaching an entry for
        /// different bytes here would play a different song than the one the player chose, and
        /// would record the score against this hash.
        /// </remarks>
        public void Materialise(SongEntry real)
        {
            _materialised = real;
        }

        public override SongChart? LoadChart() => null;

        public override StemMixer? LoadAudio(float speed, double volume, bool enableCensoring,
            params SongStem[] ignoreStems) => null;

        public override StemMixer? LoadPreviewAudio(float speed, bool enableCensoring) => null;

        public override YARGImage? LoadAlbumData() => null;

        public override BackgroundResult? LoadBackground(bool enableCensoring,
            bool excludeYarground = false) => null;

        public override FixedArray<byte>? LoadMiloData() => null;

        public override FixedArray<byte>? LoadVocData() => null;
    }
}
