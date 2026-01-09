#!/usr/bin/env python3
"""
LangBot 集成测试脚本

用于测试 LangBot 与 FastAPI 后端的集成，包括：
- Webhook 端点连接测试
- 关键词触发测试
- 群组白名单验证测试
- 端到端消息处理测试

使用方法:
    python scripts/test_langbot_integration.py [--webhook-url URL] [--group-id GROUP_ID] [--user-id USER_ID]

示例:
    # 使用默认配置测试
    python scripts/test_langbot_integration.py

    # 指定 webhook URL
    python scripts/test_langbot_integration.py --webhook-url https://api.yourdomain.com/webhook/langbot

    # 测试特定群组
    python scripts/test_langbot_integration.py --group-id 123456789 --user-id 987654321
"""

import argparse
import asyncio
import json
import sys
from typing import Optional

import httpx
import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


async def test_webhook_connection(webhook_url: str) -> bool:
    """
    测试 webhook 端点连接。

    Args:
        webhook_url: Webhook URL (包含 /webhook/langbot)

    Returns:
        True 如果连接成功，False 否则
    """
    logger.info("test_webhook_connection_start", webhook_url=webhook_url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 发送测试请求
            test_payload = {
                "group_id": "test_group",
                "user_id": "test_user",
                "message": "Mika, test connection",
                "images": [],
            }

            response = await client.post(
                webhook_url,
                json=test_payload,
                headers={"Content-Type": "application/json"},
            )

            logger.info(
                "test_webhook_connection_response",
                status_code=response.status_code,
                response_preview=response.text[:200],
            )

            if response.status_code == 200:
                logger.info("test_webhook_connection_success")
                return True
            else:
                logger.warning(
                    "test_webhook_connection_failed",
                    status_code=response.status_code,
                    response_text=response.text[:500],
                )
                return False

    except httpx.ConnectError as e:
        logger.error(
            "test_webhook_connection_network_error",
            error=str(e),
            message="无法连接到 webhook 端点，请检查 URL 和网络连接",
        )
        return False
    except httpx.TimeoutException as e:
        logger.error(
            "test_webhook_connection_timeout",
            error=str(e),
            message="Webhook 请求超时，请检查后端服务是否运行",
        )
        return False
    except Exception as e:
        logger.error(
            "test_webhook_connection_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


async def test_keyword_trigger(
    webhook_url: str, group_id: str, user_id: str
) -> bool:
    """
    测试关键词触发。

    Args:
        webhook_url: Webhook URL
        group_id: QQ 群组 ID
        user_id: QQ 用户 ID

    Returns:
        True 如果触发成功，False 否则
    """
    logger.info(
        "test_keyword_trigger_start",
        group_id=group_id,
        user_id=user_id,
    )

    # 测试不同的关键词变体
    keywords = ["Mika", "mika", "MIKA", "米卡", "mika酱"]

    results = []

    for keyword in keywords:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                test_payload = {
                    "group_id": group_id,
                    "user_id": user_id,
                    "message": f"{keyword}, 测试关键词触发",
                    "images": [],
                }

                response = await client.post(
                    webhook_url,
                    json=test_payload,
                    headers={"Content-Type": "application/json"},
                )

                response_data = response.json() if response.status_code == 200 else {}

                # 检查响应
                # 如果 skip_pipeline=False 或 success=False，说明消息被过滤（没有触发）
                triggered = (
                    response_data.get("skip_pipeline", False)
                    or response_data.get("success", False)
                )

                results.append(
                    {
                        "keyword": keyword,
                        "status_code": response.status_code,
                        "triggered": triggered,
                    }
                )

                logger.info(
                    "test_keyword_trigger_result",
                    keyword=keyword,
                    status_code=response.status_code,
                    triggered=triggered,
                )

        except Exception as e:
            logger.error(
                "test_keyword_trigger_error",
                keyword=keyword,
                error=str(e),
            )
            results.append({"keyword": keyword, "error": str(e)})

    # 汇总结果
    success_count = sum(1 for r in results if r.get("triggered", False))
    total_count = len(keywords)

    logger.info(
        "test_keyword_trigger_summary",
        success_count=success_count,
        total_count=total_count,
        results=results,
    )

    return success_count > 0


async def test_group_whitelist(
    webhook_url: str, allowed_group_id: str, blocked_group_id: str, user_id: str
) -> bool:
    """
    测试群组白名单验证。

    Args:
        webhook_url: Webhook URL
        allowed_group_id: 允许的群组 ID
        blocked_group_id: 被阻止的群组 ID
        user_id: QQ 用户 ID

    Returns:
        True 如果白名单验证工作正常，False 否则
    """
    logger.info(
        "test_group_whitelist_start",
        allowed_group_id=allowed_group_id,
        blocked_group_id=blocked_group_id,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 测试允许的群组
            allowed_payload = {
                "group_id": allowed_group_id,
                "user_id": user_id,
                "message": "Mika, 测试白名单（允许的群组）",
                "images": [],
            }

            allowed_response = await client.post(
                webhook_url,
                json=allowed_payload,
                headers={"Content-Type": "application/json"},
            )

            allowed_data = (
                allowed_response.json()
                if allowed_response.status_code == 200
                else {}
            )
            allowed_triggered = (
                allowed_data.get("skip_pipeline", False)
                or allowed_data.get("success", False)
            )

            # 测试被阻止的群组
            blocked_payload = {
                "group_id": blocked_group_id,
                "user_id": user_id,
                "message": "Mika, 测试白名单（被阻止的群组）",
                "images": [],
            }

            blocked_response = await client.post(
                webhook_url,
                json=blocked_payload,
                headers={"Content-Type": "application/json"},
            )

            blocked_data = (
                blocked_response.json()
                if blocked_response.status_code == 200
                else {}
            )
            blocked_triggered = (
                blocked_data.get("skip_pipeline", False)
                or blocked_data.get("success", False)
            )

            # 验证结果
            # 允许的群组应该触发，被阻止的群组不应该触发
            whitelist_working = allowed_triggered and not blocked_triggered

            logger.info(
                "test_group_whitelist_result",
                allowed_group_triggered=allowed_triggered,
                blocked_group_triggered=blocked_triggered,
                whitelist_working=whitelist_working,
            )

            return whitelist_working

    except Exception as e:
        logger.error(
            "test_group_whitelist_error",
            error=str(e),
        )
        return False


async def test_private_message(webhook_url: str, user_id: str) -> bool:
    """
    测试私聊消息处理。

    Args:
        webhook_url: Webhook URL
        user_id: QQ 用户 ID

    Returns:
        True 如果私聊消息处理成功，False 否则
    """
    logger.info("test_private_message_start", user_id=user_id)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 私聊消息不需要 "Mika" 关键词
            private_payload = {
                "group_id": "",  # 空字符串表示私聊
                "user_id": user_id,
                "message": "你好，这是私聊测试",
                "images": [],
            }

            response = await client.post(
                webhook_url,
                json=private_payload,
                headers={"Content-Type": "application/json"},
            )

            response_data = response.json() if response.status_code == 200 else {}
            triggered = (
                response_data.get("skip_pipeline", False)
                or response_data.get("success", False)
            )

            logger.info(
                "test_private_message_result",
                status_code=response.status_code,
                triggered=triggered,
            )

            return triggered

    except Exception as e:
        logger.error(
            "test_private_message_error",
            error=str(e),
        )
        return False


async def main() -> None:
    """主测试函数。"""
    parser = argparse.ArgumentParser(
        description="LangBot 集成测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置测试
  python scripts/test_langbot_integration.py

  # 指定 webhook URL
  python scripts/test_langbot_integration.py --webhook-url https://api.yourdomain.com/webhook/langbot

  # 测试特定群组
  python scripts/test_langbot_integration.py --group-id 123456789 --user-id 987654321
        """,
    )

    parser.add_argument(
        "--webhook-url",
        type=str,
        default="http://localhost:8000/webhook/langbot",
        help="Webhook URL (默认: http://localhost:8000/webhook/langbot)",
    )
    parser.add_argument(
        "--group-id",
        type=str,
        default="123456789",
        help="测试群组 ID (默认: 123456789)",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default="987654321",
        help="测试用户 ID (默认: 987654321)",
    )
    parser.add_argument(
        "--skip-whitelist",
        action="store_true",
        help="跳过群组白名单测试",
    )

    args = parser.parse_args()

    logger.info(
        "test_start",
        webhook_url=args.webhook_url,
        group_id=args.group_id,
        user_id=args.user_id,
    )

    # 运行测试
    results = {}

    # 1. 测试 webhook 连接
    logger.info("=" * 60)
    logger.info("测试 1: Webhook 连接测试")
    logger.info("=" * 60)
    results["webhook_connection"] = await test_webhook_connection(args.webhook_url)

    if not results["webhook_connection"]:
        logger.error(
            "test_aborted",
            reason="Webhook 连接失败，无法继续测试",
        )
        sys.exit(1)

    # 2. 测试关键词触发
    logger.info("=" * 60)
    logger.info("测试 2: 关键词触发测试")
    logger.info("=" * 60)
    results["keyword_trigger"] = await test_keyword_trigger(
        args.webhook_url, args.group_id, args.user_id
    )

    # 3. 测试群组白名单（如果未跳过）
    if not args.skip_whitelist:
        logger.info("=" * 60)
        logger.info("测试 3: 群组白名单验证测试")
        logger.info("=" * 60)
        # 使用一个不同的群组 ID 作为被阻止的群组
        blocked_group_id = "999999999"
        results["group_whitelist"] = await test_group_whitelist(
            args.webhook_url,
            args.group_id,
            blocked_group_id,
            args.user_id,
        )
    else:
        logger.info("跳过群组白名单测试")
        results["group_whitelist"] = None

    # 4. 测试私聊消息
    logger.info("=" * 60)
    logger.info("测试 4: 私聊消息测试")
    logger.info("=" * 60)
    results["private_message"] = await test_private_message(
        args.webhook_url, args.user_id
    )

    # 汇总结果
    logger.info("=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败" if result is not None else "⊘ 跳过"
        logger.info("test_result", test_name=test_name, status=status)

    # 计算成功率
    completed_tests = [r for r in results.values() if r is not None]
    passed_tests = [r for r in completed_tests if r]
    success_rate = len(passed_tests) / len(completed_tests) * 100 if completed_tests else 0

    logger.info(
        "test_summary",
        total_tests=len(completed_tests),
        passed_tests=len(passed_tests),
        failed_tests=len(completed_tests) - len(passed_tests),
        success_rate=f"{success_rate:.1f}%",
    )

    # 退出码
    if all(r for r in completed_tests):
        logger.info("all_tests_passed")
        sys.exit(0)
    else:
        logger.warning("some_tests_failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
