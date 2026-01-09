#!/usr/bin/env python3
"""
Quick script to check LangBot API configuration.

Usage:
    poetry run python scripts/check_langbot_config.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings


def main() -> None:
    """Check LangBot API configuration."""
    print("=" * 60)
    print("LangBot API Configuration Check")
    print("=" * 60)
    print()
    
    # Check API Key
    api_key = settings.langbot_api_key
    if api_key:
        print(f"✓ LANGBOT_API_KEY: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else 'SET'}")
    else:
        print("✗ LANGBOT_API_KEY: NOT SET")
        print("  → Add to .env file: LANGBOT_API_KEY=lbk_...")
        print()
    
    # Check API Base URL
    api_base_url = settings.langbot_api_base_url
    print(f"{'✓' if api_base_url else '✗'} LANGBOT_API_BASE_URL: {api_base_url}")
    print()
    
    # Summary
    if api_key and api_base_url:
        print("✓ Configuration looks good!")
        print()
        print("Next steps:")
        print("1. Restart FastAPI server if you just added the API key")
        print("2. Send a test message to QQ")
        print("3. Check FastAPI logs for 'langbot_api_send_*' entries")
    else:
        print("✗ Configuration incomplete!")
        print()
        print("Please add to .env file:")
        if not api_key:
            print("  LANGBOT_API_KEY=lbk_nAftIpIZTN_HY2YwvXgcAt3OVJM-dj3FG6SHHgVJTiU")
        if not api_base_url:
            print("  LANGBOT_API_BASE_URL=http://localhost:3000")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
