using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using YARG.Core.Song;
using YARG.Integration.RemoteQueue;

namespace YARG.Editor
{
    /// <summary>
    /// Checks the rule that protects a running show from the phones: during a setlist, the song
    /// being played and everything behind it are not editable remotely.
    /// </summary>
    /// <remarks>
    /// Written on 2026-11-02, when bringing the fork current on upstream's dev replaced the state
    /// the remote queue was built on. Upstream's #1758 moved the live setlist behind a single
    /// <c>Setlist</c> owner and deleted <c>PersistentState.ShowSongs</c>, <c>ShowIndex</c> and
    /// <c>PlayingAShow</c>, so every one of those guards had to be rewritten - in a different index
    /// space, against a list that must now be mutated through the Playlist API. 87 compile errors
    /// said the rewrite was needed; nothing said it was right.
    ///
    /// It cannot drive the real entry points. <c>Remove</c>, <c>Move</c> and the vote paths run
    /// through <c>RunOnMain</c> and resolve hashes against a scanned <c>SongContainer</c>, and a
    /// show cannot be started headless at all - <c>Setlist.TryStart</c> needs songs that resolve,
    /// and batchmode has no audio backend, so most of the test corpus will not scan. Asking for a
    /// real show here would mean this went unmeasured.
    ///
    /// So the arithmetic is the unit, and the bridge exposes it as pure functions for exactly that
    /// reason. The hashes below are made up, which is the point: the guard is about POSITIONS, and
    /// a real library would add a scan to the list of things that could make this fail without
    /// saying anything about the guard.
    ///
    /// It was proved able to go red before its green was believed, once per function, by breaking
    /// each one in turn and watching which checks noticed:
    ///
    ///   - <c>CanEditWithinShow</c> as <c>at >= floor</c> (off by one at the playing song)
    ///   - <c>QueueWithSongNext</c> without the <c>at--</c> that accounts for the vacated position
    ///   - <c>QueueInVoteOrder</c> without the loop that puts back what the sort did not name
    ///
    /// Each break was measured, not predicted; what each one caught is recorded in the ROADMAP
    /// entry for 2026-11-02. Only the first of those is the kind of mistake a reviewer would spot,
    /// which is roughly the argument for the other two being here.
    /// </remarks>
    public static class SetlistGuardProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        private static void Check(string what, bool ok)
        {
            if (ok) { Pass(what); } else { Fail(what); }
        }

        /// <summary>Distinct, stable hashes. Content is irrelevant; only their order is tested.</summary>
        private static List<HashWrapper> Queue(int count)
        {
            var hashes = new List<HashWrapper>();
            for (var i = 0; i < count; i++)
            {
                hashes.Add(HashWrapper.Hash(new[] { (byte) (i + 1) }));
            }

            return hashes;
        }

        private static string Shape(IEnumerable<HashWrapper> hashes, List<HashWrapper> named)
        {
            return string.Join(",", hashes.Select(h => named.IndexOf(h).ToString()));
        }

        public static void Run()
        {
            _failures = 0;

            CheckEditGuard();
            CheckMoveGuard();
            CheckPlayNext();
            CheckVoteOrder();

            Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
            EditorApplication.Exit(_failures == 0 ? 0 : 1);
        }

        /// <summary>
        /// The removal rule. Position 2 is playing in a five-song show.
        /// </summary>
        private static void CheckEditGuard()
        {
            const int floor = 2;

            Check("the song being played cannot be removed",
                !RemoteQueueBridge.CanEditWithinShow(floor, floor));
            Check("a song already played cannot be removed",
                !RemoteQueueBridge.CanEditWithinShow(0, floor) &&
                !RemoteQueueBridge.CanEditWithinShow(1, floor));
            Check("a song still ahead can be removed",
                RemoteQueueBridge.CanEditWithinShow(3, floor) &&
                RemoteQueueBridge.CanEditWithinShow(4, floor));

            // IndexOf returns -1 for a song nobody queued, and the same comparison has to refuse
            // it. Before the port this was a separate accident of `at <= ShowIndex` being true for
            // -1; now it is a property worth stating, because CanEditWithinShow could plausibly be
            // written to treat "not queued" as "not protected".
            Check("a song that is not in the queue is refused, not treated as unprotected",
                !RemoteQueueBridge.CanEditWithinShow(-1, floor));

            // With no show running nothing is protected, which is what makes the same predicate
            // usable off the show path.
            Check("outside a show every position is editable",
                RemoteQueueBridge.CanEditWithinShow(0, -1));
        }

