# 端到端测试指南 (End-to-End Testing Guide)

**目的**: 完整测试 Mika Bot 的所有功能，从接收消息到返回响应

---

## 📋 前置准备

### 1. 环境检查清单

- [ ] MongoDB 运行中（Docker 或本地）
- [ ] Temporal Server 运行中（Docker 或本地）
- [ ] Python 虚拟环境已激活
- [ ] 环境变量已配置（`.env` 文件）
- [ ] LLM API Key 已配置

### 2. 启动服务

#### 终端 1: MongoDB（如果使用 Docker）
```bash
docker run -d -p 27017:27017 --name mongo mongo:latest
```

#### 终端 2: Temporal Server（如果使用 Docker）
```bash
docker run -d -p 7233:7233 -p 8088:8088 --name temporal temporalio/auto-setup:latest
```

#### 终端 3: FastAPI 服务
```bash
cd c:\Users\陈逸楠\.vscode\taiko_bot
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**验证**: 访问 http://localhost:8000/docs 应该看到 Swagger UI

#### 终端 4: Temporal Worker
```bash
cd c:\Users\陈逸楠\.vscode\taiko_bot
poetry run python -m src.workers.temporal_worker
```

**验证**: 应该看到 "Worker started" 日志

#### 终端 5: ngrok（用于 QQ 测试）
```bash
ngrok http 8000
```

**验证**: 应该看到类似 `Forwarding https://xxxx-xx-xx-xx-xx.ngrok-free.app -> http://localhost:8000`

---

## 🧪 测试流程

### 阶段 1: 本地 API 测试（不使用 ngrok）

#### 测试 1.1: 健康检查

```bash
curl http://localhost:8000/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T12:00:00Z"
}
```

#### 测试 1.2: 基本消息处理（带 Mika 提及）

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }'
```

**验证点**:
- [ ] 返回 HTTP 200
- [ ] 响应包含 `response` 字段
- [ ] 响应内容包含问候语
- [ ] FastAPI 日志显示消息已处理
- [ ] Temporal Worker 日志显示工作流已执行

**预期响应示例**:
```json
{
  "response": "你好！我是 Mika，太鼓之魂！🥁 很高兴认识你！",
  "status": "success"
}
```

#### 测试 1.3: 消息过滤（无 Mika 提及）

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "今天天气不错",
    "images": []
  }'
```

**验证点**:
- [ ] 返回 HTTP 200
- [ ] 响应可能为空或包含过滤信息
- [ ] FastAPI 日志显示消息被过滤

#### 测试 1.4: 意图检测 - 问候

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }'
```

**验证点**:
- [ ] 响应使用 `intent_greeting` 提示
- [ ] 响应热情友好
- [ ] 日志显示 `intent=greeting`

#### 测试 1.5: 意图检测 - 歌曲推荐（场景化）

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 推荐一些高 BPM 的歌曲",
    "images": []
  }'
```

**验证点**:
- [ ] 响应使用 `scenario_song_recommendation_high_bpm` 提示
- [ ] 推荐高 BPM 歌曲（如 千本桜 200 BPM）
- [ ] 日志显示 `intent=song_recommendation, scenario=song_recommendation_high_bpm`

#### 测试 1.6: 歌曲查询

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 千本桜的BPM是多少？",
    "images": []
  }'
```

**验证点**:
- [ ] 响应包含准确的 BPM 信息
- [ ] 响应包含歌曲名称
- [ ] 日志显示歌曲查询成功

**预期响应示例**:
```json
{
  "response": "千本桜的 BPM 是 200！🥁 这是一首非常快的歌曲，适合挑战！",
  "status": "success"
}
```

#### 测试 1.7: 模糊匹配歌曲查询

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 千本樱的难度是多少？",
    "images": []
  }'
```

**验证点**:
- [ ] 即使拼写略有不同，也能找到歌曲
- [ ] 返回正确的难度信息

#### 测试 1.8: 游戏技巧请求

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 有什么游戏技巧吗？",
    "images": []
  }'
```

**验证点**:
- [ ] 响应使用 `intent_game_tips` 提示
- [ ] 提供实用的游戏建议
- [ ] 日志显示 `intent=game_tips`

#### 测试 1.9: 新手建议（场景化）

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 新手怎么开始练习？",
    "images": []
  }'
```

**验证点**:
- [ ] 响应使用 `scenario_difficulty_advice_beginner` 提示
- [ ] 提供新手友好的建议
- [ ] 日志显示 `intent=difficulty_advice, scenario=difficulty_advice_beginner`

#### 测试 1.10: 多轮对话（记忆功能）

```bash
# 第一轮：表达偏好
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 我喜欢高 BPM 的歌曲",
    "images": []
  }'

# 等待几秒，然后第二轮：基于偏好的推荐
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 推荐一些歌曲",
    "images": []
  }'
```

