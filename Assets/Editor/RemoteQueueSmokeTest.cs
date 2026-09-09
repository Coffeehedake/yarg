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

            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Off);
            Check("Off again: the socket is closed", !CanConnect(IPAddress.Loopback));
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
