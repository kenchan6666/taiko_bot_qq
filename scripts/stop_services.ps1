# PowerShell 停止脚本
# 使用方法: poetry run pwsh scripts/stop_services.ps1

Write-Host "=== 停止 Mika Bot 服务 ===" -ForegroundColor Yellow

$composeFile = Join-Path $PSScriptRoot "..\docker-compose.yml"

Write-Host "`n停止 Docker 服务..." -ForegroundColor Yellow
docker compose -f $composeFile down

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ 服务已停止" -ForegroundColor Green
} else {
    Write-Host "  ✗ 停止服务时出错" -ForegroundColor Red
    exit 1
}

Write-Host "`n提示: 使用 'docker compose -f $composeFile down -v' 删除数据卷" -ForegroundColor Gray
