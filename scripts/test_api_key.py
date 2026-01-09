"""
快速测试 OpenRouter API Key
使用方法: poetry run python scripts/test_api_key.py
"""

import asyncio
import httpx
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 要测试的 API Key
API_KEY = "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"

async def test_api_key():
    """测试 API Key 是否有效"""
    print("=== 测试 OpenRouter API Key ===\n")
    print(f"API Key: {API_KEY[:20]}...\n")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "openai/gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": "你好，请用一句话回复。"
            }
        ],
        "max_tokens": 50,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("正在调用 OpenRouter API...")
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"状态码: {response.status_code}\n")
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    print("[SUCCESS] API Key is valid!")
                    print(f"\nResponse: {content}\n")
                    print("[OK] This API Key works correctly")
                    print("\nPlease update .env file:")
                    print(f"  OPENROUTER_API_KEY={API_KEY}")
                    return True
                else:
                    print("[ERROR] API response format is invalid")
                    print(f"Response content: {response.text[:200]}")
                    return False
            else:
                print(f"[ERROR] API call failed (Status: {response.status_code})")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Error content: {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_key())
    sys.exit(0 if success else 1)
