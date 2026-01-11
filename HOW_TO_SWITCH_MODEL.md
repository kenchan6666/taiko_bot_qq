# 如何切换 LLM 模型

**更新日期**: 2026-01-10  
**目的**: 指导如何切换不同的 LLM 模型以优化 Mika 的对话质量

---

## 当前支持的模型

### 1. GPT-4o (`openai/gpt-4o`) - 默认
- **优点**: 速度快，多模态支持，准确度高
- **缺点**: 真人对话感一般，不够活泼
- **适用**: 预算有限或需要多模态支持

### 2. Claude 3.5 Sonnet (`anthropic/claude-3.5-sonnet`) - 推荐
- **优点**: 真人对话感最强，情感理解好，准确度高
- **缺点**: 响应稍慢，成本稍高
- **适用**: 需要真人对话感和情感理解（推荐）

### 3. Claude Opus (`anthropic/claude-opus`) - 更强大
- **优点**: 比 Sonnet 更强大，真人对话感最强
- **缺点**: 更贵，响应更慢
- **适用**: 需要最强性能

### 4. Grok 2 (`xai/grok-2`) - 活泼风趣
- **优点**: 活泼风趣，个性鲜明，对话自然
- **缺点**: 幻觉率高（4.8%），准确性较低
- **适用**: 需要活泼性格，但要注意准确性

### 5. Grok 2 Vision (`xai/grok-2-vision-1212`) - 支持图片
- **优点**: 活泼风趣 + 支持图片
- **缺点**: 幻觉率高，准确性较低
- **适用**: 需要活泼性格 + 图片支持

---

## 切换方法

### 方法 1: 通过环境变量（推荐）

在 `.env` 文件中添加：

```bash
# 切换到 Claude 3.5 Sonnet（推荐）
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# 或切换到 Grok 2（活泼风格）
OPENROUTER_MODEL=xai/grok-2

# 或切换到 Claude Opus（最强性能）
OPENROUTER_MODEL=anthropic/claude-opus
```

然后重启服务：
```bash
# 重启 Temporal Worker
poetry run python -m src.workers.temporal_worker

# 如果 FastAPI 在本地运行，也重启它
poetry run uvicorn src.api.main:app --reload
```

---

### 方法 2: 直接修改代码（临时测试）

修改 `src/services/llm.py`：

```python
# 第 48 行左右
# 原来:
# self.model = "openai/gpt-4o"

# 改为:
self.model = "anthropic/claude-3.5-sonnet"  # 切换到 Claude 3.5 Sonnet
```

⚠️ **注意**: 这种方法不推荐，因为代码修改后需要重新部署。

---

## 推荐配置

### 对于 Mika 这种"可爱有活力的真人女孩"性格:

**最推荐**: **Claude 3.5 Sonnet** (`anthropic/claude-3.5-sonnet`)

**理由**:
1. ✅ **真人对话感最强**: 在所有模型中表现最好
2. ✅ **情感理解好**: 能更好地理解用户情感，做出更贴切的回复
3. ✅ **准确度高**: 不会说错话（歌曲查询等）
4. ✅ **上下文记忆强**: 200K 上下文窗口，能更好地记住对话历史

**配置**:
```bash
# .env
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

**Temperature 调整**:
- Claude 对 temperature 更敏感，建议从 0.7 调整为 **0.8-0.9**
- 朋友/常客可以更高（**0.9-1.0**）

**修改位置**: `src/steps/step4.py` 第 407-418 行左右

```python
# 调整 temperature
base_temperature = 0.8  # 从 0.7 提高到 0.8
if context.impression:
    if context.relationship_status in ["friend", "regular"]:
        temperature = base_temperature + 0.2  # 1.0 for more diversity
    elif context.relationship_status == "acquaintance":
        temperature = base_temperature + 0.1  # 0.9
    else:
        temperature = base_temperature  # 0.8
else:
    temperature = base_temperature
```

---

### 如果想尝试更活泼的风格: **Grok 2** (`xai/grok-2`)

**理由**:
1. ✅ **活泼风趣**: 非常适合"可爱有活力的女孩"性格
2. ✅ **个性鲜明**: 能很好地表达 Mika 的个性
3. ✅ **对话自然**: 回复更像真人，不那么"机器人"

**⚠️ 注意事项**:
1. ❌ **幻觉率高**: 4.8%，可能说错话
2. ❌ **准确性较低**: 对于需要准确信息的场景（歌曲查询），可能不够可靠
3. ⚠️ **建议**: 
   - 混合使用（主要对话用 Grok，关键场景用 Claude）
   - 加强验证（对重要信息进行二次验证）
   - 降低 temperature（0.6-0.7）来减少幻觉

**配置**:
```bash
# .env
OPENROUTER_MODEL=xai/grok-2
```

**Temperature 调整**:
- Grok 本身就很活泼，建议**降低** temperature（**0.6-0.7**）来减少幻觉
- 或提高 self-reflection 的频率

**修改位置**: `src/steps/step4.py` 第 407-418 行左右

```python
# 调整 temperature（降低以减少幻觉）
base_temperature = 0.6  # 从 0.7 降低到 0.6
if context.impression:
    if context.relationship_status in ["friend", "regular"]:
        temperature = base_temperature + 0.1  # 0.7
    elif context.relationship_status == "acquaintance":
        temperature = base_temperature + 0.05  # 0.65
    else:
        temperature = base_temperature  # 0.6
