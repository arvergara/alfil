#!/usr/bin/env python3
"""
Script de prueba para el agente de clipping usando Ollama
"""
import sys
import os
import pandas as pd
from datetime import datetime

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Reemplazar el procesador LLM original con la versión de Ollama
import llm_processor_ollama as llm_processor
sys.modules['llm_processor'] = llm_processor

from models import Article
from classifier import NewsClassifier, NewsSection
from llm_processor_ollama import LLMProcessor

def test_ollama_integration():
    """Prueba la integración con Ollama"""
    
    print("="*60)
    print("PRUEBA DE CLIPPING AGENT CON OLLAMA")
    print("="*60)
    
    # 1. Verificar Ollama
    print("\n1. VERIFICANDO OLLAMA")
    print("-"*40)
    llm = LLMProcessor(model_name="gpt-oss:20b")
    
    # 2. Probar clasificación de noticias
    print("\n2. PROBANDO CLASIFICADOR")
    print("-"*40)
    
    try:
        # Cargar palabras clave
        keywords_file = '/Users/alfil/Mi unidad/0_Consultorias/Proyecta/Palabras_Claves.xlsx'
        
        # Verificar que el archivo existe
        if not os.path.exists(keywords_file):
            print(f"❌ No se encuentra el archivo: {keywords_file}")
            return
            
        classifier = NewsClassifier(keywords_file=keywords_file)
        
        # Crear artículos de prueba
        test_articles = [
            Article(
                url="https://df.cl/test1",
                source="Diario Financiero",
                title="ACAFI y LarrainVial lanzan nuevo fondo de venture capital",
                subtitle="Inversión inicial de US$100 millones",
                content="La Asociación Chilena de Administradoras de Fondos de Inversión (ACAFI) junto a LarrainVial Asset Management anunciaron hoy el lanzamiento de un nuevo fondo de venture capital...",
                published_at=datetime.now()
            ),
            Article(
                url="https://elmercurio.com/test2",
                source="El Mercurio",
                title="Banco Central mantiene tasa de interés en 5,5%",
                subtitle="Decisión unánime del consejo",
                content="El Banco Central de Chile decidió mantener la tasa de política monetaria en 5,5% citando presiones inflacionarias...",
                published_at=datetime.now()
            ),
            Article(
                url="https://latercera.com/test3",
                source="La Tercera",
                title="Fondos inmobiliarios muestran recuperación en tercer trimestre",
                subtitle="Rentabilidad promedio alcanza 8% anual",
                content="Los fondos de inversión inmobiliaria y multifamily mostraron una significativa recuperación durante el tercer trimestre del año...",
                published_at=datetime.now()
            )
        ]
        
        # Clasificar artículos
        classified = {}
        for article in test_articles:
            result = classifier.classify(article)
            if result.section not in classified:
                classified[result.section] = []
            classified[result.section].append((article, result))
            
            print(f"\n📰 {article.title[:60]}...")
            print(f"   Sección: {result.section.value}")
            print(f"   Confianza: {result.confidence:.0%}")
            print(f"   Menciona ACAFI: {'Sí' if result.mentions_acafi else 'No'}")
            if result.sector_tags:
                print(f"   Tags: {', '.join(result.sector_tags)}")
        
        # 3. Generar resumen editorial
        print("\n3. GENERANDO RESUMEN EDITORIAL CON OLLAMA")
        print("-"*40)
        print("⏳ Generando resumen (esto puede tomar unos segundos)...")
        
        editorial = llm.generate_editorial_summary(classified)
        print("\n📝 RESUMEN EDITORIAL:")
        print("-"*40)
        print(editorial)
        
        # 4. Generar resumen de artículo
        print("\n4. GENERANDO RESUMEN DE ARTÍCULO")
        print("-"*40)
        print("⏳ Generando resumen del primer artículo...")
        
        summary = llm.generate_article_summary(test_articles[0], max_lines=2)
        print(f"\n📄 Resumen: {summary}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("PRUEBA COMPLETADA")
    print("="*60)
    
    print("\n✅ PRÓXIMOS PASOS:")
    print("1. Configurar las fuentes de noticias reales")
    print("2. Configurar Mailchimp (opcional)")
    print("3. Ejecutar el agente completo")

if __name__ == "__main__":
    # Verificar que Ollama está corriendo
    import subprocess
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ollama no está instalado o no está corriendo")
            print("   Ejecuta: ollama serve")
            sys.exit(1)
    except FileNotFoundError:
        print("❌ Ollama no está instalado")
        print("   Instala desde: https://ollama.ai")
        sys.exit(1)
    
    test_ollama_integration()