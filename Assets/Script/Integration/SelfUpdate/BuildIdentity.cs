using System.Text.RegularExpressions;
using UnityEngine;

namespace YARG.Integration.SelfUpdate
{
    /// <summary>
    /// Which build this is, read from the version file the build process writes.
    /// </summary>
    /// <remarks>
    /// This deliberately does NOT use <see cref="GlobalVariables.CurrentVersion"/>, and that is
    /// the single most important thing in this file.
    ///
    /// <c>GlobalVariables.LoadVersion()</c> reads <c>Resources/version.txt</c> only under
    /// <c>YARG_TEST_BUILD</c> or <c>YARG_NIGHTLY_BUILD</c>. A build made by
    /// <c>Assets/Editor/BuildPlayerHeadless.cs</c> sets no scripting defines at all -
    /// <c>BuildOptions.Development</c> is a build option, not a define - so in that build
    /// <c>CurrentVersion</c> stays the hardcoded <c>"v0.15"</c> for every commit ever made.
    /// An updater asking it "which build are you?" would get a constant, conclude it was
    /// up to date forever, and look like it was working.
    ///
    /// The file itself is written on every build by <c>Editor.Build.BuildGitCommitVersion</c>
    /// and ships in <c>resources.assets</c> regardless of defines - measured on the build made
    /// 2026-10-31, which carried <c>dev b4180 (679f00d3)</c>. So reading the TextAsset directly
    /// gets the truth without setting a define, and setting the define would have moved
    /// <c>PathHelper.PersistentDataPath</c> from <c>release/</c> to <c>dev/</c>, silently
    /// orphaning an existing install's settings, song cache and characters.
    ///
    /// <see cref="Build"/> is <c>git rev-list --count HEAD</c>, which only increases along a
    /// branch. It is the ONLY field that may be used for ordering: comparing commit hashes
    /// tells you two builds are different, never which is newer.
    /// </remarks>
    public readonly struct BuildIdentity
    {
        /// <summary>Matches what <c>GlobalVariables.LoadVersionFromGit</c> writes, e.g. <c>dev b4180 (679f00d3)</c>.</summary>
        private static readonly Regex _format = new(
            @"^\s*(?<branch>\S+)\s+b(?<build>\d+)\s+\((?<commit>[0-9a-fA-F]+)\)\s*$",
            RegexOptions.Compiled);

        public string Branch { get; }
        public int Build { get; }
        public string Commit { get; }

        /// <summary>False when the version file was missing or in a shape we do not recognise.</summary>
        public bool IsKnown => !string.IsNullOrEmpty(Branch);

        private BuildIdentity(string branch, int build, string commit)
        {
            Branch = branch;
            Build = build;
            Commit = commit;
        }

        public static bool TryParse(string text, out BuildIdentity identity)
        {
            identity = default;
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            var m = _format.Match(text);
            if (!m.Success || !int.TryParse(m.Groups["build"].Value, out int build))
            {
                return false;
            }

            identity = new BuildIdentity(m.Groups["branch"].Value, build, m.Groups["commit"].Value);
            return true;
        }

        /// <summary>
        /// This build's identity, or an unknown one if the version file is absent or unparseable.
        /// </summary>
        /// <remarks>
        /// An unknown identity is not an error to report at the player: it is what an editor
        /// session or a hand-made build legitimately looks like. The updater simply disables
        /// itself, because it cannot answer "newer than what?".
        /// </remarks>
        public static BuildIdentity Load()
        {
            var asset = Resources.Load<TextAsset>("version");
            if (asset == null || !TryParse(asset.text, out var identity))
            {
                return default;
            }

            return identity;
        }

        public override string ToString()
        {
            return IsKnown ? $"{Branch} b{Build} ({Commit})" : "unknown build";
        }
    }
}
