# Canva to PDF Integration

Este módulo proporciona funcionalidad para exportar diseños de Canva a formato PDF utilizando la API de Canva.

## Características

- Exportación de diseños de Canva a PDF
- Soporte para URLs de Canva o IDs de diseño directo
- Configuración de calidad de exportación (baja, media, alta)
- Exportación de páginas específicas
- Exportación por lotes de múltiples diseños
- Reintentos automáticos con backoff exponencial
- Manejo de rate limiting de la API
- Logging detallado con loguru
- Seguimiento de trabajos de exportación

## Requisitos

### Obtener una API Key de Canva

1. Ve a [Canva Developers](https://www.canva.com/developers/)
2. Crea una cuenta de desarrollador o inicia sesión
3. Crea una nueva aplicación
4. Copia tu API key o access token
5. Configura los scopes necesarios:
   - `design:content:read` - Para leer contenido de diseños
   - `design:meta:read` - Para leer metadatos
   - `asset:read` - Para leer assets
   - `design:permission:read` - Para verificar permisos

### Configuración

Agrega tu API key al archivo `.env`:

```bash
CANVA_API_KEY=your_canva_api_key_here
```

O expórtala como variable de entorno:

```bash
export CANVA_API_KEY="your_canva_api_key_here"
```

### Configuración Adicional (Opcional)

En el archivo `.env` puedes configurar:

```bash
# Directorio para exportaciones (por defecto: ./exports)
CANVA_EXPORT_DIR=/ruta/a/tus/exportaciones

# Timeout para operaciones de exportación en segundos (por defecto: 300)
CANVA_EXPORT_TIMEOUT=600

# Calidad de exportación por defecto: low, medium, high (por defecto: high)
CANVA_EXPORT_QUALITY=high
```

## Instalación

Las dependencias necesarias ya están incluidas en `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Uso

### 1. Uso Básico - Función de Conveniencia

La forma más simple de convertir un diseño de Canva a PDF:

```python
from canva_to_pdf import convert_canva_to_pdf

# Usando una URL de Canva
result = convert_canva_to_pdf(
    design_id_or_url="https://www.canva.com/design/DAFxxxxx/view",
    api_key="your_api_key",
    filename="mi_diseño"
)

if result.success:
    print(f"PDF guardado en: {result.file_path}")
else:
    print(f"Error: {result.error}")
```

### 2. Uso Avanzado - Clase CanvaToPDFConverter

Para más control y opciones avanzadas:

```python
from canva_to_pdf import CanvaToPDFConverter, ExportQuality
from pathlib import Path

# Inicializar el conversor
converter = CanvaToPDFConverter(
    api_key="your_api_key",
    output_dir=Path("./exports"),
    timeout=600,  # 10 minutos
    max_retries=5
)

# Exportar con opciones personalizadas
result = converter.export_design_to_pdf(
    design_id="DAFxxxxx",
    filename="newsletter_enero",
    quality=ExportQuality.HIGH,
    pages=[1, 2, 3]  # Solo exportar páginas 1, 2 y 3
)
```

### 3. Exportar desde URL

```python
from canva_to_pdf import CanvaToPDFConverter

converter = CanvaToPDFConverter(api_key="your_api_key")

# La clase automáticamente extrae el design ID de la URL
result = converter.export_from_url(
    canva_url="https://www.canva.com/design/DAFxxxxx/edit",
    filename="mi_diseño"
)
```

### 4. Obtener Información del Diseño

```python
# Obtener metadata antes de exportar
design_info = converter.get_design_info("DAFxxxxx")

print(f"Título: {design_info.get('title')}")
print(f"Páginas: {design_info.get('page_count')}")
print(f"Creado: {design_info.get('created_at')}")
```

### 5. Exportación por Lotes

```python
designs = [
    {"id": "DAFxxxxx1", "name": "diseño_1"},
    {"id": "DAFxxxxx2", "name": "diseño_2"},
    {"id": "DAFxxxxx3", "name": "diseño_3"},
]

for design in designs:
    result = converter.export_design_to_pdf(
        design_id=design['id'],
        filename=design['name'],
        quality=ExportQuality.MEDIUM
    )
    print(f"{design['name']}: {'✓' if result.success else '✗'}")
```

### 6. Listar Trabajos de Exportación

```python
# Listar todas las exportaciones
exports = converter.list_exports()

for export in exports:
    print(f"ID: {export['id']}")
    print(f"Estado: {export['status']}")
    print(f"Diseño: {export['design_id']}")

# Listar exportaciones de un diseño específico
exports = converter.list_exports(design_id="DAFxxxxx")
```

## Línea de Comandos

También puedes usar el módulo directamente desde la línea de comandos:

```bash
# Usando URL
python canva_to_pdf.py "https://www.canva.com/design/DAFxxxxx/view" "your_api_key"

# Usando design ID
python canva_to_pdf.py "DAFxxxxx" "your_api_key"

# Con directorio de salida y nombre personalizado
python canva_to_pdf.py "DAFxxxxx" "your_api_key" "./mis_pdfs" "mi_diseño"
```

## Ejemplos

Ejecuta el script de ejemplos para ver todas las funcionalidades:

```bash
python examples/canva_export_example.py
```

Los ejemplos incluyen:
1. Exportación simple con función de conveniencia
2. Exportación avanzada con configuración personalizada
3. Obtener información del diseño antes de exportar
4. Exportación por lotes de múltiples diseños
5. Listar trabajos de exportación previos

## Integración con el Sistema de Newsletters

### Ejemplo: Exportar Newsletter a PDF

```python
from canva_to_pdf import CanvaToPDFConverter
from config import settings

# Inicializar usando configuración del proyecto
converter = CanvaToPDFConverter(
    api_key=settings.CANVA_API_KEY.get_secret_value(),
    output_dir=settings.CANVA_EXPORT_DIR,
    timeout=settings.CANVA_EXPORT_TIMEOUT
)

# Exportar el template de newsletter
newsletter_result = converter.export_design_to_pdf(
    design_id="your_newsletter_template_id",
    filename=f"newsletter_{datetime.now().strftime('%Y%m%d')}",
    quality=ExportQuality[settings.CANVA_EXPORT_QUALITY.upper()]
)

if newsletter_result.success:
    # El PDF está listo para adjuntar al email o almacenar
    pdf_path = newsletter_result.file_path
```

## Estructura de Respuesta

La clase `CanvaExportResult` contiene:

```python
@dataclass
class CanvaExportResult:
    success: bool                    # True si la exportación fue exitosa
    file_path: Optional[Path]        # Ruta al archivo PDF exportado
    url: Optional[str]               # URL de descarga de Canva
    error: Optional[str]             # Mensaje de error si falló
    export_id: Optional[str]         # ID del trabajo de exportación
    metadata: Optional[Dict]         # Metadata adicional (quality, pages, etc.)
```

## Calidades de Exportación

```python
from canva_to_pdf import ExportQuality

# Opciones disponibles:
ExportQuality.LOW      # Archivo más pequeño, menor calidad
ExportQuality.MEDIUM   # Balance entre tamaño y calidad
ExportQuality.HIGH     # Máxima calidad, archivo más grande
```

## Manejo de Errores

```python
from canva_to_pdf import CanvaToPDFConverter, CanvaAPIError

try:
    converter = CanvaToPDFConverter(api_key="your_key")
    result = converter.export_design_to_pdf("DAFxxxxx")

    if result.success:
        print(f"Éxito: {result.file_path}")
    else:
        print(f"Falló: {result.error}")

except CanvaAPIError as e:
    print(f"Error de API: {e}")
except Exception as e:
    print(f"Error inesperado: {e}")
```

## Logging

El módulo utiliza `loguru` para logging detallado:

```python
from loguru import logger

# Los logs incluyen:
# - INFO: Operaciones exitosas y progreso
# - DEBUG: Detalles de requests y responses
# - WARNING: Reintentos y rate limiting
# - ERROR: Fallos y excepciones
```

## Limitaciones y Consideraciones

1. **Rate Limiting**: La API de Canva tiene límites de tasa. El módulo maneja esto automáticamente con reintentos.

2. **Timeout**: Las exportaciones grandes pueden tardar. Ajusta `timeout` según sea necesario.

3. **Permisos**: Necesitas los permisos apropiados en Canva para los diseños que quieres exportar.

4. **Formato de URL**: Las URLs de Canva deben tener el formato:
   - `https://www.canva.com/design/{DESIGN_ID}/view`
   - `https://www.canva.com/design/{DESIGN_ID}/edit`

5. **Tamaño de Archivo**: PDFs de alta calidad pueden ser grandes. Considera usar `ExportQuality.MEDIUM` para exportaciones por lotes.

## Solución de Problemas

### Error: "No export ID received from API"
- Verifica que tu API key tiene los permisos correctos
- Asegúrate de que el design ID es válido

### Error: "Export timeout"
- Aumenta el valor de `timeout` en el constructor
- Verifica la conexión a internet
- Intenta con `ExportQuality.MEDIUM` o `LOW`

### Error: "Rate limited"
- El módulo maneja esto automáticamente
- Si persiste, reduce la frecuencia de requests

### Error: "Invalid Canva URL format"
- Verifica que la URL tiene el formato correcto
- O usa el design ID directamente en lugar de la URL

## API de Canva

Para más información sobre la API de Canva:
- [Documentación oficial](https://www.canva.com/developers/docs)
- [API Reference](https://www.canva.com/developers/docs/api)
- [Guía de autenticación](https://www.canva.com/developers/docs/authentication)

## Soporte

Para problemas o preguntas:
1. Revisa la documentación de Canva
2. Verifica los logs en `./logs/`
3. Asegúrate de tener la última versión del código
4. Contacta al equipo de desarrollo

## Licencia

Este módulo es parte del proyecto ACAFI Clipping Agent.
