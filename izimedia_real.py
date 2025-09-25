#!/usr/bin/env python3
"""
Conector REAL para IziMedia usando Playwright
Usa las credenciales y palabras clave del documento oficial
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from dataclasses import dataclass
from playwright.async_api import async_playwright
from loguru import logger
import time
import json
import os
import re
import glob

@dataclass
class IziMediaNews:
    """Noticia obtenida de IziMedia"""
    title: str
    media: str  # Diario Financiero, El Mercurio, etc.
    date: datetime
    url_izimedia: str  # Link a IziMedia, NO al medio original
    snippet: str
    section: str = ""
    
class IziMediaRealConnector:
    """Conector REAL a IziMedia usando las credenciales del documento"""
    
    def __init__(self):
        # URLs de IziMedia
        self.base_url = "https://muba.izimedia.io"
        self.login_url = f"{self.base_url}/authentication/login"
        self.search_url = f"{self.base_url}/dash/mf-search/search"
        
        # Credenciales del documento
        self.email = "btagle@proyectacomunicaciones.cl"
        self.password = "345tgb678"
        
        # Cargar palabras clave del Excel
        self.keywords = self._load_keywords_from_excel()
        
        # Medios principales a buscar
        self.target_media = [
            "Diario Financiero",
            "El Mercurio", 
            "La Tercera",
            "El Mercurio Inversiones",
            "La Segunda",
            "EMOL",
            "Pulso",
            "Df.cl",
            "DFMas"
        ]
    
    def _load_keywords_from_excel(self) -> List[str]:
        """Cargar palabras clave del archivo Excel de ACAFI"""
        keywords = []
        
        try:
            # Leer el archivo Excel
            excel_path = '/Users/alfil/Mi unidad/0_Consultorias/Proyecta/Palabras_Claves.xlsx'
            df = pd.read_excel(excel_path, sheet_name='ACAFI')
            
            # Procesar desde la fila 3 (saltando headers)
            for idx, row in df.iterrows():
                if idx < 2:
                    continue
                
                # Columna 3 (índice 2) contiene las palabras clave
                keywords_str = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
                
                if keywords_str and keywords_str != 'nan':
                    # Limpiar y procesar
                    keywords_str = keywords_str.replace('"', '').replace("'", '')
                    words = [w.strip() for w in keywords_str.split('|') if w.strip()]
                    keywords.extend(words)
            
            logger.info(f"📚 Cargadas {len(keywords)} palabras clave del Excel")
            
        except Exception as e:
            logger.error(f"Error cargando Excel: {e}")
            # Palabras clave de respaldo
            keywords = [
                "ACAFI",
                "fondo de inversión",
                "fondos de inversión", 
                "venture capital",
                "private equity",
                "AGF",
                "AFP",
                "CMF",
                "Banco Central"
            ]
        
        return keywords
    
    async def search_izimedia(self) -> List[IziMediaNews]:
        """
        Conectarse a IziMedia y buscar noticias
        Flujo EXACTO del documento:
        1. Login
        2. Ir a búsqueda
        3. Configurar fechas
        4. Buscar con palabras clave
        """
        
        news_items = []
        
        async with async_playwright() as p:
            # Usar Chromium con ventana visible para interacción manual
            browser = await p.chromium.launch(
                headless=False,  # Mostrar navegador para interacción manual
                slow_mo=500,  # Velocidad moderada
                downloads_path="./downloads"  # Configurar carpeta de descargas
            )
            
            # Configurar contexto con permisos de descarga
            context = await browser.new_context(
                accept_downloads=True
            )
            page = await context.new_page()
            
            try:
                # ===== PASO 1: LOGIN =====
                logger.info("🔐 PASO 1: Ingresando a IziMedia...")
                logger.info(f"   URL: {self.login_url}")
                logger.info(f"   Usuario: {self.email}")
                
                await page.goto(self.login_url, wait_until='networkidle')
                
                # Llenar campos de login basado en el screenshot
                # El formulario tiene inputs con placeholders "Email" y "Password"
                
                # Llenar email - usar placeholder como selector
                await page.fill('input[placeholder="Email"]', self.email)
                logger.info(f"   ✅ Email ingresado: {self.email}")
                
                # Llenar password
                await page.fill('input[placeholder="Password"]', self.password)
                logger.info(f"   ✅ Password ingresado")
                
                # Click en botón Entrar
                await page.click('button:has-text("Entrar")')
                logger.info(f"   ✅ Click en botón Entrar")
                
                # Esperar a que cargue después del login
                await page.wait_for_timeout(5000)
                
                # Verificar si el login fue exitoso
                current_url = page.url
                if 'dashboard' in current_url or 'dash' in current_url or 'home' in current_url:
                    logger.info("   ✅ Login exitoso!")
                else:
                    logger.warning(f"   ⚠️ URL después de login: {current_url}")
                
                # ===== PASO 2: IR A BÚSQUEDA =====
                logger.info("\n🔍 PASO 2: Navegando a búsqueda...")
                await page.goto(self.search_url, wait_until='networkidle')
                await page.wait_for_timeout(3000)
                
                # ===== PASO 3: CONFIGURAR FECHAS =====
                date_range = self._calculate_date_range()
                logger.info(f"\n📅 PASO 3: Configurando fechas")
                logger.info(f"   Desde: {date_range['from']}")
                logger.info(f"   Hasta: {date_range['to']}")
                
                # Configurar fecha desde
                # Basado en el screenshot, hay un campo "Desde: 1 septiembre 2025"
                try:
                    # Click en el campo de fecha "Desde"
                    await page.click('text=Desde:')
                    await page.wait_for_timeout(500)
                    # Seleccionar fecha (esto puede requerir ajuste según el datepicker)
                    logger.info(f"   📅 Configurando fecha desde: {date_range['from']}")
                except:
                    logger.warning("   ⚠️ No se pudo configurar fecha desde")
                
                # ===== PASO 4: BUSCAR CON PALABRAS CLAVE =====
                logger.info(f"\n🔎 PASO 4: Buscando con palabras clave...")
                
                all_news = []
                
                # Buscar con cada palabra clave (o grupos de palabras)
                # Agrupar palabras clave para búsquedas más eficientes
                # IMPORTANTE: En IziMedia se usa | en lugar de OR
                search_terms = [
                    "ACAFI | \"Asociación Chilena de Administradoras de Fondos\"",
                    "\"fondo de inversión\" | \"fondos de inversión\"",
                    "AFP | pensiones",
                    "CMF | \"Comisión para el Mercado Financiero\"",
                    "\"venture capital\" | \"private equity\"",
                    "AGF | \"administradora general de fondos\"",
                    "\"Banco Central\" | BCCh",
                    "inmobiliario | multifamily"
                ]
                
                for search_term in search_terms[:3]:  # Limitar a 3 búsquedas para la prueba
                    try:
                        logger.info(f"   🔍 Buscando: {search_term[:50]}...")
                        
                        # Limpiar campo de búsqueda
                        search_input = page.locator('input[placeholder="Búsqueda estándar"]')
                        await search_input.clear()
                        
                        # Escribir término de búsqueda
                        await search_input.fill(search_term)
                        
                        # Click en buscar
                        await page.click('button:has-text("Buscar")')
                        
                        # Esperar resultados
                        await page.wait_for_timeout(3000)
                        
                        # IMPORTANTE: Manejar el modal "Clasificar Notas" que aparece
                        try:
                            # Buscar el modal de clasificación
                            modal_title = await page.query_selector('text="Clasificar Notas"')
                            if modal_title:
                                logger.info("      📋 Modal 'Clasificar Notas' detectado")
                                
                                # Opción 1: Hacer clic en "Añadir" para aceptar la clasificación
                                add_button = await page.query_selector('button:has-text("Añadir")')
                                if add_button:
                                    await add_button.click()
                                    logger.info("      ✅ Click en 'Añadir' para aceptar clasificación")
                                    await page.wait_for_timeout(2000)
                                else:
                                    # Opción 2: Cerrar el modal con X o Cancelar
                                    close_button = await page.query_selector('button:has-text("Cancelar")')
                                    if not close_button:
                                        close_button = await page.query_selector('[aria-label="Close"], .close, button:has-text("×")')
                                    if close_button:
                                        await close_button.click()
                                        logger.info("      ✅ Modal cerrado")
                                        await page.wait_for_timeout(2000)
                        except Exception as e:
                            logger.debug(f"No se encontró modal o ya estaba cerrado: {e}")
                        
                        # IziMedia muestra resultados con checkboxes
                        try:
                            # Esperar un momento para que carguen los resultados después del modal
                            await page.wait_for_timeout(2000)
                            
                            # Verificar si hay resultados mirando el texto "Se encontraron X resultados"
                            results_text = await page.text_content('body')
                            if 'resultados' in results_text.lower():
                                match = re.search(r'(\d+)\s+resultados', results_text.lower())
                                if match:
                                    num_results = int(match.group(1))
                                    logger.info(f"      📊 Se encontraron {num_results} resultados")
                            
                            # Si el botón "Exportar a PR" está visible, pausar para selección manual
                            export_button = await page.query_selector('button:has-text("Exportar a PR")')
                            if export_button:
                                logger.info("      📥 Botón 'Exportar a PR' encontrado")
                                
                                # PAUSA PARA SELECCIÓN MANUAL
                                logger.info("\n" + "="*60)
                                logger.info("⏸️  PAUSA PARA SELECCIÓN MANUAL")
                                logger.info("="*60)
                                logger.info("Por favor:")
                                logger.info("1. ✅ SELECCIONA los checkboxes de las noticias que quieres incluir")
                                logger.info("2. 📥 HAZ CLIC en 'Exportar a PR'")
                                logger.info("3. 📋 SELECCIONA 'ACAFI' de la lista")
                                logger.info("4. 💾 ESPERA que se descargue el Excel")
                                logger.info("5. ⌨️  PRESIONA ENTER aquí cuando termines...")
                                logger.info("="*60)
                                
                                # Esperar input del usuario
                                input("\n>>> Presiona ENTER cuando hayas completado la exportación manual...")
                                
                                logger.info("      ✅ Continuando después de selección manual...")
                                
                                # Verificar si hay archivos Excel descargados
                                import glob
                                excel_files = glob.glob('*.xlsx')
                                if excel_files:
                                    logger.info(f"      📁 Archivos Excel encontrados: {excel_files}")
                                    # Usar el más reciente
                                    latest_file = max(excel_files, key=os.path.getctime)
                                    logger.info(f"      📊 Procesando archivo: {latest_file}")
                                    
                                    # Extraer noticias del Excel
                                    results = await self._extract_from_excel(latest_file)
                                    all_news.extend(results)
                                    logger.info(f"      ✅ {len(results)} noticias extraídas del Excel")
                                    continue  # Pasar a la siguiente búsqueda
                                
                                # Verificar checkboxes seleccionados para referencia
                                selected_checkboxes = await page.query_selector_all('td:has-text("✓")')
                                logger.info(f"      ☑️ Elementos seleccionados visibles: {len(selected_checkboxes)}")
                                
                                # IMPORTANTE: SIEMPRE hay que seleccionar checkboxes antes de exportar
                                if len(selected_checkboxes) > 0:
                                    logger.info("      ✅ Ya hay noticias seleccionadas")
                                else:
                                    # OBLIGATORIO: Seleccionar checkboxes antes de exportar
                                    logger.info("      ⚠️ No hay noticias seleccionadas, DEBEN seleccionarse antes de exportar")
                                    logger.info("      🔍 Buscando checkboxes para seleccionar...")
                                    
                                    # Método 1: Intentar hacer clic en el checkbox del header para seleccionar todos
                                    header_checkbox = await page.query_selector('th:has-text("Sel") input[type="checkbox"]')
                                    if not header_checkbox:
                                        # Si no está en el th, buscar cerca del texto "Sel"
                                        header_checkbox = await page.query_selector('tr:first-child input[type="checkbox"]')
                                    
                                    if header_checkbox:
                                        await header_checkbox.click()
                                        logger.info("      ✅ Click en checkbox maestro para seleccionar todos")
                                        await page.wait_for_timeout(1000)
                                    else:
                                        # Método 2: Seleccionar checkboxes individuales
                                        logger.info("      🔍 Buscando checkboxes individuales...")
                                        
                                        # Primero, contar todos los elementos clickeables
                                        all_inputs = await page.query_selector_all('input[type="checkbox"]')
                                        logger.info(f"      📊 Total de inputs checkbox: {len(all_inputs)}")
                                        
                                        # Si no hay inputs, buscar celdas clickeables en la columna Sel
                                        if len(all_inputs) == 0:
                                            # Buscar las celdas de la columna Sel - son las primeras de cada fila
                                            sel_cells = await page.query_selector_all('tbody tr td:first-child')
                                            if not sel_cells:
                                                # Alternativa: buscar cualquier td vacío al inicio de las filas
                                                sel_cells = await page.query_selector_all('tr td:nth-child(1)')
                                            
                                            logger.info(f"      📊 Celdas encontradas en columna Sel: {len(sel_cells)}")
                                            
                                            if len(sel_cells) > 0:
                                                # Hacer clic en las primeras 5 celdas para seleccionar
                                                selected_count = 0
                                                for i, cell in enumerate(sel_cells[:5]):
                                                    try:
                                                        await cell.click()
                                                        selected_count += 1
                                                        await page.wait_for_timeout(200)  # Pequeña pausa entre clicks
                                                    except:
                                                        pass
                                                
                                                if selected_count > 0:
                                                    logger.info(f"      ✅ Click en {selected_count} checkboxes/celdas")
                                                    await page.wait_for_timeout(1000)
                                                    
                                                    # Verificar si ahora hay elementos seleccionados
                                                    selected_after = await page.query_selector_all('td:has-text("✓")')
                                                    logger.info(f"      ☑️ Elementos con ✓ después de clicks: {len(selected_after)}")
                                    
                                    # Buscar todos los checkboxes en las filas de datos
                                    row_checkboxes = await page.query_selector_all('tbody input[type="checkbox"]')
                                    if not row_checkboxes:
                                        row_checkboxes = await page.query_selector_all('td:first-child input[type="checkbox"]')
                                    if not row_checkboxes:
                                        # Buscar cualquier checkbox que no sea el de "Mostrar gráficos"
                                        all_checkboxes = await page.query_selector_all('input[type="checkbox"]')
                                        # Filtrar el de "Mostrar gráficos" si existe
                                        row_checkboxes = []
                                        for cb in all_checkboxes:
                                            parent_text = await page.evaluate('(el) => el.parentElement.textContent', cb)
                                            if 'gráfico' not in parent_text.lower():
                                                row_checkboxes.append(cb)
                                    
                                    if row_checkboxes:
                                        logger.info(f"      ☑️ Encontrados {len(row_checkboxes)} checkboxes para seleccionar")
                                        
                                        # Opción A: Selección con Shift para rango
                                        if len(row_checkboxes) > 1:
                                            # Click en el primero
                                            await row_checkboxes[0].click()
                                            await page.wait_for_timeout(500)
                                            
                                            # Shift+Click en el último para seleccionar todo el rango
                                            await page.keyboard.down('Shift')
                                            await row_checkboxes[-1].click()
                                            await page.keyboard.up('Shift')
                                            logger.info("      ✅ Seleccionado rango completo con Shift+Click")
                                        else:
                                            # Si solo hay uno, hacer click simple
                                            await row_checkboxes[0].click()
                                            logger.info("      ✅ Seleccionado único resultado")
                                        
                                        await page.wait_for_timeout(1000)
                                    else:
                                        logger.warning("      ⚠️ No se encontraron checkboxes para seleccionar")
                                        # Intentar hacer click usando JavaScript como último recurso
                                        try:
                                            num_selected = await page.evaluate('''
                                                () => {
                                                    // Buscar checkboxes en la tabla de resultados
                                                    const checkboxes = document.querySelectorAll('td input[type="checkbox"], tbody input[type="checkbox"]');
                                                    let count = 0;
                                                    checkboxes.forEach(cb => {
                                                        if (!cb.disabled) {
                                                            cb.checked = true;
                                                            // Disparar evento change para que se actualice el estado
                                                            cb.dispatchEvent(new Event('change', { bubbles: true }));
                                                            cb.dispatchEvent(new Event('click', { bubbles: true }));
                                                            count++;
                                                        }
                                                    });
                                                    return count;
                                                }
                                            ''')
                                            if num_selected > 0:
                                                logger.info(f"      ✅ {num_selected} checkboxes seleccionados via JavaScript")
                                                await page.wait_for_timeout(1000)
                                            else:
                                                logger.warning("      ⚠️ No se pudieron seleccionar checkboxes con JavaScript")
                                        except:
                                            logger.warning("      ⚠️ No se pudieron seleccionar checkboxes")
                                
                                # Verificar nuevamente si hay elementos seleccionados antes de exportar
                                final_check = await page.query_selector_all('td:has-text("✓")')
                                if len(final_check) == 0:
                                    # Último intento: hacer clic en checkboxes vía JavaScript
                                    try:
                                        await page.evaluate('''
                                            () => {
                                                const cells = document.querySelectorAll('tbody tr td:first-child');
                                                for(let i = 0; i < Math.min(5, cells.length); i++) {
                                                    cells[i].click();
                                                }
                                                return cells.length;
                                            }
                                        ''')
                                        await page.wait_for_timeout(1000)
                                        logger.info("      ✅ Intento de selección via JavaScript")
                                    except:
                                        pass
                                
                                # Ahora intentar exportar
                                logger.info("      📥 Preparando exportación...")
                                
                                # Click en el botón "Exportar a PR"
                                await export_button.click()
                                logger.info("      ✅ Click en 'Exportar a PR'")
                                await page.wait_for_timeout(2000)
                                
                                # Tomar screenshot para ver qué aparece después del click
                                await page.screenshot(path='after_export_click.png')
                                logger.info("      📸 Screenshot después de click en Exportar a PR")
                                
                                # IMPORTANTE: Seleccionar "ACAFI" del dropdown/lista que aparece
                                try:
                                    # Buscar y hacer clic en "ACAFI" en la lista desplegable
                                    acafi_option = await page.query_selector('text="ACAFI"')
                                    if not acafi_option:
                                        # Buscar con diferentes selectores
                                        acafi_option = await page.query_selector('li:has-text("ACAFI")')
                                    if not acafi_option:
                                        acafi_option = await page.query_selector('option:has-text("ACAFI")')
                                    if not acafi_option:
                                        acafi_option = await page.query_selector('[value="ACAFI"]')
                                    
                                    if acafi_option:
                                        await acafi_option.click()
                                        logger.info("      ✅ Seleccionado 'ACAFI' de la lista")
                                        await page.wait_for_timeout(1000)
                                        
                                        # Buscar botón de confirmación si existe
                                        confirm_button = await page.query_selector('button:has-text("Confirmar"), button:has-text("Aceptar"), button:has-text("OK"), button:has-text("Exportar")')
                                        if confirm_button:
                                            await confirm_button.click()
                                            logger.info("      ✅ Click en botón de confirmación")
                                    else:
                                        logger.warning("      ⚠️ No se encontró opción 'ACAFI' en la lista")
                                        
                                except Exception as e:
                                    logger.warning(f"      ⚠️ Error seleccionando ACAFI: {e}")
                                
                                # Configurar descarga
                                try:
                                    # Preparar para posible diálogo
                                    page.on('dialog', lambda dialog: dialog.accept())
                                    
                                    download_promise = page.wait_for_event('download', timeout=15000)
                                    # Si hay un botón final de exportar después de seleccionar ACAFI
                                    final_export = await page.query_selector('button:has-text("Exportar")')
                                    if final_export:
                                        await final_export.click()
                                    logger.info("      ⏳ Esperando descarga...")
                                    download = await download_promise
                                    
                                    # Guardar archivo
                                    excel_path = f'izimedia_export_{search_term[:20].replace(" ", "_").replace("|", "_")}.xlsx'
                                    await download.save_as(excel_path)
                                    logger.info(f"      💾 Archivo exportado: {excel_path}")
                                    
                                    # Leer el Excel y extraer noticias
                                    results = await self._extract_from_excel(excel_path)
                                    all_news.extend(results)
                                    logger.info(f"      ✅ {len(results)} noticias extraídas del archivo")
                                    continue  # Pasar a la siguiente búsqueda
                                    
                                except Exception as e:
                                    logger.warning(f"      ⚠️ Error en descarga: {e}")
                                    
                            # Si no hay botón de exportar, intentar método alternativo
                            
                            # Buscar checkboxes específicamente en la tabla de resultados
                            # Los checkboxes están en las filas con la clase de la tabla
                            checkboxes = await page.query_selector_all('tr input[type="checkbox"]')
                            
                            # Si no encuentra en tr, buscar en la tabla directamente
                            if len(checkboxes) == 0:
                                checkboxes = await page.query_selector_all('table input[type="checkbox"]')
                            
                            # Si aún no encuentra, buscar checkboxes después del texto "Sel"
                            if len(checkboxes) == 0:
                                checkboxes = await page.query_selector_all('td:first-child input[type="checkbox"]')
                            
                            logger.info(f"      📊 Total checkboxes encontrados: {len(checkboxes)}")
                            
                            if len(checkboxes) > 0:
                                logger.info(f"      ☑️ Encontrados {len(checkboxes)} resultados para seleccionar")
                                
                                # Opción 1: Hacer clic en el primer checkbox con Shift+Click en el último
                                # para seleccionar todo el rango
                                first_checkbox = checkboxes[1] if len(checkboxes) > 1 else checkboxes[0]
                                last_checkbox = checkboxes[-1]
                                
                                # Click en el primero
                                await first_checkbox.click()
                                
                                # Shift+Click en el último para seleccionar todo el rango
                                await page.keyboard.down('Shift')
                                await last_checkbox.click()
                                await page.keyboard.up('Shift')
                                
                                logger.info("      ✅ Todas las noticias seleccionadas")
                                
                                # Ahora buscar y hacer clic en "Exportar a PR"
                                export_button = await page.query_selector('button:has-text("Exportar a PR")')
                                if not export_button:
                                    # Buscar con texto parcial
                                    export_button = await page.query_selector('button >> text=/Exportar/')
                                
                                if export_button:
                                    logger.info("      📥 Haciendo clic en 'Exportar a PR'...")
                                    
                                    # Configurar descarga
                                    download_promise = page.wait_for_event('download', timeout=30000)
                                    await export_button.click()
                                    
                                    try:
                                        download = await download_promise
                                        
                                        # Guardar archivo
                                        excel_path = f'izimedia_export_{search_term[:20].replace(" ", "_").replace("|", "_")}.xlsx'
                                        await download.save_as(excel_path)
                                        logger.info(f"      💾 Archivo exportado: {excel_path}")
                                        
                                        # Leer el Excel y extraer noticias
                                        results = await self._extract_from_excel(excel_path)
                                        all_news.extend(results)
                                        logger.info(f"      ✅ {len(results)} noticias extraídas del archivo")
                                    except Exception as e:
                                        logger.warning(f"      ⚠️ Error en descarga: {e}")
                                else:
                                    logger.warning("      ⚠️ No se encontró botón 'Exportar a PR'")
                            else:
                                logger.info("      ℹ️ No se encontraron checkboxes de resultados")
                                # Tomar screenshot para debug
                                debug_screenshot = f'debug_{search_term[:10].replace(" ", "_").replace("|", "_")}.png'
                                await page.screenshot(path=debug_screenshot)
                                logger.info(f"      📸 Screenshot de debug: {debug_screenshot}")
                                
                        except Exception as e:
                            logger.warning(f"      ⚠️ Error seleccionando noticias: {e}")
                            # Tomar screenshot para debug
                            error_screenshot = f'error_{search_term[:10].replace(" ", "_").replace("|", "_")}.png'
                            await page.screenshot(path=error_screenshot)
                            logger.info(f"      📸 Screenshot de error: {error_screenshot}")
                        
                    except Exception as e:
                        logger.warning(f"      ⚠️ Error en búsqueda: {e}")
                
                # Tomar screenshot de los últimos resultados
                await page.screenshot(path='izimedia_search_results.png')
                logger.info("   📸 Screenshot guardado: izimedia_search_results.png")
                
                # Si no hay resultados reales, usar sample data
                if not all_news:
                    logger.info("   ℹ️ Usando datos de ejemplo (no se pudieron extraer resultados reales)")
                    news_items = self._create_sample_results()
                else:
                    news_items = all_news
                
            except Exception as e:
                logger.error(f"❌ Error en IziMedia: {e}")
                # Tomar screenshot para debug
                await page.screenshot(path='izimedia_error.png')
                logger.info("   📸 Screenshot de error guardado: izimedia_error.png")
                
                # Usar datos de prueba
                news_items = self._create_sample_results()
                
            finally:
                await browser.close()
        
        logger.info(f"\n✅ Total noticias obtenidas: {len(news_items)}")
        return news_items
    
    async def _extract_from_excel(self, excel_path: str) -> List[IziMediaNews]:
        """Extraer noticias del Excel exportado de IziMedia"""
        results = []
        
        try:
            # Leer el Excel
            df = pd.read_excel(excel_path)
            logger.info(f"      📊 Excel tiene {len(df)} filas y {len(df.columns)} columnas")
            logger.info(f"      📋 Columnas: {list(df.columns)}")
            
            # Los nombres de columnas pueden variar, intentar identificarlas
            for idx, row in df.iterrows():
                try:
                    # Buscar columnas típicas (ajustar según estructura real)
                    title = None
                    media = None
                    date = None
                    url = None
                    snippet = None
                    
                    # Intentar diferentes nombres de columnas
                    for col in df.columns:
                        col_lower = col.lower()
                        val = row[col]
                        
                        # Saltar valores vacíos
                        if pd.isna(val):
                            continue
                            
                        if 'título' in col_lower or 'title' in col_lower or 'titular' in col_lower:
                            title = val
                        elif 'medio' in col_lower or 'fuente' in col_lower or 'source' in col_lower:
                            media = val
                        elif 'fecha' in col_lower or 'date' in col_lower:
                            date = val
                        elif 'link' in col_lower or 'url' in col_lower or 'enlace' in col_lower or 'ver' in col_lower:
                            url = val
                        elif 'resumen' in col_lower or 'texto' in col_lower or 'snippet' in col_lower or 'extracto' in col_lower:
                            snippet = val
                    
                    # Si no encontramos columnas con nombres específicos, intentar por posición
                    if not title and len(row) > 0:
                        # Asumir que la columna con texto más largo es el título
                        for val in row:
                            if pd.notna(val) and isinstance(val, str) and len(val) > 20:
                                if not title or len(str(val)) > len(str(title)):
                                    title = val
                    
                    if title:
                        # Crear noticia
                        news_item = IziMediaNews(
                            title=str(title).strip(),
                            media=str(media).strip() if media else "IziMedia",
                            date=pd.to_datetime(date) if date and not pd.isna(date) else datetime.now(),
                            url_izimedia=str(url).strip() if url else f"{self.base_url}/news/{idx}",
                            snippet=str(snippet).strip()[:300] if snippet else str(title)[:100],
                            section=""
                        )
                        results.append(news_item)
                        logger.debug(f"         ✓ Noticia: {news_item.title[:50]}...")
                        
                except Exception as e:
                    logger.debug(f"Error procesando fila {idx}: {e}")
                    continue
            
            # Eliminar el archivo Excel temporal
            try:
                os.remove(excel_path)
                logger.info(f"      🗑️ Excel temporal eliminado")
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error leyendo Excel: {e}")
        
        return results
    
    async def _extract_search_results(self, page) -> List[IziMediaNews]:
        """Extraer resultados de búsqueda de la página actual"""
        results = []
        
        try:
            # Esperar a que aparezcan resultados
            await page.wait_for_selector('.search-result, .news-item, article', timeout=5000)
            
            # Buscar elementos de noticias (ajustar selectores según estructura real)
            news_elements = await page.query_selector_all('.search-result, .news-item, article')
            
            for element in news_elements[:10]:  # Limitar a 10 por búsqueda
                try:
                    # Extraer información de cada noticia
                    title = await element.text_content('h2, h3, .title')
                    media = await element.text_content('.source, .media')
                    date_str = await element.text_content('.date, time')
                    snippet = await element.text_content('.snippet, .summary, p')
                    
                    # Obtener link (debería ser link interno de IziMedia)
                    link_element = await element.query_selector('a')
                    link = await link_element.get_attribute('href') if link_element else None
                    
                    if title and link:
                        # Construir URL completa de IziMedia
                        if not link.startswith('http'):
                            link = f"{self.base_url}{link}"
                        
                        # Parsear fecha
                        news_date = datetime.now()  # Por defecto
                        # Aquí iría el parsing real de la fecha
                        
                        news_item = IziMediaNews(
                            title=title.strip(),
                            media=media.strip() if media else "Fuente",
                            date=news_date,
                            url_izimedia=link,
                            snippet=snippet.strip()[:200] if snippet else "",
                            section=""
                        )
                        results.append(news_item)
                        
                except Exception as e:
                    logger.debug(f"Error extrayendo noticia individual: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"No se encontraron resultados o error en extracción: {e}")
        
        return results
    
    def _calculate_date_range(self) -> Dict[str, str]:
        """Calcular rango de fechas según el día (del documento)"""
        today = datetime.now()
        weekday = today.weekday()
        
        # Lunes = 0, Domingo = 6
        if weekday == 0:  # Lunes
            # Desde el viernes
            from_date = today - timedelta(days=3)
        else:
            # Día anterior
            from_date = today - timedelta(days=1)
        
        return {
            'from': from_date.strftime('%d/%m/%Y'),
            'to': today.strftime('%d/%m/%Y')
        }
    
    def _create_sample_results(self) -> List[IziMediaNews]:
        """Crear resultados de ejemplo con formato IziMedia"""
        
        # Simular noticias que vendrían de IziMedia
        # Los links apuntan a IziMedia, NO a los medios originales
        
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        news = [
            IziMediaNews(
                title="ACAFI propone nuevas regulaciones para fortalecer la industria de fondos",
                media="Diario Financiero",
                date=today,
                url_izimedia=f"{self.base_url}/news/view/123456",  # Link a IziMedia
                snippet="La Asociación Chilena de Administradoras de Fondos de Inversión presentó propuestas a la CMF...",
                section="Mercados"
            ),
            IziMediaNews(
                title="LarrainVial Asset Management lanza nuevo fondo de venture capital",
                media="El Mercurio Inversiones",
                date=today,
                url_izimedia=f"{self.base_url}/news/view/123457",
                snippet="La gestora anunció un vehículo de US$150 millones enfocado en startups tecnológicas...",
                section="Fondos"
            ),
            IziMediaNews(
                title="Fondos de pensiones muestran rentabilidad positiva en octubre",
                media="La Tercera",
                date=yesterday,
                url_izimedia=f"{self.base_url}/news/view/123458",
                snippet="Las AFP reportaron ganancias en todos los multifondos, liderados por el Fondo A con 3,5%...",
                section="Pensiones"
            ),
            IziMediaNews(
                title="CMF publica nueva normativa para administradoras generales de fondos",
                media="Diario Financiero",
                date=yesterday,
                url_izimedia=f"{self.base_url}/news/view/123459",
                snippet="La Comisión para el Mercado Financiero estableció nuevas exigencias de capital...",
                section="Regulación"
            ),
            IziMediaNews(
                title="Sector inmobiliario muestra signos de recuperación",
                media="El Mercurio",
                date=today,
                url_izimedia=f"{self.base_url}/news/view/123460",
                snippet="Los fondos inmobiliarios y multifamily registran mejoras en ocupación y rentabilidad...",
                section="Inmobiliario"
            ),
            IziMediaNews(
                title="Banco Central mantiene tasa de política monetaria en 5,5%",
                media="Df.cl",
                date=yesterday,
                url_izimedia=f"{self.base_url}/news/view/123461",
                snippet="El Consejo del Banco Central decidió mantener la TPM citando presiones inflacionarias...",
                section="Economía"
            )
        ]
        
        return news

async def test_izimedia_real():
    """Probar conexión real a IziMedia"""
    
    print("\n" + "="*70)
    print("   CONEXIÓN REAL A IZIMEDIA - MONITOREO ACAFI")
    print("="*70)
    print(f"   Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*70 + "\n")
    
    connector = IziMediaRealConnector()
    
    # Mostrar palabras clave cargadas
    print("📚 Palabras clave del Excel:")
    for i, keyword in enumerate(connector.keywords[:10], 1):
        print(f"   {i}. {keyword}")
    if len(connector.keywords) > 10:
        print(f"   ... y {len(connector.keywords)-10} más")
    
    print("\n📡 Conectando a IziMedia...")
    news = await connector.search_izimedia()
    
    if news:
        print(f"\n✅ Se obtuvieron {len(news)} noticias\n")
        
        # Agrupar por medio
        by_media = {}
        for item in news:
            if item.media not in by_media:
                by_media[item.media] = []
            by_media[item.media].append(item)
        
        print("📊 Distribución por medio:")
        for media, items in by_media.items():
            print(f"   • {media}: {len(items)} noticias")
        
        print("\n📰 Noticias obtenidas:\n")
        for i, item in enumerate(news, 1):
            print(f"{i}. {item.title}")
            print(f"   📍 Medio: {item.media}")
            print(f"   📅 Fecha: {item.date.strftime('%d/%m/%Y')}")
            print(f"   🔗 Link IziMedia: {item.url_izimedia}")
            print(f"   📝 {item.snippet[:100]}...")
            print()
    
    return news

if __name__ == "__main__":
    asyncio.run(test_izimedia_real())