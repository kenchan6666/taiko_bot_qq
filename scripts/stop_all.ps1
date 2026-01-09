# PowerShell 停止所有服务
# 使用方法: poetry run pwsh scripts/stop_all.ps1

Write-Host "=== 停止所有服务 ===" -ForegroundColor Yellow

# 停止后台作业
$jobsFile = Join-Path $PSScriptRoot "..\.jobs.json"
if (Test-Path $jobsFile) {
    Write-Host "`n停止后台作业..." -ForegroundColor Yellow
    $jobs = Get-Content $jobsFile | ConvertFrom-Json
    
    if ($jobs.FastAPI) {
        Stop-Job -Id $jobs.FastAPI -ErrorAction SilentlyContinue
        Remove-Job -Id $jobs.FastAPI -ErrorAction SilentlyContinue
        Write-Host "  ✓ FastAPI 已停止" -ForegroundColor Green
    }
    
    if ($jobs.Worker) {
        Stop-Job -Id $jobs.Worker -ErrorAction SilentlyContinue
        Remove-Job -Id $jobs.Worker -ErrorAction SilentlyContinue
        Write-Host "  ✓ Worker 已停止" -ForegroundColor Green
    }
    
    Remove-Item $jobsFile -ErrorAction SilentlyContinue
}

# 停止 Docker 服务
Write-Host "`n停止 Docker 服务..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "stop_services.ps1")

Write-Host "`n✓ 所有服务已停止" -ForegroundColor Green
