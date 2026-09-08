using System;
using System.IO;
using YARG.Core.Song;
using YARG.Helpers;

namespace YARG.Song.RemoteLibrary
{
    /// <summary>
    /// Tells whether a song came from the song server mirror.
    /// </summary>
    /// <remarks>
    /// THE SIGNAL IS THE PATH, and that was measured rather than assumed. The obvious
    /// candidates both fail: <c>Source</c> belongs to whoever charted the song, and
    /// <c>Playlist</c> — which is what YARG's existing <c>folder:</c> search filter actually
    /// matches on — reads "Unknown Playlist" for every mirrored song, because a loose
    /// <c>.sng</c> takes its playlist from its own metadata and not from the folder it sits
    /// in. Measured on a real 23-song mirror: playlist matched the folder name for 0 of them,
    /// and the path matched for all of them.
    ///
    /// That also settles a design question in the other direction: <c>folder:serverlibrary</c>
    /// does NOT already do this, so the filter below is not a duplicate of something the game
    /// already had.
    /// </remarks>
    public static class MirroredSongs
    {
        /// <summary>
        /// The search prefix. <c>server:yes</c> keeps mirrored songs, <c>server:no</c> keeps
        /// everything else.
        /// </summary>
        public const string SearchPrefix = "server:";

        public enum Want
        {
            Either,
            Mirrored,
            NotMirrored,
        }

        public static bool IsMirrored(SongEntry entry)
        {
            return IsUnder(entry?.ActualLocation, PathHelper.ServerLibraryPath);
        }

        /// <summary>
        /// Path containment that will not answer yes for a sibling folder whose name merely
        /// starts the same way — "…/ServerLibraryOld" is not inside "…/ServerLibrary".
        /// </summary>
        public static bool IsUnder(string path, string root)
        {
            if (string.IsNullOrEmpty(path) || string.IsNullOrEmpty(root))
            {
                return false;
            }

            string normalisedPath = Normalise(path);
            string normalisedRoot = Normalise(root);

            if (normalisedPath.Length <= normalisedRoot.Length)
            {
                return string.Equals(normalisedPath, normalisedRoot,
                    StringComparison.OrdinalIgnoreCase);
            }

            return normalisedPath.StartsWith(normalisedRoot, StringComparison.OrdinalIgnoreCase) &&
                normalisedPath[normalisedRoot.Length] == '/';
        }

        private static string Normalise(string path)
        {
            return path.Replace('\\', '/').TrimEnd('/');
        }

        /// <summary>
        /// Pulls any <c>server:</c> term out of a search query, returning the query without it.
        /// </summary>
        /// <remarks>
        /// Handled here rather than as a new <c>SortAttribute</c> on purpose. The search
        /// pipeline keys its filters on that enum, but the enum is also what the library
        /// sorts and groups by, and several of its values already have no comparer — adding
        /// one for something that can never be a sort order would put a value into that enum
        /// that half the code must remember to ignore. Post-filtering costs one pass over an
        /// already-narrowed list.
        /// </remarks>
        public static Want ExtractWant(string query, out string remaining)
        {
            remaining = query;
            if (string.IsNullOrEmpty(query))
            {
                return Want.Either;
            }

            var want = Want.Either;
            var kept = new System.Text.StringBuilder();

            foreach (string term in query.Split(';'))
            {
                string trimmed = term.Trim();
                if (!trimmed.StartsWith(SearchPrefix, StringComparison.OrdinalIgnoreCase))
                {
                    if (kept.Length > 0)
                    {
                        kept.Append(';');
                    }
                    kept.Append(term);
                    continue;
                }

                string value = trimmed[SearchPrefix.Length..].Trim().ToLowerInvariant();
                want = value switch
                {
                    "no" or "false" or "local" => Want.NotMirrored,
                    // Anything else, "yes" included, means "from the server". A bare
                    // "server:" is a half-typed query, and treating it as "mirrored" shows
                    // the player something rather than silently everything.
                    _ => Want.Mirrored,
                };
            }

            remaining = kept.ToString();
            return want;
        }

        public static bool Matches(SongEntry entry, Want want)
        {
            return want switch
            {
                Want.Mirrored    => IsMirrored(entry),
                Want.NotMirrored => !IsMirrored(entry),
                _                => true,
            };
        }
    }
}
