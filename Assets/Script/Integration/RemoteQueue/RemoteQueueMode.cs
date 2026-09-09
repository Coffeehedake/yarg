namespace YARG.Integration.RemoteQueue
{
    /// <summary>
    /// Who may reach the remote queue server.
    ///
    /// Deliberately three values rather than a bool. "On" would have had to mean
    /// <see cref="Lan"/>, and on a home network that is every device in the house
    /// including the ones nobody is thinking about. This server has no
    /// authentication - anybody who can reach it can queue a song - so the
    /// difference between "only this machine" and "anybody on the wifi" is a
    /// decision the player should make on purpose.
    /// </summary>
    public enum RemoteQueueMode
    {
        /// <summary>No socket is opened at all. The default.</summary>
        Off = 0,

        /// <summary>Bound to loopback only. Useful for trying it on the same machine.</summary>
        Local = 1,

        /// <summary>Bound to every interface, so phones on the same network can reach it.</summary>
        Lan = 2,
    }
}
