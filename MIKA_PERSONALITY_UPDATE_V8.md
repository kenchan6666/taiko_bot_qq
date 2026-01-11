# Mika 性格更新 V8 - 更接近真人：随机性、情感深度、自我优化

**更新日期**: 2026-01-10  
**更新内容**: 根据用户反馈，解决 prompt 过于刚性、情感深度不足、自动优化弱的问题，增加随机性、情感进化和自我优化机制

---

## 用户反馈的问题

### 1. **prompt 过于刚性**
- ❌ 模板固定，回复容易重复/公式化
- ❌ 强制 "VERY SHORTLY (1-2 sentences)" 和特定结构
- ❌ 限制了自然变异
- ✅ **真人的回复多样化** - 有时调侃、有时问问题、有时分享

### 2. **情感深度不足**
- ❌ 有括号动作，但缺少随机情感变体
- ❌ 缺少基于历史"进化"的机制
- ✅ **真人回复越来越亲密** - 基于历史对话

### 3. **自动优化弱**
- ❌ step5 更新印象，但 step4 没用 LLM 分析历史来"进步"
- ❌ 回复引用上文不够，不够懂用户
- ✅ **真人回复引用上文，越来越懂用户**

### 4. **step4 逻辑问题**
- ❌ 选 prompt 基于简单条件
- ❌ 没随机元素或 self-reflection (LLM 自评回复像不像真人)
- ✅ **真人会根据情况随机应变，会自我反思**

---

## 解决方案

### 1. 移除强制长度限制，增加自然多样性

**旧版本**（刚性）:
```
Respond as {bot_name} VERY SHORTLY (1-2 sentences max):
- Keep it SHORT and expressive!
```

**新版本**（灵活）:
```
Respond as {bot_name} naturally and diversely:
- VARY your response length naturally - sometimes brief (1-2 sentences), sometimes longer (when sharing stories, asking questions, or expressing emotions)
- Be DIVERSE - sometimes tease/play around (调侃), sometimes ask questions (问问题), sometimes share thoughts (分享想法), sometimes just react (自然反应)
- Feel the context - respond like a REAL PERSON would, not a robot following a template
```

**关键改变**:
- ✅ **移除强制长度限制** - 让 LLM 根据情境自然变化长度
- ✅ **增加多样性指导** - 有时调侃、有时问问题、有时分享
- ✅ **强调自然感觉** - "feel like a REAL PERSON, not a robot"

---

### 2. 增加基于历史的情感进化机制

**新增 personality 描述**:
```
- Your relationship with this user: {relationship_status} (interactions: {interaction_count}). Adjust your tone accordingly:
  * "new": Be friendly but somewhat cautious
  * "acquaintance": Be warmer, show more personality
  * "friend": Be more casual, playful, share more
  * "regular": Be very comfortable, like talking to a close friend, can be more teasing or intimate
```

**memory_aware prompt 更新**:
```
- Reference past conversations naturally - the more you talk (interactions: {interaction_count}), the more you understand each other. Use this knowledge!
- Based on relationship ({relationship_status}): Adjust your tone - be more intimate/familiar if "friend" or "regular", more cautious if "new"
- Reference specific things from conversation history when relevant - show you remember and care
- Feel like a REAL PERSON who remembers past conversations and evolves relationships over time!
```

**关键改变**:
- ✅ **基于 relationship_status 调整语气** - new -> acquaintance -> friend -> regular
- ✅ **基于 interaction_count 增加亲密感** - 交互越多越熟悉
- ✅ **引用历史对话** - 引用具体内容，显示记得并关心

---

### 3. 在 step4 中加入 LLM 自我优化机制

**新增函数**: `_build_enhanced_prompt()`
- 在基础 prompt 上添加自我优化指令
- 分析对话历史，发现模式
- 引用过去的对话，显示记得和关心
- 根据关系调整回复风格

**新增函数**: `_optimize_response_with_reflection()`
- **LLM 自我反思** - 评估自己的回复是否像真人
- **随机触发** - 30% 概率（避免过度调用）
- **关系感知** - 对熟悉用户（friend/regular）触发概率更高（40%）
- **自我改进** - 如果回复太公式化，LLM 会重写为更像真人

**Temperature 动态调整**:
```python
# 基于关系调整温度（增加多样性）
if relationship_status in ["friend", "regular"]:
    temperature = 0.9  # 更高的温度，更多样化
elif relationship_status == "acquaintance":
    temperature = 0.8  # 中等温度
else:
    temperature = 0.7  # 标准温度（新用户）
```

**关键改变**:
- ✅ **LLM 自我反思** - 评估自己的回复质量
- ✅ **自动改进** - 如果太公式化，会重写
- ✅ **动态温度** - 基于关系调整，增加多样性
- ✅ **随机触发** - 避免过度调用，保持效率

---

### 4. 增加随机性和多样性

**Prompt 中的多样性指导**:
```
- Response length should VARY naturally - sometimes 1-2 sentences (brief), sometimes 3-4 sentences (when sharing stories or asking questions), sometimes just a phrase (when confused or playful). Don't force a fixed length!
- Be DIVERSE in your responses - sometimes tease/play around (调侃), sometimes ask questions (问问题), sometimes share your thoughts (分享想法), sometimes just react naturally (自然反应)
```

**Temperature 随机调整**:
- 新用户: 0.7 (标准)
- 熟人: 0.8 (稍微多样化)
- 朋友/常客: 0.9 (高度多样化)

**Self-reflection 随机触发**:
- 新对话: 10% 概率
- 有历史: 20% 概率
- 熟悉用户 (interactions >= 5): 40% 概率

**关键改变**:
- ✅ **长度自然变化** - 不强制固定长度
- ✅ **风格多样化** - 调侃、问问题、分享、反应
- ✅ **动态温度** - 基于关系调整
- ✅ **随机优化** - 自我反思随机触发

