# 快速修复指南

## 🔴 问题: Temporal Worker 无法连接

**错误**: `ConnectionRefused: 127.0.0.1:7233`

**原因**: Temporal Server 未运行或未完全启动

---

## ✅ 解决方案

### 步骤 1: 启动 Docker 服务

```powershell
# 如果服务未运行，启动它们
docker compose -f docker-compose.yml up -d

# 等待 30-60 秒让 Temporal 完全启动
Start-Sleep -Seconds 45
```

### 步骤 2: 验证服务状态

```powershell
# 检查容器状态
docker ps

# 应该看到:
# - mika_bot_mongodb (运行中)
# - mika_bot_postgresql (运行中)
# - mika_bot_temporal (运行中)
```

### 步骤 3: 检查 Temporal Web UI

打开浏览器访问: http://localhost:8088

如果能看到 Temporal Web UI，说明 Temporal Server 已启动。

### 步骤 4: 启动 Temporal Worker

```bash
poetry run python -m src.workers.temporal_worker
```

**应该看到**:
- `temporal_client_connected`
- `Worker started` 或类似消息

---

## 🎯 完整启动流程

```powershell
# 终端 1: 启动 Docker 服务
docker compose -f docker-compose.yml up -d

# 等待 45 秒
Start-Sleep -Seconds 45

# 终端 2: 启动 FastAPI
poetry run uvicorn src.api.main:app --reload

# 终端 3: 启动 Temporal Worker
poetry run python -m src.workers.temporal_worker

# 终端 4: 启动 ngrok (可选)
ngrok http 8000
```

---

## ⏱️ 等待时间

- **PostgreSQL**: ~10 秒
- **MongoDB**: ~5 秒
- **Temporal**: ~30-60 秒（最慢）

**总等待时间**: 约 60 秒

---

## 🔍 验证所有服务

运行检查脚本（在 PowerShell 中直接运行，不使用 poetry run）：

```powershell
.\scripts\check_services.ps1
```

或者手动检查：

```powershell
# 检查 Temporal Web UI
Invoke-WebRequest -Uri "http://localhost:8088" -UseBasicParsing

# 检查 FastAPI
Invoke-RestMethod -Uri "http://localhost:8000/health"

# 检查 MongoDB
docker exec mika_bot_mongodb mongosh --eval "db.adminCommand('ping')"
```

---

## 📝 注意事项

1. **Temporal 启动最慢**: 需要等待 30-60 秒
2. **健康检查**: 使用 `depends_on` 确保 PostgreSQL 先启动
3. **启动顺序**: PostgreSQL → Temporal → Worker

---

## 🆘 如果仍然失败

1. **查看 Temporal 日志**:
   ```powershell
   docker logs mika_bot_temporal --tail 50
   ```

2. **重启服务**:
   ```powershell
   docker compose -f docker-compose.yml restart temporal
   ```

3. **完全重新启动**:
   ```powershell
   docker compose -f docker-compose.yml down
   docker compose -f docker-compose.yml up -d
   ```
