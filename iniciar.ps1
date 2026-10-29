$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
foreach ($requiredPath in @('.venv/Scripts/python.exe', 'artifacts/baseline.joblib', 'frontend/dist/index.html')) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw 'Execute .\preparar.ps1 antes de iniciar a aplicacao.'
    }
}
Write-Host 'Opinare disponivel em http://127.0.0.1:8000' -ForegroundColor Green
Write-Host 'Mantenha este terminal aberto. Use Ctrl+C para encerrar.'
& '.\.venv\Scripts\python.exe' -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel iniciar. Confira se a porta 8000 ja esta em uso.' }