**验证点**:
- [ ] 第二轮响应应该提到用户喜欢高 BPM
- [ ] 推荐高 BPM 歌曲
- [ ] 日志显示使用了 `memory_aware` 提示

#### 测试 1.11: 图像处理（需要有效的 JPEG base64）

```bash
# 注意：需要提供有效的 base64 编码的 JPEG 图像
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 看看这张图片",
    "images": ["/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="]
  }'
```

**验证点**:
- [ ] 响应使用 `image_analysis` 提示
- [ ] 如果图像是太鼓相关，提供详细分析
- [ ] 如果图像不是太鼓相关，礼貌地重定向
- [ ] 日志显示图像验证通过

---

### 阶段 2: 通过 ngrok 测试（模拟 QQ 环境）

#### 测试 2.1: 获取 ngrok URL

从 ngrok 终端复制 HTTPS URL，例如：
```
https://xxxx-xx-xx-xx-xx.ngrok-free.app
```

#### 测试 2.2: 配置 LangBot Webhook

在 LangBot 配置中设置 webhook URL：
```
https://xxxx-xx-xx-xx-xx.ngrok-free.app/webhook/langbot
```

#### 测试 2.3: 通过 ngrok 发送测试消息

```bash
curl -X POST https://xxxx-xx-xx-xx-xx.ngrok-free.app/webhook/langbot \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{
    "group_id": "test_group_001",
    "user_id": "test_user_001",
    "message": "Mika, 你好！",
    "images": []
  }'
```

**验证点**:
- [ ] ngrok 日志显示请求已转发
- [ ] FastAPI 日志显示消息已接收
- [ ] 响应正常返回

---

### 阶段 3: 真实 QQ 群组测试

#### 测试 3.1: 在 QQ 群组中发送消息

1. 在配置了 webhook 的 QQ 群组中发送：
   ```
   Mika, 你好！
   ```

**验证点**:
- [ ] Bot 在群组中回复
- [ ] 回复内容正确
- [ ] 回复时间合理（< 5 秒）

#### 测试 3.2: 测试各种意图

在 QQ 群组中依次测试：

1. **问候**: `Mika, 你好！`
2. **帮助**: `Mika, 你能做什么？`
3. **歌曲查询**: `Mika, 千本桜的BPM是多少？`
4. **歌曲推荐**: `Mika, 推荐一些高 BPM 的歌曲`
5. **游戏技巧**: `Mika, 有什么游戏技巧吗？`
6. **新手建议**: `Mika, 新手怎么开始？`

**验证点**:
- [ ] 每个消息都得到合适的回复
- [ ] 意图检测正确
- [ ] 场景检测正确（如果适用）

#### 测试 3.3: 测试多轮对话

1. 发送: `Mika, 我喜欢高 BPM 的歌曲`
2. 等待回复
3. 发送: `Mika, 推荐一些歌曲`

**验证点**:
- [ ] 第二轮回复应该提到用户喜欢高 BPM
- [ ] 推荐高 BPM 歌曲

#### 测试 3.4: 测试图像处理

在 QQ 群组中发送一张图片（太鼓相关或非太鼓相关）

**验证点**:
- [ ] Bot 能够识别图像
- [ ] 提供合适的分析或重定向

---

## 🔍 验证检查清单

### 功能验证

- [ ] **消息过滤**: 无 Mika 提及的消息被正确过滤
- [ ] **意图检测**: 各种意图被正确识别
- [ ] **场景检测**: 场景化提示被正确选择
- [ ] **歌曲查询**: 准确返回歌曲信息
- [ ] **模糊匹配**: 拼写变体能正确匹配
- [ ] **图像处理**: 图像验证和分析正常工作
- [ ] **记忆功能**: 多轮对话中偏好被记住
- [ ] **提示选择**: 优先级正确（场景 > 意图 > use_case）

### 性能验证

- [ ] **响应时间**: 大多数请求 < 3 秒
- [ ] **并发处理**: 多个请求能同时处理
- [ ] **错误恢复**: 服务异常时能优雅降级

### 日志验证

检查 FastAPI 和 Temporal Worker 日志：

- [ ] 意图检测日志: `intent_detected intent=xxx`
- [ ] 场景检测日志: `scenario_detected scenario=xxx`
- [ ] 提示选择日志: `scenario_prompt_selected` 或 `intent_prompt_selected`
- [ ] 歌曲查询日志: 显示查询结果
- [ ] 错误日志: 如有错误，应记录详细信息

---

## 🐛 常见问题排查

### 问题 1: ngrok 连接失败

**症状**: 无法通过 ngrok URL 访问服务

