using System;

namespace YARG.Settings.Types
{
    /// <summary>
    /// An http or https URL, stored without its trailing slash.
    /// </summary>
    /// <remarks>
    /// Only absolute http/https is accepted. A relative path or a "file:" URL cannot be a
    /// server address, and taking one silently would mean the failure showed up much later
    /// as a confusing network error rather than immediately as a rejected value.
    ///
    /// The trailing slash is trimmed on the way in so that callers can concatenate paths
    /// without producing a double slash - a cosmetic problem for most servers and a 404 on
    /// the strict ones.
    /// </remarks>
    public class UrlSetting : TextSetting
    {
        public UrlSetting(string defaultValue, Action<string> onChange = null, bool allowEmpty = true)
            : base(defaultValue, onChange, allowEmpty)
        {
        }

        protected override string Sanitize(string value)
        {
            return IsValidUrl(value, out string normalized) ? normalized : null;
        }

        public static bool IsValidUrl(string value, out string normalized)
        {
            normalized = null;
            if (string.IsNullOrWhiteSpace(value))
            {
                return false;
            }

            if (!Uri.TryCreate(value.Trim(), UriKind.Absolute, out var uri))
            {
                return false;
            }

            if (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps)
            {
                return false;
            }

            normalized = uri.ToString().TrimEnd('/');
            return true;
        }
    }
}
