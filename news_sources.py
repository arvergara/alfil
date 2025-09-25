"""
Conectores para fuentes reales de noticias chilenas
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
from loguru import logger

@dataclass
class NewsItem:
    """Noticia obtenida de fuente real"""
    title: str
    url: str
    source: str
    published_date: datetime
    summary: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    citation: str = ""  # Cita para referenciar: "Fuente: Diario Financiero, 08/09/2024"
    
    def __post_init__(self):
        """Generar cita automática"""
        if not self.citation:
            date_str = self.published_date.strftime("%d/%m/%Y")
            self.citation = f"Fuente: {self.source}, {date_str}"

class RealNewsConnector:
    """Conector para obtener noticias REALES de fuentes verificadas"""
    
    def __init__(self):
        self.sources = {
            'rss': {
                'EMOL Economía': 'https://www.emol.com/rss/economia.xml',
                'Cooperativa Economía': 'https://www.cooperativa.cl/noticias/site/tax/port/economia_rss.xml',
                'BioBio Economía': 'https://www.biobiochile.cl/rss/economia.xml',
                'El Mostrador Mercados': 'https://www.elmostrador.cl/mercados/feed/',
                'CNN Chile Economía': 'https://www.cnnchile.com/economia/feed/',
                'T13 Negocios': 'https://www.t13.cl/rss/negocios',
            },
            'web': {
                'Diario Financiero': 'https://www.df.cl',
                'El Mercurio Inversiones': 'https://www.elmercurioinversiones.cl',
                'La Tercera Pulso': 'https://www.latercera.com/canal/pulso/',
                'Banco Central': 'https://www.bcentral.cl/web/banco-central/areas/prensa',
            }
        }
        
        self.keywords_filter = [
            # Fondos e inversión
            'fondo', 'inversión', 'AGF', 'AFP', 'pensiones',
            'administradora', 'venture capital', 'private equity',
            
            # Mercado financiero
            'bolsa', 'IPSA', 'acciones', 'bonos', 'renta fija',
            'mercado', 'financiero', 'CMF', 'comisión',
            
            # Economía
            'Banco Central', 'tasa', 'inflación', 'IPC', 'UF',
            'dólar', 'tipo de cambio', 'política monetaria',
            
            # Inmobiliario
            'inmobiliario', 'multifamily', 'real estate',
            
            # Instituciones
            'ACAFI', 'LarrainVial', 'Banchile', 'BCI', 'Santander',
            'BTG Pactual', 'Credicorp', 'Moneda', 'Compass'
        ]
    
    def fetch_all_news(self, days_back: int = 2) -> List[NewsItem]:
        """
        Obtener noticias reales de todas las fuentes
        
        Args:
            days_back: Días hacia atrás para buscar noticias
            
        Returns:
            Lista de noticias reales con citas
        """
        all_news = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Obtener de fuentes RSS
        logger.info("📡 Conectando a fuentes RSS reales...")
        for source_name, rss_url in self.sources['rss'].items():
            try:
                news = self._fetch_rss(source_name, rss_url, cutoff_date)
                all_news.extend(news)
                logger.info(f"  ✅ {source_name}: {len(news)} noticias")
            except Exception as e:
                logger.error(f"  ❌ Error en {source_name}: {e}")
        
        # Filtrar por palabras clave relevantes
        filtered_news = self._filter_relevant_news(all_news)
        
        logger.info(f"📰 Total: {len(filtered_news)} noticias relevantes de {len(all_news)} totales")
        
        if len(filtered_news) == 0:
            logger.warning("⚠️ NO SE ENCONTRARON NOTICIAS REALES - NO SE PUEDE GENERAR NEWSLETTER")
            raise ValueError("NO HAY FUENTES DE NOTICIAS REALES DISPONIBLES")
        
        return filtered_news
    
    def _fetch_rss(self, source_name: str, rss_url: str, cutoff_date: datetime) -> List[NewsItem]:
        """Obtener noticias de un feed RSS"""
        news_items = []
        
        try:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:30]:  # Limitar a 30 más recientes
                # Parsear fecha
                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])
                
                # Filtrar por fecha
                if pub_date < cutoff_date:
                    continue
                
                # Crear item de noticia
                news_item = NewsItem(
                    title=entry.title,
                    url=entry.link,
                    source=source_name,
                    published_date=pub_date,
                    summary=getattr(entry, 'summary', None),
                    author=getattr(entry, 'author', None)
                )
                
                news_items.append(news_item)
                
        except Exception as e:
            logger.error(f"Error procesando RSS {source_name}: {e}")
        
        return news_items
    
    def _filter_relevant_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Filtrar noticias relevantes según palabras clave"""
        relevant = []
        
        for item in news_items:
            # Combinar título y resumen para búsqueda
            text = f"{item.title} {item.summary or ''}".lower()
            
            # Verificar si contiene palabras clave relevantes
            for keyword in self.keywords_filter:
                if keyword.lower() in text:
                    relevant.append(item)
                    break
        
        return relevant
    
    def verify_news_availability(self) -> Dict[str, bool]:
        """Verificar qué fuentes están disponibles"""
        status = {}
        
        logger.info("🔍 Verificando disponibilidad de fuentes...")
        
        for source_name, rss_url in self.sources['rss'].items():
            try:
                response = requests.head(rss_url, timeout=5)
                available = response.status_code == 200
                status[source_name] = available
                logger.info(f"  {'✅' if available else '❌'} {source_name}")
            except:
                status[source_name] = False
                logger.info(f"  ❌ {source_name} (timeout)")
        
        return status

