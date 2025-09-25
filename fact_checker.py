"""
Sistema de verificación de hechos y prevención de alucinaciones
"""
import re
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from difflib import SequenceMatcher

from models import Article
from classifier import NewsSection

@dataclass
class FactCheckResult:
    is_valid: bool
    confidence: float
    issues: List[str]
    evidence: Dict[str, str]
    suggestions: List[str]

class FactChecker:
    """Verificador de hechos para prevenir alucinaciones del LLM"""
    
    def __init__(self):
        self.suspicious_patterns = [
            r'\b(?:anunció|confirmó|declaró|reveló)\b.*\b(?:ayer|hoy|esta mañana|esta tarde)\b',
            r'\b\d{3,}\s*(?:millones|mil millones|billones)\b',  # Números muy grandes
            r'\b(?:todos|ninguno|siempre|nunca|100%|0%)\b',  # Absolutos sospechosos
        ]
        
        self.known_entities = {
            'ACAFI': 'Asociación Chilena de Administradoras de Fondos de Inversión',
            'CMF': 'Comisión para el Mercado Financiero',
            'AFP': 'Administradoras de Fondos de Pensiones',
            'AGF': 'Administradora General de Fondos',
            'Banco Central': 'Banco Central de Chile',
        }
        
        self.valid_sources = [
            'Diario Financiero', 'El Mercurio', 'La Tercera', 'EMOL',
            'Funds Society', 'La Segunda', 'El Mercurio Inversiones'
        ]
    
    def verify_editorial_summary(
        self, 
        editorial: str, 
        articles: List[Article]
    ) -> FactCheckResult:
        """Verificar que el resumen editorial no contenga alucinaciones"""
        issues = []
        evidence = {}
        suggestions = []
        
        # Dividir el editorial en oraciones
        sentences = self._split_into_sentences(editorial)
        
        for sentence in sentences:
            # 1. Verificar que las entidades mencionadas existen en los artículos
            entities_valid, entity_issues = self._verify_entities(sentence, articles)
            if not entities_valid:
                issues.extend(entity_issues)
            
            # 2. Verificar fechas y tiempos
            dates_valid, date_issues = self._verify_dates(sentence, articles)
            if not dates_valid:
                issues.extend(date_issues)
            
            # 3. Verificar números y estadísticas
            numbers_valid, number_issues = self._verify_numbers(sentence, articles)
            if not numbers_valid:
                issues.extend(number_issues)
            
            # 4. Buscar patrones sospechosos
            if self._has_suspicious_patterns(sentence):
                issues.append(f"Patrón sospechoso detectado: '{sentence[:50]}...'")
        
        # 5. Verificar coherencia general
        coherence_score = self._check_coherence(editorial, articles)
        
        # 6. Verificar que no inventa noticias
        invented_news = self._check_for_invented_news(editorial, articles)
        if invented_news:
            issues.extend(invented_news)
        
        # Calcular confianza
        confidence = self._calculate_confidence(issues, coherence_score)
        
        # Generar sugerencias
        if issues:
            suggestions.append("Revisar y corregir los hechos mencionados")
            suggestions.append("Basarse únicamente en el contenido de los artículos fuente")
            suggestions.append("Evitar afirmaciones absolutas sin evidencia")
        
        return FactCheckResult(
            is_valid=len(issues) == 0,
            confidence=confidence,
            issues=issues,
            evidence=evidence,
            suggestions=suggestions
        )
    
    def verify_article_summary(
        self, 
        summary: str, 
        article: Article
    ) -> FactCheckResult:
        """Verificar que el resumen del artículo sea fiel al original"""
        issues = []
        evidence = {}
        
        # 1. Verificar que el resumen no agregue información nueva
        new_info = self._detect_new_information(summary, article)
        if new_info:
            issues.append(f"Información no presente en el artículo original: {new_info}")
        
        # 2. Verificar entidades mencionadas
        if not self._verify_entities_in_summary(summary, article):
            issues.append("Menciona entidades no presentes en el artículo")
        
        # 3. Verificar números
        if not self._verify_numbers_in_summary(summary, article):
            issues.append("Contiene números no mencionados en el artículo")
        
        # 4. Calcular similitud semántica
        similarity = self._calculate_similarity(summary, article.content or article.title)
        if similarity < 0.3:
            issues.append("El resumen parece no estar relacionado con el artículo")
        
        confidence = 1.0 - (len(issues) * 0.2)
        confidence = max(0.0, confidence)
        
        return FactCheckResult(
            is_valid=len(issues) == 0,
            confidence=confidence,
            issues=issues,
            evidence={'similarity': f"{similarity:.2%}"},
            suggestions=["Revisar que el resumen se base solo en el contenido del artículo"]
        )
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Dividir texto en oraciones"""
        # Simple split por puntos, signos de exclamación e interrogación
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _verify_entities(self, sentence: str, articles: List[Article]) -> Tuple[bool, List[str]]:
        """Verificar que las entidades mencionadas existen en los artículos"""
        issues = []
        
        # Buscar nombres propios (palabras que empiezan con mayúscula)
        entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', sentence)
        
        # Combinar todo el contenido de los artículos
        all_content = ' '.join([
            f"{a.title} {a.subtitle or ''} {a.content or ''}"
            for a in articles
        ])
        
        for entity in entities:
            # Ignorar entidades conocidas y comunes
            if entity in ['Buenos', 'El', 'La', 'Los', 'Las', 'Chile']:
                continue
                
            # Verificar si la entidad aparece en algún artículo
            if entity not in all_content and entity not in self.known_entities:
                # Buscar variaciones (ej: "LarrainVial" vs "Larrain Vial")
                entity_normalized = entity.replace(' ', '').lower()
                content_normalized = all_content.replace(' ', '').lower()
                
                if entity_normalized not in content_normalized:
                    issues.append(f"Entidad '{entity}' no encontrada en artículos fuente")
        
        return len(issues) == 0, issues
    
    def _verify_dates(self, sentence: str, articles: List[Article]) -> Tuple[bool, List[str]]:
        """Verificar que las fechas mencionadas son correctas"""
        issues = []
        
        # Buscar menciones de tiempo
        time_patterns = [
            (r'\bayer\b', timedelta(days=1)),
            (r'\bhoy\b', timedelta(days=0)),
            (r'\bmañana\b', timedelta(days=-1)),
            (r'\besta semana\b', timedelta(days=7)),
            (r'\beste mes\b', timedelta(days=30)),
        ]
        
        for pattern, delta in time_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                # Verificar que hay artículos de esa fecha
                expected_date = datetime.now() - delta
                has_article_from_date = any(
                    abs((a.published_at - expected_date).days) <= 1
                    for a in articles
                )
                
                if not has_article_from_date:
                    issues.append(f"Referencia temporal '{pattern}' sin artículos correspondientes")
        
        return len(issues) == 0, issues
    
    def _verify_numbers(self, sentence: str, articles: List[Article]) -> Tuple[bool, List[str]]:
        """Verificar que los números mencionados son correctos"""
        issues = []
        
        # Buscar números en el texto
        numbers = re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:%|millones?|mil|miles)?\b', sentence)
        
        # Combinar contenido de artículos
        all_content = ' '.join([
            f"{a.title} {a.subtitle or ''} {a.content or ''}"
            for a in articles
        ])
        
        for number in numbers:
            # Normalizar el número
            number_clean = re.sub(r'[^\d.,]', '', number)
            
            # Buscar el número en los artículos (con cierta tolerancia)
            if number_clean and len(number_clean) > 1:  # Ignorar números de un dígito
                if number_clean not in all_content:
                    # Buscar con variaciones (1.000 vs 1000, etc.)
                    number_variants = [
                        number_clean,
                        number_clean.replace('.', ''),
                        number_clean.replace(',', '.'),
                        number_clean.replace('.', ',')
                    ]
                    
                    found = any(v in all_content for v in number_variants)
                    if not found and float(number_clean.replace(',', '.')) > 100:
                        issues.append(f"Número '{number}' no verificado en fuentes")
        
        return len(issues) == 0, issues
    
    def _has_suspicious_patterns(self, text: str) -> bool:
        """Detectar patrones sospechosos de alucinación"""
        for pattern in self.suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _check_coherence(self, editorial: str, articles: List[Article]) -> float:
        """Verificar coherencia entre editorial y artículos"""
        # Crear un resumen de temas de los artículos
        article_themes = set()
        for article in articles:
            # Extraer palabras clave del título
            words = re.findall(r'\b\w+\b', article.title.lower())
            article_themes.update(words)
        
        # Verificar cuántas palabras del editorial están en los temas
        editorial_words = re.findall(r'\b\w+\b', editorial.lower())
        matching_words = sum(1 for word in editorial_words if word in article_themes)
        
        coherence = matching_words / len(editorial_words) if editorial_words else 0
        return min(1.0, coherence * 2)  # Escalar para ser más generoso
    
    def _check_for_invented_news(self, editorial: str, articles: List[Article]) -> List[str]:
        """Detectar si el editorial menciona noticias no presentes"""
        issues = []
        
        # Buscar patrones de noticias (sujeto + verbo de acción)
        news_patterns = re.findall(
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(anunció|lanzó|presentó|publicó|reportó)',
            editorial
        )
        
        all_content = ' '.join([
            f"{a.title} {a.subtitle or ''} {a.content or ''}"
            for a in articles
        ])
        
        for entity, action in news_patterns:
            # Verificar si esta combinación existe en algún artículo
            if f"{entity}" not in all_content:
                issues.append(f"Posible noticia inventada: '{entity} {action}...'")
        
        return issues
    
    def _detect_new_information(self, summary: str, article: Article) -> Optional[str]:
        """Detectar información nueva no presente en el artículo"""
        article_content = f"{article.title} {article.subtitle or ''} {article.content or ''}"
        
        # Buscar entidades en el resumen
        summary_entities = set(re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', summary))
        article_entities = set(re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', article_content))
        
        new_entities = summary_entities - article_entities - {'El', 'La', 'Los', 'Las'}
        
        if new_entities:
            return f"Entidades nuevas: {', '.join(new_entities)}"
        
        return None
    
    def _verify_entities_in_summary(self, summary: str, article: Article) -> bool:
        """Verificar que las entidades del resumen estén en el artículo"""
        article_content = f"{article.title} {article.subtitle or ''} {article.content or ''}"
        
        # Extraer entidades principales del resumen
        summary_entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', summary)
        
        for entity in summary_entities:
            if len(entity) > 3 and entity not in ['Chile', 'El', 'La', 'Los', 'Las']:
                if entity not in article_content:
                    return False
        
        return True
    
    def _verify_numbers_in_summary(self, summary: str, article: Article) -> bool:
        """Verificar que los números del resumen estén en el artículo"""
        article_content = f"{article.title} {article.subtitle or ''} {article.content or ''}"
        
        # Extraer números del resumen
        summary_numbers = re.findall(r'\b\d+(?:[.,]\d+)?\b', summary)
        
        for number in summary_numbers:
            if len(number) > 1:  # Ignorar números de un dígito
                if number not in article_content:
                    # Buscar variaciones
                    variants = [
                        number,
                        number.replace('.', ''),
                        number.replace(',', '.')
                    ]
                    if not any(v in article_content for v in variants):
                        return False
        
        return True
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcular similitud entre dos textos"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def _calculate_confidence(self, issues: List[str], coherence: float) -> float:
        """Calcular nivel de confianza basado en issues y coherencia"""
        # Empezar con coherencia como base
        confidence = coherence
        
        # Reducir por cada issue encontrado
        confidence -= len(issues) * 0.15
        
        # Asegurar que esté entre 0 y 1
        return max(0.0, min(1.0, confidence))

class HallucinationPreventer:
    """Sistema para prevenir alucinaciones en los prompts"""
    
    @staticmethod
    def enhance_prompt(prompt: str, articles: List[Article] = None) -> str:
        """Mejorar el prompt para reducir alucinaciones"""
        
        constraints = """
