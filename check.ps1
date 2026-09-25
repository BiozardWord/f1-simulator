# check.ps1 - Verificacao do projeto F1 Simulator
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  F1 Simulator - Verificacao de Qualidade" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/2] basedpyright (strict)..." -ForegroundColor Yellow
$pyright = python -m basedpyright 2>&1
$pyrightExit = $LASTEXITCODE
if ($pyrightExit -eq 0) {
    Write-Host "  OK - basedpyright: 0 errors, 0 warnings" -ForegroundColor Green
} else {
    Write-Host "  FALHOU - basedpyright:" -ForegroundColor Red
    Write-Host $pyright
}

Write-Host ""
Write-Host "[2/2] pytest..." -ForegroundColor Yellow
$pytest = python -m pytest tests/ -q 2>&1
$pytestExit = $LASTEXITCODE
if ($pytestExit -eq 0) {
    $resumo = $pytest | Select-String -Pattern "passed|failed" | Select-Object -Last 1
    Write-Host "  OK - pytest: $resumo" -ForegroundColor Green
} else {
    Write-Host "  FALHOU - pytest:" -ForegroundColor Red
    Write-Host $pytest
}

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
if ($pyrightExit -eq 0 -and $pytestExit -eq 0) {
    Write-Host "  TUDO OK - pode fazer commit!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  FALHAS DETECTADAS - corrija antes do commit" -ForegroundColor Red
    exit 1
}
