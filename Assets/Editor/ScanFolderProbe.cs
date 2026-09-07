using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using YARG.Audio.BASS;
using YARG.Core.Audio;
using YARG.Core.Song.Cache;

namespace Editor
{
    /// <summary>
    /// Scans one folder with YARG's own scanner and prints the verdict for every song.
    /// </summary>
    /// <remarks>
    /// A control, not a feature. When the song-server mirror's smoke test found the scanner
    /// rejecting songs, the obvious conclusion - "the mirror produces archives YARG will not
    /// take" - had an equally plausible rival: the corpus is synthetic, its audio is
    /// zero-filled, and the same songs might be rejected as loose folders too. Those two
    /// have completely different fixes, and nothing measured so far could tell them apart.
    ///
    /// So this runs the identical scanner over the identical songs in their ORIGINAL form.
    /// Whatever it says, the comparison is what makes either claim honest.
    ///
    ///   set YARG_SCAN_FOLDER=C:\some\library
    ///   "Unity.exe" -batchmode -nographics -projectPath &lt;project&gt; ^
    ///       -executeMethod Editor.ScanFolderProbe.Run -logFile &lt;log&gt;
    /// </remarks>
    public static class ScanFolderProbe
    {
        public static void Run()
        {
            try
            {
                string folder = Environment.GetEnvironmentVariable("YARG_SCAN_FOLDER");
                if (string.IsNullOrWhiteSpace(folder) || !Directory.Exists(folder))
                {
                    Console.WriteLine($"[SCAN] FAIL - YARG_SCAN_FOLDER not set or missing: {folder}");
                    EditorApplication.Exit(1);
                    return;
                }

                // Stand the audio backend up before scanning, or the scan lies.
                //
                // A song whose song.ini has no song_length makes the scanner measure the
                // length from the audio (SongEntry.IniBase.cs:286), which needs
                // GlobalAudioHandler. In the running game that is initialised by
                // GlobalVariables; from a static editor method it is not, so LoadAudio
                // throws and the song is refused as "Corruption of either the ini file or
                // chart/mid file" - a message that names neither the real cause nor the real
                // file.
                //
                // Without this line the probe measures ITSELF, not YARG, and it does it
                // convincingly: it refuses real songs with a plausible reason. That cost a
                // wrong conclusion published in three commits before the mechanism was
                // actually read.
                GlobalAudioHandler.Initialize<BassAudioManager>();

                // Prove the backend actually came up, rather than assuming Initialize
                // worked. YARG_AUDIO_PROBE names a real audio file; if a mixer cannot be
                // made from it, this probe cannot measure song length and any refusal it
                // reports for a song lacking song_length says nothing about YARG.
                bool audioWorks = AudioBackendWorks();

                string scratch = Path.Combine(Path.GetTempPath(), "yarg-scanprobe");
                Directory.CreateDirectory(scratch);
                string cachePath = Path.Combine(scratch, "songcache.bin");
                string badSongsPath = Path.Combine(scratch, "badsongs.txt");
                foreach (string stale in new[] { cachePath, badSongsPath })
                {
                    if (File.Exists(stale))
                    {
                        File.Delete(stale);
                    }
                }

                var cache = CacheHandler.RunScan(false, cachePath, badSongsPath, false,
                    new List<string> { folder });

                int found = 0;
                foreach (var entries in cache.Entries.Values)
                {
                    found += entries.Count;
                }

                Console.WriteLine($"[SCAN] folder={folder}");
                Console.WriteLine($"[SCAN] accepted={found} distinctHashes={cache.Entries.Count}");
                if (File.Exists(badSongsPath))
                {
                    Console.WriteLine("[SCAN] badsongs.txt:");
                    Console.WriteLine(File.ReadAllText(badSongsPath));
                }
                else
                {
                    Console.WriteLine("[SCAN] no badsongs.txt - nothing was refused");
                }

                if (!audioWorks)
                {
                    // Exit 2 = INCONCLUSIVE, not failure. Without a working backend this
                    // probe cannot judge any song whose song.ini omits song_length, and
                    // printing a number anyway is how a harness artefact gets written up as
                    // a finding about YARG. That already happened once, on 2026-09-07.
                    Console.WriteLine("[SCAN] INCONCLUSIVE - no usable audio backend, so any song " +
                        "whose song.ini omits song_length was refused BY THIS HARNESS and not " +
                        "necessarily by YARG. Only songs that declare song_length were tested.");
                    EditorApplication.Exit(2);
                    return;
                }

                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Console.WriteLine($"[SCAN] FAIL - {e}");
                EditorApplication.Exit(1);
            }
        }

        /// <summary>
        /// Can this process actually decode audio? Answered by decoding something, not by
        /// checking that Initialize was called.
        /// </summary>
        /// <remarks>
        /// <see cref="GlobalAudioHandler.Initialize{T}"/> constructs the manager and reports
        /// nothing about whether it works. In editor batchmode it does NOT: making a mixer
        /// from a real 3 MB ogg throws a NullReferenceException, even straight after
        /// Initialize.
        ///
        /// This matters more than it looks. The scanner measures song length from the audio
        /// whenever song.ini omits song_length (SongEntry.IniBase.cs:286), so with no backend
        /// every such song is refused as "Corruption of either the ini file or chart/mid
        /// file" - a message naming neither the real cause nor the real file, and entirely
        /// convincing until somebody checks. It produced a confident, wrong, published
        /// conclusion that YARG dev had changed behaviour relative to the release build.
        /// </remarks>
        private static bool AudioBackendWorks()
        {
            string sample = Environment.GetEnvironmentVariable("YARG_AUDIO_PROBE");
            if (string.IsNullOrWhiteSpace(sample) || !File.Exists(sample))
            {
                Console.WriteLine("[SCAN] YARG_AUDIO_PROBE is not set to a real audio file, so the " +
                    "backend is treated as unusable - assuming the other way is what produced a " +
                    "wrong finding.");
                return false;
            }

            try
            {
                using var mixer = GlobalAudioHandler.LoadCustomFile(sample, 1, 0);
                if (mixer == null)
                {
                    Console.WriteLine("[SCAN] audio backend unusable - LoadCustomFile returned null");
                    return false;
                }
                Console.WriteLine($"[SCAN] audio backend usable - decoded {Path.GetFileName(sample)}, {mixer.Length:F1}s");
                return true;
            }
            catch (Exception e)
            {
                Console.WriteLine($"[SCAN] audio backend unusable - {e.GetType().Name}: {e.Message}");
                return false;
            }
        }
    }
}