class CitationManager:
    """Gestor de citas para cada afirmación del newsletter"""
    
    @staticmethod
    def add_citation_to_text(text: str, source: str, date: str) -> str:
        """
        Agregar cita al final del texto
        
        Ejemplo:
            Input: "ACAFI propone nuevas regulaciones"
            Output: "ACAFI propone nuevas regulaciones (Diario Financiero, 08/09/2024)"
        """
        citation = f" ({source}, {date})"
        return text + citation
    
    @staticmethod
    def extract_facts_with_sources(news_items: List[NewsItem]) -> Dict[str, str]:
        """
        Extraer hechos con sus fuentes
        
        Returns:
            Dict con formato: {"hecho": "fuente, fecha"}
        """
        facts = {}
        
        for item in news_items:
            # Extraer hechos principales del título
            fact = item.title
            source_citation = f"{item.source}, {item.published_date.strftime('%d/%m/%Y')}"
            facts[fact] = source_citation
        
        return facts
    
    @staticmethod
    def validate_editorial_citations(editorial: str, news_items: List[NewsItem]) -> tuple[bool, List[str]]:
        """
        Validar que todas las afirmaciones del editorial tengan respaldo en fuentes
        
        Returns:
            (es_válido, lista_de_problemas)
        """
        problems = []
        
        # Dividir editorial en oraciones
        sentences = re.split(r'[.!?]+', editorial)
        
        # Combinar todo el contenido de las noticias
        all_content = ' '.join([
            f"{item.title} {item.summary or ''}"
            for item in news_items
        ])
        
        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue
                
            # Buscar si la oración tiene respaldo en alguna noticia
            sentence_lower = sentence.lower().strip()
            
            # Extraer entidades principales (organizaciones, números)
            entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', sentence)
            numbers = re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:%|millones?|mil)?\b', sentence)
            
            # Verificar que las entidades y números estén en las fuentes
            for entity in entities:
                if entity not in ['El', 'La', 'Los', 'Las', 'En', 'Buenos']:
                    if entity not in all_content:
                        problems.append(f"'{entity}' no tiene fuente verificada")
            
            for number in numbers:
                if number not in all_content:
                    problems.append(f"Cifra '{number}' sin fuente")
        
        is_valid = len(problems) == 0
        return is_valid, problems

class NewsValidator:
    """Validador para asegurar que solo se use información de fuentes reales"""
    
    @staticmethod
    def validate_before_generation(news_items: List[NewsItem]) -> bool:
        """
        Validar ANTES de generar cualquier contenido
        
        Criterios:
        - Debe haber al menos 3 noticias reales
        - Las noticias deben ser de las últimas 48 horas
        - Debe haber al menos 2 fuentes diferentes
        """
        if len(news_items) < 3:
            logger.error("❌ Insuficientes noticias reales (mínimo 3)")
            return False
        
        # Verificar antigüedad
        now = datetime.now()
        for item in news_items:
            age = now - item.published_date
            if age.days > 2:
                logger.warning(f"⚠️ Noticia muy antigua: {item.title} ({age.days} días)")
        
        # Verificar diversidad de fuentes
        sources = set(item.source for item in news_items)
        if len(sources) < 2:
            logger.error("❌ Insuficiente diversidad de fuentes (mínimo 2)")
            return False
        
        logger.info(f"✅ Validación exitosa: {len(news_items)} noticias de {len(sources)} fuentes")
        return True
    
    @staticmethod
    def create_source_summary(news_items: List[NewsItem]) -> str:
        """Crear resumen de fuentes para el usuario"""
        sources = {}
        for item in news_items:
            if item.source not in sources:
                sources[item.source] = 0
            sources[item.source] += 1
        
        summary = "📊 Fuentes consultadas:\n"
        for source, count in sources.items():
            summary += f"  • {source}: {count} noticias\n"
        
        return summary