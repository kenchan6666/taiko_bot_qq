#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动图像测试脚本 - 用于快速测试图像处理功能

这个脚本帮助您：
1. 创建测试图像（JPEG/PNG/WebP）
2. 测试图像验证功能
3. 发送带图像的 webhook 请求

使用方法:
    poetry run python scripts/test_image_manual.py
"""

import asyncio
import base64
import io
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[警告] PIL/Pillow 未安装，无法创建测试图像")
    print("安装: poetry add pillow")

import httpx

from src.steps.step1 import _detect_image_format, _validate_images, parse_input
from src.services.llm import _detect_image_mime_type


def create_test_jpeg(size: tuple[int, int] = (100, 100), color: str = "red") -> bytes:
    """
    创建测试 JPEG 图像。

    Args:
        size: 图像尺寸 (width, height)
        color: 颜色名称 ("red", "blue", "green")

    Returns:
        JPEG 图像的二进制数据
    """
    if not HAS_PIL:
        # 创建最小有效 JPEG (magic bytes only)
        return b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"x" * 1000

    color_map = {
        "red": (255, 0, 0),
        "blue": (0, 0, 255),
        "green": (0, 255, 0),
        "yellow": (255, 255, 0),
    }
    rgb = color_map.get(color, (255, 0, 0))

    img = Image.new("RGB", size, color=rgb)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def create_test_png(size: tuple[int, int] = (100, 100), color: str = "blue") -> bytes:
    """
    创建测试 PNG 图像。

    Args:
        size: 图像尺寸 (width, height)
        color: 颜色名称

    Returns:
        PNG 图像的二进制数据
    """
    if not HAS_PIL:
        # 创建最小有效 PNG (magic bytes only)
        return b"\x89PNG\r\n\x1a\n" + b"x" * 1000

    color_map = {
        "red": (255, 0, 0),
        "blue": (0, 0, 255),
        "green": (0, 255, 0),
        "yellow": (255, 255, 0),
    }
    rgb = color_map.get(color, (0, 0, 255))

    img = Image.new("RGB", size, color=rgb)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_test_webp(size: tuple[int, int] = (100, 100), color: str = "green") -> bytes:
    """
    创建测试 WebP 图像。

    Args:
        size: 图像尺寸 (width, height)
        color: 颜色名称

    Returns:
        WebP 图像的二进制数据
    """
    if not HAS_PIL:
        # 创建最小有效 WebP (RIFF...WEBP)
        return b"RIFF" + b"x" * 4 + b"WEBP" + b"x" * 1000

    color_map = {
        "red": (255, 0, 0),
        "blue": (0, 0, 255),
        "green": (0, 255, 0),
        "yellow": (255, 255, 0),
    }
    rgb = color_map.get(color, (0, 255, 0))

    img = Image.new("RGB", size, color=rgb)
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP")
    return buffer.getvalue()


def test_image_validation() -> None:
    """测试图像验证功能。"""
    print("\n" + "=" * 60)
    print("测试 1: 图像验证功能")
    print("=" * 60)

    # 创建测试图像
    jpeg_data = create_test_jpeg()
    png_data = create_test_png()
    webp_data = create_test_webp()

    # 转换为 base64
    jpeg_base64 = base64.b64encode(jpeg_data).decode("utf-8")
    png_base64 = base64.b64encode(png_data).decode("utf-8")
    webp_base64 = base64.b64encode(webp_data).decode("utf-8")

    # 测试格式检测
    print("\n[格式检测测试]")
    jpeg_format = _detect_image_format(jpeg_data)
    png_format = _detect_image_format(png_data)
    webp_format = _detect_image_format(webp_data)
    print(f"  JPEG 格式检测: {jpeg_format} (期望: jpeg)")
    print(f"  PNG 格式检测: {png_format} (期望: png)")
    print(f"  WebP 格式检测: {webp_format} (期望: webp)")

    # 测试 MIME 类型检测
    print("\n[MIME 类型检测测试]")
    jpeg_mime = _detect_image_mime_type(jpeg_base64)
    png_mime = _detect_image_mime_type(png_base64)
    webp_mime = _detect_image_mime_type(webp_base64)
    print(f"  JPEG MIME: {jpeg_mime} (期望: image/jpeg)")
    print(f"  PNG MIME: {png_mime} (期望: image/png)")
    print(f"  WebP MIME: {webp_mime} (期望: image/webp)")

    # 测试图像验证
    print("\n[图像验证测试]")
    validated_jpeg = _validate_images([jpeg_base64], "zh")
    validated_png = _validate_images([png_base64], "zh")
    validated_webp = _validate_images([webp_base64], "zh")
    print(f"  JPEG 验证: {'通过' if validated_jpeg else '失败'}")
    print(f"  PNG 验证: {'通过' if validated_png else '失败'}")
    print(f"  WebP 验证: {'通过' if validated_webp else '失败'}")

    # 测试无效格式
    gif_data = b"GIF89a" + b"x" * 1000
    gif_base64 = base64.b64encode(gif_data).decode("utf-8")
    validated_gif = _validate_images([gif_base64], "zh")
    print(f"  GIF 验证 (应该失败): {'失败 ✓' if validated_gif is None else '通过 ✗'}")

    return jpeg_base64, png_base64, webp_base64


def test_parse_input_with_images(jpeg_base64: str) -> None:
    """测试 parse_input 与图像。"""
    print("\n" + "=" * 60)
    print("测试 2: parse_input 图像处理")
    print("=" * 60)

    # 测试有效图像
    result = parse_input(
        user_id="test_user_001",
        group_id="test_group_001",
        message="Mika, 看看这张图片",
        images=[jpeg_base64],
    )

    if result:
        print(f"  ✓ 成功解析输入")
        print(f"  - 哈希用户ID: {result.hashed_user_id[:16]}...")
        print(f"  - 消息: {result.message}")
        print(f"  - 图像数量: {len(result.images)}")
    else:
        print("  ✗ 解析失败")


async def test_webhook_with_image(
    base_url: str = "http://localhost:8000", image_base64: str = ""
) -> None:
    """测试带图像的 webhook 请求。"""
    print("\n" + "=" * 60)
    print("测试 3: Webhook 图像请求")
    print("=" * 60)

    if not image_base64:
        print("  [跳过] 没有提供图像数据")
        return

    url = f"{base_url}/webhook/langbot"

    payload = {
        "group_id": "test_group_001",
        "user_id": "test_user_001",
        "message": "Mika, 看看这张图片",
        "images": [image_base64],
    }

    print(f"\n发送请求到: {url}")
    print(f"消息: {payload['message']}")
    print(f"图像大小: {len(image_base64)} 字符 (base64)")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            print(f"\n状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"成功: {result.get('success', False)}")
                print(f"响应: {result.get('response', '')[:100]}...")
                print("\n  ✓ Webhook 测试成功!")
            else:
                print(f"  ✗ Webhook 测试失败: {response.status_code}")
                print(f"  响应: {response.text[:200]}")

    except httpx.ConnectError:
        print("\n  ✗ 连接失败!")
        print("  请确保 FastAPI 服务器正在运行:")
        print("  uvicorn src.api.main:app --reload")
    except Exception as e:
        print(f"\n  ✗ 错误: {e}")


def print_manual_test_instructions() -> None:
    """打印手动测试说明。"""
    print("\n" + "=" * 60)
    print("手动测试说明")
    print("=" * 60)
    print("""
