#!/usr/bin/env python3
"""
Script de prueba para el agente de clipping sin necesidad de base de datos
"""
import asyncio
from datetime import datetime
import pandas as pd
from loguru import logger

from scraper import BancoCentralScraper
from classifier import NewsClassifier
from llm_processor import LLMProcessor

async def test_components():
    """Prueba los componentes principales del sistema"""
    
    print("="*60)
    print("PRUEBA DE COMPONENTES - CLIPPING AGENT ACAFI")
    print("="*60)
    
    # 1. Probar lectura de palabras clave
    print("\n1. PROBANDO CLASIFICADOR DE NOTICIAS")
    print("-"*40)
    try:
        classifier = NewsClassifier()
        
        # Artículo de prueba
        from models import Article
        test_article = Article(
            url="https://example.com/test",
            source="Diario Financiero",
            title="ACAFI lanza nuevo fondo de inversión para venture capital",
            subtitle="La asociación busca impulsar el ecosistema de startups",
            content="La Asociación Chilena de Administradoras de Fondos de Inversión (ACAFI) anunció hoy...",
            published_at=datetime.now()
        )
        
        result = classifier.classify(test_article)
        print(f"✓ Artículo clasificado como: {result.section.value}")
        print(f"  Confianza: {result.confidence:.2%}")
        print(f"  Menciona ACAFI: {result.mentions_acafi}")
        print(f"  Tags: {', '.join(result.sector_tags)}")
        
    except Exception as e:
        print(f"✗ Error en clasificador: {e}")
    
    # 2. Probar indicadores económicos
    print("\n2. PROBANDO SCRAPER DE BANCO CENTRAL")
    print("-"*40)
    try:
        bc_scraper = BancoCentralScraper()
        indicators = await bc_scraper.fetch_indicators()
        
        print("✓ Indicadores obtenidos:")
        for key, value in indicators.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"✗ Error obteniendo indicadores: {e}")
    
    # 3. Probar generación de resúmenes (si hay API key configurada)
    print("\n3. PROBANDO GENERADOR DE RESÚMENES LLM")
    print("-"*40)
    try:
        llm = LLMProcessor()
        
        if llm.client:
            summary = llm.generate_article_summary(test_article, max_lines=2)
            print(f"✓ Resumen generado: {summary}")
        else:
            print("⚠ LLM no configurado (falta API key)")
            print("  Usando respuestas mock para pruebas")
            
    except Exception as e:
        print(f"✗ Error en LLM: {e}")
    
    # 4. Verificar archivo de palabras clave
    print("\n4. VERIFICANDO ARCHIVO DE PALABRAS CLAVE")
    print("-"*40)
    try:
        file_path = '/Users/alfil/Mi unidad/0_Consultorias/Proyecta/Palabras_Claves.xlsx'
        df = pd.read_excel(file_path, sheet_name='ACAFI')
        
        print(f"✓ Archivo encontrado con {len(df)} filas")
        print(f"  Columnas: {list(df.columns)}")
        
        # Contar palabras clave
        keyword_count = 0
        for idx, row in df.iterrows():
            if idx >= 2 and pd.notna(row.iloc[2]):
                keywords = row.iloc[2].split('|')
                keyword_count += len(keywords)
        
        print(f"  Total de palabras clave: {keyword_count}")
        
    except Exception as e:
        print(f"✗ Error leyendo archivo: {e}")
    
    print("\n" + "="*60)
    print("PRUEBA COMPLETADA")
    print("="*60)
    
    print("\nSIGUIENTES PASOS:")
    print("1. Configurar las API keys en el archivo .env")
    print("2. Configurar Mailchimp con las listas correctas")
    print("3. Ejecutar el agente completo con: python main.py")

if __name__ == "__main__":
    asyncio.run(test_components())