# LangBot 请求格式修复

## 🔴 问题

LangBot 实际发送的请求格式与我们的 API 模型不匹配，导致 `422 Unprocessable Entity` 错误。

### 错误日志示例

```json
{
  "path": "/webhook",
  "method": "POST",
  "errors": [
    {"type": "missing", "loc": ["body", "group_id"], "msg": "Field required"},
    {"type": "missing", "loc": ["body", "user_id"], "msg": "Field required"},
    {"type": "missing", "loc": ["body", "message"], "msg": "Field required"}
  ],
  "body_preview": {
    "uuid": "757837bd-a27c-4126-a8cf-76f0883c197d",
    "event_type": "bot.person_message",
    "data": {
      "bot_uuid": "c667dddf-be66-4bf9-bb4a-b8105587ecbb",
      "adapter_name": "AiocqhttpAdapter",
      "sender": {"id": "2443939219", "name": ""},
      "message": [
        {"type": "Source", "id": 894714356, "timestamp": 1767937385},
        {"type": "Plain", "text": "hi"}
      ],
      "timestamp": 1767937385.0
    }
  }
}
```

## ✅ 解决方案

已更新 `src/api/routes/langbot.py` 以支持 LangBot 的实际事件格式。

### 1. 新增 `LangBotEventRequest` 模型

支持 LangBot 的实际事件格式：

```python
class LangBotEventRequest(BaseModel):
    uuid: str
    event_type: str  # "bot.person_message" 或 "bot.group_message"
    data: dict[str, Any]  # 包含 sender, message, timestamp 等
```

### 2. 添加格式转换函数

`convert_langbot_event_to_webhook_request()` 函数将 LangBot 事件格式转换为我们的简化格式：

- **提取用户 ID**: 从 `data.sender.id`
- **提取消息文本**: 从 `data.message` 数组中提取 `type="Plain"` 的文本
- **提取图片**: 从 `data.message` 数组中提取 `type="Image"` 的图片
- **提取群组 ID**: 从 `data.group_id`（群组消息）或空字符串（私聊）
- **提取时间戳**: 从 `data.timestamp` 转换为 ISO 格式

### 3. 更新 Webhook 处理函数

两个端点现在都支持**两种格式**：

1. **LangBot 事件格式**（实际格式）:
   ```json
   {
     "uuid": "...",
     "event_type": "bot.person_message",
     "data": {...}
   }
   ```

2. **简化格式**（用于测试）:
   ```json
   {
     "group_id": "...",
     "user_id": "...",
     "message": "...",
     "images": [...]
   }
   ```

处理逻辑：
- 首先尝试解析为 LangBot 事件格式
- 如果失败，回退到简化格式
- 如果都失败，返回 422 错误

## 📋 支持的 LangBot 事件类型

- `bot.person_message`: 私聊消息
- `bot.group_message`: 群组消息

## 🔍 消息格式解析

LangBot 发送的消息是数组格式：

```json
"message": [
  {"type": "Source", "id": 894714356, "timestamp": 1767937385},
  {"type": "Plain", "text": "hi"},
  {"type": "Image", "url": "..."}
]
```

转换函数会：
- 提取所有 `type="Plain"` 的文本并拼接
- 提取所有 `type="Image"` 的图片 URL 或 base64 数据

## ✅ 验证

修复后，LangBot 的请求应该能够：
1. ✅ 成功解析 LangBot 事件格式
2. ✅ 正确提取用户 ID、消息文本、群组 ID
3. ✅ 正确处理私聊和群组消息
4. ✅ 继续支持简化格式（用于测试）

## 🧪 测试

### 测试 LangBot 事件格式

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "test-uuid",
    "event_type": "bot.person_message",
    "data": {
      "sender": {"id": "123456", "name": "Test"},
      "message": [
        {"type": "Plain", "text": "Mika, 你好"}
      ],
      "timestamp": 1767937385.0
    }
  }'
```

### 测试简化格式（仍然支持）

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group",
    "user_id": "123456",
    "message": "Mika, 你好"
  }'
```

## 📝 注意事项

1. **私聊消息**: `group_id` 会被设置为空字符串
2. **群组消息**: `group_id` 从 `data.group_id` 提取
3. **时间戳**: 支持 Unix 时间戳（整数/浮点数）和 ISO 格式字符串
4. **图片**: 支持 `url` 或 `data` 字段

## 🔄 向后兼容

- ✅ 简化格式仍然完全支持
- ✅ 现有的测试脚本无需修改
- ✅ API 文档中的格式仍然有效

---

**修复完成**: LangBot 现在应该能够成功连接到你的电脑并发送消息了！🎉
