#!/usr/bin/env python3
"""
Sistema principal de producción - REQUIERE FUENTES REALES
NO genera contenido sin noticias verificadas
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from loguru import logger
from models import Article
from classifier import NewsClassifier, NewsSection
from llm_processor import LLMProcessor
from newsletter_composer import NewsletterComposer
from news_sources import RealNewsConnector, CitationManager, NewsValidator, NewsItem
from scraper import BancoCentralScraper

# Configurar logging
logger.add(
    "logs/production_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

class ProductionClippingAgent:
    """Agente de producción que SOLO funciona con fuentes reales"""
    
    def __init__(self):
        self.news_connector = RealNewsConnector()
        self.citation_manager = CitationManager()
        self.validator = NewsValidator()
        self.classifier = NewsClassifier()
        self.llm_processor = LLMProcessor()
        self.composer = NewsletterComposer()
        self.bc_scraper = BancoCentralScraper()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_daily_newsletter(self) -> bool:
        """
        Ejecutar generación del newsletter diario
        
        Returns:
            True si se generó exitosamente, False si no hay fuentes
        """
        logger.info("\n" + "="*60)
        logger.info("🚀 INICIANDO GENERACIÓN DE NEWSLETTER DE PRODUCCIÓN")
        logger.info("="*60)
        
        try:
            # PASO 1: OBLIGATORIO - Obtener noticias reales
            logger.info("\n📡 PASO 1: Conectando a fuentes de noticias REALES...")
            
            # Verificar disponibilidad de fuentes
            sources_status = self.news_connector.verify_news_availability()
            available_sources = sum(1 for available in sources_status.values() if available)
            
            if available_sources == 0:
                logger.error("❌ NO HAY FUENTES DE NOTICIAS DISPONIBLES")
                logger.error("   No se puede generar newsletter sin fuentes reales")
                return False
            
            # Obtener noticias
            news_items = self.news_connector.fetch_all_news(days_back=2)
            
            # PASO 2: VALIDACIÓN OBLIGATORIA
            logger.info("\n✅ PASO 2: Validando fuentes...")
            if not self.validator.validate_before_generation(news_items):
                logger.error("❌ VALIDACIÓN FALLIDA - No se puede generar newsletter")
                logger.error("   Razón: Insuficientes fuentes verificadas")
                return False
            
            # Mostrar resumen de fuentes
            logger.info(self.validator.create_source_summary(news_items))
            
            # PASO 3: Convertir a formato Article con citas
            logger.info("\n📝 PASO 3: Procesando noticias con citas...")
            articles = self._convert_to_articles_with_citations(news_items)
            
            # PASO 4: Clasificar noticias
            logger.info("\n📊 PASO 4: Clasificando noticias...")
            classified = self._classify_articles(articles)
            
            # PASO 5: Generar resúmenes CON CITAS
            logger.info("\n✍️ PASO 5: Generando resúmenes con referencias...")
            articles_with_summaries = await self._generate_summaries_with_citations(
                classified, 
                news_items
            )
            
            # PASO 6: Obtener indicadores económicos
            logger.info("\n💹 PASO 6: Obteniendo indicadores económicos...")
            indicators = await self.bc_scraper.fetch_indicators()
            
            # PASO 7: Generar editorial CON VALIDACIÓN
            logger.info("\n📝 PASO 7: Generando editorial con verificación...")
            editorial = await self._generate_editorial_with_validation(
                classified,
                news_items
            )
            
            # PASO 8: Componer newsletter
            logger.info("\n📧 PASO 8: Componiendo newsletter final...")
            html_content, text_content = self.composer.compose_newsletter(
                editorial,
                indicators,
                articles_with_summaries
            )
            
            # Agregar sección de fuentes al final
            sources_section = self._create_sources_section(news_items)
            html_content = html_content.replace('</body>', f'{sources_section}</body>')
            text_content += f"\n\n{sources_section}"
            
            # PASO 9: Guardar newsletter
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.output_dir / f"newsletter_prod_{timestamp}.html"
            text_file = self.output_dir / f"newsletter_prod_{timestamp}.txt"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            logger.info(f"\n✅ NEWSLETTER GENERADO EXITOSAMENTE")
            logger.info(f"   • HTML: {html_file}")
            logger.info(f"   • Texto: {text_file}")
            logger.info(f"   • Basado en {len(news_items)} fuentes verificadas")
            
            return True
            
        except ValueError as e:
            logger.error(f"\n❌ ERROR CRÍTICO: {e}")
            logger.error("   El sistema está diseñado para NO generar contenido sin fuentes reales")
            return False
            
        except Exception as e:
            logger.error(f"\n❌ ERROR INESPERADO: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _convert_to_articles_with_citations(self, news_items: List[NewsItem]) -> List[Article]:
        """Convertir NewsItems a Articles manteniendo las citas"""
        articles = []
        
        for item in news_items:
            article = Article(
                url=item.url,
                source=item.source,
                title=item.title,
                subtitle=None,
                content=item.summary,
                published_at=item.published_date,
                scraped_at=datetime.now()
            )
            # Guardar la cita en el campo evidence
            article.evidence = item.citation
            articles.append(article)
        
        return articles
    
    def _classify_articles(self, articles: List[Article]) -> Dict:
        """Clasificar artículos por sección"""
        classified = {
            NewsSection.INDICADORES: [],
            NewsSection.ACAFI: [],
            NewsSection.INDUSTRIA: [],
            NewsSection.INTERES: [],
            NewsSection.SOCIOS: []
        }
        
        for article in articles:
            result = self.classifier.classify(article)
            classified[result.section].append((article, result))
        
        return classified
    
    async def _generate_summaries_with_citations(
        self,
        classified: Dict,
        news_items: List[NewsItem]
    ) -> Dict:
        """Generar resúmenes incluyendo citas de fuentes"""
        articles_with_summaries = {}
        
        for section, items in classified.items():
            summaries = []
            for article, classification in items[:5]:
                # Generar resumen
                summary = self.llm_processor.generate_article_summary(article)
                
                # Agregar cita al resumen
                citation = article.evidence or f"(Fuente: {article.source})"
                summary_with_citation = f"{summary} {citation}"
                
                summaries.append((article, summary_with_citation))
            
            if summaries:
                articles_with_summaries[section] = summaries
        
        return articles_with_summaries
    
    async def _generate_editorial_with_validation(
        self,
        classified: Dict,
        news_items: List[NewsItem]
    ) -> str:
        """Generar editorial con validación estricta de fuentes"""
        
        # Generar editorial
        editorial = self.llm_processor.generate_editorial_summary(classified)
        
        # Validar que todas las afirmaciones tengan respaldo
        is_valid, problems = self.citation_manager.validate_editorial_citations(
            editorial,
            news_items
        )
        
        if not is_valid:
            logger.warning(f"⚠️ Problemas de verificación en editorial:")
            for problem in problems:
                logger.warning(f"   • {problem}")
            
            # Agregar nota de precaución
            editorial += "\n\n*Nota: Este resumen se basa en las fuentes consultadas."
        
        return editorial
    
    def _create_sources_section(self, news_items: List[NewsItem]) -> str:
        """Crear sección HTML con todas las fuentes consultadas"""
        html = """
        <div style="margin-top: 40px; padding: 20px; background-color: #f5f5f5; border-radius: 8px;">
            <h3 style="color: #004B87; margin-bottom: 15px;">📚 Fuentes Consultadas</h3>
            <div style="font-size: 11pt; color: #666;">
        """
        
        # Agrupar por fuente
        sources = {}
        for item in news_items:
            if item.source not in sources:
                sources[item.source] = []
            sources[item.source].append(item)
        
        for source, items in sources.items():
            html += f"<p><strong>{source}</strong> ({len(items)} noticias):</p><ul style='margin: 5px 0 15px 20px;'>"
            for item in items[:3]:  # Máximo 3 por fuente
                html += f"<li style='margin: 3px 0;'>{item.title[:60]}...</li>"
            if len(items) > 3:
                html += f"<li style='margin: 3px 0; font-style: italic;'>...y {len(items)-3} más</li>"
            html += "</ul>"
        
        html += """
            </div>
            <p style="font-size: 10pt; color: #999; margin-top: 15px;">
                Todas las noticias fueron verificadas y obtenidas de fuentes oficiales.
                Fecha de consulta: """ + datetime.now().strftime("%d/%m/%Y %H:%M") + """
            </p>
        </div>
        """
        
        return html

async def main():
    """Función principal de producción"""
    agent = ProductionClippingAgent()
    
    success = await agent.run_daily_newsletter()
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✅ PROCESO COMPLETADO EXITOSAMENTE")
        logger.info("="*60)
        sys.exit(0)
    else:
        logger.error("\n" + "="*60)
        logger.error("❌ PROCESO FALLIDO - NO SE GENERÓ NEWSLETTER")
        logger.error("   Razón: Sin fuentes de noticias verificadas")
        logger.error("="*60)
        sys.exit(1)

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         SISTEMA DE PRODUCCIÓN - ACAFI CLIPPING          ║
    ║                                                          ║
    ║  ⚠️  IMPORTANTE: Este sistema REQUIERE fuentes reales    ║
    ║     NO genera contenido sin noticias verificadas        ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())