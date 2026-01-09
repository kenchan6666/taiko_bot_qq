# Phase 7 功能测试指南

**目的**: 快速测试意图分类和场景化提示选择功能

---

## 🚀 快速测试（无需启动服务）

### 方法 1: 使用测试脚本

```bash
# 运行手动测试脚本
poetry run python scripts/test_intent_manual.py
```

这个脚本会测试：
- ✅ 意图检测（12种意图类型）
- ✅ 场景检测（6种场景类型）
- ✅ 组合检测（意图+场景）
- ✅ parse_input 集成
- ✅ 提示模板验证

---

## 🧪 Python REPL 快速测试

### 测试意图检测

```python
# 在 Python REPL 中
import asyncio
from src.services.intent_detection import get_intent_detection_service

service = get_intent_detection_service()

# 测试问候意图
intent = await service.detect_intent("Mika, 你好！")
print(f"意图: {intent}")  # 应该输出: greeting

# 测试歌曲推荐意图
intent = await service.detect_intent("Mika, 推荐一些歌曲")
print(f"意图: {intent}")  # 应该输出: song_recommendation

# 测试场景检测
scenario = service.detect_scenario("推荐高 BPM 歌曲", intent="song_recommendation")
print(f"场景: {scenario}")  # 应该输出: song_recommendation_high_bpm

# 测试组合检测
intent, scenario = await service.detect_intent_and_scenario("推荐一些高 BPM 的歌曲")
print(f"意图: {intent}, 场景: {scenario}")
```

### 测试 parse_input 集成

```python
from src.steps.step1 import parse_input

# 测试意图检测集成
parsed = await parse_input(
    user_id="test_user",
    group_id="test_group",
    message="Mika, 推荐一些高 BPM 的歌曲",
    images=None,
)

print(f"检测到的意图: {parsed.intent}")
print(f"检测到的场景: {parsed.scenario}")
```

### 测试提示模板

```python
from src.prompts import get_prompt_manager

manager = get_prompt_manager()

# 检查意图特定提示是否存在
try:
    prompt = manager.get_prompt(
        name="intent_greeting",
        bot_name="Mika",
        language="zh",
        user_message="你好！",
        conversation_history="",
    )
    print("✓ intent_greeting 提示存在")
    print(f"提示内容（前100字符）: {prompt[:100]}...")
except ValueError as e:
    print(f"✗ intent_greeting 提示不存在: {e}")

# 检查场景化提示是否存在
try:
    prompt = manager.get_prompt(
        name="scenario_song_recommendation_high_bpm",
        bot_name="Mika",
        language="zh",
        user_message="推荐高 BPM 歌曲",
        conversation_history="",
        user_preferences="",
    )
    print("✓ scenario_song_recommendation_high_bpm 提示存在")
except ValueError as e:
    print(f"✗ 场景化提示不存在: {e}")
```

---

## 🔍 端到端测试（需要服务运行）

### 1. 启动服务

```bash
# 终端 1: FastAPI
poetry run uvicorn src.api.main:app --reload

# 终端 2: Temporal Worker
poetry run python -m src.workers.temporal_worker
```

### 2. 测试不同意图

#### 测试问候意图

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, 你好！",
    "images": []
  }'
```

**预期**: Bot 使用 `intent_greeting` 提示，返回热情的问候

#### 测试歌曲推荐场景

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, 推荐一些高 BPM 的歌曲",
    "images": []
  }'
```

**预期**: 
- 检测到意图: `song_recommendation`
- 检测到场景: `song_recommendation_high_bpm`
- 使用 `scenario_song_recommendation_high_bpm` 提示
- 推荐高 BPM 歌曲（如 千本桜 200 BPM）

#### 测试新手建议场景

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, 新手怎么开始？",
    "images": []
  }'
```

**预期**:
- 检测到意图: `difficulty_advice`
- 检测到场景: `difficulty_advice_beginner`
- 使用 `scenario_difficulty_advice_beginner` 提示
- 提供新手友好的建议

#### 测试回退场景

```bash
curl -X POST http://localhost:8000/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "test",
    "user_id": "test",
    "message": "Mika, 今天天气不错",
    "images": []
  }'
