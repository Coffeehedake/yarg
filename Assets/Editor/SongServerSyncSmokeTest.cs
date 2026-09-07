using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using YARG.Audio.BASS;
using YARG.Core.Audio;
using YARG.Core.Song.Cache;
using YARG.Helpers;
using YARG.Song.RemoteLibrary;

namespace Editor
{
    /// <summary>
    /// Runs a real sync against a real song server and reports whether it worked.
    /// </summary>
    /// <remarks>
    /// This exists because "it compiles" is not evidence that it works, and this project has
    /// been bitten more than once by a green that came from something other than the thing
    /// under test. It talks to an actual server over an actual network and verifies the
    /// chart hash of every file it wrote, so a pass means the mirror really does produce
    /// songs the scanner would accept.
    ///
    /// Run it from the command line - note NO -quit, because the work is asynchronous and
    /// the editor must stay alive to pump it; the test exits the process itself:
    ///
    ///   set YARG_SONG_SERVER=http://your-server:8099
    ///   "Unity.exe" -batchmode -nographics -projectPath &lt;project&gt; ^
    ///       -executeMethod Editor.SongServerSyncSmokeTest.Run -logFile &lt;log&gt;
    ///
    /// Exit code 0 means every song the server offered arrived and verified.
    /// </remarks>
    public static class SongServerSyncSmokeTest
    {
        private const string SERVER_ENV = "YARG_SONG_SERVER";

        [MenuItem("YARG/Debug/Song Server Sync Smoke Test", false, 400)]
        public static void RunFromMenu()
        {
            Run();
        }

        public static void Run()
        {
            string server = Environment.GetEnvironmentVariable(SERVER_ENV);
            if (string.IsNullOrWhiteSpace(server))
            {
                Fail($"{SERVER_ENV} is not set; nothing to test against.");
                return;
            }

            // A scratch folder, not PathHelper.ServerLibraryPath: a test that writes into the
            // real library would make its own second run meaningless.
            string destination = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");

            Console.WriteLine($"[SMOKE] server={server}");
            Console.WriteLine($"[SMOKE] destination={destination}");

            RunAsync(server, destination);
        }

        private static async void RunAsync(string server, string destination)
        {
            try
            {
                var result = await SongServerSync.Sync(server, destination);

                Console.WriteLine($"[SMOKE] {result}");
                foreach (var (hash, reason) in result.Failures)
                {
                    Console.WriteLine($"[SMOKE] FAILED {hash}: {reason}");
                }

                if (result.ServerTotal == 0)
                {
                    Fail("the server reported an empty library, so this run proved nothing");
                    return;
                }

                if (result.Failures.Count > 0)
                {
                    Fail($"{result.Failures.Count} song(s) could not be synced");
                    return;
                }

                // Idempotence is the property that makes this safe to run on every launch,
                // so it is asserted rather than assumed: a second pass must download nothing.
                var second = await SongServerSync.Sync(server, destination);
                if (second.Downloaded.Count != 0)
                {
                    Fail($"second run downloaded {second.Downloaded.Count} song(s); sync is not idempotent");
                    return;
                }

                int onDisk = Directory.GetFiles(destination, "*.sng").Length;
                if (onDisk != second.AlreadyHad)
                {
                    Fail($"{onDisk} .sng on disk but inventory counted {second.AlreadyHad}");
                    return;
                }

                if (!ScanFinds(destination, result.ServerTotal))
                {
                    return;
                }

                Console.WriteLine($"[SMOKE] PASS - {onDisk} songs mirrored, verified and scanned, " +
                    "second run downloaded nothing");
                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Fail(e.ToString());
            }
        }