您可以使用以下方法进行手动测试：

1. **使用 curl 命令**:
   
   # 准备图像 base64 (使用上面的函数创建)
   JPEG_BASE64="your_base64_string_here"
   
   # 发送请求
   curl -X POST http://localhost:8000/webhook/langbot \\
     -H "Content-Type: application/json" \\
     -d "{
       \\"group_id\\": \\"test_group_001\\",
       \\"user_id\\": \\"test_user_001\\",
       \\"message\\": \\"Mika, 看看这张图片\\",
       \\"images\\": [\\"$JPEG_BASE64\\"]
     }"

2. **使用 Python REPL**:
   
   from scripts.test_image_manual import create_test_jpeg
   import base64
   
   jpeg_data = create_test_jpeg()
   jpeg_base64 = base64.b64encode(jpeg_data).decode('utf-8')
   
   # 然后使用 httpx 或 requests 发送请求

3. **使用 Postman/Insomnia**:
   - 方法: POST
   - URL: http://localhost:8000/webhook/langbot
   - Headers: Content-Type: application/json
   - Body (JSON):
     {
       "group_id": "test_group_001",
       "user_id": "test_user_001",
       "message": "Mika, 看看这张图片",
       "images": ["base64_encoded_image_here"]
     }

4. **查看详细手动测试指南**:
   查看 MANUAL_TESTING_GUIDE.md 文件
""")


async def main() -> None:
    """运行所有测试。"""
    print("=" * 60)
    print("Mika Taiko Chatbot - 图像处理手动测试")
    print("=" * 60)

    # 测试 1: 图像验证
    jpeg_base64, png_base64, webp_base64 = test_image_validation()

    # 测试 2: parse_input
    test_parse_input_with_images(jpeg_base64)

    # 测试 3: Webhook (需要服务器运行)
    print("\n" + "=" * 60)
    print("提示: 要测试 webhook，请先启动 FastAPI 服务器")
    print("命令: uvicorn src.api.main:app --reload")
    print("=" * 60)

    user_input = input("\n是否要测试 webhook? (需要服务器运行) [y/N]: ")
    if user_input.lower() == "y":
        await test_webhook_with_image(image_base64=jpeg_base64)

    # 打印手动测试说明
    print_manual_test_instructions()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
