using System;

namespace YARG.Settings.Types
{
    /// <summary>
    /// A setting the player types into, with validation supplied by the subclass.
    /// </summary>
    /// <remarks>
    /// This exists because there was exactly one string setting in the project - the IPv4
    /// one - and its visual hard-coded IPv4 parsing, so a second string setting could not
    /// reuse it. The alternative was a duplicate prefab per string setting, which is the kind
    /// of copy that quietly diverges.
    ///
    /// The split is: the VISUAL owns the text field and knows nothing about what is valid;
    /// the SETTING owns what is valid and nothing about the UI. Adding another kind of text
    /// setting is then a subclass and a localization entry, with no new prefab and no
    /// Addressables change.
    /// </remarks>
    public abstract class TextSetting : AbstractSetting<string>
    {
        /// <summary>
        /// The prefab that renders every text setting.
        /// </summary>
        /// <remarks>
        /// The key still says IPv4 because that is what the prefab was originally built for
        /// and renaming an Addressables key is a separate change to a separate asset. It is
        /// a lookup key, not a description; every text setting deliberately shares this one
        /// prefab.
        /// </remarks>
        public override string AddressableName => "Setting/IPv4";

        /// <summary>
        /// What to fall back to when the player types something invalid.
        /// </summary>
        protected readonly string _defaultValue;

        /// <summary>
        /// Whether empty is a legitimate value, as opposed to invalid. For anything optional
        /// it is the difference between "not configured" and "configured wrongly".
        /// </summary>
        public bool AllowEmpty { get; }

        protected TextSetting(string defaultValue, Action<string> onChange = null, bool allowEmpty = false)
            : base(onChange)
        {
            _defaultValue = defaultValue;
            AllowEmpty = allowEmpty;
            _value = defaultValue;
        }

        /// <summary>
        /// Returns what should actually be stored for the text the player typed, or null to
        /// reject it and keep the default.
        /// </summary>
        /// <remarks>
        /// Returning the sanitised value rather than a bool is deliberate: IPv4 normalises
        /// what it accepts, and a validator that could only say yes or no would silently lose
        /// that.
        /// </remarks>
        protected abstract string Sanitize(string value);

        protected override void SetValue(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                _value = AllowEmpty ? string.Empty : _defaultValue;
                return;
            }

            _value = Sanitize(value) ?? _defaultValue;
        }

        public override bool ValueEquals(string value)
        {
            return value == Value;
        }
    }
}