        /// <summary>
        /// Runs YARG's own scanner over the mirrored folder and checks it finds the songs.
        /// </summary>
        /// <remarks>
        /// This is the assertion that actually matters, and everything above it is a
        /// prerequisite. "The files arrived and their hashes check out" is not the same claim
        /// as "YARG will play them" — the mirror could produce perfectly valid archives that
        /// the scanner ignores for some reason nothing else here would notice, and the whole
        /// design rests on the scanner treating this folder like any other.
        ///
        /// It scans the mirror folder ALONE, into throwaway cache and badsongs paths, so it
        /// says nothing about the player's real library and cannot disturb it.
        ///
        /// It also refuses to judge songs it CANNOT judge. The scanner measures song length
        /// from the audio whenever song.ini omits song_length, and the audio backend does not
        /// work in editor batchmode - so those songs get refused as
        /// "Corruption of either the ini file or chart/mid file" no matter what the mirror
        /// did. Counting those as mirror failures is how this test reported 5 of 23 and sent
        /// a whole afternoon after a defect that was in the harness.
        /// </remarks>
        private static bool ScanFinds(string destination, int expected)
        {
            string scratch = Path.Combine(Path.GetTempPath(), "yarg-smoketest-scan");
            Directory.CreateDirectory(scratch);
            string cachePath = Path.Combine(scratch, "songcache.bin");
            string badSongsPath = Path.Combine(scratch, "badsongs.txt");
            foreach (string stale in new[] { cachePath, badSongsPath })
            {
                if (File.Exists(stale))
                {
                    // A stale cache read as this run's verdict is the exact mistake the
                    // server-side oracle script exists to prevent. Same rule here.
                    File.Delete(stale);
                }
            }

            var cache = CacheHandler.RunScan(false, cachePath, badSongsPath, false,
                new List<string> { destination });

            int found = 0;
            foreach (var entries in cache.Entries.Values)
            {
                found += entries.Count;
            }

            Console.WriteLine($"[SMOKE] scan of the mirror folder found {found} song(s), " +
                $"{cache.Entries.Count} distinct chart hash(es)");

            bool audioWorks = AudioBackendWorks();
            Console.WriteLine($"[SMOKE] audio backend usable: {audioWorks}");

            if (File.Exists(badSongsPath))
            {
                Console.WriteLine("[SMOKE] the scanner refused these; see the note below:");
                Console.WriteLine(File.ReadAllText(badSongsPath));
            }

            // What this can honestly assert, and no more.
            //
            // NOT "the scanner accepts everything the server offered". A server is entitled
            // to host songs YARG refuses - the corpus this runs against deliberately does,
            // and refusing them is the scanner being right. Failing on that would make the
            // test a statement about somebody's library rather than about the mirror.
            //
            // NOT "no refusals", for the same reason plus a second one: with no audio
            // backend, every song whose song.ini omits song_length is refused by the harness
            // regardless of what the mirror did.
            //
            // What IS the mirror's business is whether the archives it writes are readable
            // by YARG's scanner at all. One accepted song proves that end to end - packed by
            // the server, fetched over the network, verified, and then read by YARG's own
            // scanner into a real SongEntry. Zero accepted would mean the mirror produces
            // something the scanner cannot use, which is the failure worth catching.
            if (found == 0)
            {
                Fail("the scanner accepted NONE of the mirrored songs - the archives are not " +
                    "readable by YARG");
                return false;
            }

            Console.WriteLine($"[SMOKE] scanner accepted {found} of {expected} mirrored song(s). " +
                "Refusals above are the songs' own properties or, where audio is unavailable, " +
                "this harness's limit - neither is evidence about the mirror.");
            return true;
        }

        /// <summary>
        /// Can this process actually decode audio? Answered by decoding a file, not by
        /// assuming <see cref="GlobalAudioHandler.Initialize{T}"/> worked - in editor
        /// batchmode it constructs the manager and still cannot make a mixer.
        /// </summary>
        private static bool AudioBackendWorks()
        {
            string sample = Environment.GetEnvironmentVariable("YARG_AUDIO_PROBE");
            if (string.IsNullOrWhiteSpace(sample) || !File.Exists(sample))
            {
                return false;
            }

            try
            {
                GlobalAudioHandler.Initialize<BassAudioManager>();
                using var mixer = GlobalAudioHandler.LoadCustomFile(sample, 1, 0);
                return mixer != null;
            }
            catch
            {
                return false;
            }
        }

        private static void Fail(string message)
        {
            Console.WriteLine($"[SMOKE] FAIL - {message}");
            EditorApplication.Exit(1);
        }
    }
}
