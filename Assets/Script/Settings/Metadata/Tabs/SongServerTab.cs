using YARG.Song.RemoteLibrary;

namespace YARG.Settings.Metadata
{
    /// <summary>
    /// The song server's own tab: where the library lives, whether it is reachable, and what
    /// this machine has of it.
    /// </summary>
    /// <remarks>
    /// A plain <see cref="MetadataTab"/> with one behaviour added. Entering the tab forgets
    /// the previous verdict so the status is re-checked, because the interesting moment is
    /// exactly when somebody opens this page after plugging the server back in - a cached
    /// "not reachable" from ten minutes ago would be worse than no answer at all.
    ///
    /// Everything on it is built from row types that already existed. It needs no prefab of
    /// its own, which is why it is a tab rather than a menu screen.
    /// </remarks>
    public class SongServerTab : MetadataTab
    {
        public SongServerTab(string name, string icon = "Generic") : base(name, icon)
        {
        }

        public override void OnTabEnter()
        {
            base.OnTabEnter();
            SongServerStatus.Invalidate();
        }

        public override void OnTabExit()
        {
            base.OnTabExit();

            // Deliberately does NOT cancel a running sync. Leaving the page you started it
            // from is not a decision to stop it, and a sync that dies because somebody
            // pressed Back would be indistinguishable from one that failed.
        }
    }
}
