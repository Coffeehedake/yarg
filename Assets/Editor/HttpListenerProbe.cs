using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEngine;

namespace Editor
{
    /// <summary>
    /// Decides how an embedded web server inside YARG should listen, by measuring
    /// rather than reasoning about it.
    ///
    /// The question matters and has a real trap. On stock .NET for Windows,
    /// <see cref="HttpListener"/> is a thin wrapper over http.sys, and binding
    /// anything except loopback needs an administrator or a pre-registered URL
    /// ACL (`netsh http add urlacl`). A feature that works for the developer on
    /// 127.0.0.1 and then throws "Access is denied" the moment a player points it
    /// at their LAN would be a miserable thing to discover after building it.
    ///
    /// Unity ships Mono's class library, whose HttpListener is a MANAGED socket
    /// implementation with no http.sys involved, so the expectation is that it
    /// binds fine. Expectation is not measurement, and this is cheap to measure.
    ///
    /// Also probed: whether the type survives at all (IL2CPP managed stripping can
    /// remove it), and whether a raw TcpListener on IPAddress.Any binds - the
    /// fallback if HttpListener turns out to be unusable.
    ///
    /// Exits 1 if no viable listening strategy exists, so this cannot be read as
    /// a pass by a build that never actually bound a socket.
    /// </summary>
    public static class HttpListenerProbe
    {
        private const int Port = 18110;

        public static void Run()
        {
            var code = 0;
            try
            {
                Log("HttpListener.IsSupported = " + HttpListener.IsSupported);
                Log("runtime = " + System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription);

                var loopback = TryHttpListener($"http://127.0.0.1:{Port}/", "loopback");
                var wildcard = TryHttpListener($"http://+:{Port + 1}/", "wildcard +  (the LAN case)");
                var star     = TryHttpListener($"http://*:{Port + 2}/", "wildcard *");
                var raw      = TryRawTcp(Port + 3);

                Log("");
                Log("RESULT");
                Log("  HttpListener loopback     : " + (loopback ? "works" : "NO"));
                Log("  HttpListener all-interfaces: " + (wildcard || star ? "works" : "NO"));
                Log("  TcpListener  all-interfaces: " + (raw ? "works" : "NO"));

                if (!loopback && !raw)
                {
                    Log("FAIL: nothing can listen, so an embedded server is not possible this way");
                    code = 1;
                }
                else if (!wildcard && !star)
                {
                    // Not a failure of the probe - a finding. Loopback-only would
                    // mean the LAN half of the feature needs the raw socket path.
                    Log("FINDING: HttpListener cannot bind all interfaces here; the LAN case needs TcpListener");
                }
                else
                {
                    Log("PASS: HttpListener can serve both loopback and the LAN");
                }
            }
            catch (Exception e)
            {
                Log("FAIL: " + e);
                code = 1;
            }

            EditorApplication.Exit(code);
        }

        /// <summary>
        /// Binds, serves exactly one request, and checks the bytes came back.
        /// Binding proves less than it looks: a listener can start and still fail
        /// on the first request, so this drives a real GET through it.
        /// </summary>
        private static bool TryHttpListener(string prefix, string what)
        {
            HttpListener listener = null;
            try
            {
                listener = new HttpListener();
                listener.Prefixes.Add(prefix);
                listener.Start();
            }
            catch (Exception e)
            {
                Log($"{what}: bind FAILED on {prefix} -> {e.GetType().Name}: {e.Message}");
                listener?.Close();
                return false;
            }

            var served = false;
            var thread = new Thread(() =>
            {
                try
                {
                    var ctx = listener.GetContext();
                    var body = Encoding.UTF8.GetBytes("yarg-probe-ok");
                    ctx.Response.ContentType = "text/plain";
                    ctx.Response.ContentLength64 = body.Length;
                    ctx.Response.OutputStream.Write(body, 0, body.Length);
                    ctx.Response.Close();
                    served = true;
                }
                catch (Exception e)
                {
                    Log($"{what}: serving threw {e.GetType().Name}: {e.Message}");
                }
            }) { IsBackground = true };
            thread.Start();

            try
            {
                // Always call back on loopback: a wildcard prefix accepts it, and
                // this probe must not depend on knowing the machine's LAN address.
                var uri = prefix.Replace("+", "127.0.0.1").Replace("*", "127.0.0.1");
                using var client = new System.Net.Http.HttpClient { Timeout = TimeSpan.FromSeconds(5) };
                var got = client.GetStringAsync(uri).GetAwaiter().GetResult();
                thread.Join(TimeSpan.FromSeconds(5));

                var ok = served && got == "yarg-probe-ok";
                Log($"{what}: bound {prefix}, request returned '{got}' -> {(ok ? "OK" : "MISMATCH")}");
                return ok;
            }
            catch (Exception e)
            {
                Log($"{what}: request FAILED -> {e.GetType().Name}: {e.Message}");
                return false;
            }
            finally
            {
                try { listener.Stop(); listener.Close(); } catch { /* closing is best effort */ }
            }
        }

        /// <summary>The fallback: can we at least bind a raw socket on every interface?</summary>
        private static bool TryRawTcp(int port)
        {
            TcpListener l = null;
            try
            {
                l = new TcpListener(IPAddress.Any, port);
                l.Start();
                Log($"raw TcpListener: bound {IPAddress.Any}:{port} OK");
                return true;
            }
            catch (Exception e)
            {
                Log($"raw TcpListener: FAILED -> {e.GetType().Name}: {e.Message}");
                return false;
            }
            finally
            {
                try { l?.Stop(); } catch { /* closing is best effort */ }
            }
        }

        private static void Log(string s)
        {
            Debug.Log("[HttpListenerProbe] " + s);
            Console.WriteLine("[HttpListenerProbe] " + s);
        }
    }
}
