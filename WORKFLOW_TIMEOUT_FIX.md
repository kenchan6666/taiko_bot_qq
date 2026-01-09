# 工作流超时修复

## 🔴 问题

工作流执行时卡住，没有响应。可能的原因：
1. **Temporal Worker 没有运行** - 工作流无法执行
2. **没有设置超时** - 工作流可能无限等待
3. **活动执行失败** - 某个活动卡住或失败

## ✅ 修复内容

### 1. 添加超时设置

在 `src/api/routes/langbot.py` 中添加了超时配置：

```python
result = await client.execute_workflow(
    ProcessMessageWorkflow.run,
    args=[...],
    id=workflow_id,
    task_queue="mika-bot-task-queue",
    execution_timeout=timedelta(minutes=2),  # 总超时：2分钟
    run_timeout=timedelta(minutes=1),  # 单次运行超时：1分钟
    task_timeout=timedelta(seconds=30),  # 单个任务超时：30秒
)
```

### 2. 添加工作流启动日志

现在会记录工作流启动信息：
```json
{
  "event": "workflow_starting",
  "workflow_id": "process_message_...",
  "user_id": "24439392...",
  "message_type": "private"
}
```

### 3. 增强错误处理

工作流执行错误会被捕获并记录详细信息。

## 🔍 诊断步骤

### 步骤 1: 检查 Temporal Worker 是否运行

```powershell
# 检查是否有 Worker 进程
Get-Process python | Where-Object {$_.CommandLine -like "*temporal_worker*"}

# 或手动启动 Worker
poetry run python -m src.workers.temporal_worker
```

**如果没有 Worker 运行**：
- 工作流会一直等待，直到超时
- 需要启动 Worker 才能执行工作流

### 步骤 2: 检查 Temporal Server 状态

```powershell
# 检查 Temporal 容器
docker ps | findstr temporal

# 检查 Temporal Web UI
# 打开浏览器: http://localhost:8088
```

### 步骤 3: 查看工作流执行状态

在 Temporal Web UI (http://localhost:8088) 中：
1. 查看 "Workflows" 页面
2. 搜索你的 `workflow_id`
3. 查看工作流状态和错误信息

## ⚠️ 常见问题

### 问题 1: Worker 没有运行

**症状**: 工作流启动但没有执行，最终超时

**解决方案**:
```bash
# 启动 Worker（新终端）
poetry run python -m src.workers.temporal_worker
```

### 问题 2: 活动执行失败

**症状**: 工作流启动，但某个活动失败或超时

**解决方案**:
1. 查看 Temporal Web UI 中的活动执行历史
2. 检查活动日志
3. 确认所有依赖服务（MongoDB, LLM API）正常运行

### 问题 3: 超时设置太短

**症状**: 工作流在完成前超时

**解决方案**: 增加超时时间：
```python
execution_timeout=timedelta(minutes=5),  # 增加到 5 分钟
run_timeout=timedelta(minutes=3),  # 增加到 3 分钟
```

## 📋 完整启动检查清单

- [ ] Docker 服务运行中（MongoDB, Temporal, PostgreSQL）
- [ ] Temporal Server 可访问 (http://localhost:8088)
- [ ] **Temporal Worker 运行中** ⚠️ **最重要**
- [ ] FastAPI 运行中
- [ ] 所有服务日志正常

## 🚀 快速启动 Worker

```bash
# 终端 1: Docker 服务
docker compose -f docker-compose.yml up -d

# 等待 60 秒让 Temporal 启动

# 终端 2: FastAPI
poetry run uvicorn src.api.main:app --reload

# 终端 3: Temporal Worker（重要！）
poetry run python -m src.workers.temporal_worker
```

---

**关键提示**: 如果没有运行 Temporal Worker，工作流会一直等待，直到超时。确保 Worker 正在运行！
