# 清理任务配置指南

**目的**: 配置 90 天对话历史自动清理任务

**适用场景**: 自动删除超过 90 天的对话记录，符合隐私要求和存储成本控制

---

## 概述

根据 FR-005 和 T080-T081，系统需要自动删除超过 90 天的对话记录。有两种配置方式：

1. **Temporal Scheduled Workflow** (推荐): 使用 Temporal 的定时工作流功能
2. **Cron Job**: 使用系统 cron 或任务调度器

---

## 方法 1: Temporal Scheduled Workflow (推荐)

### 优势

- 与现有 Temporal 基础设施集成
- 自动重试和错误处理
- 工作流历史记录和监控
- 易于管理和调试

### 实现步骤

#### 1. 创建 Scheduled Workflow

创建 `src/workflows/cleanup_workflow.py`:

```python
from datetime import timedelta
from temporalio import workflow

@workflow.defn(name="cleanup_old_conversations")
class CleanupConversationsWorkflow:
    @workflow.run
    async def run(self) -> int:
        # Import activity here to avoid import issues
        from src.activities.cleanup_activity import cleanup_old_conversations_activity
        
        # Execute cleanup activity
        deleted_count = await workflow.execute_activity(
            cleanup_old_conversations_activity,
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        return deleted_count
```

#### 2. 创建 Cleanup Activity

创建 `src/activities/cleanup_activity.py`:

```python
from temporalio import activity
from src.models.conversation import Conversation
from datetime import datetime, timedelta

@activity.defn(name="cleanup_old_conversations")
async def cleanup_old_conversations_activity(days: int = 90) -> int:
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    expired_conversations = await Conversation.find(
        Conversation.expires_at < cutoff_date
    ).to_list()
    
    count = len(expired_conversations)
    if count > 0:
        for conv in expired_conversations:
            await conv.delete()
    
    return count
```

#### 3. 注册 Scheduled Workflow

在 Temporal Worker 中注册 scheduled workflow:

```python
# In src/workers/temporal_worker.py
from temporalio.client import Client
from temporalio.workflow import WorkflowHandle

# Schedule cleanup to run daily at 2 AM UTC
async def schedule_cleanup_workflow(client: Client):
    handle = await client.start_workflow(
        "cleanup_old_conversations",
        id="cleanup-scheduled-workflow",
        task_queue="mika-bot-task-queue",
        # Schedule: Daily at 2 AM UTC
        cron_schedule="0 2 * * *",
    )
    return handle
```

#### 4. 启动 Scheduled Workflow

在应用启动时启动 scheduled workflow:

```python
# In src/api/main.py lifespan startup
from src.workers.temporal_worker import schedule_cleanup_workflow
from src.api.routes.langbot import get_temporal_client

async def lifespan(app: FastAPI):
    # ... existing startup code ...
    
    # Schedule cleanup workflow
    try:
        client = await get_temporal_client()
        await schedule_cleanup_workflow(client)
        logger.info("cleanup_workflow_scheduled", event_type="startup_success")
    except Exception as e:
        logger.warning("cleanup_workflow_schedule_failed", error=str(e))
    
    yield
    # ... existing shutdown code ...
```

---

## 方法 2: Cron Job (简单直接)

### 优势

- 简单直接，不依赖 Temporal
- 易于调试和手动执行
- 适合小型部署

### 实现步骤

#### 1. 使用系统 Cron (Linux/macOS)

编辑 crontab:

```bash
crontab -e
```

添加以下行（每天凌晨 2 点执行）:

```cron
0 2 * * * cd /path/to/taiko_bot && poetry run python scripts/cleanup_old_conversations.py >> /var/log/mika_bot_cleanup.log 2>&1
```

#### 2. 使用 Windows Task Scheduler

1. 打开 Task Scheduler
2. 创建新任务
3. 设置触发器: 每天凌晨 2 点
4. 设置操作: 运行 `python scripts/cleanup_old_conversations.py`
5. 设置工作目录: `C:\Users\陈逸楠\.vscode\taiko_bot`

#### 3. 使用 Docker Cron (容器化部署)

在 `docker-compose.yml` 中添加 cron 服务:

