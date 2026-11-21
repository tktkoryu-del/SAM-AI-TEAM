$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("startup-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + ".log")
Start-Transcript -Path $log -Append | Out-Null
try {
    try {
        $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/health' -TimeoutSec 3
        if ($health.online -eq 12 -and $health.total -eq 12) {
            Write-Output 'SAM AI TEAM already healthy; no duplicate processes started.'
            exit 0
        }
    } catch {}
    $portBusy = [bool](Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue)
    if ($portBusy) { throw 'Coordinator port 8787 is already occupied but health check did not pass. Manual inspection required.' }
    $ollamaReady = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2 | Out-Null
            $ollamaReady = $true
            break
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ollamaReady) { throw 'Ollama did not become ready within 120 seconds.' }
    & (Join-Path $root 'start.ps1')
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8787/health' -TimeoutSec 5
    if ($health.online -ne 12 -or $health.total -ne 12) { throw "Health check failed: $($health.online)/$($health.total) workers online." }
    Write-Output 'SAM AI TEAM startup completed: 12/12 workers online.'
} catch {
    Write-Error $_
    exit 1
} finally {
    Stop-Transcript | Out-Null
}