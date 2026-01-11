# Step4 高级优化 V10 - 随机变体、自我优化、历史分析、RLHF

**更新日期**: 2026-01-10  
**更新内容**: 根据用户反馈，实现随机变体选择、改进 self-reflection、添加历史分析、实现 RLHF 式多候选选择、添加随机噪声

---

## 用户反馈的问题

1. ✅ **加随机选变体** - 从 use_case 下的多个 template 随机选一个，增加多样性
2. ✅ **加 self-reflection** - LLM 生成回复后，用另一个 LLM 调用自评"这个回复像真人吗？"，如果不像，微调再生成
3. ✅ **加历史分析** - 在注入 history 前，用 LLM 总结"从历史看，用户偏好 X"，注入 prompt 让回复"进步"（越来越贴合）

**技术考虑**:
- ✅ **Few-shot learning** - 在 prompt 中加入示例（已实现）
- ✅ **Self-Reflection Loop** - LLM 自评优化（已实现，可扩展到 step5）
- ✅ **随机变体 + 噪声** - prompt 加"随机加表情或口癖"，让回复不重复
- ✅ **RLHF-like** - 生成 2-3 回复变体，用另一个 LLM 选"最像真人"的

---

## 实现的改进

### 1. 随机变体选择（Random Variant Selection）

**新增 PromptManager 方法**:
- `get_templates_by_use_case()` - 获取指定 use_case 下的所有模板
- `get_random_prompt_by_use_case()` - 随机选择一个模板

**在 step4 中的应用**:
```python
# 30% 概率使用随机变体（memory_aware use_case）
use_random_variant = random.random() < 0.3
if use_random_variant:
    template_name, prompt = prompt_manager.get_random_prompt_by_use_case(
        use_case="memory_aware",
        ...
    )
```

**效果**:
- ✅ 从同一个 use_case 下的多个模板中随机选择
- ✅ 增加回复的多样性，避免总是使用同一个模板
- ✅ 如果只有一个模板，则回退到默认模板

---

### 2. 历史分析（History Analysis）

**新增函数**: `_analyze_conversation_history()`

**功能**:
- 在注入 history 前，用 LLM 分析对话历史
- 总结用户偏好、性格、对话模式、关系发展
- 生成简洁的分析摘要（2-3 句话）

**分析内容**:
1. 用户偏好（topics/interests）
2. 沟通风格（formal, casual, playful, etc.）
3. 性格特征（friendly, shy, direct, etc.）
4. 对话模式（patterns）
5. 关系发展（evolution）

**注入 prompt**:
```python
# 在 prompt 中注入分析结果
prompt = prompt + f"\n\nUser preferences analysis from conversation history:\n{analyzed_history}\n\nUse this analysis to make your response more tailored to the user (越来越贴合)."
```

**效果**:
- ✅ 让 LLM 理解用户偏好和性格
- ✅ 回复越来越贴合用户（越来越懂用户）
- ✅ 基于历史"进步"，而不是每次都重新开始

---

### 3. 改进 Self-Reflection

**已有的函数**: `_optimize_response_with_reflection()`

**改进内容**:
- 更完善的反思提示（包括人设信息、语气要求）
- 更全面的评估标准（7 个评估点）
- 更智能的优化指导（基于关系调整）

**评估标准**:
1. 是否像真人（不是机器人）
2. 是否可爱有活力，不软弱
3. 是否引用历史对话
4. 长度是否合适和变化
5. 情感深度是否足够
6. 是否多样化
7. 太鼓推荐是否在尴尬时（频率是否合适）

**触发机制**:
- 新对话: 10% 概率
- 有历史: 20% 概率
- 熟悉用户 (interactions >= 5): 40% 概率

**效果**:
- ✅ LLM 自评回复质量
- ✅ 如果太公式化/机器人化，自动改进
- ✅ 越来越像真人

---

### 4. RLHF-like 多候选选择

**新增函数**: `_generate_and_select_best_response()`

**功能**:
- 生成 2-3 个回复变体（使用不同的 temperature）
- 用另一个 LLM 评估哪个最像真人
- 返回最佳变体

**触发条件**:
- 40% 概率（仅对朋友/常客）
- 只在 relationship_status 为 "friend" 或 "regular" 时使用

