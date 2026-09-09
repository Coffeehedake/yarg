using System;
using System.Collections.Generic;
using System.Threading;
using UnityEngine;
using YARG.Core.Logging;
using YARG.Core.Song;
using YARG.Menu.MusicLibrary;
using YARG.Song;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>One song, as a phone needs to see it.</summary>
    public sealed class RemoteSong
    {
        public string hash;
        public string name;
        public string artist;
        public string album;
        public string charter;
        public int    length_ms;
    }

    /// <summary>The queue, plus enough context for the page to explain itself.</summary>
    public sealed class RemoteQueueView
    {
        /// <summary>True while a setlist is actually being played.</summary>
        public bool playing_show;

        /// <summary>Index of the song being played, when a show is running.</summary>
        public int index;

        /// <summary>
        /// Which queue these songs came from: "show", "setlist", or "pending".
        /// The page shows this, because "queued" means something different in each.
        /// </summary>
        public string target;

        public List<RemoteSong> songs = new();
    }

    /// <summary>
    /// Everything that touches YARG's own state on behalf of an HTTP request.
    ///
    /// TWO THINGS MAKE THIS MORE THAN A THIN WRAPPER.
    ///
    /// First, Unity objects may only be touched on the main thread, and every
    /// caller here is an HTTP worker thread. <see cref="UnityMainThreadCallback"/>
    /// already exists for exactly this and is used by the audio callbacks, so
    /// this reuses it rather than inventing a second mechanism - but it is
    /// fire-and-forget, and an HTTP handler needs the answer. Hence the
    /// wait-with-timeout below.
    ///
    /// Second, and this is the part that would otherwise produce a silent
    /// nothing-happened: THERE ARE TWO QUEUES.
    ///
    ///   - In the menu, the setlist being built is <c>MusicLibraryMenu.ShowPlaylist</c>.
    ///   - Once "Start Setlist" is pressed, gameplay runs off a SNAPSHOT of it in
    ///     <c>GlobalVariables.State.ShowSongs</c>, indexed by <c>ShowIndex</c>.
    ///
    /// Adding to the wrong one looks identical to the guest - the request
    /// succeeds and the song never plays. So an add is routed by what is actually
    /// happening, and when neither queue is reachable (a single song is playing,
    /// no show, no library menu loaded) the song is held in <see cref="_pending"/>
    /// and flushed into the setlist the moment the library menu exists again.
    /// </summary>
    public static class RemoteQueueBridge
    {
        /// <summary>
        /// How long an HTTP thread will wait for the main thread to run its work.
        /// The main thread can be busy loading a song; it should never be busy for
        /// five seconds, and if it is, answering "unavailable" beats hanging a
        /// phone until it times out on its own.
        /// </summary>
        private const int MainThreadTimeoutMs = 5000;

        /// <summary>Songs queued when there was nowhere to put them yet.</summary>
        private static readonly List<SongEntry> _pending = new();

        public static int PendingCount
        {
            get { lock (_pending) { return _pending.Count; } }
        }

        // ------------------------------------------------------------------
        // Reads
        // ------------------------------------------------------------------

        public static List<RemoteSong> Search(string query, int limit)
        {
            return RunOnMain(() =>
            {
                var results = new List<RemoteSong>();
                var songs = SongContainer.Songs;

                // SortString carries a pre-normalised SearchStr, which is what the
                // game's own search uses - so matching here behaves the way the
                // in-game library behaves rather than approximating it.
                var needle = string.IsNullOrWhiteSpace(query)
                    ? null
                    : new SortString(query.Trim()).SearchStr;

                foreach (var song in songs)
                {
                    if (needle != null &&
                        !song.Name.SearchStr.Contains(needle) &&
                        !song.Artist.SearchStr.Contains(needle) &&
                        !song.Album.SearchStr.Contains(needle))
                    {
                        continue;
                    }

                    results.Add(ToRemote(song));
                    if (results.Count >= limit)
                    {
                        break;
                    }
                }

                return results;
            });
        }

        public static int LibraryCount => RunOnMain(() => SongContainer.Count);

        public static RemoteQueueView GetQueue()
        {
            return RunOnMain(() =>
            {
                FlushPendingOnMain();

                var view = new RemoteQueueView();

                if (GlobalVariables.State.PlayingAShow)
                {
                    view.playing_show = true;
                    view.index = GlobalVariables.State.ShowIndex;
                    view.target = "show";
                    foreach (var song in GlobalVariables.State.ShowSongs)
                    {
                        view.songs.Add(ToRemote(song));
                    }
                    return view;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    view.target = "setlist";
                    foreach (var song in menu.ShowPlaylist.ToList())
                    {
                        view.songs.Add(ToRemote(song));
                    }
                    return view;
                }

                view.target = "pending";
                lock (_pending)
                {
                    foreach (var song in _pending)
                    {
                        view.songs.Add(ToRemote(song));
                    }
                }

                return view;
            });
        }

        // ------------------------------------------------------------------
        // Writes
        // ------------------------------------------------------------------

        /// <summary>
        /// Adds a song by chart hash. Returns which queue it landed in, so the
        /// caller can say something true rather than a generic "queued".
        /// </summary>
        public static string Add(string hashText)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return null;
            }

            return RunOnMain(() =>
            {
                FlushPendingOnMain();

                if (GlobalVariables.State.PlayingAShow)
                {
                    // Append to the running show. The pause menu advances by
                    // ShowIndex against this list, so a song added here plays
                    // after the ones already ahead of it.
                    GlobalVariables.State.ShowSongs.Add(song);
                    return "show";
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    menu.AddSongToSetlistRemotely(song);
                    return "setlist";
                }

                lock (_pending)
                {
                    if (!_pending.Contains(song))
                    {
                        _pending.Add(song);
                    }
                }

                return "pending";
            });
        }

        public static bool Remove(string hashText)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return false;
            }

            return RunOnMain(() =>
            {
                FlushPendingOnMain();

                if (GlobalVariables.State.PlayingAShow)
                {
                    var songs = GlobalVariables.State.ShowSongs;
                    var at = songs.FindIndex(s => s.Hash.Equals(song.Hash));

                    // Never touch the song being played or anything already
                    // played: the index would then point at a different song and
                    // the show would jump. Only what is still ahead is editable.
                    if (at <= GlobalVariables.State.ShowIndex)
                    {
                        return false;
                    }

                    songs.RemoveAt(at);
                    return true;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    menu.RemoveSongFromSetlistRemotely(song);
                    return true;
                }

                lock (_pending)
                {
                    return _pending.Remove(song);
                }
            });
        }

        /// <summary>Moves a song one place earlier (<paramref name="up"/>) or later.</summary>
        public static bool Move(string hashText, bool up)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return false;
            }

            return RunOnMain(() =>
            {
                FlushPendingOnMain();

                if (GlobalVariables.State.PlayingAShow)
                {
                    var songs = GlobalVariables.State.ShowSongs;
                    var at = songs.FindIndex(s => s.Hash.Equals(song.Hash));
                    var to = up ? at - 1 : at + 1;

                    // Same rule as removal, and one more: nothing may be moved
                    // into or before the currently playing slot.
                    if (at <= GlobalVariables.State.ShowIndex ||
                        to <= GlobalVariables.State.ShowIndex ||
                        to >= songs.Count)
                    {
                        return false;
                    }

                    (songs[at], songs[to]) = (songs[to], songs[at]);
                    return true;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    menu.MoveSongInSetlistRemotely(song, up);
                    return true;
                }

                return false;
            });
        }

        // ------------------------------------------------------------------
        // Internals
        // ------------------------------------------------------------------

        /// <summary>
        /// Moves anything queued while there was nowhere to put it into the real
        /// setlist. Called at the start of every operation rather than from an
        /// Update loop, because the page polls and that is often enough - and it
        /// keeps this a plain static class with no scene object to wire up.
        ///
        /// MUST be called on the main thread.
        /// </summary>
        private static void FlushPendingOnMain()
        {
            lock (_pending)
            {
                if (_pending.Count == 0)
                {
                    return;
                }

                if (GlobalVariables.State.PlayingAShow)
                {
                    foreach (var song in _pending)
                    {
                        GlobalVariables.State.ShowSongs.Add(song);
                    }

                    YargLogger.LogFormatInfo("Remote queue: flushed {0} pending song(s) into the running show",
                        _pending.Count);
                    _pending.Clear();
                    return;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu == null)
                {
                    return;
                }

                foreach (var song in _pending)
                {
                    menu.AddSongToSetlistRemotely(song);
                }

                YargLogger.LogFormatInfo("Remote queue: flushed {0} pending song(s) into the setlist",
                    _pending.Count);
                _pending.Clear();
            }
        }

        private static SongEntry Resolve(string hashText)
        {
            if (string.IsNullOrWhiteSpace(hashText))
            {
                return null;
            }

            try
            {
                // FromString, not Create: Create takes the raw 20 bytes, while a
                // remote caller sends the hex text that ToString() produced.
                var hash = HashWrapper.FromString(hashText.Trim());
                if (SongContainer.SongsByHash.TryGetValue(hash, out var songs) && songs.Count > 0)
                {
                    return songs[0];
                }
            }
            catch (Exception)
            {
                // A malformed hash from a remote caller is an ordinary bad
                // request, not something to log noisily or crash on.
            }

            return null;
        }

        private static RemoteSong ToRemote(SongEntry song) => new()
        {
            hash      = song.Hash.ToString(),
            name      = song.Name,
            artist    = song.Artist,
            album     = song.Album,
            charter   = song.Charter,
            length_ms = (int) song.SongLengthMilliseconds,
        };

        /// <summary>
        /// Runs <paramref name="work"/> on Unity's main thread and waits for the
        /// result. Throws <see cref="TimeoutException"/> rather than hanging.
        /// </summary>
        private static T RunOnMain<T>(Func<T> work)
        {
            Exception failure = null;
            T result = default;

            using var done = new ManualResetEventSlim(false);

            UnityMainThreadCallback.QueueEvent(() =>
            {
                try
                {
                    result = work();
                }
                catch (Exception e)
                {
                    failure = e;
                }
                finally
                {
                    done.Set();
                }
            });

            if (!done.Wait(MainThreadTimeoutMs))
            {
                throw new TimeoutException("the game's main thread did not answer in time");
            }

            if (failure != null)
            {
                throw failure;
            }

            return result;
        }
    }
}
