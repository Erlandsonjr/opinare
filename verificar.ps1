$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
& '.\.venv\Scripts\ruff.exe' check backend experiments tests
if ($LASTEXITCODE -ne 0) { throw 'Verificacao de codigo falhou.' }
& '.\.venv\Scripts\python.exe' -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Os testes falharam.' }
npm.cmd run build --prefix frontend
if ($LASTEXITCODE -ne 0) { throw 'A compilacao do painel falhou.' }
Write-Host 'Verificacoes concluidas.' -ForegroundColor Green
