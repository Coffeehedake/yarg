using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using UnityEngine;
using YARG.Core.Logging;
using YARG.Core.Song;
using YARG.Menu.MusicLibrary;
using YARG.Playlists;
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
    /// Second, the queue this writes to. There used to be TWO: the setlist being
    /// built in the menu, and a SNAPSHOT of it that gameplay ran off once "Start
    /// Setlist" was pressed. Adding to the wrong one looked identical to the guest -
    /// the request succeeded and the song never played.
    ///
    /// Upstream's #1758 removed that duality, and this was ported onto it when the
    /// fork was brought current on 2026-11-02. <c>MusicLibraryMenu.ShowPlaylist</c>
    /// IS <c>Setlist.Playlist</c> now, so there is one queue and writing to it is
    /// unambiguous. What survives from the old shape is the GUARD, which is not an
    /// artefact of having had two queues: during a show, the song playing and
    /// everything behind it stay untouchable, because <c>Setlist.Index</c> is a
    /// POSITION rather than a reference to a song, so editing behind it silently
    /// repoints the show at something else.
    ///
    /// The menu is still told when it is open, for the toast and the redraw - the
    /// room should see on the TV that somebody queued from their phone - and with no
    /// menu loaded the song is held in <see cref="_pending"/> and flushed in the
    /// moment the library menu exists again. That holding is now a choice rather
    /// than a necessity, since <c>Setlist.Playlist</c> is static and reachable with
    /// no menu at all; it stays because "pending" is part of the HTTP contract the
    /// phone app transcribes, and widening a currency merge into a behaviour change
    /// is not this change.
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

        /// <summary>
        /// Index, in <c>Setlist.Playlist.SongHashes</c>, of the song being played - the last
        /// position a remote request may not touch - or -1 when no show is running.
        ///
        /// It is deliberately NOT <c>Setlist.Index</c>, which counts positions in
        /// <c>Setlist.ResolveSongs()</c>. That skips every hash the library cannot resolve, so the
        /// two disagree by one for each unresolvable hash ahead of the playing song. Guarding with
        /// one and editing with the other is exactly how an edit lands on the wrong side of the
        /// playing position, and it would do so only on a library where a queued song had gone
        /// missing - which is to say, almost never, and never on the machine it was written on.
        /// Everything on the show path here is in hash space for that reason.
        /// </summary>
        private static int PlayingHashIndex()
        {
            if (!Setlist.IsPlaying)
            {
                return -1;
            }

            var songs = Setlist.ResolveSongs();
            if (Setlist.Index < 0 || Setlist.Index >= songs.Count)
            {
                // A show is running but the position names no song. Refuse everything rather than
                // report "no show", which would hand a phone the whole queue to rearrange.
                return Setlist.Playlist.SongHashes.Count;
            }

            return Setlist.Playlist.SongHashes.IndexOf(songs[Setlist.Index].Hash);
        }

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

                if (Setlist.IsPlaying)
                {
                    view.playing_show = true;
                    // Both of these are in resolved space, and must stay in the SAME space as
                    // each other: the phone draws view.songs and highlights view.index in it.
                    view.index = Setlist.Index;
                    view.target = "show";
                    foreach (var song in Setlist.ResolveSongs())
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

                if (Setlist.IsPlaying)
                {
                    // Append to the running show. The score screen advances with
                    // Setlist.TryAdvance, so a song added here plays after the ones
                    // already ahead of it. AddSong refuses a song that is already
                    // queued, where the old snapshot would have taken it twice.
                    Setlist.Playlist.AddSong(song);
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

                if (Setlist.IsPlaying)
                {
                    var at = Setlist.Playlist.SongHashes.IndexOf(song.Hash);

                    // Never touch the song being played or anything already
                    // played: the index would then point at a different song and
                    // the show would jump. Only what is still ahead is editable.
                    if (!CanEditWithinShow(at, PlayingHashIndex()))
                    {
                        return false;
                    }

                    Setlist.Playlist.RemoveSong(song);
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

        /// <summary>Why a move did or did not happen.</summary>
        /// <remarks>
        /// A bool could not say. Both "this song cannot go there" and "there is nowhere to
        /// move it yet" came back as the same refusal, and the second one reads as a fault
        /// with the song: with the game on a settings screen a perfectly good queued song
        /// answered "cannot be moved from where it is". Playtested 2026-10-30.
        /// </remarks>
        public enum MoveResult
        {
            Moved,

            /// <summary>An unknown song, one not in the queue, or a move the show rules forbid.</summary>
            Refused,

            /// <summary>
            /// The song IS queued, but only in the pending list: with no music-library menu open
            /// there is no setlist yet, and a pending song has no order to change.
            /// </summary>
            WaitingForLibrary,
        }

        /// <summary>Moves a song one place earlier (<paramref name="up"/>) or later.</summary>
        public static MoveResult Move(string hashText, bool up)
        {
            var song = Resolve(hashText);
            if (song == null)
            {
                return MoveResult.Refused;
            }

            return RunOnMain(() =>
            {
                FlushPendingOnMain();

                if (Setlist.IsPlaying)
                {
                    var hashes = Setlist.Playlist.SongHashes;
                    var at = hashes.IndexOf(song.Hash);
                    var to = up ? at - 1 : at + 1;

                    if (!CanMoveWithinShow(at, to, PlayingHashIndex(), hashes.Count))
                    {
                        return MoveResult.Refused;
                    }

                    if (up)
                    {
                        Setlist.Playlist.MoveSongUp(song);
                    }
                    else
                    {
                        Setlist.Playlist.MoveSongDown(song);
                    }

                    return MoveResult.Moved;
                }

                var menu = UnityEngine.Object.FindAnyObjectByType<MusicLibraryMenu>();
                if (menu != null)
                {
                    // Look BEFORE moving. Playlist.MoveSongUp/Down silently do nothing at
                    // either end, which this used to report as "moved" - and for a song that
                    // is not in the setlist at all, MoveSongDown indexes SongHashes[-1] and
                    // throws whenever the setlist is non-empty, which surfaced as an HTTP 500
                    // from a request any client can send. Measured 2026-10-30 against a
                    // running game: a never-queued song moved down answered 500, moved up
                    // answered 200 "moved: true", and nothing had moved either time.
                    var hashes = menu.ShowPlaylist.SongHashes;
                    var at = hashes.IndexOf(song.Hash);
                    if (at < 0 || (up && at == 0) || (!up && at == hashes.Count - 1))
                    {
                        return MoveResult.Refused;
                    }

                    menu.MoveSongInSetlistRemotely(song, up);
                    return MoveResult.Moved;
                }

                // No menu: only blame the closed menu if the song is really waiting for it.
                // A song that was never queued is just a refusal.
                lock (_pending)
                {
                    return _pending.Contains(song) ? MoveResult.WaitingForLibrary : MoveResult.Refused;
                }
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
                if (Setlist.IsPlaying)
                {
                    return InsertNextInShow(song);
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
                if (Setlist.IsPlaying)
                {
                    var hashes = Setlist.Playlist.SongHashes;
                    var floor = PlayingHashIndex();

                    var unplayed = new List<string>();
                    for (var i = floor + 1; i < hashes.Count; i++)
                    {
                        unplayed.Add(hashes[i].ToString());
                    }

                    var reordered = QueueInVoteOrder(hashes, floor, RemoteQueueVotes.SortByScore(unplayed));
                    if (reordered != null)
                    {
                        Setlist.Playlist.ReplaceSongs(reordered);
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

            if (outcome == NominationOutcome.PlayNext && Setlist.IsPlaying)
            {
                InsertNextInShow(song);
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

        /// <summary>
        /// Puts a song immediately after the one playing, in a running show. Main thread only.
        /// Returns false when the queue was deliberately left alone.
        ///
        /// Shared by the two paths a won "play next" vote can arrive on - settled by the clock and
        /// settled by the caller - because the index arithmetic is the sort that is right once and
        /// then quietly wrong in the copy.
        /// </summary>
        private static bool InsertNextInShow(SongEntry song)
        {
            var reordered = QueueWithSongNext(Setlist.Playlist.SongHashes, PlayingHashIndex(), song.Hash);
            if (reordered == null)
            {
                return false;
            }

            Setlist.Playlist.ReplaceSongs(reordered);
            return true;
        }

        // ------------------------------------------------------------------
        // The show guard, as pure functions
        //
        // Everything that decides WHETHER a remote request may touch the queue, and WHERE in it,
        // lives here taking plain numbers. Not for tidiness: the thing being protected is the
        // playing position, the protection is index arithmetic, and a compile cannot tell a
        // correct offset from one that is out by one. They are PUBLIC, which for helpers this
        // small looks like over-exposure and is not: Assets/Editor is a separate assembly, so
        // `internal` does not reach SetlistGuardProbe - measured, as 81 CS0117 errors. The probe
        // is the only way this gets measured at all, since a show cannot be started headless.
        // `floor` is always a position in Setlist.Playlist.SongHashes; see PlayingHashIndex for
        // why that space and not the resolved one.
        // ------------------------------------------------------------------

        /// <summary>
        /// Whether a remote request may touch the song at <paramref name="at"/>, given that
        /// <paramref name="floor"/> is playing. A song that is not in the queue gives
        /// <paramref name="at"/> = -1 and is refused by the same comparison.
        /// </summary>
        public static bool CanEditWithinShow(int at, int floor)
        {
            return at > floor;
        }

        /// <summary>
        /// Whether a remote request may move the song at <paramref name="at"/> to
        /// <paramref name="to"/>. Same rule as editing, and one more: nothing may be moved INTO or
        /// before the playing slot, which is a separate clause because the destination is not the
        /// thing being checked above.
        /// </summary>
        public static bool CanMoveWithinShow(int at, int to, int floor, int count)
        {
            return CanEditWithinShow(at, floor) && to > floor && to < count;
        }

        /// <summary>
        /// The queue a won "play next" produces: <paramref name="hash"/> immediately after
        /// <paramref name="floor"/>. Null means leave the queue exactly as it is.
        /// </summary>
        public static List<HashWrapper> QueueWithSongNext(IReadOnlyList<HashWrapper> hashes, int floor,
            HashWrapper hash)
        {
            var reordered = new List<HashWrapper>(hashes);
            var existing = reordered.IndexOf(hash);
            if (existing >= 0 && !CanEditWithinShow(existing, floor))
            {
                // Already played. Moving it forward would drag the playing position with it, and
                // the setlist cannot hold a song twice, so there is nothing to do here that is
                // both safe and visible.
                return null;
            }

            var at = Math.Min(floor + 1, reordered.Count);
            if (existing >= 0)
            {
                // No adjustment to `at` for the position this vacates, which looks like an
                // omission and is not. Getting here means CanEditWithinShow said yes, so
                // existing >= floor + 1, while at <= floor + 1: the song being moved is never
                // BEFORE the slot it is moving to, so the removal never shifts that slot.
                // There was an `if (existing < at) at--;` here until it was written down that
                // way - trying to make the probe catch its absence is what showed it could
                // never run. Arithmetic that cannot execute still has to be read by whoever
                // comes next, and it claims a case exists.
                reordered.RemoveAt(existing);
            }

            reordered.Insert(Math.Min(at, reordered.Count), hash);
            return reordered;
        }

        /// <summary>
        /// The queue a settled vote produces: everything up to and including <paramref name="floor"/>
        /// exactly where it was, and the rest in <paramref name="order"/>. Null means there was
        /// nothing to reorder.
        /// </summary>
        public static List<HashWrapper> QueueInVoteOrder(IReadOnlyList<HashWrapper> hashes, int floor,
            List<string> order)
        {
            var first = floor + 1;
            if (first >= hashes.Count - 1)
            {
                // One song left ahead, or none. Nothing a sort could change.
                return null;
            }

            var tail = new List<HashWrapper>();
            for (var i = first; i < hashes.Count; i++)
            {
                tail.Add(hashes[i]);
            }

            var byText = new Dictionary<string, HashWrapper>();
            foreach (var hash in tail)
            {
                byText[hash.ToString()] = hash;
            }

            var reordered = new List<HashWrapper>();
            for (var i = 0; i < first; i++)
            {
                reordered.Add(hashes[i]);
            }

            foreach (var text in order ?? new List<string>())
            {
                if (byText.TryGetValue(text, out var hash) && !reordered.Contains(hash))
                {
                    reordered.Add(hash);
                }
            }

            // Anything the sort did not name goes back on the end. The version before the 11-02
            // port indexed the sorted list positionally, so a short result left stale entries in
            // place and an unknown one threw: a reorder must never be able to lose a song.
            foreach (var hash in tail)
            {
                if (!reordered.Contains(hash))
                {
                    reordered.Add(hash);
                }
            }

            return reordered;
        }

        /// <summary>The add path, shared by a direct queue and a won vote. Main thread only.</summary>
        private static void AddOnMain(SongEntry song)
        {
            if (Setlist.IsPlaying)
            {
                Setlist.Playlist.AddSong(song);
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

                if (Setlist.IsPlaying)
                {
                    foreach (var song in _pending)
                    {
                        Setlist.Playlist.AddSong(song);
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
