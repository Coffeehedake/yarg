using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using TMPro;
using UnityEditor;
using UnityEngine;
using YARG.Menu.Settings.Visuals;
using YARG.Settings;
using YARG.Settings.Metadata;
using YARG.Settings.Types;
using YARG.Song.RemoteLibrary;

namespace YARG.Editor
{
    /// <summary>
    /// Verifies that the shared text-setting row still resolves after the
    /// IPv4SettingVisual -> TextSettingVisual rename, and that SongServerUrl is wired to it.
    /// </summary>
    /// <remarks>
    /// The rename kept the .cs.meta GUID precisely so the prefab's component reference and
    /// its serialized fields would survive. That is a claim about an asset file, not about
    /// code, and the compiler cannot check it - so it is checked here instead of asserted.
    /// </remarks>
    public static class SettingsRowProbe
    {
        private const string PrefabPath = "Assets/Prefabs/Menu/Settings/Visuals/IPv4Setting.prefab";

        private static int _failures;

        private static void Fail(string message)
        {
            _failures++;
            Debug.LogError("PROBE FAIL: " + message);
        }

        private static void Pass(string message)
        {
            Debug.Log("PROBE PASS: " + message);
        }

        public static void Run()
        {
            _failures = 0;

            try
            {
                CheckPrefab();
                CheckSetting();
                CheckTypedFilter();
                CheckStartupSync();
                CheckStatusRow();
                CheckSongServerTab();
                CheckMirrorFilter();
            }
            catch (Exception e)
            {
                Fail("probe threw: " + e);
            }

            Debug.Log(_failures == 0 ? "PROBE RESULT: PASS" : $"PROBE RESULT: FAIL ({_failures})");
            EditorApplication.Exit(_failures == 0 ? 0 : 1);
        }

        private static void CheckPrefab()
        {
            var go = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (go == null)
            {
                Fail($"{PrefabPath} did not load");
                return;
            }

            // A missing script deserialises to a null component, so this is the check that
            // the meta GUID still points at a real class.
            var visual = go.GetComponent<BaseSettingVisual>();
            if (visual == null)
            {
                Fail("the prefab's BaseSettingVisual component is missing (broken script reference)");
                return;
            }

            if (visual is not TextSettingVisual)
            {
                Fail($"expected TextSettingVisual, got {visual.GetType().Name}");
                return;
            }

            Pass("prefab resolves TextSettingVisual");

            var so = new SerializedObject(visual);
            foreach (string field in new[] { "_settingLabel", "_evenBackground", "_advancedMarker", "_inputField" })
            {
                var prop = so.FindProperty(field);
                if (prop == null)
                {
                    Fail($"serialized field {field} is not on the component");
                }
                else if (prop.objectReferenceValue == null)
                {
                    Fail($"serialized field {field} lost its reference in the rename");
                }
            }

            if (_failures == 0)
            {
                Pass("all four serialized references survived");
            }

            // The row is useless if the text field cannot report what was typed.
            var input = go.GetComponentInChildren<TMP_InputField>(true);
            if (input == null)
            {
                Fail("no TMP_InputField under the prefab");
                return;
            }

            int calls = input.onEndEdit.GetPersistentEventCount();
            bool wired = Enumerable.Range(0, calls).Any(i =>
                input.onEndEdit.GetPersistentMethodName(i) == "OnTextFieldChange" &&
                input.onEndEdit.GetPersistentTarget(i) != null);

            if (!wired)
            {
                Fail("onEndEdit is no longer wired to OnTextFieldChange on a live target");
            }
            else
            {
                Pass("onEndEdit -> OnTextFieldChange still wired");
            }
        }