**选择标准**:
1. 是否像真人（不是机器人）
2. 是否可爱有活力，不软弱
3. 是否使用括号动作/情绪
4. 长度是否合适和变化
5. 情感深度是否足够
6. 是否多样化

**效果**:
- ✅ 生成多个候选，选择最像真人的
- ✅ 类似 RLHF（Reinforcement Learning from Human Feedback）
- ✅ 增加回复质量

---

### 5. 随机噪声（Random Noise）

**新增函数**: `_add_random_noise_to_prompt()`

**功能**:
- 在 prompt 中添加随机语言变体指令
- 根据关系选择不同的语言模式
- 避免回复重复

**语言模式**（朋友/常客）:
- 偶尔加 '啦' '嘛' '呢' 等语气词
- 偶尔用 '嘿嘿' '哈哈' '嘻嘻' 等笑声
- 偶尔加 '！' 或 '...' 来表达情绪

**语言模式**（标准）:
- 偶尔加语气词如 '呢' '呀'
- 偶尔用感叹号表达情绪

**效果**:
- ✅ 增加语言多样性
- ✅ 避免回复重复
- ✅ 更像真人说话

---

## 更新的文件

### 1. `src/prompts.py`
- ✅ 添加 `import random`
- ✅ 新增 `get_templates_by_use_case()` 方法
- ✅ 新增 `get_random_prompt_by_use_case()` 方法
- ✅ 更新 `memory_aware` prompt - 加入 `user_preferences_analysis` 变量

### 2. `src/steps/step4.py`
- ✅ 在 `invoke_llm()` 开始时调用历史分析
- ✅ 实现随机变体选择（30% 概率）
- ✅ 注入历史分析结果到 prompt
- ✅ 添加随机噪声到 prompt
- ✅ 实现 RLHF 式多候选选择（40% 概率，仅朋友/常客）
- ✅ 改进 self-reflection 机制
- ✅ 新增 `_analyze_conversation_history()` 函数
- ✅ 新增 `_add_random_noise_to_prompt()` 函数
- ✅ 新增 `_generate_and_select_best_response()` 函数

---

## 技术实现细节

### 1. 随机变体选择

**PromptManager 新方法**:
```python
def get_templates_by_use_case(self, use_case: str, **kwargs) -> list[tuple[str, str]]:
    """获取指定 use_case 下的所有模板（已渲染）"""
    templates = []
    for name, versions in self._templates.items():
        for version, template_obj in versions.items():
            if template_obj.use_case == use_case:
                try:
                    rendered = template_obj.template.format(**kwargs)
                    templates.append((name, rendered))
                except KeyError:
                    continue  # 跳过缺失变量的模板
    return templates

def get_random_prompt_by_use_case(self, use_case: str, **kwargs) -> tuple[str, str]:
    """随机选择一个模板"""
    templates = self.get_templates_by_use_case(use_case, **kwargs)
    if not templates:
        raise ValueError(f"No templates found for use_case '{use_case}'")
    return random.choice(templates)
```

**在 step4 中的应用**:
```python
# 30% 概率使用随机变体
use_random_variant = random.random() < 0.3
if use_random_variant:
    try:
        template_name, prompt = prompt_manager.get_random_prompt_by_use_case(
            use_case="memory_aware",
            ...
        )
    except (ValueError, KeyError):
        # Fallback to default
        prompt = prompt_manager.get_prompt(name="memory_aware", ...)
```

---

### 2. 历史分析

**函数实现**:
```python
async def _analyze_conversation_history(...) -> str:
    """分析对话历史，提取用户偏好和模式"""
    # 构建历史摘要（最近 10 条对话）
    # 使用 LLM 分析（temperature=0.5，更稳定）
    # 返回分析摘要："从历史看，用户偏好: ... 用户性格: ... 对话模式: ... 关系发展: ..."
```

**分析提示**:
```
Analysis task:
1. What topics/interests does the user seem to prefer?
2. What communication style does the user prefer?
3. What are the user's personality traits?
4. What patterns do you notice?
5. How has the relationship evolved?

Provide a BRIEF summary (2-3 sentences max) in this format:
"从历史看，用户偏好: [preferences]. 用户性格: [personality]. 对话模式: [patterns]. 关系发展: [evolution]."
```

**注入 prompt**:
- 如果分析结果可用，注入到 prompt 中
- 在 `memory_aware` prompt 中包含 `{user_preferences_analysis}` 变量
- 指导 LLM 使用分析结果让回复更贴合用户

