param([switch]$StartReferenceBlender)
$ErrorActionPreference = 'Stop'
$handoffRoot = $PSScriptRoot
$pythonPath = Join-Path $handoffRoot 'runtime/python/python.exe'
$venvRoot = Join-Path $handoffRoot 'environment/.venv'
$venvPython = Join-Path $venvRoot 'Scripts/python.exe'
$mcpRoot = Join-Path $handoffRoot 'environment/blender-mcp'
$wheelRoot = Join-Path $handoffRoot 'environment/wheelhouse'
if (!(Test-Path -LiteralPath $venvPython)) {
    & $pythonPath -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the new Python environment.' }
}
& $venvPython -m pip install --no-index --find-links $wheelRoot -r (Join-Path $handoffRoot 'environment/requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Offline dependency installation failed.' }
$env:PYTHONPATH = Join-Path $mcpRoot 'src'
$env:BLENDER_MCP_PYTHON = $venvPython
$env:BLENDER_MCP_ADDON = Join-Path $mcpRoot 'addon.py'
$env:GODOT_EXE = Join-Path $handoffRoot 'runtime/Godot_v4.6.1-stable_win64.exe'
$skillSource = Join-Path $handoffRoot 'environment/skills/harbor-blender-craft'
$skillTarget = Join-Path $env:USERPROFILE '.codex/skills/harbor-blender-craft'
if (!(Test-Path -LiteralPath $skillTarget)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $skillTarget) | Out-Null
    Copy-Item -LiteralPath $skillSource -Destination $skillTarget -Recurse
}
Write-Host 'Offline tools are ready. Environment variables apply to this PowerShell session.'
Write-Host 'Existing harbor skills were preserved; the exported copy is under environment/skills.'
if ($StartReferenceBlender) {
    $blenderPath = Join-Path $handoffRoot 'runtime/blender/blender.exe'
    $projectRoot = Join-Path $handoffRoot 'manila-godot'
    $blendPath = Join-Path $projectRoot 'demo/tropical_harbor_3d/source/reference_harbor_mcp.blend'
    $bootstrapPath = Join-Path $projectRoot 'demo/tropical_harbor_3d/source/connect_reference_mcp.py'
    $existing = Get-NetTCPConnection -LocalPort 9879 -State Listen -ErrorAction SilentlyContinue
    if ($existing) { throw 'Port 9879 is already in use. Check its owner before starting Blender.' }
    Start-Process -FilePath $blenderPath -ArgumentList @(('"' + $blendPath + '"'), '--python', ('"' + $bootstrapPath + '"')) -WindowStyle Hidden
    Write-Host 'Started the saved reference file in a separate Blender process. Verify its PID and file through MCP before editing.'
}
