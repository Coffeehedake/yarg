#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEngine.Networking;
using YARG.Core.IO;
using YARG.Core.Logging;
using YARG.Core.Song;
using YARG.Core.Song.Cache;

namespace YARG.Song.RemoteLibrary
{
    /// <summary>
    /// The server's catalogue, turned into entries the game can browse without holding a byte
    /// of any song.
    /// </summary>
    /// <remarks>
    /// This is the other half of <see cref="RemoteSongEntry"/>: that class proves an entry can
    /// exist without a file, this one supplies them in bulk from the server the player already
    /// configured.
    ///
    /// <para>
    /// The mapping lives HERE rather than in the probe that tests it, which matters more than it
    /// looks. An editor probe carrying its own copy of this mapping would pass against a mapping
    /// the game never runs - the measurement would be of the test, not of the product. The repo
    /// has been caught by that shape of mistake before (a probe that read a JSON field to decide
    /// whether something had been caught, and so recorded a pass for a standard it failed), so
    /// <c>Editor/RemoteEntryProbe.cs</c> calls <see cref="FromJson"/> and nothing else.
    /// </para>
    /// </remarks>
    public static class RemoteCatalog
    {
        /// <summary>The server caps a page at 500 whatever we ask for, so ask for 500.</summary>
        private const int PAGE = 500;

        /// <summary>A library this big is a server fault, not a library. Stops a runaway loop.</summary>
        private const int SANITY_LIMIT = 200_000;

        /// <summary>
        /// Builds one entry from one catalogue row.
        /// </summary>
        /// <remarks>
        /// Every field starts from <see cref="SongMetadata.Default"/> and is overwritten only when
        /// the server actually sent it, so an absent album stays "Unknown Album" - upstream's own
        /// default - instead of becoming an empty string that sorts to the top of the library.
        /// </remarks>
        public static RemoteSongEntry FromJson(JObject n)
        {
            var m = SongMetadata.Default;

            SetIfPresent(n, "name",           v => m.Name = v);
            SetIfPresent(n, "artist",         v => m.Artist = v);
            SetIfPresent(n, "album",          v => m.Album = v);
            SetIfPresent(n, "genre",          v => m.Genre = v);
            SetIfPresent(n, "subgenre",       v => m.Subgenre = v);
            SetIfPresent(n, "charter",        v => m.Charter = v);
            SetIfPresent(n, "source",         v => m.Source = v);
            SetIfPresent(n, "playlist",       v => m.Playlist = v);
            SetIfPresent(n, "year",           v => m.Year = v);
            SetIfPresent(n, "loading_phrase", v => m.LoadingPhrase = v);

            m.SongLength = (long?) n["song_length_ms"] ?? 0;
            m.AlbumTrack = (int?) n["album_track"] ?? 0;
            m.PlaylistTrack = (int?) n["playlist_track"] ?? 0;
            m.Preview = ((long?) n["preview_start_ms"] ?? -1, (long?) n["preview_end_ms"] ?? -1);
            // Through YARG.Core's own converter, never a cast. The wire carries the RAW
            // song.ini number (1 = Family Friendly ... 5 = Sensitive Content, per the wiki and
            // per internal/songini/keys.go on the server) and SongRating is 0-based in a
            // DIFFERENT order, so the cast that used to be here was wrong twice over: every
            // rated song moved one position up the enum - Mature read as Sensitive_Content,
            // Family Friendly as Supervision_Recommended - and an absent rating became 0,
            // which is Family_Friendly rather than Unspecified. The second half is the one
            // that bites quietly: 3,604 of the live server's 4,085 songs publish no rating at
            // all, so they all asserted Family Friendly, and UnratedSongRating - which decides
            // what an unrated LOCAL song counts as - could never apply to a server song.
            // RatingHelper is public in YARG.Core.IO and is what the ini and DTA scanners both
            // use, so this is the game's own mapping rather than a second copy of it.
            m.SongRating = RatingHelper.ParseSongRating((uint) ((int?) n["rating"] ?? 0));

            var parts = AvailableParts.Default;
            if (n["parts"] is JObject p)
            {
                Part(p, "band_difficulty",       ref parts.BandDifficulty);
                Part(p, "five_fret_guitar",      ref parts.FiveFretGuitar);
                Part(p, "five_fret_bass",        ref parts.FiveFretBass);
                Part(p, "five_fret_rhythm",      ref parts.FiveFretRhythm);
                Part(p, "five_fret_coop_guitar", ref parts.FiveFretCoopGuitar);
                Part(p, "keys",                  ref parts.Keys);
                Part(p, "six_fret_guitar",       ref parts.SixFretGuitar);
                Part(p, "six_fret_bass",         ref parts.SixFretBass);
                Part(p, "six_fret_rhythm",       ref parts.SixFretRhythm);
                Part(p, "six_fret_coop_guitar",  ref parts.SixFretCoopGuitar);
                Part(p, "four_lane_drums",       ref parts.FourLaneDrums);
                Part(p, "pro_drums",             ref parts.ProDrums);
                Part(p, "five_lane_drums",       ref parts.FiveLaneDrums);
                Part(p, "elite_drums",           ref parts.EliteDrums);
                Part(p, "pro_guitar_17_fret",    ref parts.ProGuitar_17Fret);
                Part(p, "pro_guitar_22_fret",    ref parts.ProGuitar_22Fret);
                Part(p, "pro_bass_17_fret",      ref parts.ProBass_17Fret);
                Part(p, "pro_bass_22_fret",      ref parts.ProBass_22Fret);
                Part(p, "pro_keys",              ref parts.ProKeys);
                Part(p, "lead_vocals",           ref parts.LeadVocals);
                Part(p, "harmony_vocals",        ref parts.HarmonyVocals);
            }

            // The stems, and whether the package ships its own preview file. Both are only here
            // for the preview: the game previews a song by mixing EVERY stem (YARG.Core's
            // CreateAudioMixer), so the client needs to know which stems exist before it can ask
            // the server for them. Without this it could only take the server's single-clip
            // guess, and ADR-009 on the server records how wrong that guess is for a Rock Band
            // package whose `song` stem is an empty backing track.
            var stems = new List<string>();
            bool hasOwnPreview = false;
            if (n["assets"] is JObject assets)
            {
                if (assets["stems"] is JArray stemRows)
                {
                    foreach (var row in stemRows)
                    {
                        // `stem` is the catalogue's label ("guitar"), which is what maps to a
                        // SongStem; `name` is the file. Prefer the label and fall back to the
                        // file's base name so a package with an odd filename still mixes.
                        var label = (string?) row["stem"];
                        if (string.IsNullOrWhiteSpace(label))
                        {
                            var file = (string?) row["name"];
                            label = string.IsNullOrWhiteSpace(file)
                                ? null
                                : Path.GetFileNameWithoutExtension(file);
                        }
                        if (!string.IsNullOrWhiteSpace(label) && !stems.Contains(label))
                        {
                            stems.Add(label);
                        }
                    }
                }
                hasOwnPreview = assets["preview_audio"] is JObject pa
                    && !string.IsNullOrWhiteSpace((string?) pa["name"]);
            }

            return RemoteSongEntry.Create(
                (string?) n["chart_hash"] ?? "",
                (string?) n["package_hash"] ?? "",
                m, parts, LoaderSettings.Default,
                (string?) n["year"] ?? "",
                (int?) n["year_as_number"] ?? int.MaxValue,
                (DateTime?) n["date_added"] ?? new DateTime(1970, 1, 1),
                stems, hasOwnPreview);
        }

