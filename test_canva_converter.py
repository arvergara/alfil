#!/usr/bin/env python3
"""
Test script for Canva to PDF converter
This script tests the basic functionality without requiring a full API key.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from canva_to_pdf import CanvaToPDFConverter, convert_canva_to_pdf


def test_url_parsing():
    """Test that we can correctly extract design IDs from URLs"""
    print("\n" + "="*60)
    print("TEST 1: URL Parsing")
    print("="*60)

    test_url = "https://www.canva.com/design/DAFnUmgypOI/2hS4yz0Ba7OCsmoYhgs9Xw/view?utm_content=DAFnUmgypOI&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=hdd8afcacfc#15"

    print(f"\nTest URL: {test_url}")

    # Create a dummy converter just to test URL parsing
    converter = CanvaToPDFConverter(api_key="dummy_key")

    try:
        design_id = converter._extract_design_id(test_url)
        print(f"✓ Successfully extracted design ID: {design_id}")
        print(f"✓ URL parsing works correctly!")
        return True
    except Exception as e:
        print(f"✗ Failed to extract design ID: {e}")
        return False


def test_module_structure():
    """Test that the module is properly structured"""
    print("\n" + "="*60)
    print("TEST 2: Module Structure")
    print("="*60)

    checks = [
        ("CanvaToPDFConverter class", "CanvaToPDFConverter"),
        ("convert_canva_to_pdf function", "convert_canva_to_pdf"),
        ("ExportQuality enum", "ExportQuality"),
        ("ExportFormat enum", "ExportFormat"),
        ("CanvaExportResult dataclass", "CanvaExportResult"),
        ("CanvaAPIError exception", "CanvaAPIError"),
    ]

    import canva_to_pdf

    all_passed = True
    for check_name, attr_name in checks:
        if hasattr(canva_to_pdf, attr_name):
            print(f"✓ {check_name} exists")
        else:
            print(f"✗ {check_name} missing")
            all_passed = False

    return all_passed


def test_configuration():
    """Test that configuration is properly set up"""
    print("\n" + "="*60)
    print("TEST 3: Configuration")
    print("="*60)

    try:
        from config import settings

        print(f"✓ Config module loaded successfully")
        print(f"  - CANVA_EXPORT_DIR: {settings.CANVA_EXPORT_DIR}")
        print(f"  - CANVA_EXPORT_TIMEOUT: {settings.CANVA_EXPORT_TIMEOUT}")
        print(f"  - CANVA_EXPORT_QUALITY: {settings.CANVA_EXPORT_QUALITY}")

        # Check if API key is configured
        if settings.CANVA_API_KEY:
            print(f"✓ CANVA_API_KEY is configured")
            return True
        else:
            print(f"⚠️  CANVA_API_KEY is NOT configured")
            print(f"\nTo use the Canva to PDF converter, you need to:")
            print(f"1. Get a Canva API key from: https://www.canva.com/developers/")
            print(f"2. Create a .env file in the project root")
            print(f"3. Add this line: CANVA_API_KEY=your_api_key_here")
            return False

    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False


def test_export_dir_creation():
    """Test that export directory is created"""
    print("\n" + "="*60)
    print("TEST 4: Export Directory")
    print("="*60)

    try:
        from config import settings

        if settings.CANVA_EXPORT_DIR.exists():
            print(f"✓ Export directory exists: {settings.CANVA_EXPORT_DIR}")
            return True
        else:
            print(f"✗ Export directory does not exist: {settings.CANVA_EXPORT_DIR}")
            return False

    except Exception as e:
        print(f"✗ Error checking export directory: {e}")
        return False


def show_api_setup_instructions():
    """Show instructions for getting a Canva API key"""
    print("\n" + "="*60)
    print("CÓMO OBTENER TU API KEY DE CANVA")
    print("="*60)

    print("""
Para usar este módulo necesitas una API key de Canva. Sigue estos pasos:

📝 PASO 1: Crear una cuenta de desarrollador
   └─ Ve a: https://www.canva.com/developers/
   └─ Haz clic en "Get started" o "Sign up"
   └─ Inicia sesión con tu cuenta de Canva

