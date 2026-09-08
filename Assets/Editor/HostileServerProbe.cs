using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEditor;
using UnityEngine;
using YARG.Core.IO;
using YARG.Core.Song;
using YARG.Song.RemoteLibrary;
using Debug = UnityEngine.Debug;

namespace YARG.Editor
{
    /// <summary>
    /// Points the mirror at a server that lies, and checks the guarantee holds.
    /// </summary>
    /// <remarks>
    /// SongServerSync's own comment claims "a crash or a dropped link mid-download therefore
    /// cannot leave a truncated archive under a name the scanner will trust." That was true
    /// by inspection and had never been reproduced — the same standing this project's
    /// packcache eviction race had right up until CI found it on the first run that could.
    ///
    /// So this serves the four ways a download goes wrong — a body cut in half mid-transfer,
    /// a real archive served under someone else's hash, a 500, and random bytes — and then
    /// checks the invariant INDEPENDENTLY: every file named &lt;hash&gt;.sng in the folder must
    /// really contain a chart hashing to &lt;hash&gt;, computed here from YARG.Core's own SngFile
    /// and HashWrapper rather than by asking the code under test whether it was happy.
    ///
    /// The good song is served LAST, so a pass also proves four failures in a row do not
    /// abandon the run.
    /// </remarks>
    public static class HostileServerProbe
    {
        private static int _failures;

        private static void Fail(string m) { _failures++; Debug.LogError("PROBE FAIL: " + m); }
        private static void Pass(string m) => Debug.Log("PROBE PASS: " + m);

        public static void Run()
        {
            Measure().Forget();
        }

