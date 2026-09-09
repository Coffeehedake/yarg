using System.Collections.Generic;
using System.Linq;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>What a nomination is currently waiting for.</summary>
    public enum NominationStage
    {
        /// <summary>Waiting to see whether the room wants it at all.</summary>
        Suggested = 0,

        /// <summary>The room said yes; now it is deciding where it goes.</summary>
        Deciding = 1,
    }

    /// <summary>How a nomination that won its second vote should land.</summary>
    public enum NominationOutcome
    {
        None = 0,

        /// <summary>Straight after the song currently playing.</summary>
        PlayNext = 1,

        /// <summary>On the end of the setlist, like any other queued song.</summary>
        AddToSetlist = 2,
    }

    /// <summary>
    /// All the voting state, and none of Unity.
    ///
    /// Kept deliberately separate from <see cref="RemoteQueueBridge"/> so the
    /// rules - who may vote, what promotes, what wins - are plain data and can be
    /// tested without a game running. That matters here: batchmode has no menu
    /// scene and no song library, so the queue plumbing cannot be exercised, but
    /// every rule in this file can be.
    ///
    /// NOTHING PERSISTS. Votes are for the party happening right now; a restart
    /// starts a fresh room. That also means this touches none of YARG's own data
    /// model - no Playlist changes, no save format - which keeps the upstream
    /// diff small.
    ///
    /// ON IDENTITY, honestly: a voter is a random id the page makes and keeps in
    /// the browser. It stops the ordinary double-tap and one phone voting twenty
    /// times. It does NOT stop somebody who clears their storage or opens a
    /// private tab. For a living room that is the right amount of ceremony; if
    /// this ever needed to be robust, it would need real accounts, and a party
    /// jukebox should not need real accounts.
    /// </summary>
    public static class RemoteQueueVotes
    {
        public sealed class Nomination
        {
            public string          Hash;
            public NominationStage Stage;

            /// <summary>voter id -> +1 or -1</summary>
            public readonly Dictionary<string, int> Votes = new();

            /// <summary>Voters who want it played next.</summary>
            public readonly HashSet<string> ForPlayNext = new();

            /// <summary>Voters who want it on the end of the setlist.</summary>
            public readonly HashSet<string> ForSetlist = new();

            public int Score => Votes.Values.Sum();
            public int Ups => Votes.Values.Count(v => v > 0);
            public int Downs => Votes.Values.Count(v => v < 0);
        }

        private static readonly object _gate = new();

        /// <summary>Songs suggested from the library, not yet in any queue.</summary>
        private static readonly Dictionary<string, Nomination> _nominations = new();

        /// <summary>Votes on songs already in the queue: hash -> voter -> +1/-1.</summary>
        private static readonly Dictionary<string, Dictionary<string, int>> _queueVotes = new();

        // ------------------------------------------------------------------
        // Suggestions
        // ------------------------------------------------------------------

        /// <summary>
        /// Suggests a song. The suggester's own vote counts as the first upvote -
        /// nobody suggests a song they would not vote for, and making them tap
        /// twice just produces a list of zero-score suggestions.
        /// </summary>
        public static Nomination Suggest(string hash, string voter)
        {
            lock (_gate)
            {
                if (!_nominations.TryGetValue(hash, out var nomination))
                {
                    nomination = new Nomination { Hash = hash, Stage = NominationStage.Suggested };
                    _nominations[hash] = nomination;
                }

                nomination.Votes[voter] = 1;
                return nomination;
            }
        }

        /// <summary>
        /// One voter, one vote, changeable. Returns true when this vote pushed the
        /// suggestion over the line into <see cref="NominationStage.Deciding"/>.
        /// </summary>
        public static bool VoteSuggestion(string hash, string voter, int delta, int threshold)
        {
            lock (_gate)
            {
                if (!_nominations.TryGetValue(hash, out var nomination) ||
                    nomination.Stage != NominationStage.Suggested)
                {
                    return false;
                }

                // Re-voting replaces rather than accumulates.
                nomination.Votes[voter] = delta >= 0 ? 1 : -1;

                if (nomination.Score < threshold)
                {
                    return false;
                }

                nomination.Stage = NominationStage.Deciding;
                return true;
            }
        }

        /// <summary>
        /// The second vote: play it next, or put it on the end. First side to
        /// reach the threshold wins.
        ///
        /// First-to-threshold rather than a countdown on purpose. A timer would
        /// need a clock running against game state, and "we are still waiting for
        /// the vote to close" is a worse party than "three people tapped, it is
        /// happening".
        /// </summary>
        public static NominationOutcome VoteOutcome(string hash, string voter, bool playNext, int threshold)
        {
            lock (_gate)
            {
                if (!_nominations.TryGetValue(hash, out var nomination) ||
                    nomination.Stage != NominationStage.Deciding)
                {
                    return NominationOutcome.None;
                }

                // Switching sides moves the vote rather than counting twice.
                if (playNext)
                {
                    nomination.ForSetlist.Remove(voter);
                    nomination.ForPlayNext.Add(voter);
                }
                else
                {
                    nomination.ForPlayNext.Remove(voter);
                    nomination.ForSetlist.Add(voter);
                }

                if (nomination.ForPlayNext.Count >= threshold)
                {
                    _nominations.Remove(hash);
                    return NominationOutcome.PlayNext;
                }

                if (nomination.ForSetlist.Count >= threshold)
                {
                    _nominations.Remove(hash);
                    return NominationOutcome.AddToSetlist;
                }

                return NominationOutcome.None;
            }
        }

        /// <summary>
        /// What happens when a voting window runs out.
        ///
        /// The LEADING suggestion wins, if the room actually wanted it - a net
        /// positive score. If it had already reached the second vote, the side
        /// with more votes decides where it goes, and a tie goes to the setlist
        /// because that is the less disruptive of the two.
        ///
        /// Suggestions nobody wanted (net zero or negative) are dropped, so a
        /// song the room ignored twice does not sit on the board all night.
        /// Everything else is KEPT for the next gap: people voted for those, and
        /// throwing their votes away because one song won would teach them not
        /// to bother.
        /// </summary>
        public static (string hash, NominationOutcome outcome) ResolveExpiry()
        {
            lock (_gate)
            {
                Nomination winner = null;
                foreach (var nomination in _nominations.Values)
                {
                    if (nomination.Score <= 0)
                    {
                        continue;
                    }

                    // Anything already at the second vote outranks a suggestion
                    // still waiting for its first - the room has spoken once.
                    if (winner == null ||
                        (nomination.Stage, nomination.Score).CompareTo((winner.Stage, winner.Score)) > 0)
                    {
                        winner = nomination;
                    }
                }

                // Drop the ones the room actively did not want.
                var unwanted = _nominations.Values.Where(n => n.Score <= 0).Select(n => n.Hash).ToList();
                foreach (var hash in unwanted)
                {
                    _nominations.Remove(hash);
                }

                if (winner == null)
                {
                    return (null, NominationOutcome.None);
                }

                var outcome = winner.Stage == NominationStage.Deciding && winner.ForPlayNext.Count > winner.ForSetlist.Count
                    ? NominationOutcome.PlayNext
                    : NominationOutcome.AddToSetlist;

                _nominations.Remove(winner.Hash);
                return (winner.Hash, outcome);
            }
        }

        public static void DropSuggestion(string hash)
        {
            lock (_gate)
            {
                _nominations.Remove(hash);
            }
        }

        /// <summary>
        /// How many suggestions are on the board.
        ///
        /// Exists so the score screen's Update can ask the cheap question every
        /// frame. <see cref="Suggestions"/> builds and sorts a list, which is
        /// fine for an HTTP request and wasteful sixty times a second.
        /// </summary>
        public static int SuggestionCount
        {
            get
            {
                lock (_gate)
                {
                    return _nominations.Count;
                }
            }
        }

        public static List<Nomination> Suggestions()
        {
            lock (_gate)
            {
                // Highest first, and ties keep the order they were suggested in.
                return _nominations.Values
                    .OrderByDescending(n => n.Stage == NominationStage.Deciding)
                    .ThenByDescending(n => n.Score)
                    .ToList();
            }
        }

        // ------------------------------------------------------------------
        // Votes on songs already queued
        // ------------------------------------------------------------------

        public static void VoteQueued(string hash, string voter, int delta)
        {
            lock (_gate)
            {
                if (!_queueVotes.TryGetValue(hash, out var votes))
                {
                    votes = new Dictionary<string, int>();
                    _queueVotes[hash] = votes;
                }

                votes[voter] = delta >= 0 ? 1 : -1;
            }
        }

        public static int QueueScore(string hash)
        {
            lock (_gate)
            {
                return _queueVotes.TryGetValue(hash, out var votes) ? votes.Values.Sum() : 0;
            }
        }

        /// <summary>
        /// Orders a run of queued songs by score, highest first.
        ///
        /// STABLE, and that is the whole reason a manual reorder still works:
        /// with no votes cast every score is zero, so this returns the list
        /// exactly as it was given. A song only moves once somebody actually
        /// votes on it.
        /// </summary>
        public static List<string> SortByScore(IEnumerable<string> hashes)
        {
            lock (_gate)
            {
                return hashes
                    .Select((hash, position) => (hash, position))
                    .OrderByDescending(x => _queueVotes.TryGetValue(x.hash, out var v) ? v.Values.Sum() : 0)
                    .ThenBy(x => x.position)
                    .Select(x => x.hash)
                    .ToList();
            }
        }

        /// <summary>Forgets everything. Used when the server stops.</summary>
        public static void Reset()
        {
            lock (_gate)
            {
                _nominations.Clear();
                _queueVotes.Clear();
            }
        }
    }
}
