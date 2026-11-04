# Run from a normal Windows PowerShell session. Existing port 8000 is untouched.
$ErrorActionPreference = 'Stop'
$aroundyouBackend = Split-Path $PSScriptRoot -Parent
$aroundyouRoot = Split-Path $aroundyouBackend -Parent
$aroundyouFrontend = Join-Path $aroundyouRoot 'frontend'
$aroundyouPython = Join-Path $aroundyouBackend '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force (Join-Path $aroundyouBackend '.tmp') | Out-Null
New-Item -ItemType Directory -Force (Join-Path $aroundyouFrontend '.tmp') | Out-Null
function AroundYou-Ready([string]$Url) {
    try { return (Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2).StatusCode -eq 200 } catch { return $false }
}
Push-Location $aroundyouBackend
try {
    # Bind-test candidate ports; leave occupied or unresponsive services untouched.
    $aroundyouPort = $null
    foreach ($aroundyouCandidate in 8001..8010) {
        $aroundyouProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $aroundyouCandidate)
        try {
            $aroundyouProbe.Start()
            $aroundyouPort = $aroundyouCandidate
            break
        } catch [System.Net.Sockets.SocketException] {
            continue
        } finally { $aroundyouProbe.Stop() }
    }
    if ($null -eq $aroundyouPort) { throw 'No available API port between 8001 and 8010. No service was stopped.' }
    $aroundyouApi = "http://127.0.0.1:$aroundyouPort"
    Start-Process -FilePath $aroundyouPython -ArgumentList '-m','uvicorn','app.main:create_app','--factory','--host','127.0.0.1','--port',"$aroundyouPort" -WorkingDirectory $aroundyouBackend -WindowStyle Hidden -RedirectStandardOutput ".tmp/live-api-$aroundyouPort.stdout.log" -RedirectStandardError ".tmp/live-api-$aroundyouPort.stderr.log" | Out-Null
    for ($aroundyouAttempt=0; $aroundyouAttempt -lt 15; $aroundyouAttempt++) {
        if (AroundYou-Ready "$aroundyouApi/health") { break }
        Start-Sleep -Seconds 1
    }
    $aroundyouSchema = Invoke-RestMethod -Uri "$aroundyouApi/openapi.json" -TimeoutSec 5
    if ($aroundyouSchema.info.title -ne 'AroundYou Backend' -or !$aroundyouSchema.paths.'/v1/auth/signup') { throw "New API failed validation. Inspect backend/.tmp/live-api-$aroundyouPort.stderr.log." }
    # Change only the frontend API URL; preserve the Maps key and all other values.
    @'
from pathlib import Path
import re,sys
p=Path('../frontend/.env.local')
s=p.read_text(encoding='utf-8') if p.exists() else ''
for key,value in [('VITE_AROUNDYOU_MODE','http'),('VITE_AROUNDYOU_API_URL',sys.argv[1])]:
    line=key+'='+value
    s=re.sub(r'^'+key+r'=.*$',line,s,flags=re.M) if re.search(r'^'+key+r'=',s,re.M) else s.rstrip()+'\n'+line+'\n'
p.write_text(s,encoding='utf-8')
'@ | & $aroundyouPython - $aroundyouApi
    if ($LASTEXITCODE -ne 0) { throw 'Frontend environment update failed.' }
    if (!(AroundYou-Ready 'http://127.0.0.1:5173/')) {
        $aroundyouNode = (Get-Command node).Source
        Start-Process -FilePath $aroundyouNode -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory $aroundyouFrontend -WindowStyle Hidden -RedirectStandardOutput '.tmp/live-frontend.stdout.log' -RedirectStandardError '.tmp/live-frontend.stderr.log' | Out-Null
    }
    Start-Process 'http://127.0.0.1:5173/signup'
    Write-Output 'Signup: http://127.0.0.1:5173/signup'
    Write-Output 'Signin: http://127.0.0.1:5173/signin'
    Write-Output "API: $aroundyouApi/docs"
    Write-Output 'Use the same 127.0.0.1 host for frontend and API so browser cookies stay same-site.'
} finally { Pop-Location }