        private static async UniTaskVoid Measure()
        {
            _failures = 0;
            HostileServer server = null;
            string destination = Path.Combine(Path.GetTempPath(), "yarg-hostile-probe");

            try
            {
                string corpus = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");
                var sources = Directory.Exists(corpus)
                    ? Directory.GetFiles(corpus, "*.sng").OrderBy(x => x).ToList()
                    : new List<string>();

                if (sources.Count < 3)
                {
                    Debug.LogError("PROBE FAIL: need at least 3 real .sng files in " + corpus +
                        " (run Editor.SongServerSyncSmokeTest.Run first)");
                    EditorApplication.Exit(1);
                    return;
                }

                // A mirrored file is named for its own chart hash, so the corpus hands us
                // known-good hash/bytes pairs for free.
                string goodHash = Path.GetFileNameWithoutExtension(sources[0]);
                string truncHash = Path.GetFileNameWithoutExtension(sources[1]);
                byte[] goodBytes = File.ReadAllBytes(sources[0]);
                byte[] truncSource = File.ReadAllBytes(sources[1]);

                const string wrongHash = "0000000000000000000000000000000000000001";
                const string errorHash = "0000000000000000000000000000000000000002";
                const string garbageHash = "0000000000000000000000000000000000000003";

                // The duplicate-package case. The corpus on the live server has
                // duplicate_packages=0, so this path had never met a real 300 - and a 300 is
                // a non-success result, which is exactly what UniTask turns into an
                // exception. sources[2] is served under its own hash, so a correct client
                // ends up with a file that verifies.
                string choiceHash = Path.GetFileNameWithoutExtension(sources[2]);
                byte[] choiceBytes = File.ReadAllBytes(sources[2]);

                // The package list is server-supplied and the chosen value goes straight into
                // a query string, so it gets the same treatment the missing-list got. The
                // hostile entry sorts BELOW every hex string ('.' is 0x2E, '0' is 0x30), so a
                // client that skipped the check would pick it - this fails loudly rather than
                // by luck. The two valid entries keep the determinism assertion honest.
                string lowPackage = new string('a', 64);
                var choicePackages = new[]
                {
                    "../../../../yarg-probe-escape/package",
                    lowPackage,
                    new string('b', 64),
                };

                // A 300 whose every choice is unusable. No real song is needed: a correct
                // client never gets as far as asking for one.
                const string allBadChoiceHash = "0000000000000000000000000000000000000004";
                var allBadPackages = new[] { "../../etc/passwd", "not-hex", "" };

                // Names that are not chart hashes at all. Each one becomes a filename via
                // Path.Combine, so these are write primitives if the client trusts them -
                // and the absolute one is the worst, because Path.Combine DISCARDS its first
                // argument when the second is rooted, putting the file wherever the server
                // said rather than under the mirror.
                string escapeDir = Path.Combine(Path.GetTempPath(), "yarg-probe-escape");
                if (Directory.Exists(escapeDir))
                {
                    Directory.Delete(escapeDir, true);
                }
                Directory.CreateDirectory(escapeDir);

                var hostileNames = new[]
                {
                    "../../../../yarg-probe-escape/traversal",
                    "..\\..\\..\\..\\yarg-probe-escape\\traversal-win",
                    Path.Combine(escapeDir, "absolute").Replace('\\', '/'),
                    "not-a-hash",
                    "",
                    "0000000000000000000000000000000000000001EXTRA",
                };

                var responses = new Dictionary<string, Reply>
                {
                    // A real archive, but announced under a hash that is not its own. This is
                    // the "a proxy served something else" case, and nothing but the hash
                    // check can catch it - the bytes are a perfectly valid .sng.
                    [wrongHash] = Reply.Body(goodBytes),
                    [errorHash] = Reply.JustStatus(500),
                    [garbageHash] = Reply.Body(Encoding.ASCII.GetBytes(new string('x', 4096))),
                    // Content-Length promises the whole file; the socket closes halfway.
                    [truncHash] = Reply.Truncated(truncSource),
                    [goodHash] = Reply.Body(goodBytes),
                    [choiceHash] = Reply.MultipleChoices(choiceBytes, choicePackages),
                    [allBadChoiceHash] = Reply.MultipleChoices(Array.Empty<byte>(), allBadPackages),
                };

                // The hostile names must be SERVED, not 404'd, or the test proves only that
                // the client tried a path it should not have - not that anything reached the
                // disk. Garbage bytes are the worst case on purpose: the download succeeds,
                // so the file is written at the attacker's path; verification then rejects
                // it; and the cleanup delete is the one that cannot succeed, because
                // YARG.Core keeps a non-.sng file locked. That chain is how a transient
                // write becomes a permanent one.
                foreach (string name in hostileNames)
                {
                    responses[name] = Reply.Body(Encoding.ASCII.GetBytes(new string('x', 2048)));
                }

                // Order matters: the good one is last, so arriving proves the four failures
                // before it did not abandon the run.
                var order = new[]
                    {
                        wrongHash, errorHash, garbageHash, truncHash, allBadChoiceHash,
                        choiceHash, goodHash,
                    }
                    .Concat(hostileNames).ToArray();

                if (Directory.Exists(destination))
                {
                    Directory.Delete(destination, true);
                }
                Directory.CreateDirectory(destination);

                server = new HostileServer(responses, order);
                server.Start();
                Debug.Log($"PROBE INFO: hostile server on port {server.Port}, serving {order.Length} songs");

                var result = await SongServerSync.Sync($"http://127.0.0.1:{server.Port}", destination);

                Debug.Log($"PROBE INFO: {result}");

                // ---- what the sync reported ----
                if (!result.Downloaded.Contains(goodHash))
                {
                    Fail("the good song did not arrive after four consecutive failures");
                }
                else
                {
                    Pass("the good song arrived, after four consecutive failures");
                }

                // The duplicate-package path: a 300 is not a failure, it is the server
                // asking the client to choose. Getting this wrong means every song that
                // exists in two packages is permanently unfetchable.
                if (!result.Downloaded.Contains(choiceHash))
                {
                    var why = result.Failures.FirstOrDefault(f => f.ChartHash == choiceHash);
                    Fail("a song offered as multiple packages was never fetched" +
                        (why.Reason == null ? "" : $": {why.Reason}"));
                }
                else
                {
                    Pass("a song offered as multiple packages was fetched by choosing one");
                }

                // ---- the CHOSEN package must be one the server could have meant ----
                // A package hash reaches a URL, not a filename, so this is a smaller hole
                // than the missing-list was - but it was the last server-supplied string the
                // client used without looking at it.
                List<string> asked;
                lock (server.RequestedPackages)
                {
                    asked = server.RequestedPackages.ToList();
                }
                Debug.Log($"PROBE INFO: the client asked for package(s): " +
                    string.Join(", ", asked.Select(a => a.Length > 12 ? a[..12] + "\u2026" : a)));

                if (asked.Count != 1)
                {
                    Fail($"expected exactly one ?package= request, saw {asked.Count} " +
                        $"({string.Join(", ", asked)})");
                }
                else if (asked[0] != lowPackage)
                {
                    Fail($"the client asked for package '{asked[0]}', which is not the lowest " +
                        "WELL-FORMED hash it was offered");
                }
                else
                {
                    Pass("the client skipped the malformed package hash and chose the lowest " +
                        "well-formed one");
                }

                var allBad = result.Failures.FirstOrDefault(f => f.ChartHash == allBadChoiceHash);
                if (allBad.Reason == null)
                {
                    Fail("a 300 listing nothing but malformed package hashes did not fail");
                }
                else if (!allBad.Reason.Contains("package_hash"))
                {
                    Fail($"a 300 listing nothing but malformed package hashes failed with " +
                        $"'{allBad.Reason}', which does not say what was wrong");
                }
                else
                {
                    Pass($"a 300 with no usable package hash is refused: '{allBad.Reason}'");
                }

                // Four download failures. The hostile names are refused before any request is
                // made, so they are rejections rather than failures - a distinction worth
                // keeping, because one means the server is broken and the other means it is
                // lying about what it holds.
                if (result.Failures.Count != 5)
                {
                    Fail($"expected 5 collected failures, got {result.Failures.Count}");
                }
                else
                {
                    Pass("all five bad songs were collected as failures, not thrown");
                    foreach (var (hash, reason) in result.Failures)
                    {
                        Debug.Log($"PROBE INFO:   {hash[^4..]} -> {reason}");
                    }
                }

                // A reason nobody can act on is barely better than no reason. The cut-off
                // body is the case that produced a bare "Unknown Error" from
                // UnityWebRequest, which names neither the cause nor anything to check.
                var truncFailure = result.Failures.FirstOrDefault(f => f.ChartHash == truncHash);
                if (truncFailure.Reason == null)
                {
                    Fail("the truncated download did not fail at all");
                }
                else if (!truncFailure.Reason.Contains("bytes"))
                {
                    Fail($"a cut-off download says '{truncFailure.Reason}', which gives the " +
                        "player nothing to act on - it should say how much arrived");
                }
                else
                {
                    Pass($"a cut-off download explains itself: '{truncFailure.Reason}'");
                }

                // ---- names that are not chart hashes must never reach the disk ----
                if (result.RejectedNames != hostileNames.Length)
                {
                    Fail($"the client accepted {hostileNames.Length - result.RejectedNames} of " +
                        $"{hostileNames.Length} names that are not chart hashes");
                }
                else
                {
                    Pass($"all {hostileNames.Length} non-hash names were refused before becoming a path");
                }

                var escaped = Directory.Exists(escapeDir)
                    ? Directory.GetFileSystemEntries(escapeDir)
                    : Array.Empty<string>();
                if (escaped.Length > 0)
                {
                    Fail($"the server wrote {escaped.Length} file(s) OUTSIDE the mirror: " +
                        string.Join(", ", escaped.Select(Path.GetFileName)));
                }
                else
                {
                    Pass("nothing was written outside the mirror folder");
                }

                // Every file that did land must be named like one of ours.
                foreach (string path in Directory.GetFileSystemEntries(destination))
                {
                    string name = Path.GetFileName(path);
                    if (!name.EndsWith(".sng") && !name.EndsWith(".part"))
                    {
                        Fail($"an unexpected file appeared in the mirror: {name}");
                    }
                }

                // ---- the failure reasons must be the REAL ones ----
                // A cleanup delete that throws will happily replace "this is not a .sng"
                // with "the file is in use", which points at the wrong thing entirely.
                var masked = result.Failures
                    .Where(f => f.Reason.Contains("being used by another process") ||
                        f.Reason.Contains("Object reference not set"))
                    .ToList();
                if (masked.Count > 0)
                {
                    Fail($"{masked.Count} failure(s) report a file-locking error instead of why " +
                        "the download was rejected");
                }
                else
                {
                    Pass("every failure reports its real cause, not a cleanup error");
                }

                // ---- what is actually on disk ----
                // A leftover .part is tolerated: on Windows a rejected download can still be
                // locked by YARG.Core (see SngFile.TryLoadFromFile). What must be true is
                // that it is not a song and that it does not accumulate.
                var leftovers = Directory.GetFiles(destination, "*.part").ToList();
                Debug.Log($"PROBE INFO: {leftovers.Count} .part file(s) after the first sync");

                var landed = Directory.GetFiles(destination, "*.sng")
                    .Select(Path.GetFileNameWithoutExtension).ToList();

                foreach (string bad in new[]
                    { wrongHash, errorHash, garbageHash, truncHash, allBadChoiceHash })
                {
                    if (landed.Contains(bad))
                    {
                        Fail($"{bad[^4..]} was accepted and is now named as a song the scanner will trust");
                    }
                }

                // ---- THE INVARIANT, checked independently ----
                int checkedFiles = 0;
                foreach (string path in Directory.GetFiles(destination, "*.sng"))
                {
                    checkedFiles++;
                    string named = Path.GetFileNameWithoutExtension(path);
                    string actual = ChartHashOf(path);
                    if (actual == null)
                    {
                        Fail($"{named[^4..]}.sng is not a readable .sng but is sitting in the mirror");
                    }
                    else if (!string.Equals(actual, named, StringComparison.OrdinalIgnoreCase))
                    {
                        Fail($"a file named {named} actually contains chart {actual}");
                    }
                }

                if (_failures == 0)
                {
                    Pass($"every one of {checkedFiles} archive(s) in the mirror hashes to its own name");
                }

                // ---- a second sync must clean up after the first ----
                // The leaked FileStream upstream keeps the rejected .part locked for as long
                // as it is unfinalized, which in a real game means "until this process
                // exits". Collecting here releases it, so what follows tests OUR sweep
                // rather than the OS holding a handle we did not open.
                GC.Collect();
                GC.WaitForPendingFinalizers();

                var second = await SongServerSync.Sync($"http://127.0.0.1:{server.Port}", destination);
                Debug.Log($"PROBE INFO: second run {second}");

                // The server is still hostile, so this run fails the same download again and
                // leaves a fresh .part. An empty folder is therefore the WRONG expectation -
                // what must be true is that dead partials do not ACCUMULATE, one per failed
                // download, forever.
                var stillThere = Directory.GetFiles(destination, "*.part").ToList();

                if (leftovers.Count > 0 && second.SweptPartials < leftovers.Count)
                {
                    Fail($"{leftovers.Count} dead .part file(s) were there to sweep but only " +
                        $"{second.SweptPartials} were swept");
                }
                else
                {
                    Pass($"the second sync swept {second.SweptPartials} dead .part file(s)");
                }

                if (stillThere.Count > leftovers.Count)
                {
                    Fail($".part files are accumulating: {leftovers.Count} after one sync, " +
                        $"{stillThere.Count} after two");
                }
                else
                {
                    Pass($"dead partials do not accumulate ({leftovers.Count} then " +
                        $"{stillThere.Count}, against a server that keeps failing)");
                }

                if (second.AlreadyHad != 2)
                {
                    Fail($"the second sync should have found both good songs already there, " +
                        $"saw {second.AlreadyHad}");
                }
                else
                {
                    Pass("the second sync re-used what it already had rather than re-downloading");
                }
            }
            catch (Exception e)
            {
                Fail("probe threw: " + e);
            }
            finally
            {
                server?.Dispose();
            }

            Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
            EditorApplication.Exit(_failures == 0 ? 0 : 1);
        }

