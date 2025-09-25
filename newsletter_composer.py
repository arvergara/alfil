"""
Compositor de newsletter HTML sin dependencias de Mailchimp
"""
from datetime import datetime
from typing import List, Dict, Tuple
from models import Article
from classifier import NewsSection

class NewsletterComposer:
    """Compose HTML and text content for newsletter"""
    
    def __init__(self):
        self.template = self._load_template()
    
    def _load_template(self) -> str:
        """Load HTML template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: Helvetica, Arial, sans-serif; 
            font-size: 12pt; 
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background-color: #004B87; 
            color: white; 
            padding: 30px; 
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28pt;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 14pt;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .editorial {{
            background-color: #f9f9f9;
            padding: 20px;
            border-left: 4px solid #004B87;
            margin: 20px 0;
            font-style: italic;
            line-height: 1.6;
        }}
        .section {{ 
            margin: 30px 0; 
        }}
        .section-title {{ 
            color: #004B87; 
            font-weight: bold; 
            font-size: 16pt; 
            margin: 20px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .article {{ 
            margin: 20px 0; 
            padding: 15px;
            background-color: #fafafa;
            border-radius: 5px;
            transition: background-color 0.3s;
        }}
        .article:hover {{
            background-color: #f0f0f0;
        }}
        .article-title {{ 
            font-weight: bold; 
            color: #333;
            font-size: 13pt;
            margin-bottom: 5px;
        }}
        .article-source {{ 
            color: #666; 
            font-style: italic; 
            font-size: 10pt;
            margin-bottom: 10px;
        }}
        .article-summary {{
            color: #444;
            line-height: 1.5;
            margin: 10px 0;
        }}
        .article a {{
            color: #004B87;
            text-decoration: none;
            font-weight: 500;
        }}
        .article a:hover {{
            text-decoration: underline;
        }}
        .footer {{ 
            background-color: #f0f0f0; 
            padding: 30px; 
            margin-top: 30px;
            text-align: center;
            border-radius: 0 0 8px 8px;
        }}
        .footer p {{
            margin: 5px 0;
            color: #666;
        }}
        .indicators {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px; 
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .indicators-title {{
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 14pt;
        }}
        .indicators-content {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .indicator-item {{
            flex: 1;
            min-width: 150px;
        }}
        .indicator-label {{
            font-size: 10pt;
            opacity: 0.9;
            margin-bottom: 2px;
        }}
        .indicator-value {{
            font-size: 14pt;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Monitoreo ACAFI</h1>
            <p>{date}</p>
        </div>
        
        <div class="content">
            <div class="editorial">
                {editorial_summary}
            </div>
            
            <div class="indicators">
                <div class="indicators-title">Indicadores Económicos del Día</div>
                <div class="indicators-content">
                    {indicators}
                </div>
            </div>
            
            {sections}
        </div>
        
        <div class="footer">
            <p><strong>ACAFI</strong></p>
            <p>Asociación Chilena de Administradoras de Fondos de Inversión</p>
            <p><a href="https://www.acafi.cl">www.acafi.cl</a></p>
        </div>
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
        
        # Format date in Spanish
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        now = datetime.now()
        date_str = f"{now.day} de {months[now.month-1]} de {now.year}"
        
        # Format indicators
        indicators_html = self._format_indicators_html(indicators)
        
        # Format sections
        sections_html = self._format_sections_html(articles_by_section)
        
        # Compose HTML
        html_content = self.template.format(
            date=date_str,
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
        items = []
        for key, value in indicators.items():
            items.append(f"""
                <div class="indicator-item">
                    <div class="indicator-label">{key}</div>
                    <div class="indicator-value">{value}</div>
                </div>
            """)
        return ''.join(items)
    
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
            
            for article, summary in articles_with_summaries:
                section_html += f'''
                <div class="article">
                    <div class="article-title">{article.title}</div>
                    <div class="article-source">
                        {article.source} - {article.published_at.strftime("%d/%m/%Y")}
                    </div>
                    <div class="article-summary">{summary}</div>
                    <a href="{article.url}" target="_blank">Leer más →</a>
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
            
            for article, summary in articles_with_summaries:
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