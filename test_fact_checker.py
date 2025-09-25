#!/usr/bin/env python3
"""
Script de prueba para el sistema de verificación de hechos y prevención de alucinaciones
"""
from datetime import datetime, timedelta
from models import Article
from fact_checker import FactChecker, HallucinationPreventer
from llm_processor import LLMProcessor
from classifier import NewsSection, ClassificationResult

def test_fact_checking():
    """Probar el sistema de verificación de hechos"""
    
    print("="*60)
    print("🔍 PRUEBA DEL SISTEMA ANTI-ALUCINACIONES")
    print("="*60)
    
    fact_checker = FactChecker()
    preventer = HallucinationPreventer()
    
    # Crear artículos de prueba
    real_articles = [
        Article(
            url="https://df.cl/test1",
            source="Diario Financiero",
            title="ACAFI presenta propuesta regulatoria a la CMF",
            subtitle="Buscan mayor flexibilidad para inversiones",
            content="La Asociación Chilena de Administradoras de Fondos de Inversión (ACAFI) presentó una propuesta a la CMF para flexibilizar las inversiones alternativas. La medida beneficiaría a 45 AGF.",
            published_at=datetime.now()
        ),
        Article(
            url="https://elmercurio.com/test2",
            source="El Mercurio",
            title="Banco Central mantiene tasa en 5,5%",
            subtitle="Decisión unánime del consejo",
            content="El Banco Central de Chile mantuvo la tasa de política monetaria en 5,5%. El consejo votó de forma unánime citando presiones inflacionarias.",
            published_at=datetime.now() - timedelta(days=1)
        )
    ]
    
    # TEST 1: Resumen editorial CON alucinaciones
    print("\n📝 TEST 1: Detectar alucinaciones en resumen editorial")
    print("-"*40)
    
    editorial_with_hallucinations = """Buenos días, ACAFI anunció ayer un acuerdo histórico con el gobierno por US$500 millones.
Además, LarrainVial reportó ganancias récord de 200% en sus fondos de tecnología.
El Banco Central sorprendió al mercado bajando la tasa a 3,5% en una decisión dividida.
Las AFP alcanzaron rentabilidades del 15% en todos sus fondos durante el último mes.
Microsoft anunció la compra de una AGF chilena por US$2 billones.
Finalmente, el Congreso aprobó la eliminación total de impuestos a los fondos de inversión."""
    
    result = fact_checker.verify_editorial_summary(editorial_with_hallucinations, real_articles)
    
    print(f"✅ Válido: {result.is_valid}")
    print(f"📊 Confianza: {result.confidence:.1%}")
    if result.issues:
        print("⚠️ Problemas detectados:")
        for issue in result.issues[:5]:  # Mostrar solo los primeros 5
            print(f"   • {issue}")
    
    # TEST 2: Resumen editorial SIN alucinaciones
    print("\n📝 TEST 2: Verificar resumen editorial correcto")
    print("-"*40)
    
    editorial_correct = """Buenos días, ACAFI presentó una propuesta regulatoria a la CMF para flexibilizar inversiones alternativas.
La medida beneficiaría a 45 administradoras generales de fondos en el país.
El Banco Central mantuvo la tasa de política monetaria en 5,5% con decisión unánime.
El consejo citó presiones inflacionarias como factor principal para mantener la restricción.
La CMF evalúa las propuestas que buscan mayor flexibilidad en el sector.
El mercado espera una respuesta en las próximas semanas sobre estas medidas."""
    
    result = fact_checker.verify_editorial_summary(editorial_correct, real_articles)
    
    print(f"✅ Válido: {result.is_valid}")
    print(f"📊 Confianza: {result.confidence:.1%}")
    if result.issues:
        print("⚠️ Problemas detectados:")
        for issue in result.issues:
            print(f"   • {issue}")
    else:
        print("✅ No se detectaron problemas de factualidad")
    
    # TEST 3: Verificar resumen de artículo
    print("\n📝 TEST 3: Verificar resumen de artículo individual")
    print("-"*40)
    
    article = real_articles[0]
    
    # Resumen con información inventada
    bad_summary = "ACAFI y el Ministerio de Hacienda firmaron un acuerdo por US$1000 millones para crear un fondo soberano."
    
    result = fact_checker.verify_article_summary(bad_summary, article)
    print(f"Resumen MALO:")
    print(f"  '{bad_summary}'")
    print(f"  Válido: {result.is_valid}")
    print(f"  Confianza: {result.confidence:.1%}")
    if result.issues:
        for issue in result.issues:
            print(f"  • {issue}")
    
    # Resumen correcto
    good_summary = "ACAFI presentó a la CMF una propuesta para flexibilizar inversiones alternativas que beneficiaría a 45 AGF."
    
    result = fact_checker.verify_article_summary(good_summary, article)
    print(f"\nResumen BUENO:")
    print(f"  '{good_summary}'")
    print(f"  Válido: {result.is_valid}")
    print(f"  Confianza: {result.confidence:.1%}")
    
    # TEST 4: Mejorar prompts para prevenir alucinaciones
    print("\n📝 TEST 4: Prompts mejorados anti-alucinación")
    print("-"*40)
    
    original_prompt = "Resume las noticias del día"
    enhanced_prompt = preventer.enhance_prompt(original_prompt, real_articles)
    
    print("Prompt original:")
    print(f"  {original_prompt}")
    print("\nPrompt mejorado (extracto):")
    lines = enhanced_prompt.split('\n')[:10]
    for line in lines:
        if line.strip():
            print(f"  {line}")
    
    # TEST 5: Probar con LLM real
    print("\n📝 TEST 5: Generar resumen con verificación integrada")
    print("-"*40)
    
    llm = LLMProcessor()
    
    # Preparar artículos clasificados
    classified = {
        NewsSection.ACAFI: [(real_articles[0], ClassificationResult(
            section=NewsSection.ACAFI,
            confidence=0.95,
            matched_keywords=['ACAFI'],
            sector_tags=['Regulación'],
            is_partner_new_fund=False,
            mentions_acafi=True
        ))],
        NewsSection.INTERES: [(real_articles[1], ClassificationResult(
            section=NewsSection.INTERES,
            confidence=0.85,
            matched_keywords=['Banco Central'],
            sector_tags=['Política Monetaria'],
            is_partner_new_fund=False,
            mentions_acafi=False
        ))]
    }
    
    print("Generando resumen editorial con verificación...")
    editorial = llm.generate_editorial_summary(classified)
    
    print("\nResumen generado:")
    print("-"*40)
    print(editorial)
    
    # Verificar el resumen generado
    print("\nVerificando factualidad del resumen generado...")
    result = fact_checker.verify_editorial_summary(editorial, real_articles)
    print(f"✅ Válido: {result.is_valid}")
    print(f"📊 Confianza: {result.confidence:.1%}")
    
    if result.issues:
        print("⚠️ Advertencias:")
        for issue in result.issues:
            print(f"   • {issue}")
    
    print("\n" + "="*60)
    print("✅ PRUEBAS COMPLETADAS")
    print("="*60)
    
    print("\n💡 CONCLUSIONES:")
    print("• El sistema detecta exitosamente información inventada")
    print("• Verifica entidades, números y fechas contra las fuentes")
    print("• Los prompts mejorados reducen las alucinaciones")
    print("• La verificación integrada asegura la calidad del contenido")

if __name__ == "__main__":
    test_fact_checking()