        /// <summary>
        /// The chart hash a .sng really carries, computed from YARG.Core directly so this is
        /// an independent reading rather than the code under test grading itself.
        /// </summary>
        private static string ChartHashOf(string path)
        {
            string[] chartNames = { "notes.mid", "notes.midi", "notes.chart", "notes.txt" };
            try
            {
                using var sng = SngFile.TryLoadFromFile(path, false);
                if (!sng.IsLoaded)
                {
                    return null;
                }

                foreach (string name in chartNames)
                {
                    if (!sng.TryGetListing(name, out var listing))
                    {
                        continue;
                    }
                    using var data = sng.LoadAllBytes(in listing);
                    return HashWrapper.Hash(data.ReadOnlySpan).ToString();
                }
            }
            catch
            {
                return null;
            }

            return null;
        }

        private readonly struct Reply
        {
            public readonly int Status;
            public readonly byte[] Bytes;
            public readonly bool CutInHalf;
            public readonly string[] Packages;

            private Reply(int status, byte[] bytes, bool cut, string[] packages = null)
            {
                Status = status;
                Bytes = bytes;
                CutInHalf = cut;
                Packages = packages;
            }

            public static Reply Body(byte[] bytes) => new(200, bytes, false);
            public static Reply JustStatus(int status) => new(status, Array.Empty<byte>(), false);
            public static Reply Truncated(byte[] bytes) => new(200, bytes, true);

            /// <summary>
            /// Answers 300 with a package list until asked for one by name. The list is
            /// supplied by the caller because a package hash is a server-supplied string the
            /// client puts straight into a URL - so what is IN the list is the thing under
            /// test, not scenery.
            /// </summary>
            public static Reply MultipleChoices(byte[] bytes, params string[] packages) =>
                new(300, bytes, false, packages);
        }

