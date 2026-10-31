using System;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;
using YARG.Core.Logging;
using YARG.Helpers;
using YARG.Menu.Settings;

namespace YARG.Integration.SelfUpdate
{
    /// <summary>
    /// Whether a newer build of this fork exists, and fetching it if so.
    /// </summary>
    /// <remarks>
    /// Owns no scene object and is reached only from the settings menu, the same shape as
    /// <c>RemoteQueueServer</c> - the fork's diff to upstream stays small, which is the thing
    /// that keeps the rest of it a candidate for a PR.
    ///
    /// It does NOT apply the update. A running process on Windows cannot replace the files it
    /// is executing, so this downloads, verifies and unpacks to a staging folder and writes a
    /// marker; an external helper does the swap after the game exits. See ADR-006.
    ///
    /// Nothing here happens on startup. A check is a button, because an update is 600 MB and
    /// the person who just launched a rhythm game wants to play it.
    /// </remarks>
    public static class SelfUpdateStatus
    {
        private const int TIMEOUT_SECONDS = 10;

        /// <summary>Where the staged update and its marker live, under the persistent data path.</summary>
        private const string STAGING_FOLDER = "update-staging";
        private const string MARKER_FILE = "update-pending.json";
        private const string HELPER_SCRIPT = "yarg-update.ps1";

        public enum State
        {
            /// <summary>Never checked, or the URL changed since the last check.</summary>
            Unknown,
            /// <summary>No version file we recognise, so "newer" has no meaning. Feature is off.</summary>
            Unsupported,
            Checking,
            UpToDate,
            UpdateAvailable,
            Downloading,
            /// <summary>Downloaded, hash verified, unpacked and waiting for a restart.</summary>
            Staged,
            Failed,
        }

        public static State Current { get; private set; } = State.Unknown;
        public static string Error { get; private set; }
        public static UpdateManifest Available { get; private set; }

        private static BuildIdentity _self;
        private static bool _selfLoaded;
        private static long _downloaded;
        private static long _toDownload;
        private static bool _redrawing;
        private static float _lastProgressRedraw;

        /// <summary>
        /// Reuses the settings menu's "something changed, redraw" path, as SongServerStatus does.
        /// </summary>
        /// <remarks>
        /// Without this the buttons look broken. They were always doing the work - the row just
        /// never asked for its text again, so a check that took two seconds and a download that
        /// took two minutes both looked like a button that did nothing. Measured on MSI,
        /// 2026-10-31: "if I type it in the buttons do nothing".
        ///
        /// The guard matters because a redraw asks the row for its text and the row's text can
        /// ask for a redraw. Dropping the nested request makes that cycle impossible by
        /// construction rather than by the order things happen to run in.
        /// </remarks>
        private static void Redraw()
        {
            if (_redrawing)
            {
                return;
            }

            _redrawing = true;
            try
            {
                SettingsMenu.Instance?.OnSettingChanged();
            }
            finally
            {
                _redrawing = false;
            }
        }

        public static BuildIdentity Self
        {
            get
            {
                if (!_selfLoaded)
                {
                    _self = BuildIdentity.Load();
                    _selfLoaded = true;
                }

                return _self;
            }
        }

        /// <summary>Forgets the last verdict. A changed URL makes the previous answer meaningless.</summary>
        public static void Invalidate()
        {
            if (Current is State.Downloading)
            {
                return;
            }

            Current = State.Unknown;
            Available = null;
            Error = null;
            Redraw();
        }

        public static string Describe()
        {
            // Answered before the Unknown branch below, because Refresh() leaves the state at
            // Unknown when there is no URL - so without this the settings row would kick off a
            // fresh Refresh on every single redraw and never stop, while telling the person
            // nothing about why no update is being offered.
            if (string.IsNullOrWhiteSpace(Settings.SettingsManager.Settings.UpdateServerUrl.Value))
            {
                return $"This build: {Self}. No update server set.";
            }

            if (Current == State.Unknown)
            {
                // Lazy, exactly as SongServerStatus does: the row cannot be on screen without
                // this having been called, and it cannot be called where the answer is unwanted.
                Refresh().Forget();
                return $"This build: {Self}";
            }

            return Current switch
            {
                State.Unsupported => "This build has no version stamp, so it cannot be compared. "
                    + "Updates are unavailable.",
                State.Checking => $"This build: {Self} — checking...",
                State.UpToDate => $"Up to date ({Self}).",
                State.UpdateAvailable => $"Update available: {Available} "
                    + $"({FormatBytes(Available.Size)}). This build: {Self}.",
                State.Downloading => _toDownload > 0
                    ? $"{Bar(_downloaded, _toDownload)}{_downloaded * 100 / _toDownload}%  "
                        + $"{FormatBytes(_downloaded)} of {FormatBytes(_toDownload)}"
                    : $"Downloading... {FormatBytes(_downloaded)} so far",
                State.Staged => $"Update {Available} is ready — restart to apply it.",
                State.Failed => $"Update check failed: {Error}",
                _ => $"This build: {Self}",
            };
        }