```yaml
services:
  cleanup-cron:
    image: mika_bot_backend:latest
    command: >
      sh -c "
        echo '0 2 * * * python scripts/cleanup_old_conversations.py' > /etc/cron.d/cleanup
        chmod 0644 /etc/cron.d/cleanup
        crontab /etc/cron.d/cleanup
        cron -f
      "
    volumes:
      - .:/app
    depends_on:
      - mongodb
    environment:
      - MONGODB_URL=mongodb://mongodb:27017/
      - MONGODB_DATABASE=mika_bot
    restart: unless-stopped
```

---

## 验证清理任务

### 1. 手动测试清理脚本

```bash
# Dry run (查看会删除多少条记录)
python scripts/cleanup_old_conversations.py --dry-run

# 实际执行清理
python scripts/cleanup_old_conversations.py

# 指定保留天数
python scripts/cleanup_old_conversations.py --days 60
```

### 2. 验证 Temporal Scheduled Workflow

```bash
# 查看 Temporal Web UI
# 访问 http://localhost:8088
# 查找 "cleanup_old_conversations" workflow

# 或使用 tctl
tctl workflow list --query "WorkflowType='cleanup_old_conversations'"
```

### 3. 检查清理结果

```bash
# 检查 MongoDB 中的对话记录
# 应该没有 expires_at < 90 days ago 的记录

# 使用 MongoDB shell
mongosh mika_bot
db.conversations.find({expires_at: {$lt: new Date(Date.now() - 90*24*60*60*1000)}}).count()
# 应该返回 0
```

---

## 配置选项

### 环境变量

可以通过环境变量配置清理任务:

```bash
# 保留天数 (默认: 90)
CLEANUP_RETENTION_DAYS=90

# Cron 调度 (默认: 每天凌晨 2 点 UTC)
CLEANUP_CRON_SCHEDULE="0 2 * * *"
```

### 清理脚本参数

```bash
# 查看帮助
python scripts/cleanup_old_conversations.py --help

# 选项:
# --days: 保留天数 (默认: 90)
# --dry-run: 仅查看，不实际删除
```

---

## 监控和日志

### 日志位置

- **清理脚本日志**: 结构化 JSON 日志输出到 stdout
- **Temporal Workflow 日志**: 在 Temporal Web UI 中查看
- **Cron 日志**: 系统日志或指定的日志文件

### 监控指标

建议监控以下指标:

- 清理执行频率
- 每次清理删除的记录数
- 清理执行时间
- 清理失败次数

### 告警设置

建议设置以下告警:

- 清理任务连续失败
- 清理执行时间过长 (> 5 分钟)
- 数据库连接失败

---

## 故障排查

### 问题 1: 清理脚本无法连接数据库

**症状**: 脚本报错 "database_connected" 失败

**解决方案**:
1. 检查 MongoDB 是否运行: `docker-compose ps mongodb`
2. 验证 `MONGODB_URL` 环境变量
3. 检查网络连接和防火墙规则

### 问题 2: Temporal Scheduled Workflow 不执行

**症状**: Workflow 已注册但不执行

**解决方案**:
1. 检查 Temporal Worker 是否运行: `docker-compose ps temporal-worker`
2. 验证 cron schedule 格式正确
3. 查看 Temporal Web UI 中的 workflow 状态
4. 检查 Temporal 日志: `docker-compose logs temporal-worker`

### 问题 3: Cron Job 不执行

**症状**: Cron 任务已配置但不运行

**解决方案**:
1. 检查 cron 服务是否运行: `systemctl status cron` (Linux)
2. 验证 crontab 语法正确
3. 检查 cron 日志: `/var/log/cron` (Linux) 或 Event Viewer (Windows)
4. 确认脚本路径和权限正确

---

## 最佳实践

1. **定期监控**: 定期检查清理任务执行情况
2. **备份数据**: 在清理前考虑备份重要数据（如果需要）
3. **测试环境**: 在测试环境先验证清理逻辑
4. **日志保留**: 保留清理任务的执行日志用于审计
5. **错误处理**: 确保清理任务失败时不会影响主应用

---

## 相关文档

- [scripts/cleanup_old_conversations.py](./scripts/cleanup_old_conversations.py) - 清理脚本
- [src/models/conversation.py](./src/models/conversation.py) - Conversation 模型
- [Temporal 文档](https://docs.temporal.io) - Temporal Scheduled Workflows

---

**最后更新**: 2026-01-09  
**维护者**: Mika Taiko Chatbot Team
