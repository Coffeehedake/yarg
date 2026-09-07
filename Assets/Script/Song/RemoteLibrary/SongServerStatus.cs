using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEngine.Networking;
using YARG.Core.Logging;
using YARG.Menu.Settings;
using YARG.Settings;

namespace YARG.Song.RemoteLibrary
{
    /// <summary>
    /// What the configured song server currently looks like, for display in the settings menu.
    /// </summary>
    /// <remarks>
    /// This exists because the only way to find out whether a server URL worked used to be to
    /// press Sync and read an error dialog. A typo, a sleeping NAS and a server that is fine
    /// were indistinguishable until you committed to a sync.
    ///
    /// It deliberately reports the SERVER's own health as well as reachability. The server
    /// already knows which directories it could not read and says so in
    /// <c>/api/v1/library</c>; a library that quietly indexes 9,000 of 10,000 songs looks
    /// exactly like a library that has 9,000 songs, and the person who can fix that is the
    /// one standing in front of the game.
    /// </remarks>
    public static class SongServerStatus
    {
        public enum State
        {
            /// <summary>Never checked, or the URL changed since the last check.</summary>
            Unknown,
            Checking,
            Reachable,
            Unreachable,
        }

        public static State Current { get; private set; } = State.Unknown;

        /// <summary>Distinct charts the server holds — songs as YARG counts them.</summary>
        public static int Songs { get; private set; }

        /// <summary>Directories or archives the server itself could not read.</summary>
        public static int ServerProblems { get; private set; }

        public static string Error { get; private set; }

        /// <summary>Outcome of the last sync run in this session, or null if none.</summary>
        public static string LastSyncSummary { get; private set; }

        private const int TIMEOUT_SECONDS = SongServerSync.STARTUP_REACHABILITY_TIMEOUT_SECONDS;

        /// <summary>
        /// Forgets what we knew. Called when the URL changes, so a corrected typo does not
        /// keep showing the old server's verdict.
        /// </summary>
        public static void Invalidate()
        {
            Current = State.Unknown;
            Songs = 0;
            ServerProblems = 0;
            Error = null;
            Redraw();
        }

        public static void RecordSync(SongServerSync.Result result)
        {
            LastSyncSummary = result.Failures.Count > 0
                ? $"Last sync: {result.Downloaded.Count} fetched, {result.Failures.Count} failed"
                : $"Last sync: {result.Downloaded.Count} fetched";
            Redraw();
        }

        public static void RecordSyncFailure(string message)
        {
            LastSyncSummary = $"Last sync failed: {message}";
            Redraw();
        }

        /// <summary>
        /// The line shown in the settings menu. Asking for it starts a check if none has
        /// happened, so simply opening the tab is enough to get an answer.
        /// </summary>
        public static string Describe()
        {
            if (Current == State.Unknown)
            {
                // Lazy rather than hooked to a tab-shown event: the row cannot be on screen
                // without this having been called, and it cannot be called from anywhere the
                // answer is not wanted.
                Refresh().Forget();
            }

            string line = Current switch
            {
                State.Unknown     => "Song server: not checked yet",
                State.Checking    => "Song server: checking...",
                State.Reachable   => Describe(Songs, ServerProblems),
                State.Unreachable => $"Song server: not reachable ({Error})",
                _                 => string.Empty,
            };

            return LastSyncSummary == null ? line : line + "\n" + LastSyncSummary;
        }

        private static string Describe(int songs, int problems)
        {
            string line = $"Song server: connected, {songs} song{(songs == 1 ? "" : "s")}";
            if (problems > 0)
            {
                line += $" — {problems} the server could not read";
            }
            return line;
        }

        /// <summary>
        /// Checks the configured server, or <paramref name="urlOverride"/> when given.
        /// </summary>
        /// <remarks>
        /// The settings read is null-guarded rather than assumed. <c>SettingsManager.Settings</c>
        /// is null until <c>LoadSettings</c> runs, and this can be reached from a menu drawn
        /// before then; the null-reference that produces is thrown inside a fire-and-forget
        /// task, so it does not crash anything - it just leaves the row permanently blank
        /// while looking like it works. A probe was passing on exactly that.
        /// </remarks>
        public static async UniTask Refresh(string urlOverride = null)
        {
            if (Current == State.Checking)
            {
                return;
            }

            string url = urlOverride ?? SettingsManager.Settings?.SongServerUrl?.Value;
            if (string.IsNullOrWhiteSpace(url))
            {
                Current = State.Unknown;
                Error = null;
                Redraw();
                return;
            }

            // Deliberately NOT redrawing here. Refresh() runs synchronously up to the first
            // await, so a caller inside Describe() already sees Checking and renders
            // "checking..." on its own. Redrawing would re-enter the settings menu's refresh
            // from inside a tab build, which is safe today only by accident of ordering.
            Current = State.Checking;

            try
            {
                string root = url.Trim().TrimEnd('/');
                using var request = UnityWebRequest.Get($"{root}/api/v1/library");
                request.SetRequestHeader("User-Agent", "YARG");
                request.timeout = TIMEOUT_SECONDS;

                await request.SendWebRequest().WithCancellation(CancellationToken.None);

                if (request.result != UnityWebRequest.Result.Success)
                {
                    throw new Exception(request.error);
                }

                var json = JObject.Parse(request.downloadHandler.text);

                // distinct_charts, not songs: the server counts packages, and two packages
                // sharing a chart are one song to YARG. Reporting the package count would
                // promise more songs than a sync can ever deliver.
                Songs = json.Value<int>("distinct_charts");
                ServerProblems = json.Value<JArray>("problems")?.Count ?? 0;
                Error = null;
                Current = State.Reachable;
            }
            catch (Exception e)
            {
                Error = e.Message;
                Current = State.Unreachable;
                YargLogger.LogFormatWarning("Song server status check failed: {0}", e.Message);
            }

            Redraw();
        }

        /// <summary>
        /// Reuses the settings menu's existing "something changed, redraw" path rather than
        /// inventing a second one.
        /// </summary>
        private static void Redraw()
        {
            SettingsMenu.Instance?.OnSettingChanged();
        }
    }
}
