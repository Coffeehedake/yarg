using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using YARG.Helpers;

namespace Editor
{
    /// <summary>
    /// Prints who this build says it is, and where it therefore keeps a player's
    /// data.
    ///
    /// It exists because renaming a fork is not a cosmetic change: Unity derives
    /// Application.persistentDataPath from companyName and productName, so the
    /// rename silently MOVES settings.json, songcache.bin and everything else a
    /// player has. Asserting that the folder actually moved - rather than
    /// reading the two strings back out of the file we just edited - is the only
    /// way to know the consequence landed with the cause.
    ///
    /// Exits 1 if the fork still claims upstream's identity, so this cannot pass
    /// by accident on a build that was never renamed.
    /// </summary>
    public static class IdentityProbe
    {
        public static void Run()
        {
            var code = 0;
            try
            {
                PathHelper.Init();

                Log("companyName          = " + Application.companyName);
                Log("productName          = " + Application.productName);
                Log("version              = " + Application.version);
                Log("persistentDataPath   = " + Application.persistentDataPath);
                Log("PathHelper.Persistent= " + PathHelper.PersistentDataPath);
                Log("songcache            = " + PathHelper.SongCachePath);
                Log("ServerLibrary        = " + PathHelper.ServerLibraryPath);

                // The YARC Launcher path is somebody ELSE'S install location and
                // must NOT follow our rename. If this ever starts pointing at a
                // FatalException folder, the fork has stopped being able to read
                // setlists the launcher put on disk.
                Log("LauncherPath         = " + PathHelper.LauncherPath);
                if (!PathHelper.LauncherPath.Replace('\\', '/').Contains("/YARC/"))
                {
                    Log("FAIL: LauncherPath no longer points at the YARC Launcher");
                    code = 1;
                }

                if (Application.companyName == "YARC" || Application.productName == "YARG")
                {
                    Log("FAIL: this build still claims upstream's identity");
                    code = 1;
                }

                // The whole point: our data must not land in upstream's folder.
                var p = Application.persistentDataPath.Replace('\\', '/');
                if (p.Contains("/YARC/YARG"))
                {
                    Log("FAIL: player data still lands in upstream's folder: " + p);
                    code = 1;
                }

                Log(code == 0 ? "PASS" : "FAIL");
            }
            catch (Exception e)
            {
                Log("FAIL: " + e);
                code = 1;
            }

            EditorApplication.Exit(code);
        }

        private static void Log(string s)
        {
            Debug.Log("[IdentityProbe] " + s);
            Console.WriteLine("[IdentityProbe] " + s);
        }
    }
}
