# ngrok + QQ 测试指南

**目的**: 使用 ngrok 将本地服务暴露到公网，在 QQ 群中测试 Mika 机器人

---

## ✅ 前置检查清单

在开始之前，确保以下内容已完成：

- [x] **Phase 1-2**: 基础设置和配置 ✅
- [x] **Phase 3**: User Story 1 - 基础对话功能 ✅
- [x] **Phase 4**: User Story 2 - 歌曲查询功能 ✅
- [x] **Phase 5**: Temporal 集成 ✅
- [x] **Phase 6**: User Story 3 - 记忆功能 ✅
- [x] **Phase 7**: User Story 4 - 图像处理 ✅

**结论**: ✅ **所有核心功能已实现，可以进行端到端测试！**

---

## 🚀 快速启动步骤

### 步骤 1: 检查环境变量

确保 `.env` 文件已配置：

```bash
# 检查 .env 文件
cat .env

# 必须包含以下配置：
# MONGODB_URL=mongodb://localhost:27017/
# MONGODB_DATABASE=mika_bot
# TEMPORAL_HOST=localhost
# TEMPORAL_PORT=7233
# TEMPORAL_NAMESPACE=default
# OPENROUTER_API_KEY=your_key_here  # 必需，用于 LLM 调用
```

### 步骤 2: 启动 MongoDB（终端 1）

```bash
# 如果 MongoDB 未运行
docker run -d -p 27017:27017 --name mika_mongo mongo:7.0

# 验证运行状态
docker ps | grep mongo
```

### 步骤 3: 启动 Temporal Server（终端 2）

```bash
# 进入 temporal-docker 目录
cd temporal-docker

# 启动 Temporal（如果未运行）
docker-compose up -d

# 验证运行状态
docker ps | grep temporal

# 返回项目根目录
cd ..
```

**验证**: 访问 `http://localhost:8088` 应该能看到 Temporal Web UI

### 步骤 4: 启动 FastAPI 服务器（终端 3）

```bash
# 在项目根目录运行
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

**验证**: 
- 打开浏览器访问 `http://localhost:8000/docs` 查看 API 文档
- 访问 `http://localhost:8000/health` 检查健康状态

### 步骤 5: 启动 Temporal Worker（终端 4）

```bash
# 在项目根目录运行（新终端）
poetry run python -m src.workers.temporal_worker
```

**预期输出**:
```
INFO: Temporal worker started
INFO: Registered workflow: process_message_workflow
INFO: Registered activities: step1_parse_input, step2_retrieve_context, ...
INFO: Worker listening on task queue: mika-bot-task-queue
```

### 步骤 6: 启动 ngrok（终端 5）

```bash
# 安装 ngrok（如果未安装）
# Windows: 从 https://ngrok.com/download 下载
# macOS: brew install ngrok
# Linux: 从 https://ngrok.com/download 下载

# 启动 ngrok 隧道（将本地 8000 端口暴露到公网）
ngrok http 8000
```

**预期输出**:
```
ngrok

Session Status                online
Account                       Your Account
Version                       3.x.x
Region                        Asia Pacific (ap)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**重要**: 复制 `Forwarding` 中的 HTTPS URL（例如：`https://abc123.ngrok.io`）

**验证**: 
- 访问 `http://127.0.0.1:4040` 查看 ngrok Web UI
- 在浏览器中访问 `https://your-ngrok-url.ngrok.io/docs` 应该能看到 FastAPI 文档

### 步骤 7: 配置 LangBot Webhook

根据 LangBot 的配置方式，将 webhook URL 设置为：

```
https://your-ngrok-url.ngrok.io/webhook/langbot
```

**注意**: 
- 使用 HTTPS URL（ngrok 自动提供）
- 确保路径是 `/webhook/langbot`
- 如果 ngrok 重启，URL 会变化，需要重新配置

---

## 🧪 本地测试（在配置 QQ 之前）

在配置 LangBot 之前，先测试本地 webhook 是否正常工作：

### 测试 1: 基础消息（包含 "Mika"）

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }'
```

**预期结果**: 返回 JSON，包含 `response` 字段和 `success: true`

### 测试 2: 不包含 "Mika" 的消息

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "今天天气真好",
    "images": []
  }'
```

**预期结果**: 返回 `success: false`, `response: ""`

### 测试 3: 歌曲查询

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, what is the BPM of 千本桜?",
    "images": []
  }'
