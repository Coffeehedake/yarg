#nullable enable
using System;
using System.IO;
using System.Collections.Generic;
using YARG.Core;
using YARG.Core.Audio;
using YARG.Core.Chart;
using YARG.Core.IO;
using YARG.Core.Song;
using YARG.Core.Venue;
using YARG.Song.RemoteLibrary;
using YARG.Settings;
using YARG.Core.Logging;

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

        /// <summary>
        /// The stem labels the server published for this song, and whether it ships its own
        /// preview file.
        /// </summary>
        /// <remarks>
        /// Only the preview uses these. The game previews a song by mixing every stem, so the
        /// client has to know which stems exist before it can ask for them; see
        /// <see cref="LoadPreviewAudio"/>.
        /// </remarks>
        private readonly List<string> _stems = new();
        private bool _hasOwnPreview;

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
            DateTime       lastWrite,
            IEnumerable<string>? stems = null,
            bool           hasOwnPreview = false)
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

            entry._hasOwnPreview = hasOwnPreview;
            if (stems != null)
            {
                foreach (var stem in stems)
                {
                    if (!string.IsNullOrWhiteSpace(stem))
                    {
                        entry._stems.Add(stem);
                    }
                }
            }

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

        // Every loader below asks the materialised entry first.
        //
        // They all used to return null unconditionally, and that was wrong in a way that is easy
        // to miss: once a song HAS been fetched, its bytes are on this disk and _materialised is
        // a real scanned entry that can answer any of these - yet a preview, album art and the
        // background all stayed blank for the rest of the session. The sibling
        // GetLastModifiedTime had been delegating correctly all along, which is what made the
        // omission look deliberate.
        //
        // Narrower than it sounds, and worth saying so: after a restart a cached song is scanned
        // as an ordinary local entry and never becomes a RemoteSongEntry at all, so this only
        // bites for songs fetched earlier in the same session. It is still wrong.

        public override SongChart? LoadChart() => _materialised?.LoadChart();

        public override StemMixer? LoadAudio(float speed, double volume, bool enableCensoring,
            params SongStem[] ignoreStems)
            => _materialised?.LoadAudio(speed, volume, enableCensoring, ignoreStems);

        /// <summary>
        /// The song's preview, fetched from the server when this machine holds no bytes.
        /// </summary>
        /// <remarks>
        /// <para>
        /// This is ADR-009 reaching the client. The server cuts about thirty seconds out of the
        /// song's own audio by copying whole Ogg pages - no decoding, no transcoding - so a
        /// preview costs a few hundred kilobytes instead of the ~50 MB the whole package would.
        /// </para>
        /// <para>
        /// Blocking the thread is deliberate: <c>PreviewContext</c> calls this inside
        /// <c>await Task.Run(..., token)</c>, so it never runs on the main thread, and it waits
        /// <c>delaySeconds</c> first - scrolling past a song does not fetch it.
        /// </para>
        /// <para>
        /// The stream is handed to the mixer, which owns it from then on; it is disposed here
        /// only when the mixer refuses it, because an undisposed MemoryStream per rejected
        /// preview is a leak nobody would look for.
        /// </para>
        /// <para>
        /// <b>Multi-stem songs are MIXED here, not chosen by the server.</b> Upstream previews a
        /// song by adding every stem to one mixer (<c>CreateAudioMixer</c>), so a server picking
        /// one stem is guessing at a question this method can answer properly. On the live
        /// library that guess was wrong for 908 of 3,860 songs: Rock Band and Guitar Hero
        /// packages keep the backing track in <c>song.ogg</c> and it is empty once every
        /// instrument has its own stem, so the preview was digital silence - every sample zero,
        /// measured. The server now serves one clip per stem and this builds the same
        /// multi-channel mixer the game builds for a local song.
        /// </para>
        /// </remarks>
        public override StemMixer? LoadPreviewAudio(float speed, bool enableCensoring)
        {
            if (_materialised != null)
            {
                return _materialised.LoadPreviewAudio(speed, enableCensoring);
            }

            var server = SettingsManager.Settings?.SongServerUrl.Value;
            if (string.IsNullOrWhiteSpace(server))
            {
                return null;
            }

            // A package that ships its own preview, or has only one stem, needs no mixing - and
            // the single-clip endpoint already serves exactly the right thing for both. Keeping
            // them on that path also keeps the common case at one request: 3,861 of the live
            // library's 4,085 songs have one stem, and 215 ship a preview.
            if (_hasOwnPreview || _stems.Count <= 1)
            {
                return LoadSingleClipPreview(server, speed);
            }

            return LoadMixedPreview(server, speed, enableCensoring);
        }

        /// <summary>One clip, decoded as the whole preview. The original ADR-009 path.</summary>
        private StemMixer? LoadSingleClipPreview(string server, float speed)
        {
            var stream = RemoteSongFetcher.DownloadPreview(server, _chartHash);
            if (stream == null)
            {
                return null;
            }

            // A name, not a path. GlobalAudioHandler only uses it to identify and log the
            // stream, and there is no file here to name.
            var mixer = GlobalAudioHandler.LoadCustomFile(
                "server://" + _chartHash + "/preview.ogg", stream, speed, 0, true,
                SongStem.Preview);

            if (mixer == null)
            {
                stream.Dispose();
                YargLogger.LogFormatWarning("The server's preview for {0} would not decode",
                    _chartHash);
            }
            return mixer;
        }

        /// <summary>
        /// One channel per stem, mirroring YARG.Core's own <c>CreateAudioMixer</c>.
        /// </summary>
        /// <remarks>
        /// <para>
        /// <c>Crowd</c> is skipped because upstream's preview skips it - <c>LoadPreviewAudio</c>
        /// passes <c>SongStem.Crowd</c> as the stem to ignore - and a crowd track under a
        /// thirty-second preview is noise over the thing being previewed.
        /// </para>
        /// <para>
        /// A stem whose clip will not fetch or decode is skipped rather than failing the whole
        /// preview: four stems of five is a preview, and none is silence. The mixer is only
        /// abandoned when NO channel was added, because a mixer with no channels plays nothing
        /// while looking like success - the same shape of bug as the silent stem this replaces.
        /// </para>
        /// </remarks>
        private StemMixer? LoadMixedPreview(string server, float speed, bool enableCensoring)
        {
            var mixer = GlobalAudioHandler.CreateMixer(
                "server://" + _chartHash + "/preview", speed, 0,
                clampStemVolume: false, normalize: true);
            if (mixer == null)
            {
                YargLogger.LogFormatWarning("Could not create a preview mixer for {0}", _chartHash);
                return null;
            }

            int added = 0;
            foreach (var stem in _stems)
            {
                if (!AudioHelpers.SupportedStems.TryGetValue(stem.ToLowerInvariant(),
                        out var stemEnum))
                {
                    // Not a stem the game knows how to place in a mix. Skipped quietly: the
                    // catalogue carries whatever the package held, and this is not an error.
                    continue;
                }
                if (stemEnum == SongStem.Crowd)
                {
                    continue;
                }
                if (enableCensoring && stem.EndsWith("_explicit", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var stream = RemoteSongFetcher.DownloadStemPreview(server, _chartHash, stem);
                if (stream == null)
                {
                    continue;
                }
                if (mixer.AddChannel(stream, stemEnum))
                {
                    added++;
                }
                else
                {
                    stream.Dispose();
                    // Interpolated, not LogFormatWarning: YargLogger's generic overloads plus
                    // their caller-info parameters make any multi-argument LogFormat* call
                    // ambiguous (CS0121), and it reads as a missing method.
                    YargLogger.LogWarning(
                        $"The preview clip for {_chartHash} stem {stem} would not decode");
                }
            }

            if (added == 0)
            {
                mixer.Dispose();
                YargLogger.LogWarning(
                    $"No stem of {_chartHash} produced a usable preview channel out of "
                    + $"{_stems.Count} published");
                return null;
            }

            YargLogger.LogInfo(
                $"Mixed a server preview for {_chartHash} from {added} of {_stems.Count} stems");
            return mixer;
        }

        public override YARGImage? LoadAlbumData() => _materialised?.LoadAlbumData();

        public override BackgroundResult? LoadBackground(bool enableCensoring,
            bool excludeYarground = false)
            => _materialised?.LoadBackground(enableCensoring, excludeYarground);

        public override FixedArray<byte>? LoadMiloData() => _materialised?.LoadMiloData();

        public override FixedArray<byte>? LoadVocData() => _materialised?.LoadVocData();
    }
}
