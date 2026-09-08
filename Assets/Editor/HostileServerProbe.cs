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

                if (sources.Count < 2)
                {
                    Debug.LogError("PROBE FAIL: need at least 2 real .sng files in " + corpus +
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
                };

                // Order matters: the good one is last, so arriving proves the four failures
                // before it did not abandon the run.
                var order = new[] { wrongHash, errorHash, garbageHash, truncHash, goodHash };

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
                if (result.Downloaded.Count != 1 || !result.Downloaded.Contains(goodHash))
                {
                    Fail($"expected exactly the good song to download, got " +
                        $"[{string.Join(", ", result.Downloaded)}]");
                }
                else
                {
                    Pass("the one good song arrived, after four consecutive failures");
                }

                if (result.Failures.Count != 4)
                {
                    Fail($"expected 4 collected failures, got {result.Failures.Count}");
                }
                else
                {
                    Pass("all four bad songs were collected as failures, not thrown");
                    foreach (var (hash, reason) in result.Failures)
                    {
                        Debug.Log($"PROBE INFO:   {hash[^4..]} -> {reason}");
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

                foreach (string bad in new[] { wrongHash, errorHash, garbageHash, truncHash })
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

                if (second.AlreadyHad != 1)
                {
                    Fail($"the second sync should have found the one good song already there, " +
                        $"saw {second.AlreadyHad}");
                }
                else
                {
                    Pass("the second sync re-used the good song rather than re-downloading it");
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

            private Reply(int status, byte[] bytes, bool cut)
            {
                Status = status;
                Bytes = bytes;
                CutInHalf = cut;
            }

            public static Reply Body(byte[] bytes) => new(200, bytes, false);
            public static Reply JustStatus(int status) => new(status, Array.Empty<byte>(), false);
            public static Reply Truncated(byte[] bytes) => new(200, bytes, true);
        }

        /// <summary>
        /// A deliberately minimal HTTP server. Raw sockets rather than HttpListener because
        /// the interesting case - promise a Content-Length and then hang up halfway - is
        /// exactly what a well-behaved HTTP stack will not let you do.
        /// </summary>
        private sealed class HostileServer : IDisposable
        {
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
                        string.Join(",", _order.Select(h => "\"" + h + "\"")) + "]}";
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
                        Write(stream, reply.Status, reply.Bytes, "application/octet-stream",
                            reply.CutInHalf);
                        return;
                    }
                }

                Write(stream, 404, Array.Empty<byte>(), "text/plain", false);
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