📝 PASO 2: Crear una nueva aplicación
   └─ En el dashboard, haz clic en "Create an app"
   └─ Elige el tipo de aplicación (selecciona "Server-side")
   └─ Dale un nombre a tu aplicación

📝 PASO 3: Configurar permisos (scopes)
   └─ En la configuración de tu app, habilita estos scopes:
      • design:content:read - Para leer contenido de diseños
      • design:meta:read - Para leer metadatos
      • asset:read - Para leer assets
      • design:permission:read - Para verificar permisos

📝 PASO 4: Obtener tu API key
   └─ En la sección "API Keys" o "Credentials"
   └─ Copia tu "Client ID" o "API Key"
   └─ También puede que necesites un "Access Token"

📝 PASO 5: Configurar en este proyecto
   └─ Crea un archivo .env en la raíz del proyecto:

      $ echo 'CANVA_API_KEY=tu_api_key_aqui' > .env

   └─ O exporta la variable de entorno:

      $ export CANVA_API_KEY="tu_api_key_aqui"

⚠️  IMPORTANTE:
   • No compartas tu API key públicamente
   • No la subas a repositorios de código
   • El archivo .env ya está en .gitignore

💡 NOTA SOBRE CANVA CONNECT:
   Si usas Canva Connect (OAuth), necesitarás:
   1. Client ID
   2. Client Secret
   3. Redirect URI configurado
   4. Generar un Access Token mediante OAuth flow

   Para este script, el método más simple es usar la API key directa.

📚 Documentación de Canva:
   • API Docs: https://www.canva.com/developers/docs
   • Authentication: https://www.canva.com/developers/docs/authentication
   • API Reference: https://www.canva.com/developers/docs/api
""")


def test_with_real_url():
    """Try to test with the real URL if API key is available"""
    print("\n" + "="*60)
    print("TEST 5: Real Export Test")
    print("="*60)

    try:
        from config import settings

        if not settings.CANVA_API_KEY:
            print("⚠️  Cannot test real export - CANVA_API_KEY not configured")
            print("   Configure your API key first (see instructions above)")
            return False

        test_url = "https://www.canva.com/design/DAFnUmgypOI/2hS4yz0Ba7OCsmoYhgs9Xw/view?utm_content=DAFnUmgypOI&utm_campaign=designshare&utm_medium=link2&utm_source=uniquelinks&utlId=hdd8afcacfc#15"

        print(f"\nAttempting to export from: {test_url}")
        print(f"Design ID: DAFnUmgypOI")
        print(f"Output directory: {settings.CANVA_EXPORT_DIR}")
        print("\nThis may take a few moments...\n")

        result = convert_canva_to_pdf(
            design_id_or_url=test_url,
            api_key=settings.CANVA_API_KEY.get_secret_value(),
            output_dir=str(settings.CANVA_EXPORT_DIR),
            filename="test_export"
        )

        if result.success:
            print(f"\n✓ SUCCESS! PDF exported successfully!")
            print(f"  File: {result.file_path}")
            print(f"  Size: {result.file_path.stat().st_size / 1024:.2f} KB")
            print(f"  Export ID: {result.export_id}")
            return True
        else:
            print(f"\n✗ Export failed: {result.error}")
            print("\nPossible reasons:")
            print("  • Invalid API key")
            print("  • Insufficient permissions")
            print("  • Design is private or not accessible")
            print("  • API endpoint changed")
            return False

    except Exception as e:
        print(f"\n✗ Error during export: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CANVA TO PDF CONVERTER - TEST SUITE")
    print("="*60)

    results = []

    # Run all tests
    results.append(("URL Parsing", test_url_parsing()))
    results.append(("Module Structure", test_module_structure()))
    results.append(("Configuration", test_configuration()))
    results.append(("Export Directory", test_export_dir_creation()))

    # Show API setup instructions
    show_api_setup_instructions()

    # Try real export if API key is available
    results.append(("Real Export", test_with_real_url()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! The module is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Review the output above.")

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
