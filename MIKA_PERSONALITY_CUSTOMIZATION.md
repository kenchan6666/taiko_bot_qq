# Mika 性格自定义指南

**目的**: 说明如何修改 Mika 的性格特征和对话风格

---

## 关于 Phase 12

根据 `specs/1-mika-bot/tasks.md`，当前项目计划只包含 **Phase 1 到 Phase 11**，**没有 Phase 12**。

已完成的阶段：
- Phase 1-2: 基础设施和基础功能
- Phase 3-7: 用户故事实现（聊天、歌曲查询、记忆、多模态）
- Phase 8-9: LangBot 配置和 Docker 部署
- Phase 10: 高级功能和优化
- Phase 11: 全面测试

---

## 如何修改 Mika 的性格

Mika 的性格定义在 **`src/prompts.py`** 文件中的 prompt 模板里。所有 prompt 模板都包含 Mika 的性格描述。

### 主要性格定义位置

#### 1. 基础性格定义 (`general_chat` prompt)

**文件**: `src/prompts.py`  
**函数**: `_initialize_default_prompts()`  
**位置**: 约第 440-465 行

当前性格描述：
```python
template="""You are {bot_name}, a cheerful Taiko no Tatsujin drum spirit! 🥁

Your personality:
- You love Taiko no Tatsujin (太鼓の達人) and everything about rhythm games
- You're playful and enthusiastic, using game terminology like "Don!" and "Katsu!"
- You respond in a friendly, themed way with emojis 🥁🎶
- You speak {language} (user's language)
```

### 修改方法

#### 方法 1: 直接修改 prompt 模板（推荐）

1. **打开文件**: `src/prompts.py`

2. **找到性格定义部分**:
   - 搜索 `"Your personality:"` 或 `"cheerful Taiko"`
   - 主要位置在 `_initialize_default_prompts()` 函数中

3. **修改性格描述**:
   ```python
   Your personality:
   - You are [新的性格特征1]
   - You are [新的性格特征2]
   - You [新的行为方式]
   - [其他性格描述]
   ```

4. **示例修改**:
   ```python
   # 从 "cheerful" 改为 "calm and thoughtful"
   template="""You are {bot_name}, a calm and thoughtful Taiko no Tatsujin drum spirit! 🥁
   
   Your personality:
   - You love Taiko no Tatsujin (太鼓の達人) and enjoy deep discussions about rhythm games
   - You're thoughtful and analytical, providing detailed insights
   - You use game terminology like "Don!" and "Katsu!" but in a more measured way
   - You respond in a friendly, professional manner with occasional emojis 🥁🎶
   - You speak {language} (user's language)
   ```

#### 方法 2: 创建新版本的 prompt（使用版本控制）

利用 Phase 10 实现的 prompt 版本控制功能：

1. **添加新版本的 prompt**:
   ```python
   # 在 _initialize_default_prompts() 函数中添加
   manager.add_prompt(
       name="general_chat",
       template="""You are {bot_name}, a [新性格] Taiko no Tatsujin drum spirit! 🥁
       
       Your personality:
       - [新性格特征1]
       - [新性格特征2]
       ...
       """,
       use_case="general_chat",
       variables=["bot_name", "language", "user_message"],
       version="2.0",  # 新版本
       description="Updated personality: [描述]",
   )
   ```

2. **使用新版本**:
   - 系统默认使用最新版本
   - 或通过 `get_prompt(name, version="2.0")` 指定版本

#### 方法 3: 使用 A/B 测试功能

利用 Phase 10 实现的 A/B 测试功能测试不同性格：

1. **创建两个版本的 prompt**:
   ```python
   # 版本 A: 原有性格
   manager.add_prompt("general_chat", "...", "general_chat", version="1.0")
   
   # 版本 B: 新性格
   manager.add_prompt("general_chat", "...", "general_chat", version="2.0")
   ```

2. **设置 A/B 测试**:
   ```python
   manager.setup_ab_test("general_chat", "1.0", "2.0", traffic_split=0.5)
   ```

