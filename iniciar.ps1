$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
# Nada e baixado ao iniciar: a aplicacao funciona sem internet depois da preparacao.
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
foreach ($requiredPath in @('.venv/Scripts/python.exe', 'frontend/dist/index.html')) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw 'Execute .\preparar.ps1 antes de iniciar a aplicacao.'
    }
}
if (-not ((Test-Path -LiteralPath 'artifacts/baseline-combinado.joblib') -or (Test-Path -LiteralPath 'artifacts/baseline.joblib'))) {
    throw 'Nenhum modelo encontrado. Execute .\preparar.ps1 antes de iniciar a aplicacao.'
}
if (Test-Path -LiteralPath 'artifacts/bertimbau-sentimento/model.safetensors') {
    Write-Host 'Modelo: BERTimbau encontrado; a validacao ocorre ao iniciar (pode levar alguns segundos).'
} else {
    Write-Host 'Modelo: BERTimbau ausente; a aplicacao usara o baseline TF-IDF.' -ForegroundColor Yellow
}
Write-Host 'Opinare disponivel em http://127.0.0.1:8000' -ForegroundColor Green
Write-Host 'O modelo ativo aparece no topo do painel. Mantenha este terminal aberto; Ctrl+C encerra.'
& '.\.venv\Scripts\python.exe' -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel iniciar. Confira se a porta 8000 ja esta em uso.' }
