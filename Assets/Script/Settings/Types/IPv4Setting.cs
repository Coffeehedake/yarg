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

        protected override string Sanitize(string value)
        {
            // IPAddress.Parse normalises - "010.1.1.1" and "10.1.1.1" are the same address
            // written differently - so the PARSED form is stored rather than what was typed.
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
