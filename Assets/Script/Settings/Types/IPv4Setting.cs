using System;
using System.Net;
using System.Net.Sockets;

namespace YARG.Settings.Types
{
    public class IPv4Setting : TextSetting
    {
        public IPv4Setting(string defaultValue, Action<string> onChange = null, bool allowEmpty = false)
            : base(defaultValue, onChange, allowEmpty)
        {
        }

        /// <summary>
        /// Digits and dots. Matches the filter the shared prefab was built with.
        /// </summary>
        public override string InputRegex => @"[\d.]";

        protected override string Sanitize(string value)
        {
            // The PARSED form is stored rather than what was typed, because IPAddress
            // rewrites some of what it accepts. Measured, not assumed: "010.1.1.1" parses
            // to 8.1.1.1, because .NET reads a leading-zero octet as octal. Storing what was
            // typed would mean the settings file and the address actually used disagree.
            return IPAddress.TryParse(value, out var ip) && IsValidIPv4(ip) ? ip.ToString() : null;
        }

        public static bool IsValidIPv4(string ip)
        {
            if (string.IsNullOrEmpty(ip))
            {
                return false;
            }

            if (!IPAddress.TryParse(ip, out var ipAddress))
            {
                return false;
            }

            return IsValidIPv4(ipAddress);
        }

        public static bool IsValidIPv4(IPAddress ip)
        {
            if (ip.AddressFamily != AddressFamily.InterNetwork)
            {
                return false;
            }

            return true;
        }
    }
}
