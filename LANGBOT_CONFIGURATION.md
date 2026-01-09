# LangBot 配置指南

**目的**: 配置 LangBot 以连接到 FastAPI 后端并发送 webhook

**适用场景**: 设置 LangBot 作为外部服务，连接到 Mika Taiko Chatbot 的 FastAPI 后端

---

## 概述

LangBot 是一个外部服务，需要单独部署和配置。本指南说明如何配置 LangBot 以：
1. 检测关键词触发（"Mika", "米卡", "mika酱"）
2. 发送 webhook 到 FastAPI 后端
3. 配置群组白名单（可选）

---

## 前置要求

1. **LangBot 已安装**: 按照 [LangBot 官方文档](https://docs.langbot.app) 安装 LangBot
2. **FastAPI 后端运行**: FastAPI 后端必须正在运行并可以访问
3. **Webhook 端点暴露**: 确保 `/webhook/langbot` 端点可以从 LangBot 访问
   - 本地开发: 使用 ngrok 或其他隧道服务
   - 生产环境: 使用公网 IP/域名 + Nginx
   - 详见: [WEBHOOK_SETUP_GUIDE.md](./WEBHOOK_SETUP_GUIDE.md)

---

## 配置步骤

### 步骤 1: 准备配置文件

复制示例配置文件：

```bash
# 复制示例配置
cp langbot.config.example.yaml langbot.config.yaml

# 编辑配置文件
nano langbot.config.yaml  # 或使用你喜欢的编辑器
```

### 步骤 2: 配置关键词触发

在 `langbot.config.yaml` 中配置关键词触发：

```yaml
triggers:
  - type: keyword
    # 正则表达式模式：匹配 "Mika", "米卡", "mika酱" (不区分大小写)
    pattern: "(?i)(mika|米卡|mika酱)"
    # Webhook URL: 替换为你的 FastAPI 后端 URL
    webhook_url: "https://api.yourdomain.com/webhook/langbot"
    # 或本地开发使用 ngrok: "https://abc123.ngrok.io/webhook/langbot"
    enabled: true
```

**重要**: 
- `pattern` 使用正则表达式，`(?i)` 表示不区分大小写
- `webhook_url` 必须包含完整路径 `/webhook/langbot`
- 确保 URL 可以从 LangBot 服务器访问

### 步骤 3: 配置群组白名单（可选）

#### 方法 A: 在配置文件中设置

```yaml
allowed_groups:
  - "123456789"  # QQ 群组 ID 1
  - "987654321"  # QQ 群组 ID 2
```

#### 方法 B: 使用环境变量

```bash
# 设置环境变量
export LANGBOT_ALLOWED_GROUPS="123456789,987654321"

# 或在 .env 文件中
echo "LANGBOT_ALLOWED_GROUPS=123456789,987654321" >> .env
```

**注意**:
- 如果未配置白名单，所有群组都可以使用机器人
- 私聊消息不受白名单限制
- 白名单在 FastAPI 后端也会进行验证（双重验证）

### 步骤 4: 配置 Webhook 超时和重试

```yaml
webhook:
  timeout: 30  # 超时时间（秒）
  retry:
    max_attempts: 3  # 最大重试次数
    backoff_seconds: 2  # 重试间隔（秒）
```

### 步骤 5: 配置日志

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"  # json 或 text
```

---

## 启动 LangBot

### 方法 1: 直接运行

```bash
# 使用配置文件启动
langbot start --config langbot.config.yaml

# 或使用环境变量
export LANGBOT_CONFIG_PATH=langbot.config.yaml
langbot start
```

### 方法 2: 使用 Docker

```bash
# 创建 docker-compose.yml
cat > docker-compose.langbot.yml << EOF
version: '3.8'
services:
  langbot:
    image: langbot/langbot:latest
    volumes:
      - ./langbot.config.yaml:/app/config.yaml
      - ./langbot-data:/app/data
    environment:
      - LANGBOT_ALLOWED_GROUPS=123456789,987654321
    restart: unless-stopped
EOF

# 启动
docker-compose -f docker-compose.langbot.yml up -d
```

---

## 验证配置

### 1. 检查 LangBot 日志

启动 LangBot 后，检查日志确认配置加载成功：

```bash
# 查看日志
tail -f langbot.log

# 或 Docker
docker-compose -f docker-compose.langbot.yml logs -f langbot
```

应该看到类似以下日志：
```
INFO: LangBot started successfully
INFO: Keyword trigger configured: pattern=(?i)(mika|米卡|mika酱)
INFO: Webhook URL: https://api.yourdomain.com/webhook/langbot
INFO: Allowed groups: 123456789, 987654321
```

### 2. 测试 Webhook 连接

从 LangBot 服务器测试 webhook 端点：

```bash
# 测试 webhook 端点
curl -X POST https://api.yourdomain.com/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, test message",
    "images": []
  }'