        /// <summary>
        /// A deliberately minimal HTTP server. Raw sockets rather than HttpListener because
        /// the interesting case - promise a Content-Length and then hang up halfway - is
        /// exactly what a well-behaved HTTP stack will not let you do.
        /// </summary>
        private sealed class HostileServer : IDisposable
        {
            /// <summary>Every value the client sent as ?package=, in the order it asked.</summary>
            public readonly List<string> RequestedPackages = new();

            private readonly TcpListener _listener;
            private readonly Dictionary<string, Reply> _replies;
            private readonly string[] _order;
            private Thread _thread;
            private volatile bool _stop;

            public int Port { get; }

            public HostileServer(Dictionary<string, Reply> replies, string[] order)
            {
                _replies = replies;
                _order = order;
                _listener = new TcpListener(IPAddress.Loopback, 0);
                _listener.Start();
                Port = ((IPEndPoint) _listener.LocalEndpoint).Port;
            }

            public void Start()
            {
                _thread = new Thread(Loop) { IsBackground = true };
                _thread.Start();
            }

            private void Loop()
            {
                while (!_stop)
                {
                    try
                    {
                        using var client = _listener.AcceptTcpClient();
                        using var stream = client.GetStream();
                        Handle(stream);
                    }
                    catch
                    {
                        // A closed listener during teardown, or a client that gave up. The
                        // probe's assertions are about the mirror's folder, not about this.
                    }
                }
            }

