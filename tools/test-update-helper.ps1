<#
.SYNOPSIS
Exercises Assets/StreamingAssets/update/yarg-update.ps1 against throwaway folders.

.DESCRIPTION
The helper is the only part of the self-update feature that can destroy a working install, and
it is the part no unit test reaches. So it gets tested against fake installs here, where being
wrong costs nothing.

Three paths, because the two that refuse matter as much as the one that works:
  1. the swap succeeds, the new build is in place, the backup is gone and the marker is removed
  2. a staging folder with no YARG.exe is REFUSED and the install is untouched
  3. a game process that will not exit means the helper changes nothing at all

Run:  pwsh -NoProfile -File tools\test-update-helper.ps1
Exit 0 means every case held.
#>
$ErrorActionPreference = 'Continue'

$helper = Join-Path $PSScriptRoot '..\Assets\StreamingAssets\update\yarg-update.ps1'
$helper = [IO.Path]::GetFullPath($helper)
if (-not (Test-Path $helper)) { Write-Output "no helper at $helper"; exit 1 }

$root = Join-Path $env:TEMP 'yarg-update-helper-test'
$failures = 0

# Reads a build marker without throwing when the file is absent. A missing file IS the
# failure in several of these cases, and an assertion that throws reports it as a crashed
# test rather than as the defect it found - which is how the red-proof run came out
# unreadable the first time.
function Get-BuildTag([string]$installPath) {
    $f = Join-Path $installPath 'which-build.txt'
    if (-not (Test-Path $f)) { return '<missing>' }
    return (Get-Content $f -Raw).Trim()
}

function Check([string]$what, [bool]$ok) {
    Write-Output ("  {0}  {1}" -f $(if ($ok) { 'pass' } else { 'FAIL' }), $what)
    if (-not $ok) { $script:failures++ }
}

function New-FakeInstall([string]$path, [string]$marker) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    # A real executable so the helper's relaunch is genuinely exercised. hostname.exe prints
    # a line and exits, which is the cheapest honest stand-in for a game.
    Copy-Item 'C:\Windows\System32\hostname.exe' (Join-Path $path 'YARG.exe') -Force
    Set-Content -Path (Join-Path $path 'which-build.txt') -Value $marker
}

function Reset-Scratch {
    # Case 1 ends by RELAUNCHING the fake game, and that process holds a handle on the very
    # YARG.exe the next case wants to overwrite. Without this wait the setup fails silently and
    # the following assertions read leftovers from the previous case - a pass that comes from
    # something other than the thing under test.
    foreach ($p in Get-Process -ErrorAction SilentlyContinue) {
        try {
            if ($p.Path -and $p.Path.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
                $p.Kill()
                $p.WaitForExit(5000) | Out-Null
            }
        } catch { }
    }

    for ($i = 0; $i -lt 20 -and (Test-Path $root); $i++) {
        Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path $root) { Start-Sleep -Milliseconds 250 }
    }
    if (Test-Path $root) { throw "could not clear $root; the test cannot trust its own setup" }
    New-Item -ItemType Directory -Path $root -Force | Out-Null
}

function Write-Marker([string]$markerPath, [string]$staged, [string]$install, [int]$build) {
    $o = [ordered]@{ build = $build; branch = 'dev'; commit = 'deadbee'
                     staged = $staged; install = $install }
    $o | ConvertTo-Json | Set-Content -Path $markerPath -Encoding utf8
}

# A process that exits on its own, standing in for the game closing.
function Start-ShortLivedGame([int]$seconds) {
    (Start-Process -FilePath 'powershell.exe' `
        -ArgumentList '-NoProfile', '-Command', "Start-Sleep -Seconds $seconds" `
        -PassThru -WindowStyle Hidden)
}

