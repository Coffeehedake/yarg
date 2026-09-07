using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine.Networking;
using YARG.Core.IO;
using YARG.Core.Logging;
using YARG.Core.Song;

namespace YARG.Song.RemoteLibrary
{
    /// <summary>
    /// Mirrors a yarg-song-server's library into a folder this game manages, so the
    /// ordinary song scanner can pick it up like any other folder.
    /// </summary>
    /// <remarks>
    /// This deliberately adds NO new concept to the song pipeline. YARG already appends a
    /// folder the player never chose - <see cref="Helpers.PathHelper.SetlistPath"/>, filled
    /// out of band by the YARC Launcher - to the scan list. This is a second producer for
    /// that same shape of folder, which is why nothing downstream of the scan needs to know
    /// a server exists.
    ///
    /// The server hands out plain .sng files that unmodified YARG already reads, so there is
    /// no protocol here beyond "list, fetch, verify".
    /// </remarks>
    public static class SongServerSync
    {
        /// <summary>
        /// Files this mirror considers its own: exactly "&lt;40 hex&gt;.sng".
        /// </summary>
        /// <remarks>
        /// Everything else in the folder belongs to the player and is never counted, never
        /// overwritten and never deleted. A sync tool that eats songs somebody put there by
        /// hand is worse than no sync tool, and the name is the whole guarantee - a file
        /// named for its own chart hash cannot collide with anything a person would type.
        /// </remarks>
        private static readonly Regex ManagedName = new(@"^[0-9a-f]{40}\.sng$", RegexOptions.Compiled);

        /// <summary>
        /// Chart filenames, in the order YARG resolves them. First match wins HARD - a song
        /// holding both notes.mid and notes.chart is a notes.mid song, and the loser is not
        /// consulted.
        /// </summary>
        private static readonly string[] ChartFileNames =
        {
            "notes.mid", "notes.midi", "notes.chart", "notes.txt"
        };

        /// <summary>
        /// HTTP 300. Not an error here: it is the server declining to pick between packages
        /// that share a chart hash, which is the client's decision to make.
        /// </summary>
        private const int MULTIPLE_CHOICES = 300;

        private const int LIST_TIMEOUT_SECONDS = 30;

        /// <summary>
        /// How long the startup sync waits to find out whether the server is even there.
        /// </summary>
        /// <remarks>
        /// Short on purpose, and it answers a different question from how long a download
        /// may take. A server that is off - the Pi unplugged, the laptop off the LAN - is
        /// an ordinary case rather than an exceptional one, and every launch would
        /// otherwise sit on a frozen loading screen for the full 30 s before the game
        /// started. Downloads stay unbounded once something is known to be listening.
        /// </remarks>
        public const int STARTUP_REACHABILITY_TIMEOUT_SECONDS = 5;
        private const int SONG_TIMEOUT_SECONDS = 600;

        public sealed class Result
        {
            /// <summary>Managed songs already present before this run.</summary>
            public int AlreadyHad;
            /// <summary>Files in the folder that are NOT ours, and were left alone.</summary>
            public int Unmanaged;
            /// <summary>How many songs the server says it has.</summary>
            public int ServerTotal;
            public readonly List<string> Downloaded = new();
            /// <summary>Songs that could not be fetched, and why. One failure never abandons the run.</summary>
            public readonly List<(string ChartHash, string Reason)> Failures = new();
            public long BytesFetched;

            public override string ToString()
            {
                return $"server={ServerTotal} had={AlreadyHad} downloaded={Downloaded.Count} " +
                    $"failed={Failures.Count} unmanaged={Unmanaged} bytes={BytesFetched}";
            }
        }

