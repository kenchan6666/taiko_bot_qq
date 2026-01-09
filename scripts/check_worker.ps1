# PowerShell 脚本：检查 Temporal Worker 是否在运行
# 使用方法: poetry run pwsh scripts/check_worker.ps1

Write-Host "=== 检查 Temporal Worker 状态 ===" -ForegroundColor Green

# 检查是否有 Worker 进程在运行
$workerProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*temporal_worker*" -or
    $_.CommandLine -like "*src.workers.temporal_worker*"
}

if ($workerProcesses) {
    Write-Host "`n✓ 找到 Worker 进程:" -ForegroundColor Green
    foreach ($proc in $workerProcesses) {
        Write-Host "  PID: $($proc.Id), 命令行: $($proc.CommandLine)" -ForegroundColor Cyan
    }
} else {
    Write-Host "`n✗ 未找到 Worker 进程" -ForegroundColor Red
    Write-Host "`n需要启动 Worker，运行以下命令:" -ForegroundColor Yellow
    Write-Host "  poetry run python -m src.workers.temporal_worker" -ForegroundColor White
    Write-Host "`n或者使用一键启动脚本:" -ForegroundColor Yellow
    Write-Host "  poetry run pwsh scripts/start_all.ps1" -ForegroundColor White
}

# 检查是否有后台作业
$jobsFile = Join-Path $PSScriptRoot "..\.jobs.json"
if (Test-Path $jobsFile) {
    $jobs = Get-Content $jobsFile | ConvertFrom-Json
    if ($jobs.Worker) {
        $workerJob = Get-Job -Id $jobs.Worker -ErrorAction SilentlyContinue
        if ($workerJob) {
            Write-Host "`n✓ 找到 Worker 后台作业 (ID: $($jobs.Worker))" -ForegroundColor Green
            Write-Host "  状态: $($workerJob.State)" -ForegroundColor Cyan
            Write-Host "`n查看 Worker 日志:" -ForegroundColor Yellow
            Write-Host "  Receive-Job -Job $($jobs.Worker)" -ForegroundColor White
        } else {
            Write-Host "`n✗ Worker 后台作业不存在或已停止" -ForegroundColor Red
        }
    }
}

# 检查 Temporal 服务器连接
Write-Host "`n=== 检查 Temporal 服务器连接 ===" -ForegroundColor Green
try {
    $response = Invoke-WebRequest -Uri "http://localhost:7233" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "✓ Temporal 服务器可访问" -ForegroundColor Green
} catch {
    Write-Host "✗ Temporal 服务器不可访问 (localhost:7233)" -ForegroundColor Red
    Write-Host "  请确保 Docker Compose 服务已启动:" -ForegroundColor Yellow
    Write-Host "  poetry run pwsh scripts/start_services.ps1" -ForegroundColor White
}

Write-Host "`n=== 检查完成 ===" -ForegroundColor Green
