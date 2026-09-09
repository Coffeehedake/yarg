using System.Text;

namespace YARG.Integration.RemoteQueue
{
    /// <summary>
    /// The page a phone gets. Embedded as a string rather than a StreamingAsset
    /// so it cannot go missing from a build, and so this whole feature stays a
    /// handful of source files with no asset or scene changes.
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
          --text:#f2f2f7; --dim:#9a9aae; --accent:#ffd23f; --ok:#4ade80; --no:#f87171; }
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
  .tabs { display:flex; gap:6px; margin-top:10px; }
  .tabs button { flex:1; padding:9px 4px; font-size:13px; border-radius:9px; cursor:pointer;
                 border:1px solid var(--line); background:var(--card); color:var(--dim); }
  .tabs button[aria-selected=true] { color:var(--bg); background:var(--accent);
                                     border-color:var(--accent); font-weight:600; }
  main { padding:10px 14px 28px; }
  .row { display:flex; align-items:center; gap:9px; padding:11px 0; border-bottom:1px solid var(--line); }
  .meta { min-width:0; flex:1; }
  .name { font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .sub  { color:var(--dim); font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .len  { color:var(--dim); font-size:13px; font-variant-numeric:tabular-nums; }
  button.act { border:1px solid var(--line); background:var(--card); color:var(--text);
               border-radius:9px; padding:9px 12px; font-size:14px; cursor:pointer; }
  button.act:active { transform:translateY(1px); }
  button.act[disabled] { opacity:.5; }
  .votes { display:flex; align-items:center; gap:4px; }
  .votes button { border:1px solid var(--line); background:var(--card); color:var(--text);
                  border-radius:8px; width:36px; height:36px; font-size:15px; cursor:pointer; }
  .score { min-width:1.9em; text-align:center; font-variant-numeric:tabular-nums; font-weight:600; }
  .score.up { color:var(--ok); } .score.down { color:var(--no); }
  .note { color:var(--dim); font-size:13px; padding:12px 0; }
  .pos { color:var(--dim); font-variant-numeric:tabular-nums; width:1.6em; text-align:right; }
  .now { color:var(--accent); }
  .err { color:#ff9a9a; padding:10px 0; font-size:14px; }
  .decide { display:flex; gap:8px; padding:0 0 12px 0; }
  .decide button { flex:1; border:1px solid var(--accent); background:transparent; color:var(--accent);
                   border-radius:9px; padding:10px; font-size:14px; font-weight:600; cursor:pointer; }
  .stage { font-size:12px; color:var(--accent); text-transform:uppercase; letter-spacing:.06em; }
</style>
</head>
<body>
<header>
  <h1>YARG <span id=""ctx"">queue</span></h1>
  <input id=""q"" type=""search"" placeholder=""Search songs, artists, albums"" autocomplete=""off"">
  <div class=""tabs"">
    <button id=""tabFind"" aria-selected=""true"">Find</button>
    <button id=""tabQueue"" aria-selected=""false"">Up next</button>
    <button id=""tabVote"" aria-selected=""false"">Suggestions</button>
  </div>
</header>
<main>
  <div id=""err"" class=""err"" hidden></div>
  <div id=""list""></div>
</main>
<script>
(function () {
  var tab = 'find', timer = null, lastQuery = null, board = null;
  var $ = function (id) { return document.getElementById(id); };

  // A voter id, kept in this browser. Enough to stop a double tap and one phone
  // voting twenty times; not enough to stop somebody who clears storage, which
  // is the right amount of ceremony for a living room.
  var voter = (function () {
    try {
      var v = localStorage.getItem('yarg-voter');
      if (!v) { v = 'v' + Math.random().toString(36).slice(2) + Date.now().toString(36);
                localStorage.setItem('yarg-voter', v); }
      return v;
    } catch (e) { return 'v' + Math.random().toString(36).slice(2); }
  })();

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
    e.hidden = false; e.textContent = msg;
  }

  function api(path, opts) {
    opts = opts || {};
    opts.headers = Object.assign({ 'X-Voter': voter }, opts.headers || {});
    return fetch(path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (body) {
        if (!r.ok) throw new Error(body.error || ('HTTP ' + r.status));
        return body;
      });
    });
  }

  function scoreEl(n) {
    var cls = n > 0 ? 'score up' : (n < 0 ? 'score down' : 'score');
    return '<div class=""' + cls + '"">' + (n > 0 ? '+' : '') + n + '</div>';
  }

  function voteButtons(hash, on, score) {
    return '<div class=""votes"">' +
      '<button data-vote=""' + esc(hash) + '"" data-on=""' + on + '"" data-dir=""down"">▼</button>' +
      scoreEl(score) +
      '<button data-vote=""' + esc(hash) + '"" data-on=""' + on + '"" data-dir=""up"">▲</button>' +
      '</div>';
  }

  function renderFind(songs) {
    var voting = board && board.voting;
    $('list').innerHTML = songs.length ? songs.map(function (s) {
      var buttons = voting
        ? '<button class=""act"" data-suggest=""' + esc(s.hash) + '"">Suggest</button>'
        : '<button class=""act"" data-add=""' + esc(s.hash) + '"">Queue</button>';
      return '<div class=""row""><div class=""meta""><div class=""name"">' + esc(s.name) + '</div>' +
        '<div class=""sub"">' + esc(s.artist) + (s.album ? ' · ' + esc(s.album) : '') + '</div></div>' +
        '<div class=""len"">' + len(s.length_ms) + '</div>' + buttons + '</div>';
    }).join('') : '<div class=""note"">No songs matched.</div>';
  }

  function renderQueue() {
    var v = board.queue, voting = board.voting;
    if (!v.songs.length) { $('list').innerHTML = '<div class=""note"">Nothing queued yet.</div>'; return; }
    $('list').innerHTML = v.songs.map(function (s, i) {
      var playing = v.playing_show && i === v.index;
      var pos = '<div class=""pos ' + (playing ? 'now' : '') + '"">' + (playing ? '▶' : (i + 1)) + '</div>';
      // Nothing already played can be voted on or removed - moving it would
      // repoint the show at a different song.
      var editable = !v.playing_show || i > v.index;
      var right = editable
        ? (voting ? voteButtons(s.hash, 'queued', s.score || 0) : '') +
          '<button class=""act"" data-drop=""' + esc(s.hash) + '"">Remove</button>'
        : '';
      return '<div class=""row"">' + pos +
        '<div class=""meta""><div class=""name"">' + esc(s.name) + '</div>' +
        '<div class=""sub"">' + esc(s.artist) + '</div></div>' + right + '</div>';
    }).join('');
  }

  function renderVote() {
    if (!board.voting) { $('list').innerHTML = '<div class=""note"">Voting is switched off on the console.</div>'; return; }
    var s = board.suggestions;
    if (!s.length) {
      $('list').innerHTML = '<div class=""note"">Nothing suggested yet. Find a song and tap Suggest — ' +
        'it needs ' + board.threshold + ' votes to get in.</div>';
      return;
    }
    $('list').innerHTML = s.map(function (n) {
      if (n.stage === 'deciding') {
        return '<div class=""row"" style=""border:none;padding-bottom:2px"">' +
          '<div class=""meta""><div class=""stage"">it’s in — where?</div>' +
          '<div class=""name"">' + esc(n.name) + '</div>' +
          '<div class=""sub"">' + esc(n.artist) + '</div></div></div>' +
          '<div class=""decide"">' +
          '<button data-decide=""' + esc(n.hash) + '"" data-choice=""next"">Play next (' +
            n.for_next + '/' + board.threshold + ')</button>' +
          '<button data-decide=""' + esc(n.hash) + '"" data-choice=""setlist"">Add to setlist (' +
            n.for_setlist + '/' + board.threshold + ')</button>' +
          '</div>';
      }
      return '<div class=""row""><div class=""meta""><div class=""name"">' + esc(n.name) + '</div>' +
        '<div class=""sub"">' + esc(n.artist) + ' · needs ' + board.threshold + '</div></div>' +
        voteButtons(n.hash, 'suggestion', n.score) + '</div>';
    }).join('');
  }

  function draw() {
    if (tab === 'queue') renderQueue();
    else if (tab === 'vote') renderVote();
  }

  function loadBoard() {
    return api('/api/board').then(function (b) {
      board = b; fail(null);
      var q = b.queue;
      var what = q.playing_show ? 'playing a set'
               : q.target === 'pending' ? 'waiting for the song list' : 'setlist';
      $('ctx').textContent = what + ' · ' + q.songs.length +
        (b.voting && b.suggestions.length ? ' · ' + b.suggestions.length + ' suggested' : '');
      draw();
    }).catch(function (e) { fail(e.message); });
  }

  function loadLibrary() {
    var q = $('q').value.trim();
    lastQuery = q;
    return api('/api/library?limit=100&q=' + encodeURIComponent(q)).then(function (r) {
      fail(null);
      if (tab === 'find' && lastQuery === q) renderFind(r.songs);
    }).catch(function (e) { fail(e.message); });
  }

  function post(path) { return api(path, { method: 'POST' }); }

  document.addEventListener('click', function (ev) {
    var t = ev.target;
    var get = function (n) { return t.getAttribute && t.getAttribute(n); };

    var suggest = get('data-suggest');
    if (suggest) {
      t.disabled = true; t.textContent = 'Suggested';
      post('/api/suggest?hash=' + encodeURIComponent(suggest))
        .then(loadBoard)
        .catch(function (e) { fail(e.message); t.disabled = false; t.textContent = 'Suggest'; });
      return;
    }

    var add = get('data-add');
    if (add) {
      t.disabled = true; t.textContent = 'Queued';
      api('/api/queue', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ hash: add }) })
        .then(loadBoard)
        .catch(function (e) { fail(e.message); t.disabled = false; t.textContent = 'Queue'; });
      return;
    }

    var vote = get('data-vote');
    if (vote) {
      post('/api/vote?hash=' + encodeURIComponent(vote) + '&on=' + get('data-on') + '&dir=' + get('data-dir'))
        .then(loadBoard).catch(function (e) { fail(e.message); });
      return;
    }

    var decide = get('data-decide');
    if (decide) {
      post('/api/decide?hash=' + encodeURIComponent(decide) + '&choice=' + get('data-choice'))
        .then(loadBoard).catch(function (e) { fail(e.message); });
      return;
    }

    var drop = get('data-drop');
    if (drop) {
      t.disabled = true;
      api('/api/queue?hash=' + encodeURIComponent(drop), { method: 'DELETE' })
        .then(loadBoard).catch(function (e) { fail(e.message); t.disabled = false; });
    }
  });

  function pick(which) {
    tab = which;
    $('tabFind').setAttribute('aria-selected', which === 'find');
    $('tabQueue').setAttribute('aria-selected', which === 'queue');
    $('tabVote').setAttribute('aria-selected', which === 'vote');
    if (which === 'find') loadLibrary(); else draw();
  }

  $('tabFind').addEventListener('click', function () { pick('find'); });
  $('tabQueue').addEventListener('click', function () { pick('queue'); });
  $('tabVote').addEventListener('click', function () { pick('vote'); });

  $('q').addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { if (tab !== 'find') pick('find'); else loadLibrary(); }, 200);
  });

  loadLibrary();
  loadBoard();
  // The console is the source of truth, and other people are voting too.
  setInterval(loadBoard, 3000);
})();
</script>
</body>
</html>";
    }
}
