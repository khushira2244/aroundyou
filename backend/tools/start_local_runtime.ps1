$ErrorActionPreference = 'Stop'
$aroundyouBackend = Split-Path $PSScriptRoot -Parent
$aroundyouRoot = Split-Path $aroundyouBackend -Parent
$aroundyouFrontend = Join-Path $aroundyouRoot 'frontend'
$aroundyouPython = Join-Path $aroundyouBackend '.venv\Scripts\python.exe'
function AroundYou-Ready([string]$Url) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2; return $r.StatusCode -eq 200 } catch { return $false }
}
Push-Location $aroundyouBackend
try {
    if (!(AroundYou-Ready 'http://127.0.0.1:8000/health')) {
        if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8000 is occupied. No service was stopped.' }
        Start-Process -FilePath $aroundyouPython -ArgumentList '-m','uvicorn','app.main:create_app','--factory','--host','127.0.0.1','--port','8000' -WorkingDirectory $aroundyouBackend -WindowStyle Hidden -RedirectStandardOutput '.tmp/api.stdout.log' -RedirectStandardError '.tmp/api.stderr.log' | Out-Null
    }
    $aroundyouReady = $false
    for ($aroundyouAttempt = 0; $aroundyouAttempt -lt 15; $aroundyouAttempt++) {
        if (AroundYou-Ready 'http://127.0.0.1:8000/health') { $aroundyouReady = $true; break }
        Start-Sleep -Seconds 1
    }
    if (!$aroundyouReady) { throw 'FastAPI is unreachable. See backend/.tmp/api.stderr.log.' }
    if (!(AroundYou-Ready 'http://127.0.0.1:5173/')) {
        $aroundyouNode = (Get-Command node).Source
        Start-Process -FilePath $aroundyouNode -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory $aroundyouFrontend -WindowStyle Hidden -RedirectStandardOutput '.tmp/frontend.stdout.log' -RedirectStandardError '.tmp/frontend.stderr.log' | Out-Null
        for ($aroundyouAttempt = 0; $aroundyouAttempt -lt 15; $aroundyouAttempt++) {
            if (AroundYou-Ready 'http://127.0.0.1:5173/') { break }
            Start-Sleep -Seconds 1
        }
    }
    & $aroundyouPython tools/open_development_browser.py --no-browser
    if ($LASTEXITCODE -ne 0) { throw 'Local authentication preparation failed.' }
    Push-Location $aroundyouFrontend
    try {
        & node tools/verify-local-http.mjs
        if ($LASTEXITCODE -ne 0) { throw 'HTTP adapter persistence verification failed.' }
    } finally { Pop-Location }
    & $aroundyouPython tools/open_development_browser.py
    if ($LASTEXITCODE -ne 0) { throw 'Browser session opening failed.' }
    Write-Output 'React: http://127.0.0.1:5173/create/1 ; FastAPI: http://127.0.0.1:8000/docs'
    Write-Output 'No live AI calls, database reset or unrelated service changes.'
} finally { Pop-Location }
