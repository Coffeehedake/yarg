using System;
using Newtonsoft.Json.Linq;

namespace YARG.Integration.SelfUpdate
{
    /// <summary>
    /// What the update server says the newest build is.
    /// </summary>
    /// <remarks>
    /// Parsed by hand from a <see cref="JObject"/> rather than deserialised into a type,
    /// matching <c>SongServerStatus</c>. A manifest arrives from the network, and a missing
    /// or mistyped field should disable the feature with a reason, not throw inside a
    /// deserialiser whose message names a C# member the person reading it has never heard of.
    ///
    /// <see cref="Sha256"/> is required and checked before anything is unpacked. Be clear about
    /// what that buys: it proves the zip is the one this manifest describes. It proves nothing
    /// about whether the manifest is ours, because anything that can answer for the update host
    /// can serve its own manifest and its own matching hash. See ADR-006 - this is why the
    /// feature belongs on a LAN until the manifest is signed or the transport is pinned.
    /// </remarks>
    public sealed class UpdateManifest
    {
        public string Branch { get; private set; }
        public int Build { get; private set; }
        public string Commit { get; private set; }
        public string Url { get; private set; }
        public string Sha256 { get; private set; }
        public long Size { get; private set; }
        public string Notes { get; private set; }

        /// <summary>Why the manifest was rejected, when <see cref="TryParse"/> returns false.</summary>
        public static bool TryParse(string json, out UpdateManifest manifest, out string error)
        {
            manifest = null;
            error = null;

            JObject root;
            try
            {
                root = JObject.Parse(json);
            }
            catch (Exception e)
            {
                error = "the update server did not return JSON: " + e.Message;
                return false;
            }

            var m = new UpdateManifest
            {
                Branch = (string) root["branch"],
                Commit = (string) root["commit"],
                Url = (string) root["url"],
                Sha256 = ((string) root["sha256"])?.Trim().ToLowerInvariant(),
                Notes = (string) root["notes"],
            };

            if (root["build"] == null || !int.TryParse(root["build"].ToString(), out int build))
            {
                error = "manifest has no usable 'build' number";
                return false;
            }
            m.Build = build;

            if (root["size"] != null && long.TryParse(root["size"].ToString(), out long size))
            {
                m.Size = size;
            }

            if (string.IsNullOrWhiteSpace(m.Branch))
            {
                error = "manifest has no 'branch'";
                return false;
            }

            if (string.IsNullOrWhiteSpace(m.Url))
            {
                error = "manifest has no 'url'";
                return false;
            }

            // A manifest without a hash is refused rather than trusted. An unverified download
            // that replaces the game is strictly worse than no update at all.
            if (string.IsNullOrWhiteSpace(m.Sha256) || m.Sha256.Length != 64)
            {
                error = "manifest has no usable 'sha256' (64 hex characters)";
                return false;
            }

            manifest = m;
            return true;
        }

        /// <summary>
        /// Whether this manifest describes something newer than <paramref name="current"/>.
        /// </summary>
        /// <remarks>
        /// A manifest for a DIFFERENT branch is never an update, however high its build number.
        /// A machine running <c>dev</c> must not be walked onto <c>main</c> by a server that
        /// changed what it publishes.
        /// </remarks>
        public bool IsNewerThan(BuildIdentity current)
        {
            if (!current.IsKnown)
            {
                return false;
            }

            return string.Equals(Branch, current.Branch, StringComparison.Ordinal)
                && Build > current.Build;
        }

        public override string ToString()
        {
            return $"{Branch} b{Build}" + (string.IsNullOrEmpty(Commit) ? "" : $" ({Commit})");
        }
    }
}
