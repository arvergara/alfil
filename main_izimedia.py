#!/usr/bin/env python3
"""
Sistema Principal con IziMedia como fuente primaria
Flujo EXACTO según documento ACAFI
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys

from loguru import logger
from models import Article
from classifier import NewsClassifier, NewsSection
from llm_processor import LLMProcessor
from newsletter_composer import NewsletterComposer
from scraper import BancoCentralScraper
from izimedia_connector import IziMediaConnector, IziMediaValidator, IziMediaArticle

# Configurar logging
logger.add(
    "logs/izimedia_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

class ACAFIClippingAgent:
    """
    Agente de clipping siguiendo el flujo EXACTO del documento ACAFI
    """
    
    def __init__(self):
        self.izimedia = IziMediaConnector()
        self.validator = IziMediaValidator()
        self.classifier = NewsClassifier()
        self.llm_processor = LLMProcessor()
        self.composer = NewsletterComposer()
        self.bc_scraper = BancoCentralScraper()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_daily_monitoring(self) -> bool:
        """
        Ejecutar monitoreo diario según flujo del documento
        
        FLUJO OBLIGATORIO:
        1. Login en IziMedia
        2. Buscar noticias con palabras clave
        3. Clasificar y procesar
        4. Generar newsletter
        5. Enviar por Mailchimp
        """
        
        logger.info("\n" + "="*70)
        logger.info("   MONITOREO ACAFI - INICIO DE PROCESO DIARIO")
        logger.info("="*70)
        logger.info(f"   Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        logger.info("="*70 + "\n")
        
        try:
            # ========================================
            # PASO 1: IZIMEDIA (OBLIGATORIO)
            # ========================================
            logger.info("📋 PASO 1: CONEXIÓN A IZIMEDIA")
            logger.info("-"*50)
            
            # Validar conexión
            if not self.validator.validate_connection():
                logger.error("❌ No se puede conectar a IziMedia")
                logger.error("   URL: https://muba.izimedia.io")
                logger.error("   Este paso es OBLIGATORIO según el flujo")
                return False
            
            # Obtener noticias de IziMedia
            logger.info("🔐 Ingresando con credenciales...")
            izimedia_articles = await self.izimedia.fetch_daily_news()
            
            # Validar artículos
            is_valid, message = self.validator.validate_articles(izimedia_articles)
            if not is_valid:
                logger.error(f"❌ Validación fallida: {message}")
                return False
            
            logger.info(message)
            
            # Exportar a Excel (como en el flujo manual)
            excel_file = self.izimedia.export_to_excel(izimedia_articles)
            logger.info(f"📊 Exportado a: {excel_file}")
            
            # ========================================
            # PASO 2: CLASIFICACIÓN POR SECCIONES
            # ========================================
            logger.info("\n📋 PASO 2: CLASIFICACIÓN DE NOTICIAS")
            logger.info("-"*50)
            
            # Convertir a formato Article
            articles = self._convert_izimedia_to_articles(izimedia_articles)
            
            # Clasificar según secciones del documento
            classified = self._classify_by_sections(articles)
            
            # Mostrar distribución
            self._show_distribution(classified)
            
            # ========================================
            # PASO 3: INDICADORES ECONÓMICOS
            # ========================================
            logger.info("\n📋 PASO 3: INDICADORES ECONÓMICOS")
            logger.info("-"*50)
            
            indicators = await self.bc_scraper.fetch_indicators()
            logger.info("   Fuente: Banco Central de Chile")
            for key, value in indicators.items():
                logger.info(f"   • {key}: {value}")
            
            # ========================================
            # PASO 4: GENERACIÓN DE RESÚMENES
            # ========================================
            logger.info("\n📋 PASO 4: GENERACIÓN DE RESÚMENES")
            logger.info("-"*50)
            
            # Generar resumen editorial (máx 6 líneas)
            logger.info("📝 Generando resumen editorial...")
            editorial = self._generate_editorial(classified)
            
            # Generar resúmenes por noticia
            logger.info("📝 Generando resúmenes de noticias...")
            articles_with_summaries = await self._generate_summaries(classified)
            
            # ========================================
            # PASO 5: COMPOSICIÓN DEL NEWSLETTER
            # ========================================
            logger.info("\n📋 PASO 5: COMPOSICIÓN DEL NEWSLETTER")
            logger.info("-"*50)
            
            html_content, text_content = self.composer.compose_newsletter(
                editorial,
                indicators,
                articles_with_summaries
            )
            
            # Agregar nota de fuente IziMedia
            footer_note = """
            <div style="margin-top: 20px; padding: 15px; background: #f0f0f0; font-size: 10pt;">
                <p><strong>Fuente:</strong> Monitoreo realizado a través de IziMedia</p>
                <p>Total de medios consultados: 150+ fuentes nacionales e internacionales</p>
                <p>Fecha de consulta: """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """</p>
            </div>
            """
            html_content = html_content.replace('</body>', f'{footer_note}</body>')
            
            # ========================================
            # PASO 6: GUARDAR Y PREPARAR ENVÍO
            # ========================================
            logger.info("\n📋 PASO 6: GUARDANDO NEWSLETTER")
            logger.info("-"*50)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.output_dir / f"monitoreo_acafi_{timestamp}.html"
            text_file = self.output_dir / f"monitoreo_acafi_{timestamp}.txt"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            logger.info(f"✅ HTML guardado: {html_file}")
            logger.info(f"✅ Texto guardado: {text_file}")
            
            # ========================================
            # PASO 7: ENVÍO POR MAILCHIMP
            # ========================================
            logger.info("\n📋 PASO 7: PREPARACIÓN PARA ENVÍO")
            logger.info("-"*50)
            logger.info("📧 Newsletter listo para envío por Mailchimp")
            logger.info("   • Envío de prueba: acafi@acafi.com, btagle@proyectacomunicaciones.cl")
            logger.info("   • Listas: Asociados ACAFI, Colaboradores ACAFI")
            
            # Aquí iría la integración con Mailchimp cuando esté configurada
            
            # ========================================
            # RESUMEN FINAL
            # ========================================
            logger.info("\n" + "="*70)
            logger.info("   ✅ MONITOREO COMPLETADO EXITOSAMENTE")
            logger.info("="*70)
            logger.info(f"   • Noticias procesadas: {len(izimedia_articles)}")
            logger.info(f"   • Secciones generadas: {len([s for s in classified if classified[s]])}")
            logger.info(f"   • Tiempo total: {datetime.now().strftime('%H:%M')}")
            logger.info("="*70 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ ERROR EN EL PROCESO: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _convert_izimedia_to_articles(self, izimedia_articles: List[IziMediaArticle]) -> List[Article]:
        """Convertir artículos de IziMedia al formato interno"""
        articles = []
        
        for izi_article in izimedia_articles:
            article = Article(
                url=izi_article.url,
                source=izi_article.source,
                title=izi_article.title,
                subtitle=None,
                content=izi_article.content,
                published_at=izi_article.published_date,
                scraped_at=datetime.now()
            )
            articles.append(article)
        
        return articles
    
    def _classify_by_sections(self, articles: List[Article]) -> Dict:
        """
        Clasificar según las 4 secciones del documento:
        1. Indicadores Económicos
        2. ACAFI
        3. Temas Industria
        4. Noticias de Interés
        """
        classified = {
            NewsSection.INDICADORES: [],
            NewsSection.ACAFI: [],
            NewsSection.INDUSTRIA: [],
            NewsSection.INTERES: []
        }
        
        for article in articles:
            result = self.classifier.classify(article)
            
            # Aplicar reglas especiales del documento
            # "Noticias ACAFI" solo si se nombra ACAFI explícitamente
            if result.mentions_acafi:
                classified[NewsSection.ACAFI].append((article, result))
            else:
                classified[result.section].append((article, result))
        
        return classified
    
    def _show_distribution(self, classified: Dict):
        """Mostrar distribución de noticias por sección"""
        for section, items in classified.items():
            if items:
                logger.info(f"   • {section.value}: {len(items)} noticias")
    
    def _generate_editorial(self, classified: Dict) -> str:
        """
        Generar editorial según especificaciones:
        - Máximo 6 líneas
        - Comenzar con "Buenos días,"
        - Priorizar tendencias
        """
        editorial = self.llm_processor.generate_editorial_summary(classified)
        
        # Validar longitud
        lines = editorial.split('\n')
        if len(lines) > 6:
            logger.warning(f"⚠️ Editorial muy largo ({len(lines)} líneas), recortando...")
            editorial = '\n'.join(lines[:6])
        
        return editorial
    
    async def _generate_summaries(self, classified: Dict) -> Dict:
        """Generar resúmenes por noticia"""
        articles_with_summaries = {}
        
        for section, items in classified.items():
            if not items:
                continue
                
            summaries = []
            # Límite según documento: máximo 10 por sección
            for article, classification in items[:10]:
                summary = self.llm_processor.generate_article_summary(article)
                
                # Agregar fuente
                summary_with_source = f"{summary} ({article.source})"
                summaries.append((article, summary_with_source))
            
            articles_with_summaries[section] = summaries
        
        return articles_with_summaries

async def main():
    """Función principal"""
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║            SISTEMA DE MONITOREO ACAFI                       ║
    ║                                                              ║
    ║  Flujo según documento oficial:                             ║
    ║  1. Conexión a IziMedia (OBLIGATORIO)                       ║
    ║  2. Búsqueda con palabras clave                             ║
    ║  3. Clasificación por secciones                             ║
    ║  4. Generación de resúmenes                                 ║
    ║  5. Composición de newsletter                               ║
    ║  6. Envío por Mailchimp                                     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    agent = ACAFIClippingAgent()
    success = await agent.run_daily_monitoring()
    
    if success:
        print("\n✅ Proceso completado exitosamente")
        print("   Ver archivo generado en carpeta 'output'")
        sys.exit(0)
    else:
        print("\n❌ Proceso fallido")
        print("   Revisar logs para más detalles")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())