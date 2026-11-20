$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$python=(Get-Command python -ErrorAction Stop).Source
$envFile=Join-Path $root '.env'
if(Test-Path $envFile){Get-Content $envFile | ForEach-Object { if($_ -match '^\s*([^#=]+)=(.*)$'){[Environment]::SetEnvironmentVariable($matches[1].Trim(),$matches[2].Trim(),'Process')} }}
$services=Get-Content (Join-Path $root 'services.json') -Raw | ConvertFrom-Json
$pids=@()
foreach($s in $services){
 $p=Start-Process -FilePath $python -ArgumentList @((Join-Path $root 'service.py'),$s.key) -WorkingDirectory $root -PassThru -WindowStyle Hidden
 $pids += [pscustomobject]@{name=$s.key;pid=$p.Id;port=$s.port}
}
Start-Sleep -Seconds 1
$c=Start-Process -FilePath $python -ArgumentList @((Join-Path $root 'coordinator.py')) -WorkingDirectory $root -PassThru -WindowStyle Hidden
$pids += [pscustomobject]@{name='coordinator';pid=$c.Id;port=8787}
$pids | ConvertTo-Json | Set-Content (Join-Path $root 'pids.json')
Start-Sleep -Seconds 2
$h=Invoke-RestMethod http://127.0.0.1:8787/health
if($h.online -ne 12){throw "Only $($h.online) of 12 workers online"}
$h | ConvertTo-Json -Depth 6