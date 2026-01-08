# 手动测试流程指南

本文档提供完整的手动测试流程，不使用任何测试脚本，通过直接启动服务和发送 HTTP 请求来验证整个系统。

## 前置准备

### 1. 检查环境变量

确保 `.env` 文件已配置（我们之前已经创建）：

```bash
# 检查 .env 文件是否存在
cat .env

# 确认包含以下关键配置：
# - MONGODB_URL=mongodb://localhost:27017/
# - TEMPORAL_HOST=localhost
# - TEMPORAL_PORT=7233
# - OPENROUTER_API_KEY=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
```

### 2. 启动 MongoDB（终端 1）

```bash
# 如果 MongoDB 未运行，启动它
docker run -d -p 27017:27017 --name mongo mongo:7.0

# 验证 MongoDB 是否运行
docker ps | grep mongo
```

### 3. 启动 Temporal Server（终端 2）

```bash
# 如果还没有 Temporal Docker Compose，先克隆
git clone https://github.com/temporalio/docker-compose.git temporal-docker
cd temporal-docker
docker-compose up -d
cd ..

# 验证 Temporal 是否运行
docker ps | grep temporal
```

**注意**：如果已经克隆过 `temporal-docker`，直接进入目录运行 `docker-compose up -d` 即可。

### 4. 初始化数据库（可选，但推荐）

```bash
# 初始化数据库索引和结构
poetry run python scripts/init_database.py
```

## 启动服务

### 5. 启动 FastAPI 服务器（终端 3）

```bash
# 在项目根目录运行
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**预期输出**：
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**验证**：打开浏览器访问 `http://localhost:8000/docs` 应该能看到 FastAPI 自动生成的 API 文档。

### 6. 启动 Temporal Worker（终端 4）

```bash
# 在项目根目录运行
poetry run python src/workers/temporal_worker.py
```

**预期输出**：
```
INFO:     Temporal client connected
INFO:     Temporal worker started
INFO:     Waiting for workflows...
```

## 测试流程

### 测试 1: 健康检查（验证服务是否运行）

**PowerShell 版本**：
```powershell
# 在终端 5 或新的 PowerShell 窗口
Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing
```

**curl 版本**：
```bash
curl http://localhost:8000/docs
```

如果能看到 HTML 响应，说明 FastAPI 服务器正常运行。

### 测试 2: 发送包含 "Mika" 的消息（应该响应）

**PowerShell 版本**：
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/webhook/langbot" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"group_id": "123456789", "user_id": "987654321", "message": "Mika, 你好！", "images": []}'
```

**curl 版本**（如果安装了 curl）：
```bash
curl -X POST http://localhost:8000/webhook/langbot `
  -H "Content-Type: application/json" `
  -d '{\"group_id\": \"123456789\", \"user_id\": \"987654321\", \"message\": \"Mika, 你好！\", \"images\": []}'
```

**预期响应**：
- **状态码**: `200 OK`
- **响应体**: JSON 格式，包含 `status: "success"` 或类似字段
- **FastAPI 日志**: 应该显示请求被处理，Temporal 工作流被启动
- **Temporal Worker 日志**: 应该显示工作流执行，5 个步骤依次执行

**验证点**：
1. ✅ HTTP 响应状态码为 200
2. ✅ 响应包含 JSON 数据
3. ✅ FastAPI 日志显示请求被接收
4. ✅ Temporal Worker 日志显示工作流执行

### 测试 3: 发送不包含 "Mika" 的消息（不应该响应）

**PowerShell 版本**：
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/webhook/langbot" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"group_id": "123456789", "user_id": "987654321", "message": "今天天气真好", "images": []}'
```

**curl 版本**：
```bash
curl -X POST http://localhost:8000/webhook/langbot `
  -H "Content-Type: application/json" `
  -d '{\"group_id\": \"123456789\", \"user_id\": \"987654321\", \"message\": \"今天天气真好\", \"images\": []}'
```

**预期响应**：
- **状态码**: `200 OK` 或 `204 No Content`
- **响应体**: 可能为空或包含 `status: "ignored"`（因为消息不包含 "Mika"）
- **FastAPI 日志**: 可能显示消息被忽略（没有触发工作流）

**验证点**：
1. ✅ 系统不处理该消息（因为没有 "Mika" 触发）
2. ✅ 不会启动 Temporal 工作流

### 测试 4: 歌曲查询（包含 "Mika" + 歌曲查询）