        /// <summary>
        /// The move rule: the destination is checked as well as the source, so a song cannot be
        /// moved INTO or before the playing slot.
        /// </summary>
        private static void CheckMoveGuard()
        {
            const int floor = 2;
            const int count = 5;

            Check("moving the song right after the playing one UP into it is refused",
                !RemoteQueueBridge.CanMoveWithinShow(3, 2, floor, count));
            Check("moving a played song is refused",
                !RemoteQueueBridge.CanMoveWithinShow(1, 2, floor, count) &&
                !RemoteQueueBridge.CanMoveWithinShow(0, 1, floor, count));
            Check("moving the last song DOWN off the end is refused",
                !RemoteQueueBridge.CanMoveWithinShow(4, 5, floor, count));
            Check("swapping two unplayed songs is allowed, both ways",
                RemoteQueueBridge.CanMoveWithinShow(4, 3, floor, count) &&
                RemoteQueueBridge.CanMoveWithinShow(3, 4, floor, count));
            Check("a song that is not in the queue cannot be moved",
                !RemoteQueueBridge.CanMoveWithinShow(-1, 0, floor, count));
        }

        /// <summary>
        /// A won "play next" vote lands immediately after the playing song, and never disturbs
        /// what is behind it.
        /// </summary>
        private static void CheckPlayNext()
        {
            var named = Queue(5);
            const int floor = 1;

            // A song from the library, not already queued.
            var fresh = HashWrapper.Hash(new byte[] { 99 });
            var result = RemoteQueueBridge.QueueWithSongNext(named, floor, fresh);
            Check("a new song goes immediately after the playing one",
                result != null && result[floor + 1].Equals(fresh));
            Check("and nothing up to the playing song moves",
                result != null && result[0].Equals(named[0]) && result[1].Equals(named[1]));
            Check("and no song is lost",
                result != null && result.Count == named.Count + 1 &&
                named.All(h => result.Contains(h)));

            // A song ALREADY queued further back. It has to move rather than appear twice, and the
            // position it vacates shifts everything after it - the off-by-one this exists to catch.
            var already = RemoteQueueBridge.QueueWithSongNext(named, floor, named[4]);
            Check("a song already queued later moves to just after the playing one",
                already != null && already[floor + 1].Equals(named[4]));
            Check("and is not left in its old place as well",
                already != null && already.Count == named.Count);
            Check("and the songs it jumped keep their order",
                already != null &&
                already[3].Equals(named[2]) && already[4].Equals(named[3]));

            // A song that has already been played. Moving it would drag the playing position with
            // it, and the setlist cannot hold a song twice, so the only safe answer is to do
            // nothing - and to SAY nothing happened rather than report a move.
            Check("a vote for an already-played song leaves the queue untouched",
                RemoteQueueBridge.QueueWithSongNext(named, floor, named[0]) == null);

            Debug.Log($"PROBE INFO: play-next of a later song gave [{Shape(already, named)}] " +
                $"from [{Shape(named, named)}] with {floor} playing");
        }

        /// <summary>
        /// A settled vote reorders only the unplayed part, and loses nothing whatever the sort says.
        /// </summary>
        private static void CheckVoteOrder()
        {
            var named = Queue(5);
            const int floor = 1;

            // Reverse the unplayed tail: 2,3,4 -> 4,3,2.
            var reversed = new List<string>
            {
                named[4].ToString(), named[3].ToString(), named[2].ToString(),
            };

            var result = RemoteQueueBridge.QueueInVoteOrder(named, floor, reversed);
            Check("the played songs and the playing one stay exactly where they were",
                result != null && result[0].Equals(named[0]) && result[1].Equals(named[1]));
            Check("the unplayed songs take the order the vote asked for",
                result != null &&
                result[2].Equals(named[4]) && result[3].Equals(named[3]) && result[4].Equals(named[2]));
            Check("no song is added or lost", result != null && result.Count == named.Count);

            // A sort that names only some of the tail, which the version before the port handled by
            // indexing positionally - leaving stale entries in place. Anything unnamed must survive.
            var partial = new List<string> { named[4].ToString() };
            var short_ = RemoteQueueBridge.QueueInVoteOrder(named, floor, partial);
            Check("a sort that names only one song still keeps the others",
                short_ != null && short_.Count == named.Count && named.All(h => short_.Contains(h)));
            Check("and puts the named one first among the unplayed",
                short_ != null && short_[2].Equals(named[4]));

            // A sort naming a song that is not in the tail at all. Positional indexing threw here.
            var bogus = new List<string> { HashWrapper.Hash(new byte[] { 77 }).ToString() };
            var ignored = RemoteQueueBridge.QueueInVoteOrder(named, floor, bogus);
            Check("a sort naming an unknown song neither throws nor loses the queue",
                ignored != null && ignored.Count == named.Count && named.All(h => ignored.Contains(h)));

            // Nothing to reorder: one song ahead, or none.
            Check("one song left ahead is not a reorder",
                RemoteQueueBridge.QueueInVoteOrder(named, 3, reversed) == null);
            Check("the last song playing is not a reorder",
                RemoteQueueBridge.QueueInVoteOrder(named, 4, reversed) == null);

            Debug.Log($"PROBE INFO: reversing the tail gave [{Shape(result, named)}] " +
                $"from [{Shape(named, named)}] with {floor} playing");
        }
    }
}