        private static void SetIfPresent(JObject n, string key, Action<string> set)
        {
            var v = (string?) n[key];
            if (!string.IsNullOrEmpty(v))
            {
                set(v);
            }
        }

        // SubTracks and Difficulties are a union on the same byte - both are [FieldOffset(0)] -
        // so assigning one assigns the other. The server already shapes that byte to mirror
        // AvailableParts, so it is copied rather than recomputed: recomputing it here would be a
        // second opinion about song content, and the client would start disagreeing with the
        // browse list the server published.
        private static void Part(JObject parts, string key, ref PartValues target)
        {
            if (parts[key] is not JObject v)
            {
                return;
            }
            target.SubTracks = (byte) ((int?) v["difficulties"] ?? 0);
            target.Intensity = (sbyte) ((int?) v["intensity"] ?? -1);
        }

        /// <summary>
        /// Pulls the whole catalogue, a page at a time.
        /// </summary>
        public static async UniTask<List<RemoteSongEntry>> Fetch(string serverUrl,
            CancellationToken token, int timeoutSeconds = 30)
        {
            string root = serverUrl.Trim().TrimEnd('/');
            var entries = new List<RemoteSongEntry>();
            int offset = 0;
            int total = -1;
            int malformed = 0;

            while (true)
            {
                using var request = UnityWebRequest.Get($"{root}/api/v1/songs?limit={PAGE}&offset={offset}");
                request.SetRequestHeader("User-Agent", "YARG");
                request.timeout = timeoutSeconds;

                await request.SendWebRequest().WithCancellation(token);

                if (request.result != UnityWebRequest.Result.Success)
                {
                    throw new Exception($"Song server did not answer /api/v1/songs: {request.error}");
                }

                var json = JObject.Parse(request.downloadHandler.text);
                if (total < 0)
                {
                    total = json.Value<int>("total");
                    if (total > SANITY_LIMIT)
                    {
                        throw new Exception($"Song server claims {total} songs; refusing");
                    }
                }

                var page = json.Value<JArray>("songs") ?? new JArray();
                if (page.Count == 0)
                {
                    // Past the end is an empty page rather than an error, which is also what a
                    // server lying about its total looks like. Either way there is no more.
                    break;
                }

                foreach (var row in page)
                {
                    if (row is not JObject obj)
                    {
                        malformed++;
                        continue;
                    }
                    try
                    {
                        entries.Add(FromJson(obj));
                    }
                    catch (Exception ex)
                    {
                        // One unusable row must not cost the other six hundred. Counted and
                        // logged, because a server producing these is broken and that is worth
                        // seeing rather than silently browsing a short library.
                        malformed++;
                        YargLogger.LogWarning($"Song server sent a song that could not be read: {ex.Message}");
                    }
                }

                offset += page.Count;
                if (entries.Count + malformed >= total)
                {
                    break;
                }
            }

            if (malformed > 0)
            {
                YargLogger.LogWarning($"Song server catalogue: {malformed} of {total} rows unusable");
            }
            YargLogger.LogFormatInfo("Song server catalogue: {0} entries", entries.Count);
            return entries;
        }

        /// <summary>
        /// Adds remote entries to a scan result, skipping any song the player already holds.
        /// </summary>
        /// <remarks>
        /// Local wins, always. A song present on this machine has real bytes and can be played;
        /// the remote entry for the same chart could not be, so publishing both would give the
        /// player two rows of which one is a dead end. Identity is the chart hash, so "the same
        /// song" is exactly "the same key in this dictionary".
        /// </remarks>
        public static int MergeInto(SongCache cache, List<RemoteSongEntry> remote)
        {
            int added = 0;
            foreach (var entry in remote)
            {
                if (cache.Entries.ContainsKey(entry.Hash))
                {
                    continue;
                }
                cache.Entries.Add(entry.Hash, new List<SongEntry> { entry });
                added++;
            }
            return added;
        }
    }
}
