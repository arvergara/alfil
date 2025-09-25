#!/usr/bin/env python3
"""
Script para generar newsletter REAL con datos de IziMedia
Integra el conector de IziMedia con el sistema de newsletter
"""
import asyncio
from datetime import datetime
from pathlib import Path
import webbrowser

from loguru import logger
from izimedia_real import IziMediaRealConnector
from classifier import NewsClassifier, NewsSection
from llm_processor import LLMProcessor
from newsletter_composer import NewsletterComposer
from scraper import BancoCentralScraper
from models import Article

# Configurar logging
logger.add("logs/izimedia_newsletter_{time}.log", rotation="1 day", level="INFO")

class IziMediaNewsletterGenerator:
    """Generador de newsletter usando IziMedia como fuente"""
    
    def __init__(self):
        self.izimedia = IziMediaRealConnector()
        self.classifier = NewsClassifier()
        self.llm_processor = LLMProcessor()
        self.bc_scraper = BancoCentralScraper()
        self.composer = NewsletterComposer()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    async def generate_newsletter(self):
        """Generar newsletter completo con datos de IziMedia"""
        logger.info("\n" + "="*60)
        logger.info("📰 GENERACIÓN DE NEWSLETTER ACAFI - IZIMEDIA")
        logger.info("="*60)
        
        try:
            # PASO 1: Obtener noticias de IziMedia
            logger.info("\n📥 PASO 1: Obteniendo noticias de IziMedia...")
            izimedia_news = await self.izimedia.search_izimedia()
            
            if not izimedia_news:
                logger.error("❌ No se obtuvieron noticias de IziMedia")
                return False
            
            logger.info(f"   ✅ {len(izimedia_news)} noticias obtenidas de IziMedia")
            
            # PASO 2: Convertir a formato Article para clasificación
            logger.info("\n🔄 PASO 2: Convirtiendo formato para clasificación...")
            articles = self._convert_to_articles(izimedia_news)
            
            # PASO 3: Clasificar noticias
            logger.info("\n📊 PASO 3: Clasificando noticias por sección...")
            classified = self._classify_articles(articles)
            
            for section, items in classified.items():
                if items:
                    logger.info(f"   • {section.value}: {len(items)} noticias")
            
            # PASO 4: Generar resúmenes con LLM
            logger.info("\n✍️ PASO 4: Generando resúmenes con Ollama...")
            articles_with_summaries = await self._generate_summaries(classified, izimedia_news)
            logger.info("   ✅ Resúmenes generados")
            
            # PASO 5: Obtener indicadores económicos
            logger.info("\n💹 PASO 5: Obteniendo indicadores económicos...")
            indicators = await self.bc_scraper.fetch_indicators()
            logger.info(f"   ✅ Indicadores obtenidos")
            
            # PASO 6: Generar resumen editorial
            logger.info("\n📝 PASO 6: Generando resumen editorial...")
            editorial = self._generate_editorial(classified, izimedia_news)
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
            
            # Agregar sección de fuentes de IziMedia
            sources_html = self._create_izimedia_sources_section(izimedia_news)
            html_content = html_content.replace('</body>', f'{sources_html}</body>')
            
            # PASO 8: Guardar archivos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.output_dir / f"newsletter_izimedia_{timestamp}.html"
            text_file = self.output_dir / f"newsletter_izimedia_{timestamp}.txt"
            
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
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _convert_to_articles(self, izimedia_news):
        """Convertir noticias de IziMedia a formato Article"""
        articles = []
        for news in izimedia_news:
            article = Article(
                url=news.url_izimedia,  # Usar URL de IziMedia
                source=news.media,
                title=news.title,
                subtitle=None,
                content=news.snippet,
                author=None,
                published_at=news.date,
                scraped_at=datetime.now()
            )
            articles.append(article)
        return articles
    
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
    
    async def _generate_summaries(self, classified, izimedia_news):
        """Generar resúmenes manteniendo URLs de IziMedia"""
        articles_with_summaries = {}
        
        # Crear mapeo de títulos a URLs de IziMedia
        url_map = {news.title: news.url_izimedia for news in izimedia_news}
        
        for section, items in classified.items():
            if not items:
                continue
                
            summaries = []
            # Limitar a 5 por sección
            for article, classification in items[:5]:
                logger.info(f"   Generando resumen para: {article.title[:50]}...")
                
                # Generar resumen
                summary = self.llm_processor.generate_article_summary(article)
                
                # Agregar fuente y fecha
                source_date = f"({article.source}, {article.published_at.strftime('%d/%m')})"
                summary_with_source = f"{summary} {source_date}"
                
                # Asegurar que usamos URL de IziMedia
                if article.title in url_map:
                    article.url = url_map[article.title]
                
                summaries.append((article, summary_with_source))
            
            if summaries:
                articles_with_summaries[section] = summaries
        
        return articles_with_summaries
    
    def _generate_editorial(self, classified, izimedia_news):
        """Generar resumen editorial basado en noticias de IziMedia"""
        # Contar noticias relevantes
        total_fondos = len([n for n in izimedia_news if 'fond' in n.title.lower() or 'AGF' in n.title])
        
        if total_fondos > 0:
            editorial = f"Buenos días, hoy destacan {total_fondos} noticias relevantes sobre fondos de inversión y AGF. "
        else:
            editorial = "Buenos días, no hay noticias relevantes sobre fondos de inversión/AGF hoy. "
        
        # Agregar noticias destacadas
        top_news = []
        for news in izimedia_news[:3]:  # Primeras 3 noticias
            # Extraer lo esencial del título
            title_summary = news.title
            if len(title_summary) > 80:
                title_summary = title_summary[:77] + "..."
            top_news.append(title_summary)
        
        if top_news:
            editorial += " ".join(top_news)
        
        # Limitar a 6 líneas
        lines = editorial.split('. ')
        if len(lines) > 6:
            editorial = '. '.join(lines[:6]) + '.'
        
        return editorial
    
    def _create_izimedia_sources_section(self, izimedia_news):
        """Crear sección HTML con información de IziMedia"""
        medios = {}
        for news in izimedia_news:
            if news.media not in medios:
                medios[news.media] = 0
            medios[news.media] += 1
        
        html = """
        <div style="margin-top: 40px; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
            <h3 style="color: #004B87;">📰 Fuente: IziMedia</h3>
            <p style="font-size: 11pt; color: #666;">
                Noticias obtenidas desde la plataforma IziMedia<br>
                <strong>Medios consultados:</strong><br>
        """
        
        for medio, count in medios.items():
            html += f"• {medio}: {count} noticias<br>"
        
        html += f"""
            </p>
            <p style="font-size: 10pt; color: #999; margin-top: 15px;">
                Monitoreo realizado con palabras clave de ACAFI<br>
                Fecha de consulta: {datetime.now().strftime("%d/%m/%Y %H:%M")}<br>
                <a href="https://muba.izimedia.io" style="color: #004B87;">Acceder a IziMedia</a>
            </p>
        </div>
        """
        
        return html

async def main():
    """Función principal"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     NEWSLETTER ACAFI - INTEGRACIÓN CON IZIMEDIA         ║
    ║                                                          ║
    ║  Generando newsletter con noticias reales de IziMedia   ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    generator = IziMediaNewsletterGenerator()
    success = await generator.generate_newsletter()
    
    if success:
        print("\n✅ Newsletter generado exitosamente con datos de IziMedia")
        print("   El archivo HTML se abrió en tu navegador")
        print("   Los links apuntan a IziMedia, no a los medios originales")
    else:
        print("\n❌ Error generando el newsletter")

if __name__ == "__main__":
    asyncio.run(main())