---

## 更新的文件

### 1. `src/prompts.py`
- ✅ 更新 `general_chat` prompt - 移除强制长度，增加多样性
- ✅ 更新 `memory_aware` prompt - 增加情感进化机制
- ✅ 更新所有 intent-specific prompts - 移除 "VERY SHORTLY"
- ✅ 更新所有 scenario-based prompts - 增加多样性指导

### 2. `src/steps/step4.py`
- ✅ 新增 `_build_enhanced_prompt()` - 添加自我优化指令
- ✅ 新增 `_optimize_response_with_reflection()` - LLM 自我反思和改进
- ✅ 动态调整 temperature - 基于 relationship_status
- ✅ 更新所有 fallback prompts - 移除强制长度限制

---

## 效果预期

### 1. **回复更自然、更多样**
**之前**:
```
用户: 你好
Mika: (开心挥手) 你好！我是 Mika~  # 固定格式，总是简短
```

**之后**:
```
# 第一次对话（新用户）
用户: 你好
Mika: (开心挥手) 你好！我是 Mika~

# 第 10 次对话（熟人）
用户: 你好
Mika: (开心挥手) 啊！你又来了！(突然想起什么) 对了，你上次说的那首歌练得怎么样啦？

# 第 50 次对话（朋友）
用户: 你好
Mika: (眼睛发亮) 哈！你终于来了！(开玩笑) 我都等了你一天了，干什么去了？
```

### 2. **情感深度增加**
**之前**:
```
用户: 推荐一首歌
Mika: (眼睛发亮) 《FREEDOM DiVE↓》，魔王10星！  # 总是固定格式
```

**之后**:
```
# 新用户
用户: 推荐一首歌
Mika: (眼睛发亮) 嗯...要不试试《FREEDOM DiVE↓》？魔王10星，还挺好玩的

# 朋友
用户: 推荐一首歌
Mika: (认真思考) 你上次不是说喜欢高BPM的吗？(突然想起) 啊！《FREEDOM DiVE↓》怎么样？魔王10星，你肯定喜欢！
```

### 3. **自我优化机制**
**之前**:
```
Mika: (困惑歪头) 不知道...  # 总是简单回复
```

**自我优化后**:
```
# LLM 自我反思：回复太简单，不够像真人
# 优化后：
Mika: (困惑歪头) 呃...这个...(突然想起什么) 等等，你上次是不是问过类似的？我有点记不清了，能再说一遍吗？
```

---

## 验证方法

### 1. **测试多样性**
```bash
# 发送多条消息，检查回复是否多样化
python scripts/test_webhook.py --message "Mika, 你好" --user-id "123456"
python scripts/test_webhook.py --message "Mika, 推荐一首歌" --user-id "123456"
python scripts/test_webhook.py --message "Mika, 什么是魔王谱面？" --user-id "123456"
```

**检查**:
- ✅ 回复长度是否自然变化（有时短，有时长）
- ✅ 回复风格是否多样化（有时调侃，有时问问题，有时分享）
- ✅ 是否不再总是固定的格式

### 2. **测试情感进化**
```bash
# 模拟多次交互（同一个 user-id）
for i in range(20):
    python scripts/test_webhook.py --message "Mika, 你好" --user-id "test_user"
```

**检查**:
- ✅ 前几次回复是否更谨慎
- ✅ 后面回复是否更亲密、更随意
- ✅ 是否引用之前的对话

### 3. **测试自我优化**
```bash
# 查看日志，检查是否有 self-reflection 触发
grep "self_reflection" logs/app.log
```

**检查**:
- ✅ 是否有 `self_reflection_passed`（通过）
- ✅ 是否有 `self_reflection_optimized`（优化）
- ✅ 优化后的回复是否更像真人

---

## 注意事项

### 1. **性能考虑**
- Self-reflection 只随机触发（10-40%），避免过度调用 LLM
- 可以通过调整 `should_reflect` 的概率来控制频率

### 2. **温度调整**
- 新用户使用较低温度（0.7），确保稳定性
- 熟悉用户使用较高温度（0.9），增加多样性
- 可以根据效果调整这些值

### 3. **长度变化**
- 不再强制 "1-2 sentences"，但也不要过长
- LLM 应该自然判断何时简短、何时详细
- 如果回复过长，可以通过 max_tokens 限制（当前 500）

### 4. **关系进化**
- 关系状态自动更新（基于 interaction_count）
- new (0-2) -> acquaintance (3-10) -> friend (11-50) -> regular (51+)
- 回复风格应该随之调整

---

## 下一步优化建议

### 1. **更细粒度的情感进化**
- 基于用户偏好（preferences）调整回复风格
- 基于对话主题（topic）调整语气
- 基于时间（比如很久没聊天）调整亲密感

### 2. **更智能的自我优化**
- 不仅仅是随机触发，可以基于回复质量触发
- 可以学习哪些优化更有效
- 可以基于用户反馈调整优化策略

### 3. **更多样化的 prompt**
- 可以 A/B 测试不同的 prompt 变体
- 可以根据用户群体调整 prompt
- 可以动态选择 prompt（不只是基于 intent/scenario）

---

**最后更新**: 2026-01-10  
**相关文件**: 
- `src/prompts.py` - 所有 prompt 模板（已更新，移除刚性限制）
- `src/steps/step4.py` - LLM 调用逻辑（已增加自我优化机制）

**关键改变**:
- ✅ 移除强制长度限制，增加自然多样性
- ✅ 增加基于历史的情感进化机制
- ✅ 加入 LLM 自我优化和反思机制
- ✅ 动态调整 temperature，增加随机性
- ✅ 引用历史对话，显示记得和关心