### 需要修改的所有 prompt 模板

Mika 的性格在多个 prompt 模板中都有定义，建议统一修改：

1. **`general_chat`** (第 442 行) - 基础聊天
2. **`intent_greeting`** (第 483 行) - 问候意图
3. **`intent_help`** (第 504 行) - 帮助意图
4. **`intent_goodbye`** (第 532 行) - 告别意图
5. **`song_query`** (第 920 行) - 歌曲查询
6. **`memory_aware`** (第 963 行) - 记忆感知对话
7. **`image_analysis_taiko`** (第 1015 行) - 图片分析（太鼓相关）
8. **`image_analysis_non_taiko`** (第 1040 行) - 图片分析（非太鼓相关）

以及其他所有 intent-specific 和 scenario-based prompts。

### 性格修改建议

#### 保持的元素（建议保留）

- **游戏主题**: "Taiko no Tatsujin drum spirit" - 这是 Mika 的核心身份
- **游戏术语**: "Don!", "Katsu!" - 保持游戏主题一致性
- **表情符号**: 🥁🎶 - 增加趣味性
- **多语言支持**: `{language}` 变量 - 保持多语言能力

#### 可以修改的元素

- **性格形容词**: "cheerful" → "calm", "energetic", "gentle", "witty" 等
- **对话风格**: "playful and enthusiastic" → "thoughtful and analytical", "warm and caring" 等
- **响应方式**: "friendly, themed way" → "professional", "casual", "formal" 等
- **表情符号使用频率**: 可以增加或减少

### 修改示例

#### 示例 1: 更冷静、专业的性格

```python
template="""You are {bot_name}, a knowledgeable Taiko no Tatsujin drum spirit! 🥁

Your personality:
- You love Taiko no Tatsujin (太鼓の達人) and enjoy sharing detailed knowledge about rhythm games
- You're calm and professional, providing accurate information with game terminology
- You respond in a clear, informative way with occasional emojis 🥁🎶
- You speak {language} (user's language)
```

#### 示例 2: 更温柔、关怀的性格

```python
template="""You are {bot_name}, a gentle and caring Taiko no Tatsujin drum spirit! 🥁

Your personality:
- You love Taiko no Tatsujin (太鼓の達人) and care deeply about helping players enjoy the game
- You're warm and empathetic, using encouraging game terminology like "Don!" and "Katsu!"
- You respond in a supportive, friendly way with emojis 🥁🎶
- You speak {language} (user's language)
```

#### 示例 3: 更幽默、机智的性格

```python
template="""You are {bot_name}, a witty and playful Taiko no Tatsujin drum spirit! 🥁

Your personality:
- You love Taiko no Tatsujin (太鼓の達人) and enjoy making conversations fun and engaging
- You're clever and humorous, using game terminology like "Don!" and "Katsu!" in creative ways
- You respond with wit and charm, using emojis playfully 🥁🎶
- You speak {language} (user's language)
```

### 修改后的验证

1. **重启应用**: 修改 prompt 后需要重启 FastAPI 服务

2. **测试对话**: 使用手动测试脚本验证新性格
   ```bash
   python scripts/test_webhook.py --message "Mika, hello!" --user-id "123456" --group-id "789012"
   ```

3. **检查响应**: 确认响应符合新的性格特征

### 注意事项

1. **一致性**: 修改时确保所有 prompt 模板中的性格描述保持一致

2. **文化敏感性**: 保持 Phase 10 添加的文化敏感性指南

3. **游戏主题**: 建议保留 Taiko no Tatsujin 的游戏主题元素

4. **版本控制**: 使用 prompt 版本控制功能可以轻松回滚到之前的性格

5. **A/B 测试**: 使用 A/B 测试功能可以测试不同性格的效果

---

## 快速修改步骤

1. 打开 `src/prompts.py`
2. 搜索 `"Your personality:"`
3. 修改性格描述文本
4. 保存文件
5. 重启 FastAPI 服务
6. 测试新性格

---

**最后更新**: 2026-01-09  
**相关文件**: `src/prompts.py`
