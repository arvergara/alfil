#!/usr/bin/env python3
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from pathlib import Path

from loguru import logger
from sqlalchemy.orm import Session

from config import settings
from models import init_db, Article, Newsletter, NewsSource, LogEntry
from scraper import NewsScraper, BancoCentralScraper, DuplicateDetector
from classifier import NewsClassifier, NewsSection, ClassificationResult
from llm_processor import LLMProcessor
from mailchimp_integration import MailchimpManager, NewsletterComposer

# Configure logging
logger.add(
    settings.LOGS_DIR / "clipping_{time}.log",
    rotation="1 day",
    retention="30 days",
    level=settings.LOG_LEVEL
)

class ClippingAgent:
    def __init__(self):
        self.db_session = init_db(settings.DATABASE_URL)
        self.scraper = NewsScraper()
        self.bc_scraper = BancoCentralScraper()
        self.classifier = NewsClassifier()
        self.llm_processor = LLMProcessor()
        self.duplicate_detector = DuplicateDetector()
        self.mailchimp = MailchimpManager()
        self.composer = NewsletterComposer()
        
    async def run_daily_clipping(self, date: datetime = None) -> Newsletter:
        """Main orchestration method for daily clipping"""
        date = date or datetime.now()
        logger.info(f"Starting daily clipping for {date.strftime('%Y-%m-%d')}")
        
        # Create newsletter entry
        newsletter = Newsletter(date=date, status='draft')
        
        try:
            # Step 1: Fetch news articles
            logger.info("Step 1: Fetching news articles")
            articles = await self._fetch_all_articles(date)
            newsletter.logs.append(LogEntry(
                level="INFO",
                message=f"Fetched {len(articles)} articles",
                details=json.dumps({"count": len(articles)})
            ))
            
            # Step 2: Deduplicate articles
            logger.info("Step 2: Deduplicating articles")
            unique_articles = self._deduplicate_articles(articles)
            newsletter.logs.append(LogEntry(
                level="INFO",
                message=f"Deduplicated to {len(unique_articles)} unique articles",
                details=json.dumps({"original": len(articles), "unique": len(unique_articles)})
            ))
            
            # Step 3: Classify articles
            logger.info("Step 3: Classifying articles")
            classified_articles = self._classify_articles(unique_articles)
            
            # Step 4: Generate summaries
            logger.info("Step 4: Generating summaries")
            articles_with_summaries = await self._generate_summaries(classified_articles)
            
            # Step 5: Fetch economic indicators
            logger.info("Step 5: Fetching economic indicators")
            indicators = await self.bc_scraper.fetch_indicators()
            newsletter.economic_indicators = json.dumps(indicators)
            
            # Step 6: Generate editorial summary
            logger.info("Step 6: Generating editorial summary")
            editorial = self.llm_processor.generate_editorial_summary(classified_articles)
            newsletter.editorial_summary = editorial
            
            # Step 7: Compose newsletter
            logger.info("Step 7: Composing newsletter")
            html_content, text_content = self.composer.compose_newsletter(
                editorial,
                indicators,
                articles_with_summaries
            )
            newsletter.html_body = html_content
            newsletter.text_body = text_content
            
            # Step 8: Create and send via Mailchimp
            logger.info("Step 8: Sending via Mailchimp")
            await self._send_newsletter(newsletter)
            
            # Save to database
            with self.db_session() as session:
                session.add(newsletter)
                session.commit()
            
            logger.info(f"Successfully completed daily clipping for {date.strftime('%Y-%m-%d')}")
            return newsletter
            
        except Exception as e:
            logger.error(f"Error in daily clipping: {e}")
            newsletter.status = 'error'
            newsletter.logs.append(LogEntry(
                level="ERROR",
                message=f"Fatal error: {str(e)}",
                details=json.dumps({"error": str(e)})
            ))
            
            with self.db_session() as session:
                session.add(newsletter)
                session.commit()
            
            raise
    
    async def _fetch_all_articles(self, date: datetime) -> List[Article]:
        """Fetch articles from all configured sources"""
        articles = []
        
        # Determine date range
        if date.weekday() == 0:  # Monday
            start_date = date - timedelta(days=3)  # Friday
        else:
            start_date = date - timedelta(days=1)
        
        # Fetch from each source
        with self.db_session() as session:
            sources = session.query(NewsSource).filter_by(is_active=True).all()
            
            for source in sources:
                try:
                    source_articles = await self.scraper.scrape_news_source(source)
                    
                    # Filter by date range
                    filtered = [
                        a for a in source_articles
                        if start_date <= a.published_at <= date
                    ]
                    
                    articles.extend(filtered)
                    
                    # Update last scraped time
                    source.last_scraped = datetime.utcnow()
                    session.commit()
                    
                except Exception as e:
                    logger.error(f"Error scraping {source.name}: {e}")
        
        return articles
    
    def _deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """Remove duplicate articles"""
        duplicate_groups = self.duplicate_detector.find_duplicates(articles)
        
        # Keep only the first article from each group
        unique_articles = []
        for group_id, group_articles in duplicate_groups.items():
            # Prefer articles from higher priority sources
            group_articles.sort(key=lambda a: self._get_source_priority(a.source), reverse=True)
            unique_articles.append(group_articles[0])
        
        return unique_articles
    
    def _get_source_priority(self, source: str) -> int:
        """Get priority score for a news source"""
        priority_map = {
            'df.cl': 10,
            'elmercurio.com': 9,
            'latercera.com': 8,
            'emol.com': 7,
            'fundssociety.com': 6,
        }
        
        for domain, priority in priority_map.items():
            if domain in source.lower():
                return priority
        
        return 0
    
    def _classify_articles(self, articles: List[Article]) -> Dict[NewsSection, List[Tuple[Article, ClassificationResult]]]:
        """Classify articles into sections"""
        classified = {
            NewsSection.INDICADORES: [],
            NewsSection.ACAFI: [],
            NewsSection.INDUSTRIA: [],
            NewsSection.INTERES: [],
            NewsSection.SOCIOS: []
        }
        
        for article in articles:
            classification = self.classifier.classify(article)
            
            # Update article with classification results
            article.section_detected = classification.section.value
            article.sector_tags = json.dumps(classification.sector_tags)
            article.mentions_acafi = classification.mentions_acafi
            article.is_partner_new_fund = classification.is_partner_new_fund
            article.relevance_score = classification.confidence
            
            classified[classification.section].append((article, classification))
        
        # Prioritize within each section
        for section in classified:
            classified[section] = self.classifier.prioritize_articles(classified[section])
        
        return classified
    
    async def _generate_summaries(
        self,
        classified_articles: Dict[NewsSection, List[Tuple[Article, ClassificationResult]]]
    ) -> Dict[NewsSection, List[Tuple[Article, str]]]:
        """Generate summaries for articles"""
        articles_with_summaries = {}
        
        for section, articles_classifications in classified_articles.items():
            summaries = []
            
            for article, classification in articles_classifications[:settings.NEWSLETTER_MAX_ARTICLES_PER_SECTION]:
                # Generate summary if not already present
                if not article.summary:
                    article.summary = self.llm_processor.generate_article_summary(article)
                
                summaries.append((article, article.summary))
            
            articles_with_summaries[section] = summaries
        
        return articles_with_summaries
    
    async def _send_newsletter(self, newsletter: Newsletter) -> bool:
        """Send newsletter via Mailchimp"""
        try:
            # Create campaign for Asociados
            campaign_id_asociados = self.mailchimp.create_campaign(newsletter, "asociados")
            if campaign_id_asociados:
                # Update content
                self.mailchimp.update_campaign_content(
                    campaign_id_asociados,
                    newsletter.html_body,
                    newsletter.text_body
                )
                
                # Send test
                if self.mailchimp.send_test_email(campaign_id_asociados):
                    newsletter.mailchimp_test_sent_to = json.dumps(settings.NEWSLETTER_TEST_EMAILS)
                    logger.info("Test email sent successfully")
                    
                    # Send campaign
                    if self.mailchimp.send_campaign(campaign_id_asociados):
                        newsletter.mailchimp_campaign_id = campaign_id_asociados
                        newsletter.mailchimp_sent_at = datetime.utcnow()
                        newsletter.status = 'sent'
                        logger.info("Campaign sent successfully to Asociados")
            
            # Create campaign for Colaboradores
            campaign_id_colaboradores = self.mailchimp.create_campaign(newsletter, "colaboradores")
            if campaign_id_colaboradores:
                self.mailchimp.update_campaign_content(
                    campaign_id_colaboradores,
                    newsletter.html_body,
                    newsletter.text_body
                )
                
                if self.mailchimp.send_campaign(campaign_id_colaboradores):
                    logger.info("Campaign sent successfully to Colaboradores")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending newsletter: {e}")
            newsletter.status = 'error'
            return False

async def main():
    """Main entry point"""
    agent = ClippingAgent()
    
    # Run daily clipping
    newsletter = await agent.run_daily_clipping()
    
    logger.info(f"Newsletter created with status: {newsletter.status}")
    
    # Print summary
    print(f"""
    ========================================
    CLIPPING AGENT - EXECUTION SUMMARY
    ========================================
    Date: {newsletter.date.strftime('%Y-%m-%d')}
    Status: {newsletter.status}
    Campaign ID: {newsletter.mailchimp_campaign_id or 'N/A'}
    Test Emails: {newsletter.mailchimp_test_sent_to or 'N/A'}
    
    Editorial Summary:
    {newsletter.editorial_summary or 'N/A'}
    
    ========================================
    """)

if __name__ == "__main__":
    asyncio.run(main())