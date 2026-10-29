param([switch]$RecriarModelo)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'

function Invoke-Checked {
    param([scriptblock]$Command, [string]$Failure)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw $Failure }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Instale o uv (https://docs.astral.sh/uv/getting-started/installation/) e execute este arquivo novamente.'
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Instale o Node.js LTS (https://nodejs.org/) e execute este arquivo novamente.'
}

Write-Host 'Preparando o ambiente Python...'
Invoke-Checked { uv sync --frozen } 'Falha ao instalar as dependencias Python.'
if ($RecriarModelo -or -not (Test-Path -LiteralPath 'artifacts/baseline.joblib')) {
    Write-Host 'Preparando os dados academicos e treinando o modelo...'
    Invoke-Checked { & '.\.venv\Scripts\python.exe' -m experiments.train } 'Falha no treinamento. Confira a conexao e a mensagem acima.'
}
Write-Host 'Preparando o painel...'
Invoke-Checked { npm.cmd ci --prefix frontend } 'Falha ao instalar o painel.'
Invoke-Checked { npm.cmd run build --prefix frontend } 'Falha ao compilar o painel.'
Write-Host ''
Write-Host 'Tudo pronto. Execute .\iniciar.ps1 e abra http://127.0.0.1:8000' -ForegroundColor Green
