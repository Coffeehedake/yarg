using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using UnityEditor;
using UnityEngine;
using YARG;
using YARG.Integration.RemoteQueue;

namespace Editor
{
    /// <summary>
    /// Drives the remote queue server over real HTTP and checks what comes back.
    ///
    /// WHAT THIS HARNESS PROVES, and it is deliberately less than the feature:
    /// that the server binds where the mode says it should and NOWHERE ELSE,
    /// that the routes answer with the right status codes and JSON, that a
    /// request really does reach Unity's main thread and back, and that stopping
    /// it actually closes the socket.
    ///
    /// WHAT IT DOES NOT PROVE. There is no menu scene and no song library in
    /// batchmode, so the two-queue routing - setlist vs running show vs pending -
    /// is NOT exercised here. That needs the real game, and until somebody plays
    /// it, "queued songs appear in the setlist" is inference. Said plainly rather
    /// than implied by a green run.
    ///
    /// ONE HARNESS DIFFERENCE, stated because it matters: in the real game
    /// UnityMainThreadCallback drains its queue from MonoBehaviour.Update(),
    /// which does not run in edit mode. This test drains THE SAME QUEUE from
    /// EditorApplication.update instead. Same actions, same order, different
    /// pump - so a defect that only appears under the real Update loop would not
    /// be caught here.
    ///
    /// Run with NO -quit; the test exits the process itself.
    /// </summary>
    public static class RemoteQueueSmokeTest
    {
        private static readonly List<string> _failures = new();
        private static HttpClient _http;

        public static void Run()
        {
            _http = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
            StartMainThreadPump();
            EditorApplication.update += RunOnce;
        }

        private static bool _started;

        private static void RunOnce()
        {
            if (_started)
            {
                return;
            }

            _started = true;

            // The requests MUST run off the editor's update loop. The first
            // version of this test called Execute() straight from here, and the
            // two endpoints that marshal onto the main thread hung and failed -
            // because the pump below is also driven by EditorApplication.update,
            // and blocking inside one update callback means the pump never runs.
            // The endpoints were fine; the harness was deadlocking itself.
            var worker = new System.Threading.Thread(() =>
            {
                try
                {
                    Execute();
                }
                catch (Exception e)
                {
                    Fail("the test itself threw: " + e);
                }

                _done = true;
            }) { IsBackground = true, Name = "RemoteQueueSmokeTest" };

            worker.Start();
            EditorApplication.update += Finish;
        }

        private static volatile bool _done;

        private static void Finish()
        {
            if (!_done)
            {
                return;
            }

            EditorApplication.update -= Finish;

            Log("");
            if (_failures.Count == 0)
            {
                Log("PASS");
                EditorApplication.Exit(0);
            }
            else
            {
                Log($"FAIL with {_failures.Count} problem(s):");
                foreach (var f in _failures)
                {
                    Log("  - " + f);
                }

                EditorApplication.Exit(1);
            }
        }

        private static void Execute()
        {
            var lan = FindLanAddress();
            Log("lan address for the negative test = " + (lan?.ToString() ?? "(none found)"));

            // ---------------------------------------------------------------
            // Off means no socket at all.
            // ---------------------------------------------------------------
            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Off);
            Check("Off: nothing is listening", !CanConnect(IPAddress.Loopback));

            // ---------------------------------------------------------------
            // Local binds loopback ONLY. The second half is the one that matters:
            // "local" has to mean unreachable from the network, not reachable
            // and refusing, or a player's idea of private is wrong.
            // ---------------------------------------------------------------
            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Local);
            Check("Local: loopback answers", Get("http://127.0.0.1:8099/healthz") == "ok");

            if (lan != null)
            {
                Check("Local: the LAN address does NOT answer", !CanConnect(lan));
            }
            else
            {
                Log("SKIP: no non-loopback address on this machine, so the negative test cannot run");
            }

            // ---------------------------------------------------------------
            // Routing and shapes.
            // ---------------------------------------------------------------
            var (status, body) = GetWithStatus("http://127.0.0.1:8099/nope");
            Check("unknown path is 404", status == 404);
            Check("unknown path answers JSON with a reason", body.Contains("\"error\""));

            var page = Get("http://127.0.0.1:8099/");
            Check("the page is served", page != null && page.Contains("<title>YARG queue</title>"));

            // Reaches Unity's main thread and back. With no library loaded the
            // honest answer is zero songs - which is still a real round trip.
            var (libStatus, lib) = GetWithStatus("http://127.0.0.1:8099/api/library");
            Check("library answers 200", libStatus == 200);
            Check("library reports a total", lib.Contains("\"total\""));

