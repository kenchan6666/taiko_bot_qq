# Docker 一键启动指南

本指南介绍如何使用 Docker 一键启动 MongoDB、Temporal 等服务。

---

## 📋 前置要求

- [ ] Docker Desktop 已安装并运行
- [ ] docker-compose 可用（Docker Desktop 自带）
- [ ] Python 3.12+ 和 Poetry 已安装

---

## 🚀 快速开始

### 方法 1: 仅启动 Docker 服务（推荐）

#### 启动 Docker 服务

```powershell
poetry run pwsh scripts/start_services.ps1
```

这会启动：
- ✅ MongoDB (端口 27017)
- ✅ Temporal Server (端口 7233, Web UI 8088)
- ✅ PostgreSQL (Temporal 依赖，端口 5432)

#### 然后手动启动其他服务

**终端 1: FastAPI**
```bash
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2: Temporal Worker**
```bash
poetry run python -m src.workers.temporal_worker
```

**终端 3: ngrok**
```bash
ngrok http 8000
```

#### 停止 Docker 服务

```powershell
poetry run pwsh scripts/stop_services.ps1
```

---

### 方法 2: 一键启动所有服务（包括 FastAPI 和 Worker）

#### 启动所有服务

```powershell
poetry run pwsh scripts/start_all.ps1
```

这会启动：
- ✅ Docker 服务（MongoDB, Temporal, PostgreSQL）
- ✅ FastAPI（后台运行）
- ✅ Temporal Worker（后台运行）

**注意**: 你仍然需要手动启动 ngrok。

#### 停止所有服务

```powershell
poetry run pwsh scripts/stop_all.ps1
```

---

## 📊 服务端口

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| MongoDB | 27017 | `mongodb://localhost:27017` |
| Temporal Web UI | 8088 | http://localhost:8088 |
| Temporal gRPC | 7233 | `localhost:7233` |
| PostgreSQL | 5432 | `localhost:5432` |
| FastAPI | 8000 | http://localhost:8000 |
| FastAPI Docs | 8000 | http://localhost:8000/docs |

---

## 🔍 验证服务状态

### 检查 Docker 服务

```powershell
docker compose -f docker-compose.yml ps
```

### 检查服务健康状态

**MongoDB**
```powershell
docker exec mika_bot_mongodb mongosh --eval "db.adminCommand('ping')"
```

**Temporal Web UI**
打开浏览器访问: http://localhost:8088

**FastAPI**
```powershell
curl http://localhost:8000/health
```

---

## 🛠️ 常用命令

### 查看日志

**MongoDB 日志**
```powershell
docker logs mika_bot_mongodb
```

**Temporal 日志**
```powershell
docker logs mika_bot_temporal
```

**所有服务日志**
```powershell
docker compose -f docker-compose.yml logs -f
```

### 重启服务

```powershell
docker compose -f docker-compose.yml restart
```

### 完全清理（删除数据卷）

```powershell
docker compose -f docker-compose.yml down -v
```

**警告**: 这会删除所有数据！

---

## 🐛 故障排查

### 问题 1: 端口已被占用

**症状**: `Error: bind: address already in use`

**解决方案**:
1. 检查端口占用: `netstat -ano | findstr :27017`
2. 停止占用端口的进程
3. 或修改 `docker-compose.yml` 中的端口映射

### 问题 2: Docker 服务启动失败

**症状**: `docker compose up` 失败

**解决方案**:
1. 检查 Docker Desktop 是否运行
2. 查看详细日志: `docker compose -f docker-compose.yml logs`
3. 检查磁盘空间: `docker system df`
4. 清理未使用的资源: `docker system prune`

### 问题 3: MongoDB 连接失败

**症状**: 应用无法连接到 MongoDB

**解决方案**:
1. 检查 MongoDB 是否运行: `docker ps | grep mongo`
2. 检查连接字符串: `MONGO_URL` 环境变量
3. 查看 MongoDB 日志: `docker logs mika_bot_mongodb`

### 问题 4: Temporal 无法启动

**症状**: Temporal Web UI 无法访问

**解决方案**:
1. 等待更长时间（Temporal 需要 30-60 秒启动）
2. 检查 PostgreSQL 是否运行: `docker ps | grep postgres`
3. 查看 Temporal 日志: `docker logs mika_bot_temporal`

---

## 📝 环境变量配置

确保你的 `.env` 文件包含：

```env
# MongoDB
MONGO_URL=mongodb://localhost:27017/mika_bot

# Temporal
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default

# LLM API
LLM_API_KEY=your_api_key_here
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

---

## 🔄 开发工作流

### 日常开发

1. **启动 Docker 服务**
   ```powershell
   poetry run pwsh scripts/start_services.ps1
   ```

2. **启动 FastAPI 和 Worker**（在单独的终端）
   ```bash
   # 终端 1
   poetry run uvicorn src.api.main:app --reload
   
   # 终端 2
   poetry run python -m src.workers.temporal_worker
   ```

3. **开发测试**
   - 代码更改会自动重载（FastAPI `--reload`）
   - Worker 需要手动重启

4. **停止服务**
   ```powershell
   poetry run pwsh scripts/stop_services.ps1
   ```

### 完整测试

1. **启动所有服务**
   ```powershell
   poetry run pwsh scripts/start_all.ps1
   ```

2. **启动 ngrok**
   ```bash
   ngrok http 8000
   ```

3. **运行测试**
   ```bash
   poetry run python scripts/e2e_test_simple.py
   ```

4. **停止所有服务**
   ```powershell
   poetry run pwsh scripts/stop_all.ps1
   ```

---

## 💾 数据持久化

Docker Compose 配置了数据卷，数据会持久化：

- **MongoDB 数据**: `mongodb_data` 卷
- **PostgreSQL 数据**: `postgresql_data` 卷

即使容器停止，数据也不会丢失。

要删除所有数据：
```powershell
docker compose -f docker-compose.yml down -v
```

---

## 🔐 安全注意事项

⚠️ **默认配置仅用于开发环境！**

生产环境需要：
- 更改默认密码
- 使用环境变量管理敏感信息
- 配置网络隔离
- 启用 TLS/SSL
- 设置适当的资源限制

---

## 📚 相关文档

- [端到端测试指南](E2E_TEST_GUIDE.md)
- [ngrok QQ 测试指南](NGROK_QQ_TEST_GUIDE.md)
- [Phase 7 测试指南](PHASE7_TEST_GUIDE.md)

---

## 🆘 获取帮助

如果遇到问题：
1. 查看服务日志
2. 检查 Docker 状态
3. 参考故障排查部分
4. 查看相关文档