        public static async UniTask Refresh(string urlOverride = null)
        {
            string url = urlOverride ?? Settings.SettingsManager.Settings.UpdateServerUrl.Value;

            if (!Self.IsKnown)
            {
                Current = State.Unsupported;
                return;
            }

            if (string.IsNullOrWhiteSpace(url))
            {
                Current = State.Unknown;
                return;
            }

            if (Current is State.Checking or State.Downloading)
            {
                return;
            }

            Current = State.Checking;
            Redraw();   // so the row says "checking..." the instant the button is pressed

            try
            {
                using var request = UnityWebRequest.Get(url.Trim());
                request.SetRequestHeader("User-Agent", "YARG");
                request.timeout = TIMEOUT_SECONDS;

                await request.SendWebRequest().WithCancellation(CancellationToken.None);

                if (request.result != UnityWebRequest.Result.Success)
                {
                    throw new Exception(request.error);
                }

                if (!UpdateManifest.TryParse(request.downloadHandler.text, out var manifest, out string why))
                {
                    throw new Exception(why);
                }

                Available = manifest;
                Error = null;
                Current = manifest.IsNewerThan(Self) ? State.UpdateAvailable : State.UpToDate;
                YargLogger.LogFormatInfo("Self-update: this build {0}, server offers {1} -> {2}",
                    Self, manifest, Current);
            }
            catch (Exception e)
            {
                Error = e.Message;
                Current = State.Failed;
                YargLogger.LogFormatWarning("Self-update check failed: {0}", e.Message);
            }

            Redraw();
        }

        /// <summary>
        /// Downloads the offered build, verifies its hash, and unpacks it ready for a restart.
        /// </summary>
        /// <remarks>
        /// The hash is checked BEFORE a single entry is unpacked. Unpacking first and checking
        /// afterwards would mean a corrupt or hostile archive had already written itself across
        /// the staging folder by the time we knew.
        /// </remarks>
        public static async UniTask Download()
        {
            if (Current != State.UpdateAvailable || Available == null)
            {
                return;
            }

            var manifest = Available;
            string staging = Path.Combine(PathHelper.PersistentDataPath, STAGING_FOLDER);
            string zipPath = Path.Combine(staging, $"update-b{manifest.Build}.zip");
            string unpacked = Path.Combine(staging, $"b{manifest.Build}");

            Current = State.Downloading;
            _downloaded = 0;
            _toDownload = manifest.Size;
            _lastProgressRedraw = 0f;
            Redraw();

            try
            {
                if (Directory.Exists(staging))
                {
                    Directory.Delete(staging, true);
                }
                Directory.CreateDirectory(staging);

                using (var request = UnityWebRequest.Get(manifest.Url))
                {
                    // Streamed to disk: a whole build is hundreds of megabytes and must never
                    // be held in memory to be hashed.
                    request.downloadHandler = new DownloadHandlerFile(zipPath);
                    request.SetRequestHeader("User-Agent", "YARG");

                    var operation = request.SendWebRequest();
                    while (!operation.isDone)
                    {
                        _downloaded = (long) request.downloadedBytes;

                        // Four times a second, not every frame. A redraw rebuilds the settings
                        // tab, and doing that at 60fps for the length of a 160 MB download
                        // would make the menu the expensive part of downloading.
                        if (Time.realtimeSinceStartup - _lastProgressRedraw > 0.25f)
                        {
                            _lastProgressRedraw = Time.realtimeSinceStartup;
                            Redraw();
                        }

                        await UniTask.Yield();
                    }

                    if (request.result != UnityWebRequest.Result.Success)
                    {
                        throw new Exception(request.error);
                    }
                }

                _downloaded = new FileInfo(zipPath).Length;

                string actual = Sha256OfFile(zipPath);
                if (!string.Equals(actual, manifest.Sha256, StringComparison.Ordinal))
                {
                    throw new Exception(
                        $"hash mismatch: manifest says {Short(manifest.Sha256)}, download is {Short(actual)}");
                }

                Extract(zipPath, unpacked);
                File.Delete(zipPath);

                string marker = WriteMarker(manifest, unpacked);
                ArmHelper(marker);

                Current = State.Staged;
                Error = null;
                // LogInfo, not LogFormatInfo: YargLogger's caller-info parameters are optional,
                // so a two-argument format call whose last argument is a string is ambiguous
                // with the one-argument overload. Existing two-argument calls only compile
                // because their last argument happens not to be a string.
                YargLogger.LogInfo($"Self-update: staged {manifest} at {unpacked}");
            }
            catch (Exception e)
            {
                Error = e.Message;
                Current = State.Failed;
                YargLogger.LogFormatWarning("Self-update download failed: {0}", e.Message);
            }

            Redraw();
        }

        /// <summary>
        /// A text progress bar, because the settings row is a line of text.
        /// </summary>
        private static string Bar(long done, long total, int width = 24)
        {
            if (total <= 0)
            {
                return string.Empty;
            }

            int filled = (int) Math.Round(width * Math.Clamp(done / (double) total, 0, 1));
            return "[" + new string('#', filled) + new string('-', width - filled) + "] ";
        }

