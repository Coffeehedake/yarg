using System;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;
using YARG.Core.Logging;
using YARG.Menu.Navigation;
using YARG.Settings.Types;

namespace YARG.Menu.Settings.Visuals
{
    /// <summary>
    /// The settings row for any <see cref="TextSetting"/>: a label and a text field.
    /// </summary>
    /// <remarks>
    /// This was <c>IPv4SettingVisual</c> and parsed IPv4 addresses itself, so the prefab it
    /// is attached to could not serve a second string setting. Both halves of "what may be
    /// typed" now belong to the setting - the character filter and the validation - and this
    /// class only applies them and redraws.
    ///
    /// The file was renamed rather than replaced so its .meta GUID survives, which is what
    /// keeps the prefab's component reference and its four serialized fields intact.
    /// </remarks>
    public class TextSettingVisual : BaseSettingVisual<TextSetting>
    {
        [SerializeField]
        private TMP_InputField _inputField;

        protected override void OnSettingInit()
        {
            // The prefab is shared and has the IPv4 filter - CharacterValidation.Regex with
            // m_RegexValue "[\d.]" - serialized on it, so a setting that wants a different
            // filter, or none, has to actively displace it. TMP exposes no setter for
            // m_RegexValue, but onValidateInput is public and takes precedence over the
            // built-in validation (TMP_InputField.cs:631, `onValidateInput ?? Validate`), so
            // the filter is installed as a delegate and the serialized one is switched off.
            _inputField.characterValidation = TMP_InputField.CharacterValidation.None;

            string regex = Setting.InputRegex;
            if (string.IsNullOrEmpty(regex))
            {
                _inputField.onValidateInput = null;
            }
            else
            {
                var filter = new Regex(regex);
                // '\0' is TMP's "reject this character"; it is what its own Validate returns.
                _inputField.onValidateInput =
                    (_, _, added) => filter.IsMatch(added.ToString()) ? added : '\0';
            }

            base.OnSettingInit();
        }

        public override void RefreshVisual()
        {
            _inputField.text = Setting.Value;
        }

        public override NavigationScheme GetNavigationScheme()
        {
            return new NavigationScheme(new()
            {
                NavigateFinish
            }, true);
        }

        public void OnTextFieldChange()
        {
            try
            {
                // The setter sanitises and falls back to the default on its own, so there is
                // no validation to do here. RefreshVisual then shows what was actually
                // stored, which is how a rejected entry becomes visible to the player.
                Setting.Value = _inputField.text;
            }
            catch (Exception e)
            {
                // The old version swallowed this silently. A setting's OnChange callback
                // throwing is a real bug and should not be invisible.
                YargLogger.LogException(e, "Failed to apply a typed setting value");
            }

            RefreshVisual();
        }
    }
}
