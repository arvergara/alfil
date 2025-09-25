# ACAFI Clipping Agent

Agente automatizado para la generación y distribución del boletín diario "Monitoreo ACAFI" con noticias del sector financiero chileno.

## Características

- **Scraping Inteligente**: Recolección automática de noticias desde múltiples fuentes
- **Clasificación Automática**: Categorización de noticias en secciones predefinidas usando palabras clave
- **Generación de Resúmenes**: Creación de resúmenes editoriales y por artículo usando LLM
- **Integración con Mailchimp**: Envío automatizado a listas de distribución
- **Deduplicación**: Detección y eliminación de noticias duplicadas
- **Indicadores Económicos**: Integración con Banco Central para indicadores diarios

## Arquitectura

```
clipping_agent/
├── config.py              # Configuración y settings
├── models.py              # Modelos de base de datos
├── scraper.py             # Módulo de scraping de noticias
├── classifier.py          # Clasificador de noticias por sección
├── llm_processor.py       # Procesamiento con LLM para resúmenes
├── mailchimp_integration.py # Integración con Mailchimp
├── main.py                # Orquestador principal
├── requirements.txt       # Dependencias
├── .env.example          # Ejemplo de configuración
└── README.md             # Este archivo
```

## Instalación

### 1. Clonar el repositorio

```bash
cd /Users/alfil/Mi\ unidad/0_Consultorias/Proyecta/clipping_agent
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 5. Configurar base de datos

```bash
# PostgreSQL debe estar instalado y corriendo
createdb clipping_db

# Las tablas se crean automáticamente al ejecutar el script
```

## Configuración

### Variables de Entorno Requeridas

- `OPENAI_API_KEY` o `ANTHROPIC_API_KEY`: Para generación de resúmenes con LLM
- `MAILCHIMP_API_KEY`: Para integración con Mailchimp
- `MAILCHIMP_LIST_ID_ASOCIADOS`: ID de lista de Asociados ACAFI
- `MAILCHIMP_LIST_ID_COLABORADORES`: ID de lista de Colaboradores ACAFI
- `DATABASE_URL`: URL de conexión a PostgreSQL

### Archivo de Palabras Clave

El sistema utiliza el archivo Excel `Palabras_Claves.xlsx` para clasificar noticias. Cada hoja representa un cliente y contiene:
- Sección
- Tema
- Palabras clave (separadas por |)
- Medios clave

## Uso

### Ejecución Manual

```bash
python main.py
```

### Ejecución Programada (Cron)

Agregar al crontab para ejecución diaria a las 7:00 AM:

```bash
0 7 * * 1-5 cd /path/to/clipping_agent && /path/to/venv/bin/python main.py
```

### API (Opcional)

```bash
uvicorn api:app --reload --port 8000
```

Endpoints disponibles:
- `POST /newsletter/generate` - Generar newsletter para fecha específica
- `GET /newsletter/{date}` - Obtener newsletter por fecha
- `POST /newsletter/{id}/send` - Enviar newsletter específico

## Flujo de Procesamiento

1. **Ingesta de Noticias**
   - Scraping de fuentes configuradas
   - Extracción de metadatos (título, fecha, autor, contenido)

2. **Deduplicación**
   - Comparación por URL canónica
   - Similitud de títulos (threshold: 85%)
   - Hash de contenido

3. **Clasificación**
   - Matching con palabras clave del Excel
   - Asignación a secciones:
     - Indicadores Económicos
     - ACAFI (solo si menciona ACAFI)
     - Temas Industria
     - Noticias de Interés
     - Noticias de Socios (solo nuevos fondos)

4. **Generación de Resúmenes**
   - Resumen editorial (máx. 6 líneas)
   - Resúmenes por artículo (1-2 líneas)

5. **Composición del Newsletter**
   - Template HTML con estilo Helvetica 12pt
   - Versión texto plano
   - Indicadores económicos del día

6. **Distribución**
   - Creación de campaña en Mailchimp
   - Envío de prueba a emails configurados
   - Envío a listas de Asociados y Colaboradores

## Monitoreo y Logs

Los logs se guardan en `logs/clipping_YYYY-MM-DD.log` con rotación diaria.

Niveles de log:
- `INFO`: Operaciones normales
- `WARNING`: Situaciones anómalas no críticas
- `ERROR`: Errores que requieren atención

## Troubleshooting

### Error de API de Mailchimp
- Verificar API key y server prefix
- Confirmar IDs de listas
- Revisar límites de rate limiting

### Sin noticias encontradas
- Verificar conectividad a fuentes
- Revisar selectores CSS en configuración de scraping
- Confirmar rango de fechas

### Resúmenes de baja calidad
- Ajustar temperatura del LLM (default: 0.3)
- Revisar prompts en `llm_processor.py`
- Aumentar max_tokens si es necesario

## Mantenimiento

### Actualizar fuentes de noticias

Editar en `config.py`:

```python
NEWS_SOURCES = [
    {"name": "Nueva Fuente", "url": "https://example.com", "type": "web"},
    # ...
]
```

### Actualizar palabras clave

Modificar el archivo Excel `Palabras_Claves.xlsx` manteniendo el formato:
- Columna 1: Sección
- Columna 2: Tema
- Columna 3: Palabras clave (separadas por |)
- Columna 4: Medios clave

### Backup de base de datos

```bash
pg_dump clipping_db > backup_$(date +%Y%m%d).sql
```

## Seguridad

- **Nunca** commitar el archivo `.env` con credenciales reales
- Rotar API keys periódicamente
- Usar conexiones SSL para base de datos en producción
- Implementar rate limiting para APIs externas

## Roadmap

- [ ] Dashboard web para monitoreo
- [ ] Análisis de sentimiento de noticias
- [ ] Detección automática de tendencias
- [ ] Integración con más fuentes de noticias
- [ ] API REST completa
- [ ] Métricas de engagement (clicks, aperturas)
- [ ] Generación de reportes semanales/mensuales

## Soporte

Para soporte y consultas, contactar a:
- Email: btagle@proyectacomunicaciones.cl
- ACAFI: acafi@acafi.com

## Licencia

Propiedad de Proyecta Comunicaciones / ACAFI. Todos los derechos reservados.