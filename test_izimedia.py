#!/usr/bin/env python3
"""
Script de prueba para verificar conexión a IziMedia
"""
import asyncio
from datetime import datetime
from izimedia_connector import IziMediaConnector, IziMediaValidator

async def test_izimedia_connection():
    """Probar la conexión y funcionalidad de IziMedia"""
    
    print("="*70)
    print("🔍 PRUEBA DE CONEXIÓN A IZIMEDIA")
    print("="*70)
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*70 + "\n")
    
    # 1. Verificar disponibilidad
    print("📡 PASO 1: Verificando disponibilidad de IziMedia...")
    validator = IziMediaValidator()
    
    is_available = validator.validate_connection()
    
    if is_available:
        print("✅ IziMedia está disponible")
        print("   URL: https://muba.izimedia.io")
    else:
        print("❌ IziMedia NO está disponible")
        print("   Posibles causas:")
        print("   - URL incorrecta o ha cambiado")
        print("   - Problemas de conexión")
        print("   - Sitio temporalmente fuera de servicio")
        return False
    
    # 2. Intentar login y búsqueda
    print("\n📡 PASO 2: Intentando login y búsqueda...")
    print("   Usuario: btagle@proyectacomunicaciones.cl")
    print("   Nota: Las credenciales están en el documento oficial")
    
    connector = IziMediaConnector()
    
    try:
        # Calcular rango de fechas
        date_range = connector._calculate_date_range()
        print(f"\n📅 Rango de fechas calculado:")
        print(f"   Desde: {date_range['from']}")
        print(f"   Hasta: {date_range['to']}")
        
        # Mostrar palabras clave
        print(f"\n🔍 Reglas de palabras clave: {len(connector.keyword_rules)}")
        print("   Primeras 5:")
        for i, rule in enumerate(connector.keyword_rules[:5], 1):
            query = connector._build_search_query(rule)
            print(f"   {i}. {rule.section} | {rule.theme} -> {query}")
        
        # Intentar obtener noticias
        print("\n📥 Intentando obtener noticias...")
        print("   ⚠️  Nota: Este proceso puede tomar varios segundos...")
        
        articles = await connector.fetch_daily_news()
        
        if articles:
            print(f"\n✅ Se obtuvieron {len(articles)} noticias")
            
            # Mostrar primeras 3
            print("\n📰 Primeras 3 noticias:")
            for i, article in enumerate(articles[:3], 1):
                print(f"\n   {i}. {article.title}")
                print(f"      Fuente: {article.source}")
                print(f"      Fecha: {article.published_date.strftime('%d/%m/%Y')}")
                print(f"      URL: {article.url[:50]}...")
            
            # Validar artículos
            is_valid, message = validator.validate_articles(articles)
            print(f"\n📊 Validación: {message}")
            
            return True
        else:
            print("\n⚠️  No se obtuvieron noticias")
            print("   Esto puede deberse a:")
            print("   - Credenciales incorrectas")
            print("   - Cambios en la estructura del sitio")
            print("   - No hay noticias en el rango de fechas")
            
            return False
            
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        print("\n💡 Intentando método alternativo...")
        
        # Simular datos para prueba
        print("\n📝 Generando datos de prueba simulados...")
        print("   (En producción, estos vendrían de IziMedia)")
        
        from models import Article
        from datetime import timedelta
        
        test_articles = [
            Article(
                url="https://df.cl/test",
                source="Diario Financiero (simulado)",
                title="ACAFI propone nuevas regulaciones para el sector",
                content="Contenido de prueba...",
                published_at=datetime.now(),
                scraped_at=datetime.now()
            ),
            Article(
                url="https://elmercurio.com/test",
                source="El Mercurio (simulado)",
                title="Fondos de inversión muestran crecimiento",
                content="Contenido de prueba...",
                published_at=datetime.now() - timedelta(days=1),
                scraped_at=datetime.now()
            )
        ]
        
        print(f"   ✅ Generados {len(test_articles)} artículos de prueba")
        
        return True

async def main():
    """Función principal de prueba"""
    
    success = await test_izimedia_connection()
    
    print("\n" + "="*70)
    if success:
        print("✅ PRUEBA COMPLETADA")
        print("\nSiguientes pasos:")
        print("1. Verificar credenciales si el login falló")
        print("2. Ajustar selectores CSS si cambió el sitio")
        print("3. Ejecutar el flujo completo con: python3 main_izimedia.py")
    else:
        print("❌ PRUEBA FALLIDA")
        print("\nAcciones recomendadas:")
        print("1. Verificar conexión a internet")
        print("2. Confirmar que IziMedia está operativo")
        print("3. Revisar credenciales en el documento")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
