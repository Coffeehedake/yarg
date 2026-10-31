using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>
    /// What to tell the player about where the remote queue is, in words.
    /// </summary>
    /// <remarks>
    /// WHY THIS EXISTS. The phone app tells a guest "set Remote queue to LAN; YARG will show an
    /// address" - and for a long time YARG showed nothing. The only trace was a log line,
    /// <c>listening on http://+:8099/</c>, whose host is a wildcard rather than an address.
    ///
    /// IT REPORTS THE REAL STATE, not just the chosen mode: off, this-computer-only, listening
    /// at <i>this</i> address, or could not start and why. A failed start used to be a log line
    /// and nothing else, leaving a setting that said LAN over a server that was not running.
    ///
    /// A CORRECTION, KEPT BECAUSE IT WAS EASY TO MAKE. An earlier version of this class warned
    /// that LAN mode cannot bind for an ordinary Windows user and suggested a <c>netsh</c>
    /// command. That rested on a test run in PowerShell 7, where HttpListener is HTTP.sys and
    /// does need a URL reservation. The game is Unity's Mono, whose HttpListener is a managed
    /// implementation that does not: LAN mode bound to 0.0.0.0:8099 as a non-elevated user and
    /// answered on the LAN address (measured against the running game, 2026-10-30). The wrong
    /// runtime was measured, so the warning and the command are gone.
    ///
    /// Pure on purpose: everything it needs is passed in, so every sentence can be checked
    /// headless. The one impure part is <see cref="Gather"/>, which only reads the machine.
    /// </remarks>
    public static class RemoteQueueAddress
    {
        /// <summary>One IPv4 address a phone might reach this machine on.</summary>
        public readonly struct Candidate
        {
            public readonly string Ip;

            /// <summary>
            /// Whether the interface it belongs to has a default gateway. The one a phone on
            /// the same Wi-Fi can reach is, in practice, the one that does; Tailscale and the
            /// virtual switches Hyper-V and WSL create usually do not.
            /// </summary>
            public readonly bool HasGateway;

            public Candidate(string ip, bool hasGateway)
            {
                Ip = ip;
                HasGateway = hasGateway;
            }
        }

        /// <summary>Reads this machine's IPv4 addresses. An empty list is a valid answer.</summary>
        public static List<Candidate> Gather()
        {
            var found = new List<Candidate>();

            try
            {
                foreach (var nic in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (nic.OperationalStatus != OperationalStatus.Up ||
                        nic.NetworkInterfaceType == NetworkInterfaceType.Loopback)
                    {
                        continue;
                    }

                    var properties = nic.GetIPProperties();
                    bool hasGateway = properties.GatewayAddresses.Any(g =>
                        g.Address.AddressFamily == AddressFamily.InterNetwork &&
                        !g.Address.Equals(IPAddress.Any));

                    foreach (var unicast in properties.UnicastAddresses)
                    {
                        if (unicast.Address.AddressFamily == AddressFamily.InterNetwork)
                        {
                            found.Add(new Candidate(unicast.Address.ToString(), hasGateway));
                        }
                    }
                }
            }
            catch (Exception)
            {
                // Some platforms refuse to enumerate interfaces. "Nothing found" is handled
                // below with its own sentence; it is not worth failing a settings screen over.
            }

            return found;
        }

        /// <summary>
        /// The addresses worth showing, best first: no loopback, no link-local (169.254, what an
        /// adapter gives itself when it has no network), no duplicates, and the ones on an
        /// interface with a gateway ahead of the rest.
        /// </summary>
        public static IReadOnlyList<string> Choose(IEnumerable<Candidate> candidates)
        {
            if (candidates == null)
            {
                return Array.Empty<string>();
            }

            return candidates
                .Where(c => !string.IsNullOrWhiteSpace(c.Ip) &&
                            !c.Ip.StartsWith("127.", StringComparison.Ordinal) &&
                            !c.Ip.StartsWith("169.254.", StringComparison.Ordinal) &&
                            c.Ip != "0.0.0.0")
                .Select((c, order) => (c, order))
                .OrderByDescending(x => x.c.HasGateway) // then by original order, which OrderBy keeps
                .ThenBy(x => x.order)
                .Select(x => x.c.Ip)
                .Distinct()
                .ToList();
        }

        /// <summary>The sentence the settings screen shows under the Remote Queue setting.</summary>
        /// <param name="running">Whether the listener is actually up, not merely whether a mode is chosen.</param>
        /// <param name="error">Why it could not start, if it could not.</param>
        public static string Format(
            RemoteQueueMode mode,
            bool running,
            string error,
            IEnumerable<Candidate> candidates,
            int port)
        {
            if (mode == RemoteQueueMode.Off)
            {
                return "Remote queue is off.";
            }

            if (!running)
            {
                string why = string.IsNullOrWhiteSpace(error) ? "no reason was reported" : error.Trim().TrimEnd('.');
                return $"Could not start ({mode}): {why}. Another program may be using port {port}.";
            }

            if (mode == RemoteQueueMode.Local)
            {
                return $"Only this computer can reach it: 127.0.0.1:{port}. Choose LAN to let phones connect.";
            }

            var addresses = Choose(candidates);
            if (addresses.Count == 0)
            {
                return "On, but no network address was found. Is this computer connected to a network?";
            }

            string line = $"Type this into the app: {addresses[0]}:{port}";
            if (addresses.Count > 1)
            {
                line += $" (if that does not connect, try {string.Join(", ", addresses.Skip(1).Take(3).Select(a => $"{a}:{port}"))})";
            }

            return line;
        }
    }
}