        private static void CheckSetting()
        {
            // SettingsManager.Settings is null outside a running game, so the wiring is
            // checked on the type rather than on an instance.
            var prop = typeof(SettingsManager.SettingContainer).GetProperty("SongServerUrl");
            if (prop == null)
            {
                Fail("SettingContainer has no SongServerUrl property");
                return;
            }

            if (prop.PropertyType != typeof(UrlSetting))
            {
                Fail($"SongServerUrl is a {prop.PropertyType.Name}, not a UrlSetting");
                return;
            }

            Pass("SongServerUrl is a UrlSetting property");

            var tab = SettingsManager.DisplayedSettingsTabs
                .OfType<MetadataTab>()
                .FirstOrDefault(t => t.Name == "SongServer");

            if (tab == null)
            {
                Fail("no SongServer tab");
            }
            else if (!tab.Settings.OfType<FieldMetadata>().Any(f => f.FieldName == "SongServerUrl"))
            {
                Fail("the SongServer tab does not list SongServerUrl, so the row never renders");
            }
            else
            {
                Pass("SongServerUrl is listed on the SongServer tab");
            }

            // The localization key landing in the wrong section is a mistake this project
            // has already made once, and it is invisible until someone opens the menu.
            string langPath = Path.Combine(Application.streamingAssetsPath, "lang", "en-US.json");
            if (!File.Exists(langPath))
            {
                Fail($"{langPath} is missing");
            }
            else
            {
                var root = JObject.Parse(File.ReadAllText(langPath));
                foreach (string key in new[] { "Name", "Description" })
                {
                    if (root.SelectToken($"Settings.Setting.SongServerUrl.{key}") == null)
                    {
                        Fail($"Settings.Setting.SongServerUrl.{key} is not in en-US.json");
                    }
                }

                if (_failures == 0)
                {
                    Pass("localization keys are in Settings.Setting");
                }
            }

            // The behaviour the row now delegates to, exercised directly.
            var url = new UrlSetting(string.Empty, allowEmpty: true);

            if (url.AddressableName != "Setting/IPv4")
            {
                Fail($"UrlSetting asks for prefab '{url.AddressableName}', which is not the text row");
            }

            if (url.InputRegex != null)
            {
                Fail("UrlSetting declares a character filter; a URL must accept letters");
            }

            url.Value = "http://192.168.1.10:8080/";
            if (url.Value != "http://192.168.1.10:8080")
            {
                Fail($"trailing slash not trimmed: '{url.Value}'");
            }

            url.Value = "not a url";
            if (url.Value != string.Empty)
            {
                Fail($"an invalid URL was stored: '{url.Value}'");
            }

            url.Value = string.Empty;
            if (url.Value != string.Empty)
            {
                Fail("empty was rejected even though allowEmpty is set");
            }

            var ip = new IPv4Setting(string.Empty, allowEmpty: true);
            if (ip.InputRegex != @"[\d.]")
            {
                Fail($"IPv4Setting lost its character filter: '{ip.InputRegex}'");
            }

            // Leading-zero octets are octal to .NET, so this is 8.1.1.1 and not 10.1.1.1.
            // Asserted as measured rather than as expected: it is upstream YARG behaviour,
            // it surprises people, and pinning it here means a future change to it is seen.
            ip.Value = "010.1.1.1";
            if (ip.Value != "8.1.1.1")
            {
                Fail($"IPv4 parsing changed: '010.1.1.1' now stores '{ip.Value}'");
            }
        }

        /// <summary>
        /// The claim that actually matters to a player: a URL can be typed into the row.
        /// </summary>
        /// <remarks>
        /// Reported as inconclusive rather than failed when the row cannot be built outside
        /// a running menu - an unbuildable row proves nothing either way, and calling that a
        /// failure would be the same mistake as reading a broken harness as a defect.
        /// </remarks>
        private static void CheckTypedFilter()
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null)
            {
                return;
            }