**PowerShell 版本**：
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/webhook/langbot" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"group_id": "123456789", "user_id": "987654321", "message": "Mika, what is the BPM of 千本桜?", "images": []}'
```

**curl 版本**：
```bash
curl -X POST http://localhost:8000/webhook/langbot `
  -H "Content-Type: application/json" `
  -d '{\"group_id\": \"123456789\", \"user_id\": \"987654321\", \"message\": \"Mika, what is the BPM of 千本桜?\", \"images\": []}'
```

**预期响应**：
- **状态码**: `200 OK`
- **响应体**: JSON 格式，可能包含歌曲信息
- **Temporal Worker 日志**: 应该显示 step3 查询歌曲，step4 生成包含歌曲信息的响应

**验证点**：
1. ✅ 系统识别出歌曲查询
2. ✅ 返回歌曲信息（BPM、难度等）
3. ✅ LLM 响应包含歌曲相关信息

### 测试 5: 中文名称变体（"米卡"）

**PowerShell 版本**：
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/webhook/langbot" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"group_id": "123456789", "user_id": "987654321", "message": "米卡，帮我查一下千本桜的难度", "images": []}'
```

**curl 版本**：
```bash
curl -X POST http://localhost:8000/webhook/langbot `
  -H "Content-Type: application/json" `
  -d '{\"group_id\": \"123456789\", \"user_id\": \"987654321\", \"message\": \"米卡，帮我查一下千本桜的难度\", \"images\": []}'
```

**预期响应**：
- **状态码**: `200 OK`
- **验证点**: 系统应该识别 "米卡" 作为触发词

### 测试 6: 速率限制测试（可选）

快速发送多个请求，验证速率限制：

**PowerShell 版本**：
```powershell
# 快速发送 25 个请求（超过 20/user/min 限制）
1..25 | ForEach-Object {
  try {
    Invoke-RestMethod -Uri "http://localhost:8000/webhook/langbot" `
      -Method POST `
      -ContentType "application/json" `
      -Body "{\"group_id\": \"123456789\", \"user_id\": \"987654321\", \"message\": \"Mika, test $_\", \"images\": []}"
    Write-Host "Request $_: Success"
  } catch {
    Write-Host "Request $_: $($_.Exception.Message)"
  }
  Start-Sleep -Milliseconds 100
}
```

**Bash 版本**：
```bash
# 快速发送 25 个请求（超过 20/user/min 限制）
for i in {1..25}; do
  curl -X POST http://localhost:8000/webhook/langbot \
    -H "Content-Type: application/json" \
    -d "{\"group_id\": \"123456789\", \"user_id\": \"987654321\", \"message\": \"Mika, test $i\", \"images\": []}"
  sleep 0.1
done
```

**预期响应**：
- 前 20 个请求应该成功（200）
- 第 21-25 个请求应该返回 `429 Too Many Requests`

## 验证数据库

### 检查 MongoDB 中的数据

**PowerShell 版本**：
```powershell
# 连接到 MongoDB（在 PowerShell 中）
docker exec -it mongo mongosh

# 然后在 MongoDB shell 中执行：
# use mika_bot
# db.users.find().pretty()
# db.conversations.find().pretty()
# db.impressions.find().pretty()
# exit
```

**或者使用单行命令查询**：
```powershell
# 查看用户数量
docker exec mongo mongosh mika_bot --eval "db.users.countDocuments()"

# 查看对话数量
docker exec mongo mongosh mika_bot --eval "db.conversations.countDocuments()"

# 查看印象数量
docker exec mongo mongosh mika_bot --eval "db.impressions.countDocuments()"
```

**验证点**：
1. ✅ 用户记录已创建（hashed_user_id）
2. ✅ 对话记录已保存
3. ✅ 印象记录已更新（interaction_count 增加）

## 验证 Temporal 工作流

### 查看 Temporal UI（如果可用）

如果 Temporal 服务器配置了 UI，访问：
```
http://localhost:8088
```

在 UI 中可以查看：
- 工作流执行历史
- 活动执行状态
- 重试记录
- 错误日志

## 常见问题排查

### 问题 1: FastAPI 启动失败

**症状**: `poetry run uvicorn` 报错

**检查**：
```bash
# 检查端口是否被占用
netstat -ano | findstr :8000

# 检查 .env 文件是否存在
cat .env

# 检查依赖是否安装
poetry install
```

### 问题 2: Temporal Worker 连接失败

**症状**: `Temporal client connected` 后立即报错

**检查**：
```bash
# 检查 Temporal 服务是否运行
docker ps | grep temporal

# 检查 Temporal 端口
netstat -ano | findstr :7233

