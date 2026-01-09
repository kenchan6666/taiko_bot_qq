# PowerShell 端到端测试脚本
# 使用方法: poetry run pwsh scripts/e2e_test.ps1

$BASE_URL = "http://localhost:8000"

Write-Host "=== E2E 测试开始 ===" -ForegroundColor Green

# 测试 1: 健康检查
Write-Host "`n1. 健康检查..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/health" -Method Get
    Write-Host "✓ 健康检查通过" -ForegroundColor Green
    $response | ConvertTo-Json
} catch {
    Write-Host "✗ 健康检查失败: $_" -ForegroundColor Red
    exit 1
}

# 测试 2: 基本消息（问候）
Write-Host "`n2. 基本消息（问候）..." -ForegroundColor Yellow
try {
    $body = @{
        group_id = "test_group_001"
        user_id = "test_user_001"
        message = "Mika, 你好！"
        images = @()
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/webhook/langbot" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✓ 基本消息处理成功" -ForegroundColor Green
    Write-Host "响应: $($response.response)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ 基本消息处理失败: $_" -ForegroundColor Red
}

# 测试 3: 意图检测 - 歌曲推荐（场景化）
Write-Host "`n3. 意图检测 - 歌曲推荐（高 BPM 场景）..." -ForegroundColor Yellow
try {
    $body = @{
        group_id = "test_group_001"
        user_id = "test_user_001"
        message = "Mika, 推荐一些高 BPM 的歌曲"
        images = @()
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/webhook/langbot" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✓ 歌曲推荐成功" -ForegroundColor Green
    Write-Host "响应: $($response.response)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ 歌曲推荐失败: $_" -ForegroundColor Red
}

# 测试 4: 歌曲查询
Write-Host "`n4. 歌曲查询..." -ForegroundColor Yellow
try {
    $body = @{
        group_id = "test_group_001"
        user_id = "test_user_001"
        message = "Mika, 千本桜的BPM是多少？"
        images = @()
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/webhook/langbot" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✓ 歌曲查询成功" -ForegroundColor Green
    Write-Host "响应: $($response.response)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ 歌曲查询失败: $_" -ForegroundColor Red
}

# 测试 5: 游戏技巧
Write-Host "`n5. 游戏技巧请求..." -ForegroundColor Yellow
try {
    $body = @{
        group_id = "test_group_001"
        user_id = "test_user_001"
        message = "Mika, 有什么游戏技巧吗？"
        images = @()
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/webhook/langbot" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✓ 游戏技巧请求成功" -ForegroundColor Green
    Write-Host "响应: $($response.response)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ 游戏技巧请求失败: $_" -ForegroundColor Red
}

# 测试 6: 新手建议（场景化）
Write-Host "`n6. 新手建议（场景化）..." -ForegroundColor Yellow
try {
    $body = @{
        group_id = "test_group_001"
        user_id = "test_user_001"
        message = "Mika, 新手怎么开始练习？"
        images = @()
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/webhook/langbot" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✓ 新手建议成功" -ForegroundColor Green
    Write-Host "响应: $($response.response)" -ForegroundColor Cyan
} catch {
    Write-Host "✗ 新手建议失败: $_" -ForegroundColor Red
}

# 测试 7: 消息过滤（无 Mika 提及）
Write-Host "`n7. 消息过滤（无 Mika 提及）..." -ForegroundColor Yellow
try {
    $body = @{
        group_id = "test_group_001"
        user_id = "test_user_001"
        message = "今天天气不错"
        images = @()
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/webhook/langbot" -Method Post -Body $body -ContentType "application/json"
    Write-Host "✓ 消息过滤成功（应该被过滤）" -ForegroundColor Green
    if ($response.response) {
        Write-Host "响应: $($response.response)" -ForegroundColor Cyan
    } else {
        Write-Host "消息被正确过滤（无响应）" -ForegroundColor Cyan
    }
} catch {
    Write-Host "✗ 消息过滤测试失败: $_" -ForegroundColor Red
}

Write-Host "`n=== E2E 测试完成 ===" -ForegroundColor Green
Write-Host "`n提示: 查看 FastAPI 和 Temporal Worker 日志以获取详细信息" -ForegroundColor Yellow
