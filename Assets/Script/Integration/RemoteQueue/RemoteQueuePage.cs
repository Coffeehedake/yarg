using System.Text;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>
    /// The page a phone gets. Embedded as a string rather than a StreamingAsset
    /// so it cannot go missing from a build, and so this whole feature is four
    /// source files with no asset or scene changes.
    ///
    /// Deliberately dependency-free: no CDN, no framework, no fonts. A phone at a
    /// party is on the house wifi talking to a games console; there may be no
    /// route to the internet at all, and a page that waits on a CDN would appear
    /// broken at exactly the wrong moment.
    /// </summary>
    public static class RemoteQueuePage
    {
        public static readonly byte[] Bytes = Encoding.UTF8.GetBytes(Html);

        private const string Html = @"<!doctype html>
<html lang=""en"">
<head>
<meta charset=""utf-8"">
<meta name=""viewport"" content=""width=device-width, initial-scale=1, viewport-fit=cover"">
<title>YARG queue</title>
<style>
  :root { color-scheme: dark; --bg:#12121a; --card:#1d1d28; --line:#2e2e3d;
          --text:#f2f2f7; --dim:#9a9aae; --accent:#ffd23f; --ok:#4ade80; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font:16px/1.45 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom); }
  header { position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line);
           padding:12px 14px 10px; z-index:2; }
  h1 { margin:0 0 8px; font-size:17px; letter-spacing:.02em; }
  h1 span { color:var(--dim); font-weight:400; font-size:14px; }
  input { width:100%; padding:12px 14px; font-size:16px; border-radius:10px;
          border:1px solid var(--line); background:var(--card); color:var(--text); }
  input:focus { outline:2px solid var(--accent); outline-offset:1px; }
  .tabs { display:flex; gap:8px; margin-top:10px; }
  .tabs button { flex:1; padding:9px; font-size:14px; border-radius:9px; cursor:pointer;
                 border:1px solid var(--line); background:var(--card); color:var(--dim); }
  .tabs button[aria-selected=true] { color:var(--bg); background:var(--accent);
                                     border-color:var(--accent); font-weight:600; }
  main { padding:10px 14px 28px; }
  .row { display:flex; align-items:center; gap:10px; padding:11px 0; border-bottom:1px solid var(--line); }
  .meta { min-width:0; flex:1; }
  .name { font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sub  { color:var(--dim); font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .len  { color:var(--dim); font-size:13px; font-variant-numeric:tabular-nums; }
  button.act { border:1px solid var(--line); background:var(--card); color:var(--text);
               border-radius:9px; padding:9px 13px; font-size:15px; cursor:pointer; }
  button.act:active { transform:translateY(1px); }
  .queued { color:var(--ok); font-size:13px; }
  .note { color:var(--dim); font-size:13px; padding:12px 0; }
  .pos { color:var(--dim); font-variant-numeric:tabular-nums; width:1.6em; text-align:right; }
  .now { color:var(--accent); }
  .err { color:#ff9a9a; padding:10px 0; font-size:14px; }
</style>
</head>
<body>
<header>
  <h1>YARG <span id=""ctx"">queue</span></h1>
  <input id=""q"" type=""search"" placeholder=""Search songs, artists, albums"" autocomplete=""off"">
  <div class=""tabs"">
    <button id=""tabFind"" aria-selected=""true"">Find a song</button>
    <button id=""tabQueue"" aria-selected=""false"">Up next</button>
  </div>
</header>
<main>
  <div id=""err"" class=""err"" hidden></div>
  <div id=""list""></div>
</main>
<script>
(function () {
  var showingQueue = false, timer = null, lastQuery = null;
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>""']/g, function (c) {
      return ({ '&':'&amp;','<':'&lt;','>':'&gt;','""':'&quot;',""'"":'&#39;' })[c];
    });
  }

  function len(ms) {
    if (!ms || ms < 0) return '';
    var s = Math.round(ms / 1000);
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  }

  function fail(msg) {
    var e = $('err');
    if (!msg) { e.hidden = true; return; }
    e.hidden = false;
    e.textContent = msg;
  }

  function api(path, opts) {
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) {
        if (!r.ok) throw new Error(body.error || ('HTTP ' + r.status));
        return body;
      });
    });
  }

  function render(items, queueView) {
    var list = $('list');
    if (!items.length) {
      list.innerHTML = '<div class=""note"">' +
        (showingQueue ? 'Nothing queued yet.' : 'No songs matched.') + '</div>';
      return;
    }

    list.innerHTML = items.map(function (s, i) {
      var right = showingQueue
        ? '<button class=""act"" data-drop=""' + esc(s.hash) + '"">Remove</button>'
        : '<button class=""act"" data-add=""' + esc(s.hash) + '"">Queue</button>';
      var pos = showingQueue
        ? '<div class=""pos ' + (queueView && queueView.playing_show && i === queueView.index ? 'now' : '') + '"">' +
          (queueView && queueView.playing_show && i === queueView.index ? '▶' : (i + 1)) + '</div>'
        : '';
      return '<div class=""row"">' + pos +
        '<div class=""meta""><div class=""name"">' + esc(s.name) + '</div>' +
        '<div class=""sub"">' + esc(s.artist) + (s.album ? ' · ' + esc(s.album) : '') + '</div></div>' +
        '<div class=""len"">' + len(s.length_ms) + '</div>' + right + '</div>';
    }).join('');
  }

  function loadQueue() {
    return api('/api/queue').then(function (v) {
      fail(null);
      var what = v.playing_show ? 'playing a set' :
                 v.target === 'pending' ? 'queued, waiting for the song list' : 'setlist';
      $('ctx').textContent = what + ' · ' + v.songs.length;
      if (showingQueue) render(v.songs, v);
    }).catch(function (e) { fail(e.message); });
  }

  function loadLibrary() {
    var q = $('q').value.trim();
    lastQuery = q;
    return api('/api/library?limit=100&q=' + encodeURIComponent(q)).then(function (r) {
      fail(null);
      if (!showingQueue && lastQuery === q) render(r.songs, null);
    }).catch(function (e) { fail(e.message); });
  }

  function refresh() { return showingQueue ? loadQueue() : loadLibrary(); }

  document.addEventListener('click', function (ev) {
    var add = ev.target.getAttribute && ev.target.getAttribute('data-add');
    var drop = ev.target.getAttribute && ev.target.getAttribute('data-drop');

    if (add) {
      ev.target.disabled = true;
      ev.target.textContent = 'Queued';
      api('/api/queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hash: add })
      }).then(loadQueue).catch(function (e) {
        fail(e.message);
        ev.target.disabled = false;
        ev.target.textContent = 'Queue';
      });
    }

    if (drop) {
      ev.target.disabled = true;
      api('/api/queue?hash=' + encodeURIComponent(drop), { method: 'DELETE' })
        .then(loadQueue)
        .catch(function (e) { fail(e.message); ev.target.disabled = false; });
    }
  });

  $('tabFind').addEventListener('click', function () {
    showingQueue = false;
    $('tabFind').setAttribute('aria-selected', 'true');
    $('tabQueue').setAttribute('aria-selected', 'false');
    loadLibrary();
  });

  $('tabQueue').addEventListener('click', function () {
    showingQueue = true;
    $('tabQueue').setAttribute('aria-selected', 'true');
    $('tabFind').setAttribute('aria-selected', 'false');
    loadQueue();
  });

  $('q').addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      if (showingQueue) { $('tabFind').click(); } else { loadLibrary(); }
    }, 200);
  });

  loadLibrary();
  loadQueue();
  // The TV is the source of truth; somebody else may queue something too.
  setInterval(loadQueue, 4000);
})();
</script>
</body>
</html>";
    }
}
