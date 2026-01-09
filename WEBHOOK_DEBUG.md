# Webhook 调试指南

## 问题: 422 Unprocessable Entity

当看到 `422 Unprocessable Entity` 错误时，表示请求体格式验证失败。

---

## 🔍 诊断步骤

### 1. 查看详细错误日志

FastAPI 现在会记录详细的验证错误。查看终端日志，应该看到类似：

```json
{
  "event_type": "error",
  "event": "request_validation_failed",
  "path": "/webhook",
  "method": "POST",
  "errors": [...],
  "body_preview": "..."
}
```

### 2. 检查 LangBot 发送的请求格式

LangBot 应该发送以下格式的 JSON：

```json
{
  "group_id": "123456789",
  "user_id": "987654321",
  "message": "Mika, 你好！",
  "images": [],
  "timestamp": "2026-01-09T12:00:00Z"
}
```

**必需字段**:
- `group_id` (string)
- `user_id` (string)
- `message` (string)

**可选字段**:
- `images` (array of strings, base64-encoded)
- `timestamp` (string, ISO format)

### 3. 常见问题

#### 问题 1: 字段名称不匹配

**错误**: LangBot 可能使用不同的字段名

**解决方案**: 检查 LangBot 配置，确保字段名匹配：
- `group_id` (不是 `groupId` 或 `group`)
- `user_id` (不是 `userId` 或 `user`)
- `message` (不是 `text` 或 `content`)

#### 问题 2: 字段类型不匹配

**错误**: 字段类型不正确（例如 `group_id` 是数字而不是字符串）

**解决方案**: 确保所有字段都是正确的类型：
- `group_id`: 字符串
- `user_id`: 字符串
- `message`: 字符串
- `images`: 数组（可选）

#### 问题 3: 缺少必需字段

**错误**: 缺少 `group_id`、`user_id` 或 `message`

**解决方案**: 检查 LangBot 配置，确保所有必需字段都被发送

---

## 🧪 测试正确的请求格式

### 使用 curl 测试

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group",
    "user_id": "test_user",
    "message": "Mika, 你好！",
    "images": []
  }'
```

### 使用 PowerShell 测试

```powershell
$body = @{
    group_id = "test_group"
    user_id = "test_user"
    message = "Mika, 你好！"
    images = @()
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/webhook" -Method Post -Body $body -ContentType "application/json"
```

---

## 📋 验证检查清单

- [ ] 请求包含 `group_id` 字段（字符串）
- [ ] 请求包含 `user_id` 字段（字符串）
- [ ] 请求包含 `message` 字段（字符串）
- [ ] 字段名称完全匹配（小写，下划线分隔）
- [ ] Content-Type 头是 `application/json`
- [ ] JSON 格式有效

---

## 🔧 临时解决方案

如果需要支持不同的请求格式，可以：

1. **修改模型以支持多种格式**（不推荐）
2. **在 LangBot 中配置正确的格式**（推荐）
3. **添加适配器层**（如果 LangBot 格式无法更改）

---

## 📝 日志示例

### 成功的请求

```json
{
  "event": "webhook_received",
  "group_id": "123456789",
  "user_id": "987654...",
  "message_length": 10,
  "has_images": false
}
```

### 失败的请求（422）

```json
{
  "event": "request_validation_failed",
  "path": "/webhook",
  "method": "POST",
  "errors": [
    {
      "loc": ["body", "group_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "body_preview": "{\"groupId\":\"123\",\"userId\":\"456\",\"message\":\"test\"}"
}
```

从上面的错误可以看出，LangBot 使用了 `groupId` 而不是 `group_id`。

---

## 🎯 下一步

1. **查看日志**: 检查 FastAPI 终端中的详细错误信息
2. **检查 LangBot 配置**: 确保字段名称匹配
3. **测试本地**: 使用 curl 或 PowerShell 测试正确的格式
4. **更新 LangBot**: 如果格式不匹配，更新 LangBot 配置

---

**提示**: 如果 LangBot 的格式无法更改，我们可以添加一个适配器来转换格式。
