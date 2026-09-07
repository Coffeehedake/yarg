using System;

namespace YARG.Settings.Metadata
{
    public sealed class TextMetadata : AbstractMetadata
    {
        public override string[] UnlocalizedSearchNames => null;

        public string TextName { get; private set; }

        /// <summary>
        /// Supplies the row's text at draw time, for text that is not knowable up front.
        /// Null for the ordinary localized case.
        /// </summary>
        /// <remarks>
        /// A status line has no localization key because its content is a fact about the
        /// world - whether a server answered, and what it said - rather than a phrase. Rows
        /// built this way are re-evaluated whenever the settings menu redraws, which is what
        /// lets an asynchronous check replace "checking..." with its answer in place.
        /// </remarks>
        public Func<string> LiveText { get; }

        public TextMetadata(string textName, bool isAdvanced = false)
            : base(isAdvanced)
        {
            TextName = textName;
        }

        public TextMetadata(Func<string> liveText, bool isAdvanced = false)
            : base(isAdvanced)
        {
            LiveText = liveText;
        }
    }
}