IMPORTANTE - REGLAS ESTRICTAS:
1. Basarte ÚNICAMENTE en la información proporcionada
2. NO inventar fechas, números o nombres
3. NO agregar información que no esté en los artículos
4. Si no tienes información sobre algo, NO lo menciones
5. Usar solo los datos exactos de las fuentes
6. NO hacer suposiciones o inferencias
7. Citar la fuente cuando sea posible
"""
        
        if articles:
            # Agregar contexto específico
            context = "\nARTÍCULOS FUENTE (usar SOLO esta información):\n"
            for i, article in enumerate(articles, 1):
                context += f"\n{i}. {article.title}"
                if article.subtitle:
                    context += f"\n   Subtítulo: {article.subtitle}"
                if article.content:
                    context += f"\n   Contenido: {article.content[:200]}..."
                context += f"\n   Fuente: {article.source}"
                context += "\n"
        else:
            context = ""
        
        return f"{constraints}\n{context}\n{prompt}"
    
    @staticmethod
    def create_verification_prompt(text: str) -> str:
        """Crear prompt para auto-verificación"""
        return f"""
Verifica el siguiente texto y responde:
1. ¿Contiene información no verificable? (Sí/No)
2. ¿Hay fechas o números específicos sin fuente? (Sí/No)
3. ¿Se hacen afirmaciones absolutas sin evidencia? (Sí/No)
4. ¿Hay entidades o nombres que parecen inventados? (Sí/No)

Texto a verificar:
{text}

Responde en formato JSON:
{{"verificable": true/false, "issues": ["lista de problemas encontrados"]}}
"""