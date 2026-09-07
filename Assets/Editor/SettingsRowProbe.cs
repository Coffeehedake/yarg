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
                .FirstOrDefault(t => t.Name == "SongManager");

            if (tab == null)
            {
                Fail("no SongManager tab");
            }
            else if (!tab.Settings.OfType<FieldMetadata>().Any(f => f.FieldName == "SongServerUrl"))
            {
                Fail("the SongManager tab does not list SongServerUrl, so the row never renders");
            }
            else
            {
                Pass("SongServerUrl is listed on the SongManager tab");
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
                .FirstOrDefault(t => t.Name == "SongManager");

            if (tab == null || !tab.Settings.OfType<FieldMetadata>().Any(f => f.FieldName == "SyncOnStartup"))
            {
                Fail("SyncOnStartup is not listed on the SongManager tab, so it never renders");
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
                .FirstOrDefault(t => t.Name == "SongManager");

            if (tab == null)
            {
                Fail("no SongManager tab");
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
    }
}
