#!/usr/bin/env python3
"""
Manual testing script for LangBot webhook endpoint.

This script allows manual testing of the webhook endpoint with
command-line arguments for message, group_id, user_id, and optional image.

Per T102: Create scripts/test_webhook.py for manual testing

Usage:
    python scripts/test_webhook.py --message "Mika, hello!" --group-id "123456" --user-id "789012"
    python scripts/test_webhook.py --message "Mika, hello!" --user-id "789012"  # Private message
    python scripts/test_webhook.py --message "Mika, analyze this" --user-id "789012" --image path/to/image.jpg
"""

import argparse
import asyncio
import base64
import sys
from pathlib import Path

import httpx


async def test_webhook(
    message: str,
    user_id: str,
    group_id: str = "",
    image_path: str = None,
    webhook_url: str = "http://localhost:8000/webhook/langbot",
) -> None:
    """
    Test webhook endpoint with given parameters.

    Args:
        message: User message content.
        user_id: QQ user ID.
        group_id: QQ group ID (empty for private messages).
        image_path: Optional path to image file.
        webhook_url: Webhook endpoint URL.
    """
    # Prepare request body
    body = {
        "user_id": user_id,
        "group_id": group_id,
        "message": message,
    }
    
    # Add image if provided
    if image_path:
        image_file = Path(image_path)
        if not image_file.exists():
            print(f"Error: Image file not found: {image_path}")
            sys.exit(1)
        
        # Read and encode image
        with open(image_file, "rb") as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            body["images"] = [image_base64]
    
    # Send request
    print(f"Testing webhook: {webhook_url}")
    print(f"Message: {message}")
    print(f"User ID: {user_id}")
    print(f"Group ID: {group_id if group_id else '(private message)'}")
    if image_path:
        print(f"Image: {image_path}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=body)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "ok":
                    print(f"\n✓ Success!")
                    print(f"Bot Response: {result.get('response', 'N/A')}")
                else:
                    print(f"\n✗ Request failed: {result.get('message', 'Unknown error')}")
            else:
                print(f"\n✗ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                
    except httpx.TimeoutException:
        print("\n✗ Request timeout (> 30s)")
        sys.exit(1)
    except httpx.ConnectError:
        print(f"\n✗ Connection error: Could not connect to {webhook_url}")
        print("Make sure the FastAPI server is running.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test LangBot webhook endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Group message
  python scripts/test_webhook.py --message "Mika, hello!" --group-id "123456" --user-id "789012"
  
  # Private message
  python scripts/test_webhook.py --message "Mika, hello!" --user-id "789012"
  
  # With image
  python scripts/test_webhook.py --message "Mika, analyze this" --user-id "789012" --image image.jpg
  
  # Custom webhook URL
  python scripts/test_webhook.py --message "Mika, hello!" --user-id "789012" --url "https://api.example.com/webhook/langbot"
        """,
    )
    
    parser.add_argument(
        "--message",
        type=str,
        required=True,
        help="User message content",
    )
    
    parser.add_argument(
        "--user-id",
        type=str,
        required=True,
        help="QQ user ID",
    )
    
    parser.add_argument(
        "--group-id",
        type=str,
        default="",
        help="QQ group ID (empty for private messages)",
    )
    
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to image file (JPEG, PNG, or WebP)",
    )
    
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000/webhook/langbot",
        help="Webhook endpoint URL (default: http://localhost:8000/webhook/langbot)",
    )
    
    args = parser.parse_args()
    
    # Validate message
    if not args.message.strip():
        print("Error: Message cannot be empty")
        sys.exit(1)
    
    # Run test
    asyncio.run(
        test_webhook(
            message=args.message,
            user_id=args.user_id,
            group_id=args.group_id,
            image_path=args.image,
            webhook_url=args.url,
        )
    )


if __name__ == "__main__":
    main()
