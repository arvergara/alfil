import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from loguru import logger
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError

from config import settings
from models import Newsletter, Article
from classifier import NewsSection

class MailchimpManager:
    def __init__(self):
        self.client = None
        if settings.MAILCHIMP_API_KEY:
            self.client = MailchimpMarketing.Client()
            self.client.set_config({
                "api_key": settings.MAILCHIMP_API_KEY.get_secret_value(),
                "server": settings.MAILCHIMP_SERVER_PREFIX
            })
            self.template_id = settings.MAILCHIMP_TEMPLATE_ID
            self.list_id_asociados = settings.MAILCHIMP_LIST_ID_ASOCIADOS
            self.list_id_colaboradores = settings.MAILCHIMP_LIST_ID_COLABORADORES
        else:
            logger.warning("Mailchimp API key not configured")
    
    def create_campaign(self, newsletter: Newsletter, list_type: str = "asociados") -> Optional[str]:
        """Create a new campaign in Mailchimp"""
        if not self.client:
            logger.error("Mailchimp client not initialized")
            return None
        
        try:
            list_id = self.list_id_asociados if list_type == "asociados" else self.list_id_colaboradores
            
            # Get the latest campaign to replicate
            campaigns = self.client.campaigns.list(count=10, sort_field="send_time", sort_dir="DESC")
            base_campaign = None
            
            for campaign in campaigns.get('campaigns', []):
                if 'Monitoreo ACAFI' in campaign.get('settings', {}).get('subject_line', ''):
                    base_campaign = campaign
                    break
            
            # Create new campaign
            campaign_data = {
                "type": "regular",
                "recipients": {
                    "list_id": list_id
                },
                "settings": {
                    "subject_line": f"Monitoreo ACAFI - {newsletter.date.strftime('%d/%m/%Y')}",
                    "preview_text": "Resumen diario de noticias del sector financiero",
                    "title": f"Monitoreo ACAFI {newsletter.date.strftime('%Y-%m-%d')}",
                    "from_name": "ACAFI",
                    "reply_to": settings.GMAIL_SENDER_EMAIL,
                    "template_id": int(self.template_id) if self.template_id else None
                }
            }
            
            # If we have a base campaign, copy additional settings
            if base_campaign:
                campaign_data["settings"].update({
                    "from_name": base_campaign["settings"].get("from_name", "ACAFI"),
                    "reply_to": base_campaign["settings"].get("reply_to", settings.GMAIL_SENDER_EMAIL)
                })
            
            response = self.client.campaigns.create(campaign_data)
            campaign_id = response.get('id')
            
            logger.info(f"Created Mailchimp campaign: {campaign_id}")
            return campaign_id
            
        except ApiClientError as e:
            logger.error(f"Mailchimp API error creating campaign: {e.text}")
            return None
        except Exception as e:
            logger.error(f"Error creating Mailchimp campaign: {e}")
            return None
    
    def update_campaign_content(self, campaign_id: str, html_content: str, text_content: str) -> bool:
        """Update campaign content"""
        if not self.client:
            return False
        
        try:
            self.client.campaigns.set_content(
                campaign_id,
                {
                    "html": html_content,
                    "plain_text": text_content
                }
            )
            logger.info(f"Updated content for campaign {campaign_id}")
            return True
            
        except ApiClientError as e:
            logger.error(f"Mailchimp API error updating content: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Error updating campaign content: {e}")
            return False
    
    def send_test_email(self, campaign_id: str, test_emails: List[str] = None) -> bool:
        """Send test email"""
        if not self.client:
            return False
        
        test_emails = test_emails or settings.NEWSLETTER_TEST_EMAILS
        
        try:
            self.client.campaigns.send_test_email(
                campaign_id,
                {
                    "test_emails": test_emails,
                    "send_type": "html"
                }
            )
            logger.info(f"Sent test email for campaign {campaign_id} to {test_emails}")
            return True
            
        except ApiClientError as e:
            logger.error(f"Mailchimp API error sending test: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return False
    
    def send_campaign(self, campaign_id: str) -> bool:
        """Send the campaign to the list"""
        if not self.client:
            return False
        
        try:
            self.client.campaigns.send(campaign_id)
            logger.info(f"Sent campaign {campaign_id}")
            return True
            
        except ApiClientError as e:
            logger.error(f"Mailchimp API error sending campaign: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Error sending campaign: {e}")
            return False
    
    def schedule_campaign(self, campaign_id: str, send_time: datetime) -> bool:
        """Schedule campaign for later sending"""
        if not self.client:
            return False
        
        try:
            self.client.campaigns.schedule(
                campaign_id,
                {
                    "schedule_time": send_time.isoformat()
                }
            )
            logger.info(f"Scheduled campaign {campaign_id} for {send_time}")
            return True
            
        except ApiClientError as e:
            logger.error(f"Mailchimp API error scheduling campaign: {e.text}")
            return False
        except Exception as e:
            logger.error(f"Error scheduling campaign: {e}")
            return False

class NewsletterComposer:
    """Compose HTML and text content for newsletter"""
    
    def __init__(self):
        self.template = self._load_template()
    
    def _load_template(self) -> str:
        """Load HTML template"""
        # This would load from file, but for now we'll use a basic template
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Helvetica, Arial, sans-serif; font-size: 12pt; }
        .header { background-color: #004B87; color: white; padding: 20px; }
        .section { margin: 20px 0; }
        .section-title { color: #004B87; font-weight: bold; font-size: 14pt; margin: 15px 0; }
        .article { margin: 10px 0; }
        .article-title { font-weight: bold; }
        .article-source { color: #666; font-style: italic; }
        .footer { background-color: #f0f0f0; padding: 20px; margin-top: 30px; }
        .indicators { background-color: #f9f9f9; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Monitoreo ACAFI</h1>
        <p>{date}</p>
    </div>
    
    <div class="section">
        <p>{editorial_summary}</p>
    </div>
    
    <div class="indicators">
        <div class="section-title">Indicadores Económicos</div>
        {indicators}
    </div>
    
    {sections}
    
    <div class="footer">
        <p>ACAFI - Asociación Chilena de Administradoras de Fondos de Inversión</p>
        <p><a href="https://www.acafi.cl">www.acafi.cl</a></p>
    </div>
</body>
</html>
"""
    
    def compose_newsletter(
        self,
        editorial_summary: str,
        indicators: Dict[str, str],
        articles_by_section: Dict[NewsSection, List[Tuple[Article, str]]]
    ) -> Tuple[str, str]:
        """Compose HTML and text versions of newsletter"""
        
        # Format indicators
        indicators_html = self._format_indicators_html(indicators)
        
        # Format sections
        sections_html = self._format_sections_html(articles_by_section)
        
        # Compose HTML
        html_content = self.template.format(
            date=datetime.now().strftime("%d de %B de %Y"),
            editorial_summary=editorial_summary.replace('\n', '<br>'),
            indicators=indicators_html,
            sections=sections_html
        )
        
        # Create text version
        text_content = self._create_text_version(
            editorial_summary,
            indicators,
            articles_by_section
        )
        
        return html_content, text_content
    
    def _format_indicators_html(self, indicators: Dict[str, str]) -> str:
        """Format economic indicators for HTML"""
        parts = []
        for key, value in indicators.items():
            parts.append(f"<strong>{key}:</strong> {value}")
        return " | ".join(parts)
    
    def _format_sections_html(self, articles_by_section: Dict[NewsSection, List[Tuple[Article, str]]]) -> str:
        """Format article sections for HTML"""
        sections_html = []
        
        for section, articles_with_summaries in articles_by_section.items():
            # Skip empty sections or ACAFI section if no articles
            if not articles_with_summaries:
                continue
            
            if section == NewsSection.ACAFI and not articles_with_summaries:
                continue  # Skip ACAFI section if empty
            
            section_html = f'<div class="section">'
            section_html += f'<div class="section-title">{section.value}</div>'
            
            for article, summary in articles_with_summaries[:settings.NEWSLETTER_MAX_ARTICLES_PER_SECTION]:
                section_html += f'''
                <div class="article">
                    <div class="article-title">{article.title}</div>
                    <div class="article-source">{article.source} - {article.published_at.strftime("%d/%m/%Y")}</div>
                    <p>{summary}</p>
                    <a href="{article.url}">Leer más</a>
                </div>
                '''
            
            section_html += '</div>'
            sections_html.append(section_html)
        
        return '\n'.join(sections_html)
    
    def _create_text_version(
        self,
        editorial_summary: str,
        indicators: Dict[str, str],
        articles_by_section: Dict[NewsSection, List[Tuple[Article, str]]]
    ) -> str:
        """Create plain text version of newsletter"""
        lines = []
        
        # Header
        lines.append("MONITOREO ACAFI")
        lines.append(f"{datetime.now().strftime('%d de %B de %Y')}")
        lines.append("=" * 50)
        lines.append("")
        
        # Editorial
        lines.append(editorial_summary)
        lines.append("")
        
        # Indicators
        lines.append("INDICADORES ECONÓMICOS")
        lines.append("-" * 30)
        for key, value in indicators.items():
            lines.append(f"{key}: {value}")
        lines.append("")
        
        # Sections
        for section, articles_with_summaries in articles_by_section.items():
            if not articles_with_summaries:
                continue
                
            lines.append(section.value.upper())
            lines.append("-" * 30)
            
            for article, summary in articles_with_summaries[:settings.NEWSLETTER_MAX_ARTICLES_PER_SECTION]:
                lines.append(f"• {article.title}")
                lines.append(f"  {article.source} - {article.published_at.strftime('%d/%m/%Y')}")
                lines.append(f"  {summary}")
                lines.append(f"  Leer más: {article.url}")
                lines.append("")
        
        # Footer
        lines.append("=" * 50)
        lines.append("ACAFI - Asociación Chilena de Administradoras de Fondos de Inversión")
        lines.append("www.acafi.cl")
        
        return '\n'.join(lines)