```

**预期结果**: 返回包含歌曲信息的响应

### 测试 4: 通过 ngrok URL 测试

```bash
# 替换 YOUR_NGROK_URL 为实际的 ngrok URL
curl -X POST https://YOUR_NGROK_URL.ngrok.io/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }'
```

**预期结果**: 与本地测试相同

---

## 📱 QQ 群测试

### 步骤 1: 在 QQ 群中发送消息

在配置好 LangBot webhook 后，在 QQ 群中发送：

```
Mika, 你好！
```

### 步骤 2: 验证响应

**检查点**:

1. ✅ **FastAPI 日志**（终端 3）:
   ```
   INFO: webhook_received group_id=xxx user_id=xxx
   INFO: workflow_started workflow_id=xxx
   ```

2. ✅ **Temporal Worker 日志**（终端 4）:
   ```
   INFO: Activity started: step1_parse_input
   INFO: Activity completed: step1_parse_input
   INFO: Activity started: step2_retrieve_context
   ...
   ```

3. ✅ **Temporal UI** (`http://localhost:8088`):
   - 查看工作流执行历史
   - 查看活动执行状态

4. ✅ **QQ 群消息**:
   - Bot 应该回复包含 "Don!" 或 "🥁" 的消息

### 步骤 3: 测试不同功能

#### 测试歌曲查询

```
Mika, what is the BPM of 千本桜?
```

#### 测试记忆功能

```
Mika, 我喜欢高 BPM 的歌曲
```

然后：

```
Mika, 是的，我喜欢
```

最后：

```
Mika, 推荐一些歌曲给我
```

#### 测试图像处理

在 QQ 群中发送包含图片的消息：

```
Mika, 看看这张图片
[附上一张图片]
```

---

## 🔍 调试技巧

### 1. 查看 FastAPI 日志

FastAPI 会在终端 3 输出结构化 JSON 日志，查找：
- `webhook_received`: Webhook 请求已接收
- `workflow_started`: Temporal 工作流已启动
- `workflow_completed`: 工作流执行完成
- `workflow_failed`: 工作流执行失败

### 2. 查看 Temporal UI

访问 `http://localhost:8088`:
- **Workflows**: 查看所有工作流执行
- **Activities**: 查看活动执行状态
- **Retries**: 查看重试情况

### 3. 查看 ngrok 请求

访问 `http://127.0.0.1:4040`:
- **Requests**: 查看所有通过 ngrok 的请求
- **Replay**: 重放请求进行调试

### 4. 检查 MongoDB

```bash
# 连接到 MongoDB
mongosh mongodb://localhost:27017/mika_bot

# 查看最近的对话
db.conversations.find().sort({timestamp: -1}).limit(5).pretty()

# 查看用户印象
db.impressions.find().pretty()
```

### 5. 常见问题排查

#### Bot 不响应

1. ✅ 检查消息是否包含 "Mika" 或 "米卡"
2. ✅ 检查 FastAPI 是否运行（终端 3）
3. ✅ 检查 Temporal Worker 是否运行（终端 4）
4. ✅ 检查 ngrok 是否运行（终端 5）
5. ✅ 检查 LangBot webhook URL 是否正确
6. ✅ 查看 FastAPI 日志中的错误

#### ngrok URL 变化

- **问题**: ngrok 免费版每次重启 URL 都会变化
- **解决**: 
  - 使用 ngrok 付费版设置固定域名
  - 或使用 `cloudflared` 等其他工具
  - 或每次重启后重新配置 LangBot webhook

#### Temporal Worker 未处理工作流

1. ✅ 检查 Temporal Server 是否运行
2. ✅ 检查 Worker 是否连接到正确的 Task Queue
3. ✅ 查看 Worker 日志中的错误
4. ✅ 检查 Temporal UI 中的工作流状态

---

## 📊 服务状态检查清单

在开始测试前，确保所有服务都在运行：

- [ ] **MongoDB**: `docker ps | grep mongo`
- [ ] **Temporal Server**: `docker ps | grep temporal`
- [ ] **FastAPI**: `curl http://localhost:8000/health`
- [ ] **Temporal Worker**: 查看终端 4 日志
- [ ] **ngrok**: 访问 `http://127.0.0.1:4040` 查看状态
- [ ] **LangBot**: 根据 LangBot 文档检查状态

---

## 🎯 下一步

完成测试后，可以：

1. **优化性能**: 监控响应时间，优化慢查询
2. **增强功能**: 实现更多用户故事
3. **完善测试**: 添加更多集成测试
4. **部署到生产**: 使用固定域名替代 ngrok

---

## 📝 注意事项

### ngrok 免费版限制

- ⚠️ URL 每次重启都会变化
- ⚠️ 需要重新配置 LangBot webhook
- ⚠️ 有连接数限制
- ⚠️ 不适合生产环境

### ngrok 付费版优势

- ✅ 可以设置固定域名
- ✅ 更高的连接数限制
- ✅ 更适合长期开发

### 替代方案

如果不想使用 ngrok，可以考虑：

1. **Cloudflare Tunnel** (`cloudflared`):
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```

2. **localtunnel**:
   ```bash
   npx localtunnel --port 8000
   ```

3. **serveo**:
   ```bash
   ssh -R 80:localhost:8000 serveo.net
   ```

---

**最后更新**: 2026-01-08  
**版本**: 1.0
