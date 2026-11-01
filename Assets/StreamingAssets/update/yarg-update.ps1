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

# A process exiting does not mean its files are free. Windows releases an executable's image
# section a moment later, Defender often opens the folder to scan it the instant the process
# dies, and an install folder that sits inside an SMB share can be held by any client that
# merely listed it. Measured on MSI 2026-10-31: three consecutive runs aborted with "being
# used by another process" roughly one second after the game exited, each correctly leaving
# the install intact. Waiting is the fix; giving up on the first refusal was the bug.
function Move-WithRetry([string]$from, [string]$to, [int]$attempts = 15, [int]$delayMs = 2000) {
    for ($i = 1; $i -le $attempts; $i++) {
        try {
            Move-Item -LiteralPath $from -Destination $to -Force -ErrorAction Stop
            if ($i -gt 1) { Say "  succeeded on attempt $i" }
            return $true
        } catch {
            if ($i -eq 1 -or $i % 5 -eq 0) {
                Say ("  attempt {0}/{1}: {2}" -f $i, $attempts, $_.Exception.Message)
            }
            Start-Sleep -Milliseconds $delayMs
        }
    }
    return $false
}

# 3. The swap. Rename first so the old install still exists if the move fails.
#
# Move-Item on a directory it cannot rename falls back to COPY THEN DELETE, and reports success
# when the copy worked even if the delete did not. The source folder is then still there, and
# the next Move-Item - whose destination now exists as a directory - moves the new build INSIDE
# the old one instead of replacing it. Measured 2026-10-31: the helper logged "moved old install
# aside" and "new build moved into place", exited 0, and left which-build.txt reading OLD with a
# "staged" folder nested inside. A success that has not been verified is not a success.
$renamed = Move-WithRetry $install $backup
if ($renamed -and (Test-Path $install)) {
    Say 'the rename reported success but the old install is still there (copy-then-delete); not trusting it'
    Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue
    $renamed = $false
}

if ($renamed) {
    Say "moved old install aside -> $backup"
} else {
    Say "could not move the old install after repeated attempts; trying a contents swap instead"

    # The install FOLDER may be held while its children are free - that is what happens when
    # the folder itself is shared, or is some process's current directory. Moving the contents
    # leaves the folder in place and still restores cleanly.
    $ok = $true
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach ($child in Get-ChildItem -LiteralPath $install -Force) {
        if (-not (Move-WithRetry $child.FullName (Join-Path $backup $child.Name) 8 1500)) {
            Say "  could not move $($child.Name)"
            $ok = $false
            break
        }
    }

    if (-not $ok) {
        Say 'FAILED: putting back what had already been moved'
        foreach ($child in Get-ChildItem -LiteralPath $backup -Force) {
            [void](Move-WithRetry $child.FullName (Join-Path $install $child.Name) 8 1500)
        }
        Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue
        Say 'ABORT: the previous build is intact and nothing was changed'
        exit 6
    }

    # Contents moved out, folder still there: move the new build's contents in. $staged is
    # enumerated ONCE up front, because the loop moves items out of the folder it is reading.
    $incoming = @(Get-ChildItem -LiteralPath $staged -Force)
    foreach ($child in $incoming) {
        if (-not (Move-WithRetry $child.FullName (Join-Path $install $child.Name) 8 1500)) {
            Say "FAILED moving in $($child.Name); restoring the previous build"
            foreach ($c in Get-ChildItem -LiteralPath $install -Force) {
                Remove-Item $c.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }
            foreach ($c in Get-ChildItem -LiteralPath $backup -Force) {
                [void](Move-WithRetry $c.FullName (Join-Path $install $c.Name) 8 1500)
            }
            Say 'ABORT: rolled back'
            exit 7
        }
    }

    if (-not (Test-Path (Join-Path $install 'YARG.exe'))) {
        Say 'ABORT: the contents swap finished but there is no YARG.exe; restoring'
        foreach ($c in Get-ChildItem -LiteralPath $backup -Force) {
            [void](Move-WithRetry $c.FullName (Join-Path $install $c.Name) 8 1500)
        }
        exit 8
    }

    Remove-Item -LiteralPath $staged -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $Marker -Force -ErrorAction SilentlyContinue
    try {
        Start-Process -FilePath (Join-Path $install 'YARG.exe') -WorkingDirectory $install
        Say 'relaunched'
    } catch {
        Say "could not relaunch: $($_.Exception.Message) - the update itself is applied"
    }
    Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue
    Say 'done (contents swap)'
    exit 0
}

if (Move-WithRetry $staged $install) {
    Say 'new build moved into place'
} else {
    Say 'FAILED to move the new build in'
    if (Move-WithRetry $backup $install) {
        Say 'rolled back; the previous build is intact'
    } else {
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