---

### 3. 改进 Self-Reflection

**触发概率**:
- 新对话: 10%
- 有历史 (>= 3 条): 20%
- 熟悉用户 (interactions >= 5): 40%

**反思提示**（改进版）:
```
Self-reflection task:
1. Does this response feel like a REAL PERSON talking, or a robot following a template?
2. Is it cute and energetic (可爱有活力), not too soft/gentle?
3. Does it reference past conversations naturally?
4. Is the response length appropriate and varied?
5. Does it show emotional depth based on relationship status?
6. Is it diverse enough?
7. If feeling awkward/embarrassed, does it use urgent tone when suggesting Taiko?

If the response feels too formulaic, repetitive, robotic, or too soft/gentle, rewrite it...
```

**优化指导**:
- 根据关系调整语气（朋友/常客可以更亲密/调情）
- 改变结构（不要总是同样的开始方式）
- 引用历史对话
- 显示适当的情感深度
- 多样化（调侃、问问题、分享）

---

### 4. RLHF 式多候选选择

**触发条件**:
- 40% 概率
- 仅对朋友/常客 (relationship_status in ["friend", "regular"])

**实现流程**:
1. 生成 3 个变体（temperature 有 ±0.1 变化）
2. 构建选择提示，让 LLM 评估哪个最像真人
3. 解析选择结果（提取变体编号）
4. 返回最佳变体（或第一个如果解析失败）

**选择提示**:
```
Selection task:
Which variant is MOST HUMAN-LIKE? Consider:
1. Does it feel like a REAL PERSON talking, not a robot?
2. Is it cute and energetic (可爱有活力), not too soft/gentle?
3. Does it use parenthetical actions/emotions naturally?
4. Is the length appropriate and varied?
5. Does it show appropriate emotional depth for the relationship?
6. Is it diverse and not formulaic?

Respond with ONLY the variant number (1, 2, or 3) and a brief reason.
```

**效果**:
- ✅ 生成多个候选，选择最像真人的
- ✅ 类似 RLHF（人类反馈强化学习）
- ✅ 增加回复质量

---

### 5. 随机噪声

**函数实现**:
```python
def _add_random_noise_to_prompt(prompt: str, context: UserContext) -> str:
    """添加随机语言变体指令到 prompt"""
    # 根据关系选择不同的语言模式
    if relationship_status in ["friend", "regular"]:
        patterns = ["偶尔加 '啦' '嘛' '呢' 等语气词", ...]
    else:
        patterns = ["偶尔加语气词如 '呢' '呀'", ...]
    
    # 随机选择一个模式
    pattern = random.choice(patterns)
    return prompt + f"\n\nRandom variation: {pattern} - vary your speech patterns naturally to avoid repetition."
```

**效果**:
- ✅ 增加语言多样性
- ✅ 避免回复重复
- ✅ 更像真人说话

---

## 效果预期

### 1. **随机变体选择**
**之前**:
```
用户: 你好
Mika: (开心挥手) 你好！  # 总是用同一个模板
```

**之后**:
```
用户: 你好
Mika: (开心挥手) 哈！你好啊！  # 随机选择了不同的变体
```

### 2. **历史分析**
**之前**:
```
用户: 推荐一首歌
Mika: (眼睛发亮) 《FREEDOM DiVE↓》，魔王10星！  # 不知道用户偏好
```

**之后**（有历史分析）:
```
用户: 推荐一首歌
Mika: (突然想起什么) 啊！你不是喜欢高BPM的吗？(眼睛发亮) 《FREEDOM DiVE↓》怎么样？魔王10星，BPM还挺高的！  # 基于历史分析，知道用户偏好
```

### 3. **Self-Reflection**
**之前**:
```
LLM 生成: (困惑歪头) 不知道...
# 直接返回，可能太简单
```

**Self-Reflection 后**:
```
LLM 反思: 这个回复太简单了，不够像真人
LLM 优化: (困惑歪头) 呃...这个...(突然想起什么) 等等，你上次是不是问过类似的？我有点记不清了，能再说一遍吗？
```

