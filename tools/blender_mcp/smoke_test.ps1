param([string]$BlendFile = '')
$ErrorActionPreference = 'Stop'
$installRoot = Join-Path $env:LOCALAPPDATA 'ManilaBlenderMCP'
$python = Join-Path $installRoot 'venv\Scripts\python.exe'
$reportDir = Join-Path $PSScriptRoot '.logs'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$beforeHash = if ($BlendFile) { (Get-FileHash -LiteralPath $BlendFile -Algorithm SHA256).Hash } else { '' }
$launch = (& (Join-Path $installRoot 'start_blender.ps1') -BlendFile $BlendFile) | ConvertFrom-Json
$deadline = (Get-Date).AddSeconds(50)
do {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $launch.Port -ErrorAction SilentlyContinue
    if ($listener) { break }
    if (!(Get-Process -Id $launch.Pid -ErrorAction SilentlyContinue)) {
        Get-Content -LiteralPath $launch.OutputLog,$launch.ErrorLog
        throw 'Independent Blender process exited before MCP became ready.'
    }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)
if (!$listener -or $listener.OwningProcess -ne $launch.Pid) { throw 'Expected MCP listener was not ready.' }
$report = Join-Path $reportDir 'mcp-verification.json'
$env:PYTHONUTF8 = '1'
& $python (Join-Path $PSScriptRoot 'verify_mcp.py') --pid $launch.Pid --file $BlendFile --report $report --close
if ($LASTEXITCODE -ne 0) { throw "MCP test failed; inspect PID $($launch.Pid) and logs." }
Wait-Process -Id $launch.Pid -Timeout 15 -ErrorAction SilentlyContinue
if (Get-Process -Id $launch.Pid -ErrorAction SilentlyContinue) { throw 'Verified Blender process did not close.' }
$afterHash = if ($BlendFile) { (Get-FileHash -LiteralPath $BlendFile -Algorithm SHA256).Hash } else { '' }
if ($beforeHash -ne $afterHash) { throw 'Blender source changed during read-only verification.' }
[pscustomobject]@{Passed=$true;SourceUnchanged=($beforeHash -eq $afterHash);SourceSHA256=$afterHash;BlenderProcessClosed=$true;Report=$report} | ConvertTo-Json