            var (qStatus, queue) = GetWithStatus("http://127.0.0.1:8099/api/queue");
            Check("queue answers 200", qStatus == 200);
            Check("queue names which queue it means", queue.Contains("\"target\""));

            // A hash nobody has is a 404, not a 500 and not a silent success.
            var (addStatus, addBody) = PostWithStatus("http://127.0.0.1:8099/api/queue",
                "{\"hash\":\"0000000000000000000000000000000000000000\"}");
            Check("queueing an unknown hash is 404", addStatus == 404);
            Check("queueing an unknown hash explains itself", addBody.Contains("no song with that hash"));

            var (badStatus, _) = PostWithStatus("http://127.0.0.1:8099/api/queue", "{}");
            Check("queueing with no hash is 400", badStatus == 400);

            var (garbageStatus, _) = PostWithStatus("http://127.0.0.1:8099/api/queue", "not json at all");
            Check("a garbage body is 400, not 500", garbageStatus == 400);

            // ---------------------------------------------------------------
            // Lan opens it up, and Off closes it again.
            // ---------------------------------------------------------------
            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Lan);
            Check("Lan: loopback still answers", Get("http://127.0.0.1:8099/healthz") == "ok");
            if (lan != null)
            {
                Check("Lan: the LAN address answers", Get($"http://{lan}:8099/healthz") == "ok");
            }

            // ---------------------------------------------------------------
            // Voting endpoints. With no library loaded these can only reach the
            // rejection paths - the rules themselves are checked below, where
            // they can be checked properly.
            // ---------------------------------------------------------------
            var (boardStatus, boardBody) = GetWithStatus("http://127.0.0.1:8099/api/board");
            Check("board answers 200", boardStatus == 200);
            Check("board carries the vote threshold", boardBody.Contains("\"threshold\""));

            var (sugStatus, _) = PostWithStatus(
                "http://127.0.0.1:8099/api/suggest?hash=0000000000000000000000000000000000000000", "");
            Check("suggesting an unknown song is 404", sugStatus == 404);

            var (decideStatus, _) = PostWithStatus(
                "http://127.0.0.1:8099/api/decide?hash=0000000000000000000000000000000000000000&choice=sideways", "");
            Check("a nonsense decision is 400", decideStatus == 400);

            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Off);
            Check("Off again: the socket is closed", !CanConnect(IPAddress.Loopback));

            CheckVotingRules();
            CheckIntermissionRules();
        }

        /// <summary>
        /// The voting window between songs. Also plain data, also checkable here.
        /// </summary>
        private static void CheckIntermissionRules()
        {
            const string a = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
            const string b = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
            const string c = "cccccccccccccccccccccccccccccccccccccccc";

            RemoteQueueVotes.Reset();
            RemoteQueueIntermission.Close();

            Check("no window means nothing is held", !RemoteQueueIntermission.ShouldHold());

            RemoteQueueIntermission.Open(30);
            Check("an opened window is open", RemoteQueueIntermission.IsOpen);
            Check("a window with nothing suggested holds nothing",
                !RemoteQueueIntermission.ShouldHold());

            RemoteQueueVotes.Suggest(a, "alice");
            Check("a window with a suggestion holds", RemoteQueueIntermission.ShouldHold());

            RemoteQueueIntermission.Close();
            Check("closing releases the hold", !RemoteQueueIntermission.ShouldHold());

            // A window that runs out reports it, so Update can settle the vote.
            RemoteQueueIntermission.Open(1);
            System.Threading.Thread.Sleep(1300);
            Check("a window that runs out is no longer open", !RemoteQueueIntermission.IsOpen);
            Check("a window that runs out reports having expired", RemoteQueueIntermission.HasExpired);

            // Expiry: the leading net-positive suggestion wins, negatives are
            // dropped, and everything else survives for the next gap.
            RemoteQueueVotes.Reset();
            RemoteQueueVotes.Suggest(a, "alice");                       // score 1
            RemoteQueueVotes.Suggest(b, "bob");                         // score 1 ...
            RemoteQueueVotes.VoteSuggestion(b, "carol", 1, 99);         // ... then 2
            RemoteQueueVotes.Suggest(c, "dave");                        // score 1 ...
            RemoteQueueVotes.VoteSuggestion(c, "erin", -1, 99);         // ... then 0
            RemoteQueueVotes.VoteSuggestion(c, "frank", -1, 99);        // ... then -1

            var (winner, outcome) = RemoteQueueVotes.ResolveExpiry();
            Check("the leading suggestion wins on expiry", winner == b);
            Check("a suggestion that never reached the second vote goes to the setlist",
                outcome == NominationOutcome.AddToSetlist);

            var left = RemoteQueueVotes.Suggestions();
            Check("the disliked suggestion is dropped", left.All(n => n.Hash != c));
            Check("an unresolved suggestion survives for the next gap",
                left.Any(n => n.Hash == a));

            // One already at the second vote outranks a higher-scoring suggestion
            // that has not got there yet, and its own side decides where it goes.
            RemoteQueueVotes.Reset();
            RemoteQueueVotes.Suggest(a, "alice");
            RemoteQueueVotes.VoteSuggestion(a, "bob", 1, 2);   // promoted at 2
            RemoteQueueVotes.VoteOutcome(a, "alice", true, 99); // one for play-next
            RemoteQueueVotes.Suggest(b, "carol");
            RemoteQueueVotes.VoteSuggestion(b, "dave", 1, 99);
            RemoteQueueVotes.VoteSuggestion(b, "erin", 1, 99); // score 3, still stage one

            var (winner2, outcome2) = RemoteQueueVotes.ResolveExpiry();
            Check("a promoted suggestion outranks a higher-scoring un-promoted one", winner2 == a);
            Check("its own second-vote lead decides where it goes",
                outcome2 == NominationOutcome.PlayNext);

            RemoteQueueVotes.Reset();
            RemoteQueueIntermission.Close();
        }

        /// <summary>
        /// The voting rules, exercised directly.
        ///
        /// This is the part of the feature batchmode CAN verify properly: the
        /// rules are plain data with no Unity in them, so unlike the queue
        /// plumbing there is no "we think it works" here.
        /// </summary>
        private static void CheckVotingRules()
        {
            const int threshold = 3;
            const string a = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
            const string b = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

            RemoteQueueVotes.Reset();

            // Suggesting counts as the suggester's own upvote.
            var nomination = RemoteQueueVotes.Suggest(a, "alice");
            Check("suggesting counts as one vote", nomination.Score == 1);

            // One voter, one vote - tapping twice must not count twice.
            RemoteQueueVotes.VoteSuggestion(a, "bob", 1, threshold);
            RemoteQueueVotes.VoteSuggestion(a, "bob", 1, threshold);
            Check("one voter cannot vote twice", RemoteQueueVotes.Suggestions()[0].Score == 2);

            // A voter changing their mind moves their vote rather than adding one.
            RemoteQueueVotes.VoteSuggestion(a, "bob", -1, threshold);
            Check("changing your mind moves your vote", RemoteQueueVotes.Suggestions()[0].Score == 0);
            RemoteQueueVotes.VoteSuggestion(a, "bob", 1, threshold);

            // The third distinct voter is the one that promotes it.
            var promoted = RemoteQueueVotes.VoteSuggestion(a, "carol", 1, threshold);
            Check("reaching the threshold promotes", promoted);
            Check("a promoted suggestion is now deciding",
                RemoteQueueVotes.Suggestions()[0].Stage == NominationStage.Deciding);

            // ...and only once, so the queue cannot be hit twice by one song.
            var again = RemoteQueueVotes.VoteSuggestion(a, "dave", 1, threshold);
            Check("promotion happens exactly once", !again);

            // The second vote: first side to the threshold wins.
            Check("one vote does not settle it",
                RemoteQueueVotes.VoteOutcome(a, "alice", true, threshold) == NominationOutcome.None);
            RemoteQueueVotes.VoteOutcome(a, "bob", true, threshold);
            var outcome = RemoteQueueVotes.VoteOutcome(a, "carol", true, threshold);
            Check("three votes settle it as play-next", outcome == NominationOutcome.PlayNext);
            Check("a settled suggestion leaves the board", RemoteQueueVotes.Suggestions().Count == 0);

            // Switching sides moves the vote instead of counting on both.
            RemoteQueueVotes.Reset();
            RemoteQueueVotes.Suggest(b, "alice");
            RemoteQueueVotes.VoteSuggestion(b, "bob", 1, 2);
            RemoteQueueVotes.VoteOutcome(b, "alice", true, 2);
            RemoteQueueVotes.VoteOutcome(b, "alice", false, 2);
            var settled = RemoteQueueVotes.VoteOutcome(b, "bob", false, 2);
            Check("switching sides moves the vote", settled == NominationOutcome.AddToSetlist);

            // Ordering. Stability is what lets a hand-arranged queue survive
            // until somebody actually votes on it.
            RemoteQueueVotes.Reset();
            var order = new List<string> { "one", "two", "three" };
            var unchanged = RemoteQueueVotes.SortByScore(order);
            Check("with no votes the order is untouched",
                unchanged[0] == "one" && unchanged[1] == "two" && unchanged[2] == "three");

            RemoteQueueVotes.VoteQueued("three", "alice", 1);
            RemoteQueueVotes.VoteQueued("one", "bob", -1);
            var sorted = RemoteQueueVotes.SortByScore(order);
            Check("votes reorder highest first",
                sorted[0] == "three" && sorted[1] == "two" && sorted[2] == "one");

            RemoteQueueVotes.Reset();
        }

        // -------------------------------------------------------------------
        // The pump. Same queue the game drains in Update(), drained here instead.
        // -------------------------------------------------------------------
        private static void StartMainThreadPump()
        {
            var field = typeof(UnityMainThreadCallback)
                .GetField("CallbackQueue", BindingFlags.NonPublic | BindingFlags.Static);

            if (field?.GetValue(null) is not Queue<Action> queue)
            {
                Fail("could not reach UnityMainThreadCallback's queue; the pump would deadlock");
                return;
            }

            EditorApplication.update += () =>
            {
                while (true)
                {
                    Action action;
                    lock (queue)
                    {
                        if (queue.Count == 0)
                        {
                            return;
                        }

                        action = queue.Dequeue();
                    }

                    try
                    {
                        action.Invoke();
                    }
                    catch (Exception e)
                    {
                        Log("main thread action threw: " + e.Message);
                    }
                }
            };
        }

        // -------------------------------------------------------------------
        // Plumbing
        // -------------------------------------------------------------------
        private static IPAddress FindLanAddress()
        {
            try
            {
                return NetworkInterface.GetAllNetworkInterfaces()
                    .Where(n => n.OperationalStatus == OperationalStatus.Up)
                    .SelectMany(n => n.GetIPProperties().UnicastAddresses)
                    .Select(a => a.Address)
                    .FirstOrDefault(a => a.AddressFamily == AddressFamily.InterNetwork
                                         && !IPAddress.IsLoopback(a));
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static bool CanConnect(IPAddress address)
        {
            try
            {
                using var client = new TcpClient();
                var connect = client.BeginConnect(address, RemoteQueueServer.Port, null, null);
                var ok = connect.AsyncWaitHandle.WaitOne(TimeSpan.FromSeconds(2)) && client.Connected;
                if (ok)
                {
                    client.EndConnect(connect);
                }

                return ok;
            }
            catch (Exception)
            {
                return false;
            }
        }

        private static string Get(string url)
        {
            try
            {
                return _http.GetStringAsync(url).GetAwaiter().GetResult();
            }
            catch (Exception e)
            {
                Log($"GET {url} threw {e.GetType().Name}");
                return null;
            }
        }

        private static (int, string) GetWithStatus(string url)
        {
            try
            {
                var r = _http.GetAsync(url).GetAwaiter().GetResult();
                return ((int) r.StatusCode, r.Content.ReadAsStringAsync().GetAwaiter().GetResult());
            }
            catch (Exception e)
            {
                Log($"GET {url} threw {e.GetType().Name}");
                return (0, string.Empty);
            }
        }

        private static (int, string) PostWithStatus(string url, string body)
        {
            try
            {
                var content = new StringContent(body, Encoding.UTF8, "application/json");
                var r = _http.PostAsync(url, content).GetAwaiter().GetResult();
                return ((int) r.StatusCode, r.Content.ReadAsStringAsync().GetAwaiter().GetResult());
            }
            catch (Exception e)
            {
                Log($"POST {url} threw {e.GetType().Name}");
                return (0, string.Empty);
            }
        }

        private static void Check(string what, bool ok)
        {
            Log((ok ? "  ok   " : "  FAIL ") + what);
            if (!ok)
            {
                _failures.Add(what);
            }
        }

        private static void Fail(string message)
        {
            Log("  FAIL " + message);
            _failures.Add(message);
        }

        private static void Log(string s)
        {
            Debug.Log("[RemoteQueueSmokeTest] " + s);
            Console.WriteLine("[RemoteQueueSmokeTest] " + s);
        }
    }
}
