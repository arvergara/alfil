#!/usr/bin/env python3
"""
Script de prueba local del agente de clipping SIN Mailchimp
Genera el newsletter en HTML y lo guarda localmente
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import webbrowser
import tempfile

# Configurar logging simple
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from models import Article
from classifier import NewsClassifier, NewsSection
from llm_processor import LLMProcessor
from newsletter_composer import NewsletterComposer
from scraper import BancoCentralScraper, DuplicateDetector

class LocalClippingAgent:
    def __init__(self):
        logger.info("🚀 Inicializando agente de clipping local...")
        self.classifier = NewsClassifier()
        self.llm_processor = LLMProcessor()
        self.bc_scraper = BancoCentralScraper()
        self.duplicate_detector = DuplicateDetector()
        self.composer = NewsletterComposer()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def create_sample_articles(self) -> list[Article]:
        """Crear artículos de ejemplo para pruebas"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        articles = [
            Article(
                url="https://df.cl/mercados/fondos/acafi-propone-nuevas-regulaciones",
                source="Diario Financiero",
                title="ACAFI propone nuevas regulaciones para fortalecer industria de fondos de inversión",
                subtitle="Asociación busca mayor transparencia y flexibilidad regulatoria",
                content="""La Asociación Chilena de Administradoras de Fondos de Inversión (ACAFI) presentó 
                una serie de propuestas regulatorias a la CMF con el objetivo de fortalecer la industria. 
                Entre las medidas destacan mayor flexibilidad para inversiones alternativas y nuevos 
                mecanismos de supervisión.""",
                published_at=today,
                scraped_at=today
            ),
            Article(
                url="https://elmercurio.com/inversiones/larrain-vial-nuevo-fondo",
                source="El Mercurio Inversiones",
                title="LarrainVial Asset Management lanza fondo de venture capital de US$150 millones",
                subtitle="Apuesta por startups tecnológicas en Latinoamérica",
                content="""LarrainVial Asset Management anunció el lanzamiento de su nuevo fondo de 
                venture capital enfocado en startups tecnológicas. El vehículo, que ya cuenta con 
                compromisos por US$150 millones, invertirá en empresas en etapa Serie A y B.""",
                published_at=today,
                scraped_at=today
            ),
            Article(
                url="https://latercera.com/pulso/fondos-inmobiliarios-recuperacion",
                source="La Tercera Pulso",
                title="Fondos inmobiliarios muestran signos de recuperación con rentabilidades de 8% anual",
                subtitle="Sector multifamily lidera el repunte",
                content="""Los fondos de inversión inmobiliaria registraron una recuperación significativa 
                en el tercer trimestre, con rentabilidades promedio de 8% anual. El segmento multifamily 
                fue el más destacado, impulsado por la demanda de arriendos.""",
                published_at=today,
                scraped_at=today
            ),
            Article(
                url="https://df.cl/economia/banco-central-tasa",
                source="Diario Financiero",
                title="Banco Central mantiene tasa de política monetaria en 5,5%",
                subtitle="Consejo cita presiones inflacionarias persistentes",
                content="""El Banco Central de Chile decidió mantener la tasa de política monetaria en 5,5% 
                en su reunión mensual. El Consejo señaló que las presiones inflacionarias continúan 
                presentes y que mantendrá una política restrictiva.""",
                published_at=yesterday,
                scraped_at=today
            ),
            Article(
                url="https://emol.com/economia/afp-rentabilidad",
                source="Emol Economía",
                title="AFP reportan rentabilidad positiva en todos los fondos durante octubre",
                subtitle="Fondo A lidera con 3,5% mensual",
                content="""Las Administradoras de Fondos de Pensiones reportaron rentabilidades positivas 
                en todos los multifondos durante octubre. El Fondo A, de mayor riesgo, lideró con un 
                retorno de 3,5% en el mes.""",
                published_at=yesterday,
                scraped_at=today
            ),
            Article(
                url="https://df.cl/mercados/cmf-nueva-normativa",
                source="Diario Financiero",
                title="CMF publica nueva normativa para administradoras generales de fondos",
                subtitle="Cambios entrarán en vigencia en enero de 2025",
                content="""La Comisión para el Mercado Financiero (CMF) publicó la nueva normativa que 
                regula a las administradoras generales de fondos. Los cambios incluyen mayores exigencias 
                de capital y nuevos reportes de riesgo.""",
                published_at=today,
                scraped_at=today
            ),
            Article(
                url="https://fundssociety.com/es/noticias/private-equity-latam",
                source="Funds Society",
                title="Private equity en Latinoamérica alcanza récord de US$15 mil millones en activos",
                subtitle="Chile concentra el 25% de las inversiones regionales",
                content="""La industria de private equity en Latinoamérica alcanzó un récord de US$15 mil 
                millones en activos bajo administración. Chile se posiciona como el segundo mercado más 
                importante de la región, concentrando el 25% de las inversiones.""",
                published_at=today,
                scraped_at=today
            ),
            Article(
                url="https://latercera.com/pulso/fintech-corfo-fondo",
                source="La Tercera Pulso",
                title="Corfo anuncia nuevo fondo de US$50 millones para impulsar fintech",
                subtitle="Programa busca acelerar innovación financiera",
                content="""Corfo anunció la creación de un nuevo fondo de US$50 millones destinado a 
                impulsar el desarrollo de empresas fintech en Chile. El programa incluye capital y 
                mentoría para startups del sector financiero.""",
                published_at=today,
                scraped_at=today
            )
        ]
        
        return articles
    
    async def run_test(self):
        """Ejecutar prueba completa del sistema"""
        logger.info("\n" + "="*60)
        logger.info("📰 INICIANDO GENERACIÓN DE NEWSLETTER DE PRUEBA")
        logger.info("="*60)
        
        try:
            # 1. Obtener artículos
            logger.info("\n📥 Paso 1: Obteniendo artículos de ejemplo...")
            articles = self.create_sample_articles()
            logger.info(f"   ✅ {len(articles)} artículos cargados")
            
            # 2. Deduplicar
            logger.info("\n🔍 Paso 2: Verificando duplicados...")
            unique_articles = self._deduplicate_articles(articles)
            logger.info(f"   ✅ {len(unique_articles)} artículos únicos")
            
            # 3. Clasificar
            logger.info("\n📊 Paso 3: Clasificando artículos por sección...")
            classified = self._classify_articles(unique_articles)
            for section, items in classified.items():
                if items:
                    logger.info(f"   • {section.value}: {len(items)} artículos")
            
            # 4. Generar resúmenes
            logger.info("\n✍️ Paso 4: Generando resúmenes con Ollama...")
            articles_with_summaries = await self._generate_summaries(classified)
            logger.info("   ✅ Resúmenes generados")
            
            # 5. Obtener indicadores económicos
            logger.info("\n💹 Paso 5: Obteniendo indicadores económicos...")
            indicators = await self.bc_scraper.fetch_indicators()
            logger.info(f"   ✅ Indicadores: {', '.join(indicators.keys())}")
            
            # 6. Generar resumen editorial
            logger.info("\n📝 Paso 6: Generando resumen editorial...")
            editorial = self.llm_processor.generate_editorial_summary(classified)
            logger.info("   ✅ Resumen editorial generado")
            logger.info("\n" + "-"*40)
            logger.info("RESUMEN EDITORIAL:")
            logger.info(editorial)
            logger.info("-"*40)
            
            # 7. Componer newsletter
            logger.info("\n📧 Paso 7: Componiendo newsletter HTML...")
            html_content, text_content = self.composer.compose_newsletter(
                editorial,
                indicators,
                articles_with_summaries
            )
            
            # 8. Guardar y mostrar resultado
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = self.output_dir / f"newsletter_{timestamp}.html"
            text_file = self.output_dir / f"newsletter_{timestamp}.txt"
            
            # Guardar archivos
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
            
        except Exception as e:
            logger.error(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    def _deduplicate_articles(self, articles: list[Article]) -> list[Article]:
        """Deduplicar artículos"""
        duplicate_groups = self.duplicate_detector.find_duplicates(articles)
        unique = []
        for group_id, group_articles in duplicate_groups.items():
            unique.append(group_articles[0])
        return unique
    
    def _classify_articles(self, articles: list[Article]) -> dict:
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
            article.section_detected = result.section.value
            article.sector_tags = json.dumps(result.sector_tags)
            article.mentions_acafi = result.mentions_acafi
            article.is_partner_new_fund = result.is_partner_new_fund
            article.relevance_score = result.confidence
            
            classified[result.section].append((article, result))
        
        # Priorizar dentro de cada sección
        for section in classified:
            classified[section] = self.classifier.prioritize_articles(classified[section])
        
        return classified
    
    async def _generate_summaries(self, classified: dict) -> dict:
        """Generar resúmenes para artículos"""
        articles_with_summaries = {}
        
        for section, items in classified.items():
            summaries = []
            for article, classification in items[:5]:  # Limitar a 5 por sección
                if not article.summary:
                    logger.info(f"   Generando resumen para: {article.title[:50]}...")
                    article.summary = self.llm_processor.generate_article_summary(article)
                summaries.append((article, article.summary))
            
            if summaries:
                articles_with_summaries[section] = summaries
        
        return articles_with_summaries
    
    def _show_statistics(self, classified: dict, articles_with_summaries: dict):
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
        
        logger.info(f"\n📑 Por sección:")
        for section in NewsSection:
            classified_count = len(classified.get(section, []))
            included_count = len(articles_with_summaries.get(section, []))
            if classified_count > 0:
                logger.info(f"   • {section.value}: {included_count}/{classified_count} artículos")

async def main():
    """Función principal"""
    agent = LocalClippingAgent()
    await agent.run_test()
    
    logger.info("\n" + "="*60)
    logger.info("✅ PRUEBA COMPLETADA EXITOSAMENTE")
    logger.info("="*60)
    logger.info("\n💡 Próximos pasos:")
    logger.info("   1. Revisar el HTML generado en la carpeta 'output'")
    logger.info("   2. Configurar fuentes de noticias reales")
    logger.info("   3. Configurar Mailchimp cuando tengas las credenciales")
    logger.info("   4. Ejecutar en producción con: python main.py")

if __name__ == "__main__":
    # Verificar que Ollama está corriendo
    import subprocess
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            logger.error("❌ Ollama no está corriendo. Ejecuta: ollama serve")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Error verificando Ollama: {e}")
        logger.info("   Continuando de todos modos...")
    
    # Ejecutar prueba
    asyncio.run(main())