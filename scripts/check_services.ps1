# PowerShell 服务状态检查脚本
# 使用方法: poetry run pwsh scripts/check_services.ps1

Write-Host "=== 服务状态检查 ===" -ForegroundColor Green

$allOk = $true

# 检查 Docker
Write-Host "`n[1] Docker..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "  ✓ Docker 正在运行" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker 未运行" -ForegroundColor Red
    $allOk = $false
}

# 检查 MongoDB
Write-Host "`n[2] MongoDB..." -ForegroundColor Yellow
try {
    $result = docker exec mika_bot_mongodb mongosh --eval "db.adminCommand('ping')" --quiet 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ MongoDB 运行正常 (localhost:27017)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MongoDB 未运行或未就绪" -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host "  ✗ MongoDB 容器不存在或未运行" -ForegroundColor Red
    $allOk = $false
}

# 检查 Temporal
Write-Host "`n[3] Temporal Server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8088" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "  ✓ Temporal Web UI 可访问 (http://localhost:8088)" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ Temporal Web UI 不可访问" -ForegroundColor Red
    $allOk = $false
}

# 检查 FastAPI
Write-Host "`n[4] FastAPI..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction Stop
    if ($response.status -eq "healthy") {
        Write-Host "  ✓ FastAPI 运行正常 (http://localhost:8000)" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ FastAPI 未运行或不可访问" -ForegroundColor Red
    $allOk = $false
}

# 检查 Worker（通过检查进程）
Write-Host "`n[5] Temporal Worker..." -ForegroundColor Yellow
$workerProcess = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*temporal_worker*"
}
if ($workerProcess) {
    Write-Host "  ✓ Worker 进程正在运行" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Worker 进程未检测到（可能在其他终端运行）" -ForegroundColor Yellow
}

# 检查 ngrok（通过检查进程）
Write-Host "`n[6] ngrok..." -ForegroundColor Yellow
$ngrokProcess = Get-Process ngrok -ErrorAction SilentlyContinue
if ($ngrokProcess) {
    Write-Host "  ✓ ngrok 进程正在运行" -ForegroundColor Green
    Write-Host "    提示: 查看 ngrok 终端获取 HTTPS URL" -ForegroundColor Cyan
} else {
    Write-Host "  ⚠ ngrok 未运行（可选，仅用于 QQ 测试）" -ForegroundColor Yellow
}

# 总结
Write-Host "`n=== 检查总结 ===" -ForegroundColor Green
if ($allOk) {
    Write-Host "  ✓ 核心服务运行正常" -ForegroundColor Green
} else {
    Write-Host "  ✗ 部分服务未运行，请检查" -ForegroundColor Red
    Write-Host "`n提示: 运行 'poetry run pwsh scripts/start_services.ps1' 启动 Docker 服务" -ForegroundColor Yellow
}
