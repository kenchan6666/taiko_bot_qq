# PowerShell 启动脚本
# 使用方法: poetry run pwsh scripts/start_services.ps1

Write-Host "=== 启动 Mika Bot 服务 ===" -ForegroundColor Green

# 检查 Docker 是否运行
Write-Host "`n[1/4] 检查 Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "  ✓ Docker 正在运行" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查 docker-compose 是否可用
Write-Host "`n[2/4] 检查 docker-compose..." -ForegroundColor Yellow
try {
    docker compose version | Out-Null
    Write-Host "  ✓ docker-compose 可用" -ForegroundColor Green
} catch {
    Write-Host "  ✗ docker-compose 不可用" -ForegroundColor Red
    exit 1
}

# 启动 Docker 服务
Write-Host "`n[3/4] 启动 Docker 服务 (MongoDB, Temporal, PostgreSQL)..." -ForegroundColor Yellow
$composeFile = Join-Path $PSScriptRoot "..\docker-compose.yml"
docker compose -f $composeFile up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Docker 服务启动成功" -ForegroundColor Green
} else {
    Write-Host "  ✗ Docker 服务启动失败" -ForegroundColor Red
    exit 1
}

# 等待服务就绪
Write-Host "`n[4/4] 等待服务就绪..." -ForegroundColor Yellow
Write-Host "  等待 MongoDB..." -ForegroundColor Cyan
$maxRetries = 30
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    try {
        $result = docker exec mika_bot_mongodb mongosh --eval "db.adminCommand('ping')" --quiet 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ MongoDB 就绪" -ForegroundColor Green
            break
        }
    } catch {
        # 继续等待
    }
    Start-Sleep -Seconds 2
    $retryCount++
    Write-Host "    ... ($retryCount/$maxRetries)" -ForegroundColor Gray
}

if ($retryCount -ge $maxRetries) {
    Write-Host "  ⚠ MongoDB 可能未完全就绪，但继续..." -ForegroundColor Yellow
}

Write-Host "  等待 Temporal..." -ForegroundColor Cyan
Start-Sleep -Seconds 10  # Temporal 需要更多时间启动

# 显示服务状态
Write-Host "`n=== 服务状态 ===" -ForegroundColor Green
docker compose -f $composeFile ps

Write-Host "`n=== 服务信息 ===" -ForegroundColor Green
Write-Host "  MongoDB:    mongodb://localhost:27017" -ForegroundColor Cyan
Write-Host "  Temporal:  http://localhost:8088 (Web UI)" -ForegroundColor Cyan
Write-Host "  Temporal:  localhost:7233 (gRPC)" -ForegroundColor Cyan
Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor Cyan

Write-Host "`n=== 下一步 ===" -ForegroundColor Yellow
Write-Host "  1. 启动 FastAPI:    poetry run uvicorn src.api.main:app --reload" -ForegroundColor White
Write-Host "  2. 启动 Worker:     poetry run python -m src.workers.temporal_worker" -ForegroundColor White
Write-Host "  3. 启动 ngrok:      ngrok http 8000" -ForegroundColor White
Write-Host "`n提示: 使用 'poetry run pwsh scripts/stop_services.ps1' 停止服务" -ForegroundColor Gray
