using System;
using System.Net;
using System.Net.Http;
using System.Text;
using UnityEditor;
using UnityEngine;
using YARG.Integration.RemoteQueue;

namespace Editor
{
    /// <summary>
    /// A hostile client, pointed at our own server, that PRINTS what happens
    /// rather than asserting what should.
    ///
    /// Written this way on purpose: the same approach found five things in the
    /// archive reader that reasoning about the standard library had missed. An
    /// assertion can only fail in the way its author imagined, so the first pass
    /// at an attacker-facing surface should observe, not judge. Assertions come
    /// after, written against what was actually seen.
    ///
    /// This is not a penetration test of the network. It is the set of questions
    /// a stranger on the same wifi - or a web page open on any device in the
    /// house - can ask this server without being invited.
    /// </summary>
    public static class RemoteQueueSecurityProbe
    {
        private static HttpClient _http;
        private const string Base = "http://127.0.0.1:8099";

        public static void Run()
        {
            _http = new HttpClient { Timeout = TimeSpan.FromSeconds(20) };
            EditorApplication.update += Once;
        }

        private static bool _started;
        private static volatile bool _done;

        private static void Once()
        {
            if (_started)
            {
                if (_done)
                {
                    EditorApplication.update -= Once;
                    EditorApplication.Exit(0);
                }

                return;
            }

            _started = true;

            var worker = new System.Threading.Thread(() =>
            {
                try
                {
                    Probe();
                }
                catch (Exception e)
                {
                    Log("probe threw: " + e);
                }

                _done = true;
            }) { IsBackground = true };
            worker.Start();
        }

        private static void Probe()
        {
            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Local);
            System.Threading.Thread.Sleep(500);

            Log("=== 1. how big a body will it swallow? ===");
            foreach (var mb in new[] { 1, 8 })
            {
                var payload = new string('A', mb * 1024 * 1024);
                var body = "{\"hash\":\"" + payload + "\"}";
                var sw = System.Diagnostics.Stopwatch.StartNew();
                var (status, _) = Post("/api/queue", body, null);
                sw.Stop();
                Log($"  {mb} MB body -> HTTP {status} in {sw.ElapsedMilliseconds} ms");
            }

            Log("=== 2. cross-origin: can a web page on another site drive this? ===");
            // A browser sends Origin on cross-site requests. A "simple" POST -
            // no custom headers, a form-ish content type - is sent WITHOUT a
            // preflight, so the server sees it and acts before the browser ever
            // checks whether it was allowed to.
            var (xoStatus, xoBody) = Post("/api/queue?hash=0000000000000000000000000000000000000000",
                string.Empty, ("Origin", "http://evil.example"));
            Log($"  cross-origin POST with Origin header -> HTTP {xoStatus} {Trim(xoBody)}");

            var (xoDelete, _) = Send(HttpMethod.Delete,
                "/api/queue?hash=0000000000000000000000000000000000000000", null, ("Origin", "http://evil.example"));
            Log($"  cross-origin DELETE -> HTTP {xoDelete}");

            var (xoVote, _) = Post("/api/vote?hash=0000000000000000000000000000000000000000&on=queued",
                string.Empty, ("Origin", "http://evil.example"));
            Log($"  cross-origin vote -> HTTP {xoVote}");

            Log("=== 3. does the legitimate page still work? ===");
            // The control that matters: everything above must still be REJECTED
            // while our own page's request shape is ACCEPTED. Without this the
            // probe cannot tell a fix from a brick.
            _actLikeOurPage = true;
            var (okQueue, okBody) = Post("/api/queue?hash=0000000000000000000000000000000000000000",
                string.Empty, null);
            Log($"  our page's POST -> HTTP {okQueue} {Trim(okBody)}   (404 = reached the handler)");
            var (okDelete, _) = Send(HttpMethod.Delete,
                "/api/queue?hash=0000000000000000000000000000000000000000", null, null);
            Log($"  our page's DELETE -> HTTP {okDelete}   (409 = reached the handler)");
            var (sameOrigin, _) = Post("/api/queue?hash=0000000000000000000000000000000000000000",
                string.Empty, ("Origin", "http://127.0.0.1:8099"));
            Log($"  our page's POST with its OWN Origin -> HTTP {sameOrigin}");
            _actLikeOurPage = false;

