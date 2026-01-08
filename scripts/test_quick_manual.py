#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速手动测试脚本 - 无需启动服务

这个脚本可以快速测试核心功能，无需启动 FastAPI、Temporal 或 MongoDB。

使用方法:
    poetry run python scripts/test_quick_manual.py
"""

import base64
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.steps.step1 import _detect_image_format, _validate_images, parse_input
from src.services.llm import _detect_image_mime_type
from src.utils.hashing import hash_user_id


def test_name_detection() -> bool:
    """测试名称检测功能。"""
    print("\n" + "=" * 60)
    print("测试 1: 名称检测")
    print("=" * 60)

    # 测试包含 "Mika" 的消息
    result1 = parse_input(
        user_id="123456",
        group_id="789012",
        message="Mika, 你好！",
        images=None,
    )
    print(f"✓ 包含 'Mika': {result1 is not None} (期望: True)")
    if result1:
        print(f"  - 哈希用户ID: {result1.hashed_user_id[:16]}...")
        print(f"  - 消息: {result1.message}")
        print(f"  - 语言: {result1.language}")

    # 测试不包含 "Mika" 的消息
    result2 = parse_input(
        user_id="123456",
        group_id="789012",
        message="今天天气真好",
        images=None,
    )
    print(f"✓ 不包含 'Mika': {result2 is None} (期望: True)")

    # 测试中文名称变体
    result3 = parse_input(
        user_id="123456",
        group_id="789012",
        message="米卡，帮我查一下歌曲",
        images=None,
    )
    print(f"✓ 包含 '米卡': {result3 is not None} (期望: True)")

    return result1 is not None and result2 is None and result3 is not None


def test_image_validation() -> bool:
    """测试图像验证功能。"""
    print("\n" + "=" * 60)
    print("测试 2: 图像验证")
    print("=" * 60)

    # 创建有效的 JPEG
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"x" * 5000
    jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")

    # 测试格式检测
    format_result = _detect_image_format(jpeg_data)
    print(f"✓ JPEG 格式检测: {format_result} (期望: jpeg)")

    # 测试 MIME 类型检测
    mime_result = _detect_image_mime_type(jpeg_base64)
    print(f"✓ JPEG MIME 类型: {mime_result} (期望: image/jpeg)")

    # 测试图像验证
    validated = _validate_images([jpeg_base64], "zh")
    print(f"✓ JPEG 验证: {validated is not None} (期望: True)")
    if validated:
        print(f"  - 验证后的图像数量: {len(validated)}")

    # 测试无效格式 (GIF)
    gif_data = b"GIF89a" + b"x" * 1000
    gif_base64 = base64.b64encode(gif_data).decode("utf-8")
    validated_gif = _validate_images([gif_base64], "zh")
    print(f"✓ GIF 验证 (应该失败): {validated_gif is None} (期望: True)")

    return (
        format_result == "jpeg"
        and mime_result == "image/jpeg"
        and validated is not None
        and validated_gif is None
    )


def test_parse_input_with_images() -> bool:
    """测试 parse_input 与图像。"""
    print("\n" + "=" * 60)
    print("测试 3: parse_input 图像处理")
    print("=" * 60)

    # 创建有效的 JPEG
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01" + b"x" * 5000
    jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")

    # 测试 parse_input 与图像
    result = parse_input(
        user_id="test_user_001",
        group_id="test_group_001",
        message="Mika, 看看这张图片",
        images=[jpeg_base64],
    )

    if result:
        print(f"✓ 成功解析输入")
        print(f"  - 哈希用户ID: {result.hashed_user_id[:16]}...")
        print(f"  - 消息: {result.message}")
        print(f"  - 图像数量: {len(result.images)}")
        return True
    else:
        print("✗ 解析失败")
        return False


def test_user_id_hashing() -> bool:
    """测试用户ID哈希功能。"""
    print("\n" + "=" * 60)
    print("测试 4: 用户ID哈希")
    print("=" * 60)

    user_id = "123456789"
    hashed1 = hash_user_id(user_id)
    hashed2 = hash_user_id(user_id)

    print(f"✓ 哈希一致性: {hashed1 == hashed2} (期望: True)")
    print(f"  - 哈希长度: {len(hashed1)} (期望: 64)")
    print(f"  - 哈希值 (前16字符): {hashed1[:16]}...")

    return hashed1 == hashed2 and len(hashed1) == 64


def main() -> None:
    """运行所有快速测试。"""
    print("=" * 60)
    print("Mika Taiko Chatbot - 快速手动测试")
    print("=" * 60)
    print("\n这些测试不需要启动服务（FastAPI、Temporal、MongoDB）")
    print("可以快速验证核心功能是否正常工作。\n")

    results = []

    # 运行测试
    results.append(("名称检测", test_name_detection()))
    results.append(("图像验证", test_image_validation()))
    results.append(("parse_input 图像处理", test_parse_input_with_images()))
    results.append(("用户ID哈希", test_user_id_hashing()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[成功] 所有快速测试通过！")
        print("\n下一步: 启动服务进行完整测试")
        print("  1. 启动 FastAPI: poetry run uvicorn src.api.main:app --reload")
        print("  2. 启动 Temporal Worker: poetry run python -m src.workers.temporal_worker")
        print("  3. 使用 curl 或浏览器测试 webhook 端点")
        return 0
    else:
        print("\n[失败] 部分测试未通过，请检查代码")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
