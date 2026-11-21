$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$startup = [Environment]::GetFolderPath('Startup')
if (-not (Test-Path $startup)) { throw "Current-user Startup folder not found: $startup" }
$target = Join-Path $startup 'SAM AI TEAM.lnk'
$launcher = Join-Path $root 'startup-launch.ps1'
if (-not (Test-Path $launcher)) { throw "Launcher not found: $launcher" }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($target)
$shortcut.TargetPath = (Get-Command powershell.exe).Source
$shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $launcher + '"'
$shortcut.WorkingDirectory = $root
$shortcut.Description = 'Start SAM AI TEAM workers after this Windows user signs in'
$shortcut.Save()
if (-not (Test-Path $target)) { throw 'Startup shortcut was not created.' }
Write-Output "STARTUP_SHORTCUT_CREATED=$target"