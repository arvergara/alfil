import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, urljoin

import feedparser
import httpx
import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import Article, NewsSource

class NewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.timeout = settings.SCRAPING_TIMEOUT
        self.max_retries = settings.SCRAPING_MAX_RETRIES
        self.delay = settings.SCRAPING_DELAY
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_url(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def parse_article(self, html: str, url: str, source_config: Dict[str, Any]) -> Optional[Article]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Default selectors - can be customized per source
        title_selector = source_config.get('title_selector', 'h1')
        subtitle_selector = source_config.get('subtitle_selector', 'h2')
        content_selector = source_config.get('content_selector', 'article')
        author_selector = source_config.get('author_selector', '.author')
        date_selector = source_config.get('date_selector', 'time')
        
        title = self._extract_text(soup, title_selector)
        if not title:
            return None
            
        article = Article(
            url=url,
            url_canonical=self._get_canonical_url(soup, url),
            source=urlparse(url).netloc,
            title=title,
            subtitle=self._extract_text(soup, subtitle_selector),
            content=self._extract_text(soup, content_selector),
            author=self._extract_text(soup, author_selector),
            published_at=self._extract_date(soup, date_selector),
            scraped_at=datetime.utcnow()
        )
        
        return article
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        except Exception as e:
            logger.debug(f"Error extracting text with selector {selector}: {e}")
        return None
    
    def _extract_date(self, soup: BeautifulSoup, selector: str) -> datetime:
        try:
            element = soup.select_one(selector)
            if element:
                # Try different date attributes
                date_str = element.get('datetime') or element.get('content') or element.get_text(strip=True)
                # Here you would implement date parsing logic
                return datetime.utcnow()  # Placeholder
        except Exception as e:
            logger.debug(f"Error extracting date: {e}")
        return datetime.utcnow()
    
    def _get_canonical_url(self, soup: BeautifulSoup, url: str) -> str:
        canonical = soup.find('link', {'rel': 'canonical'})
        if canonical and canonical.get('href'):
            return canonical['href']
        return url
    
    async def scrape_rss_feed(self, feed_url: str) -> List[Article]:
        articles = []
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:50]:  # Limit to recent 50 entries
                article = Article(
                    url=entry.link,
                    url_canonical=entry.link,
                    source=feed.feed.title if hasattr(feed.feed, 'title') else urlparse(feed_url).netloc,
                    title=entry.title,
                    subtitle=entry.get('subtitle', ''),
                    content=entry.get('summary', ''),
                    author=entry.get('author', ''),
                    published_at=datetime.fromtimestamp(entry.published_parsed) if hasattr(entry, 'published_parsed') else datetime.utcnow(),
                    scraped_at=datetime.utcnow()
                )
                articles.append(article)
        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {e}")
        
        return articles
    
    async def scrape_news_source(self, source: NewsSource) -> List[Article]:
        articles = []
        
        if source.source_type == 'rss':
            articles = await self.scrape_rss_feed(source.url)
        elif source.source_type == 'web':
            # For web sources, we'd need to implement crawling logic
            # This is a simplified version
            html = self.fetch_url(source.url)
            if html:
                config = json.loads(source.scraping_config or '{}')
                article = self.parse_article(html, source.url, config)
                if article:
                    articles.append(article)
        elif source.source_type == 'api':
            # Implement API-specific logic
            pass
        
        logger.info(f"Scraped {len(articles)} articles from {source.name}")
        return articles

class BancoCentralScraper:
    """Special scraper for Banco Central indicators"""
    
    INDICATORS_URL = "https://si3.bcentral.cl/indicadoressiete/secure/indicadoresdiarios.aspx"
    
    async def fetch_indicators(self) -> Dict[str, str]:
        indicators = {}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.INDICATORS_URL)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Parse indicators (this would need to be adjusted based on actual HTML structure)
                # This is a placeholder implementation
                indicators = {
                    'UF': '$39.360,32',
                    'Dólar Observado': '$967,48',
                    'Euro': '$1.130,63',
                    'UTM': '$68.647,00'
                }
                
        except Exception as e:
            logger.error(f"Error fetching Banco Central indicators: {e}")
            # Return default values as fallback
            indicators = {
                'UF': 'N/A',
                'Dólar Observado': 'N/A',
                'Euro': 'N/A',
                'UTM': 'N/A'
            }
        
        return indicators

class DuplicateDetector:
    """Detect duplicate articles using multiple strategies"""
    
    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute hash of normalized text"""
        normalized = ' '.join(text.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    @staticmethod
    def similarity_ratio(text1: str, text2: str) -> float:
        """Compute similarity between two texts"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def is_duplicate(self, article1: Article, article2: Article, threshold: float = 0.85) -> bool:
        """Check if two articles are duplicates"""
        # Check URL similarity
        if article1.url == article2.url or article1.url_canonical == article2.url_canonical:
            return True
        
        # Check title similarity
        if self.similarity_ratio(article1.title, article2.title) > threshold:
            return True
        
        # Check content hash
        if article1.content and article2.content:
            if self.compute_hash(article1.content) == self.compute_hash(article2.content):
                return True
        
        return False
    
    def find_duplicates(self, articles: List[Article]) -> Dict[str, List[Article]]:
        """Group duplicate articles together"""
        groups = {}
        processed = set()
        
        for i, article in enumerate(articles):
            if i in processed:
                continue
                
            group_id = str(article.id)
            groups[group_id] = [article]
            processed.add(i)
            
            for j, other in enumerate(articles[i+1:], i+1):
                if j in processed:
                    continue
                    
                if self.is_duplicate(article, other):
                    groups[group_id].append(other)
                    processed.add(j)
                    other.is_duplicate_of = article.id
        
        return groups