Write-Output '=== 1. the swap succeeds ==='
Reset-Scratch
$install = Join-Path $root 'install'
$staged  = Join-Path $root 'staged'
$marker  = Join-Path $root 'update-pending.json'
New-FakeInstall $install 'OLD'
New-FakeInstall $staged  'NEW'
Write-Marker $marker $staged $install 4181
$game = Start-ShortLivedGame 3
& $helper -GamePid $game.Id -Marker $marker -WaitSeconds 30 | Out-Null
$rc = $LASTEXITCODE
Check 'helper exits 0'                  ($rc -eq 0)
Check 'the new build is in place'       ((Get-BuildTag $install) -eq 'NEW')
Check 'the staging folder is gone'      (-not (Test-Path $staged))
Check 'the backup was cleaned up'       (-not (Test-Path "$install.old-b4181"))
Check 'the marker was removed'          (-not (Test-Path $marker))

Write-Output '=== 2. a staging folder with no YARG.exe is refused ==='
Reset-Scratch
$install = Join-Path $root 'install'
$staged  = Join-Path $root 'staged'
$marker  = Join-Path $root 'update-pending.json'
New-FakeInstall $install 'OLD'
New-Item -ItemType Directory -Path $staged -Force | Out-Null
Set-Content -Path (Join-Path $staged 'junk.txt') -Value 'not a game'
Write-Marker $marker $staged $install 4182
$game = Start-ShortLivedGame 2
& $helper -GamePid $game.Id -Marker $marker -WaitSeconds 30 | Out-Null
$rc = $LASTEXITCODE
Check 'helper refuses with exit 4'      ($rc -eq 4)
Check 'the install is untouched'        ((Get-BuildTag $install) -eq 'OLD')
Check 'YARG.exe is still there'         (Test-Path (Join-Path $install 'YARG.exe'))
Check 'the marker survives for a retry' (Test-Path $marker)

Write-Output '=== 3. a game that will not exit changes nothing ==='
Reset-Scratch
$install = Join-Path $root 'install'
$staged  = Join-Path $root 'staged'
$marker  = Join-Path $root 'update-pending.json'
New-FakeInstall $install 'OLD'
New-FakeInstall $staged  'NEW'
Write-Marker $marker $staged $install 4183
$game = Start-ShortLivedGame 60
& $helper -GamePid $game.Id -Marker $marker -WaitSeconds 3 | Out-Null
$rc = $LASTEXITCODE
Check 'helper aborts with exit 2'       ($rc -eq 2)
Check 'the install is untouched'        ((Get-BuildTag $install) -eq 'OLD')
Check 'the staged build is still staged' (Test-Path (Join-Path $staged 'YARG.exe'))
Stop-Process -Id $game.Id -Force -ErrorAction SilentlyContinue

Write-Output '=== 4. a HELD install folder still updates, via the contents swap ==='
# This is the case MSI actually hit: the install folder could not be renamed because something
# held it - it sits inside an SMB share - while its children were perfectly free. A process
# whose current directory is the folder reproduces that exactly. Takes ~30s because the helper
# retries the rename before falling back.
Reset-Scratch
$install = Join-Path $root 'install'
$staged  = Join-Path $root 'staged'
$marker  = Join-Path $root 'update-pending.json'
New-FakeInstall $install 'OLD'
New-FakeInstall $staged  'NEW'
Write-Marker $marker $staged $install 4187
$game = Start-ShortLivedGame 2
$holder = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList '-NoProfile', '-Command', 'Start-Sleep -Seconds 120' `
    -WorkingDirectory $install -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 1
& $helper -GamePid $game.Id -Marker $marker -WaitSeconds 30 | Out-Null
$rc = $LASTEXITCODE
Stop-Process -Id $holder.Id -Force -ErrorAction SilentlyContinue
Check 'helper still exits 0'            ($rc -eq 0)
Check 'the new build is in place'       ((Get-BuildTag $install) -eq 'NEW')
Check 'the install folder was not moved' (Test-Path $install)
Check 'the marker was removed'          (-not (Test-Path $marker))

Reset-Scratch
Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue

Write-Output ''
if ($failures -eq 0) { Write-Output 'RESULT: PASS'; exit 0 }
Write-Output "RESULT: FAIL ($failures case(s))"
exit 1
