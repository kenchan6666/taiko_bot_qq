# 服务启动指南

## 🚀 完整启动流程

### 步骤 1: 启动 Docker 服务

```powershell
# 方法 1: 使用脚本（推荐）
.\scripts\start_services.ps1

# 方法 2: 直接使用 docker compose
docker compose -f docker-compose.yml up -d
```

**等待时间**: 约 60 秒（Temporal 需要最长时间启动）

### 步骤 2: 验证 Docker 服务

```powershell
# 检查容器状态
docker ps

# 应该看到所有容器都是 "Up" 状态
# - mika_bot_mongodb
# - mika_bot_postgresql  
# - mika_bot_temporal
```

**验证 Temporal**:
- 打开浏览器: http://localhost:8088
- 如果能看到 Temporal Web UI，说明启动成功

### 步骤 3: 启动 FastAPI

**新开一个终端**:
```bash
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**验证**: 访问 http://localhost:8000/docs

### 步骤 4: 启动 Temporal Worker

**再开一个终端**:
```bash
poetry run python -m src.workers.temporal_worker
```

**应该看到**:
```
temporal_client_connected
Worker started
```

### 步骤 5: 启动 ngrok（用于 QQ 测试）

**再开一个终端**:
```bash
ngrok http 8000
```

**复制 HTTPS URL**，例如: `https://xxxx-xx-xx-xx-xx.ngrok-free.app`

---

## ⚡ 快速启动（一键）

如果你想一次性启动所有服务（除了 ngrok），可以使用：

```powershell
.\scripts\start_all.ps1
```

这会启动：
- ✅ Docker 服务（MongoDB, Temporal, PostgreSQL）
- ✅ FastAPI（后台运行）
- ✅ Temporal Worker（后台运行）

**注意**: 你仍然需要手动启动 ngrok。

---

## 🔍 检查服务状态

```powershell
# 使用检查脚本
.\scripts\check_services.ps1

# 或手动检查
docker ps
curl http://localhost:8000/health
```

---

## ⏱️ 启动时间参考

- **MongoDB**: ~5 秒
- **PostgreSQL**: ~10 秒
- **Temporal**: ~30-60 秒（最慢）
- **FastAPI**: ~3 秒
- **Worker**: ~2 秒

**总时间**: 约 60-90 秒

---

## 🛑 停止服务

```powershell
# 停止 Docker 服务
.\scripts\stop_services.ps1

# 或
docker compose -f docker-compose.yml down

# 停止所有服务（包括 FastAPI 和 Worker）
.\scripts\stop_all.ps1
```

---

## 📋 启动检查清单

- [ ] Docker Desktop 运行中
- [ ] MongoDB 容器运行中
- [ ] PostgreSQL 容器运行中
- [ ] Temporal 容器运行中（等待 60 秒）
- [ ] Temporal Web UI 可访问 (http://localhost:8088)
- [ ] FastAPI 运行中 (http://localhost:8000)
- [ ] Temporal Worker 运行中（看到 "Worker started"）
- [ ] ngrok 运行中（可选，用于 QQ 测试）

---

## 🐛 常见问题

### 问题: Temporal 容器一直重启

**解决方案**:
1. 查看日志: `docker logs mika_bot_temporal --tail 50`
2. 检查 PostgreSQL 是否运行: `docker ps | grep postgresql`
3. 等待更长时间（Temporal 需要 60 秒启动）

### 问题: Worker 无法连接

**解决方案**:
1. 确认 Temporal Server 已完全启动（访问 http://localhost:8088）
2. 等待 60 秒后再启动 Worker
3. 检查配置: `TEMPORAL_HOST=localhost` 和 `TEMPORAL_PORT=7233`

---

## ✅ 成功标志

当所有服务都启动成功后，你应该：

1. **Docker 容器**: 所有容器状态为 "Up"
2. **Temporal Web UI**: http://localhost:8088 可访问
3. **FastAPI**: http://localhost:8000/docs 可访问
4. **Worker**: 终端显示 "Worker started"
5. **测试请求**: 发送测试请求应该得到正常响应（不是回退响应）

---

**提示**: 如果遇到问题，查看 `TROUBLESHOOTING.md` 获取详细帮助。
