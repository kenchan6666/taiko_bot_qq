#!/usr/bin/env python3
"""
Simple webhook test script for Mika Taiko Chatbot.

This script tests the webhook endpoint by sending HTTP requests.
Requires FastAPI server to be running.

Usage:
    # Start FastAPI server first:
    # uvicorn src.api.main:app --reload
    
    # Then run this script:
    poetry run python scripts/test_webhook_simple.py
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_webhook(
    base_url: str = "http://localhost:8000",
    message: str = "Mika, 你好！",
    group_id: str = "123456789",
    user_id: str = "987654321",
) -> None:
    """
    Test webhook endpoint.
    
    Args:
        base_url: FastAPI server base URL
        message: Test message
        group_id: Test group ID
        user_id: Test user ID
    """
    url = f"{base_url}/webhook/langbot"
    
    payload = {
        "group_id": group_id,
        "user_id": user_id,
        "message": message,
        "images": [],
    }
    
    print(f"Testing webhook: {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
            
            if response.status_code == 200:
                print("\n✓ Webhook test successful!")
                return True
            else:
                print(f"\n✗ Webhook test failed with status {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print("\n✗ Connection failed!")
        print("  Make sure FastAPI server is running:")
        print("  uvicorn src.api.main:app --reload")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


async def main() -> None:
    """Run webhook tests."""
    print("=" * 60)
    print("Mika Taiko Chatbot - Webhook Test")
    print("=" * 60)
    print()
    
    # Test 1: Message with "Mika"
    print("Test 1: Message with 'Mika' mention")
    print("-" * 60)
    result1 = await test_webhook(message="Mika, 你好！")
    print()
    
    # Test 2: Message without "Mika"
    print("Test 2: Message without 'Mika' mention")
    print("-" * 60)
    result2 = await test_webhook(message="今天天气真好")
    print()
    
    # Test 3: Song query
    print("Test 3: Song query")
    print("-" * 60)
    result3 = await test_webhook(message="Mika, what's the BPM of 千本桜?")
    print()
    
    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum([result1, result2, result3])
    print(f"Passed: {passed}/3")
    
    if passed == 3:
        print("[SUCCESS] All webhook tests passed!")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
