param([switch]$Run)
$ErrorActionPreference = 'Stop'
$handoffRoot = $PSScriptRoot
$projectRoot = Join-Path $handoffRoot 'manila-godot'
$enginePath = Join-Path $handoffRoot 'runtime/Godot_v4.6.1-stable_win64.exe'
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'project.godot'))) { throw 'Extract 01-resume-core.zip first.' }
if (!(Test-Path -LiteralPath $enginePath)) { throw 'The bundled Godot executable is missing.' }
$env:GODOT_EXE = $enginePath
if ($Run) {
    # This launcher is explicitly run by the user to open the interactive game.
    Start-Process -FilePath $enginePath -ArgumentList @('--path', ('"' + $projectRoot + '"')) -WindowStyle Normal
} else {
    Start-Process -FilePath $enginePath -ArgumentList @('--editor', '--path', ('"' + $projectRoot + '"')) -WindowStyle Normal
}