**解决方案**:
1. 检查 ngrok 是否运行: `ngrok http 8000`
2. 检查 FastAPI 是否运行: `curl http://localhost:8000/health`
3. 检查防火墙设置
4. 尝试使用 ngrok 的 HTTP URL 而不是 HTTPS

### 问题 2: Temporal Worker 未处理工作流

**症状**: 消息被接收但没有响应

**解决方案**:
1. 检查 Temporal Worker 是否运行
2. 检查 Temporal Server 连接: `curl http://localhost:8088`
3. 查看 Temporal Worker 日志中的错误
4. 检查工作流是否在 Temporal UI 中显示: http://localhost:8088

### 问题 3: MongoDB 连接失败

**症状**: 日志显示数据库连接错误

**解决方案**:
1. 检查 MongoDB 是否运行: `docker ps | grep mongo`
2. 检查连接字符串: `MONGO_URL` 环境变量
3. 检查网络连接: `telnet localhost 27017`

### 问题 4: LLM API 调用失败

**症状**: 响应为空或错误

**解决方案**:
1. 检查 API Key 配置: `LLM_API_KEY` 环境变量
2. 检查 API 配额和限制
3. 查看 LLM 服务日志
4. 测试 API Key: 使用 curl 直接调用 LLM API

### 问题 5: 意图检测不准确

**症状**: 意图被错误分类

**解决方案**:
1. 检查日志中的意图检测结果
2. 查看 `src/services/intent_detection.py` 中的模式
3. 考虑启用 LLM 辅助检测: `use_llm=True`

---

## 📊 测试报告模板

```
测试日期: 2026-01-09
测试人员: [你的名字]
测试环境: [本地/开发/生产]

### 测试结果

#### 基本功能
- [ ] 健康检查: ✓/✗
- [ ] 消息过滤: ✓/✗
- [ ] 基本消息处理: ✓/✗

#### 意图检测
- [ ] 问候意图: ✓/✗
- [ ] 歌曲推荐意图: ✓/✗
- [ ] 歌曲查询意图: ✓/✗
- [ ] 游戏技巧意图: ✓/✗

#### 场景检测
- [ ] 高 BPM 推荐场景: ✓/✗
- [ ] 新手建议场景: ✓/✗

#### 歌曲功能
- [ ] 精确查询: ✓/✗
- [ ] 模糊匹配: ✓/✗
- [ ] 缓存刷新: ✓/✗

#### 图像处理
- [ ] 图像验证: ✓/✗
- [ ] 太鼓图像分析: ✓/✗
- [ ] 非太鼓图像处理: ✓/✗

#### 记忆功能
- [ ] 偏好学习: ✓/✗
- [ ] 多轮对话: ✓/✗
- [ ] 偏好持久化: ✓/✗

#### 性能
- [ ] 平均响应时间: ___ 秒
- [ ] 最长响应时间: ___ 秒
- [ ] 并发处理: ✓/✗

### 发现的问题

1. [问题描述]
   - 严重程度: [高/中/低]
   - 影响范围: [描述]
   - 建议修复: [描述]

### 总体评估

- 功能完整性: [%]
- 性能表现: [%]
- 稳定性: [%]

### 建议

- [建议 1]
- [建议 2]
```

---

## 🚀 快速测试脚本

创建一个快速测试脚本 `scripts/e2e_test.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== E2E 测试开始 ==="

# 健康检查
echo "1. 健康检查..."
curl -s "$BASE_URL/health" | jq .

# 基本消息
echo "2. 基本消息..."
curl -s -X POST "$BASE_URL/webhook/langbot" \
  -H "Content-Type: application/json" \
  -d '{"group_id":"test","user_id":"test","message":"Mika, 你好！","images":[]}' | jq .

# 歌曲查询
echo "3. 歌曲查询..."
curl -s -X POST "$BASE_URL/webhook/langbot" \
  -H "Content-Type: application/json" \
  -d '{"group_id":"test","user_id":"test","message":"Mika, 千本桜的BPM是多少？","images":[]}' | jq .

echo "=== E2E 测试完成 ==="
```

---

## 📝 注意事项

1. **测试数据**: 使用测试用户 ID 和群组 ID，避免污染生产数据
2. **速率限制**: 注意 API 速率限制，避免触发限制
3. **日志级别**: 测试时使用 DEBUG 级别日志以便排查问题
4. **环境隔离**: 使用独立的测试数据库（如果可能）
5. **清理数据**: 测试后清理测试数据

---

**更多信息**: 
- 查看 `NGROK_QQ_TEST_GUIDE.md` 了解 QQ 测试详细步骤
- 查看 `PHASE7_TEST_GUIDE.md` 了解意图检测测试
- 查看 `PHASE7_IMPLEMENTATION_SUMMARY.md` 了解功能实现细节
