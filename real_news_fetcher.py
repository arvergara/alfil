#!/usr/bin/env python3
"""
Obtenedor de noticias reales de fuentes RSS chilenas
"""
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List
import re
from models import Article
from loguru import logger

class RealNewsFetcher:
    """Obtener noticias REALES de fuentes RSS chilenas"""
    
    def __init__(self):
        # Fuentes RSS que funcionan actualmente
        self.rss_sources = [
            {
                'name': 'El Mostrador - Mercados',
                'url': 'https://www.elmostrador.cl/mercados/feed/',
                'category': 'mercados'
            },
            {
                'name': 'El Mostrador - Economía',
                'url': 'https://www.elmostrador.cl/categoria/pais/economia/feed/',
                'category': 'economia'
            },
            {
                'name': 'CNN Chile - Economía',
                'url': 'https://www.cnnchile.com/economia/feed/',
                'category': 'economia'
            },
            {
                'name': 'Cooperativa - Economía',
                'url': 'https://www.cooperativa.cl/noticias/site/tax/port/economia_rss_3.xml',
                'category': 'economia'
            },
            {
                'name': 'BioBioChile - Nacional',
                'url': 'https://www.biobiochile.cl/rss/nacional.xml',
                'category': 'nacional'
            },
            {
                'name': 'La Tercera - RSS',
                'url': 'https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml',
                'category': 'general'
            },
            {
                'name': 'EMOL - Economía',
                'url': 'https://www.emol.com/rss/economia.xml',
                'category': 'economia'
            },
            {
                'name': 'Diario Financiero',
                'url': 'https://www.df.cl/rss/site',
                'category': 'finanzas'
            }
        ]
        
        # Palabras clave relevantes para ACAFI
        self.keywords = [
            'fondo', 'inversión', 'AFP', 'pensiones', 'CMF',
            'mercado', 'financiero', 'bolsa', 'IPSA', 'acción',
            'banco central', 'tasa', 'interés', 'inflación', 'IPC',
            'inmobiliario', 'AGF', 'administradora', 'fintech',
            'economía', 'PIB', 'dólar', 'UF', 'peso chileno',
            'empresa', 'startup', 'emprendimiento', 'innovación'
        ]
    
    def fetch_all_news(self, days_back: int = 2) -> List[Article]:
        """Obtener noticias reales de todas las fuentes RSS"""
        all_articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        logger.info("📡 Obteniendo noticias reales de fuentes RSS...")
        
        for source in self.rss_sources:
            try:
                logger.info(f"  🔍 Consultando {source['name']}...")
                articles = self._fetch_from_rss(source, cutoff_date)
                all_articles.extend(articles)
                logger.info(f"     ✅ {len(articles)} noticias obtenidas")
            except Exception as e:
                logger.warning(f"     ⚠️ Error en {source['name']}: {str(e)[:50]}")
        
        # Filtrar por relevancia
        relevant_articles = self._filter_relevant(all_articles)
        
        logger.info(f"\n📊 Total: {len(relevant_articles)} noticias relevantes de {len(all_articles)} totales")
        
        return relevant_articles
    
    def _fetch_from_rss(self, source: dict, cutoff_date: datetime) -> List[Article]:
        """Obtener noticias de un feed RSS específico"""
        articles = []
        
        try:
            # Configurar headers para evitar bloqueos
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            # Algunos feeds requieren headers específicos
            response = requests.get(source['url'], headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            
            for entry in feed.entries[:20]:  # Máximo 20 por fuente
                try:
                    # Obtener fecha de publicación
                    pub_date = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    # Filtrar por fecha
                    if pub_date < cutoff_date:
                        continue
                    
                    # Obtener contenido
                    content = ""
                    if hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # Limpiar HTML del contenido
                    content = re.sub('<.*?>', '', content)
                    content = content.replace('&nbsp;', ' ').replace('&quot;', '"')
                    content = content[:500]  # Limitar a 500 caracteres
                    
                    # Crear artículo
                    article = Article(
                        url=entry.link,
                        source=source['name'],
                        title=entry.title,
                        subtitle=None,
                        content=content,
                        author=getattr(entry, 'author', None),
                        published_at=pub_date,
                        scraped_at=datetime.now()
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.debug(f"Error procesando entrada: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error obteniendo RSS de {source['name']}: {e}")
        
        return articles
    
    def _filter_relevant(self, articles: List[Article]) -> List[Article]:
        """Filtrar artículos relevantes según palabras clave"""
        relevant = []
        
        for article in articles:
            # Combinar título y contenido para búsqueda
            text = f"{article.title} {article.content or ''}".lower()
            
            # Verificar si contiene palabras clave relevantes
            relevance_score = 0
            for keyword in self.keywords:
                if keyword.lower() in text:
                    relevance_score += 1
            
            # Incluir si tiene al menos 1 palabra clave relevante
            if relevance_score > 0:
                article.relevance_score = relevance_score
                relevant.append(article)
        
        # Ordenar por relevancia y fecha
        relevant.sort(key=lambda x: (x.relevance_score, x.published_at), reverse=True)
        
        # Limitar a las 30 más relevantes
        return relevant[:30]

def test_real_news():
    """Probar la obtención de noticias reales"""
    print("\n" + "="*60)
    print("🔍 PROBANDO OBTENCIÓN DE NOTICIAS REALES")
    print("="*60 + "\n")
    
    fetcher = RealNewsFetcher()
    articles = fetcher.fetch_all_news(days_back=2)
    
    if articles:
        print(f"\n✅ Se obtuvieron {len(articles)} noticias relevantes\n")
        
        # Mostrar las primeras 5
        print("📰 Primeras 5 noticias:\n")
        for i, article in enumerate(articles[:5], 1):
            print(f"{i}. {article.title}")
            print(f"   📍 Fuente: {article.source}")
            print(f"   📅 Fecha: {article.published_at.strftime('%d/%m/%Y %H:%M')}")
            print(f"   🔗 URL: {article.url}")
            print(f"   📝 Resumen: {article.content[:100]}...")
            print()
    else:
        print("❌ No se pudieron obtener noticias")
    
    return articles

if __name__ == "__main__":
    test_real_news()