        private static string Sha256OfFile(string path)
        {
            using var stream = File.OpenRead(path);
            using var sha = SHA256.Create();
            byte[] hash = sha.ComputeHash(stream);
            return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
        }

        /// <summary>
        /// Unpacks the archive, refusing any entry that would escape the destination.
        /// </summary>
        /// <remarks>
        /// ZipArchive rather than ZipFile.ExtractToDirectory, so the destination of every entry
        /// is checked here. An archive entry named <c>..\..\Windows\System32\...</c> is a file
        /// write anywhere the game can reach, and an updater is exactly the thing an attacker
        /// would aim that at. The server side of this project already learned that archives lie
        /// about their contents - see yarg-song-server's hostile-archive tests.
        /// </remarks>
        private static void Extract(string zipPath, string destination)
        {
            Directory.CreateDirectory(destination);
            string root = Path.GetFullPath(destination);
            if (!root.EndsWith(Path.DirectorySeparatorChar))
            {
                root += Path.DirectorySeparatorChar;
            }

            using var archive = ZipFile.OpenRead(zipPath);
            foreach (var entry in archive.Entries)
            {
                // A directory entry has an empty name; it is created implicitly below.
                if (string.IsNullOrEmpty(entry.Name))
                {
                    continue;
                }

                string target = Path.GetFullPath(Path.Combine(destination, entry.FullName));
                if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                {
                    throw new Exception($"archive entry escapes the staging folder: {entry.FullName}");
                }

                Directory.CreateDirectory(Path.GetDirectoryName(target));
                entry.ExtractToFile(target, true);
            }
        }

        /// <summary>
        /// Arranges for the helper to run once this process has exited.
        /// </summary>
        /// <remarks>
        /// The helper is COPIED OUT of the install folder first. It ships in StreamingAssets,
        /// which lives inside the folder about to be replaced - running it from there would be
        /// moving the ground it stands on, and the script's own directory is enough to keep a
        /// handle open on a folder Windows then refuses to rename.
        ///
        /// Hooked to <see cref="Application.quitting"/> rather than started immediately, so a
        /// staged update that the player never restarts into costs nothing and changes nothing.
        /// </remarks>
        private static void ArmHelper(string marker)
        {
            _markerForHelper = marker;
            Application.quitting -= LaunchHelper;
            Application.quitting += LaunchHelper;
        }

        private static string _markerForHelper;

        private static void LaunchHelper()
        {
            if (string.IsNullOrEmpty(_markerForHelper) || !File.Exists(_markerForHelper))
            {
                return;
            }

            try
            {
                string source = Path.Combine(PathHelper.StreamingAssetsPath, "update", HELPER_SCRIPT);
                if (!File.Exists(source))
                {
                    YargLogger.LogWarning("Self-update: helper script is missing; not applying");
                    return;
                }

                string runnable = Path.Combine(PathHelper.PersistentDataPath, HELPER_SCRIPT);
                File.Copy(source, runnable, true);

                int pid = System.Diagnostics.Process.GetCurrentProcess().Id;
                var start = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = $"-NoProfile -ExecutionPolicy Bypass -File \"{runnable}\" " +
                        $"-GamePid {pid} -Marker \"{_markerForHelper}\"",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                };
                System.Diagnostics.Process.Start(start);
                YargLogger.LogInfo("Self-update: helper launched; it waits for this process to exit");
            }
            catch (Exception e)
            {
                // Never let this stop the game closing. A failed hand-off leaves the staged
                // build on disk and the install untouched, which is the safe end of the trade.
                YargLogger.LogWarning("Self-update: could not launch the helper: " + e.Message);
            }
        }

        /// <summary>
        /// Tells the external helper what to swap in. The game cannot do this itself.
        /// </summary>
        private static string WriteMarker(UpdateManifest manifest, string unpacked)
        {
            string install = PathHelper.ExecutablePath;
            string marker = Path.Combine(PathHelper.PersistentDataPath, MARKER_FILE);
            string json =
                "{\n" +
                $"  \"build\": {manifest.Build},\n" +
                $"  \"branch\": {Quote(manifest.Branch)},\n" +
                $"  \"commit\": {Quote(manifest.Commit)},\n" +
                $"  \"staged\": {Quote(unpacked)},\n" +
                $"  \"install\": {Quote(install)}\n" +
                "}\n";
            File.WriteAllText(marker, json);
            return marker;
        }

        private static string Quote(string s)
        {
            return "\"" + (s ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
        }

        private static string Short(string hash)
        {
            return string.IsNullOrEmpty(hash) || hash.Length < 12 ? hash : hash.Substring(0, 12);
        }

        private static string FormatBytes(long bytes)
        {
            if (bytes <= 0)
            {
                return "unknown size";
            }

            string[] units = { "B", "KB", "MB", "GB" };
            double value = bytes;
            int unit = 0;
            while (value >= 1024 && unit < units.Length - 1)
            {
                value /= 1024;
                unit++;
            }

            return $"{value:0.#} {units[unit]}";
        }
    }
}