```

**预期**:
- 意图检测: `None` 或不确定
- 场景检测: `None`
- 回退到 `general_chat` 或 `memory_aware` 提示
- 仍然返回合理的响应

---

## 📊 验证检查清单

### 意图检测验证

- [ ] 问候消息 → 检测到 `greeting` 意图
- [ ] 帮助请求 → 检测到 `help` 意图
- [ ] 歌曲查询 → 检测到 `song_query` 意图
- [ ] 歌曲推荐 → 检测到 `song_recommendation` 意图
- [ ] 游戏技巧 → 检测到 `game_tips` 意图

### 场景检测验证

- [ ] "推荐高 BPM 歌曲" → 场景 `song_recommendation_high_bpm`
- [ ] "推荐新手歌曲" → 场景 `song_recommendation_beginner_friendly`
- [ ] "新手怎么开始" → 场景 `difficulty_advice_beginner`
- [ ] "高级玩家建议" → 场景 `difficulty_advice_expert`
- [ ] "怎么提高节奏" → 场景 `game_tips_timing`
- [ ] "怎么提高准确" → 场景 `game_tips_accuracy`

### 提示选择验证

- [ ] 场景化提示优先级最高（场景 > 意图 > use_case）
- [ ] 意图特定提示在场景不存在时使用
- [ ] 回退到 use_case 提示（memory_aware / general_chat）
- [ ] 日志记录意图和场景选择

---

## 🐛 调试技巧

### 1. 查看意图检测日志

在 FastAPI 日志中查找：
```
intent_detected intent=greeting score=1
scenario_detected scenario=song_recommendation_high_bpm
```

### 2. 查看提示选择日志

在 FastAPI 日志中查找：
```
scenario_prompt_selected scenario=song_recommendation_high_bpm
intent_prompt_selected intent=song_recommendation
memory_aware_prompt_selected
general_chat_prompt_selected
```

### 3. 测试特定意图

```python
# 在 Python REPL 中测试特定消息
from src.services.intent_detection import get_intent_detection_service
import asyncio

service = get_intent_detection_service()

# 测试你的消息
message = "你的测试消息"
intent, scenario = await service.detect_intent_and_scenario(message)
print(f"意图: {intent}, 场景: {scenario}")
```

---

## ✅ 预期行为

### 成功场景

1. **明确的意图和场景**:
   - 消息: "推荐高 BPM 歌曲"
   - 意图: `song_recommendation`
   - 场景: `song_recommendation_high_bpm`
   - 提示: `scenario_song_recommendation_high_bpm`
   - 响应: 推荐高 BPM 歌曲（如 千本桜 200 BPM）

2. **只有意图，无场景**:
   - 消息: "推荐一些歌曲"
   - 意图: `song_recommendation`
   - 场景: `None`
   - 提示: `intent_song_recommendation`
   - 响应: 一般歌曲推荐

3. **无意图，回退**:
   - 消息: "今天天气不错"
   - 意图: `None`
   - 场景: `None`
   - 提示: `general_chat` 或 `memory_aware`
   - 响应: 通用聊天响应

---

## 📝 测试报告模板

测试完成后，记录结果：

```
测试日期: 2026-01-08
测试人员: [你的名字]

意图检测测试:
- greeting: ✓/✗
- help: ✓/✗
- song_query: ✓/✗
- song_recommendation: ✓/✗
- game_tips: ✓/✗

场景检测测试:
- song_recommendation_high_bpm: ✓/✗
- song_recommendation_beginner_friendly: ✓/✗
- difficulty_advice_beginner: ✓/✗
- game_tips_timing: ✓/✗

提示选择测试:
- 场景化提示优先级: ✓/✗
- 意图特定提示: ✓/✗
- 回退机制: ✓/✗

问题记录:
- [记录任何发现的问题]
```

---

**更多信息**: 查看 `PHASE7_IMPLEMENTATION_SUMMARY.md`