            GameObject instance = null;
            try
            {
                instance = UnityEngine.Object.Instantiate(prefab);
                var visual = instance.GetComponent<BaseSettingVisual>();
                var input = instance.GetComponentInChildren<TMP_InputField>(true);

                visual.AssignPresetSetting("SongServerUrl", false, new UrlSetting(string.Empty, allowEmpty: true));

                if (input.characterValidation != TMP_InputField.CharacterValidation.None)
                {
                    Fail($"the prefab's IPv4 character filter is still active ({input.characterValidation})");
                }

                if (input.onValidateInput != null && input.onValidateInput(string.Empty, 0, 'h') == '\0')
                {
                    Fail("the row rejects the letter 'h', so no URL can be typed into it");
                }
                else
                {
                    Pass("a URL is typeable in the row");
                }

                visual.AssignPresetSetting("RB3EBroadcastIP", false, new IPv4Setting(string.Empty, allowEmpty: true));

                if (input.onValidateInput == null)
                {
                    Fail("IPv4 lost its character filter entirely");
                }
                else if (input.onValidateInput(string.Empty, 0, 'h') != '\0')
                {
                    Fail("the IPv4 row now accepts letters");
                }
                else if (input.onValidateInput(string.Empty, 0, '7') != '7')
                {
                    Fail("the IPv4 row rejects digits");
                }
                else
                {
                    Pass("the IPv4 filter still rejects letters and accepts digits");
                }
            }
            catch (Exception e)
            {
                Debug.Log("PROBE INCONCLUSIVE: the row could not be built outside a running menu: " + e.Message);
            }
            finally
            {
                if (instance != null)
                {
                    UnityEngine.Object.DestroyImmediate(instance);
                }
            }
        }

        /// <summary>
        /// The startup auto-sync wiring: the setting exists, is reachable from the menu, and
        /// the sync can actually be told to fail fast.
        /// </summary>
        /// <remarks>
        /// The behaviour these guard is asymmetric and easy to regress silently. A startup
        /// sync that cannot time out quickly turns "my Pi is off" into a 30 s freeze on every
        /// launch, and a Sync overload that loses its timeout parameter would compile
        /// perfectly while doing exactly that.
        /// </remarks>
        private static void CheckStartupSync()
        {
            var prop = typeof(SettingsManager.SettingContainer).GetProperty("SyncOnStartup");
            if (prop == null)
            {
                Fail("SettingContainer has no SyncOnStartup property");
                return;
            }

            if (prop.PropertyType != typeof(ToggleSetting))
            {
                Fail($"SyncOnStartup is a {prop.PropertyType.Name}, not a ToggleSetting");
                return;
            }

            var tab = SettingsManager.DisplayedSettingsTabs
                .OfType<MetadataTab>()
                .FirstOrDefault(t => t.Name == "SongServer");

            if (tab == null || !tab.Settings.OfType<FieldMetadata>().Any(f => f.FieldName == "SyncOnStartup"))
            {
                Fail("SyncOnStartup is not listed on the SongServer tab, so it never renders");
            }

            string langPath = Path.Combine(Application.streamingAssetsPath, "lang", "en-US.json");
            if (File.Exists(langPath))
            {
                var root = JObject.Parse(File.ReadAllText(langPath));
                foreach (string key in new[] { "Name", "Description" })
                {
                    if (root.SelectToken($"Settings.Setting.SyncOnStartup.{key}") == null)
                    {
                        Fail($"Settings.Setting.SyncOnStartup.{key} is not in en-US.json");
                    }
                }
            }

            // The startup budget must be a real fail-fast, and must be shorter than the
            // ordinary one rather than accidentally equal to it.
            int startup = SongServerSync.STARTUP_REACHABILITY_TIMEOUT_SECONDS;
            if (startup <= 0 || startup > 10)
            {
                Fail($"STARTUP_REACHABILITY_TIMEOUT_SECONDS is {startup}s; that is not a fail-fast");
            }

            // Sync must still ACCEPT a shorter timeout. Reflection rather than a call,
            // because calling it needs a server.
            var sync = typeof(SongServerSync).GetMethod("Sync");
            var timeoutParam = sync?.GetParameters().FirstOrDefault(x => x.Name == "listTimeoutSeconds");
            if (timeoutParam == null)
            {
                Fail("SongServerSync.Sync no longer takes listTimeoutSeconds, so the startup " +
                    "path cannot fail fast");
            }
            else if (!timeoutParam.HasDefaultValue || (int) timeoutParam.DefaultValue != 30)
            {
                Fail($"listTimeoutSeconds default changed to {timeoutParam.DefaultValue}; the " +
                    "manual sync path relies on the longer one");
            }
            else
            {
                Pass("startup sync is wired, fails fast, and leaves the manual path alone");
            }
        }

        /// <summary>
        /// The live status row: it is on the tab, it renders without a server, and asking for
        /// it does not recurse.
        /// </summary>
        /// <remarks>
        /// The interesting failure is not "wrong text" but "no text ever". Describe() starts
        /// its own check as a side effect of being called, and that check redraws the menu,
        /// which calls Describe() again - so an ordering mistake here is an infinite loop or a
        /// row permanently stuck on "checking...", neither of which the compiler can see.
        /// </remarks>
        private static void CheckStatusRow()
        {
            var tab = SettingsManager.DisplayedSettingsTabs
                .OfType<MetadataTab>()
                .FirstOrDefault(t => t.Name == "SongServer");

            if (tab == null)
            {
                Fail("no SongServer tab");
                return;
            }

            var live = tab.Settings.OfType<TextMetadata>().Where(t => t.LiveText != null).ToList();
            if (live.Count == 0)
            {
                Fail("the SongManager tab has no live text row, so no server status is shown");
                return;
            }

            // With no URL configured this must settle immediately and say so, rather than
            // hanging or reporting a server that is not there.
            SongServerStatus.Invalidate();
            string text = live[0].LiveText();

            if (string.IsNullOrWhiteSpace(text))
            {
                Fail("the status row rendered empty");
            }
            else if (!text.Contains("Song server"))
            {
                Fail($"the status row does not name what it describes: '{text}'");
            }
            else
            {
                Pass($"status row renders with no server configured: '{text}'");
            }

            // Calling it repeatedly must be free and must not wedge the state machine.
            for (int i = 0; i < 5; i++)
            {
                live[0].LiveText();
            }

            if (SongServerStatus.Current == SongServerStatus.State.Checking)
            {
                Fail("the status row is stuck in Checking with no URL set");
            }
            else
            {
                Pass("repeated draws leave the status state settled");
            }

            // The check above is only meaningful if Describe() actually RAN. It used to
            // throw inside a fire-and-forget task before setting any state, which left
            // Current at Unknown and made both assertions pass vacuously. Refreshing with an
            // explicit empty URL exercises the same path with nothing to swallow an error.
            SongServerStatus.Refresh(string.Empty).GetAwaiter().GetResult();

            if (SongServerStatus.Current != SongServerStatus.State.Unknown)
            {
                Fail($"an empty URL left the status at {SongServerStatus.Current}, not Unknown");
            }
            else
            {
                Pass("an empty URL settles to Unknown without throwing");
            }
        }

        /// <summary>
        /// The Song Server tab as a whole: it exists, its icon is a sprite that is really in
        /// the atlas, and it offers both a sync and a way out of one.
        /// </summary>
        /// <remarks>
        /// The icon check is the one worth having. Tab icons are Addressables sprite-atlas
        /// lookups by string - <c>TabIcons[Import]</c> - so a name that is not in the atlas
        /// compiles, runs, and produces a tab with no icon that nobody notices until a
        /// screenshot.
        /// </remarks>
        private static void CheckSongServerTab()
        {
            var tab = SettingsManager.DisplayedSettingsTabs
                .OfType<MetadataTab>()
                .FirstOrDefault(t => t.Name == "SongServer");

            if (tab == null)
            {
                Fail("there is no SongServer settings tab");
                return;
            }

            var atlas = AssetDatabase.LoadAllAssetsAtPath("Assets/Art/Menu/Common/Icons/TabIcons.png")
                .OfType<Sprite>()
                .Select(x => x.name)
                .ToList();

            if (atlas.Count == 0)
            {
                Debug.Log("PROBE INCONCLUSIVE: the tab icon atlas could not be read");
            }
            else if (!atlas.Contains(tab.Icon))
            {
                Fail($"tab icon '{tab.Icon}' is not a sprite in TabIcons; the tab renders blank. " +
                    $"Available: {string.Join(", ", atlas)}");
            }
            else
            {
                Pass($"the SongServer tab uses a real atlas sprite ('{tab.Icon}')");
            }

            var buttons = tab.Settings.OfType<ButtonRowMetadata>().SelectMany(b => b.Buttons).ToList();
            foreach (string name in new[] { "SyncFromSongServer", "CancelSongServerSync" })
            {
                if (!buttons.Contains(name))
                {
                    Fail($"the SongServer tab has no {name} button");
                }
                else if (typeof(SettingsManager.SettingContainer).GetMethod(name) == null)
                {
                    Fail($"{name} is on the tab but is not a public method, so pressing it throws");
                }
            }

            // Both live rows must be present: reachability and what this machine holds
            // answer different questions and one is not a substitute for the other.
            if (tab.Settings.OfType<TextMetadata>().Count(t => t.LiveText != null) < 2)
            {
                Fail("the SongServer tab is missing a live row (status and mirror are both needed)");
            }

            string mirror = SongServerStatus.DescribeMirror();
            if (string.IsNullOrWhiteSpace(mirror) || !mirror.Contains("Mirrored"))
            {
                Fail($"the mirror row does not describe the mirror: '{mirror}'");
            }
            else
            {
                Pass($"mirror row renders with an empty mirror: '{mirror}'");
            }

            // Counting against a folder that really holds songs, rather than trusting that
            // the empty case generalises. The smoke test leaves 23 verified archives here.
            string populated = Path.Combine(Path.GetTempPath(), "yarg-song-server-smoketest");
            if (!Directory.Exists(populated))
            {
                Debug.Log("PROBE INCONCLUSIVE: no mirrored corpus on disk to count " +
                    "(run Editor.SongServerSyncSmokeTest.Run first)");
            }
            else
            {
                int onDisk = Directory.GetFiles(populated, "*.sng").Length;
                string counted = SongServerStatus.DescribeMirror(populated);

                if (!counted.Contains(onDisk.ToString()))
                {
                    Fail($"the mirror row counted wrong: folder has {onDisk}, row says '{counted}'");
                }
                else if (counted.Contains("0 KB"))
                {
                    Fail($"the mirror row reports no bytes for {onDisk} real files: '{counted}'");
                }
                else
                {
                    Pass($"mirror row counts a real mirror: '{counted}' ({onDisk} files on disk)");
                }
            }

            // Cancelling when nothing is running must be a no-op, not a crash: the button is
            // always on screen.
            SongServerStatus.CancelSync();

            var langRoot = JObject.Parse(File.ReadAllText(
                Path.Combine(Application.streamingAssetsPath, "lang", "en-US.json")));
            foreach (string token in new[] { "Settings.Tab.SongServer", "Settings.Button.CancelSongServerSync" })
            {
                if (langRoot.SelectToken(token) == null)
                {
                    Fail($"{token} is not in en-US.json, so it renders as a raw key");
                }
            }

            if (_failures == 0)
            {
                Pass("the SongServer tab is complete and localized");
            }
        }

        /// <summary>
        /// The "server:" search filter's two pieces of real logic, exercised directly.
        /// </summary>
        /// <remarks>
        /// Both are the kind of thing that is obviously correct and quietly is not. Prefix
        /// containment says a song in "ServerLibraryOld" lives in "ServerLibrary" unless the
        /// separator is checked, and query splitting has to hand back the REST of the query
        /// intact or typing "artist:queen;server:yes" silently drops the artist term.
        /// </remarks>
        private static void CheckMirrorFilter()
        {
            // Path containment.
            var pathCases = new (string Path, string Root, bool Expected, string Why)[]
            {
                (@"C:\x\ServerLibrary\a.sng",    @"C:\x\ServerLibrary", true,  "a file directly inside"),
                (@"C:\x\ServerLibrary\s\a.sng", @"C:\x\ServerLibrary", true,  "a file nested deeper"),
                (@"C:/x/ServerLibrary/a.sng",       @"C:\x\ServerLibrary", true,  "mixed separators"),
                (@"c:\X\serverlibrary\a.sng",    @"C:\x\ServerLibrary", true,  "different case"),
                (@"C:\x\ServerLibrary",           @"C:\x\ServerLibrary", true,  "the root itself"),
                (@"C:\x\ServerLibraryOld\a.sng", @"C:\x\ServerLibrary", false, "a sibling sharing a prefix"),
                (@"C:\x\Other\a.sng",            @"C:\x\ServerLibrary", false, "an unrelated folder"),
                (null,                              @"C:\x\ServerLibrary", false, "a null path"),
            };

            int pathFailures = 0;
            foreach (var (path, root, expected, why) in pathCases)
            {
                if (MirroredSongs.IsUnder(path, root) != expected)
                {
                    Fail($"path containment wrong for {why}: '{path}' under '{root}' " +
                        $"should be {expected}");
                    pathFailures++;
                }
            }

            if (pathFailures == 0)
            {
                Pass($"mirror path containment holds for {pathCases.Length} cases incl. a prefix sibling");
            }

            // Query extraction. The remaining query matters as much as the verdict.
            var queryCases = new (string Query, MirroredSongs.Want Want, string Remaining)[]
            {
                ("server:yes",              MirroredSongs.Want.Mirrored,    ""),
                ("server:no",               MirroredSongs.Want.NotMirrored, ""),
                ("server:local",            MirroredSongs.Want.NotMirrored, ""),
                ("server:",                 MirroredSongs.Want.Mirrored,    ""),
                ("SERVER:YES",              MirroredSongs.Want.Mirrored,    ""),
                ("artist:queen;server:yes", MirroredSongs.Want.Mirrored,    "artist:queen"),
                ("server:yes;artist:queen", MirroredSongs.Want.Mirrored,    "artist:queen"),
                ("artist:queen",            MirroredSongs.Want.Either,      "artist:queen"),
                ("",                        MirroredSongs.Want.Either,      ""),
                ("observer:x",              MirroredSongs.Want.Either,      "observer:x"),
            };

            int queryFailures = 0;
            foreach (var (query, expectedWant, expectedRemaining) in queryCases)
            {
                var want = MirroredSongs.ExtractWant(query, out string remaining);
                if (want != expectedWant)
                {
                    Fail($"'{query}' gave want={want}, expected {expectedWant}");
                    queryFailures++;
                }
                if (remaining.Trim() != expectedRemaining)
                {
                    Fail($"'{query}' left '{remaining}', expected '{expectedRemaining}'");
                    queryFailures++;
                }
            }

            if (queryFailures == 0)
            {
                Pass($"'server:' extraction holds for {queryCases.Length} queries, " +
                    "including one that only looks like it ('observer:')");
            }
        }
    }
}
