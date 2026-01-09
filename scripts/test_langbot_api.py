#!/usr/bin/env python3
"""
Test LangBot API connection and message sending.

Usage:
    poetry run python scripts/test_langbot_api.py
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings


async def test_langbot_api() -> None:
    """Test LangBot API connection and message sending."""
    print("=" * 60)
    print("LangBot API Test")
    print("=" * 60)
    print()
    
    # Check configuration
    api_key = settings.langbot_api_key
    api_base_url = settings.langbot_api_base_url
    
    if not api_key:
        print("✗ LANGBOT_API_KEY: NOT SET")
        print("  → Add to .env file: LANGBOT_API_KEY=lbk_...")
        return
    
    if not api_base_url:
        print("✗ LANGBOT_API_BASE_URL: NOT SET")
        print("  → Add to .env file: LANGBOT_API_BASE_URL=http://localhost:5300")
        return
    
    print(f"✓ LANGBOT_API_KEY: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else 'SET'}")
    print(f"✓ LANGBOT_API_BASE_URL: {api_base_url}")
    print()
    
    # Test API connection
    # Note: We need bot_uuid to send a message, but we can at least test the API endpoint
    print("Testing LangBot API connection...")
    print()
    
    # Use a test bot UUID (you'll need to replace this with your actual bot UUID)
    # From the logs, I can see: c667dddf-be66-4bf9-bb4a-b8105587ecbb
    test_bot_uuid = "c667dddf-be66-4bf9-bb4a-b8105587ecbb"
    test_target_id = "2443939219"  # From previous logs
    
    api_url = f"{api_base_url}/api/v1/platform/bots/{test_bot_uuid}/send_message"
    
    payload = {
        "target_type": "person",
        "target_id": test_target_id,
        "message_chain": [
            {
                "type": "Plain",
                "text": "测试消息：这是通过 LangBot API 发送的测试消息。",
            }
        ],
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"POST {api_url}")
            print(f"Headers: X-API-Key: {api_key[:10]}...")
            print(f"Payload: {payload}")
            print()
            
            response = await client.post(
                api_url,
                json=payload,
                headers={
                    "X-API-Key": api_key,
                    "Content-Type": "application/json",
                },
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            print()
            
            if response.status_code == 200:
                print("✓ API test successful! Message should be sent.")
            elif response.status_code == 401:
                print("✗ API Key authentication failed (401 Unauthorized)")
                print("  → Check if API key is correct")
            elif response.status_code == 404:
                print("✗ Bot UUID not found (404 Not Found)")
                print("  → Check if bot UUID is correct")
            else:
                print(f"✗ API test failed with status {response.status_code}")
                print(f"  → Response: {response.text[:200]}")
                
    except httpx.ConnectError:
        print("✗ Connection failed!")
        print(f"  → Cannot connect to {api_base_url}")
        print("  → Make sure LangBot is running and accessible")
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"  → Error type: {type(e).__name__}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_langbot_api())
