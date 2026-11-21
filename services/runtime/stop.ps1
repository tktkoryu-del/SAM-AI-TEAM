$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$f=Join-Path $root 'pids.json'
if(Test-Path $f){$items=Get-Content $f -Raw | ConvertFrom-Json; foreach($x in $items){Stop-Process -Id $x.pid -Force -ErrorAction SilentlyContinue}; Remove-Item $f -Force}
Write-Output 'SAM AI TEAM services stopped'