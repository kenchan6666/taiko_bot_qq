"""
测试 OpenRouter LLM API 调用

这个脚本直接测试 OpenRouter API 是否正常工作。
使用方法: poetry run python scripts/test_llm_api.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.services.llm import LLMService


async def test_llm_api() -> None:
    """测试 OpenRouter LLM API 调用"""
    print("=== 测试 OpenRouter LLM API ===\n")

    # 检查 API Key
    if not settings.openrouter_api_key:
        print("❌ 错误: OPENROUTER_API_KEY 未设置")
        print("\n请设置环境变量或在 .env 文件中添加:")
        print("  OPENROUTER_API_KEY=sk-or-v1-你的API密钥")
        sys.exit(1)

    print(f"✓ API Key 已设置 (长度: {len(settings.openrouter_api_key)} 字符)")
    print(f"  API Key 前缀: {settings.openrouter_api_key[:15]}...\n")

    # 创建 LLM 服务
    try:
        llm_service = LLMService()
        print("✓ LLMService 初始化成功\n")
    except Exception as e:
        print(f"❌ LLMService 初始化失败: {e}")
        sys.exit(1)

    # 测试 API 调用
    print("正在调用 OpenRouter API...")
    test_prompt = "你好，请用一句话介绍你自己。"
    print(f"测试提示: {test_prompt}\n")

    try:
        response = await llm_service.generate_response(
            prompt=test_prompt,
            temperature=0.7,
            max_tokens=100,
        )
        print("✅ API 调用成功!")
        print(f"\n响应内容:\n{response}\n")
        print("✓ 如果看到这条消息，说明 API Key 工作正常")
        print("  请在 OpenRouter Dashboard 中检查 API 使用情况")

    except RuntimeError as e:
        print(f"❌ API 调用失败: {e}")
        print("\n可能的原因:")
        print("  1. API Key 无效或已过期")
        print("  2. 网络连接问题")
        print("  3. OpenRouter 服务暂时不可用")
        print("\n请检查:")
        print("  - OpenRouter Dashboard: https://openrouter.ai/keys")
        print("  - 网络连接")
        print("  - Worker 日志中的详细错误信息")
        sys.exit(1)

    except Exception as e:
        print(f"❌ 意外错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # 关闭服务
        await llm_service.close()
        print("\n✓ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_llm_api())
