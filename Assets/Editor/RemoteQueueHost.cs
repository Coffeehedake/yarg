using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using YARG;
using YARG.Integration.RemoteQueue;

namespace Editor
{
    /// <summary>
    /// Brings the remote queue server up in the editor and LEAVES IT UP, so
    /// something outside Unity can talk to it.
    ///
    /// WHY THIS EXISTS. <see cref="RemoteQueueSmokeTest"/> drives the server from
    /// inside the same process and then exits, which is the right shape for
    /// checking the server against itself and the wrong shape for checking
    /// anything else against the server. The phone app in the sibling
    /// `yarg-remote` repo has its own idea of every route, method and query
    /// parameter, read off this C# by a human; the only thing that settles
    /// whether it read them correctly is pointing it at a real listener. This is
    /// that listener.
    ///
    /// It is also what makes a phone usable without playing the game: run this,
    /// pass Lan, and the app on a phone can be exercised against a real console
    /// with no scene loaded.
    ///
    /// WHAT IT CANNOT GIVE YOU. Batchmode has no song library, so
    /// <c>/api/library</c> is empty and every hash is unknown. A caller can
    /// verify that it is asking the right questions and reading the answers
    /// correctly; it cannot verify that queueing a real song works. Said here
    /// because a green contract run against this host would otherwise look like
    /// more than it is.
    ///
    /// Run with NO -quit. The process stays up until it is killed:
    ///
    ///   Unity.exe -batchmode -nographics -projectPath &lt;path&gt; \
    ///             -executeMethod Editor.RemoteQueueHost.RunLocal
    ///
    /// LAUNCH IT WITH Win32_Process.Create, NOT Start-Process, when starting it
    /// from an automated session. A process started from a Cowork bridge call
    /// inherits a job object that kills Unity's Package Manager CHILD, and the
    /// editor then dies with "Could not connect to IPC stream Upm-&lt;pid&gt;" and a
    /// message blaming anti-virus, which it is not. -noUpm is not a way around
    /// it: the packages it disables are real dependencies. This cost an hour on
    /// 2026-09-10 and was already documented before it did.
    ///
    /// Whatever launched this should also revert
    /// ProjectSettings/ProjectSettings.asset afterwards; Unity re-adds a
    /// VisionOS icon block on every run, including runs that die.
    /// </summary>
    public static class RemoteQueueHost
    {
        /// <summary>Loopback only. What a contract test on this machine wants.</summary>
        public static void RunLocal() => Run(RemoteQueueMode.Local);

        /// <summary>Every interface, so a phone on the LAN can reach it.</summary>
        public static void RunLan() => Run(RemoteQueueMode.Lan);

        private static void Run(RemoteQueueMode mode)
        {
            StartMainThreadPump();

            RemoteQueueServer.HandleModeChanged(mode);

            // Say it on stdout as well as through the logger. Whatever launched
            // this is watching the log file for a line that means "you may start
            // now", and YargLogger's output is not guaranteed to be flushed in
            // the order a tail expects.
            Debug.Log(RemoteQueueServer.IsRunning
                ? $"REMOTE_QUEUE_HOST_READY mode={mode} port={RemoteQueueServer.Port}"
                : $"REMOTE_QUEUE_HOST_FAILED mode={mode}");

            // Without -quit the editor stays alive on its own; nothing further to
            // do here. Application.quitting already closes the listener.
        }

        /// <summary>
        /// The same queue the game drains in Update(), drained from
        /// EditorApplication.update instead — because MonoBehaviour.Update does
        /// not run in edit mode, and without this every endpoint that marshals
        /// onto the main thread would time out instead of answering.
        ///
        /// Copied deliberately rather than shared with the smoke test: that class
        /// exits the process when it finishes, and importing it here to reuse one
        /// method would be a good way to have this host quietly stop existing.
        /// </summary>
        private static void StartMainThreadPump()
        {
            var field = typeof(UnityMainThreadCallback)
                .GetField("CallbackQueue", BindingFlags.NonPublic | BindingFlags.Static);

            if (field?.GetValue(null) is not Queue<Action> queue)
            {
                Debug.LogError("REMOTE_QUEUE_HOST_FAILED could not reach UnityMainThreadCallback's queue");
                return;
            }

            EditorApplication.update += () =>
            {
                while (true)
                {
                    Action action;
                    lock (queue)
                    {
                        if (queue.Count == 0)
                        {
                            return;
                        }

                        action = queue.Dequeue();
                    }

                    try
                    {
                        action.Invoke();
                    }
                    catch (Exception e)
                    {
                        Debug.LogWarning("main thread action threw: " + e.Message);
                    }
                }
            };
        }
    }
}
