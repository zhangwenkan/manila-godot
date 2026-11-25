param(
    [string]$PythonExe = 'D:\Python\python.exe',
    [string]$BlenderExe = 'D:\blender5.3\blender.exe',
    [switch]$OnlineBundle,
    [switch]$ForceReinstall
)
$ErrorActionPreference = 'Stop'
$installRoot = Join-Path $env:LOCALAPPDATA 'ManilaBlenderMCP'
$venv = Join-Path $installRoot 'venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
$wheelhouse = Join-Path $PSScriptRoot '.packages'
if ($OnlineBundle) { $wheelhouse = Join-Path $PSScriptRoot '.packages-online' }
$offlineWheelhouse = 'F:\马尼拉godot\manila-codex-handoff-20261117-100405\environment\wheelhouse'
$archive = 'F:\马尼拉godot\manila-codex-handoff-20261117-100405\01-resume-core.zip'
$addonDir = Join-Path $env:APPDATA 'Blender Foundation\Blender\5.3\scripts\addons'
if (Get-Process blender -ErrorAction SilentlyContinue) { throw 'Close or inspect existing Blender sessions before changing addon preferences.' }
if (!(Test-Path -LiteralPath (Join-Path $wheelhouse 'mcp_for_blender-2.2.8-py3-none-any.whl'))) { throw 'Download the complete 2.2.8 wheel and dependencies first.' }
New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
& $PythonExe (Join-Path $PSScriptRoot 'prepare_runtime.py') $archive (Join-Path $installRoot 'python')
if ($LASTEXITCODE -ne 0) { throw 'Portable Python restoration failed.' }
$runtimePython = Join-Path $installRoot 'python\python.exe'
if (!(Test-Path -LiteralPath $venvPython)) {
    & $runtimePython -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
$pipArguments = @('-m','pip','install','--disable-pip-version-check','--no-index','--find-links',$wheelhouse)
if (!$OnlineBundle) { $pipArguments += @('--find-links',$offlineWheelhouse) }
if ($ForceReinstall) { $pipArguments += '--force-reinstall' }
$pipArguments += 'mcp-for-blender==2.2.8'
& $venvPython @pipArguments
if ($LASTEXITCODE -ne 0) { throw 'MCP package installation failed.' }
$env:DISABLE_TELEMETRY = 'true'
$env:BLENDERMCP_NO_UPDATE_CHECK = '1'
$mcpCommand = Join-Path $venv 'Scripts\mcp-for-blender.exe'
& $mcpCommand install-addon --addons-dir $addonDir
if ($LASTEXITCODE -ne 0) { throw 'Blender addon installation failed.' }
foreach ($name in @('enable_addon.py','connect_blender.py','start_blender.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $installRoot $name) -Force
}
$preferencesFile = Join-Path $env:APPDATA 'Blender Foundation\Blender\5.3\config\userpref.blend'
if (Test-Path -LiteralPath $preferencesFile) {
    Copy-Item -LiteralPath $preferencesFile -Destination ($preferencesFile + '.before-mcp-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak')
}
& $BlenderExe --background --python-exit-code 1 --python (Join-Path $installRoot 'enable_addon.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not enable Blender addon.' }
$configPath = Join-Path $env:USERPROFILE '.codex\config.toml'
if (Test-Path -LiteralPath $configPath) {
    Copy-Item -LiteralPath $configPath -Destination ($configPath + '.before-blender-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak')
}
& codex mcp add blender --env 'BLENDER_HOST=127.0.0.1' --env 'BLENDER_PORT=9879' --env 'DISABLE_TELEMETRY=true' --env 'BLENDERMCP_NO_UPDATE_CHECK=1' --env 'PYTHONUTF8=1' -- $mcpCommand
if ($LASTEXITCODE -ne 0) { throw 'Codex MCP registration failed.' }
$configText = [System.IO.File]::ReadAllText($configPath)
if ($configText -notmatch '(?m)^\[mcp_servers\.blender\]\r?$') { throw 'Expected Codex MCP section missing.' }
$configText = [regex]::Replace($configText, '(?ms)^\[mcp_servers\.blender\]\r?\n(.*?)(?=^\[|\z)', {
    param($match)
    $body = [regex]::Replace($match.Groups[1].Value, '(?m)^(startup_timeout_sec|tool_timeout_sec)\s*=.*\r?\n', '')
    return "[mcp_servers.blender]`nstartup_timeout_sec = 120`ntool_timeout_sec = 240`n" + $body
})
[System.IO.File]::WriteAllText($configPath, $configText, [System.Text.UTF8Encoding]::new($false))
Write-Output "MANILA_MCP_INSTALLED $installRoot"
