<#
.SYNOPSIS
Applies a staged YARG-FE update after the game has exited, then restarts it.

.DESCRIPTION
This exists because a running process on Windows cannot replace the files it is executing. The
game downloads, verifies and unpacks; this does the swap. See ADR-006 in yarg-song-server.

It is COPIED OUT of the install folder before it runs. Running it from inside the folder it is
about to move would be moving the ground it is standing on - PowerShell does not guarantee the
whole script is read before execution, and the current directory alone can hold a directory
handle open.

Every step is reversible until the last one. The old install is renamed aside rather than
deleted, and any failure puts it back, because a failed update that leaves no game at all is
far worse than a failed update that changes nothing.
#>
param(
    [Parameter(Mandatory = $true)][int]    $GamePid,
    [Parameter(Mandatory = $true)][string] $Marker,
    [int] $WaitSeconds = 60
)

$ErrorActionPreference = 'Stop'
Set-Location $env:TEMP          # never hold a handle inside the folder being replaced

$log = Join-Path (Split-Path $Marker) 'update-helper.log'
function Say([string]$m) {
    $line = ('{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
    Write-Output $line
    try { Add-Content -Path $log -Value $line } catch { }
}

Say "helper starting: pid=$GamePid marker=$Marker"

# 1. Wait for the game to go. Do not proceed on a timeout: swapping under a live process is
#    how you get a half-replaced install and a crash that looks like a corrupt build.
for ($i = 0; $i -lt $WaitSeconds; $i++) {
    if (-not (Get-Process -Id $GamePid -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Seconds 1
}
if (Get-Process -Id $GamePid -ErrorAction SilentlyContinue) {
    Say "ABORT: pid $GamePid is still running after $WaitSeconds seconds; nothing changed"
    exit 2
}
Say 'game has exited'

if (-not (Test-Path $Marker)) { Say "ABORT: no marker at $Marker"; exit 3 }
$m = Get-Content $Marker -Raw | ConvertFrom-Json
$staged  = $m.staged
$install = $m.install
Say "build=$($m.build) branch=$($m.branch) staged=$staged install=$install"

# 2. Refuse anything that does not look like a game. An empty or partial staging folder that
#    replaced a working install would be unrecoverable from here.
if (-not (Test-Path (Join-Path $staged 'YARG.exe'))) {
    Say "ABORT: no YARG.exe in $staged"; exit 4
}
if (-not (Test-Path (Join-Path $install 'YARG.exe'))) {
    Say "ABORT: $install does not look like a YARG install"; exit 5
}

$backup = "$install.old-b$($m.build)"
if (Test-Path $backup) { Remove-Item $backup -Recurse -Force }

# 3. The swap. Rename first so the old install still exists if the move fails.
try {
    Move-Item -LiteralPath $install -Destination $backup -Force
    Say "moved old install aside -> $backup"
} catch {
    Say "ABORT: could not move the old install: $($_.Exception.Message)"
    exit 6
}

try {
    Move-Item -LiteralPath $staged -Destination $install -Force
    Say 'new build moved into place'
} catch {
    Say "FAILED to move the new build in: $($_.Exception.Message)"
    try {
        Move-Item -LiteralPath $backup -Destination $install -Force
        Say 'rolled back; the previous build is intact'
    } catch {
        Say "ROLLBACK FAILED. The previous build is at $backup - move it back by hand."
    }
    exit 7
}

# 4. Only now is the update real. Remove the marker BEFORE relaunching, or the new build sees a
#    pending update that has already been applied and tries again on every start.
Remove-Item $Marker -Force -ErrorAction SilentlyContinue

try {
    Start-Process -FilePath (Join-Path $install 'YARG.exe') -WorkingDirectory $install
    Say 'relaunched'
} catch {
    Say "could not relaunch: $($_.Exception.Message) - the update itself is applied"
}

try {
    Remove-Item $backup -Recurse -Force
    Say 'old build deleted'
} catch {
    Say "could not delete $backup - harmless, remove it whenever"
}

Say 'done'
exit 0
