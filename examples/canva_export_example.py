"""
Example script demonstrating how to use the Canva to PDF converter.

This script shows various ways to export Canva designs to PDF format.
"""

import sys
from pathlib import Path

# Add parent directory to path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from canva_to_pdf import (
    CanvaToPDFConverter,
    convert_canva_to_pdf,
    ExportQuality,
    CanvaExportResult
)
from config import settings
from loguru import logger


def example_1_simple_export():
    """
    Example 1: Simple export using the convenience function.
    """
    print("\n" + "="*60)
    print("Example 1: Simple Export")
    print("="*60)

    # Get API key from settings
    api_key = settings.CANVA_API_KEY
    if not api_key:
        print("⚠️  CANVA_API_KEY not set in environment variables")
        print("   Set it using: export CANVA_API_KEY='your-api-key'")
        return

    # Example Canva URL
    canva_url = "https://www.canva.com/design/DAFxxxxx/view"

    print(f"\nExporting design from URL: {canva_url}")
    print(f"Output directory: {settings.CANVA_EXPORT_DIR}")

    result = convert_canva_to_pdf(
        design_id_or_url=canva_url,
        api_key=api_key.get_secret_value(),
        output_dir=str(settings.CANVA_EXPORT_DIR),
        filename="newsletter_template"
    )

    if result.success:
        print(f"✓ Success! PDF saved to: {result.file_path}")
        print(f"  File size: {result.file_path.stat().st_size / 1024:.2f} KB")
    else:
        print(f"✗ Error: {result.error}")


def example_2_advanced_export():
    """
    Example 2: Advanced export with custom settings using the class.
    """
    print("\n" + "="*60)
    print("Example 2: Advanced Export with Custom Settings")
    print("="*60)

    api_key = settings.CANVA_API_KEY
    if not api_key:
        print("⚠️  CANVA_API_KEY not set")
        return

    # Initialize converter with custom settings
    converter = CanvaToPDFConverter(
        api_key=api_key.get_secret_value(),
        output_dir=settings.CANVA_EXPORT_DIR,
        timeout=600,  # 10 minutes
        max_retries=5
    )

    # Example design ID (not URL)
    design_id = "DAFxxxxx"

    print(f"\nExporting design ID: {design_id}")
    print(f"Quality: HIGH")
    print(f"Exporting specific pages: [1, 2, 3]")

    # Export with custom quality and specific pages
    result = converter.export_design_to_pdf(
        design_id=design_id,
        filename="custom_export",
        quality=ExportQuality.HIGH,
        pages=[1, 2, 3]  # Only export pages 1, 2, and 3
    )

    if result.success:
        print(f"\n✓ Export completed successfully!")
        print(f"  File: {result.file_path}")
        print(f"  Export ID: {result.export_id}")
        print(f"  Metadata: {result.metadata}")
    else:
        print(f"\n✗ Export failed: {result.error}")


def example_3_get_design_info():
    """
    Example 3: Get design information before exporting.
    """
    print("\n" + "="*60)
    print("Example 3: Get Design Information")
    print("="*60)

    api_key = settings.CANVA_API_KEY
    if not api_key:
        print("⚠️  CANVA_API_KEY not set")
        return

    converter = CanvaToPDFConverter(
        api_key=api_key.get_secret_value(),
        output_dir=settings.CANVA_EXPORT_DIR
    )

    design_id = "DAFxxxxx"

    print(f"\nFetching information for design: {design_id}")

    # Get design info
    design_info = converter.get_design_info(design_id)

    if design_info:
        print("\nDesign Information:")
        print(f"  Title: {design_info.get('title', 'N/A')}")
        print(f"  Created: {design_info.get('created_at', 'N/A')}")
        print(f"  Modified: {design_info.get('updated_at', 'N/A')}")
        print(f"  Pages: {design_info.get('page_count', 'N/A')}")
        print(f"  Status: {design_info.get('status', 'N/A')}")

        # Now export it
        print("\nExporting design...")
        result = converter.export_design_to_pdf(design_id)

        if result.success:
            print(f"✓ Exported to: {result.file_path}")
        else:
            print(f"✗ Export failed: {result.error}")
    else:
        print("✗ Could not retrieve design information")


