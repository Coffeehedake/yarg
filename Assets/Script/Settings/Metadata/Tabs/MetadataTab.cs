using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.AddressableAssets;
using YARG.Localization;
using YARG.Menu.Navigation;
using YARG.Menu.Settings;
using YARG.Menu.Settings.Visuals;

namespace YARG.Settings.Metadata
{
    public class MetadataTab : Tab, IEnumerable<AbstractMetadata>
    {
        // Prefabs needed for this tab type
        private static GameObject _buttonPrefab;
        private static GameObject _textPrefab;

        private readonly Dictionary<string, BaseSettingVisual> _settingVisuals = new();

        /// <summary>
        /// Text rows whose content is produced at draw time. Kept because
        /// <see cref="OnSettingChanged"/> only walks <see cref="_settingVisuals"/>, and a
        /// status line that never redraws would be stuck on "checking..." forever.
        /// </summary>
        private readonly List<(TextMetadata Metadata, TextMeshProUGUI Label)> _liveTextRows = new();
        private readonly List<AbstractMetadata> _settings = new();

        public IReadOnlyList<AbstractMetadata> Settings => _settings;
        private HeaderMetadata[] _sectionsCache;
        public override IReadOnlyList<HeaderMetadata> Sections =>
            _sectionsCache ??= _settings.OfType<HeaderMetadata>().Where(header => header.IsVisible).ToArray();

        public override bool HasPreview => base.HasPreview && Sections.Any(section =>
            section.ShowPreview && section.HeaderName == SettingsMenu.Instance.CurrentSection);

        public MetadataTab(string name, string icon = "Generic", IPreviewBuilder previewBuilder = null)
            : base(name, icon, previewBuilder)
        {
        }

        public override void BuildSettingTab(Transform container, NavigationGroup navGroup)
        {
            _settingVisuals.Clear();
            _liveTextRows.Clear();

            var currentSection = SettingsMenu.Instance.CurrentSection;
            var settingIndex = 0;

            // Once we've found the tab, add the settings
            foreach (var (settingMetadata, section) in VisibleSettings())
            {
                if (section != currentSection)
                {
                    continue;
                }

                switch (settingMetadata)
                {
                    case ButtonRowMetadata buttonRow:
                    {
                        if (_buttonPrefab == null)
                        {
                            _buttonPrefab = Addressables
                                .LoadAssetAsync<GameObject>("SettingTab/Button")
                                .WaitForCompletion();
                        }
                        // Spawn the button
                        var go = Object.Instantiate(_buttonPrefab, container);

                        var buttonGroup = go.GetComponent<SettingsButton>();
                        buttonGroup.SetInfo(buttonRow.Buttons);
                        navGroup.AddNavigatable(buttonGroup);

                        break;
                    }
                    case TextMetadata text:
                    {
                        if (_textPrefab == null)
                        {
                            _textPrefab = Addressables
                                .LoadAssetAsync<GameObject>("SettingTab/Text")
                                .WaitForCompletion();
                        }
                        // Spawn in the header
                        var go = Object.Instantiate(_textPrefab, container);

                        var label = go.GetComponentInChildren<TextMeshProUGUI>();
                        if (text.LiveText != null)
                        {
                            label.text = text.LiveText();
                            _liveTextRows.Add((text, label));
                        }
                        else
                        {
                            label.text = Localize.Key("Settings.Text", text.TextName);
                        }

                        break;
                    }
                    case FieldMetadata field:
                    {
                        var setting = SettingsManager.GetSettingByName(field.FieldName);

                        var visual = SpawnSettingVisual(setting: setting, container: container);
                        visual.AssignSetting(field.FieldName, field.HasDescription);
                        visual.AssignIndex(settingIndex);
                        visual.SetEditable(setting.IsEditable);

                        _settingVisuals.Add(field.FieldName, visual);
                        navGroup.AddNavigatable(visual.gameObject);

                        settingIndex++;
                        break;
                    }
                }
            }
        }

        private IEnumerable<(AbstractMetadata Metadata, string Section)> VisibleSettings()
        {
            var section = string.Empty;
            foreach (var metadata in _settings)
            {
                if (metadata is HeaderMetadata header)
                {
                    section = header.HeaderName;
                    continue;
                }

                if (metadata.IsVisible)
                {
                    yield return (metadata, section);
                }
            }
        }

        public (string Section, int Index) GetSettingPosition(string searchName)
        {
            var currentSection = string.Empty;
            var index = 0;
            foreach (var (metadata, section) in VisibleSettings())
            {
                if (section != currentSection)
                {
                    currentSection = section;
                    index = 0;
                }

                if (metadata is not FieldMetadata && metadata is not ButtonRowMetadata)
                {
                    continue;
                }

                if (metadata.UnlocalizedSearchNames.Contains(searchName))
                {
                    return (section, index);
                }

                index++;
            }

            throw new System.ArgumentException($"Setting '{searchName}' is not visible in tab '{Name}'.", nameof(searchName));
        }

        public override void OnSettingChanged()
        {
            foreach (var (metadata, label) in _liveTextRows)
            {
                // The row can outlive its tab if the menu was rebuilt underneath us.
                if (label != null)
                {
                    label.text = metadata.LiveText();
                }
            }

            foreach (var pair in _settingVisuals)
            {
                var setting = SettingsManager.GetSettingByName(pair.Key);
                pair.Value.SetEditable(setting.IsEditable);
                pair.Value.RefreshVisual();
            }
        }

        // For collection initializer support
        public void Add(AbstractMetadata setting) => _settings.Add(setting);
        private List<AbstractMetadata>.Enumerator GetEnumerator() => _settings.GetEnumerator();
        IEnumerator<AbstractMetadata> IEnumerable<AbstractMetadata>.GetEnumerator() => GetEnumerator();
        IEnumerator IEnumerable.GetEnumerator() => GetEnumerator();
    }
}
