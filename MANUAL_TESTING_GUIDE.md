# 手动测试指南 - Mika Taiko Chatbot

**目的**: 提供详细的手动测试步骤，无需编写脚本即可验证功能

**适用场景**: 
- 快速功能验证
- 调试和问题排查
- 用户体验测试
- 集成测试前的验证

---

## 目录

1. [环境准备](#环境准备)
2. [基础功能测试](#基础功能测试)
3. [图像处理测试](#图像处理测试)
4. [记忆功能测试](#记忆功能测试)
5. [歌曲查询测试](#歌曲查询测试)
6. [错误场景测试](#错误场景测试)

---

## 环境准备

### 1. 启动服务

#### 启动 MongoDB
```bash
# 如果使用 Docker
docker run -d -p 27017:27017 --name mika_mongo mongo:7.0

# 或者使用本地 MongoDB
mongod --dbpath /path/to/data
```

#### 启动 Temporal Server
```bash
# 使用 Docker Compose (在 temporal-docker 目录)
cd temporal-docker
docker-compose up -d
```

#### 启动 FastAPI 后端
```bash
# 在项目根目录
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 启动 Temporal Worker
```bash
# 在另一个终端
poetry run python -m src.workers.temporal_worker
```

### 2. 验证服务状态

访问健康检查端点：
```bash
curl http://localhost:8000/health
```

或使用浏览器访问：`http://localhost:8000/docs` 查看 API 文档

---

## 基础功能测试

### 测试 1: 名称检测

**目标**: 验证 bot 只响应包含 "Mika" 的消息

#### 方法 A: 使用 curl

```bash
# 测试 1.1: 包含 "Mika" 的消息（应该响应）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }'

# 预期结果: 返回 JSON，包含 "response" 字段，有内容

# 测试 1.2: 不包含 "Mika" 的消息（不应该响应）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "今天天气真好",
    "images": []
  }'

# 预期结果: 返回 JSON，success: false，response: ""

# 测试 1.3: 中文名称变体 "米卡"
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "米卡，帮我查一下歌曲",
    "images": []
  }'

# 预期结果: 返回 JSON，包含响应
```

#### 方法 B: 使用 Python 交互式测试

```python
# 在 Python REPL 中
import asyncio
from src.steps.step1 import parse_input

# 测试名称检测
result1 = parse_input(
    user_id="123456",
    group_id="789012",
    message="Mika, 你好！",
    images=None
)
print(f"包含 'Mika': {result1 is not None}")  # 应该为 True

result2 = parse_input(
    user_id="123456",
    group_id="789012",
    message="今天天气真好",
    images=None
)
print(f"不包含 'Mika': {result2 is None}")  # 应该为 True
```

---

## 图像处理测试

### 测试 2: 图像验证

**目标**: 验证图像大小和格式限制

#### 准备测试图像

1. **创建有效的 JPEG 图像** (小尺寸，< 1MB)
   ```python
   # 使用 Python 创建测试图像
   from PIL import Image
   import io
   import base64
   
   # 创建 100x100 的测试图像
   img = Image.new('RGB', (100, 100), color='red')
   buffer = io.BytesIO()
   img.save(buffer, format='JPEG')
   jpeg_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
   print(f"JPEG base64 (前50字符): {jpeg_base64[:50]}...")
   ```

2. **创建有效的 PNG 图像**
   ```python
   img = Image.new('RGB', (100, 100), color='blue')
   buffer = io.BytesIO()
   img.save(buffer, format='PNG')
   png_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
   ```

3. **创建无效格式** (GIF)
   ```python
   # GIF 格式不被支持
   gif_data = b"GIF89a" + b"x" * 1000
   gif_base64 = base64.b64encode(gif_data).decode('utf-8')
   ```

#### 测试步骤

```bash
# 测试 2.1: 发送有效的 JPEG 图像
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d "{
    \"group_id\": \"test_group_001\",
    \"user_id\": \"test_user_001\",
    \"message\": \"Mika, 看看这张图片\",
    \"images\": [\"${JPEG_BASE64}\"]
  }"

# 预期结果: 成功处理，返回图像分析响应

# 测试 2.2: 发送无效格式 (GIF)
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d "{
    \"group_id\": \"test_group_001\",
    \"user_id\": \"test_user_001\",
    \"message\": \"Mika, 看看这张图片\",
    \"images\": [\"${GIF_BASE64}\"]
  }"

# 预期结果: 被拒绝，返回 success: false

# 测试 2.3: 发送超大图像 (> 10MB)
# 注意: 需要创建大于 10MB 的图像
# 预期结果: 被拒绝
```

#### 使用 Python 直接测试图像验证

```python
from src.steps.step1 import _validate_images, _detect_image_format
import base64

# 创建测试 JPEG
jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"x" * 1000
jpeg_base64 = base64.b64encode(jpeg_data).decode('utf-8')

# 测试验证
result = _validate_images([jpeg_base64], "zh")
print(f"JPEG 验证结果: {result is not None}")  # 应该为 True

# 测试格式检测
format_result = _detect_image_format(jpeg_data)
print(f"检测到的格式: {format_result}")  # 应该为 "jpeg"
```

---

## 记忆功能测试

### 测试 3: 对话历史记忆

**目标**: 验证 bot 能记住之前的对话

#### 测试步骤

```bash
# 第一次对话
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 我喜欢高 BPM 的歌曲",
    "images": []
  }'

# 记录响应中的偏好确认请求

# 第二次对话（确认偏好）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 是的，我喜欢高 BPM",
    "images": []
  }'

# 预期结果: Bot 应该确认并记住偏好

# 第三次对话（引用之前的对话）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 推荐一些歌曲给我",
    "images": []
  }'

# 预期结果: Bot 应该基于之前记住的偏好（高 BPM）推荐歌曲
```

#### 使用 MongoDB 查看记忆

```bash
# 连接到 MongoDB
mongosh mongodb://localhost:27017/mika_bot

# 查看用户记录
db.users.find().pretty()

# 查看印象记录（记忆）
db.impressions.find().pretty()

# 查看对话历史
db.conversations.find().sort({timestamp: -1}).limit(10).pretty()
```

---

## 歌曲查询测试

### 测试 4: 歌曲信息查询

**目标**: 验证歌曲查询和模糊匹配功能

#### 测试步骤

```bash
# 测试 4.1: 精确歌曲名查询
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, what is the BPM of 千本桜?",
    "images": []
  }'

# 预期结果: 返回歌曲信息（BPM、难度等）

# 测试 4.2: 模糊匹配（拼写错误）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 千本樱的难度是多少？",
    "images": []
  }'

# 预期结果: 返回最匹配的歌曲，并询问确认（"你是指《千本桜》吗？"）

# 测试 4.3: 不存在的歌曲
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 告诉我关于《不存在的歌曲12345》的信息",
    "images": []
  }'

# 预期结果: 礼貌地表示找不到该歌曲
```

---

## 错误场景测试

### 测试 5: 错误处理和降级

**目标**: 验证系统在错误情况下的优雅降级

#### 测试步骤

```bash
# 测试 5.1: 无效的 API key（模拟 LLM 服务失败）
# 临时修改 .env 中的 OPENROUTER_API_KEY 为无效值
# 然后发送请求

curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好",
    "images": []
  }'

# 预期结果: 返回降级响应 "Don! Mika暂时无法回应，但我会尽快回来的！🥁"

# 测试 5.2: 空消息
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "",
    "images": []
  }'

# 预期结果: 被拒绝，success: false

# 测试 5.3: 恶意内容（如果配置了内容过滤）
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, [包含过滤关键词的消息]",
    "images": []
  }'

# 预期结果: 被过滤，success: false
```

---

## 快速测试脚本

### 使用现有的测试脚本

```bash
# 基础功能测试（不需要 MongoDB/Temporal）
poetry run python scripts/test_basic.py

# Webhook 测试（需要 FastAPI 运行）
poetry run python scripts/test_webhook_simple.py
```

---

## 检查清单

### 功能验证清单

- [ ] **名称检测**: Bot 只响应包含 "Mika" 的消息
- [ ] **图像验证**: 拒绝 > 10MB 的图像
- [ ] **图像格式**: 只接受 JPEG/PNG/WebP
- [ ] **图像分析**: Taiko 图像得到详细分析
- [ ] **非 Taiko 图像**: 礼貌重定向到 Taiko 内容
- [ ] **对话记忆**: Bot 记住之前的对话
- [ ] **偏好学习**: Bot 学习并确认用户偏好
- [ ] **歌曲查询**: 精确和模糊匹配都工作
- [ ] **错误处理**: 服务失败时优雅降级
- [ ] **速率限制**: 超过限制时被拒绝

### 性能检查清单

- [ ] **响应时间**: 大多数请求 < 3 秒
- [ ] **并发处理**: 可以处理多个并发请求
- [ ] **数据库连接**: MongoDB 连接稳定
- [ ] **Temporal 工作流**: 工作流正常执行

---

## 调试技巧

### 1. 查看日志

```bash
# FastAPI 日志会在控制台输出
# 查找包含以下关键词的日志：
# - "webhook_received"
# - "workflow_completed"
# - "workflow_execution_failed"
```

### 2. 检查 Temporal UI

访问 `http://localhost:8088` 查看 Temporal Web UI，可以：
- 查看工作流执行历史
- 查看活动执行状态
- 查看重试情况

### 3. 检查 MongoDB

```bash
# 查看最近的对话
mongosh mongodb://localhost:27017/mika_bot
db.conversations.find().sort({timestamp: -1}).limit(5).pretty()

# 查看用户印象
db.impressions.find().pretty()
```

### 4. 使用 Postman 或 Insomnia

导入以下 API 请求进行测试：

```json
{
  "method": "POST",
  "url": "http://localhost:8000/webhook/langbot",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }
}
```

---

## 常见问题排查

### 问题 1: Bot 不响应

**检查**:
1. 消息是否包含 "Mika"？
2. FastAPI 服务是否运行？
3. Temporal Worker 是否运行？
4. 查看 FastAPI 日志中的错误

### 问题 2: 图像被拒绝

**检查**:
1. 图像大小是否 < 10MB？
2. 图像格式是否为 JPEG/PNG/WebP？
3. Base64 编码是否正确？

### 问题 3: LLM 响应失败

**检查**:
1. `OPENROUTER_API_KEY` 是否正确设置？
2. API key 是否有足够的配额？
3. 网络连接是否正常？

### 问题 4: 记忆不工作

**检查**:
1. MongoDB 是否运行？
2. 数据库连接字符串是否正确？
3. 查看 `conversations` 和 `impressions` 集合是否有数据？

---

## 测试数据准备

### 创建测试用户

```python
# 在 Python REPL 中
from src.models.user import User
from src.models.impression import Impression
from src.utils.hashing import hash_user_id
import asyncio

async def create_test_user():
    user_id = "test_user_manual"
    hashed_id = hash_user_id(user_id)
    
    user = User(
        hashed_user_id=hashed_id,
        preferred_language="zh"
    )
    await user.insert()
    
    impression = Impression(
        user_id=hashed_id,
        relationship_status="new",
        interaction_count=0
    )
    await impression.insert()
    
    print(f"创建测试用户: {hashed_id}")

asyncio.run(create_test_user())
```

---

**最后更新**: 2026-01-08  
**版本**: 1.0
