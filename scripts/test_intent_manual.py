#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动测试意图检测和场景化提示选择功能

这个脚本可以快速测试 Phase 7 的意图分类和场景化提示功能。

使用方法:
    poetry run python scripts/test_intent_manual.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.intent_detection import get_intent_detection_service
from src.steps.step1 import parse_input
from src.prompts import get_prompt_manager


async def test_intent_detection() -> None:
    """测试意图检测功能。"""
    print("\n" + "=" * 60)
    print("测试 1: 意图检测")
    print("=" * 60)
    
    service = get_intent_detection_service()
    
    test_cases = [
        ("Mika, 你好！", "greeting"),
        ("Mika, 你能做什么？", "help"),
        ("Mika, 推荐一些歌曲", "song_recommendation"),
        ("Mika, 千本桜的BPM是多少？", "song_query"),
        ("Mika, 有什么游戏技巧吗？", "game_tips"),
        ("Mika, 推荐一些高 BPM 的歌曲", "song_recommendation"),
    ]
    
    for message, expected_intent in test_cases:
        intent = await service.detect_intent(message)
        status = "[OK]" if intent == expected_intent else "[FAIL]"
        print(f"{status} 消息: {message[:30]}...")
        print(f"   检测意图: {intent} (期望: {expected_intent})")
        if intent != expected_intent:
            print(f"   [WARNING] 意图不匹配")


async def test_scenario_detection() -> None:
    """测试场景检测功能。"""
    print("\n" + "=" * 60)
    print("测试 2: 场景检测")
    print("=" * 60)
    
    service = get_intent_detection_service()
    
    test_cases = [
        ("推荐一些高 BPM 的歌曲", "song_recommendation", "song_recommendation_high_bpm"),
        ("推荐适合新手的歌曲", "song_recommendation", "song_recommendation_beginner_friendly"),
        ("新手怎么开始？", "difficulty_advice", "difficulty_advice_beginner"),
        ("高级玩家怎么提高？", "difficulty_advice", "difficulty_advice_expert"),
        ("怎么提高节奏感？", "game_tips", "game_tips_timing"),
        ("怎么提高准确率？", "game_tips", "game_tips_accuracy"),
    ]
    
    for message, intent, expected_scenario in test_cases:
        scenario = service.detect_scenario(message, intent=intent)
        status = "[OK]" if scenario == expected_scenario else "[FAIL]"
        print(f"{status} 消息: {message[:30]}...")
        print(f"   意图: {intent}, 检测场景: {scenario} (期望: {expected_scenario})")
        if scenario != expected_scenario:
            print(f"   [WARNING] 场景不匹配")


async def test_combined_detection() -> None:
    """测试组合检测（意图+场景）。"""
    print("\n" + "=" * 60)
    print("测试 3: 组合检测（意图 + 场景）")
    print("=" * 60)
    
    service = get_intent_detection_service()
    
    test_cases = [
        ("Mika, 推荐一些高 BPM 的歌曲", "song_recommendation", "song_recommendation_high_bpm"),
        ("Mika, 推荐适合新手的歌曲", "song_recommendation", "song_recommendation_beginner_friendly"),
    ]
    
    for message, expected_intent, expected_scenario in test_cases:
        intent, scenario = await service.detect_intent_and_scenario(message)
        intent_ok = intent == expected_intent
        scenario_ok = scenario == expected_scenario
        status = "[OK]" if (intent_ok and scenario_ok) else "[FAIL]"
        print(f"{status} 消息: {message[:30]}...")
        print(f"   意图: {intent} (期望: {expected_intent}) {'[OK]' if intent_ok else '[FAIL]'}")
        print(f"   场景: {scenario} (期望: {expected_scenario}) {'[OK]' if scenario_ok else '[FAIL]'}")


async def test_parse_input_with_intent() -> None:
    """测试 parse_input 集成意图检测。"""
    print("\n" + "=" * 60)
    print("测试 4: parse_input 意图检测集成")
    print("=" * 60)
    
    test_cases = [
        ("Mika, 你好！", "greeting", None),
        ("Mika, 推荐一些高 BPM 的歌曲", "song_recommendation", "song_recommendation_high_bpm"),
    ]
    
    for message, expected_intent, expected_scenario in test_cases:
        parsed = await parse_input(
            user_id="test_user",
            group_id="test_group",
            message=message,
            images=None,
        )
        
        if parsed:
            intent_ok = parsed.intent == expected_intent
            scenario_ok = parsed.scenario == expected_scenario
            status = "[OK]" if (intent_ok and scenario_ok) else "[FAIL]"
            print(f"{status} 消息: {message[:30]}...")
            print(f"   检测意图: {parsed.intent} (期望: {expected_intent})")
            print(f"   检测场景: {parsed.scenario} (期望: {expected_scenario})")
        else:
            print(f"[FAIL] 消息被拒绝: {message[:30]}...")


def test_prompt_templates() -> None:
    """测试提示模板是否存在。"""
    print("\n" + "=" * 60)
    print("测试 5: 提示模板验证")
    print("=" * 60)
    
    manager = get_prompt_manager()
    
    # 检查意图特定提示
    intent_prompts = [
        "intent_greeting",
        "intent_help",
        "intent_goodbye",
        "intent_song_recommendation",
        "intent_difficulty_advice",
        "intent_bpm_analysis",
        "intent_game_tips",
        "intent_achievement_celebration",
        "intent_practice_advice",
    ]
    
    print("\n意图特定提示:")
    for prompt_name in intent_prompts:
        try:
            # 尝试获取提示（不渲染，只检查是否存在）
            # 使用 get_prompt 会尝试渲染，如果变量缺失会报错
            # 所以我们检查模板是否存在
            if prompt_name in manager._templates:
                print(f"  [OK] {prompt_name}")
            else:
                print(f"  [FAIL] {prompt_name} (未找到)")
        except Exception as e:
            print(f"  [FAIL] {prompt_name} (错误: {e})")
    
    # 检查场景化提示
    scenario_prompts = [
        "scenario_song_recommendation_high_bpm",
        "scenario_song_recommendation_beginner_friendly",
        "scenario_difficulty_advice_beginner",
        "scenario_difficulty_advice_expert",
        "scenario_game_tips_timing",
        "scenario_game_tips_accuracy",
    ]
    
    print("\n场景化提示:")
    for prompt_name in scenario_prompts:
        try:
            if prompt_name in manager._templates:
                print(f"  [OK] {prompt_name}")
            else:
                print(f"  [FAIL] {prompt_name} (未找到)")
        except Exception as e:
            print(f"  [FAIL] {prompt_name} (错误: {e})")


async def main() -> None:
    """运行所有测试。"""
    print("=" * 60)
    print("Phase 7 功能测试 - 意图分类和场景化提示")
    print("=" * 60)
    print("\n这些测试不需要启动服务（FastAPI、Temporal、MongoDB）")
    print("可以快速验证意图检测和场景化提示功能。\n")
    
    # 运行测试
    await test_intent_detection()
    await test_scenario_detection()
    await test_combined_detection()
    await test_parse_input_with_intent()
    test_prompt_templates()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n如果所有测试通过，说明 Phase 7 功能正常工作。")
    print("如果有失败，请检查意图检测模式和提示模板。\n")


if __name__ == "__main__":
    asyncio.run(main())