```

应该收到 FastAPI 后端的响应。

### 3. 端到端测试

在配置的 QQ 群中发送消息：

```
Mika, 你好！
```

检查：
1. **LangBot 日志**: 应该看到关键词检测和 webhook 发送
2. **FastAPI 日志**: 应该看到 webhook 接收和处理
3. **QQ 群**: 应该收到机器人的回复

---

## 配置示例

### 完整配置示例

```yaml
# LangBot 完整配置示例
bot:
  name: "Mika"
  description: "Taiko no Tatsujin themed QQ chatbot"

triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "https://api.yourdomain.com/webhook/langbot"
    enabled: true

allowed_groups:
  - "123456789"
  - "987654321"

webhook:
  timeout: 30
  retry:
    max_attempts: 3
    backoff_seconds: 2

logging:
  level: "INFO"
  format: "json"
```

### 本地开发配置示例

```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    # 使用 ngrok URL（每次重启 ngrok 需要更新）
    webhook_url: "https://abc123.ngrok.io/webhook/langbot"
    enabled: true

# 本地开发可以不配置白名单（允许所有群组）
# allowed_groups: []
```

### 生产环境配置示例

```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    # 使用 HTTPS 域名
    webhook_url: "https://api.yourdomain.com/webhook/langbot"
    enabled: true

# 生产环境必须配置白名单
allowed_groups:
  - "123456789"
  - "987654321"

webhook:
  timeout: 60  # 生产环境可以增加超时时间
  retry:
    max_attempts: 5
    backoff_seconds: 3

logging:
  level: "INFO"
  format: "json"
```

---

## 故障排查

### 问题 1: LangBot 无法检测关键词

**症状**: 在 QQ 群中发送 "Mika" 但 LangBot 没有反应

**解决方案**:
- 检查正则表达式模式是否正确: `(?i)(mika|米卡|mika酱)`
- 确认 trigger 已启用: `enabled: true`
- 检查 LangBot 日志是否有错误
- 确认 LangBot 已连接到 QQ（通过 Napcat）

### 问题 2: Webhook 发送失败

**症状**: LangBot 日志显示 webhook 发送失败

**解决方案**:
- 验证 webhook URL 是否正确（包含 `/webhook/langbot`）
- 从 LangBot 服务器测试连接: `curl https://api.yourdomain.com/webhook/langbot`
- 检查防火墙规则是否允许 LangBot 服务器访问
- 确认 FastAPI 后端正在运行: `curl https://api.yourdomain.com/health`
- 检查 webhook 超时设置是否足够

### 问题 3: 群组白名单不工作

**症状**: 未在白名单中的群组仍然可以触发机器人

**解决方案**:
- 检查 LangBot 配置中的 `allowed_groups` 是否正确
- 检查环境变量 `LANGBOT_ALLOWED_GROUPS` 是否设置
- 确认 FastAPI 后端的 `LANGBOT_ALLOWED_GROUPS` 配置（双重验证）
- 查看 LangBot 和 FastAPI 日志确认白名单检查

### 问题 4: 私聊消息不响应

**症状**: 私聊消息没有触发机器人

**解决方案**:
- 确认 LangBot 配置支持私聊消息（通常默认支持）
- 检查 FastAPI 后端的私聊处理逻辑（私聊不需要 "Mika" 关键词）
- 查看 LangBot 日志确认私聊消息是否被接收

---

## 安全建议

1. **使用 HTTPS**: 生产环境必须使用 HTTPS 保护 webhook 数据
2. **配置白名单**: 限制只有特定群组可以使用机器人
3. **监控日志**: 定期检查 LangBot 和 FastAPI 日志，检测异常活动
4. **定期更新**: 保持 LangBot 和 FastAPI 后端更新到最新版本
5. **备份配置**: 定期备份 LangBot 配置文件

---

## 相关文档

- [langbot.config.example.yaml](./langbot.config.example.yaml) - 配置文件示例
- [WEBHOOK_SETUP_GUIDE.md](./WEBHOOK_SETUP_GUIDE.md) - Webhook 端点暴露指南
- [quickstart.md](./specs/1-mika-bot/quickstart.md) - 完整设置指南
- [LangBot 官方文档](https://docs.langbot.app) - LangBot 官方文档

---

## 下一步

配置完成后，进行端到端测试：

1. 运行测试脚本: `python scripts/test_langbot_integration.py`
2. 在 QQ 群中测试: 发送 "Mika, 你好！"
3. 验证响应: 确认机器人正确回复

---

**最后更新**: 2026-01-09  
**维护者**: Mika Taiko Chatbot Team
