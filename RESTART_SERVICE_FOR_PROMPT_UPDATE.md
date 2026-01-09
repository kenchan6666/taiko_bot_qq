# 重启服务以应用 Prompt 更新

## 问题说明

您更新了 Mika 的性格 prompt，但前端响应没有改变。这是因为：

1. **PromptManager 是单例模式**：在模块导入时初始化，prompt 在服务启动时加载
2. **Python 模块缓存**：已导入的模块会被缓存，除非重启服务，否则不会重新加载
3. **Temporal Worker 需要重启**：Temporal worker 进程需要重启才能加载新的代码

## 已完成的修复

我已经更新了：
- ✅ 所有 prompt 模板（`src/prompts.py`）
- ✅ 所有 fallback prompt（`src/steps/step4.py`）
- ✅ Fallback 响应（`src/steps/step4.py`）

## 重启步骤

### 1. 停止当前运行的服务

如果您正在运行 Temporal Worker：
```bash
# 在运行 worker 的终端按 Ctrl+C 停止
```

如果您正在运行 FastAPI 服务：
```bash
# 在运行服务的终端按 Ctrl+C 停止
```

### 2. 重启 Temporal Worker

```bash
poetry run python -m src.workers.temporal_worker
```

### 3. 重启 FastAPI 服务（如果需要）

```bash
poetry run uvicorn src.api.main:app --reload
```

## 验证更新

重启后，测试新的性格：

```bash
python scripts/test_webhook.py --message "Mika, 你好" --user-id "123456" --group-id "789012"
```

**预期响应**应该包含：
- ✅ 颜文字（如 `(´･ω･`)` 或 `( ﾟ∀ﾟ)`）而不是 emoji
- ✅ 可爱呆萌的语气，而不是过度傲娇
- ✅ 太鼓元素（如"不如去玩太鼓"或"魔王10星"）
- ✅ 简洁的回复

**不应该包含**：
- ❌ Emoji 表情符号（🥁🎶😏 等）
- ❌ 过度傲娇的语气
- ❌ 冗长的回复

## 如果仍然没有改变

如果重启后仍然没有改变，请检查：

1. **确认代码已保存**：检查 `src/prompts.py` 和 `src/steps/step4.py` 是否已保存
2. **检查服务日志**：查看是否有错误信息
3. **清除 Python 缓存**（如果需要）：
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} +
   find . -type f -name "*.pyc" -delete
   ```
4. **重新启动服务**：完全停止并重新启动

## 更新的内容总结

### 性格变化
- **减少傲娇**：从 "slightly tsundere" 改为 "cute and slightly silly (呆萌)"
- **增加可爱呆萌**：强调 "cute and a bit silly (呆萌)"
- **添加抽象元素**：添加 "slightly abstract (抽象) sense of humor"

### 太鼓元素
- 推荐魔王10星歌曲
- 鼓励玩游戏："有时间找我不如玩一把（从taikowiki找一首魔王10星）呢"

### 颜文字替换
- 移除所有 emoji（🥁🎶😏 等）
- 使用 kaomoji（颜文字）：(´･ω･`), ( ﾟ∀ﾟ), (´∀`) 等

### 网络梗
- 自然引用网络梗（如"董卓"等）
- 抽象幽默感

---

**重要**：重启服务后，新的 prompt 才会生效！