            private void Handle(NetworkStream stream)
            {
                var header = new StringBuilder();
                var one = new byte[1];
                while (!header.ToString().EndsWith("\r\n\r\n"))
                {
                    if (stream.Read(one, 0, 1) <= 0)
                    {
                        return;
                    }
                    header.Append((char) one[0]);
                }

                string head = header.ToString();
                string requestLine = head.Split("\r\n")[0];
                string[] parts = requestLine.Split(' ');
                if (parts.Length < 2)
                {
                    return;
                }

                string method = parts[0];
                string path = parts[1];

                if (method == "POST" && path.StartsWith("/api/v1/have"))
                {
                    int length = ContentLength(head);
                    var body = new byte[length];
                    int read = 0;
                    while (read < length)
                    {
                        int n = stream.Read(body, read, length - read);
                        if (n <= 0) break;
                        read += n;
                    }

                    string json = "{\"library_total\":" + _order.Length + ",\"missing\":[" +
                        string.Join(",", _order.Select(h => "\"" + JsonEscape(h) + "\"")) + "]}";
                    Write(stream, 200, Encoding.UTF8.GetBytes(json), "application/json", false);
                    return;
                }

                if (method == "GET" && path.StartsWith("/song/"))
                {
                    string hash = path[6..];
                    int dot = hash.IndexOf(".sng", StringComparison.Ordinal);
                    if (dot > 0)
                    {
                        hash = hash[..dot];
                    }

                    if (_replies.TryGetValue(hash, out var reply))
                    {
                        int q = path.IndexOf("package=", StringComparison.Ordinal);
                        if (q >= 0)
                        {
                            // Recorded rather than assumed: the only way to know WHICH
                            // package the client picked is to watch what it asks for.
                            lock (RequestedPackages)
                            {
                                RequestedPackages.Add(path[(q + "package=".Length)..]);
                            }
                        }
                        else if (reply.Status == 300)
                        {
                            // Decline to choose, and say what the choices are - the shape the
                            // real server uses when two packages share a chart hash.
                            string body = "{\"packages\":[" + string.Join(",",
                                (reply.Packages ?? Array.Empty<string>())
                                    .Select(x => "{\"package_hash\":\"" + JsonEscape(x) + "\"}")) +
                                "]}";
                            Write(stream, 300, Encoding.UTF8.GetBytes(body), "application/json", false);
                            return;
                        }

                        Write(stream, reply.Status == 300 ? 200 : reply.Status, reply.Bytes,
                            "application/octet-stream", reply.CutInHalf);
                        return;
                    }
                }

                Write(stream, 404, Array.Empty<byte>(), "text/plain", false);
            }

