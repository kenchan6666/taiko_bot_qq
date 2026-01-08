# Mika Taiko Chatbot

一个基于 Taiko no Tatsujin 主题的 QQ 聊天机器人，名为 "Mika"。使用 LangBot 进行 QQ 集成，FastAPI 后端提供高级逻辑处理。

## 功能特性

- 🥁 **主题化对话**: 所有回复都融入太鼓达人游戏元素（"Don!", "Katsu!", emojis 🥁🎶）
- 🎵 **歌曲查询**: 支持查询太鼓达人歌曲信息，包括难度等级和 BPM
- 🧠 **记忆功能**: 机器人能记住用户偏好和之前的对话内容
- 🖼️ **多模态支持**: 支持处理图片内容（游戏截图分析）
- 🔒 **隐私保护**: 使用哈希用户 ID，90 天自动删除对话历史
- ⚡ **高并发**: 支持多群组部署，处理 100+ 并发请求

## 技术栈

- **后端框架**: FastAPI + Uvicorn
- **数据库**: MongoDB (via Beanie ODM)
- **工作流编排**: Temporal.io
- **QQ 集成**: LangBot
- **AI 模型**: gpt-4o (via OpenRouter)
- **依赖管理**: Poetry
- **部署**: Docker Compose

## 项目结构

```
taiko_bot/
├── src/
│   ├── steps/          # 5步处理链
│   ├── models/         # Beanie 数据模型
│   ├── services/       # 业务服务层
│   ├── workflows/      # Temporal 工作流
│   ├── activities/     # Temporal 活动
│   ├── api/            # FastAPI 路由和中间件
│   ├── utils/          # 工具函数
│   ├── config.py       # 配置管理
│   └── prompts.py      # 提示词模板
├── tests/              # 测试文件
├── docker/             # Docker 配置
└── scripts/            # 工具脚本
```

## 快速开始

### 前置要求

- Python 3.12+
- Poetry 1.6+
- MongoDB 7.0+
- Temporal Server
- Docker & Docker Compose (可选)

### 安装步骤

1. **克隆仓库并安装依赖**:
   ```bash
   poetry install
   poetry shell
   ```

2. **配置环境变量**:
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的 API 密钥
   ```

3. **启动 MongoDB 和 Temporal**:
   ```bash
   docker-compose up -d mongo temporal
   ```

4. **运行应用**:
   ```bash
   # 启动 FastAPI 服务器
   uvicorn src.api.main:app --reload

   # 在另一个终端启动 Temporal Worker
   python src/workers/temporal_worker.py
   ```

详细设置说明请参考 [quickstart.md](specs/1-mika-bot/quickstart.md)

## 开发

### 代码风格

项目使用 Black 进行代码格式化，遵循 PEP 8 规范：

```bash
# 格式化代码
poetry run black src/ tests/

# 类型检查
poetry run mypy src/
```

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行测试并生成覆盖率报告
poetry run pytest --cov=src --cov-report=html
```

## 配置说明

所有敏感信息（API 密钥等）必须通过环境变量提供。配置文件（`.env.example`）中只包含占位符。

**重要**: 不要将 `.env` 文件提交到版本控制系统！

## 许可证

MIT License

## 相关文档

- [功能规范](specs/1-mika-bot/spec.md)
- [实现计划](specs/1-mika-bot/plan.md)
- [任务列表](specs/1-mika-bot/tasks.md)
- [快速开始指南](specs/1-mika-bot/quickstart.md)
