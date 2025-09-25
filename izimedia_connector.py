"""
Conector para IziMedia - Plataforma principal de monitoreo
IMPORTANTE: Este es el PRIMER PASO obligatorio del proceso
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import pandas as pd
from loguru import logger
from playwright.async_api import async_playwright, ElementHandle

from config import settings

@dataclass
class IziMediaArticle:
    """Artículo obtenido de IziMedia"""
    title: str
    url: str
    source: str
    published_date: datetime
    content: str
    author: Optional[str] = None
    section: Optional[str] = None


@dataclass
class KeywordRule:
    """Regla de búsqueda para Izimedia"""
    section: str
    theme: str
    include_terms: List[str]
    exclude_terms: List[str]
    media_whitelist: List[str]


class IziMediaConnector:
    """
    Conector para IziMedia - FUENTE PRINCIPAL DE NOTICIAS
    Flujo según documento oficial ACAFI
    """
    
    def __init__(self):
        self.base_url = "https://muba.izimedia.io"
        self.login_url = f"{self.base_url}/authentication/login"
        self.search_url = f"{self.base_url}/dash/mf-search/search"
        
        # Credenciales del documento
        self.credentials = {
            'email': 'btagle@proyectacomunicaciones.cl',
            'password': '345tgb678'
        }
        
        # Palabras clave para búsqueda (del archivo Excel)
        self.keyword_rules = self._load_keywords()

    def _load_keywords(self) -> List[KeywordRule]:
        """Cargar palabras clave, exclusiones y medios desde el Excel oficial"""
        try:
            df = pd.read_excel(
                settings.KEYWORDS_FILE,
                sheet_name=settings.CLIENT_NAME,
                skiprows=2
            )
        except Exception as exc:
            logger.error(f"❌ No fue posible cargar el archivo de palabras clave: {exc}")
            return []

        df = df.rename(columns=lambda c: str(c).strip())
        df = df.dropna(how="all")

        required_columns = {
            'SECCION',
            'TEMA',
            '"Palabras" | (OR)',
            'MEDIOS CLAVES'
        }
        missing = required_columns - set(df.columns)
        if missing:
            logger.error(f"❌ Columnas faltantes en el Excel de palabras clave: {missing}")
            return []

        rules: List[KeywordRule] = []

        for _, row in df.iterrows():
            section = str(row['SECCION']).strip()
            theme = str(row['TEMA']).strip() if pd.notna(row['TEMA']) else ''
            include_raw = str(row['"Palabras" | (OR)']) if pd.notna(row['"Palabras" | (OR)']) else ''
            exclude_raw = str(row.get('TÉRMINOS EXCLUIDOS', '') or '')
            media_raw = str(row['MEDIOS CLAVES']) if pd.notna(row['MEDIOS CLAVES']) else ''

            include_terms = self._parse_pipe_list(include_raw)
            exclude_terms = self._parse_pipe_list(exclude_raw)
            media_whitelist = self._parse_pipe_list(media_raw)

            if not include_terms:
                continue

            rules.append(
                KeywordRule(
                    section=section,
                    theme=theme,
                    include_terms=include_terms,
                    exclude_terms=exclude_terms,
                    media_whitelist=media_whitelist
                )
            )

        logger.info(f"🔑 Cargadas {len(rules)} reglas de palabras clave desde Excel")
        return rules

    @staticmethod
    def _parse_pipe_list(raw: str) -> List[str]:
        """Convertir cadenas del Excel en listas limpias"""
        if not raw:
            return []

        parts = [
            part.strip().strip('"').strip('“”').strip("'")
            for part in raw.split('|')
        ]
        return [part for part in parts if part and part.lower() != 'nan']

    def _build_search_query(self, rule: KeywordRule) -> str:
        """Construir expresión de búsqueda con inclusiones y exclusiones"""
        include = [self._quote_term(term) for term in rule.include_terms if term]
        exclude = [f"-{self._quote_term(term)}" for term in rule.exclude_terms if term]

        query_parts: List[str] = []
        if include:
            query_parts.append(" OR ".join(include))
        if exclude:
            query_parts.append(" ".join(exclude))

        return " ".join(query_parts).strip()

    @staticmethod
    def _quote_term(term: str) -> str:
        """Asegurar que los términos con espacios queden entre comillas"""
        term = term.strip()
        if not term:
            return term
        if ' ' in term and not (term.startswith('"') and term.endswith('"')):
            return f'"{term}"'
        return term

    @staticmethod
    def _normalize_media_name(value: str) -> str:
        return ''.join(ch for ch in value.lower() if ch.isalnum())

    def _passes_filters(self, article: IziMediaArticle, rule: KeywordRule) -> bool:
        """Aplicar exclusiones y lista blanca de medios"""
        text = f"{article.title} {article.content}".lower()

        for term in rule.exclude_terms:
            clean_term = term.strip().lower()
            if clean_term and clean_term in text:
                logger.debug(f"⛔ Excluyendo '{article.title}' por término '{clean_term}'")
                return False

        whitelist = [self._normalize_media_name(m) for m in rule.media_whitelist if m]
        if whitelist and 'todos' not in [m.lower() for m in rule.media_whitelist if m]:
            source_normalized = self._normalize_media_name(article.source)
            if not any(
                allowed in source_normalized or source_normalized in allowed
                for allowed in whitelist
            ):
                logger.debug(f"⛔ Excluyendo '{article.title}' por medio '{article.source}'")
                return False

        return True

    async def _ensure_login_form(self, page) -> None:
        """Asegurarse de que el formulario de login esté visible"""
        possible_tabs = [
            'button:has-text("Iniciar sesión")',
            'button:has-text("Ingresar")',
            'a:has-text("Iniciar sesión")',
            'a:has-text("Ingresar")'
        ]

        for selector in possible_tabs:
            locator = page.locator(selector)
            try:
                if await locator.count() > 0:
                    await locator.first.click()
                    await page.wait_for_timeout(500)
                    break
            except Exception:
                continue

    async def _visible_locator(self, page, selectors: List[str]):
        """Devolver el primer locator visible para la lista de selectores"""
        for selector in selectors:
            locator = page.locator(selector)
            try:
                await locator.wait_for(state='visible', timeout=5000)
                return locator
            except Exception:
                continue
        return None

    async def _find_login_input(self, page, input_type: str):
        """Obtener el input de login evitando campos de recuperación"""

        if input_type == 'email':
            selectors = [
                'input[formcontrolname="email"]',
                'input[type="text"][placeholder="Email"]',
                'input[type="email"][placeholder="Email"]'
            ]
        else:  # password
            selectors = [
                'input[formcontrolname="password"]',
                'input[type="password"]'
            ]

        for selector in selectors:
            locator = page.locator(selector)
            try:
                await locator.wait_for(state='visible', timeout=5000)
            except Exception:
                continue

            count = await locator.count()
            for idx in range(count):
                element = locator.nth(idx)
                try:
                    form_control = await element.get_attribute('formcontrolname') or ''
                except Exception:
                    form_control = ''

                if 'recover' in form_control.lower():
                    continue

                if not await element.is_visible():
                    continue

                return element

        return None

    async def fetch_daily_news(self) -> List[IziMediaArticle]:
        """
        PASO 1 OBLIGATORIO: Obtener noticias de IziMedia

        Flujo exacto según documento:
        1. Login en IziMedia
        2. Ir a búsqueda
        3. Configurar rango de fechas
        4. Buscar con palabras clave
        5. Descargar resultados (máx 5000)
        """
        
        logger.info("="*60)
        logger.info("🔑 PASO 1: CONECTANDO A IZIMEDIA (OBLIGATORIO)")
        logger.info("="*60)
        
        if not self.keyword_rules:
            logger.error("❌ Sin reglas de palabras clave cargadas. Abortando búsqueda en Izimedia.")
            raise ValueError("No hay reglas configuradas para Izimedia")

        articles: List[IziMediaArticle] = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # PASO 1.1: Login
                logger.info("📝 Ingresando a IziMedia...")
                logger.info(f"   URL: {self.login_url}")

                await page.goto(self.login_url)
                await page.wait_for_load_state('networkidle')

                await self._ensure_login_form(page)

                email_field = await self._find_login_input(page, 'email')
                password_field = await self._find_login_input(page, 'password')

                if not email_field or not password_field:
                    raise RuntimeError("No se encontró el formulario de login visible en Izimedia")

                email_attr = await email_field.get_attribute('formcontrolname')
                password_attr = await password_field.get_attribute('formcontrolname')
                logger.debug(f"Campo email detectado: {email_attr}")
                logger.debug(f"Campo password detectado: {password_attr}")

                await email_field.fill(self.credentials['email'])
                await password_field.fill(self.credentials['password'])
                submit_btn = await self._visible_locator(
                    page,
                    [
                        'button[type="submit"]:visible',
                        'button:has-text("Ingresar")',
                        'button:has-text("Iniciar sesión")'
                    ]
                )
                if submit_btn:
                    await submit_btn.click()
                else:
                    await page.keyboard.press('Enter')

                # Esperar login
                await page.wait_for_url(f"{self.base_url}/dash/*", timeout=10000)
                logger.info("   ✅ Login exitoso")

                # PASO 1.2: Ir a búsqueda
                logger.info("🔍 Accediendo a búsqueda...")
                await page.goto(self.search_url)
                await page.wait_for_timeout(2000)

                # PASO 1.3: Configurar fechas
                date_range = self._calculate_date_range()
                logger.info(f"📅 Rango de fechas: {date_range['from']} a {date_range['to']}")

                date_from_container = page.locator('div.dateselect-container:has-text("Desde")')
                date_to_container = page.locator('div.dateselect-container:has-text("Hasta")')

                if await date_from_container.count() and await date_to_container.count():
                    await date_from_container.first.click(force=True)
                    await page.wait_for_selector('.cdk-overlay-container .ngb-dp, .multi-datepicker', timeout=3000)

                    from_year, from_month, from_day = date_range['from'].split('-')
                    from_month = str(int(from_month))
                    from_day = str(int(from_day))

                    to_year, to_month, to_day = date_range['to'].split('-')
                    to_month = str(int(to_month))
                    to_day = str(int(to_day))

                    month_selector = page.locator('.cdk-overlay-container select[ng-reflect-ng-model="month"], .multi-datepicker select[name="month"]')
                    year_selector = page.locator('.cdk-overlay-container select[ng-reflect-ng-model="year"], .multi-datepicker select[name="year"]')

                    if await month_selector.count():
                        await month_selector.first.select_option(from_month)
                    if await year_selector.count():
                        await year_selector.first.select_option(from_year)

                    day_locator = page.locator(
                        f'.cdk-overlay-container .ngb-dp-day button:has-text("{from_day}")',
                    )
                    if not await day_locator.count():
                        day_locator = page.locator(
                            f'.cdk-overlay-container .ngb-dp-day:has-text("{from_day}")'
                        )
                    if not await day_locator.count():
                        day_locator = page.locator(
                            f'.multi-datepicker li.numbers:has-text("{from_day}")'
                        )
                    if await day_locator.count():
                        clicked = False
                        try:
                            await day_locator.first.click(force=True)
                            clicked = True
                        except Exception:
                            pass

                        if not clicked:
                            try:
                                handle = await day_locator.first.evaluate_handle('el => el')
                                await page.evaluate('(el) => el.click()', handle)
                                clicked = True
                            except Exception as second_error:
                                logger.debug(f"No se pudo clicar el día inicial: {second_error}")

                        if not clicked:
                            logger.warning("⚠️ No se pudo seleccionar el día inicial en el calendario")
                    await page.wait_for_timeout(200)

                    await date_to_container.first.click(force=True)
                    await page.wait_for_selector('.cdk-overlay-container .ngb-dp, .multi-datepicker', timeout=3000)

                    month_selector_to = page.locator('.cdk-overlay-container select[ng-reflect-ng-model="month"], .multi-datepicker select[name="month"]')
                    year_selector_to = page.locator('.cdk-overlay-container select[ng-reflect-ng-model="year"], .multi-datepicker select[name="year"]')

                    if await month_selector_to.count():
                        await month_selector_to.first.select_option(to_month)
                    if await year_selector_to.count():
                        await year_selector_to.first.select_option(to_year)

                    day_to_locator = page.locator(
                        f'.cdk-overlay-container .ngb-dp-day button:has-text("{to_day}")'
                    )
                    if not await day_to_locator.count():
                        day_to_locator = page.locator(
                            f'.cdk-overlay-container .ngb-dp-day:has-text("{to_day}")'
                        )
                    if not await day_to_locator.count():
                        day_to_locator = page.locator(
                            f'.multi-datepicker li.numbers:has-text("{to_day}")'
                        )
                    if await day_to_locator.count():
                        clicked_to = False
                        try:
                            await day_to_locator.first.click(force=True)
                            clicked_to = True
                        except Exception:
                            pass

                        if not clicked_to:
                            try:
                                handle_to = await day_to_locator.first.evaluate_handle('el => el')
                                await page.evaluate('(el) => el.click()', handle_to)
                                clicked_to = True
                            except Exception as second_error:
                                logger.debug(f"No se pudo clicar el día final: {second_error}")

                        if not clicked_to:
                            logger.warning("⚠️ No se pudo seleccionar el día final en el calendario")
                    await page.wait_for_timeout(200)
                else:
                    logger.warning("⚠️ No se pudo localizar el selector de fechas en Izimedia")

                # PASO 1.4: Buscar con palabras clave
                logger.info("🔎 Buscando con palabras clave...")

                for rule in self.keyword_rules:
                    query = self._build_search_query(rule)
                    if not query:
                        continue

                    logger.info(f"   • {rule.section} | {rule.theme}: {query}")

                    # Ingresar palabra clave
                    search_input = await self._visible_locator(
                        page,
                        [
                            'input[placeholder="Búsqueda estándar"]',
                            'input[name="search"]'
                        ]
                    )

                    if not search_input:
                        logger.warning("⚠️ No se encontró el campo de búsqueda principal")
                        continue

                    await search_input.click()
                    await search_input.fill('')
                    await search_input.type(query, delay=30)

                    search_button = await self._visible_locator(
                        page,
                        [
                            'button:has-text("Buscar")',
                            'button[type="submit"]'
                        ]
                    )

                    if search_button:
                        await search_button.click()
                    else:
                        await search_input.press('Enter')

                    try:
                        await page.wait_for_selector('table.table-striped.izitable-search tbody tr', timeout=6000)
                        results = await page.query_selector_all('table.table-striped.izitable-search tbody tr')
                    except Exception as wait_error:
                        logger.warning(f"   ⚠️ Sin resultados visibles para la query: {wait_error}")
                        await search_input.fill('')
                        continue

                    limit = settings.NEWSLETTER_MAX_ARTICLES_PER_SECTION * 3
                    for result in results[:limit]:
                        article = await self._parse_result(result)
                        if not article:
                            continue

                        if not self._passes_filters(article, rule):
                            continue

                        article.section = rule.section
                        articles.append(article)

                    # Limpiar búsqueda
                    await search_input.fill('')

                logger.info(f"✅ Total de noticias obtenidas (sin filtrar duplicados): {len(articles)}")

                # NOTA IMPORTANTE del documento:
                # "Hay un límite de 5000 noticias por descarga"
                if len(articles) >= 5000:
                    logger.warning("⚠️ LÍMITE DE 5000 NOTICIAS ALCANZADO")
                    logger.warning("   Reducir filtros según documento")

            except Exception as e:
                logger.error(f"❌ Error en IziMedia: {e}")
                # Si falla IziMedia, intentar método alternativo
                articles = self._fallback_method()

            finally:
                await browser.close()
        
        articles = self._deduplicate_articles(articles)
        logger.info(f"🗂️  Noticias únicas tras deduplicar: {len(articles)}")

        if len(articles) == 0:
            logger.error("❌ NO SE OBTUVIERON NOTICIAS DE IZIMEDIA")
            raise ValueError("IziMedia es obligatorio - No se puede continuar sin noticias")

        return articles
    
    def _calculate_date_range(self) -> Dict[str, str]:
        """
        Calcular rango de fechas según el día
        Reglas del documento:
        - Martes a Viernes: día anterior hasta hoy
        - Lunes y feriados: día hábil anterior hasta hoy
        """
        today = datetime.now()
        weekday = today.weekday()  # 0=Lunes, 6=Domingo
        
        if weekday == 0:  # Lunes
            # Desde el viernes
            from_date = today - timedelta(days=3)
        else:
            # Día anterior
            from_date = today - timedelta(days=1)
        
        return {
            'from': from_date.strftime('%Y-%m-%d'),
            'to': today.strftime('%Y-%m-%d')
        }
    
    async def _parse_result(self, element: ElementHandle) -> Optional[IziMediaArticle]:
        """Parsear un resultado de búsqueda"""
        try:
            # Intentar parsear como fila de tabla
            cells = await element.query_selector_all('td')
            if cells:
                source = ''
                title = ''
                url = ''
                date_str = ''
                content = ''

                if len(cells) >= 2:
                    source = (await cells[1].inner_text()).strip()

                if len(cells) >= 3:
                    link_el = await cells[2].query_selector('a')
                    if link_el:
                        title = (await link_el.inner_text()).strip()
                        url = await link_el.get_attribute('href') or ''
                    else:
                        title = (await cells[2].inner_text()).strip()
                else:
                    link_el = None

                if len(cells) >= 4:
                    date_str = (await cells[3].inner_text()).strip()

                if not url and 'href' in (await element.inner_html()):
                    # Intentar atributo data-url si existe
                    url = await element.get_attribute('data-url') or ''

                if not url:
                    logger.debug("Fila sin URL, se omite")
                    return None

                pub_date = self._parse_date(date_str)

                return IziMediaArticle(
                    title=title or 'Sin título',
                    url=url,
                    source=source or 'Desconocido',
                    published_date=pub_date,
                    content=content
                )

            # Fallback al formato anterior
            title_el = await element.query_selector('.title')
            source_el = await element.query_selector('.source')
            date_el = await element.query_selector('.date')
            link_el = await element.query_selector('a')
            snippet_el = await element.query_selector('.snippet')

            if not all([title_el, source_el, date_el, link_el]):
                return None

            title = (await title_el.inner_text()).strip()
            source = (await source_el.inner_text()).strip()
            date_str = (await date_el.inner_text()).strip()
            url = await link_el.get_attribute('href')
            content = (await snippet_el.inner_text()).strip() if snippet_el else ''

            if not url:
                return None

            pub_date = self._parse_date(date_str)

            return IziMediaArticle(
                title=title,
                url=url,
                source=source,
                published_date=pub_date,
                content=content
            )
        except Exception as e:
            logger.debug(f"Error parseando resultado: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """Intentar parsear fecha en varios formatos"""
        if not date_str:
            return datetime.utcnow()

        formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.debug(f"No se pudo parsear la fecha '{date_str}', se usa fecha actual")
        return datetime.utcnow()
    
    def _fallback_method(self) -> List[IziMediaArticle]:
        """Método alternativo si falla el scraping"""
        logger.warning("⚠️ Usando método alternativo (API si existe)")
        
        # Intentar API REST si existe
        try:
            headers = {
                'Authorization': f'Bearer {self._get_token()}',
                'Content-Type': 'application/json'
            }
            
            date_range = self._calculate_date_range()
            
            # Construir query
            include_terms: List[str] = []
            for rule in self.keyword_rules:
                include_terms.extend(rule.include_terms)
            query = ' OR '.join(self._quote_term(term) for term in include_terms[:20])
            
            payload = {
                'query': query,
                'date_from': date_range['from'],
                'date_to': date_range['to'],
                'limit': 1000
            }
            
            response = requests.post(
                f"{self.base_url}/api/search",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = []
                
                for item in data.get('results', []):
                    article = IziMediaArticle(
                        title=item['title'],
                        url=item['url'],
                        source=item['source'],
                        published_date=datetime.fromisoformat(item['date']),
                        content=item.get('content', '')
                    )
                    articles.append(article)
                
                return articles
            
        except Exception as e:
            logger.error(f"Error en fallback: {e}")
        
        return []

    def _get_token(self) -> str:
        """Obtener token de autenticación"""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=self.credentials,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json().get('token', '')
        except:
            pass
        
        return ""
    
    def export_to_excel(self, articles: List[IziMediaArticle], filename: str = None):
        """Exportar resultados a Excel como en el flujo manual"""
        import pandas as pd
        
        if not filename:
            filename = f"izimedia_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        data = []
        for article in articles:
            data.append({
                'Fecha': article.published_date.strftime('%d/%m/%Y'),
                'Medio': article.source,
                'Título': article.title,
                'URL': article.url,
                'Contenido': article.content[:500],  # Primeros 500 caracteres
                'Sección': article.section or 'General'
            })
        
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)

        logger.info(f"📊 Exportado a Excel: {filename}")
        return filename

    def _deduplicate_articles(self, articles: List[IziMediaArticle]) -> List[IziMediaArticle]:
        """Eliminar duplicados priorizando medios principales"""
        priority = {
            'diariofinanciero': 3,
            'elmercurio': 2,
            'latercera': 1
        }

        unique: Dict[str, IziMediaArticle] = {}

        for article in articles:
            key = article.url or article.title
            normalized_source = self._normalize_media_name(article.source)
            score = priority.get(normalized_source, 0)

            if key not in unique:
                unique[key] = article
                continue

            existing = unique[key]
            existing_score = priority.get(self._normalize_media_name(existing.source), 0)

            if score > existing_score:
                unique[key] = article

        return list(unique.values())

class IziMediaValidator:
    """Validador para asegurar que IziMedia funciona correctamente"""
    
    @staticmethod
    def validate_connection() -> bool:
        """Verificar que podemos conectar a IziMedia"""
        try:
            response = requests.get(
                "https://muba.izimedia.io/authentication/login",
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def validate_articles(articles: List[IziMediaArticle]) -> tuple[bool, str]:
        """Validar que los artículos son válidos"""
        if len(articles) == 0:
            return False, "No hay artículos"
        
        if len(articles) < 10:
            return False, f"Muy pocos artículos ({len(articles)})"
        
        # Verificar que no son muy antiguos
        today = datetime.now()
        for article in articles:
            age = today - article.published_date
            if age.days > 7:
                return False, f"Artículos muy antiguos (>{age.days} días)"
        
        return True, f"✅ {len(articles)} artículos válidos"
