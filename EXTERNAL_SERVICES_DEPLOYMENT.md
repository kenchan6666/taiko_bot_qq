# 外部服务部署要求

**目的**: 文档化 LangBot 和 Napcat 的外部服务部署要求

**适用场景**: 部署 LangBot 和 Napcat 作为独立服务，连接到 FastAPI 后端

---

## 概述

根据 NFR-013 和 Phase 9 要求，以下服务必须持续运行：

### 本项目 Docker Compose 中的服务（必须持续运行）

1. **FastAPI Backend** (`backend`): 处理 webhook，调用 gpt-4o，执行 5 步处理链
2. **Temporal Worker** (`temporal-worker`): 处理工作流和活动
3. **Temporal Server** (`temporal`): 工作流引擎，必须在线以调度任务和重试
4. **PostgreSQL** (`postgresql`): Temporal 的状态存储
5. **MongoDB** (`mongodb`): 存储用户数据、对话历史和印象
6. **Nginx** (可选但推荐): 反向代理，HTTPS，负载均衡

### 外部服务（必须持续运行，单独部署）

1. **LangBot**: 核心机器人平台，必须接收 QQ 消息并管理触发器
2. **Napcat**: QQ 协议层，必须保持机器人账号在线

**重要**: LangBot 和 Napcat **不包含**在本项目的 Docker Compose 堆栈中，必须单独部署。

---

## LangBot 部署要求

### 1. 服务要求

- **必须持续运行**: LangBot 必须保持运行以接收 QQ 消息
- **Webhook 配置**: LangBot 必须配置为向 FastAPI 后端发送 webhook
- **关键词触发**: 配置关键词触发模式 `(?i)(mika|米卡|mika酱)`
- **群组白名单**: 可选，但推荐配置以限制访问

### 2. 部署方法

LangBot 可以部署为：

- **独立进程**: 直接在服务器上运行 LangBot
- **Docker 容器**: 使用 Docker 运行 LangBot（推荐）
- **Docker Compose**: 使用独立的 docker-compose.yml 文件

### 3. 配置要求

#### Webhook URL 配置

LangBot 必须配置为向 FastAPI 后端发送 webhook：

```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "http://your-backend-url:8000/webhook/langbot"
    # 或使用 HTTPS (推荐生产环境)
    # webhook_url: "https://api.yourdomain.com/webhook/langbot"
```

**重要**: 
- 本地开发: 使用 ngrok URL (例如: `https://abc123.ngrok.io/webhook/langbot`)
- 生产环境: 使用公网域名/IP (例如: `https://api.yourdomain.com/webhook/langbot`)

#### 群组白名单配置

在 LangBot 配置中设置允许的群组：

```yaml
allowed_groups:
  - "123456789"
  - "987654321"
```

或使用环境变量：

```bash
export LANGBOT_ALLOWED_GROUPS="123456789,987654321"
```

### 4. 网络连接要求

LangBot 必须能够访问 FastAPI 后端的 webhook 端点：

- **本地开发**: 
  - 如果 LangBot 和 FastAPI 在同一台机器上，使用 `http://localhost:8000/webhook/langbot`
  - 如果 LangBot 在不同机器上，使用 ngrok 或公网 IP
- **生产环境**: 
  - 使用公网域名/IP
  - 确保防火墙规则允许 LangBot 服务器访问 FastAPI 后端

### 5. 验证连接

测试 LangBot 到 FastAPI 后端的连接：

```bash
# 从 LangBot 服务器测试 webhook 端点
curl -X POST http://your-backend-url:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, test message",
    "images": []
  }'
```

### 6. 监控和日志

- **日志位置**: 检查 LangBot 日志确认 webhook 发送成功
- **错误处理**: 监控 LangBot 日志中的 webhook 错误
- **重试机制**: LangBot 应该配置 webhook 重试机制

### 7. 相关文档

- [LANGBOT_CONFIGURATION.md](./LANGBOT_CONFIGURATION.md) - LangBot 配置指南
- [WEBHOOK_SETUP_GUIDE.md](./WEBHOOK_SETUP_GUIDE.md) - Webhook 端点暴露指南
- [langbot.config.example.yaml](./langbot.config.example.yaml) - LangBot 配置示例

---

## Napcat 部署要求

### 1. 服务要求

- **必须持续运行**: Napcat 必须保持运行以保持机器人账号在线
- **QQ 协议连接**: Napcat 必须连接到 QQ 平台
- **与 LangBot 集成**: Napcat 通常作为 LangBot 的一部分部署，或单独部署并与 LangBot 连接

### 2. 部署方法

Napcat 可以部署为：

- **独立进程**: 直接在服务器上运行 Napcat
- **Docker 容器**: 使用 Docker 运行 Napcat
- **与 LangBot 集成**: 作为 LangBot 部署的一部分

### 3. 配置要求

Napcat 需要配置：

- **QQ 账号信息**: 机器人 QQ 账号和密码/令牌
- **协议配置**: QQ 协议相关配置
- **连接设置**: 连接到 QQ 平台的网络设置

