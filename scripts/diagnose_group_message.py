"""
诊断群聊消息未回复的问题。

这个脚本可以帮助排查为什么群聊消息没有收到回复。

使用方法:
    python scripts/diagnose_group_message.py --message "Mika, 你好" --group-id "123456789" --user-id "987654321"
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
from src.steps.step1 import parse_input, MIKA_NAME_PATTERN
from src.utils.hashing import hash_user_id
from src.services.content_filter import check_content
from src.services.message_deduplication import get_deduplication_service
from src.config import settings


async def diagnose_group_message(message: str, group_id: str, user_id: str) -> None:
    """
    诊断群聊消息处理流程。
    
    Args:
        message: 用户消息
        group_id: 群组ID
        user_id: 用户ID
    """
    print("=" * 60)
    print("群聊消息诊断工具")
    print("=" * 60)
    print(f"\n消息内容: {message}")
    print(f"群组ID: {group_id}")
    print(f"用户ID: {user_id}")
    print("\n" + "-" * 60)
    
    # 检查 1: Mika 名称检测
    print("\n[检查 1] Mika 名称检测")
    match_result = MIKA_NAME_PATTERN.search(message)
    if match_result:
        print(f"✅ 检测到 'Mika' 提及: {match_result.group()}")
    else:
        print(f"❌ 未检测到 'Mika' 提及")
        print(f"   模式: {MIKA_NAME_PATTERN.pattern}")
        print(f"   提示: 群聊消息必须包含 'Mika', '米卡', 或 'mika酱' 才会触发回复")
        print("\n   这是最常见的原因！群聊消息必须明确提到 'Mika' 才会回复。")
        return
    
    # 检查 2: 内容过滤
    print("\n[检查 2] 内容过滤")
    from src.utils.language import detect_language
    language = detect_language(message, default="zh")
    is_harmful, reason = check_content(message, language=language)
    if is_harmful:
        print(f"❌ 内容被过滤: {reason}")
        return
    else:
        print(f"✅ 内容通过过滤检查")
    
    # 检查 3: 用户ID哈希
    print("\n[检查 3] 用户ID哈希")
    try:
        hashed_user_id = hash_user_id(user_id)
        print(f"✅ 用户ID哈希成功: {hashed_user_id[:16]}...")
    except ValueError as e:
        print(f"❌ 用户ID哈希失败: {e}")
        return
    
    # 检查 4: 消息去重
    print("\n[检查 4] 消息去重")
    deduplication_service = get_deduplication_service()
    if deduplication_service.is_duplicate(hashed_user_id, message):
        print(f"❌ 消息被判定为重复消息")
        print(f"   提示: 如果最近发送过相同或相似的消息，会被跳过")
        return
    else:
        print(f"✅ 消息不是重复消息")
    
    # 检查 5: 群组白名单
    print("\n[检查 5] 群组白名单")
    allowed_groups = settings.get_langbot_allowed_groups_list()
    if allowed_groups:
        if group_id in allowed_groups:
            print(f"✅ 群组在白名单中")
        else:
            print(f"❌ 群组不在白名单中")
            print(f"   允许的群组数量: {len(allowed_groups)}")
            print(f"   提示: 如果配置了群组白名单，只有白名单中的群组才会收到回复")
            return
    else:
        print(f"✅ 未配置群组白名单（允许所有群组）")
    
    # 检查 6: 完整解析流程
    print("\n[检查 6] 完整解析流程")
    parsed_input = await parse_input(
        user_id=user_id,
        group_id=group_id,
        message=message,
        images=None,
    )
    
    if parsed_input is None:
        print(f"❌ 解析失败 - 消息被拒绝")
        print(f"   可能的原因:")
        print(f"   - 未提到 'Mika' (群聊消息必须提到)")
        print(f"   - 内容被过滤")
        print(f"   - 消息是重复的")
        print(f"   - 其他验证失败")
    else:
        print(f"✅ 解析成功")
        print(f"   哈希用户ID: {parsed_input.hashed_user_id[:16]}...")
        print(f"   语言: {parsed_input.language}")
        print(f"   意图: {parsed_input.intent}")
        print(f"   场景: {parsed_input.scenario}")
        print(f"\n✅ 消息应该会被处理并生成回复！")
        print(f"   如果仍然没有回复，请检查:")
        print(f"   - Temporal worker 是否正在运行")
        print(f"   - 查看 Temporal worker 日志是否有错误")
        print(f"   - 查看 FastAPI 日志是否有错误")
    
    print("\n" + "=" * 60)


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="诊断群聊消息未回复的问题")
    parser.add_argument("--message", required=True, help="用户消息内容")
    parser.add_argument("--group-id", required=True, help="群组ID")
    parser.add_argument("--user-id", required=True, help="用户ID")
    
    args = parser.parse_args()
    
    asyncio.run(diagnose_group_message(
        message=args.message,
        group_id=args.group_id,
        user_id=args.user_id,
    ))


if __name__ == "__main__":
    main()
