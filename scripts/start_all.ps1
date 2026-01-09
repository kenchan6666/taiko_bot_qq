# PowerShell 一键启动所有服务（包括 FastAPI 和 Worker）
# 使用方法: poetry run pwsh scripts/start_all.ps1

Write-Host "=== 一键启动所有服务 ===" -ForegroundColor Green

# 先启动 Docker 服务
Write-Host "`n[步骤 1] 启动 Docker 服务..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "start_services.ps1")

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n✗ Docker 服务启动失败，退出" -ForegroundColor Red
    exit 1
}

# 等待服务就绪
Write-Host "`n等待服务完全就绪..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 启动 FastAPI
Write-Host "`n[步骤 2] 启动 FastAPI..." -ForegroundColor Yellow
Write-Host "  在后台启动 FastAPI (端口 8000)..." -ForegroundColor Cyan

$fastapiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
}

Start-Sleep -Seconds 3

# 检查 FastAPI 是否启动
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ FastAPI 启动成功" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ FastAPI 可能还在启动中..." -ForegroundColor Yellow
}

# 启动 Temporal Worker
Write-Host "`n[步骤 3] 启动 Temporal Worker..." -ForegroundColor Yellow
Write-Host "  在后台启动 Worker..." -ForegroundColor Cyan

$workerJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    poetry run python -m src.workers.temporal_worker
}

Start-Sleep -Seconds 3
Write-Host "  ✓ Worker 已启动（后台运行）" -ForegroundColor Green

Write-Host "`n=== 所有服务已启动 ===" -ForegroundColor Green
Write-Host "  MongoDB:    localhost:27017" -ForegroundColor Cyan
Write-Host "  Temporal:   http://localhost:8088" -ForegroundColor Cyan
Write-Host "  FastAPI:    http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Worker:    后台运行中" -ForegroundColor Cyan

Write-Host "`n=== 下一步 ===" -ForegroundColor Yellow
Write-Host "  启动 ngrok: ngrok http 8000" -ForegroundColor White

Write-Host "`n提示:" -ForegroundColor Gray
Write-Host "  - 查看 FastAPI 日志: Receive-Job -Job $fastapiJob" -ForegroundColor Gray
Write-Host "  - 查看 Worker 日志: Receive-Job -Job $workerJob" -ForegroundColor Gray
Write-Host "  - 停止所有服务: poetry run pwsh scripts/stop_all.ps1" -ForegroundColor Gray

# 保存作业 ID 到文件，以便后续停止
$jobs = @{
    FastAPI = $fastapiJob.Id
    Worker = $workerJob.Id
}
$jobs | ConvertTo-Json | Out-File -FilePath (Join-Path $PSScriptRoot "..\.jobs.json") -Encoding UTF8
