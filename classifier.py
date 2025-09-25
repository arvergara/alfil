import re
import json
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from models import Article, KeywordRule
from config import settings

class NewsSection(Enum):
    INDICADORES = "Indicadores Económicos"
    ACAFI = "ACAFI"
    INDUSTRIA = "Temas Industria"
    INTERES = "Noticias de Interés"
    SOCIOS = "Noticias de Socios"

@dataclass
class ClassificationResult:
    section: NewsSection
    confidence: float
    matched_keywords: List[str]
    sector_tags: List[str]
    is_partner_new_fund: bool
    mentions_acafi: bool

class NewsClassifier:
    def __init__(self, keywords_file: str = None):
        self.keywords_file = keywords_file or settings.KEYWORDS_FILE
        self.keyword_rules = self._load_keywords()
        self.section_patterns = self._compile_patterns()
        
    def _load_keywords(self) -> Dict[str, List[KeywordRule]]:
        """Load keywords from Excel file"""
        try:
            df = pd.read_excel(self.keywords_file, sheet_name=settings.CLIENT_NAME)
            rules = {}
            
            # Skip header rows and process data
            for idx, row in df.iterrows():
                if idx < 2:  # Skip header rows
                    continue
                    
                section = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
                theme = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                keywords_str = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
                media = str(row.iloc[3]) if pd.notna(row.iloc[3]) else "Todos"
                
                if section and keywords_str:
                    # Clean and parse keywords
                    keywords = self._parse_keywords(keywords_str)
                    
                    if section not in rules:
                        rules[section] = []
                    
                    rules[section].append({
                        'theme': theme,
                        'keywords': keywords,
                        'media': media,
                        'pattern': self._create_pattern(keywords)
                    })
            
            return rules
            
        except Exception as e:
            logger.error(f"Error loading keywords: {e}")
            return self._get_default_keywords()
    
    def _parse_keywords(self, keywords_str: str) -> List[str]:
        """Parse keyword string into list"""
        # Remove quotes and split by pipe
        keywords_str = keywords_str.replace('"', '').replace("'", '')
        keywords = [k.strip() for k in keywords_str.split('|') if k.strip()]
        return keywords
    
    def _create_pattern(self, keywords: List[str]) -> re.Pattern:
        """Create regex pattern from keywords"""
        # Escape special regex characters and create pattern
        escaped_keywords = [re.escape(k) for k in keywords]
        pattern_str = '|'.join(escaped_keywords)
        return re.compile(pattern_str, re.IGNORECASE)
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for each section"""
        patterns = {}
        
        # ACAFI mentions
        patterns['acafi'] = re.compile(
            r'\b(acafi|asociación\s+chilena\s+de\s+administradoras?\s+de\s+fondos\s+de\s+inversión)\b',
            re.IGNORECASE
        )
        
        # Industry patterns
        patterns['fondos'] = re.compile(
            r'\b(fondo[s]?\s+de\s+inversión|venture\s+capital|private\s+equity|deuda\s+privada|'
            r'renta\s+fija|AGF|administradora[s]?\s+general(es)?\s+de\s+fondos|gestora[s]?\s+de\s+fondos)\b',
            re.IGNORECASE
        )
        
        patterns['inmobiliario'] = re.compile(
            r'\b(industria\s+inmobiliaria|inmobiliario[s]?|multifamily|fondo[s]?\s+inmobiliario[s]?)\b',
            re.IGNORECASE
        )
        
        patterns['pensiones'] = re.compile(
            r'\b(AFP|administradora[s]?\s+de\s+fondos\s+de\s+pensiones|reforma\s+de\s+pensiones)\b',
            re.IGNORECASE
        )
        
        patterns['seguros'] = re.compile(
            r'\b(compañía[s]?\s+de\s+seguros|aseguradora[s]?|industry\s+aseguradora)\b',
            re.IGNORECASE
        )
        
        patterns['otros_instrumentos'] = re.compile(
            r'\b(fondos\s+mutuos|bonos|bolsa\s+de\s+comercio|bolsa\s+electrónica|IPSA)\b',
            re.IGNORECASE
        )
        
        patterns['normativas'] = re.compile(
            r'\b(reforma\s+tributaria|pacto\s+fiscal|CMF|comisión\s+para\s+el\s+mercado\s+financiero|'
            r'permisología|permisos\s+sectoriales)\b',
            re.IGNORECASE
        )
        
        patterns['innovacion'] = re.compile(
            r'\b(ronda[s]?\s+de\s+inversiones|fintech|insurtech|startup[s]?|corfo)\b',
            re.IGNORECASE
        )
        
        patterns['macro'] = re.compile(
            r'\b(IPC|índice\s+de\s+precios|desempleo|tasa\s+de\s+desempleo|inflación)\b',
            re.IGNORECASE
        )
        
        patterns['energia_mineria'] = re.compile(
            r'\b(energías?\s+(renovables?|favorables)|litio|hidrógeno\s+verde|royalty\s+minero|codelco)\b',
            re.IGNORECASE
        )
        
        patterns['nuevo_fondo'] = re.compile(
            r'\b(lanza(r|miento)?\s+(de\s+)?nuevo\s+fondo|nuevo\s+fondo\s+de\s+inversión|'
            r'crea(r|ción)?\s+(de\s+)?fondo|levanta(r|miento)?\s+(de\s+)?capital)\b',
            re.IGNORECASE
        )
        
        return patterns
    
    def classify(self, article: Article) -> ClassificationResult:
        """Classify an article into sections"""
        text = f"{article.title} {article.subtitle or ''} {article.content or ''}"
        
        # Check for ACAFI mentions
        mentions_acafi = bool(self.section_patterns['acafi'].search(text))
        
        # Check for new fund from partners
        is_partner_new_fund = bool(self.section_patterns['nuevo_fondo'].search(text))
        
        # Determine section and tags
        section = NewsSection.INTERES  # Default
        confidence = 0.5
        matched_keywords = []
        sector_tags = []
        
        # Priority 1: ACAFI mentions
        if mentions_acafi:
            section = NewsSection.ACAFI
            confidence = 0.95
            matched_keywords.append("ACAFI")
        
        # Priority 2: Check keyword rules
        for section_name, rules in self.keyword_rules.items():
            for rule in rules:
                if rule['pattern'].search(text):
                    matched_keywords.extend(rule['keywords'])
                    
                    if 'Indicadores' in section_name:
                        section = NewsSection.INDICADORES
                        confidence = 0.9
                    elif 'ACAFI' in section_name.upper():
                        section = NewsSection.ACAFI
                        confidence = max(confidence, 0.9)
                    elif 'Industria' in section_name:
                        section = NewsSection.INDUSTRIA
                        confidence = max(confidence, 0.85)
                        sector_tags.append(rule['theme'])
                    elif 'Interés' in section_name:
                        section = NewsSection.INTERES
                        confidence = max(confidence, 0.8)
        
        # Check for partner new fund (special case)
        if is_partner_new_fund and not mentions_acafi:
            section = NewsSection.SOCIOS
            confidence = 0.9
        
        # Additional sector tagging
        if self.section_patterns['fondos'].search(text):
            sector_tags.append("Fondos de Inversión")
        if self.section_patterns['inmobiliario'].search(text):
            sector_tags.append("Inmobiliario")
        if self.section_patterns['pensiones'].search(text):
            sector_tags.append("AFP")
        if self.section_patterns['seguros'].search(text):
            sector_tags.append("Seguros")
        if self.section_patterns['innovacion'].search(text):
            sector_tags.append("Innovación")
        if self.section_patterns['energia_mineria'].search(text):
            sector_tags.append("Energía/Minería")
        
        return ClassificationResult(
            section=section,
            confidence=confidence,
            matched_keywords=list(set(matched_keywords)),
            sector_tags=list(set(sector_tags)),
            is_partner_new_fund=is_partner_new_fund,
            mentions_acafi=mentions_acafi
        )
    
    def _get_default_keywords(self) -> Dict[str, List[Dict]]:
        """Return default keywords if file cannot be loaded"""
        return {
            "ACAFI": [{
                'theme': 'ACAFI',
                'keywords': ['acafi', 'asociación chilena de administradoras de fondos de inversión'],
                'media': 'Todos',
                'pattern': re.compile(r'\b(acafi|asociación\s+chilena)\b', re.IGNORECASE)
            }],
            "Temas Industria": [{
                'theme': 'Fondos',
                'keywords': ['fondo de inversión', 'venture capital', 'private equity'],
                'media': 'Todos',
                'pattern': re.compile(r'\b(fondo[s]?\s+de\s+inversión|venture\s+capital|private\s+equity)\b', re.IGNORECASE)
            }]
        }
    
    def prioritize_articles(self, articles: List[Tuple[Article, ClassificationResult]]) -> List[Tuple[Article, ClassificationResult]]:
        """Prioritize articles within each section"""
        # Sort by confidence and relevance
        prioritized = sorted(
            articles,
            key=lambda x: (
                x[1].mentions_acafi,  # ACAFI mentions first
                x[1].is_partner_new_fund,  # New funds second
                x[1].confidence,  # Then by confidence
                x[0].published_at  # Most recent
            ),
            reverse=True
        )
        
        return prioritized