            /// <summary>
            /// Escapes a string for a JSON literal. Needed because the whole point here is to
            /// send names containing backslashes, which a hand-rolled encoder gets wrong -
            /// and did, on the first run.
            /// </summary>
            private static string JsonEscape(string value)
            {
                var sb = new StringBuilder(value.Length + 8);
                foreach (char c in value)
                {
                    switch (c)
                    {
                        case '"': sb.Append("\\\""); break;
                        case '\\': sb.Append("\\\\"); break;
                        case '\n': sb.Append("\\n"); break;
                        case '\r': sb.Append("\\r"); break;
                        case '\t': sb.Append("\\t"); break;
                        default:
                            if (c < 0x20)
                            {
                                sb.Append("\\u").Append(((int) c).ToString("x4"));
                            }
                            else
                            {
                                sb.Append(c);
                            }
                            break;
                    }
                }
                return sb.ToString();
            }

            private static int ContentLength(string head)
            {
                foreach (string line in head.Split("\r\n"))
                {
                    if (line.StartsWith("Content-Length:", StringComparison.OrdinalIgnoreCase))
                    {
                        return int.Parse(line[15..].Trim());
                    }
                }
                return 0;
            }

            private static void Write(NetworkStream stream, int status, byte[] body,
                string contentType, bool cutInHalf)
            {
                // Content-Length always advertises the FULL length. When cutting, only half
                // the bytes follow and the socket closes - a client that trusts the header
                // and not the transfer keeps a half file.
                string head =
                    $"HTTP/1.1 {status} X\r\n" +
                    $"Content-Type: {contentType}\r\n" +
                    $"Content-Length: {body.Length}\r\n" +
                    "Connection: close\r\n\r\n";

                var headBytes = Encoding.ASCII.GetBytes(head);
                stream.Write(headBytes, 0, headBytes.Length);

                int send = cutInHalf ? body.Length / 2 : body.Length;
                if (send > 0)
                {
                    stream.Write(body, 0, send);
                }
                stream.Flush();
            }

            public void Dispose()
            {
                _stop = true;
                try { _listener.Stop(); } catch { }
            }
        }
    }
}
