# PowerShell 脚本：验证 OpenRouter API Key
# 使用方法: .\scripts\verify_api_key.ps1

Write-Host "=== 验证 OpenRouter API Key ===" -ForegroundColor Green

# 从 .env 文件读取
$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envFile) {
    Write-Host "`n检查 .env 文件..." -ForegroundColor Cyan
    $envContent = Get-Content $envFile -Raw
    
    if ($envContent -match "OPENROUTER_API_KEY\s*=\s*(.+)") {
        $apiKeyFromEnv = $matches[1].Trim()
        Write-Host "✓ 在 .env 文件中找到 API Key" -ForegroundColor Green
        Write-Host "  长度: $($apiKeyFromEnv.Length) 字符" -ForegroundColor Cyan
        Write-Host "  前缀: $($apiKeyFromEnv.Substring(0, [Math]::Min(20, $apiKeyFromEnv.Length)))..." -ForegroundColor Cyan
        
        # 检查格式
        if ($apiKeyFromEnv -match "^\s*sk-or-v1-") {
            Write-Host "  ✓ 格式正确 (以 sk-or-v1- 开头)" -ForegroundColor Green
        } else {
            Write-Host "  ✗ 格式可能不正确 (应该以 sk-or-v1- 开头)" -ForegroundColor Red
        }
        
        # 检查是否有空格或换行
        if ($apiKeyFromEnv -match "\s") {
            Write-Host "  ⚠ 警告: API Key 包含空格或换行符" -ForegroundColor Yellow
            Write-Host "    请确保 API Key 是单行，没有多余的空格" -ForegroundColor Yellow
        }
        
        # 检查长度（通常 OpenRouter API Key 长度在 60-80 字符之间）
        if ($apiKeyFromEnv.Length -lt 50) {
            Write-Host "  ⚠ 警告: API Key 长度较短，可能不完整" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "✗ .env 文件中未找到 OPENROUTER_API_KEY" -ForegroundColor Red
    }
} else {
    Write-Host "✗ .env 文件不存在" -ForegroundColor Red
}

# 检查环境变量
Write-Host "`n检查环境变量..." -ForegroundColor Cyan
if ($env:OPENROUTER_API_KEY) {
    Write-Host "✓ 环境变量 OPENROUTER_API_KEY 已设置" -ForegroundColor Green
    Write-Host "  长度: $($env:OPENROUTER_API_KEY.Length) 字符" -ForegroundColor Cyan
} else {
    Write-Host "✗ 环境变量 OPENROUTER_API_KEY 未设置" -ForegroundColor Red
}

Write-Host "`n=== 建议 ===" -ForegroundColor Yellow
Write-Host "1. 访问 https://openrouter.ai/keys 检查 API Key 状态" -ForegroundColor White
Write-Host "2. 如果 API Key 无效，创建新的 API Key" -ForegroundColor White
Write-Host "3. 确保 .env 文件中的 API Key:" -ForegroundColor White
Write-Host "   - 是完整的（没有截断）" -ForegroundColor White
Write-Host "   - 没有多余的空格或换行" -ForegroundColor White
Write-Host "   - 格式: OPENROUTER_API_KEY=sk-or-v1-..." -ForegroundColor White
Write-Host "4. 更新后重启 FastAPI 和 Worker" -ForegroundColor White
