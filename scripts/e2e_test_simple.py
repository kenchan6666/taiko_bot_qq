#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的端到端测试脚本

使用方法:
    poetry run python scripts/e2e_test_simple.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx


BASE_URL = "http://localhost:8000"


async def test_health_check() -> bool:
    """测试健康检查端点。"""
    print("\n[测试 1] 健康检查...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("  ✓ 健康检查通过")
                print(f"  响应: {response.json()}")
                return True
            else:
                print(f"  ✗ 健康检查失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"  ✗ 健康检查失败: {e}")
        return False


async def test_basic_message() -> bool:
    """测试基本消息处理。"""
    print("\n[测试 2] 基本消息（问候）...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/webhook/langbot",
                json={
                    "group_id": "test_group_001",
                    "user_id": "test_user_001",
                    "message": "Mika, 你好！",
                    "images": [],
                },
            )
            if response.status_code == 200:
                data = response.json()
                print("  ✓ 基本消息处理成功")
                print(f"  响应: {data.get('response', 'N/A')[:100]}...")
                return True
            else:
                print(f"  ✗ 基本消息处理失败: HTTP {response.status_code}")
                print(f"  响应: {response.text}")
                return False
    except Exception as e:
        print(f"  ✗ 基本消息处理失败: {e}")
        return False


async def test_song_recommendation() -> bool:
    """测试歌曲推荐（场景化）。"""
    print("\n[测试 3] 歌曲推荐（高 BPM 场景）...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/webhook/langbot",
                json={
                    "group_id": "test_group_001",
                    "user_id": "test_user_001",
                    "message": "Mika, 推荐一些高 BPM 的歌曲",
                    "images": [],
                },
            )
            if response.status_code == 200:
                data = response.json()
                print("  ✓ 歌曲推荐成功")
                print(f"  响应: {data.get('response', 'N/A')[:100]}...")
                return True
            else:
                print(f"  ✗ 歌曲推荐失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"  ✗ 歌曲推荐失败: {e}")
        return False


async def test_song_query() -> bool:
    """测试歌曲查询。"""
    print("\n[测试 4] 歌曲查询...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/webhook/langbot",
                json={
                    "group_id": "test_group_001",
                    "user_id": "test_user_001",
                    "message": "Mika, 千本桜的BPM是多少？",
                    "images": [],
                },
            )
            if response.status_code == 200:
                data = response.json()
                print("  ✓ 歌曲查询成功")
                print(f"  响应: {data.get('response', 'N/A')[:100]}...")
                return True
            else:
                print(f"  ✗ 歌曲查询失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"  ✗ 歌曲查询失败: {e}")
        return False


async def test_game_tips() -> bool:
    """测试游戏技巧请求。"""
    print("\n[测试 5] 游戏技巧请求...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/webhook/langbot",
                json={
                    "group_id": "test_group_001",
                    "user_id": "test_user_001",
                    "message": "Mika, 有什么游戏技巧吗？",
                    "images": [],
                },
            )
            if response.status_code == 200:
                data = response.json()
                print("  ✓ 游戏技巧请求成功")
                print(f"  响应: {data.get('response', 'N/A')[:100]}...")
                return True
            else:
                print(f"  ✗ 游戏技巧请求失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"  ✗ 游戏技巧请求失败: {e}")
        return False


async def test_message_filtering() -> bool:
    """测试消息过滤（无 Mika 提及）。"""
    print("\n[测试 6] 消息过滤（无 Mika 提及）...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/webhook/langbot",
                json={
                    "group_id": "test_group_001",
                    "user_id": "test_user_001",
                    "message": "今天天气不错",
                    "images": [],
                },
            )
            if response.status_code == 200:
                data = response.json()
                print("  ✓ 消息过滤测试完成")
                if data.get("response"):
                    print(f"  响应: {data.get('response', 'N/A')[:100]}...")
                else:
                    print("  消息被正确过滤（无响应）")
                return True
            else:
                print(f"  ✗ 消息过滤测试失败: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"  ✗ 消息过滤测试失败: {e}")
        return False


async def main() -> None:
    """运行所有测试。"""
    print("=" * 60)
    print("端到端测试 (E2E Testing)")
    print("=" * 60)
    print("\n确保以下服务正在运行:")
    print("  1. FastAPI: http://localhost:8000")
    print("  2. Temporal Worker")
    print("  3. MongoDB")
    print("  4. Temporal Server")
    print("\n开始测试...\n")

    results = []

    # 运行测试
    results.append(("健康检查", await test_health_check()))
    results.append(("基本消息", await test_basic_message()))
    results.append(("歌曲推荐", await test_song_recommendation()))
    results.append(("歌曲查询", await test_song_query()))
    results.append(("游戏技巧", await test_game_tips()))
    results.append(("消息过滤", await test_message_filtering()))

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n通过: {passed}/{total}")
    print(f"失败: {total - passed}/{total}")
    print(f"通过率: {passed/total*100:.1f}%")

    print("\n详细结果:")
    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"  {status} {name}")

    if passed == total:
        print("\n✓ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n✗ 部分测试失败，请检查日志")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