        /// <summary>
        /// Brings <paramref name="destination"/> in line with the server at
        /// <paramref name="serverUrl"/>. Idempotent: a second run downloads nothing.
        /// </summary>
        /// <remarks>
        /// This NEVER deletes. The server-side client has an opt-in prune; deciding what to
        /// do about a song the server no longer offers is a separate question from getting
        /// the songs it does, and answering it wrong costs somebody their library.
        /// </remarks>
        public static async UniTask<Result> Sync(string serverUrl, string destination,
            LoadingContext context = null, CancellationToken token = default,
            int listTimeoutSeconds = LIST_TIMEOUT_SECONDS)
        {
            if (string.IsNullOrWhiteSpace(serverUrl))
            {
                throw new ArgumentException("No song server URL configured.", nameof(serverUrl));
            }

            string root = serverUrl.Trim().TrimEnd('/');
            Directory.CreateDirectory(destination);

            var result = new Result();
            var have = Inventory(destination, result);

            context?.SetLoadingText("Asking the song server what is missing...");
            var missing = await AskWhatIsMissing(root, have, result, token, listTimeoutSeconds);

            for (int i = 0; i < missing.Count; i++)
            {
                token.ThrowIfCancellationRequested();

                string hash = missing[i];
                context?.SetSubText($"Downloading song {i + 1} of {missing.Count}");

                try
                {
                    result.BytesFetched += await FetchOne(root, hash, destination, token);
                    result.Downloaded.Add(hash);
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception e)
                {
                    // Collected, not thrown: one unreachable song must not abandon a sync
                    // of ten thousand.
                    YargLogger.LogWarning($"Could not sync song {hash}: {e.Message}");
                    result.Failures.Add((hash, e.Message));
                }
            }

            YargLogger.LogInfo($"Song server sync finished: {result}");
            return result;
        }

        /// <summary>
        /// Reads what is already here from the directory listing alone.
        /// </summary>
        /// <remarks>
        /// Deliberately not a state file. "What do I already have?" must be answerable
        /// without opening ten thousand archives, and a state file is one more thing that
        /// can disagree with the folder it claims to describe.
        /// </remarks>
        private static List<string> Inventory(string destination, Result result)
        {
            var have = new List<string>();
            foreach (string path in Directory.EnumerateFileSystemEntries(destination))
            {
                string name = Path.GetFileName(path);
                if (ManagedName.IsMatch(name))
                {
                    have.Add(Path.GetFileNameWithoutExtension(name));
                    continue;
                }

                // A leftover .part is ours but incomplete: neither inventory nor a
                // stranger's file, so it is counted as neither.
                if (!name.EndsWith(".part", StringComparison.Ordinal))
                {
                    result.Unmanaged++;
                }
            }

            have.Sort(StringComparer.Ordinal);
            result.AlreadyHad = have.Count;
            return have;
        }

        /// <summary>
        /// One round trip, whatever the size of either side: we send what we hold, the
        /// server answers with everything we do not.
        /// </summary>
        private static async UniTask<List<string>> AskWhatIsMissing(string root, List<string> have,
            Result result, CancellationToken token, int timeoutSeconds)
        {
            string body = JsonConvert.SerializeObject(new { chart_hashes = have });

            using var request = new UnityWebRequest($"{root}/api/v1/have", UnityWebRequest.kHttpVerbPOST);
            request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");
            request.SetRequestHeader("User-Agent", "YARG");
            request.timeout = timeoutSeconds;

            await request.SendWebRequest().WithCancellation(token);

            if (request.result != UnityWebRequest.Result.Success)
            {
                throw new Exception($"Song server did not answer /api/v1/have: {request.error}");
            }

            var json = JObject.Parse(request.downloadHandler.text);
            result.ServerTotal = json.Value<int>("library_total");

            var missing = new List<string>();
            foreach (var entry in json.Value<JArray>("missing") ?? new JArray())
            {
                missing.Add(entry.ToString());
            }
            return missing;
        }

        /// <summary>
        /// Downloads one song to a .part file, verifies it, and only then gives it its real
        /// name. A crash or a dropped link mid-download therefore cannot leave a truncated
        /// archive under a name the scanner will trust.
        /// </summary>
        private static async UniTask<long> FetchOne(string root, string hash, string destination,
            CancellationToken token)
        {
            string part = Path.Combine(destination, hash + ".sng.part");
            string final = Path.Combine(destination, hash + ".sng");
            bool multipleChoices = false;

            try
            {
                using (var request = new UnityWebRequest($"{root}/song/{hash}.sng", UnityWebRequest.kHttpVerbGET))
                {
                    request.downloadHandler = new DownloadHandlerFile(part);
                    request.SetRequestHeader("User-Agent", "YARG");
                    request.timeout = SONG_TIMEOUT_SECONDS;

                    await request.SendWebRequest().WithCancellation(token);

                    if (request.responseCode == MULTIPLE_CHOICES)
                    {
                        multipleChoices = true;
                    }
                    else if (request.result != UnityWebRequest.Result.Success)
                    {
                        throw new Exception($"download failed: {request.error}");
                    }
                }

                if (multipleChoices)
                {
                    // The server will not choose between packages that share this chart
                    // hash, because choosing would hand different clients different audio
                    // for the same request. So the client chooses, and does it the same way
                    // every time - see ChoosePackage.
                    //
                    // The first request wrote the 300's JSON body into the .part file rather
                    // than a song, so it is discarded and the choices are asked for again
                    // with a handler that can hold them. Three requests in a case that is
                    // rare, one in the case that is not.
                    File.Delete(part);
                    string package = await ChoosePackage(root, hash, token);

                    using var retry = new UnityWebRequest(
                        $"{root}/song/{hash}.sng?package={package}", UnityWebRequest.kHttpVerbGET);
                    retry.downloadHandler = new DownloadHandlerFile(part);
                    retry.SetRequestHeader("User-Agent", "YARG");
                    retry.timeout = SONG_TIMEOUT_SECONDS;

                    await retry.SendWebRequest().WithCancellation(token);

                    if (retry.result != UnityWebRequest.Result.Success)
                    {
                        throw new Exception($"download failed after choosing package {package}: {retry.error}");
                    }
                }

                VerifyChartHash(part, hash);

                // File.Move overwrites nothing by default; a concurrent run that already
                // finished this song wins and we discard our copy rather than fighting it.
                if (File.Exists(final))
                {
                    File.Delete(part);
                    return 0;
                }

                var length = new FileInfo(part).Length;
                File.Move(part, final);
                return length;
            }
            catch
            {
                if (File.Exists(part))
                {
                    File.Delete(part);
                }
                throw;
            }
        }

