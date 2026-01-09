# PowerShell 脚本：检查 LLM (OpenRouter) 配置
# 使用方法: .\scripts\check_llm_config.ps1
# 或者: poetry run python -c "from src.config import settings; print('API Key:', 'SET' if settings.openrouter_api_key else 'NOT SET')"

Write-Host "=== 检查 OpenRouter LLM 配置 ===" -ForegroundColor Green

# 检查环境变量
$apiKey = $env:OPENROUTER_API_KEY

if ($apiKey) {
    Write-Host "`n✓ OPENROUTER_API_KEY 已设置" -ForegroundColor Green
    Write-Host "  长度: $($apiKey.Length) 字符" -ForegroundColor Cyan
    Write-Host "  前缀: $($apiKey.Substring(0, [Math]::Min(10, $apiKey.Length)))..." -ForegroundColor Cyan
} else {
    Write-Host "`n✗ OPENROUTER_API_KEY 未设置" -ForegroundColor Red
    Write-Host "`n请设置环境变量:" -ForegroundColor Yellow
    Write-Host "  `$env:OPENROUTER_API_KEY = 'sk-or-v1-...'" -ForegroundColor White
    Write-Host "`n或者在 .env 文件中添加:" -ForegroundColor Yellow
    Write-Host "  OPENROUTER_API_KEY=sk-or-v1-..." -ForegroundColor White
    exit 1
}

# 检查 .env 文件
$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match "OPENROUTER_API_KEY") {
        Write-Host "`n✓ .env 文件中包含 OPENROUTER_API_KEY" -ForegroundColor Green
    } else {
        Write-Host "`n⚠ .env 文件中未找到 OPENROUTER_API_KEY" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n⚠ .env 文件不存在" -ForegroundColor Yellow
}

# 测试 API 连接（可选）
Write-Host "`n=== 测试 OpenRouter API 连接 ===" -ForegroundColor Green
Write-Host "正在测试 API 连接..." -ForegroundColor Cyan

try {
    $testResponse = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/models" -Method Get -Headers @{
        "Authorization" = "Bearer $apiKey"
    } -TimeoutSec 10 -ErrorAction Stop
    
    Write-Host "✓ OpenRouter API 连接成功" -ForegroundColor Green
    Write-Host "  可用模型数量: $($testResponse.data.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ OpenRouter API 连接失败" -ForegroundColor Red
    Write-Host "  错误: $($_.Exception.Message)" -ForegroundColor Yellow
    
    if ($_.Exception.Message -match "401|Unauthorized") {
        Write-Host "`n提示: API Key 可能无效或已过期" -ForegroundColor Yellow
    } elseif ($_.Exception.Message -match "timeout|timed out") {
        Write-Host "`n提示: 网络连接超时，请检查网络" -ForegroundColor Yellow
    }
}

Write-Host "`n=== 检查完成 ===" -ForegroundColor Green
