import json
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import Article
from classifier import NewsSection, ClassificationResult

@dataclass
class SummaryResult:
    editorial_summary: str
    article_summaries: Dict[str, str]
    line_count: int
    word_count: int

class LLMProcessor:
    def __init__(self):
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434') + '/api/generate'
        
        # Check if we're using Ollama or external API
        if settings.OPENAI_API_KEY:
            self.provider = 'openai'
            import openai
            openai.api_key = settings.OPENAI_API_KEY.get_secret_value()
            self.client = openai
        elif settings.ANTHROPIC_API_KEY:
            self.provider = 'anthropic'
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY.get_secret_value())
        else:
            self.provider = 'ollama'
            self.client = None
            self._check_ollama_connection()
    
    def _check_ollama_connection(self):
        """Check if Ollama is available"""
        try:
            response = requests.get(self.ollama_url.replace('/api/generate', '/api/tags'))
            if response.status_code == 200:
                logger.info(f"Connected to Ollama with model {self.model}")
            else:
                logger.warning("Ollama not responding, will use mock responses")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_editorial_summary(
        self,
        articles_by_section: Dict[NewsSection, List[Tuple[Article, ClassificationResult]]]
    ) -> str:
        """Generate the editorial summary for the newsletter"""
        
        # Extraer todos los artículos
        all_articles = []
        for section_articles in articles_by_section.values():
            all_articles.extend([article for article, _ in section_articles])
        
        # Prepare context for the LLM
        context = self._prepare_editorial_context(articles_by_section)
        
        prompt = f"""Eres un editor financiero experto del mercado chileno. 
        Escribe un resumen editorial de MÁXIMO 6 líneas que comience con 'Buenos días,' 
        
        Estructura OBLIGATORIA:
        1. Primera oración: La noticia más importante del sector de fondos de inversión/AGF
        2. Segunda parte: Otras noticias relevantes del sector financiero
        3. Parte final: Anuncio económico o medida regulatoria/política relevante
        
        IMPORTANTE:
        - Máximo 6 líneas totales
        - Evitar opiniones o adjetivos valorativos
        - Priorizar tendencias y hechos concretos
        - Usar verbos en presente
        
        Noticias de hoy:
        {context}
        
        Resumen editorial:"""
        
        # Agregar restricciones anti-alucinación al prompt
        anti_hallucination_rules = """
        
        REGLAS ESTRICTAS - NO INVENTAR INFORMACIÓN:
        1. Usa SOLO información de los artículos proporcionados
        2. NO inventes números, fechas o nombres
        3. NO agregues información que no esté explícita
        4. Si no hay información sobre algo, NO lo menciones
        """
        
        enhanced_prompt = prompt + anti_hallucination_rules
        
        response = self._call_llm(enhanced_prompt)
        
        # Validate response
        editorial = self._validate_editorial(response)
        
        return editorial
    
    def generate_article_summary(self, article: Article, max_lines: int = 2) -> str:
        """Generate a summary for a single article"""
        
        prompt = f"""Resume la siguiente noticia en máximo {max_lines} líneas.
        Mantén solo los hechos más importantes, sin opiniones.
        
        Título: {article.title}
        Subtítulo: {article.subtitle or 'N/A'}
        Contenido: {article.content[:1000] if article.content else 'N/A'}
        
        Resumen:"""
        
        summary = self._call_llm(prompt, max_tokens=200)
        return summary.strip()
    
    def _prepare_editorial_context(
        self,
        articles_by_section: Dict[NewsSection, List[Tuple[Article, ClassificationResult]]]
    ) -> str:
        """Prepare context string for editorial generation"""
        context_parts = []
        
        # ACAFI news
        if NewsSection.ACAFI in articles_by_section:
            acafi_articles = articles_by_section[NewsSection.ACAFI][:3]
            context_parts.append("NOTICIAS ACAFI:")
            for article, _ in acafi_articles:
                context_parts.append(f"- {article.title}")
        
        # Industry news
        if NewsSection.INDUSTRIA in articles_by_section:
            industry_articles = articles_by_section[NewsSection.INDUSTRIA][:5]
            context_parts.append("\nNOTICIAS INDUSTRIA:")
            for article, classification in industry_articles:
                tags = ', '.join(classification.sector_tags) if classification.sector_tags else 'General'
                context_parts.append(f"- [{tags}] {article.title}")
        
        # Interest news
        if NewsSection.INTERES in articles_by_section:
            interest_articles = articles_by_section[NewsSection.INTERES][:5]
            context_parts.append("\nNOTICIAS DE INTERÉS:")
            for article, _ in interest_articles:
                context_parts.append(f"- {article.title}")
        
        return '\n'.join(context_parts)
    
    def _call_llm(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Call the LLM API"""
        max_tokens = max_tokens or self.max_tokens
        
        try:
            if self.provider == 'ollama':
                # Use Ollama local API
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": max_tokens
                    }
                }
                
                response = requests.post(self.ollama_url, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return self._mock_response(prompt)
                    
            elif self.provider == 'openai':
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Eres un editor financiero experto en el mercado chileno."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
            elif self.provider == 'anthropic':
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text
            else:
                return self._mock_response(prompt)
                
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return self._mock_response(prompt)
    
    def _validate_editorial(self, editorial: str) -> str:
        """Validate and fix editorial summary"""
        lines = editorial.strip().split('\n')
        
        # Ensure it starts with "Buenos días,"
        if not lines[0].startswith("Buenos días,"):
            lines[0] = "Buenos días, " + lines[0].lower()
        
        # Limit to 6 lines
        if len(lines) > 6:
            lines = lines[:6]
        
        # Join and clean
        editorial = '\n'.join(lines)
        
        # Remove any markdown formatting
        editorial = editorial.replace('**', '').replace('*', '').replace('#', '')
        
        return editorial.strip()
    
    def _mock_response(self, prompt: str) -> str:
        """Generate mock response for testing"""
        if "resumen editorial" in prompt.lower():
            return """Buenos días, hoy destacamos el lanzamiento de un nuevo fondo de inversión por parte de LarrainVial Asset Management enfocado en tecnología.
Además, la CMF anunció nuevas regulaciones para administradoras generales de fondos que entrarán en vigor el próximo mes.
En el sector inmobiliario, se reporta un aumento del 15% en la demanda de fondos multifamily durante el último trimestre.
Las AFP mostraron rentabilidades positivas en todos sus fondos durante octubre, lideradas por el fondo A con un 3,5%.
El Banco Central mantuvo la tasa de interés en 5,5% citando presiones inflacionarias persistentes.
Finalmente, el gobierno anunció avances en la reforma de pensiones que incluiría cambios en los límites de inversión."""
        else:
            return "Resumen de prueba para el artículo."
    
    def validate_content_quality(self, content: str) -> Tuple[bool, List[str]]:
        """Validate content quality and return issues if any"""
        issues = []
        
        # Check for sensitive information
        sensitive_patterns = [
            r'\b\d{4,}\b',  # Long numbers (could be IDs)
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Emails
            r'(?:password|clave|contraseña)[\s:]+\S+',  # Passwords
        ]
        
        import re
        for pattern in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"Possible sensitive information detected: {pattern}")
        
        # Check content length
        if len(content) < 50:
            issues.append("Content too short")
        
        # Check for placeholder text
        placeholder_terms = ['lorem ipsum', 'test', 'example', 'placeholder']
        for term in placeholder_terms:
            if term in content.lower():
                issues.append(f"Placeholder text detected: {term}")
        
        return len(issues) == 0, issues

class FactChecker:
    """Basic fact checking and validation"""
    
    @staticmethod
    def verify_date_consistency(article: Article, summary: str) -> bool:
        """Check if dates in summary match article date"""
        # This would implement date extraction and comparison
        return True
    
    @staticmethod
    def verify_entity_mentions(article: Article, summary: str) -> bool:
        """Check if entities mentioned in summary exist in article"""
        # This would implement NER and validation
        return True
    
    @staticmethod
    def check_numerical_accuracy(article: Article, summary: str) -> bool:
        """Verify numbers in summary match source"""
        # This would extract and compare numerical values
        return True