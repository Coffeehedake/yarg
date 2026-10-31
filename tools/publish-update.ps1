<#
.SYNOPSIS
Builds the fork, packages it, uploads it to the update server and writes the manifest.

.DESCRIPTION
Without this, "auto updater" means automatic for the player and manual for whoever builds. This
is the manual half, made repeatable.

    pwsh -NoProfile -File tools\publish-update.ps1
    pwsh -NoProfile -File tools\publish-update.ps1 -SkipBuild   # reuse the last build

The manifest's build number is read from Assets/Resources/version.txt AFTER the build, not from
a separate git call. The version file is what the player will actually report, so taking the
number from anywhere else invites a manifest that disagrees with the build it describes - and
the symptom would be a machine that updates to a build it thinks is still out of date, forever.

Refuses to publish from a dirty working tree. The version stamp names a commit, and a build
containing uncommitted changes is labelled as something it is not.
#>
param(
    [string] $Project   = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string] $OutputDir = 'C:\dev\YARG - Open Source Contributions\build\publish',
    [string] $Unity     = 'C:\Program Files\Unity\Hub\Editor\6000.3.5f2\Editor\Unity.exe',
    [string] $VaultHost = '192.168.2.7',
    [int]    $VaultPort = 8098,
    [string] $RemoteDir = '/mnt/user/YARG/updates',
    [string] $KeyFile   = "$env:USERPROFILE\.ssh\id_ed25519_vault2",
    [string] $Notes     = '',
    [switch] $SkipBuild
)

$ErrorActionPreference = 'Stop'
function Step($m) { Write-Output ("=== {0}" -f $m) }

# --- 1. the tree must be clean ------------------------------------------------------------
Step 'checking the working tree'
$dirty = & git -C $Project status --porcelain
if ($dirty) {
    Write-Output 'REFUSING: the working tree has uncommitted changes:'
    $dirty | Select-Object -First 10 | ForEach-Object { '  ' + $_ }
    Write-Output 'A build from a dirty tree carries a version stamp that names a commit it is not.'
    exit 2
}
Write-Output '  clean'

