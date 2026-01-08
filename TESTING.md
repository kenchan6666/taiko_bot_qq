# 测试指南

本文档说明如何测试 Mika Taiko Chatbot 的当前功能。

## 当前功能状态

✅ **已完成的功能**：
- Phase 1-2: 基础设置和基础设施
- Phase 3 (US1): 核心聊天功能（5步处理链）
- Phase 4 (US2): 歌曲查询功能
- Phase 5: Temporal 工作流集成

⚠️ **测试状态**：
- 部分单元测试已实现（test_step3.py, test_song_query.py, test_activities.py, test_workflow.py）
- 缺少部分测试（test_step1.py, test_step2.py, test_step4.py）

## 快速测试（无需外部服务）

### 1. 运行基本功能测试

这个测试脚本不需要 MongoDB、Temporal 或 OpenRouter API，使用模拟数据：

```bash
poetry run python scripts/test_basic.py
```

这个脚本会测试：
- ✅ Step 1: 名称检测和内容过滤
- ✅ Step 2: 上下文检索（模拟）
- ✅ Step 3: 歌曲查询（模拟）
- ✅ Step 4: LLM 调用（模拟）
- ✅ Step 5: 印象更新（模拟）

### 2. 运行现有单元测试

```bash
# 运行所有测试
poetry run pytest

# 运行特定测试文件
poetry run pytest tests/unit/test_step3.py
poetry run pytest tests/unit/test_song_query.py
poetry run pytest tests/integration/test_workflow.py

# 运行测试并查看覆盖率
poetry run pytest --cov=src --cov-report=term-missing
```

## 完整功能测试（需要外部服务）

### 前置要求

1. **MongoDB** (必需)
   ```bash
   docker run -d -p 27017:27017 --name mongo mongo:7.0
   ```

2. **Temporal Server** (必需)
   ```bash
   # 使用 Temporal Docker Compose
   git clone https://github.com/temporalio/docker-compose.git temporal-docker
   cd temporal-docker
   docker-compose up -d
   cd ..
   ```

3. **环境变量配置**
   ```bash
   # 复制 .env.example 到 .env
   cp .env.example .env
   
   # 编辑 .env，至少需要：
   # - MONGODB_URL=mongodb://localhost:27017
   # - TEMPORAL_HOST=localhost
   # - TEMPORAL_PORT=7233
   # - OPENROUTER_API_KEY=your_key_here (可选，用于真实 LLM 调用)
   ```

### 启动服务

1. **启动 FastAPI 服务器**（终端 1）
   ```bash
   poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动 Temporal Worker**（终端 2）
   ```bash
   poetry run python src/workers/temporal_worker.py
   ```

### 测试 Webhook 端点

#### 方法 1: 使用测试脚本

```bash
poetry run python scripts/test_webhook_simple.py
```

#### 方法 2: 使用 curl

```bash
# 测试 1: 包含 "Mika" 的消息
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, 你好！",
    "images": []
  }'

# 测试 2: 不包含 "Mika" 的消息（应该不响应）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "今天天气真好",
    "images": []
  }'

# 测试 3: 歌曲查询
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, what is the BPM of 千本桜?",
    "images": []
  }'
```

#### 方法 3: 使用 Python 交互式测试

```python
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/webhook/langbot",
            json={
                "group_id": "123456789",
                "user_id": "987654321",
                "message": "Mika, 你好！",
                "images": []
            }
        )
        print(response.json())

asyncio.run(test())
```

## 测试检查清单

### 基本功能测试

- [ ] Step 1: 名称检测（"Mika", "米卡", "mika酱"）
- [ ] Step 1: 内容过滤（不当内容应被过滤）
- [ ] Step 2: 用户上下文检索
- [ ] Step 3: 歌曲查询（如果消息包含歌曲查询）
- [ ] Step 4: LLM 响应生成
- [ ] Step 5: 印象和对话保存

### Webhook 测试

- [ ] 包含 "Mika" 的消息 → 应该响应
- [ ] 不包含 "Mika" 的消息 → 不应该响应
- [ ] 歌曲查询消息 → 应该返回歌曲信息
- [ ] 速率限制 → 超过限制应返回 429

### 集成测试

- [ ] 完整工作流（从 webhook 到响应）
- [ ] Temporal 工作流执行
- [ ] 数据库持久化
- [ ] 错误处理和重试

## 常见问题

### Q: 测试失败，提示 MongoDB 连接错误

**A**: 确保 MongoDB 正在运行：
```bash
docker ps | grep mongo
# 如果没有运行，启动它：
docker run -d -p 27017:27017 --name mongo mongo:7.0
```

### Q: 测试失败，提示 Temporal 连接错误

**A**: 确保 Temporal 服务器正在运行：
```bash
# 检查 Temporal
docker ps | grep temporal

# 如果没有运行，启动它（见上面的 Temporal 设置）
```

### Q: LLM 调用失败

**A**: 
1. 检查 `.env` 文件中的 `OPENROUTER_API_KEY` 是否正确
2. 如果没有 API key，LLM 调用会失败，但其他功能仍可测试
3. 可以使用模拟的 LLM 响应进行测试

### Q: 如何跳过某些外部服务进行测试？

**A**: 使用 `scripts/test_basic.py`，它使用模拟数据，不需要外部服务。

## 下一步

完成基本测试后，可以：

1. **实现缺失的测试**：
   - `tests/unit/test_step1.py`
   - `tests/unit/test_step2.py`
   - `tests/unit/test_step4.py`
   - `tests/integration/test_basic_flow.py`

2. **添加更多集成测试**：
   - 多群组测试
   - 错误场景测试
   - 负载测试

3. **配置 LangBot**：
   - 设置 LangBot 连接到 webhook
   - 使用 ngrok 暴露本地端点
   - 测试真实的 QQ 群组交互