### 4. **RLHF 式多候选选择**
**生成 3 个变体**:
```
Variant 1: (困惑歪头) 不知道...
Variant 2: (困惑歪头) 呃...这个...(突然想起什么) 等等，你上次是不是问过类似的？
Variant 3: (困惑歪头) 让我想想...(小声) 我好像记得之前聊过这个...

LLM 选择: Variant 2 - most natural and playful
返回: Variant 2
```

### 5. **随机噪声**
**之前**:
```
Mika: (困惑歪头) 不知道
Mika: (困惑歪头) 不知道  # 回复重复
```

**之后**（有随机噪声）:
```
Mika: (困惑歪头) 不知道呢...
Mika: (困惑歪头) 呃...不知道呀  # 语言变体，不重复
```

---

## 性能考虑

### 1. **LLM 调用次数**
- **标准流程**: 1 次 LLM 调用（生成回复）
- **有历史分析**: 2 次 LLM 调用（分析历史 + 生成回复）
- **有 RLHF 选择**: 4 次 LLM 调用（生成 3 个变体 + 选择最佳）
- **有 Self-Reflection**: +1 次 LLM 调用（反思优化）

**优化**:
- ✅ 历史分析只在有足够历史时进行（>= 2 条对话）
- ✅ RLHF 选择只在朋友/常客时使用（40% 概率）
- ✅ Self-Reflection 随机触发（10-40% 概率）
- ✅ 所有优化都是可选的，可以调整概率

### 2. **响应时间**
- 标准流程: ~1-2 秒
- 有历史分析: ~2-3 秒
- 有 RLHF 选择: ~4-6 秒（生成 3 个变体 + 选择）
- 有 Self-Reflection: +1-2 秒

**建议**:
- 可以根据需要调整触发概率
- 可以禁用某些优化（设置为 0% 概率）
- 可以限制 RLHF 变体数量（从 3 减少到 2）

---

## 验证方法

### 1. **测试随机变体选择**
```bash
# 多次发送相同消息，检查是否使用不同的模板
for i in range(10):
    python scripts/test_webhook.py --message "Mika, 你好" --user-id "test_user"
```

**检查**:
- ✅ 日志中是否有 `random_variant_selected` 记录
- ✅ 回复是否多样化（不总是同一个格式）

### 2. **测试历史分析**
```bash
# 模拟多次交互，然后发送新消息
for i in range(10):
    python scripts/test_webhook.py --message "Mika, 你好" --user-id "test_user"
python scripts/test_webhook.py --message "Mika, 推荐一首歌" --user-id "test_user"
```

**检查**:
- ✅ 日志中是否有 `history_analysis_completed` 记录
- ✅ 回复是否引用历史对话（比如"你不是喜欢高BPM的吗？"）

### 3. **测试 Self-Reflection**
```bash
# 查看日志，检查是否有 self-reflection 触发
grep "self_reflection" logs/app.log
```

**检查**:
- ✅ 是否有 `self_reflection_passed`（通过，无需优化）
- ✅ 是否有 `self_reflection_optimized`（优化了回复）
- ✅ 优化后的回复是否更像真人

### 4. **测试 RLHF 选择**
```bash
# 模拟多次交互后（成为朋友），发送消息
for i in range(20):
    python scripts/test_webhook.py --message "Mika, 你好" --user-id "friend_user"
python scripts/test_webhook.py --message "Mika, 推荐一首歌" --user-id "friend_user"
```

**检查**:
- ✅ 日志中是否有 `rlhf_response_selected` 记录
- ✅ 是否有 `variant_generated` 记录（生成多个变体）
- ✅ 是否有 `best_variant_selected` 记录（选择最佳）

### 5. **测试随机噪声**
```bash
# 多次发送相同消息，检查语言变体
for i in range(10):
    python scripts/test_webhook.py --message "Mika, 你好" --user-id "test_user"
```

**检查**:
- ✅ 回复是否使用了不同的语言模式（语气词、笑声、感叹号等）
- ✅ 是否避免了重复

---

## 技术考虑（哪些可以实现）

### ✅ 已实现的技术

1. **Few-shot learning**
   - ✅ 在 prompt 中加入示例（已实现）
   - ✅ 可以搜索类似聊天记录添加更多 examples（需要 web_search 集成）

2. **Self-Reflection Loop**
   - ✅ LLM 自评优化（已实现）
   - ✅ 可以扩展到 step5 更新 impression 时，用 LLM 分析"这个对话如何更真人"（后续可以实现）

