#!/usr/bin/env python3
"""
Script de prueba con noticias REALES
"""
import asyncio
from datetime import datetime
from pathlib import Path
import webbrowser

from loguru import logger
from real_news_fetcher import RealNewsFetcher
from classifier import NewsClassifier, NewsSection
from llm_processor import LLMProcessor
from newsletter_composer import NewsletterComposer
from scraper import BancoCentralScraper, DuplicateDetector

# Configurar logging
logger.add("logs/test_real_{time}.log", rotation="1 day", level="INFO")

class RealNewsClippingAgent:
    def __init__(self):
        self.news_fetcher = RealNewsFetcher()
        self.classifier = NewsClassifier()
        self.llm_processor = LLMProcessor()
        self.bc_scraper = BancoCentralScraper()
        self.duplicate_detector = DuplicateDetector()
        self.composer = NewsletterComposer()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_with_real_news(self):
        """Ejecutar con noticias reales de fuentes RSS"""
        logger.info("\n" + "="*60)
        logger.info("📰 GENERACIÓN DE NEWSLETTER CON NOTICIAS REALES")
        logger.info("="*60)
        
        try:
            # PASO 1: Obtener noticias REALES
            logger.info("\n📥 PASO 1: Obteniendo noticias reales de fuentes RSS...")
            articles = self.news_fetcher.fetch_all_news(days_back=3)  # Últimos 3 días
            
            if not articles:
                logger.error("❌ No se pudieron obtener noticias reales")
                return False
            
            logger.info(f"   ✅ {len(articles)} noticias reales obtenidas")
            
            # Mostrar fuentes
            sources = {}
            for article in articles:
                if article.source not in sources:
                    sources[article.source] = 0
                sources[article.source] += 1
            
            logger.info("\n📊 Distribución por fuente:")
            for source, count in sources.items():
                logger.info(f"   • {source}: {count} noticias")
            
            # PASO 2: Deduplicar
            logger.info("\n🔍 PASO 2: Eliminando duplicados...")
            unique_articles = self._deduplicate_articles(articles)
            logger.info(f"   ✅ {len(unique_articles)} noticias únicas")
            
            # PASO 3: Clasificar
            logger.info("\n📊 PASO 3: Clasificando noticias por sección...")
            classified = self._classify_articles(unique_articles)
            
            for section, items in classified.items():
                if items:
                    logger.info(f"   • {section.value}: {len(items)} noticias")
            
            # PASO 4: Generar resúmenes
            logger.info("\n✍️ PASO 4: Generando resúmenes con Ollama...")
            articles_with_summaries = await self._generate_summaries(classified)
            logger.info("   ✅ Resúmenes generados")
            
            # PASO 5: Obtener indicadores económicos
            logger.info("\n💹 PASO 5: Obteniendo indicadores económicos...")
            indicators = await self.bc_scraper.fetch_indicators()
            logger.info(f"   ✅ Indicadores obtenidos")
            
            # PASO 6: Generar resumen editorial
            logger.info("\n📝 PASO 6: Generando resumen editorial...")
            editorial = self.llm_processor.generate_editorial_summary(classified)
            logger.info("   ✅ Resumen editorial generado")
            
            # Mostrar el editorial
            logger.info("\n" + "-"*40)
            logger.info("RESUMEN EDITORIAL:")
            logger.info(editorial)
            logger.info("-"*40)
            
            # PASO 7: Componer newsletter
            logger.info("\n📧 PASO 7: Componiendo newsletter HTML...")
            html_content, text_content = self.composer.compose_newsletter(
                editorial,
                indicators,
                articles_with_summaries
            )
            
            # Agregar sección de fuentes consultadas
            sources_html = self._create_sources_section(articles)
            html_content = html_content.replace('</body>', f'{sources_html}</body>')
            
            # PASO 8: Guardar archivos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.output_dir / f"newsletter_real_{timestamp}.html"
            text_file = self.output_dir / f"newsletter_real_{timestamp}.txt"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            logger.info(f"\n✅ Newsletter generado exitosamente:")
            logger.info(f"   • HTML: {html_file}")
            logger.info(f"   • Texto: {text_file}")
            
            # Abrir en navegador
            logger.info("\n🌐 Abriendo newsletter en el navegador...")
            webbrowser.open(f"file://{html_file.absolute()}")
            
            # Mostrar estadísticas
            self._show_statistics(classified, articles_with_summaries)
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _deduplicate_articles(self, articles):
        """Deduplicar artículos"""
        # Por ahora, usar URLs únicas
        seen_urls = set()
        unique = []
        for article in articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique.append(article)
        return unique
    
    def _classify_articles(self, articles):
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
        
        # Priorizar dentro de cada sección
        for section in classified:
            classified[section] = self.classifier.prioritize_articles(classified[section])
        
        return classified
    
    async def _generate_summaries(self, classified):
        """Generar resúmenes para artículos"""
        articles_with_summaries = {}
        
        for section, items in classified.items():
            if not items:
                continue
                
            summaries = []
            # Limitar a 5 por sección para la prueba
            for article, classification in items[:5]:
                logger.info(f"   Generando resumen para: {article.title[:50]}...")
                
                # Generar resumen
                summary = self.llm_processor.generate_article_summary(article)
                
                # Agregar fuente y fecha al resumen
                source_date = f"({article.source}, {article.published_at.strftime('%d/%m')})"
                summary_with_source = f"{summary} {source_date}"
                
                summaries.append((article, summary_with_source))
            
            if summaries:
                articles_with_summaries[section] = summaries
        
        return articles_with_summaries
    
    def _create_sources_section(self, articles):
        """Crear sección HTML con fuentes consultadas"""
        sources = {}
        for article in articles:
            if article.source not in sources:
                sources[article.source] = []
            sources[article.source].append(article)
        
        html = """
        <div style="margin-top: 40px; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
            <h3 style="color: #004B87;">📚 Fuentes Consultadas</h3>
            <p style="font-size: 11pt; color: #666;">
        """
        
        for source, source_articles in sources.items():
            html += f"<strong>{source}</strong>: {len(source_articles)} noticias<br>"
        
        html += f"""
            </p>
            <p style="font-size: 10pt; color: #999; margin-top: 15px;">
                Noticias obtenidas de fuentes RSS públicas<br>
                Fecha de consulta: {datetime.now().strftime("%d/%m/%Y %H:%M")}
            </p>
        </div>
        """
        
        return html
    
    def _show_statistics(self, classified, articles_with_summaries):
        """Mostrar estadísticas del newsletter"""
        logger.info("\n" + "="*60)
        logger.info("📊 ESTADÍSTICAS DEL NEWSLETTER")
        logger.info("="*60)
        
        total_classified = sum(len(items) for items in classified.values())
        total_included = sum(len(items) for items in articles_with_summaries.values())
        
        logger.info(f"\n📈 Resumen:")
        logger.info(f"   • Artículos procesados: {total_classified}")
        logger.info(f"   • Artículos incluidos: {total_included}")
        logger.info(f"   • Secciones con contenido: {len([s for s in articles_with_summaries if articles_with_summaries[s]])}")

async def main():
    """Función principal"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║      PRUEBA CON NOTICIAS REALES - ACAFI CLIPPING        ║
    ║                                                          ║
    ║  Usando fuentes RSS públicas de medios chilenos         ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    agent = RealNewsClippingAgent()
    success = await agent.run_with_real_news()
    
    if success:
        print("\n✅ Newsletter generado exitosamente con noticias reales")
        print("   El archivo HTML se abrió en tu navegador")
    else:
        print("\n❌ Error generando el newsletter")

if __name__ == "__main__":
    asyncio.run(main())