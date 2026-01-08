#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic functionality test script for Mika Taiko Chatbot.

This script tests the core functionality without requiring:
- MongoDB (uses mocked data)
- Temporal (tests step functions directly)
- OpenRouter API (uses mocked LLM responses)

Usage:
    poetry run python scripts/test_basic.py
"""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows console encoding for UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from unittest.mock import AsyncMock, MagicMock, patch

from src.steps import step1, step2, step3, step4, step5
from src.utils.hashing import hash_user_id


async def test_step1_name_detection() -> None:
    """Test step1: Name detection and content filtering."""
    print("\n=== Testing Step 1: Name Detection ===")
    
    # Test 1: Message with "Mika" mention
    result1 = step1.parse_input(
        user_id="123456",
        group_id="789012",
        message="Mika, 你好！",
        images=None,
    )
    print(f"[PASS] Test 1 - Message with 'Mika': {result1 is not None}")
    if result1:
        print(f"  - Hashed user ID: {result1.hashed_user_id[:16]}...")
        print(f"  - Message: {result1.message[:30]}...")
        print(f"  - Language: {result1.language}")
    
    # Test 2: Message without "Mika" mention
    result2 = step1.parse_input(
        user_id="123456",
        group_id="789012",
        message="你好，今天天气真好",
        images=None,
    )
    print(f"[PASS] Test 2 - Message without 'Mika': {result2 is None}")
    
    # Test 3: Message with Chinese name variant
    result3 = step1.parse_input(
        user_id="123456",
        group_id="789012",
        message="米卡，帮我查一下歌曲",
        images=None,
    )
    print(f"[PASS] Test 3 - Message with '米卡': {result3 is not None}")
    
    return result1 is not None and result2 is None and result3 is not None


async def test_step2_context_retrieval() -> None:
    """Test step2: Context retrieval (mocked)."""
    print("\n=== Testing Step 2: Context Retrieval ===")
    
    hashed_id = hash_user_id("123456")
    
    # Mock database query
    # Beanie's find_one is a class method that returns an awaitable
    with patch("src.steps.step2.User.find_one", new_callable=AsyncMock) as mock_user, \
         patch("src.steps.step2.Impression.find_one", new_callable=AsyncMock) as mock_impression, \
         patch("src.steps.step2.Conversation.find") as mock_conversation:
        
        # Mock user
        mock_user_obj = MagicMock()
        mock_user_obj.preferred_language = "zh"
        mock_user.return_value = mock_user_obj
        
        # Mock impression
        mock_impression_obj = MagicMock()
        mock_impression_obj.preferences = {}
        mock_impression_obj.relationship_status = "neutral"
        mock_impression.return_value = mock_impression_obj
        
        # Mock conversations - find() returns a query builder that chains sort().limit().to_list()
        mock_query_builder = MagicMock()
        mock_query_builder.sort.return_value = mock_query_builder
        mock_query_builder.limit.return_value = mock_query_builder
        mock_query_builder.to_list = AsyncMock(return_value=[])
        mock_conversation.return_value = mock_query_builder
        
        parsed_input = step1.parse_input(
            user_id="123456",
            group_id="789012",
            message="Mika, 你好",
            images=None,
        )
        
        if parsed_input:
            # retrieve_context takes hashed_user_id as parameter, not parsed_input
            context = await step2.retrieve_context(parsed_input.hashed_user_id)
            print(f"[PASS] Context retrieved: {context is not None}")
            if context:
                print(f"  - User language: {context.user.preferred_language if context.user else 'None'}")
                return True
    
    return False


async def test_step3_song_query() -> None:
    """Test step3: Song query (mocked)."""
    print("\n=== Testing Step 3: Song Query ===")
    
    parsed_input = step1.parse_input(
        user_id="123456",
        group_id="789012",
        message="Mika, what's the BPM of 千本桜?",
        images=None,
    )
    
    if not parsed_input:
        print("[FAIL] Could not parse input")
        return False
    
    # Mock song query service
    with patch("src.steps.step3.get_song_service") as mock_service:
        mock_song = {
            "name": "千本桜",
            "bpm": 200,
            "difficulty_stars": 8,
            "metadata": {},
        }
        mock_service_instance = MagicMock()
        mock_service_instance.query_song = MagicMock(return_value=mock_song)
        mock_service_instance.ensure_cache_fresh = AsyncMock()
        mock_service.return_value = mock_service_instance
        
        # query_song takes message string as parameter, not parsed_input
        # step3.query_song() returns dict with "song_name" key (converted from song["name"])
        song_info = await step3.query_song(parsed_input.message)
        print(f"[PASS] Song query result: {song_info is not None}")
        if song_info:
            print(f"  - Song name: {song_info.get('song_name', 'N/A')}")
            print(f"  - BPM: {song_info.get('bpm', 'N/A')}")
            return True
    
    return False


async def test_step4_llm_invocation() -> None:
    """Test step4: LLM invocation (mocked)."""
    print("\n=== Testing Step 4: LLM Invocation ===")
    
    parsed_input = step1.parse_input(
        user_id="123456",
        group_id="789012",
        message="Mika, 你好！",
        images=None,
    )
    
    if not parsed_input:
        print("[FAIL] Could not parse input")
        return False
    
    # Mock context
    mock_context = MagicMock()
    mock_context.user = None
    mock_context.impression = None
    mock_context.recent_conversations = []
    
    # Mock LLM service and PromptManager
    with patch("src.steps.step4.get_llm_service") as mock_llm, \
         patch("src.steps.step4.get_prompt_manager") as mock_prompt_manager:
        
        # Mock prompt manager
        mock_pm_instance = MagicMock()
        mock_pm_instance.get_prompt = MagicMock(return_value="Mock prompt template")
        mock_prompt_manager.return_value = mock_pm_instance
        
        # Mock LLM service
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_response = AsyncMock(
            return_value="你好！我是 Mika，很高兴认识你！🥁"
        )
        mock_llm.return_value = mock_llm_instance
        
        response = await step4.invoke_llm(
            parsed_input=parsed_input,
            context=mock_context,
            song_info=None,
        )
        print(f"[PASS] LLM response generated: {response is not None}")
        if response:
            print(f"  - Response: {response[:50]}...")
            return True
    
    return False


async def test_step5_impression_update() -> None:
    """Test step5: Impression update (mocked)."""
    print("\n=== Testing Step 5: Impression Update ===")
    
    parsed_input = step1.parse_input(
        user_id="123456",
        group_id="789012",
        message="Mika, 我喜欢太鼓达人！",
        images=None,
    )
    
    if not parsed_input:
        print("[FAIL] Could not parse input")
        return False
    
    # Mock context and response
    mock_context = MagicMock()
    mock_response = "我也喜欢太鼓达人！🥁"
    
    # Mock database operations
    # step5.update_impression() uses User.insert(), Impression.insert(), Conversation.insert()
    with patch("src.steps.step5.User") as mock_user, \
         patch("src.steps.step5.Impression") as mock_impression, \
         patch("src.steps.step5.Conversation") as mock_conversation:
        
        # Mock User
        mock_user_instance = MagicMock()
        mock_user_instance.insert = AsyncMock()
        mock_user_instance.save = AsyncMock()
        mock_user_instance.update_timestamp = MagicMock()
        mock_user.return_value = mock_user_instance
        
        # Mock Impression
        mock_impression_instance = MagicMock()
        mock_impression_instance.insert = AsyncMock()
        mock_impression_instance.save = AsyncMock()
        mock_impression_instance.increment_interaction = MagicMock()
        mock_impression.return_value = mock_impression_instance
        
        # Mock Conversation
        mock_conv_instance = MagicMock()
        mock_conv_instance.insert = AsyncMock()
        mock_conversation.create = MagicMock(return_value=mock_conv_instance)
        
        # Mock context to have no existing user/impression (new user scenario)
        mock_context.user = None
        mock_context.impression = None
        
        await step5.update_impression(
            parsed_input=parsed_input,
            context=mock_context,
            response=mock_response,
        )
        print("[PASS] Impression update completed (mocked)")
        return True


async def test_webhook_endpoint() -> None:
    """Test webhook endpoint (requires FastAPI app)."""
    print("\n=== Testing Webhook Endpoint ===")
    print("[INFO] This test requires FastAPI server to be running")
    print("   Run: uvicorn src.api.main:app --reload")
    print("   Then test with: curl -X POST http://localhost:8000/webhook/langbot \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"group_id\":\"123\",\"user_id\":\"456\",\"message\":\"Mika, 你好\",\"images\":[]}'")
    return True


async def main() -> None:
    """Run all basic tests."""
    print("=" * 60)
    print("Mika Taiko Chatbot - Basic Functionality Test")
    print("=" * 60)
    
    results = []
    
    # Test each step
    results.append(await test_step1_name_detection())
    results.append(await test_step2_context_retrieval())
    results.append(await test_step3_song_query())
    results.append(await test_step4_llm_invocation())
    results.append(await test_step5_impression_update())
    await test_webhook_endpoint()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] All basic tests passed!")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
