import json
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from models import Article
from classifier import NewsSection, ClassificationResult

@dataclass
class SummaryResult:
    editorial_summary: str
    article_summaries: Dict[str, str]
    line_count: int
    word_count: int

class LLMProcessor:
    def __init__(self, model_name: str = "gpt-oss:20b"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        self.temperature = 0.3
        self.max_tokens = 2000
        
        # Verificar que Ollama está corriendo
        self.check_ollama_connection()
    
    def check_ollama_connection(self):
        """Verificar que Ollama está disponible"""
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                if self.model_name not in model_names:
                    print(f"⚠️  Modelo {self.model_name} no encontrado. Modelos disponibles: {model_names}")
                else:
                    print(f"✅ Conectado a Ollama con modelo {self.model_name}")
        except Exception as e:
            print(f"⚠️  No se pudo conectar a Ollama: {e}")
            print("   Asegúrate de que Ollama está corriendo: ollama serve")
    
    def generate_editorial_summary(
        self,
        articles_by_section: Dict[NewsSection, List[Tuple[Article, ClassificationResult]]]
    ) -> str:
        """Generate the editorial summary for the newsletter"""
        
        # Preparar contexto para el LLM
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
        
        response = self._call_ollama(prompt)
        
        # Validar respuesta
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
        
        summary = self._call_ollama(prompt)
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
    
    def _call_ollama(self, prompt: str) -> str:
        """Llamar a Ollama API"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens
                }
            }
            
            response = requests.post(self.ollama_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                print(f"Error llamando a Ollama: {response.status_code}")
                return self._mock_response(prompt)
                
        except Exception as e:
            print(f"Error llamando a Ollama: {e}")
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