# 检查 .env 中的 Temporal 配置
cat .env | grep TEMPORAL
```

### 问题 3: MongoDB 连接失败

**症状**: FastAPI 启动时 MongoDB 连接错误

**检查**：
```bash
# 检查 MongoDB 是否运行
docker ps | grep mongo

# 检查 MongoDB 端口
netstat -ano | findstr :27017

# 测试 MongoDB 连接
docker exec -it mongo mongosh --eval "db.adminCommand('ping')"
```

### 问题 4: LLM 调用失败

**症状**: step4 活动失败，OpenRouter API 错误

**检查**：
```bash
# 检查 API key 是否正确
cat .env | grep OPENROUTER_API_KEY

# 检查网络连接
curl https://openrouter.ai/api/v1/models
```

### 问题 5: 没有响应或响应很慢

**检查**：
1. 查看 FastAPI 日志：是否有错误信息
2. 查看 Temporal Worker 日志：工作流是否在执行
3. 检查 MongoDB：数据是否正常写入
4. 检查 OpenRouter API：是否有速率限制

## 测试检查清单

完成以下检查清单，确保系统正常工作：

- [ ] MongoDB 运行正常
- [ ] Temporal Server 运行正常
- [ ] FastAPI 服务器启动成功（端口 8000）
- [ ] Temporal Worker 启动成功并连接到服务器
- [ ] 测试 1: 健康检查通过
- [ ] 测试 2: "Mika" 消息触发响应
- [ ] 测试 3: 非 "Mika" 消息被忽略
- [ ] 测试 4: 歌曲查询返回信息
- [ ] 测试 5: 中文名称变体识别
- [ ] 数据库验证: 用户、对话、印象记录已创建
- [ ] 日志验证: FastAPI 和 Temporal Worker 日志正常

## 集成测试（需要 ngrok + LangBot）

如果你已经安装了 LangBot 并想要测试真实的 QQ 集成，需要以下步骤：

### 前置条件

1. **已安装并配置 LangBot**（参考 `specs/1-mika-bot/quickstart.md`）
2. **已安装 ngrok**（下载：https://ngrok.com/download）

### 步骤 1: 启动 ngrok（新终端窗口）

```powershell
# 启动 ngrok 隧道，将本地 8000 端口暴露到公网
ngrok http 8000
```

**预期输出**：
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

**重要**：复制这个 `https://abc123.ngrok.io` URL（你的 URL 会不同），稍后需要在 LangBot 配置中使用。

### 步骤 2: 配置 LangBot

在 LangBot 配置文件中设置 webhook URL：

```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "https://abc123.ngrok.io/webhook/langbot"  # 替换为你的 ngrok URL
```

### 步骤 3: 启动所有服务

确保以下服务都在运行：

1. ✅ **MongoDB**: `docker ps | grep mongo`
2. ✅ **Temporal Server**: `docker ps | grep temporal`
3. ✅ **FastAPI**: `poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`
4. ✅ **Temporal Worker**: `poetry run python src/workers/temporal_worker.py`
5. ✅ **ngrok**: `ngrok http 8000`（显示公网 URL）
6. ✅ **LangBot**: 按照 LangBot 文档启动

### 步骤 4: 测试真实 QQ 消息

在 QQ 群中发送包含 "Mika" 的消息：

```
Mika, 你好！
```

**验证点**：
1. ✅ LangBot 接收到消息
2. ✅ LangBot 发送 webhook 到 ngrok URL
3. ✅ FastAPI 接收到请求（查看 FastAPI 日志）
4. ✅ Temporal Worker 执行工作流（查看 Worker 日志）
5. ✅ 机器人回复消息（在 QQ 群中看到回复）

### 注意事项

- **ngrok 免费版限制**：
  - URL 每次重启都会变化
  - 需要重新配置 LangBot webhook URL
  - 有连接数限制

- **ngrok 付费版**：
  - 可以设置固定域名
  - 更适合长期开发

- **替代方案**：
  - Cloudflare Tunnel (`cloudflared`)
  - localtunnel (`npx localtunnel --port 8000`)
  - serveo (`ssh -R 80:localhost:8000 serveo.net`)

## 下一步

完成手动测试后，可以：

1. **继续实现 Phase 6**: User Story 3 (Memory) - 让机器人记住用户偏好
2. **继续实现 Phase 7**: User Story 4 (Multi-Modal) - 支持图片处理
3. **继续实现 Phase 8**: LangBot Configuration - 配置真实的 QQ 集成
4. **完善测试**: 实现缺失的单元测试（T030-T033）
