# 快速启动指南

最简单的启动方式，适合日常开发。

---

## 🚀 一键启动（推荐）

### 步骤 1: 启动 Docker 服务

```powershell
poetry run pwsh scripts/start_services.ps1
```

这会启动：
- ✅ MongoDB
- ✅ Temporal Server
- ✅ PostgreSQL

**等待**: 脚本会自动等待服务就绪（约 30 秒）

### 步骤 2: 启动 FastAPI

**新开一个终端**:
```bash
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 步骤 3: 启动 Temporal Worker

**再开一个终端**:
```bash
poetry run python -m src.workers.temporal_worker
```

### 步骤 4: 启动 ngrok（用于 QQ 测试）

**再开一个终端**:
```bash
ngrok http 8000
```

---

## ✅ 验证服务

### 检查所有服务

1. **MongoDB**: `docker ps | grep mongo` ✅
2. **Temporal**: 打开 http://localhost:8088 ✅
3. **FastAPI**: 打开 http://localhost:8000/docs ✅
4. **Worker**: 查看终端日志，应该显示 "Worker started" ✅
5. **ngrok**: 查看 ngrok 终端，应该显示 HTTPS URL ✅

### 快速测试

```bash
curl http://localhost:8000/health
```

应该返回: `{"status":"healthy",...}`

---

## 🛑 停止服务

### 停止 Docker 服务

```powershell
poetry run pwsh scripts/stop_services.ps1
```

### 停止 FastAPI 和 Worker

在各自的终端按 `Ctrl+C`

### 停止 ngrok

在 ngrok 终端按 `Ctrl+C`

---

## 📝 完整启动命令总结

```powershell
# 终端 1: 启动 Docker 服务
poetry run pwsh scripts/start_services.ps1

# 终端 2: 启动 FastAPI
poetry run uvicorn src.api.main:app --reload

# 终端 3: 启动 Worker
poetry run python -m src.workers.temporal_worker

# 终端 4: 启动 ngrok
ngrok http 8000
```

---

## 🎯 下一步

1. ✅ 所有服务启动后，运行测试: `poetry run python scripts/e2e_test_simple.py`
2. ✅ 配置 LangBot webhook: 使用 ngrok 提供的 HTTPS URL
3. ✅ 在 QQ 群组中测试: 发送 "Mika, 你好！"

---

## 📚 更多信息

- 详细 Docker 设置: [DOCKER_SETUP.md](DOCKER_SETUP.md)
- 端到端测试: [E2E_TEST_GUIDE.md](E2E_TEST_GUIDE.md)
- QQ 测试指南: [NGROK_QQ_TEST_GUIDE.md](NGROK_QQ_TEST_GUIDE.md)