# --- 2. build ------------------------------------------------------------------------------
$exe = Join-Path $OutputDir 'YARG.exe'
if (-not $SkipBuild) {
    Step 'building (development build: a release build refuses plain http to the song server)'
    if (Test-Path $OutputDir) { Remove-Item $OutputDir -Recurse -Force }
    $log = Join-Path (Split-Path $OutputDir) 'publish-build.log'
    $cmdFile = Join-Path $env:TEMP 'yarg-publish-build.cmd'
    @(
        '@echo off'
        "set `"YARG_BUILD_OUTPUT=$exe`""
        'set "YARG_BUILD_DEVELOPMENT=1"'
        "`"$Unity`" -batchmode -nographics -projectPath `"$Project`" -logFile `"$log`" -executeMethod YARG.Editor.BuildPlayerHeadless.Run"
        "echo EXIT=%ERRORLEVEL% > `"$env:TEMP\yarg-publish-exit.txt`""
    ) | Set-Content -Path $cmdFile -Encoding ascii

    Remove-Item "$env:TEMP\yarg-publish-exit.txt" -ErrorAction SilentlyContinue
    # Win32_Process.Create, not Start-Process: see WORKSPACE.md - a bridge-spawned Unity dies.
    $null = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = "`"$cmdFile`"" }
    $deadline = (Get-Date).AddMinutes(30)
    while (-not (Test-Path "$env:TEMP\yarg-publish-exit.txt") -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 15
    }
    $code = (Get-Content "$env:TEMP\yarg-publish-exit.txt" -Raw -ErrorAction SilentlyContinue)
    Write-Output ("  unity {0}" -f ($code ?? 'TIMED OUT').Trim())
    Select-String -Path $log -Pattern '^BUILD RESULT|^BUILD INFO: result' |
        ForEach-Object { '  ' + $_.Line.Trim() }
}
if (-not (Test-Path $exe)) { Write-Output "REFUSING: no build at $exe"; exit 3 }

# --- 3. identity, from the file the PLAYER reads -------------------------------------------
Step 'reading the build identity'
$versionFile = Join-Path $Project 'Assets\Resources\version.txt'
$stamp = (Get-Content $versionFile -Raw).Trim()
if ($stamp -notmatch '^(?<branch>\S+)\s+b(?<build>\d+)\s+\((?<commit>[0-9a-fA-F]+)\)$') {
    Write-Output "REFUSING: cannot parse '$stamp' from $versionFile"
    exit 4
}
$branch = $Matches['branch']; $build = [int]$Matches['build']; $commit = $Matches['commit']
Write-Output "  $stamp  ->  branch=$branch build=$build commit=$commit"

# --- 4. package ----------------------------------------------------------------------------
Step 'packaging'
$zipName = "YARG-FE-$branch-b$build.zip"
$zip = Join-Path (Split-Path $OutputDir) $zipName
if (Test-Path $zip) { Remove-Item $zip -Force }
& 'C:\Program Files\7-Zip\7z.exe' a -tzip -mx1 -bso0 -bsp0 $zip (Join-Path $OutputDir '*') | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Output "REFUSING: 7z exited $LASTEXITCODE"; exit 5 }

$size = (Get-Item $zip).Length
$sha  = [BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash(
          [IO.File]::ReadAllBytes($zip))).Replace('-','').ToLower()
Write-Output ("  {0}  {1} MB  sha256 {2}" -f $zipName, [int]($size/1MB), $sha.Substring(0,16))

# --- 5. upload -----------------------------------------------------------------------------
Step 'uploading'
Import-Module Posh-SSH -ErrorAction Stop
$cred = New-Object PSCredential('root', (ConvertTo-SecureString 'x' -AsPlainText -Force))
Set-SCPItem -ComputerName $VaultHost -Credential $cred -KeyFile $KeyFile -AcceptKey -Force `
    -Path $zip -Destination $RemoteDir | Out-Null
Write-Output "  uploaded to ${VaultHost}:$RemoteDir/$zipName"

# --- 6. manifest, written only AFTER the zip is in place -----------------------------------
# Order matters: a manifest pointing at a zip that is still uploading is a client error that
# looks like a corrupt build.
Step 'writing the manifest'
$manifest = [ordered]@{
    branch = $branch
    build  = $build
    commit = $commit
    url    = "http://${VaultHost}:$VaultPort/$zipName"
    sha256 = $sha
    size   = $size
    notes  = if ($Notes) { $Notes } else { "$branch b$build ($commit)" }
} | ConvertTo-Json

$session = New-SSHSession -ComputerName $VaultHost -Credential $cred -KeyFile $KeyFile -AcceptKey -Force
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($manifest))
$null = Invoke-SSHCommand -SSHSession $session `
    -Command "echo $b64 | base64 -d > $RemoteDir/$branch.json && chmod 644 $RemoteDir/$branch.json"

# --- 7. verify over HTTP, as a client would ------------------------------------------------
Step 'verifying from here, over HTTP'
$manifestUrl = "http://${VaultHost}:$VaultPort/$branch.json"
$served = Invoke-RestMethod -Uri $manifestUrl -TimeoutSec 10
Write-Output ("  manifest: branch={0} build={1} size={2}" -f $served.branch, $served.build, $served.size)
Write-Output ("  manifest matches what we published: {0}" -f
    (($served.build -eq $build) -and ($served.sha256 -eq $sha)))

$head = Invoke-WebRequest -Uri $served.url -Method Head -TimeoutSec 15 -UseBasicParsing
$servedLen = [int64]$head.Headers['Content-Length'][0]
Write-Output ("  zip is served: HTTP {0}, Content-Length {1}" -f $head.StatusCode, $servedLen)
Write-Output ("  served length matches the file we hashed: {0}" -f ($servedLen -eq $size))

Write-Output ''
Write-Output "Point the game's Update Server URL at: $manifestUrl"