        /// <summary>
        /// Picks one of the packages sharing a chart hash - the same one, every time.
        /// </summary>
        /// <remarks>
        /// The smallest package hash, ordinally. The rule itself does not matter; that it is
        /// TOTAL and DETERMINISTIC does. Two players syncing the same library must end up
        /// with the same audio, and a client that picked "the first one the server listed"
        /// would be at the mercy of map ordering on the far side.
        ///
        /// This matches yarg-sync, deliberately: the two clients choosing differently would
        /// be a difference nobody would think to look for until two people compared scores
        /// on what they believed was the same song.
        /// </remarks>
        private static async UniTask<string> ChoosePackage(string root, string hash, CancellationToken token)
        {
            using var request = UnityWebRequest.Get($"{root}/song/{hash}.sng");
            request.SetRequestHeader("User-Agent", "YARG");
            request.timeout = LIST_TIMEOUT_SECONDS;

            await request.SendWebRequest().WithCancellation(token);

            if (request.responseCode != MULTIPLE_CHOICES)
            {
                throw new Exception(
                    $"expected 300 listing the packages, got {request.responseCode}");
            }

            var packages = JObject.Parse(request.downloadHandler.text).Value<JArray>("packages");
            if (packages == null || packages.Count == 0)
            {
                throw new Exception("server reported several packages but listed none");
            }

            string best = null;
            foreach (var package in packages)
            {
                string candidate = package.Value<string>("package_hash");
                if (candidate == null)
                {
                    continue;
                }
                if (best == null || string.CompareOrdinal(candidate, best) < 0)
                {
                    best = candidate;
                }
            }

            if (best == null)
            {
                throw new Exception("server listed packages with no package_hash");
            }
            return best;
        }

        /// <summary>
        /// Checks the archive really contains the chart it is named after.
        /// </summary>
        /// <remarks>
        /// Naming files by chart hash is only worth anything if somebody checks. The hash is
        /// SHA-1 over the chart file's bytes, which is exactly what the scanner computes when
        /// it indexes a song, so a file that passes here is a file the scanner will agree
        /// with. It catches a truncated download, a proxy that served something else, and a
        /// server that is not the server we think it is.
        ///
        /// It does NOT verify the audio: the chart is what identity is defined over, and a
        /// package differing only in album art is deliberately the same song.
        /// </remarks>
        private static void VerifyChartHash(string path, string expected)
        {
            using var sng = SngFile.TryLoadFromFile(path, false);
            if (!sng.IsLoaded)
            {
                throw new Exception("downloaded file is not a readable .sng");
            }

            foreach (string chartName in ChartFileNames)
            {
                if (!sng.TryGetListing(chartName, out var listing))
                {
                    continue;
                }

                using var data = sng.LoadAllBytes(in listing);
                string actual = HashWrapper.Hash(data.ReadOnlySpan).ToString();
                if (!string.Equals(actual, expected, StringComparison.OrdinalIgnoreCase))
                {
                    throw new Exception($"chart hash mismatch: expected {expected}, got {actual}");
                }
                return;
            }

            throw new Exception("downloaded .sng contains no chart file");
        }
    }
}