else:
    temperature = base_temperature
```

---

## 测试步骤

### 1. 切换到 Claude 3.5 Sonnet

```bash
# 1. 修改 .env 文件
echo "OPENROUTER_MODEL=anthropic/claude-3.5-sonnet" >> .env

# 2. 重启服务
poetry run python -m src.workers.temporal_worker

# 3. 测试主要场景
# - 普通对话（真人对话感）
# - 歌曲查询（准确性）
# - 图片分析（多模态）
# - 历史记忆（上下文理解）
```

### 2. 对比效果

**与 GPT-4o 对比**:
- ✅ 回复是否更像真人？
- ✅ 是否更活泼？
- ✅ 情感理解是否更好？
- ✅ 准确性是否保持？

### 3. 调整参数

**如果觉得"不够活泼"**:
- 提高 temperature（0.9-1.0）
- 加强 self-reflection
- 使用 RLHF 选择

**如果觉得"太活泼"**:
- 降低 temperature（0.7-0.8）
- 减少 self-reflection 频率
- 调整 prompt

---

## 成本对比（参考）

**注意**: 实际成本可能因地区和用量而异，以下仅供参考。

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| GPT-4o | ~$5/M tokens | ~$15/M tokens | 默认，快速 |
| Claude 3.5 Sonnet | ~$3/M tokens | ~$15/M tokens | 推荐，真人对话感强 |
| Claude Opus | ~$15/M tokens | ~$75/M tokens | 最强大，但很贵 |
| Grok 2 | 价格不明确 | 价格不明确 | 可能比 GPT-4o 贵 |

**结论**: Claude 3.5 Sonnet 的成本与 GPT-4o 相近，但性能更好。

---

## 常见问题

### Q1: 切换到 Claude 后，图片分析还能用吗？

**A**: 可以！Claude 3.5 Sonnet 也支持多模态（图片），不影响现有功能。

### Q2: Grok 的幻觉率真的很高吗？

**A**: 是的。根据测试，Grok 的幻觉率是 4.8%，比 GPT-4o (1.49%) 和 Claude 高很多。对于需要准确信息的场景（歌曲查询），建议使用 Claude。

### Q3: 可以混合使用多个模型吗？

**A**: 可以！但需要修改代码逻辑。例如：
- 主要对话用 Claude（真人对话感）
- 图片分析用 GPT-4o（多模态支持）
- 非关键对话用 Grok（活泼性格）

### Q4: 切换到新模型后，需要调整 prompt 吗？

**A**: 
- **Claude**: 可能需要稍微调整 prompt 格式（Claude 对格式更敏感）
- **Grok**: 可以保持现有 prompt，但建议降低 temperature 来减少幻觉

### Q5: 如何监控成本？

**A**: 
- OpenRouter 会提供使用统计
- 可以在代码中添加日志记录每次调用的 token 数
- 定期检查账单

---

## 下一步

1. **先测试 Claude 3.5 Sonnet**（推荐）:
   ```bash
   # 切换模型
   echo "OPENROUTER_MODEL=anthropic/claude-3.5-sonnet" >> .env
   
   # 调整 temperature（可选）
   # 修改 src/steps/step4.py，将 base_temperature 从 0.7 调整为 0.8
   
   # 重启服务
   poetry run python -m src.workers.temporal_worker
   ```

2. **测试效果**:
   - 发送几条消息，看看回复是否更像真人
   - 检查歌曲查询是否准确
   - 测试图片分析是否正常

3. **根据效果调整**:
   - 如果觉得"不够活泼"，可以尝试 Grok 2
   - 如果觉得"太活泼"，可以降低 temperature
   - 如果觉得"成本太高"，可以切换回 GPT-4o

---

**最后更新**: 2026-01-10  
**相关文件**: 
- `src/config.py` - 模型配置
- `src/services/llm.py` - LLM 服务
- `src/steps/step4.py` - Temperature 调整
- `LLM_MODEL_RECOMMENDATION.md` - 详细模型推荐
