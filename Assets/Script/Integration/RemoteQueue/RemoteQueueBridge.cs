using System;
using System.Collections.Generic;
using System.Linq;
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

        /// <summary>Net votes, when this song is in the queue.</summary>
        public int    score;
    }

    /// <summary>A song somebody suggested, and how the room feels about it.</summary>
    public sealed class RemoteNomination
    {
        public string hash;
        public string name;
        public string artist;

        /// <summary>"suggested" while the room decides whether to play it at all;
        /// "deciding" once it has won that and is choosing where it goes.</summary>
        public string stage;

        public int score;
        public int ups;
        public int downs;
        public int for_next;
        public int for_setlist;
    }

    /// <summary>Everything a phone needs in one poll.</summary>
    public sealed class RemoteBoard
    {
        public RemoteQueueView         queue;
        public List<RemoteNomination>  suggestions = new();

        /// <summary>How many votes promote a suggestion, or settle where it goes.</summary>
        public int threshold;

        /// <summary>Whether voting is on at all.</summary>
        public bool voting;

        /// <summary>
        /// True during the gap between two songs - the only moment anybody's
        /// hands are free to vote. The page shouts about it, because a vote cast
        /// at any other time is a vote cast into an empty room.
        /// </summary>
        public bool intermission;

        /// <summary>Seconds left in that window, or 0.</summary>
        public int intermission_seconds;
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
        // Voting (increment 3)
        // ------------------------------------------------------------------

        /// <summary>
        /// Suggests a song from the library. It does NOT enter the queue - it
        /// goes on the suggestion board for the room to vote on, which is the
        /// point: anybody can put a song forward, and the room decides.
        /// </summary>
        public static RemoteNomination Suggest(string hashText, string voter)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return null;
            }

            var hash = song.Hash.ToString();
            var nomination = RemoteQueueVotes.Suggest(hash, voter);

            // Null means the board is full rather than the song being unknown,
            // and the caller has to be able to tell those apart.
            return nomination == null ? null : Describe(nomination, song);
        }

        /// <summary>A vote on a suggestion. Promotion happens at the threshold.</summary>
        public static bool VoteSuggestion(string hashText, string voter, int delta, int threshold)
        {
            var song = Resolve(hashText);
            return song != null &&
                RemoteQueueVotes.VoteSuggestion(song.Hash.ToString(), voter, delta, threshold);
        }

        /// <summary>
        /// The second vote, and the one that actually changes the queue: play it
        /// next, or add it to the end. Returns what happened, or None while the
        /// room is still deciding.
        /// </summary>
        public static NominationOutcome VoteOutcome(string hashText, string voter, bool playNext, int threshold)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return NominationOutcome.None;
            }

            var outcome = RemoteQueueVotes.VoteOutcome(song.Hash.ToString(), voter, playNext, threshold);
            if (outcome == NominationOutcome.None)
            {
                return outcome;
            }

            RunOnMain(() =>
            {
                FlushPendingOnMain();

                if (outcome == NominationOutcome.AddToSetlist)
                {
                    AddOnMain(song);
                    return true;
                }

                // PLAY NEXT, NOT PLAY NOW. Cutting off whoever is mid-song to
                // start a different one is not a party feature, it is a way to
                // start an argument. "Next" is the strongest thing a vote should
                // be able to do to a song already in progress.
                if (GlobalVariables.State.PlayingAShow)
                {
                    var songs = GlobalVariables.State.ShowSongs;
                    var at = Math.Min(GlobalVariables.State.ShowIndex + 1, songs.Count);
                    songs.Insert(at, song);
                    return true;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    menu.InsertSongAtTopOfSetlistRemotely(song);
                    return true;
                }

                lock (_pending)
                {
                    _pending.Insert(0, song);
                }

                return true;
            });

            return outcome;
        }

        /// <summary>
        /// A vote on something already queued, followed immediately by a re-sort
        /// of the part of the queue that has not been played yet.
        /// </summary>
        public static bool VoteQueued(string hashText, string voter, int delta)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return false;
            }

            RemoteQueueVotes.VoteQueued(song.Hash.ToString(), voter, delta);
            ApplyVoteOrder();
            return true;
        }

        /// <summary>
        /// Reorders the unplayed queue by score.
        ///
        /// Only ever the unplayed part. During a show everything up to and
        /// including <c>ShowIndex</c> is left exactly where it is, because
        /// ShowIndex is a position rather than a reference - shuffling songs
        /// behind it would silently repoint the show at a different song.
        /// </summary>
        public static void ApplyVoteOrder()
        {
            RunOnMain(() =>
            {
                if (GlobalVariables.State.PlayingAShow)
                {
                    var songs = GlobalVariables.State.ShowSongs;
                    var first = GlobalVariables.State.ShowIndex + 1;
                    if (first >= songs.Count - 1)
                    {
                        return true;
                    }

                    var tail = songs.GetRange(first, songs.Count - first);
                    var order = RemoteQueueVotes.SortByScore(tail.Select(s => s.Hash.ToString()));

                    var byHash = new Dictionary<string, SongEntry>();
                    foreach (var s in tail)
                    {
                        byHash[s.Hash.ToString()] = s;
                    }

                    for (var i = 0; i < order.Count; i++)
                    {
                        songs[first + i] = byHash[order[i]];
                    }

                    return true;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    menu.ReorderSetlistRemotely(RemoteQueueVotes.SortByScore(
                        menu.ShowPlaylist.ToList().Select(s => s.Hash.ToString())));
                }

                return true;
            });
        }

        /// <summary>
        /// Closes a voting window and applies whatever the room decided.
        /// Returns the outcome so the caller can say something true about it.
        ///
        /// Safe to call from the main thread: unlike the other write paths this
        /// does its own work inline rather than through <see cref="RunOnMain"/>,
        /// because the score screen calls it from Update and waiting on the main
        /// thread from the main thread is a deadlock.
        /// </summary>
        public static NominationOutcome ResolveIntermissionOnMain()
        {
            var (hash, outcome) = RemoteQueueVotes.ResolveExpiry();
            RemoteQueueIntermission.Close();

            if (outcome == NominationOutcome.None || hash == null)
            {
                return NominationOutcome.None;
            }

            var song = Resolve(hash);
            if (song == null)
            {
                return NominationOutcome.None;
            }

            FlushPendingOnMain();

            if (outcome == NominationOutcome.PlayNext && GlobalVariables.State.PlayingAShow)
            {
                var songs = GlobalVariables.State.ShowSongs;
                var at = Math.Min(GlobalVariables.State.ShowIndex + 1, songs.Count);
                songs.Insert(at, song);
                return outcome;
            }

            AddOnMain(song);
            return outcome;
        }

        /// <summary>The queue and the suggestion board in one call, so a phone polls once.</summary>
        public static RemoteBoard GetBoard(int threshold, bool voting)
        {
            var board = new RemoteBoard
            {
                queue = GetQueue(),
                threshold = threshold,
                voting = voting,
                intermission = RemoteQueueIntermission.IsOpen,
                intermission_seconds = RemoteQueueIntermission.SecondsLeft,
            };

            foreach (var nomination in RemoteQueueVotes.Suggestions())
            {
                var song = Resolve(nomination.Hash);
                if (song == null)
                {
                    // The library changed under us - a suggestion for a song that
                    // no longer exists should not sit on the board forever.
                    RemoteQueueVotes.DropSuggestion(nomination.Hash);
                    continue;
                }

                board.suggestions.Add(Describe(nomination, song));
            }

            return board;
        }

        private static RemoteNomination Describe(RemoteQueueVotes.Nomination nomination, SongEntry song) => new()
        {
            hash        = nomination.Hash,
            name        = song.Name,
            artist      = song.Artist,
            stage       = nomination.Stage == NominationStage.Deciding ? "deciding" : "suggested",
            score       = nomination.Score,
            ups         = nomination.Ups,
            downs       = nomination.Downs,
            for_next    = nomination.ForPlayNext.Count,
            for_setlist = nomination.ForSetlist.Count,
        };

        /// <summary>The add path, shared by a direct queue and a won vote. Main thread only.</summary>
        private static void AddOnMain(SongEntry song)
        {
            if (GlobalVariables.State.PlayingAShow)
            {
                GlobalVariables.State.ShowSongs.Add(song);
                return;
            }

            var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
            if (menu != null)
            {
                menu.AddSongToSetlistRemotely(song);
                return;
            }

            lock (_pending)
            {
                if (!_pending.Contains(song))
                {
                    _pending.Add(song);
                }
            }
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
            score     = RemoteQueueVotes.QueueScore(song.Hash.ToString()),
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
