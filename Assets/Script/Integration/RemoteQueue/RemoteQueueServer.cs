using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using UnityEngine;
using YARG.Core.Logging;
using YARG.Settings;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>
    /// A small web server inside YARG, so people on the couch can search the
    /// library and queue songs from their phones. Issue YARC-Official/YARG#860.
    ///
    /// WHY A STATIC CLASS AND NOT A MonoSingleton. The other networked
    /// integration here (DataStreamController) is a MonoBehaviour on a scene
    /// object, which means adding it to a scene or prefab. This needs no scene
    /// presence at all: it owns a socket and a thread, and everything it touches
    /// in the game goes through <see cref="RemoteQueueBridge"/>, which marshals
    /// onto the main thread anyway. Keeping it out of the scene graph also keeps
    /// the diff to upstream small, which matters for a PR.
    ///
    /// HttpListener rather than a hand-rolled socket server, and that was
    /// measured rather than assumed. On stock .NET for Windows, HttpListener is
    /// backed by http.sys and binding anything but loopback needs an admin or a
    /// URL ACL - which would have made the LAN half of this feature fail only on
    /// players' machines. Unity ships Mono's managed implementation instead:
    /// Assets/Editor/HttpListenerProbe.cs binds 127.0.0.1, "+" and "*", serves a
    /// real request through each, and all three pass with no elevation
    /// (Mono 6.13.0, Unity 6000.3.5f2). Parsing HTTP by hand for a surface that
    /// strangers on a LAN can reach would have been the riskier choice.
    ///
    /// KNOWN GAP: that measurement is the EDITOR, which is Mono. A shipped
    /// player is IL2CPP with managed stripping, and that is a different harness.
    /// It needs its own measurement before this is promised in a release.
    /// </summary>
    public static class RemoteQueueServer
    {
        /// <summary>
        /// Unregistered, memorable, and out of the way of the usual suspects.
        /// </summary>
        public const int Port = 8099;

        private static HttpListener _listener;
        private static Thread       _thread;
        private static volatile bool _running;
        private static RemoteQueueMode _mode = RemoteQueueMode.Off;

        public static bool IsRunning => _running;
        public static RemoteQueueMode Mode => _mode;

        /// <summary>Wired to the setting's onChange. Idempotent on purpose.</summary>
        public static void HandleModeChanged(RemoteQueueMode mode)
        {
            Stop();

            _mode = mode;
            if (mode == RemoteQueueMode.Off)
            {
                return;
            }

            Start(mode);
        }

        private static void Start(RemoteQueueMode mode)
        {
            // "+" binds every interface; 127.0.0.1 binds only this machine. The
            // narrow one is not a formality - in Local mode the socket is simply
            // not reachable from the network, rather than reachable and refusing.
            var prefix = mode == RemoteQueueMode.Lan
                ? $"http://+:{Port}/"
                : $"http://127.0.0.1:{Port}/";

            try
            {
                _listener = new HttpListener();
                _listener.Prefixes.Add(prefix);
                _listener.Start();
            }
            catch (Exception e)
            {
                YargLogger.LogException(e, $"Remote queue: could not listen on {prefix}");
                _listener = null;
                return;
            }

            _running = true;
            _thread = new Thread(AcceptLoop)
            {
                IsBackground = true,
                Name = "YARG Remote Queue",
            };
            _thread.Start();

            Application.quitting -= Stop;
            Application.quitting += Stop;

            YargLogger.LogFormatInfo("Remote queue: listening on {0} (mode {1})", prefix, mode);
        }

        public static void Stop()
        {
            if (!_running && _listener == null)
            {
                return;
            }

            _running = false;

            try
            {
                _listener?.Stop();
                _listener?.Close();
            }
            catch (Exception e)
            {
                YargLogger.LogException(e, "Remote queue: error while closing the listener");
            }
            finally
            {
                _listener = null;
            }

            // The accept loop is blocked in GetContext(); closing the listener is
            // what releases it. Join briefly so a mode change does not leave two
            // threads racing to bind the same port.
            try
            {
                _thread?.Join(TimeSpan.FromSeconds(2));
            }
            catch (Exception)
            {
                // A thread that will not join is not worth failing a settings change over.
            }

            _thread = null;

            // Votes are for the party that was happening. Keeping them across a
            // stop would mean a room that reconvenes inherits an argument.
            RemoteQueueVotes.Reset();

            YargLogger.LogInfo("Remote queue: stopped");
        }

        private static void AcceptLoop()
        {
            while (_running)
            {
                HttpListenerContext ctx;
                try
                {
                    ctx = _listener.GetContext();
                }
                catch (Exception)
                {
                    // Stopping the listener throws in here. That is the normal
                    // way out, so only a still-running server treats it as news.
                    if (_running)
                    {
                        YargLogger.LogWarning("Remote queue: accept failed; stopping");
                    }

                    return;
                }

                // One phone should not be able to stall the others by holding a
                // request open, and the work itself blocks on the main thread.
                ThreadPool.QueueUserWorkItem(_ => Handle(ctx));
            }
        }

        private static void Handle(HttpListenerContext ctx)
        {
            try
            {
                if (!IsCallerAllowed(ctx.Request))
                {
                    // Not 401: there is nothing to authenticate as. This caller
                    // is simply not somewhere this server answers.
                    Send(ctx, 403, "text/plain", Encoding.UTF8.GetBytes("not available from this address"));
                    return;
                }

                var path = ctx.Request.Url?.AbsolutePath ?? "/";
                var method = ctx.Request.HttpMethod;

                switch (path)
                {
                    case "/":
                        Send(ctx, 200, "text/html; charset=utf-8", RemoteQueuePage.Bytes);
                        return;

                    case "/healthz":
                        Send(ctx, 200, "text/plain", Encoding.UTF8.GetBytes("ok"));
                        return;

                    case "/api/library":
                        if (method != "GET") { SendStatus(ctx, 405, "GET only"); return; }
                        HandleLibrary(ctx);
                        return;

                    case "/api/queue":
                        HandleQueue(ctx, method);
                        return;

                    case "/api/board":
                        if (method != "GET") { SendStatus(ctx, 405, "GET only"); return; }
                        SendJson(ctx, 200, RemoteQueueBridge.GetBoard(VotesNeeded, VotingEnabled));
                        return;

                    case "/api/suggest":
                        if (method != "POST") { SendStatus(ctx, 405, "POST only"); return; }
                        HandleSuggest(ctx);
                        return;

                    case "/api/vote":
                        if (method != "POST") { SendStatus(ctx, 405, "POST only"); return; }
                        HandleVote(ctx);
                        return;

                    case "/api/decide":
                        if (method != "POST") { SendStatus(ctx, 405, "POST only"); return; }
                        HandleDecide(ctx);
                        return;

                    default:
                        SendStatus(ctx, 404, "no such endpoint");
                        return;
                }
            }
            catch (TimeoutException e)
            {
                // The game did not answer. That is a real state worth naming
                // rather than a generic 500 - it usually means it is mid-load.
                SendStatus(ctx, 503, e.Message);
            }
            catch (Exception e)
            {
                YargLogger.LogException(e, "Remote queue: request failed");
                SendStatus(ctx, 500, "internal error");
            }
        }

        private static void HandleLibrary(HttpListenerContext ctx)
        {
            var q = ctx.Request.QueryString["q"] ?? string.Empty;
            var limitText = ctx.Request.QueryString["limit"];

            var limit = 100;
            if (int.TryParse(limitText, out var parsed))
            {
                limit = Math.Clamp(parsed, 1, 500);
            }

            var songs = RemoteQueueBridge.Search(q, limit);
            SendJson(ctx, 200, new
            {
                query = q,
                total = RemoteQueueBridge.LibraryCount,
                shown = songs.Count,
                songs,
            });
        }

        private static void HandleQueue(HttpListenerContext ctx, string method)
        {
            switch (method)
            {
                case "GET":
                {
                    SendJson(ctx, 200, RemoteQueueBridge.GetQueue());
                    return;
                }

                case "POST":
                {
                    var body = ReadBody(ctx.Request);
                    var hash = ReadHash(body, ctx);
                    if (hash == null) { SendStatus(ctx, 400, "a 'hash' is required"); return; }

                    var action = ctx.Request.QueryString["action"];
                    if (action is "up" or "down")
                    {
                        var moved = RemoteQueueBridge.Move(hash, action == "up");
                        if (!moved) { SendStatus(ctx, 409, "that song cannot be moved from where it is"); return; }
                        SendJson(ctx, 200, new { moved = true, hash, action });
                        return;
                    }

                    var target = RemoteQueueBridge.Add(hash);
                    if (target == null) { SendStatus(ctx, 404, "no song with that hash"); return; }

                    SendJson(ctx, 200, new { queued = true, hash, target });
                    return;
                }

                case "DELETE":
                {
                    var hash = ctx.Request.QueryString["hash"];
                    if (string.IsNullOrWhiteSpace(hash)) { SendStatus(ctx, 400, "a 'hash' is required"); return; }

                    var removed = RemoteQueueBridge.Remove(hash);
                    if (!removed) { SendStatus(ctx, 409, "that song is not removable right now"); return; }

                    SendJson(ctx, 200, new { removed = true, hash });
                    return;
                }

                default:
                    SendStatus(ctx, 405, "GET, POST or DELETE");
                    return;
            }
        }

        // ------------------------------------------------------------------
        // Voting
        // ------------------------------------------------------------------

        // Defaults used when settings are not available yet. This is not
        // theoretical: the mode callback deliberately runs when a saved setting
        // is LOADED, so the listener can be accepting requests before the
        // settings object is fully there. Reading it unguarded turned every
        // voting endpoint into a 500 - found by the smoke test, which runs in
        // exactly that state.
        private const bool DefaultVoting = true;
        private const int  DefaultVotesNeeded = 3;

        private static bool VotingEnabled
        {
            get
            {
                try
                {
                    return SettingsManager.Settings?.RemoteQueueVoting?.Value ?? DefaultVoting;
                }
                catch (Exception)
                {
                    return DefaultVoting;
                }
            }
        }

        private static int VotesNeeded
        {
            get
            {
                try
                {
                    return SettingsManager.Settings?.RemoteQueueVotesNeeded?.Value ?? DefaultVotesNeeded;
                }
                catch (Exception)
                {
                    return DefaultVotesNeeded;
                }
            }
        }

        /// <summary>
        /// Who is voting. The page makes a random id and keeps it in the browser;
        /// the remote address is the fallback when it does not send one.
        ///
        /// This stops the ordinary double-tap and one phone voting twenty times.
        /// It does NOT stop somebody clearing their storage or opening a private
        /// tab, and it is not trying to: a party jukebox that needed real
        /// accounts would not get used.
        /// </summary>
        private static string VoterOf(HttpListenerRequest request)
        {
            var declared = request.Headers["X-Voter"];
            if (!string.IsNullOrWhiteSpace(declared) && declared.Length <= 64)
            {
                return declared.Trim();
            }

            return request.RemoteEndPoint?.Address?.ToString() ?? "unknown";
        }

        private static void HandleSuggest(HttpListenerContext ctx)
        {
            if (!VotingEnabled) { SendStatus(ctx, 404, "voting is off"); return; }

            var hash = ReadHash(ReadBody(ctx.Request), ctx);
            if (hash == null) { SendStatus(ctx, 400, "a 'hash' is required"); return; }

            var nomination = RemoteQueueBridge.Suggest(hash, VoterOf(ctx.Request));
            if (nomination == null) { SendStatus(ctx, 404, "no song with that hash"); return; }

            SendJson(ctx, 200, nomination);
        }

        private static void HandleVote(HttpListenerContext ctx)
        {
            if (!VotingEnabled) { SendStatus(ctx, 404, "voting is off"); return; }

            var body = ReadBody(ctx.Request);
            var hash = ReadHash(body, ctx);
            if (hash == null) { SendStatus(ctx, 400, "a 'hash' is required"); return; }

            var down = string.Equals(ctx.Request.QueryString["dir"], "down", StringComparison.OrdinalIgnoreCase);
            var delta = down ? -1 : 1;
            var voter = VoterOf(ctx.Request);

            // "queued" votes reorder the queue; "suggestion" votes decide whether
            // a song gets in at all. Same gesture on the phone, different lists.
            if (string.Equals(ctx.Request.QueryString["on"], "queued", StringComparison.OrdinalIgnoreCase))
            {
                if (!RemoteQueueBridge.VoteQueued(hash, voter, delta))
                {
                    SendStatus(ctx, 404, "no song with that hash");
                    return;
                }

                SendJson(ctx, 200, new { voted = true, on = "queued", hash, dir = down ? "down" : "up" });
                return;
            }

            var promoted = RemoteQueueBridge.VoteSuggestion(hash, voter, delta, VotesNeeded);
            SendJson(ctx, 200, new { voted = true, on = "suggestion", hash, promoted });
        }

        private static void HandleDecide(HttpListenerContext ctx)
        {
            if (!VotingEnabled) { SendStatus(ctx, 404, "voting is off"); return; }

            var body = ReadBody(ctx.Request);
            var hash = ReadHash(body, ctx);
            if (hash == null) { SendStatus(ctx, 400, "a 'hash' is required"); return; }

            var choice = ctx.Request.QueryString["choice"];
            var playNext = string.Equals(choice, "next", StringComparison.OrdinalIgnoreCase);
            if (!playNext && !string.Equals(choice, "setlist", StringComparison.OrdinalIgnoreCase))
            {
                SendStatus(ctx, 400, "choice must be 'next' or 'setlist'");
                return;
            }

            var outcome = RemoteQueueBridge.VoteOutcome(hash, VoterOf(ctx.Request), playNext, VotesNeeded);
            SendJson(ctx, 200, new
            {
                voted = true,
                hash,
                choice = playNext ? "next" : "setlist",
                decided = outcome != NominationOutcome.None,
                outcome = outcome.ToString(),
            });
        }

        /// <summary>
        /// Decides whether this caller may be answered at all.
        ///
        /// Locality comes from the socket's own remote address and NEVER from a
        /// header. X-Forwarded-For is caller-supplied, so trusting it would make
        /// "local only" a polite suggestion.
        ///
        /// In LAN mode this additionally refuses anything that is not a private
        /// address. It is a small check that turns an accidental port-forward
        /// from "the internet can queue songs on my TV" into a 403.
        /// </summary>
        private static bool IsCallerAllowed(HttpListenerRequest request)
        {
            var address = request.RemoteEndPoint?.Address;
            if (address == null)
            {
                return false;
            }

            if (IPAddress.IsLoopback(address))
            {
                return true;
            }

            if (_mode != RemoteQueueMode.Lan)
            {
                return false;
            }

            return IsPrivate(address);
        }

        private static bool IsPrivate(IPAddress address)
        {
            if (address.AddressFamily == AddressFamily.InterNetworkV6)
            {
                // Link-local (fe80::/10) and unique-local (fc00::/7).
                return address.IsIPv6LinkLocal || (address.GetAddressBytes()[0] & 0xFE) == 0xFC;
            }

            var b = address.GetAddressBytes();
            return b[0] == 10                                   // 10.0.0.0/8
                || (b[0] == 192 && b[1] == 168)                 // 192.168.0.0/16
                || (b[0] == 172 && b[1] >= 16 && b[1] <= 31)    // 172.16.0.0/12
                || (b[0] == 169 && b[1] == 254)                 // link-local
                // 100.64.0.0/10. Shared address space, and the range Tailscale
                // and similar overlays hand out - which for a lot of people IS
                // how their other devices reach this machine. Found by the smoke
                // test: on a box whose only non-loopback address is Tailscale,
                // refusing this made LAN mode reject every caller including the
                // player's own phone. It does not widen exposure to the internet
                // either: a stranger arriving over a port-forward presents their
                // public address, not a 100.x one.
                || (b[0] == 100 && b[1] >= 64 && b[1] <= 127);
        }

        // ------------------------------------------------------------------
        // Plumbing
        // ------------------------------------------------------------------

        private static string ReadBody(HttpListenerRequest request)
        {
            using var reader = new StreamReader(request.InputStream, request.ContentEncoding ?? Encoding.UTF8);
            return reader.ReadToEnd();
        }

        /// <summary>Accepts the hash as JSON, as a form field, or as a query parameter.</summary>
        private static string ReadHash(string body, HttpListenerContext ctx)
        {
            var fromQuery = ctx.Request.QueryString["hash"];
            if (!string.IsNullOrWhiteSpace(fromQuery))
            {
                return fromQuery;
            }

            if (string.IsNullOrWhiteSpace(body))
            {
                return null;
            }

            try
            {
                var parsed = JsonConvert.DeserializeObject<Dictionary<string, string>>(body);
                if (parsed != null && parsed.TryGetValue("hash", out var hash) && !string.IsNullOrWhiteSpace(hash))
                {
                    return hash;
                }
            }
            catch (JsonException)
            {
                // Not JSON. Fall through - a malformed body is a 400, not a 500.
            }

            return null;
        }

        private static void SendJson(HttpListenerContext ctx, int status, object payload)
        {
            var json = JsonConvert.SerializeObject(payload);
            Send(ctx, status, "application/json; charset=utf-8", Encoding.UTF8.GetBytes(json));
        }

        private static void SendStatus(HttpListenerContext ctx, int status, string message)
            => SendJson(ctx, status, new { error = message });

        private static void Send(HttpListenerContext ctx, int status, string contentType, byte[] body)
        {
            try
            {
                ctx.Response.StatusCode = status;
                ctx.Response.ContentType = contentType;
                ctx.Response.ContentLength64 = body.Length;

                // The page is served from this same origin, so no CORS is needed
                // and none is granted: a browser on some other site should not be
                // able to drive somebody's game.
                ctx.Response.OutputStream.Write(body, 0, body.Length);
            }
            catch (Exception)
            {
                // A phone that walked out of wifi mid-response is not an error
                // worth logging on every occurrence.
            }
            finally
            {
                try { ctx.Response.Close(); } catch { /* best effort */ }
            }
        }
    }
}
