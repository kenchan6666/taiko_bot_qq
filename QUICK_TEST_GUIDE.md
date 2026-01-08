# 快速测试指南 - Mika Taiko Chatbot

**目的**: 快速验证功能，无需编写复杂脚本

---

## 🚀 快速开始

### 1. 启动服务

```bash
# 终端 1: 启动 FastAPI
poetry run uvicorn src.api.main:app --reload

# 终端 2: 启动 Temporal Worker
poetry run python -m src.workers.temporal_worker
```

### 2. 验证服务运行

打开浏览器访问: `http://localhost:8000/docs`

---

## 📝 基础功能测试

### 测试 1: 名称检测

**使用 curl**:
```bash
# 应该响应
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{"group_id":"test","user_id":"test","message":"Mika, 你好","images":[]}'

# 不应该响应
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{"group_id":"test","user_id":"test","message":"今天天气真好","images":[]}'
```

**使用 Python**:
```python
from src.steps.step1 import parse_input

# 应该成功
result1 = parse_input("123", "456", "Mika, 你好", None)
print(f"包含 Mika: {result1 is not None}")  # True

# 应该失败
result2 = parse_input("123", "456", "今天天气真好", None)
print(f"不包含 Mika: {result2 is None}")  # True
```

---

## 🖼️ 图像处理测试

### 测试 2: 创建测试图像

**使用 Python 脚本**:
```bash
poetry run python scripts/test_image_manual.py
```

**手动创建**:
```python
from PIL import Image
import io
import base64

# 创建 JPEG
img = Image.new('RGB', (100, 100), color='red')
buffer = io.BytesIO()
img.save(buffer, format='JPEG')
jpeg_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
print(f"JPEG base64: {jpeg_base64[:50]}...")
```

### 测试 3: 发送带图像的请求

**使用 curl** (替换 `YOUR_BASE64` 为实际的 base64 字符串):
```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, 看看这张图片",
    "images": ["YOUR_BASE64_HERE"]
  }'
```

**使用 Python**:
```python
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/webhook/langbot",
            json={
                "group_id": "test",
                "user_id": "test",
                "message": "Mika, 看看这张图片",
                "images": [jpeg_base64]  # 使用上面创建的 base64
            }
        )
        print(response.json())

asyncio.run(test())
```

---

## 🧠 记忆功能测试

### 测试 4: 多轮对话

**步骤**:
1. 第一次对话 - 表达偏好
```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test_user_001",
    "message": "Mika, 我喜欢高 BPM 的歌曲",
    "images": []
  }'
```

2. 第二次对话 - 确认偏好
```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test_user_001",
    "message": "Mika, 是的，我喜欢",
    "images": []
  }'
```

3. 第三次对话 - 引用记忆
```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test_user_001",
    "message": "Mika, 推荐一些歌曲",
    "images": []
  }'
```

**预期**: Bot 应该基于之前记住的偏好（高 BPM）推荐歌曲

---

## 🎵 歌曲查询测试

### 测试 5: 歌曲信息查询

```bash
# 精确查询
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, what is the BPM of 千本桜?",
    "images": []
  }'

# 模糊匹配
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, 千本樱的难度是多少？",
    "images": []
  }'
```

---

## 🔍 检查数据库

### 查看对话历史

```bash
# 使用 mongosh
mongosh mongodb://localhost:27017/mika_bot

# 查看最近的对话
db.conversations.find().sort({timestamp: -1}).limit(5).pretty()

# 查看用户印象
db.impressions.find().pretty()

# 查看用户
db.users.find().pretty()
```

---

## 🛠️ 使用现有测试脚本

### 基础功能测试（不需要服务）
```bash
poetry run python scripts/test_basic.py
```

### Webhook 测试（需要 FastAPI 运行）
```bash
poetry run python scripts/test_webhook_simple.py
```

### 图像测试
```bash
poetry run python scripts/test_image_manual.py
```

---

## 📊 自动化测试

### 运行所有单元测试
```bash
poetry run pytest tests/unit/ -v
```

### 运行所有集成测试
```bash
poetry run pytest tests/integration/ -v
```

### 运行图像处理测试
```bash
poetry run pytest tests/unit/test_multimodal.py tests/integration/test_image_flow.py -v
```

---

## ✅ 快速检查清单

- [ ] FastAPI 服务器运行在 `http://localhost:8000`
- [ ] Temporal Worker 正在运行
- [ ] MongoDB 连接正常
- [ ] Bot 响应包含 "Mika" 的消息
- [ ] Bot 忽略不包含 "Mika" 的消息
- [ ] 图像验证工作正常（JPEG/PNG/WebP）
- [ ] 图像分析功能正常
- [ ] 对话记忆功能正常
- [ ] 歌曲查询功能正常

---

## 🐛 常见问题

### Bot 不响应
1. 检查消息是否包含 "Mika"
2. 检查 FastAPI 日志
3. 检查 Temporal Worker 是否运行

### 图像被拒绝
1. 检查图像大小 < 10MB
2. 检查格式是否为 JPEG/PNG/WebP
3. 检查 base64 编码是否正确

### 查看详细日志
- FastAPI 日志在控制台输出
- Temporal UI: `http://localhost:8088`
- MongoDB: 使用 mongosh 查询

---

**更多详细信息**: 查看 `MANUAL_TESTING_GUIDE.md`
