# LangBot API 配置指南

## 概述

现在系统支持通过 LangBot API 直接发送消息，而不是依赖 webhook 响应。这确保了消息能够正确发送到 QQ。

## 配置步骤

### 1. 设置环境变量

在 `.env` 文件中添加以下配置：

```env
# LangBot API Configuration
LANGBOT_API_KEY=lbk_nAftIpIZTN_HY2YwvXgcAt3OVJM-dj3FG6SHHgVJTiU
LANGBOT_API_BASE_URL=http://localhost:3000
```

**注意**：
- `LANGBOT_API_KEY`: 你的 LangBot API Key（已提供）
- `LANGBOT_API_BASE_URL`: LangBot API 的基础 URL
  - 本地开发：`http://localhost:3000`
  - 如果 LangBot 运行在其他端口，请相应修改

### 2. 验证配置

配置完成后，重启 FastAPI 服务器。系统会自动：
1. 接收 LangBot webhook 请求
2. 处理消息并生成回复
3. 通过 LangBot API 发送回复到 QQ

## 工作原理

1. **Webhook 接收**：LangBot 发送消息事件到 `/webhook/langbot`
2. **消息处理**：系统通过 Temporal 工作流处理消息（LLM 生成回复）
3. **API 发送**：生成回复后，系统通过 LangBot API 的 `send_message` 端点发送消息
4. **响应返回**：Webhook 返回 `skip_pipeline=true`，告诉 LangBot 跳过内部处理

## 日志监控

系统会记录以下日志：

- `langbot_api_send_starting`: 开始通过 API 发送消息
- `langbot_api_send_success`: 消息发送成功
- `langbot_api_send_http_error`: HTTP 错误（如 401, 404 等）
- `langbot_api_send_network_error`: 网络错误（连接失败等）

## 故障排除

### 问题：消息没有发送

1. **检查 API Key**：
   - 确认 `.env` 文件中的 `LANGBOT_API_KEY` 已设置
   - 确认 API Key 格式正确（以 `lbk_` 开头）

2. **检查 API Base URL**：
   - 确认 `LANGBOT_API_BASE_URL` 指向正确的 LangBot 服务器
   - 本地开发通常是 `http://localhost:3000`

3. **检查日志**：
   - 查看 FastAPI 日志中的 `langbot_api_send_*` 条目
   - 如果看到 `langbot_api_send_http_error`，检查状态码和错误详情

4. **检查 Bot UUID**：
   - 确认 webhook 请求中包含 `bot_uuid`
   - 如果 `bot_uuid` 缺失，系统会记录错误但不会发送消息

### 问题：401 Unauthorized

- API Key 无效或格式错误
- 检查 API Key 是否正确复制（没有多余空格）

### 问题：404 Not Found

- Bot UUID 不正确
- API Base URL 不正确
- 检查 LangBot 服务器是否正在运行

## 测试

配置完成后，发送一条测试消息到 QQ。你应该会收到 Mika 的回复。

如果消息没有发送，检查：
1. FastAPI 日志中的错误信息
2. LangBot 日志中的错误信息
3. 确认所有服务都在运行（FastAPI, Temporal Worker, MongoDB, LangBot）
