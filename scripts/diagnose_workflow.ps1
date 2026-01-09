# PowerShell 工作流诊断脚本
# 使用方法: poetry run pwsh scripts/diagnose_workflow.ps1

Write-Host "=== 工作流诊断 ===" -ForegroundColor Green

$issues = @()

# 检查 1: Temporal Server
Write-Host "`n[1] 检查 Temporal Server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8088" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ Temporal Server 运行正常 (http://localhost:8088)" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ Temporal Server 不可访问" -ForegroundColor Red
    $issues += "Temporal Server 未运行 - 运行: poetry run pwsh scripts/start_services.ps1"
}

# 检查 2: Temporal Worker 进程
Write-Host "`n[2] 检查 Temporal Worker..." -ForegroundColor Yellow
$workerProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*temporal_worker*" -or
    $_.Path -like "*temporal_worker*"
}
if ($workerProcess) {
    Write-Host "  ✓ Worker 进程正在运行 (PID: $($workerProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  ✗ Worker 进程未运行" -ForegroundColor Red
    $issues += "Temporal Worker 未运行 - 运行: poetry run python -m src.workers.temporal_worker"
}

# 检查 3: FastAPI
Write-Host "`n[3] 检查 FastAPI..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction Stop
    if ($response.status -eq "healthy") {
        Write-Host "  ✓ FastAPI 运行正常" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ FastAPI 不可访问" -ForegroundColor Red
    $issues += "FastAPI 未运行 - 运行: poetry run uvicorn src.api.main:app --reload"
}

# 检查 4: MongoDB
Write-Host "`n[4] 检查 MongoDB..." -ForegroundColor Yellow
try {
    docker exec mika_bot_mongodb mongosh --eval "db.adminCommand('ping')" --quiet 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ MongoDB 运行正常" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MongoDB 未运行或未就绪" -ForegroundColor Red
        $issues += "MongoDB 未运行 - 运行: poetry run pwsh scripts/start_services.ps1"
    }
} catch {
    Write-Host "  ✗ MongoDB 容器不存在" -ForegroundColor Red
    $issues += "MongoDB 未运行 - 运行: poetry run pwsh scripts/start_services.ps1"
}

# 检查 5: 测试工作流连接
Write-Host "`n[5] 测试 Temporal 连接..." -ForegroundColor Yellow
try {
    # 创建一个简单的 Python 脚本来测试连接
    $testScript = @"
import asyncio
from temporalio.client import Client
from src.config import settings

async def test():
    try:
        client = await Client.connect(
            target_host=f"{settings.temporal_host}:{settings.temporal_port}",
            namespace=settings.temporal_namespace,
        )
        print("✓ Temporal 连接成功")
        return True
    except Exception as e:
        print(f"✗ Temporal 连接失败: {e}")
        return False

result = asyncio.run(test())
"@
    
    $testScript | Out-File -FilePath "$env:TEMP\temporal_test.py" -Encoding UTF8
    $result = & poetry run python "$env:TEMP\temporal_test.py" 2>&1
    Remove-Item "$env:TEMP\temporal_test.py" -ErrorAction SilentlyContinue
    
    if ($result -match "✓") {
        Write-Host "  ✓ Temporal 连接成功" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Temporal 连接失败" -ForegroundColor Red
        $issues += "Temporal 连接失败 - 检查 Temporal Server 和配置"
    }
} catch {
    Write-Host "  ⚠ 无法测试连接" -ForegroundColor Yellow
}

# 总结
Write-Host "`n=== 诊断结果 ===" -ForegroundColor Green
if ($issues.Count -eq 0) {
    Write-Host "  ✓ 所有服务运行正常" -ForegroundColor Green
    Write-Host "`n如果工作流仍然失败，请检查:" -ForegroundColor Yellow
    Write-Host "  1. FastAPI 日志中的详细错误信息" -ForegroundColor White
    Write-Host "  2. Temporal Worker 日志" -ForegroundColor White
    Write-Host "  3. Temporal Web UI: http://localhost:8088" -ForegroundColor White
} else {
    Write-Host "  发现 $($issues.Count) 个问题:" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Yellow
    }
}

Write-Host "`n提示: 查看 FastAPI 终端日志获取详细的错误信息（包括 traceback）" -ForegroundColor Cyan
