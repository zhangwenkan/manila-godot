param(
    [string]$BlendFile = '',
    [string]$BlenderExe = 'D:\blender5.3\blender.exe',
    [int]$Port = 9879
)
$ErrorActionPreference = 'Stop'
$installRoot = Join-Path $env:LOCALAPPDATA 'ManilaBlenderMCP'
$connector = Join-Path $installRoot 'connect_blender.py'
if (!(Test-Path -LiteralPath $connector)) { throw 'Install Blender MCP first.' }
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
    throw "Port $Port is already occupied. Verify its Blender process before reusing it."
}
$blenderArguments = @()
if ($BlendFile) {
    $BlendFile = (Resolve-Path -LiteralPath $BlendFile).Path
    $blenderArguments += '"' + $BlendFile + '"'
} else {
    $blenderArguments += '--factory-startup'
}
$blenderArguments += @('--python-exit-code', '1', '--python', ('"' + $connector + '"'))
$env:MANILA_EXPECTED_BLEND = $BlendFile
$env:MANILA_MCP_PORT = [string]$Port
$env:BLENDERMCP_NO_UPDATE_CHECK = '1'
$env:DISABLE_TELEMETRY = 'true'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logDir = Join-Path $installRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outputLog = Join-Path $logDir "blender-$stamp.log"
$errorLog = Join-Path $logDir "blender-$stamp.error.log"
$process = Start-Process -FilePath $BlenderExe -ArgumentList $blenderArguments -WindowStyle Hidden -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog -PassThru
[pscustomobject]@{Pid=$process.Id;Port=$Port;File=$BlendFile;OutputLog=$outputLog;ErrorLog=$errorLog} | ConvertTo-Json
