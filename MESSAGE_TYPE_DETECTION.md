# 私聊/群聊检测功能

## ✅ 功能概述

系统**完全支持**检测私聊和群聊消息，并根据消息类型进行不同的处理。

## 🔍 检测机制

### 1. LangBot 事件类型

LangBot 发送的事件包含 `event_type` 字段：
- `bot.person_message`: 私聊消息
- `bot.group_message`: 群聊消息

### 2. 自动识别

系统在 `convert_langbot_event_to_webhook_request()` 函数中自动识别：

```python
if event.event_type == "bot.person_message":
    # 私聊消息 - group_id 为空字符串
    group_id = ""
elif event.event_type == "bot.group_message":
    # 群聊消息 - 从 data.group_id 提取
    group_id = data.get("group_id", "")
```

### 3. 识别规则

- **私聊消息**:
  - `event_type = "bot.person_message"`
  - `group_id = ""` (空字符串)
  - 日志显示: `message_type: "private"`

- **群聊消息**:
  - `event_type = "bot.group_message"`
  - `group_id = "群组ID"` (从 `data.group_id` 提取)
  - 日志显示: `message_type: "group"`

## 📋 日志信息

### 事件格式检测日志

```json
{
  "event": "webhook_event_format_detected",
  "event_type": "bot.person_message",  // 或 "bot.group_message"
  "message_type": "private",  // 或 "group"
  "has_group_id": false,  // 私聊为 false，群聊为 true
  "extracted_message_preview": "mika你好",
  "extracted_message_length": 6
}
```

### 消息接收日志

```json
{
  "event": "webhook_received",
  "message_type": "private",  // 或 "group"
  "group_id": "(private)",  // 私聊显示 "(private)"，群聊显示群组ID
  "user_id": "24439392...",
  "message_length": 6,
  "message_preview": "mika你好"
}
```

## 🎯 使用场景

### 1. 私聊消息

- **特点**: 一对一对话，更私密
- **group_id**: 空字符串 `""`
- **用途**: 
  - 个人咨询
  - 私密对话
  - 不需要群组上下文

### 2. 群聊消息

- **特点**: 群组内对话，可能有多个参与者
- **group_id**: 群组ID（如 `"123456789"`）
- **用途**:
  - 群组内问答
  - 群组推荐
  - 需要群组上下文

## 🔧 代码中的使用

### 检查消息类型

```python
# 在代码中检查是否为私聊
if not request.group_id:
    # 这是私聊消息
    pass

# 或检查是否为群聊
if request.group_id:
    # 这是群聊消息
    pass
```

### 根据类型使用不同逻辑

```python
if not request.group_id:
    # 私聊消息：可以使用更详细的回复
    response = "Don! 这是私聊，我可以更详细地回答你！🥁"
else:
    # 群聊消息：回复可以更简洁
    response = "Don! 我知道了！🥁"
```

## 📊 数据存储

### Conversation 模型

`Conversation` 模型中的 `group_id` 字段：
- **私聊**: `group_id = ""` (空字符串)
- **群聊**: `group_id = "群组ID"` (实际群组ID)

这样可以：
- 区分私聊和群聊的对话历史
- 按群组查询对话历史
- 统计群组使用情况

## 🎨 日志示例

### 私聊消息日志

```
{
  "event": "webhook_event_format_detected",
  "event_type": "bot.person_message",
  "message_type": "private",
  "has_group_id": false
}

{
  "event": "webhook_received",
  "message_type": "private",
  "group_id": "(private)",
  "user_id": "24439392..."
}
```

### 群聊消息日志

```
{
  "event": "webhook_event_format_detected",
  "event_type": "bot.group_message",
  "message_type": "group",
  "has_group_id": true
}

{
  "event": "webhook_received",
  "message_type": "group",
  "group_id": "123456789",
  "user_id": "24439392..."
}
```

## ✅ 验证方法

### 1. 查看日志

发送消息后，查看 FastAPI 日志：
- 查找 `webhook_event_format_detected` 事件
- 查看 `message_type` 字段：`"private"` 或 `"group"`

### 2. 检查 group_id

- **私聊**: `group_id` 为空字符串或日志显示 `"(private)"`
- **群聊**: `group_id` 有实际值（群组ID）

## 🔄 未来扩展

如果需要根据消息类型使用不同的处理逻辑，可以：

1. **不同的 Prompt**: 私聊使用更详细的 prompt，群聊使用简洁的 prompt
2. **不同的响应风格**: 私聊更正式，群聊更轻松
3. **不同的功能**: 某些功能只在群聊中启用，某些只在私聊中启用

---

**总结**: 系统完全支持私聊/群聊检测，所有相关日志都会显示 `message_type` 字段，方便调试和监控。