### 4. 网络连接要求

Napcat 必须能够：

- **连接到 QQ 平台**: 确保网络连接正常
- **保持长连接**: 保持与 QQ 平台的持久连接
- **处理重连**: 自动处理连接断开和重连

### 5. 验证连接

检查 Napcat 是否正常运行：

- **进程检查**: 确认 Napcat 进程正在运行
- **日志检查**: 查看 Napcat 日志确认连接状态
- **QQ 状态**: 确认机器人账号在线

### 6. 监控和日志

- **日志位置**: 检查 Napcat 日志确认连接状态
- **错误处理**: 监控 Napcat 日志中的连接错误
- **自动重连**: 确保 Napcat 配置了自动重连机制

---

## 部署架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
│  (本项目部署的服务)                                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Backend    │  │Temporal Worker│  │  Temporal    │      │
│  │  (FastAPI)  │  │               │  │   Server     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘             │
│                            │                                 │
│         ┌──────────────────┴──────────────────┐             │
│         │                                      │             │
│  ┌──────▼──────┐                      ┌───────▼──────┐      │
│  │  MongoDB    │                      │  PostgreSQL  │      │
│  └─────────────┘                      └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Webhook (HTTP/HTTPS)
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              External Services (单独部署)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                          │
│  │   LangBot    │◄──────────────────┐                      │
│  │              │                   │                      │
│  └──────┬───────┘                   │                      │
│         │                            │                      │
│         │ QQ Messages                │                      │
│         │                            │                      │
│  ┌──────▼───────┐                    │                      │
│  │   Napcat     │                    │                      │
│  │              │                    │                      │
│  └──────┬───────┘                    │                      │
│         │                            │                      │
│         └────────────────────────────┘                      │
│                  QQ Platform                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 部署检查清单

### LangBot 部署检查

- [ ] LangBot 已安装并配置
- [ ] Webhook URL 配置正确（指向 FastAPI 后端）
- [ ] 关键词触发模式配置正确: `(?i)(mika|米卡|mika酱)`
- [ ] 群组白名单已配置（可选但推荐）
- [ ] LangBot 可以访问 FastAPI 后端 webhook 端点
- [ ] LangBot 日志显示正常运行
- [ ] LangBot 服务配置为自动重启（systemd/docker restart policy）

### Napcat 部署检查

- [ ] Napcat 已安装并配置
- [ ] QQ 账号信息配置正确
- [ ] Napcat 可以连接到 QQ 平台
- [ ] 机器人账号在线
- [ ] Napcat 日志显示正常运行
- [ ] Napcat 服务配置为自动重启

### 集成测试检查

- [ ] 在 QQ 群中发送 "Mika, 你好！"
- [ ] LangBot 检测到关键词并发送 webhook
- [ ] FastAPI 后端接收到 webhook 请求
- [ ] Temporal 工作流成功执行
- [ ] 机器人回复消息
- [ ] 消息成功发送到 QQ 群

---

## 故障排查

### LangBot 无法连接 FastAPI 后端

**症状**: LangBot 日志显示 webhook 发送失败

**解决方案**:
1. 验证 webhook URL 是否正确（包含 `/webhook/langbot`）
2. 从 LangBot 服务器测试连接: `curl http://your-backend-url:8000/health`
3. 检查防火墙规则是否允许 LangBot 访问 FastAPI 后端
4. 确认 FastAPI 后端正在运行: `docker-compose ps backend`
5. 检查 FastAPI 后端日志: `docker-compose logs backend`

### Napcat 无法连接 QQ 平台

**症状**: Napcat 日志显示连接失败

**解决方案**:
1. 检查网络连接是否正常
2. 验证 QQ 账号信息是否正确
3. 检查防火墙规则是否允许 Napcat 连接到 QQ 平台
4. 查看 Napcat 日志获取详细错误信息
5. 尝试重启 Napcat 服务

### 机器人不响应消息

**症状**: 在 QQ 群中发送消息但机器人不回复

**解决方案**:
1. 检查 LangBot 是否检测到关键词（查看 LangBot 日志）
2. 检查 webhook 是否成功发送（查看 LangBot 日志）
3. 检查 FastAPI 后端是否接收到 webhook（查看后端日志）
4. 检查 Temporal 工作流是否执行（查看 Temporal Web UI: http://localhost:8088）
5. 检查 Temporal Worker 是否运行: `docker-compose ps temporal-worker`
6. 验证所有服务健康状态: `docker-compose ps`

---

## 相关文档

- [quickstart.md](./specs/1-mika-bot/quickstart.md) - 完整设置指南
- [LANGBOT_CONFIGURATION.md](./LANGBOT_CONFIGURATION.md) - LangBot 配置指南
- [WEBHOOK_SETUP_GUIDE.md](./WEBHOOK_SETUP_GUIDE.md) - Webhook 端点暴露指南
- [docker-compose.yml](./docker-compose.yml) - Docker Compose 配置

---

**最后更新**: 2026-01-09  
**维护者**: Mika Taiko Chatbot Team
