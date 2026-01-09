# 故障排查指南

## 🔴 问题: 工作流执行失败

**症状**: 收到回退响应 "Don! Mika暂时无法回应，但我会尽快回来的！🥁"

**原因**: Temporal 工作流执行失败，可能的原因：

1. **Temporal Worker 未运行**
2. **Temporal Server 未运行**
3. **工作流执行超时**
4. **Activity 执行失败**

---

## 🔍 诊断步骤

### 步骤 1: 检查服务状态

运行服务状态检查脚本：

```powershell
poetry run pwsh scripts/check_services.ps1
```

**应该看到**:
- ✅ MongoDB 运行正常
- ✅ Temporal Web UI 可访问
- ✅ FastAPI 运行正常
- ✅ Worker 进程正在运行

### 步骤 2: 查看详细错误日志

查看 FastAPI 终端日志，应该看到类似：

```json
{
  "event": "workflow_execution_failed",
  "error": "...",
  "error_type": "...",
  "traceback": "..."
}
```

### 步骤 3: 检查 Temporal Worker 日志

查看运行 Worker 的终端，应该看到：
- Worker 启动消息
- Activity 执行日志
- 任何错误信息

### 步骤 4: 检查 Temporal Web UI

打开 http://localhost:8088，查看：
- 工作流执行历史
- 失败的工作流
- 错误详情

---

## 🛠️ 常见问题解决方案

### 问题 1: Temporal Worker 未运行

**症状**: Worker 进程不存在

**解决方案**:
```bash
poetry run python -m src.workers.temporal_worker
```

**验证**: 应该看到 "Worker started" 或类似消息

### 问题 2: Temporal Server 未运行

**症状**: 无法连接到 Temporal Server

**解决方案**:
```powershell
# 使用 Docker Compose 启动
poetry run pwsh scripts/start_services.ps1
```

**验证**: 访问 http://localhost:8088 应该看到 Temporal Web UI

### 问题 3: 工作流超时

**症状**: 日志显示超时错误

**解决方案**:
1. 检查 LLM API 是否响应正常
2. 检查网络连接
3. 增加超时时间（如果需要）

### 问题 4: Activity 执行失败

**症状**: 特定 Activity 失败

**检查**:
- Step 1: 检查消息解析逻辑
- Step 2: 检查 MongoDB 连接
- Step 3: 检查歌曲查询服务
- Step 4: 检查 LLM API 配置
- Step 5: 检查数据库写入权限

---

## 📋 快速检查清单

- [ ] MongoDB 运行中 (`docker ps | grep mongo`)
- [ ] Temporal Server 运行中 (`docker ps | grep temporal`)
- [ ] Temporal Worker 运行中 (`ps aux | grep temporal_worker`)
- [ ] FastAPI 运行中 (`curl http://localhost:8000/health`)
- [ ] 环境变量配置正确 (`.env` 文件)
- [ ] LLM API Key 有效
- [ ] 网络连接正常

---

## 🔧 调试命令

### 检查 Temporal 连接

```python
# 在 Python REPL 中
from temporalio.client import Client
from src.config import settings

client = await Client.connect(
    target_host=f"{settings.temporal_host}:{settings.temporal_port}",
    namespace=settings.temporal_namespace,
)
print("Connected!")
```

### 检查 MongoDB 连接

```python
# 在 Python REPL 中
from src.services.database import init_database
await init_database()
print("Connected!")
```

### 手动测试工作流

```python
# 在 Python REPL 中
from temporalio.client import Client
from src.workflows.message_workflow import ProcessMessageWorkflow
from src.config import settings

client = await Client.connect(
    target_host=f"{settings.temporal_host}:{settings.temporal_port}",
    namespace=settings.temporal_namespace,
)

result = await client.execute_workflow(
    ProcessMessageWorkflow.run,
    "test_user",
    "test_group",
    "Mika, 你好！",
    None,
    id="test_workflow_001",
    task_queue="mika-bot-task-queue",
)

print(result)
```

---

## 📝 日志位置

- **FastAPI 日志**: 运行 uvicorn 的终端
- **Temporal Worker 日志**: 运行 worker 的终端
- **Temporal Server 日志**: `docker logs mika_bot_temporal`
- **MongoDB 日志**: `docker logs mika_bot_mongodb`

---

## 🆘 获取帮助

如果问题仍然存在：

1. **收集日志**: 保存所有相关终端的日志
2. **检查配置**: 确认 `.env` 文件配置正确
3. **查看错误详情**: 检查 FastAPI 日志中的 `traceback` 字段
4. **检查 Temporal UI**: 查看工作流执行历史

---

## 🎯 预期行为

**成功的工作流执行**:
```json
{
  "event": "workflow_completed",
  "workflow_id": "process_message_...",
  "hashed_user_id": "...",
  "has_song_info": false
}
```

**失败的工作流执行**:
```json
{
  "event": "workflow_execution_failed",
  "error": "...",
  "error_type": "...",
  "traceback": "..."
}
```
