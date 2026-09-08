# This is a modified fork of YARG

**Upstream:** [YARC-Official/YARG](https://github.com/YARC-Official/YARG) — the original work,
by the YARG Community and contributors, licensed **LGPL-3.0-or-later**.

**This fork:** FatalException. Same licence, unchanged: LGPL-3.0-or-later. Every modification
here is offered under the same terms the original was given to us under, which is both the
licence's requirement and the point of it.

Kept as a file rather than a line in the README because the README is upstream's and stays that
way apart from the pointer at the top of it — a fork that quietly rewrites the original's front
page makes the two harder to diff, not easier.

## Why this exists

LGPL-3.0-or-later carries GPL-3.0 §5(a) through: a modified work must **carry prominent notices
stating that it was changed, and giving a relevant date.** That obligation is not conditional on
whether anyone downstream ever asks, and it attaches to the modified work itself rather than to
some later release process. Recording it here means the fork satisfies it from the day it started
being distributed, rather than from the day somebody remembered.

Nothing about it is grudging. Upstream's work is the reason any of this exists, and the licence
they chose is what makes building on it allowed.

## What was changed, and when

Changes are on the `dev` branch. Every one of them is in git history with a message explaining
why; this is the summary, not the record.

### Since 2026-09-07 — a native remote song source

The fork can mirror a self-hosted song library into the game, so a household can keep one copy of
its songs on a server instead of one copy per machine. It is
[ADR-004](https://github.com/Coffeehedake/yarg-song-server/blob/main/docs/ADR-004-remote-song-source.md)
increment 1, and it needed **no change to YARG.Core at all**.

| Area | What was added |
|---|---|
| `Assets/Script/Song/RemoteLibrary/` | The mirror client, its status and progress reporting, and the "is this song from the server" test. New files; nothing replaced. |
| `Assets/Script/Persistent/LoadingScreen.cs` | Syncs from the server at startup, without holding startup up, and never in front of a modal. |
| `Assets/Script/Settings/` and `Assets/Script/Menu/Settings/` | A Song Server settings tab: URL, sync toggle, live status, progress, cancel. One prefab-backed row type was renamed (`IPv4SettingVisual` → `TextSettingVisual`) and generalised; its `.cs.meta` GUID was carried over so existing prefab references still resolve. |
| `Assets/Script/Menu/MusicLibrary/ViewTypes/SongViewType.cs` | Marks songs that came from the server, as a tag appended to the artist line. |
| `Assets/Script/Song/SongSearching.cs` | A `server:` search filter. |
| `Assets/Editor/` | Editor-only probes that verify the above from batchmode. Not shipped in a build. |

### Not changed

`YARG.Core` is a submodule and points at **upstream, unmodified**. Where a change there would
have helped, it is written up as a patch to hand upstream rather than applied here — see
`docs/patches/` in the server repository.

## Attribution

The upstream copyright and licence notices are untouched, in `LICENSE` and throughout the source.
Nothing in this fork claims authorship of upstream's work, and the fork's own additions are not
represented as upstream's.
