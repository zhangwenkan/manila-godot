$ErrorActionPreference = 'Stop'
$handoffRoot = $PSScriptRoot
$projectRoot = Join-Path $handoffRoot 'manila-godot'
$bundlePath = Join-Path $handoffRoot 'git/git-history.bundle'
$snapshot = Get-Content -LiteralPath (Join-Path $handoffRoot 'git/snapshot.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (Test-Path -LiteralPath (Join-Path $projectRoot '.git')) { throw 'Target already has .git; no changes were made. Use the exported patches manually.' }
Get-Command git -ErrorAction Stop | Out-Null
function Invoke-CheckedGit {
    param([string[]]$Arguments)
    & git -C $projectRoot @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('Git failed: ' + ($Arguments -join ' ')) }
}
Invoke-CheckedGit -Arguments @('init')
Invoke-CheckedGit -Arguments @('fetch', $bundlePath, '+refs/*:refs/*')
if ($snapshot.branch) {
    Invoke-CheckedGit -Arguments @('symbolic-ref', 'HEAD', ('refs/heads/' + $snapshot.branch))
} else {
    Invoke-CheckedGit -Arguments @('update-ref', '--no-deref', 'HEAD', $snapshot.head)
}
Invoke-CheckedGit -Arguments @('reset', '--mixed', $snapshot.head)
$stagePatch = Join-Path $handoffRoot 'git/staged.patch'
if ((Get-Item -LiteralPath $stagePatch).Length -gt 0) {
    Invoke-CheckedGit -Arguments @('apply', '--cached', '--binary', $stagePatch)
}
$lfsSource = Join-Path $handoffRoot 'git/lfs-objects'
if (Test-Path -LiteralPath $lfsSource) {
    $lfsTarget = Join-Path $projectRoot '.git/lfs/objects'
    New-Item -ItemType Directory -Force -Path $lfsTarget | Out-Null
    Get-ChildItem -LiteralPath $lfsSource | Copy-Item -Destination $lfsTarget -Recurse
}
if ($snapshot.origin) {
    Invoke-CheckedGit -Arguments @('remote', 'add', 'origin', $snapshot.origin)
}
Invoke-CheckedGit -Arguments @('status', '--short')
Write-Host 'Git history and the saved index were restored. Working files were kept from the exported snapshot.'
