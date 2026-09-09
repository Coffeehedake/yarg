using System;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>
    /// The gap between two songs in a setlist, which is the only moment a vote
    /// can actually happen.
    ///
    /// WHY THIS EXISTS AT ALL. While a song is playing, everybody's hands are on
    /// an instrument - nobody is holding a phone. So voting is not a continuous
    /// background activity the way the first version of this assumed; it happens
    /// in the gap, or it does not happen. That observation is Jay's, and it is
    /// the reason a countdown belongs here after all: a vote with a dedicated
    /// window wants a clock, where a vote running under a song did not.
    ///
    /// WHAT THIS DOES NOT NEED TO DO, measured rather than assumed: it does not
    /// need to stop the game advancing. YARG's score screen already waits for a
    /// human to press Continue - there is no auto-advance and no timer in
    /// ScoreScreenMenu. Nothing progresses on its own, so there is nothing to
    /// block.
    ///
    /// What it DOES prevent is the habitual instant Continue: somebody presses
    /// Green out of muscle memory before anybody has had a chance to vote, and
    /// the suggestion is silently discarded. So while a vote is open the button
    /// says so, the first press closes the vote and resolves it rather than
    /// advancing, and the second press advances. The window closes itself if
    /// nobody presses anything at all.
    /// </summary>
    public static class RemoteQueueIntermission
    {
        /// <summary>
        /// Long enough to read a couple of suggestions and tap, short enough that
        /// a room where nobody votes is not standing around waiting.
        /// </summary>
        public const int DefaultSeconds = 30;

        private static readonly object _gate = new();
        private static DateTime _closesAtUtc;
        private static bool     _open;

        /// <summary>Whether a voting window is currently running.</summary>
        public static bool IsOpen
        {
            get
            {
                lock (_gate)
                {
                    return _open && DateTime.UtcNow < _closesAtUtc;
                }
            }
        }

        /// <summary>Whether the window was opened and has since run out.</summary>
        public static bool HasExpired
        {
            get
            {
                lock (_gate)
                {
                    return _open && DateTime.UtcNow >= _closesAtUtc;
                }
            }
        }

        public static int SecondsLeft
        {
            get
            {
                lock (_gate)
                {
                    if (!_open)
                    {
                        return 0;
                    }

                    var left = (int) Math.Ceiling((_closesAtUtc - DateTime.UtcNow).TotalSeconds);
                    return left < 0 ? 0 : left;
                }
            }
        }

        public static void Open(int seconds)
        {
            lock (_gate)
            {
                _open = true;
                _closesAtUtc = DateTime.UtcNow.AddSeconds(seconds <= 0 ? DefaultSeconds : seconds);
            }
        }

        public static void Close()
        {
            lock (_gate)
            {
                _open = false;
            }
        }

        /// <summary>
        /// True when a window is running AND there is something to wait for.
        /// An open window with nothing suggested holds nothing up - the room has
        /// not asked for anything, so the button behaves normally.
        /// </summary>
        /// <remarks>
        /// Called from the score screen's Update, so both halves are cheap:
        /// a lock and an int. Asking <see cref="RemoteQueueVotes.Suggestions"/>
        /// would build and sort a list every frame for the length of the window.
        /// </remarks>
        public static bool ShouldHold()
        {
            return IsOpen && RemoteQueueVotes.SuggestionCount > 0;
        }
    }
}