            Log("=== 4. does the suggestion board have a ceiling? ===");
            RemoteQueueVotes.Reset();
            for (var i = 0; i < 5000; i++)
            {
                RemoteQueueVotes.Suggest("hash" + i, "voter" + i);
            }

            Log($"  after 5000 suggestions the board holds {RemoteQueueVotes.SuggestionCount}");

            Log("=== 5. what does the vote store do with distinct identities? ===");
            // NOTE ON WHAT THIS CAN AND CANNOT SHOW. The HTTP vote path resolves
            // a hash against the song library, and batchmode has no library, so
            // votes cannot be driven end to end from here. What this measures is
            // the STORE: given N distinct voter ids it counts N votes, exactly as
            // designed. That is the reason identity must not be something the
            // caller can choose - and it no longer is, because the server now
            // takes it from the socket. That change is structural rather than
            // demonstrable here, and is called out as such in the audit.
            RemoteQueueVotes.Reset();
            RemoteQueueVotes.Suggest("target", "seed");
            for (var i = 0; i < 20; i++)
            {
                RemoteQueueVotes.VoteSuggestion("target", "sock" + i, 1, 999);
            }

            var board = RemoteQueueVotes.Suggestions();
            Log($"  20 distinct identities -> score {board[0].Score} (so identity must come from the socket)");

            Log("=== 6. what does an unknown method do? ===");
            var (putStatus, _) = Send(new HttpMethod("PUT"), "/api/queue", "{}", null);
            Log($"  PUT /api/queue -> HTTP {putStatus}");

            Log("=== 7. is there a static file handler to walk out of? ===");
            foreach (var path in new[] { "/../../etc/passwd", "/..%2f..%2fwindows/win.ini", "/index.html" })
            {
                var (s, _) = Get(path);
                Log($"  GET {path} -> HTTP {s}");
            }

            RemoteQueueVotes.Reset();
            RemoteQueueServer.HandleModeChanged(RemoteQueueMode.Off);
            Log("=== done ===");
        }

        private static string Trim(string s) =>
            string.IsNullOrEmpty(s) ? string.Empty : s.Substring(0, Math.Min(90, s.Length)).Replace("\n", " ");

        private static (int, string) Get(string path) => Send(HttpMethod.Get, path, null, null);

        private static (int, string) Post(string path, string body, (string, string)? header) =>
            Send(HttpMethod.Post, path, body, header);

        /// <summary>
        /// Set on the calls that are meant to look like OUR page, so the probe
        /// can tell "the fix rejected a hostile shape" apart from "the fix broke
        /// the page too". A security control that also breaks the legitimate
        /// client is not a fix.
        /// </summary>
        private static bool _actLikeOurPage;

        private static (int, string) Send(HttpMethod method, string path, string body, (string, string)? header)
        {
            try
            {
                var request = new HttpRequestMessage(method, Base + path);
                if (body != null)
                {
                    request.Content = new StringContent(body, Encoding.UTF8, "text/plain");
                }

                if (_actLikeOurPage)
                {
                    request.Headers.TryAddWithoutValidation("X-Yarg-Remote", "1");
                }

                if (header.HasValue)
                {
                    request.Headers.TryAddWithoutValidation(header.Value.Item1, header.Value.Item2);
                }

                var response = _http.SendAsync(request).GetAwaiter().GetResult();
                return ((int) response.StatusCode,
                    response.Content.ReadAsStringAsync().GetAwaiter().GetResult());
            }
            catch (Exception e)
            {
                return (0, e.GetType().Name + ": " + e.Message);
            }
        }

        private static void Log(string s)
        {
            Debug.Log("[SecProbe] " + s);
            Console.WriteLine("[SecProbe] " + s);
        }
    }
}
