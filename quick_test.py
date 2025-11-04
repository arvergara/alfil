#!/usr/bin/env python3
"""
Quick test script for the Canva link provided
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from canva_to_pdf import convert_canva_to_pdf

# The Canva URL to test
CANVA_URL = "https://www.canva.com/design/DAFnUmgypOI/2hS4yz0Ba7OCsmoYhgs9Xw/view?utm_content=DAFnUmgypOI&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=hdd8afcacfc#15"


def main():
    print("\n" + "="*60)
    print("QUICK TEST - Canva to PDF")
    print("="*60)

    # Check if API key is provided as argument
    if len(sys.argv) < 2:
        print("\n⚠️  API Key required!")
        print("\nUsage:")
        print("  python quick_test.py YOUR_CANVA_API_KEY")
        print("\nOr set it in .env file:")
        print("  echo 'CANVA_API_KEY=your_key' > .env")
        print("  python quick_test.py")
        print("\n")

        # Try to load from config
        try:
            from config import settings
            if settings.CANVA_API_KEY:
                api_key = settings.CANVA_API_KEY.get_secret_value()
                print("✓ Using API key from .env file")
            else:
                print("✗ No API key found in .env")
                sys.exit(1)
        except:
            sys.exit(1)
    else:
        api_key = sys.argv[1]
        print("✓ Using API key from command line argument")

    print(f"\nCanva URL: {CANVA_URL}")
    print(f"Design ID: DAFnUmgypOI")
    print(f"\nStarting export...\n")

    # Perform the conversion
    result = convert_canva_to_pdf(
        design_id_or_url=CANVA_URL,
        api_key=api_key,
        filename="canva_export_DAFnUmgypOI",
        quality="high"
    )

    print("\n" + "="*60)
    if result.success:
        print("✅ SUCCESS! PDF exported successfully!")
        print("="*60)
        print(f"\n📄 File: {result.file_path}")
        print(f"📊 Size: {result.file_path.stat().st_size / 1024:.2f} KB")
        print(f"🆔 Export ID: {result.export_id}")
        if result.metadata:
            print(f"ℹ️  Metadata: {result.metadata}")
        print(f"\n✓ You can now open the PDF at: {result.file_path.absolute()}")
    else:
        print("❌ EXPORT FAILED")
        print("="*60)
        print(f"\n✗ Error: {result.error}")
        print("\n💡 Troubleshooting tips:")
        print("  1. Verify your API key is correct")
        print("  2. Check if the design is accessible (not private)")
        print("  3. Ensure you have the correct permissions/scopes")
        print("  4. Visit: https://www.canva.com/developers/docs")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