def example_4_batch_export():
    """
    Example 4: Batch export multiple designs.
    """
    print("\n" + "="*60)
    print("Example 4: Batch Export Multiple Designs")
    print("="*60)

    api_key = settings.CANVA_API_KEY
    if not api_key:
        print("⚠️  CANVA_API_KEY not set")
        return

    converter = CanvaToPDFConverter(
        api_key=api_key.get_secret_value(),
        output_dir=settings.CANVA_EXPORT_DIR
    )

    # List of designs to export
    designs = [
        {"id": "DAFxxxxx1", "name": "newsletter_january"},
        {"id": "DAFxxxxx2", "name": "newsletter_february"},
        {"id": "DAFxxxxx3", "name": "newsletter_march"},
    ]

    print(f"\nExporting {len(designs)} designs...")

    results = []
    for i, design in enumerate(designs, 1):
        print(f"\n[{i}/{len(designs)}] Exporting: {design['name']}")

        result = converter.export_design_to_pdf(
            design_id=design['id'],
            filename=design['name'],
            quality=ExportQuality.MEDIUM  # Use medium quality for batch
        )

        results.append({
            'name': design['name'],
            'success': result.success,
            'file_path': result.file_path if result.success else None,
            'error': result.error if not result.success else None
        })

        if result.success:
            print(f"  ✓ Success: {result.file_path}")
        else:
            print(f"  ✗ Failed: {result.error}")

    # Summary
    print("\n" + "="*60)
    print("Batch Export Summary")
    print("="*60)
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful

    print(f"\nTotal: {len(results)} designs")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")

    if failed > 0:
        print("\nFailed exports:")
        for result in results:
            if not result['success']:
                print(f"  - {result['name']}: {result['error']}")


def example_5_list_exports():
    """
    Example 5: List previous export jobs.
    """
    print("\n" + "="*60)
    print("Example 5: List Export Jobs")
    print("="*60)

    api_key = settings.CANVA_API_KEY
    if not api_key:
        print("⚠️  CANVA_API_KEY not set")
        return

    converter = CanvaToPDFConverter(
        api_key=api_key.get_secret_value(),
        output_dir=settings.CANVA_EXPORT_DIR
    )

    print("\nFetching export history...")

    # List all exports
    exports = converter.list_exports()

    if exports:
        print(f"\nFound {len(exports)} export jobs:\n")
        for i, export in enumerate(exports[:10], 1):  # Show first 10
            print(f"{i}. Export ID: {export.get('id')}")
            print(f"   Design: {export.get('design_id')}")
            print(f"   Status: {export.get('status')}")
            print(f"   Created: {export.get('created_at')}")
            print(f"   Format: {export.get('format')}")
            print()
    else:
        print("No export jobs found")


def main():
    """
    Main function to run examples.
    """
    print("\n" + "="*60)
    print("Canva to PDF Converter - Examples")
    print("="*60)

    # Check if API key is configured
    if not settings.CANVA_API_KEY:
        print("\n⚠️  WARNING: CANVA_API_KEY is not configured!")
        print("\nTo use this module, you need to:")
        print("1. Get a Canva API key from: https://www.canva.com/developers/")
        print("2. Set the environment variable: export CANVA_API_KEY='your-api-key'")
        print("3. Or add it to your .env file: CANVA_API_KEY=your-api-key")
        print("\n" + "="*60)
        return

    # Menu
    print("\nSelect an example to run:")
    print("1. Simple export using convenience function")
    print("2. Advanced export with custom settings")
    print("3. Get design information before exporting")
    print("4. Batch export multiple designs")
    print("5. List previous export jobs")
    print("0. Run all examples")

    try:
        choice = input("\nEnter your choice (0-5): ").strip()

        if choice == "1":
            example_1_simple_export()
        elif choice == "2":
            example_2_advanced_export()
        elif choice == "3":
            example_3_get_design_info()
        elif choice == "4":
            example_4_batch_export()
        elif choice == "5":
            example_5_list_exports()
        elif choice == "0":
            example_1_simple_export()
            example_2_advanced_export()
            example_3_get_design_info()
            example_4_batch_export()
            example_5_list_exports()
        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nExecution cancelled by user")
    except Exception as e:
        logger.exception("Error running examples")
        print(f"\n✗ Error: {e}")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
