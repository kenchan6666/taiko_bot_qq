# LLM (OpenRouter) 配置指南

## 问题诊断

如果收到 fallback 响应 "Don! Mika暂时无法回应，但我会尽快回来的！🥁"，通常是因为 **OpenRouter API Key 未配置**。

## 快速检查

运行以下命令检查 API Key 是否已设置：

```powershell
# 方法 1: 使用 Python 检查
poetry run python -c "from src.config import settings; print('API Key:', 'SET ✓' if settings.openrouter_api_key else 'NOT SET ✗')"

# 方法 2: 检查环境变量
echo $env:OPENROUTER_API_KEY

# 方法 3: 检查 .env 文件
Get-Content .env | Select-String "OPENROUTER"
```

## 配置步骤

### 1. 获取 OpenRouter API Key

1. 访问 https://openrouter.ai/
2. 注册账号（或登录）
3. 进入 API Keys 页面：https://openrouter.ai/keys
4. 创建新的 API Key（格式：`sk-or-v1-...`）

### 2. 设置 API Key

**方法 A: 使用 .env 文件（推荐）**

在项目根目录的 `.env` 文件中添加：

```env
OPENROUTER_API_KEY=sk-or-v1-你的API密钥
```

**方法 B: 使用环境变量（临时）**

在 PowerShell 中：

```powershell
$env:OPENROUTER_API_KEY = "sk-or-v1-你的API密钥"
```

**方法 C: 系统环境变量（永久）**

1. 打开"系统属性" → "高级" → "环境变量"
2. 在"用户变量"中添加：
   - 变量名：`OPENROUTER_API_KEY`
   - 变量值：`sk-or-v1-你的API密钥`

### 3. 验证配置

重启服务后，运行检查命令：

```powershell
poetry run python -c "from src.config import settings; print('API Key:', 'SET ✓' if settings.openrouter_api_key else 'NOT SET ✗')"
```

应该显示 `API Key: SET ✓`

### 4. 重启服务

配置完成后，需要重启服务：

1. **重启 FastAPI**（如果正在运行）：
   - 按 `Ctrl+C` 停止
   - 重新运行：`poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`

2. **重启 Temporal Worker**（如果正在运行）：
   - 按 `Ctrl+C` 停止
   - 重新运行：`poetry run python -m src.workers.temporal_worker`

## 测试 LLM 调用

配置完成后，发送一条测试消息。如果配置正确，应该收到 LLM 生成的回复而不是 fallback 响应。

## 常见问题

### Q: 为什么需要 OpenRouter API Key？

A: OpenRouter 是一个 LLM API 聚合服务，提供访问 GPT-4o 等模型的接口。需要 API Key 才能调用。

### Q: API Key 是免费的吗？

A: OpenRouter 提供免费额度，但超出后需要付费。查看 https://openrouter.ai/pricing 了解详情。

### Q: 如何查看 API 使用情况？

A: 登录 OpenRouter 账号，在 Dashboard 中查看使用量和余额。

### Q: 如果 API Key 无效会怎样？

A: LLM 调用会失败，系统会返回 fallback 响应。检查 Worker 日志中的 `llm_invocation_failed` 错误信息。

## 故障排除

如果配置了 API Key 但仍然失败：

1. **检查 Worker 日志**：
   - 查看是否有 `llm_invocation_failed` 错误
   - 错误信息会显示具体原因（如 "401 Unauthorized" 表示 API Key 无效）

2. **验证 API Key 格式**：
   - 应该以 `sk-or-v1-` 开头
   - 没有多余的空格或换行

3. **测试 API 连接**：
   ```powershell
   $apiKey = "sk-or-v1-你的API密钥"
   Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/models" -Method Get -Headers @{"Authorization" = "Bearer $apiKey"}
   ```

4. **检查网络连接**：
   - 确保可以访问 `openrouter.ai`
   - 检查防火墙设置