3. **随机变体 + 噪声**
   - ✅ prompt 加"随机加表情或口癖"（已实现）
   - ✅ 让回复不重复（已实现）

4. **RLHF-like**
   - ✅ 生成 2-3 回复变体（已实现，默认 3 个）
   - ✅ 用另一个 LLM 选"最像真人"的（已实现）
   - ✅ 增加 step4 调用（已实现）

### 🔄 后续可以实现的技术

1. **Few-shot learning（扩展）**
   - 🔄 使用 web_search 搜索"可爱女孩 QQ 聊天示例"
   - 🔄 添加更多 examples 到 prompt
   - 🔄 动态更新 examples（基于历史对话）

2. **Fine-Tuning**
   - 🔄 OpenRouter 支持自定义模型
   - 🔄 需要收集真人聊天记录
   - 🔄 Fine-tune gpt-4o-mini（需要数据集准备）
   - ⚠️ **注意**: 这需要较长时间和资源，建议作为长期目标

3. **Self-Reflection Loop（扩展）**
   - 🔄 扩展到 step5 更新 impression 时
   - 🔄 用 LLM 分析"这个对话如何更真人"
   - 🔄 存储分析结果，用于下次优化

---

## 注意事项

### 1. **性能影响**
- ✅ 历史分析增加 1 次 LLM 调用（~1-2 秒）
- ✅ RLHF 选择增加 3-4 次 LLM 调用（~3-4 秒）
- ✅ Self-Reflection 增加 1 次 LLM 调用（~1-2 秒）
- ⚠️ **建议**: 根据实际需求调整触发概率，平衡质量和性能

### 2. **成本考虑**
- ✅ 历史分析只在有足够历史时进行
- ✅ RLHF 选择只在朋友/常客时使用（40% 概率）
- ✅ Self-Reflection 随机触发（10-40% 概率）
- ⚠️ **注意**: 如果频繁使用，会增加 API 调用成本

### 3. **随机变体选择**
- ✅ 需要同一个 use_case 下有多个模板才能有效
- ⚠️ **建议**: 为同一个 use_case 创建多个变体模板（例如 `memory_aware_v1`, `memory_aware_v2`）
- ⚠️ **注意**: 如果只有一个模板，随机选择没有意义

### 4. **历史分析准确性**
- ✅ 使用较低 temperature (0.5) 确保分析稳定
- ⚠️ **注意**: 如果历史对话太少（< 2 条），可能无法生成有效分析
- ⚠️ **建议**: 可以根据历史数量调整分析深度

### 5. **RLHF 选择准确性**
- ✅ 使用较低 temperature (0.3) 确保选择稳定
- ⚠️ **注意**: 如果 LLM 选择失败（解析错误），会回退到第一个变体
- ⚠️ **建议**: 可以改进解析逻辑，或使用更明确的输出格式

---

## 下一步优化建议

### 1. **添加更多变体模板**
- 为同一个 use_case 创建多个变体（例如 `memory_aware_v1`, `memory_aware_v2`, `memory_aware_v3`）
- 每个变体有不同的风格（更活泼、更害羞、更调皮等）
- 随机选择增加多样性

### 2. **Few-shot Learning（扩展）**
- 使用 web_search 搜索"可爱女孩 QQ 聊天示例"
- 添加更多 examples 到 prompt
- 动态更新 examples（基于历史对话）

### 3. **Self-Reflection Loop（扩展）**
- 扩展到 step5 更新 impression 时
- 用 LLM 分析"这个对话如何更真人"
- 存储分析结果，用于下次优化

### 4. **Fine-Tuning（长期目标）**
- 收集真人聊天记录
- 准备 fine-tuning 数据集
- Fine-tune gpt-4o-mini
- ⚠️ **注意**: 这需要较长时间和资源

---

**最后更新**: 2026-01-10  
**相关文件**: 
- `src/prompts.py` - 新增随机变体选择方法
- `src/steps/step4.py` - 实现所有高级优化功能

**关键改变**:
- ✅ 随机变体选择（30% 概率）
- ✅ 历史分析（注入用户偏好）
- ✅ 改进 Self-Reflection（更完善的评估和优化）
- ✅ RLHF 式多候选选择（40% 概率，仅朋友/常客）
- ✅ 随机噪声（增加语言多样性）
