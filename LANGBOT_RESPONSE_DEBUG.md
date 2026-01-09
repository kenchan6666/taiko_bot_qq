# LangBot 响应问题调试指南

## 🔴 问题

从日志看，消息被过滤了（`no_mika_mention_or_filtered`），返回空响应，导致 LangBot 使用自己的默认回复而不是 Mika 的回复。

## 📋 当前行为

### 日志显示：
```
message_length: 3  # 消息只有 3 个字符（可能是 "hi"）
reason: "no_mika_mention_or_filtered"
```

### 返回的响应：
```json
{
  "response": "",
  "success": false
}
```

### 问题原因

根据 FR-001，系统**只响应明确提到 "Mika" 的消息**。如果消息中没有提到 "Mika"、"米卡" 或 "mika酱"，消息会被过滤。

## ✅ 解决方案

### 方案 1: 确保消息包含 "Mika"（推荐）

用户发送消息时，必须包含以下之一：
- `Mika` (不区分大小写)
- `米卡`
- `mika酱`

**示例**：
- ✅ `Mika, 你好` - 会响应
- ✅ `米卡，推荐一首歌` - 会响应
- ✅ `mika酱，hi` - 会响应
- ❌ `hi` - 不会响应（被过滤）
- ❌ `你好` - 不会响应（被过滤）

### 方案 2: 检查消息解析是否正确

如果消息确实包含 "Mika" 但仍被过滤，可能是消息解析有问题。

**调试步骤**：

1. **查看详细日志**：
   现在日志会显示：
   - `message_preview`: 实际提取的消息内容（前 50 个字符）
   - `extracted_message_preview`: 从 LangBot 事件中提取的消息预览
   - `extracted_message_length`: 提取的消息长度

2. **检查 LangBot 消息格式**：
   LangBot 发送的消息格式是数组：
   ```json
   "message": [
     {"type": "Source", "id": 123, "timestamp": 1234567890},
     {"type": "Plain", "text": "Mika, hi"}
   ]
   ```
   
   如果消息格式不同，可能无法正确提取。

3. **查看完整请求**：
   在日志中查找 `webhook_event_format_detected` 或 `webhook_simplified_format_detected`，查看实际收到的消息内容。

### 方案 3: 临时禁用名称检测（仅用于调试）

如果需要测试其他功能，可以临时修改 `src/steps/step1.py`：

```python
# 临时注释掉名称检测（仅用于调试）
# if not MIKA_NAME_PATTERN.search(message):
#     return None
```

**⚠️ 警告**: 这只是用于调试，不要在生产环境中使用！

## 🔍 调试命令

### 查看详细日志

FastAPI 日志现在会显示：
- 实际收到的消息内容
- 消息是否包含 "Mika"
- 消息被过滤的原因

### 测试消息格式

使用 curl 测试：

```bash
# 测试包含 "Mika" 的消息
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "test",
    "event_type": "bot.person_message",
    "data": {
      "sender": {"id": "123456", "name": "Test"},
      "message": [
        {"type": "Plain", "text": "Mika, 你好"}
      ],
      "timestamp": 1234567890
    }
  }'
```

## 📝 下一步

1. **检查日志**：查看 `message_preview` 字段，确认实际收到的消息内容
2. **确认消息格式**：如果消息包含 "Mika" 但仍被过滤，检查消息解析逻辑
3. **测试响应**：发送包含 "Mika" 的消息，确认能正常响应

## 🎯 预期行为

### 消息包含 "Mika"：
- ✅ 消息被处理
- ✅ 启动 Temporal workflow
- ✅ 返回 Mika 的回复

### 消息不包含 "Mika"：
- ❌ 消息被过滤
- ❌ 返回空响应（`response=""`, `success=False`）
- ⚠️ LangBot 可能使用自己的默认回复

---

**提示**: 如果消息确实包含 "Mika" 但仍被过滤，请检查日志中的 `message_preview` 字段，确认消息是否正确提取。
