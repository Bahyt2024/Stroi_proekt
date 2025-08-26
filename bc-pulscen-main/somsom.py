import os
import re
import json
import asyncio
import logging
import time
import threading
import webbrowser
import pyautogui
from datetime import datetime
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from openai import AsyncOpenAI

# Импорты из наших модулей
from config import (
    OPENAI_API_KEY, BROWSER_USER_AGENT, BROWSER_VIEWPORT, BROWSER_ARGS,
    PAGE_TIMEOUT, SELLER_PAGE_TIMEOUT, PRODUCT_PAGE_TIMEOUT, MAX_PAGES
)
from models import ProductQuery, pulscen_get_subdomain
from utils import (
    extract_phone_number, extract_dates_from_main_page, get_current_date,
    get_current_year_quarter
)
from ai_services import (
    perplexity_search_product_cards, gpt_check_product_match,
    extract_text_from_image, gpt_extract_data_from_screenshot
)
from company_extractor import extract_company_data
from pdf_generator import create_pdf_with_fpdf
import aiohttp

def auto_screenshot_system():
    """
    Автоматически открывает сайт в браузере и делает скриншот всего экрана
    """
    try:
        # Ждем немного, чтобы сервер запустился
        time.sleep(3)
        
        # URL сайта
        url = "http://localhost:8000"
        
        print(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 Открываю сайт в браузере: {url}")
        
        # Открываем сайт в браузере по умолчанию
        webbrowser.open(url)
        
        # Ждем 8 секунд, чтобы сайт полностью загрузился
        print("⏳ Ждем загрузки сайта в браузере...")
        time.sleep(8)
        
        # Делаем скриншот всего экрана
        print("📸 Делаем скриншот всего экрана...")
        
        # Создаем папку для скриншотов, если её нет
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Генерируем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{screenshots_dir}/fullscreen_screenshot_{timestamp}.png"
        
        # Делаем скриншот всего экрана
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_filename)
        
        print(f"✅ Скриншот всего экрана сохранен: {screenshot_filename}")
        print(f"🕐 Время создания скриншота: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Размер скриншота: {screenshot.size}")
        print(f"🖥️ Разрешение экрана: {pyautogui.size()}")
        
        return screenshot_filename
        
    except Exception as e:
        print(f"❌ Ошибка автоматического скриншота: {e}")
        return None

# Функция валидации URL с улучшенной проверкой
async def validate_url(url: str, timeout: int = 15, retries: int = 3) -> bool:
    """Проверяет доступность URL с повторными попытками"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for attempt in range(retries):
        try:
            connector = aiohttp.TCPConnector(ssl=False)  # Отключаем SSL проверку
            timeout_config = aiohttp.ClientTimeout(total=timeout, connect=5)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout_config, headers=headers) as session:
                # Сначала пробуем HEAD запрос
                try:
                    async with session.head(url, allow_redirects=True) as response:
                        if 200 <= response.status < 400:
                            logger.info(f"[URL-VALID] ✅ HEAD {url} → {response.status}")
                            return True
                        else:
                            logger.warning(f"[URL-INVALID] HEAD {url} → {response.status}")
                except:
                    # Если HEAD не работает, пробуем GET
                    async with session.get(url, allow_redirects=True) as response:
                        if 200 <= response.status < 400:
                            logger.info(f"[URL-VALID] ✅ GET {url} → {response.status}")
                            return True
                        else:
                            logger.warning(f"[URL-INVALID] GET {url} → {response.status}")
                            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"[URL-VALIDATION] Attempt {attempt + 1}/{retries} failed for {url}: {error_msg}")
            
            # Быстро отклоняем известные недоступные ошибки
            if any(err in error_msg for err in [
                "Name or service not known", 
                "Connection refused", 
                "SSL",
                "certificate",
                "timeout"
            ]):
                logger.warning(f"[URL-INVALID] ❌ Quick reject {url}: {error_msg}")
                return False
                
            # Пауза перед повтором только для других ошибок
            if attempt < retries - 1:
                await asyncio.sleep(1)
    
    logger.warning(f"[URL-INVALID] ❌ All {retries} attempts failed for {url}")
    return False

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация FastAPI для работы через туннели
app = FastAPI(
    title="Pulscen Parser API",
    description="API для парсинга товаров с pulscen.ru",
    version="1.0.0"
)

@app.get("/screenshot")
async def take_system_screenshot():
    """
    Создает скриншот всего экрана
    """
    try:
        # Создаем папку для скриншотов, если её нет
        screenshots_dir = "system_screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Генерируем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = f"{screenshots_dir}/manual_fullscreen_{timestamp}.png"
        
        # Делаем скриншот всего экрана
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_filename)
        
        return {
            "success": True,
            "message": "Скриншот всего экрана создан успешно",
            "filename": screenshot_filename,
            "timestamp": datetime.now().isoformat(),
            "size": f"{screenshot.size[0]}x{screenshot.size[1]}",
            "screen_resolution": f"{pyautogui.size()[0]}x{pyautogui.size()[1]}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Добавляем middleware для работы через туннели
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# CORS для работы с внешними клиентами
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host для защиты от Host header атак
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # В продакшене указать конкретные хосты
)

print("FastAPI app created successfully!")

# Инициализация OpenAI клиента
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

@app.post("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Server is working"}

@app.post("/debug_collect")
async def debug_collect_offers(data: dict):
    print("DEBUG_COLLECT CALLED!")
    logger.info(f"DEBUG: Received data: {data}")
    try:
        return {"status": "received", "data": data}
    except Exception as e:
        logger.error(f"DEBUG ERROR: {str(e)}")
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "Server is running"}

@app.post("/simple_test")
async def simple_test():
    print("SIMPLE_TEST CALLED!")
    return {"message": "Simple test works"}

@app.post("/validate_test")
async def validate_test(query: ProductQuery):
    print("VALIDATE_TEST CALLED!")
    print(f"Received query: {query}")
    return {"message": "Validation works", "data": query.model_dump()}

@app.post("/collect_offers")
async def collect_offers(query: ProductQuery):
    print("=" * 50)
    print("COLLECT_OFFERS CALLED!")
    print(f"Received query: {query}")
    print("=" * 50)
    logger.info("COLLECT_OFFERS FUNCTION STARTED")
    
    try:
        logger.info(f"Starting collect_offers with query: {query}")
        name, code, weight, number, city, monitor = query.name, query.code, query.weight, query.number, query.city, query.monitor
        # number - это стартовый номер п/п в таблице, но всегда парсим 3 карточки
        cards_to_parse = 3
        logger.info(f"Extracted variables: name={name}, code={code}, weight={weight}, number={number} (start row), city={city}, monitor={monitor}")
        try:
            int_number = int(number)
            logger.info(f"DEBUG: number type={type(number)}, number value='{number}', int(number)={int_number}")
        except (ValueError, TypeError) as e:
            logger.error(f"DEBUG: Invalid number '{number}': {e}")
            int_number = 1

        # Безопасное формирование имени папки для output
        safe_code = str(code).strip() if str(code).strip() else "unknown_code"
        safe_name = str(query.name).strip() if str(query.name).strip() else "unknown_name"
        safe_code = re.sub(r'[^\w\-]', '_', safe_code)
        safe_name = re.sub(r'[^\w\-]', '_', safe_name)
        
        # Ограничиваем длину названия (максимум 100 символов для safe_name)
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        out_dir = f"output/{safe_code}_{safe_name}"
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Created output directory: {out_dir}")

        logger.info("Starting Playwright...")
        print("About to start Playwright...")
        
        # Проверяем установку Playwright браузеров
        try:
            from playwright.async_api import async_playwright
            logger.info("Playwright imported successfully")
        except ImportError as e:
            logger.error(f"Playwright import failed: {e}")
            raise HTTPException(status_code=500, detail="Playwright not installed")
        
        async with async_playwright() as p:
            print("Playwright started, launching browser...")
            browser = await p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS
            )
            print("Browser launched successfully!")
            context = await browser.new_context(
                user_agent=BROWSER_USER_AGENT,
                viewport=BROWSER_VIEWPORT
            )

            try:
                page = await context.new_page()

                # Формируем ссылку с правильным поддоменом
                subdomain = pulscen_get_subdomain(query.city)
                if subdomain:
                    search_url = f"https://{subdomain}.pulscen.ru/search/price?q={query.name.replace(' ', '+')}"
                else:
                    search_url = f"https://pulscen.ru/search/price?q={query.name.replace(' ', '+')}"
                await page.goto(search_url, timeout=PAGE_TIMEOUT)

                elements = await page.query_selector_all("a.product-listing__product-name")
                if not elements:
                    raise HTTPException(status_code=404, detail="Товары не найдены")

                # Поиск товаров на Pulscen
                found_count = 0
                page_num = 1
                found_companies = []
                yes_company_names, yes_links, yes_product_names, yes_prices, yes_currencies, yes_addresses, yes_phones = [], [], [], [], [], [], []
                stop_search = False
                
                while found_count < cards_to_parse and page_num <= MAX_PAGES and not stop_search:
                    product_articles = await page.query_selector_all('article.product-listing__item-wrapper')
                    logger.info(f"[PULSCEN] Страница {page_num}, найдено карточек: {len(product_articles)}")
                    
                    for article in product_articles:
                        if found_count >= cards_to_parse:
                            stop_search = True
                            break
                        try:
                            product_name_elem = await article.query_selector('a.product-listing__product-name')
                            product_name = await product_name_elem.text_content() if product_name_elem else "не указано"
                            href = await product_name_elem.get_attribute("href") if product_name_elem else ""
                            full_link = f"https://www.pulscen.ru{href}" if href and not href.startswith("http") else href
                            
                            company_elem = await article.query_selector('span.product-listing__company-name-wrapper')
                            company_name_raw = await company_elem.text_content() if company_elem else "не указано"
                            company_name = company_name_raw.replace('\n', ' ').strip()
                            if "г." in company_name:
                                company_name = company_name.split("г.")[0].strip()
                            
                            price_elem = await article.query_selector('i[data-price-type="discount-new"]')
                            if not price_elem:
                                price_elem = await article.query_selector('i[data-price-type="exact"]')
                            if not price_elem:
                                price_from_elem = await article.query_selector('span[data-price-type="from"]')
                                price_to_elem = await article.query_selector('span[data-price-type="to"]')
                                if price_from_elem and price_to_elem:
                                    price_from = await price_from_elem.text_content()
                                    price_to = await price_to_elem.text_content()
                                    price = f"от {price_from} до {price_to}"
                                elif price_from_elem:
                                    price = f"от {await price_from_elem.text_content()}"
                                else:
                                    price = ""
                            else:
                                price = await price_elem.text_content()

                            if not price:
                                logger.info(f"[FILTER] Пропуск: нет цены у '{product_name}'")
                                continue
                            
                            currency_elem = await article.query_selector('span.price-currency')
                            currency = await currency_elem.text_content() if currency_elem else "руб."
                            address_elem = await article.query_selector('div.product-listing__address')
                            extracted_address = await address_elem.text_content() if address_elem else ""
                            
                            # Проверка соответствия товара через GPT
                            is_match = await gpt_check_product_match(query.name, product_name, company_name, list(found_companies), client)
                            logger.info(f"[GPT-CHECK] '{product_name}' (цена: '{price}', компания: '{company_name}') <==> '{query.name}' → Ответ: {is_match}")
                            
                            if is_match == "да":
                                if company_name not in found_companies:
                                    logger.info(f"[ADD-COMPANY] Добавляем новую компанию: '{company_name}' (найдено: {len(found_companies)})")
                                    found_companies.append(company_name)
                                    yes_company_names.append(company_name)
                                    yes_links.append(full_link)
                                    yes_product_names.append(product_name)
                                    yes_prices.append(price)
                                    yes_currencies.append(currency.strip())
                                    yes_addresses.append(extracted_address)
                                    yes_phones.append("")
                                    found_count = len(found_companies)
                                    logger.info(f"[ADD-COMPANY] Всего найдено компаний: {found_count}")
                                    if found_count >= cards_to_parse:
                                        stop_search = True
                                        break
                                else:
                                    logger.info(f"[SKIP-DUPLICATE] Компания '{company_name}' уже найдена. Список: {found_companies}")
                            else:
                                logger.info(f"[FILTER] Пропуск: GPT ответил '{is_match}' для '{product_name}'")
                        except Exception as e:
                            logger.error(f"Ошибка при обработке товара: {e}")
                            continue
                    
                    if found_count >= cards_to_parse:
                        break
                    
                    # Переход на следующую страницу
                    page_num += 1
                    if page_num > MAX_PAGES:
                        logger.info(f"[PULSCEN] Достигнут лимит страниц ({MAX_PAGES}). Переходим к Perplexity, если не найдено {cards_to_parse} товара.")
                        break
                    
                    logger.info(f"[PULSCEN] Переход на страницу {page_num}")
                    next_page_elem = await page.query_selector(f'a.pagination__link.js-ga-link:text("{page_num}")')
                    if not next_page_elem:
                        logger.info(f"[PULSCEN] Следующая страница {page_num} не найдена. Останавливаем поиск.")
                        break
                    next_page_url = await next_page_elem.get_attribute('href')
                    if not next_page_url:
                        logger.info(f"[PULSCEN] Не удалось получить ссылку на страницу {page_num}. Останавливаем поиск.")
                        break
                    if next_page_url.startswith('http'):
                        await page.goto(next_page_url, timeout=PAGE_TIMEOUT)
                    else:
                        await page.goto(f"https://www.pulscen.ru{next_page_url}", timeout=PAGE_TIMEOUT)

                # Замена на Perplexity если нужно
                if not yes_company_names or len(yes_company_names) < cards_to_parse:
                    needed = cards_to_parse - len(yes_company_names)
                    logger.info(f"[PULSCEN] Не найдено {needed} карточек, полностью переходим к Perplexity!")
                    try:
                        # Полностью заменяем результаты Pulscen на Perplexity (3 товара)
                        perplexity_results = []
                        failed_urls = []  # Список недоступных URL для исключения
                        failed_domains = set()  # Набор недоступных доменов
                        attempts = 0
                        max_attempts = 10
                        
                        logger.info(f"[PERPLEXITY-START] Начинаем поиск с максимум {max_attempts} попытками для получения 3 товаров")
                        
                        # Повторяем запросы пока не получим 3 товара
                        while len(perplexity_results) < 3 and attempts < max_attempts:
                            attempts += 1
                            logger.info(f"[PERPLEXITY] Попытка {attempts}/{max_attempts}: поиск товаров через Perplexity")
                            logger.info(f"[PERPLEXITY] Текущий прогресс: {len(perplexity_results)}/3 товаров найдено")
                            
                            # Передаем все failed_urls для исключения
                            current_results = await perplexity_search_product_cards(query.name, count=3, attempt=attempts, exclude_urls=failed_urls)
                            
                            logger.info(f"[PERPLEXITY] Получено {len(current_results)} результатов от Perplexity на попытке {attempts}")
                            
                            # Добавляем новые уникальные товары
                            existing_companies = [item["company"].replace("«", "\"").replace("»", "\"").strip() for item in perplexity_results]
                            existing_urls = [item["url"] for item in perplexity_results]
                            
                            for i, item in enumerate(current_results):
                                normalized_company = item["company"].replace("«", "\"").replace("»", "\"").strip()
                                item_domain = item["url"].split('/')[2] if item["url"].startswith('http') else item["url"]
                                
                                logger.info(f"[PERPLEXITY] Проверяем товар {i+1}: {item['company']} | {item_domain}")
                                
                                # Проверяем, не исключен ли уже этот домен
                                if item_domain in failed_domains:
                                    logger.warning(f"[PERPLEXITY] 🚫 Домен {item_domain} уже в списке недоступных, пропускаем")
                                    continue
                                    
                                if normalized_company not in existing_companies and item["url"] not in existing_urls and len(perplexity_results) < 3:
                                    # Валидация URL перед добавлением
                                    logger.info(f"[PERPLEXITY] 🔍 Проверка доступности URL: {item['url']}")
                                    url_valid = await validate_url(item["url"])
                                    if url_valid:
                                        perplexity_results.append(item)
                                        logger.info(f"[PERPLEXITY] ✅ Найден валидный товар {len(perplexity_results)}/3: {item['company']} | {item['name']}")
                                    else:
                                        logger.warning(f"[PERPLEXITY] ❌ URL недоступен, пропускаем: {item['url']} | {item['company']}")
                                        failed_urls.append(item['url'])  # Добавляем в список недоступных URL
                                        failed_domains.add(item_domain)  # Добавляем домен в список недоступных
                                        logger.info(f"[PERPLEXITY] 📝 Добавлен недоступный домен: {item_domain} (всего исключений: {len(failed_domains)})")
                                else:
                                    if normalized_company in existing_companies:
                                        logger.info(f"[PERPLEXITY] 🔄 Пропуск дубля компании: {normalized_company}")
                                    elif item["url"] in existing_urls:
                                        logger.info(f"[PERPLEXITY] 🔄 Пропуск дубля URL: {item['url']}")
                                    elif len(perplexity_results) >= 3:
                                        logger.info(f"[PERPLEXITY] ⏹️ Уже найдено 3 товара, пропускаем остальные")
                            
                            if len(perplexity_results) < 3:
                                logger.warning(f"[PERPLEXITY] Попытка {attempts}: найдено только {len(perplexity_results)} валидных товаров из 3")
                                logger.info(f"[PERPLEXITY] Исключенных доменов: {len(failed_domains)}, исключенных URL: {len(failed_urls)}")
                                # Если недостаточно валидных товаров, продолжаем поиск
                        
                        if len(perplexity_results) < 3:
                            logger.error(f"[PERPLEXITY] После {max_attempts} попыток найдено только {len(perplexity_results)} товаров")
                        
                        # Очищаем результаты Pulscen и используем только Perplexity
                        yes_company_names, yes_links, yes_product_names, yes_prices, yes_currencies, yes_addresses, yes_phones = [], [], [], [], [], [], []
                        for item in perplexity_results[:3]:  # Строго до 3 товаров
                            yes_company_names.append(item["company"])
                            yes_links.append(item["url"])
                            yes_product_names.append(item["name"])
                            yes_prices.append(item["price"])
                            yes_currencies.append("")
                            yes_addresses.append(item["address"])
                            yes_phones.append(item["phone"])
                            logger.info(f"[PERPLEXITY] Добавлена карточка: {item['company']} | {item['name']}")
                    except Exception as e:
                        logger.error(f"[PERPLEXITY] Ошибка при поиске через Perplexity: {e}")

                dates = await extract_dates_from_main_page(page)
                results = []

                # Добавляем отладочную информацию о найденных данных
                logger.info(f"[RESULTS-DEBUG] Найдено компаний: {len(yes_company_names)}")
                logger.info(f"[RESULTS-DEBUG] Найдено ссылок: {len(yes_links)}")
                for debug_idx, debug_link in enumerate(yes_links):
                    logger.info(f"[RESULTS-DEBUG] Link {debug_idx}: '{debug_link}' | Company: '{yes_company_names[debug_idx] if debug_idx < len(yes_company_names) else 'N/A'}'")

                # Обработка найденных товаров
                current_year, current_quarter = get_current_year_quarter()
                
                for idx, link in enumerate(yes_links):
                    await asyncio.sleep(0)
                    
                    logger.info(f"[PROCESSING] Обрабатываем товар {idx+1}/{len(yes_links)}: {link}")
                    pdf_filename = "не сгенерирован"
                    if not link:
                        logger.warning(f"[PROCESSING] Пропускаем товар {idx+1} - пустая ссылка")
                        continue

                    product_page = await context.new_page()
                    seller_page = None
                    company_data = {
                        "company_n": "не указан",
                        "email": "не указан",
                        "inn": "не найдено",
                        "kpp": "не найдено",
                        "phone": "не найдено",
                        "address": "не найдено",
                        "formula": "не найдено"
                    }
                    
                    try:
                        await product_page.goto(link, wait_until="domcontentloaded", timeout=PRODUCT_PAGE_TIMEOUT)

                        company_name = yes_company_names[idx].replace('\n', ' ').strip() if isinstance(yes_company_names[idx], str) else yes_company_names[idx]
                        material_name = yes_product_names[idx].replace('\n', ' ').strip() if isinstance(yes_product_names[idx], str) else yes_product_names[idx]
                        price_info = {
                            "price": yes_prices[idx],
                            "currency": yes_currencies[idx]
                        }
                        logger.info(f"Извлечение текста страницы")

                        phone_number = await extract_phone_number(product_page)

                        # Извлечение данных о доставке
                        try:
                            delivery_elem = await product_page.query_selector("div.product-deliveries__name")
                            delivery_method = await delivery_elem.inner_text() if delivery_elem else ""
                            if isinstance(delivery_method, str):
                                delivery_method = delivery_method.replace('\n', ' ').strip()
                        except Exception:
                            delivery_method = ""

                        # Извлечение адреса
                        try:
                            address_elem = await product_page.query_selector("div.footer-bottom__address")
                            raw_address = await address_elem.inner_text() if address_elem else ""

                            phone_pattern = r'(?:\\+7|8|7)[\\s\\-\\(\\)]*\\d{3}[\\s\\-\\(\\)]*\\d{3}[\\s\\-\\(\\)]*\\d{2}[\\s\\-\\(\\)]*\\d{2}'
                            phone_match = re.search(phone_pattern, raw_address)
                            if phone_match:
                                address_part = raw_address[:phone_match.start()]
                            else:
                                address_part = raw_address

                            pattern = r"(г\\.|город|пос\\.|пгт|деревня|село)[^+]{10,1000}"
                            match = re.search(pattern, address_part, flags=re.IGNORECASE)
                            if match:
                                extracted_address = match.group(0).strip()
                                extracted_address = re.sub(r"[\\s,;]+$", "", extracted_address)
                                STOP_WORDS = [
                                    "въезд", "подъезд", "выезд", "проезд", "переезд", "объезд", "приезд",
                                    "въезжая", "выезжающий", "объезжающий", "проезжающий", "переезжающий"
                                ]
                                for word in STOP_WORDS:
                                    extracted_address = re.sub(rf"\\b{word}\\b.*", "", extracted_address, flags=re.IGNORECASE)
                                extracted_address = re.sub(r"[\\s,;]+$", "", extracted_address)
                                if not extracted_address.strip():
                                    extracted_address = "не найдено"
                            else:
                                extracted_address = ""
                        except Exception:
                            extracted_address = "не найдено"

                        # Парсинг характеристик товара
                        try:
                            characteristics = {}
                            char_block = await product_page.query_selector('div.product-tabber__body.js-product-tabber-content')
                            if char_block:
                                logger.info("[CHAR] Найден блок характеристик товара, начинаю парсинг...")
                                items = await char_block.query_selector_all('div.product-description-list__item')
                                for item in items:
                                    label_elem = await item.query_selector('span.product-description-list__label')
                                    value_elem = await item.query_selector('span.product-description-list__value')
                                    if label_elem and value_elem:
                                        label = (await label_elem.inner_text()).strip()
                                        value_texts = []
                                        for node in await value_elem.query_selector_all('a, span, text()'):
                                            try:
                                                txt = await node.inner_text()
                                                if txt:
                                                    value_texts.append(txt.strip())
                                            except Exception:
                                                pass
                                        if not value_texts:
                                            value_texts = [(await value_elem.inner_text()).strip()]
                                        value = ", ".join(value_texts)
                                        characteristics[label] = value
                                        logger.info(f"[CHAR] {label}: {value}")
                            else:
                                logger.info("[CHAR] Блок характеристик товара не найден.")
                            
                            # Парсинг описания товара
                            try:
                                descr_block = await product_page.query_selector('div.product-tabber__body.js-product-tabber-content#tab-description div.product-description.js-apb-descr')
                                if descr_block:
                                    paragraphs = await descr_block.query_selector_all('p')
                                    description_texts = []
                                    for p in paragraphs:
                                        txt = await p.inner_text()
                                        if txt:
                                            description_texts.append(txt.strip())
                                    description = ' '.join(description_texts)
                                    words = description.split()
                                    if len(words) > 70:
                                        description = ' '.join(words[:70]) + '...'
                                    characteristics['Описание'] = description
                                    logger.info(f"[CHAR] Описание (до 70 слов): {description[:200]}...")
                                else:
                                    logger.info("[CHAR] Блок описания товара не найден.")
                            except Exception as e:
                                logger.warning(f"[CHAR] Ошибка при парсинге описания: {e}")
                        except Exception as e:
                            logger.warning(f"[CHAR] Ошибка при парсинге характеристик: {e}")

                        # Получение сайта продавца
                        try:
                            seller_site_elem = await product_page.query_selector("a.js-ykr-action")
                            seller_site = await seller_site_elem.get_attribute("href") if seller_site_elem else ""
                        except Exception:
                            seller_site = ""
                        
                        if not seller_site:
                            seller_site = link
                        
                        date = get_current_date()
                        logger.info(f"[DEBUG] Проверка seller_site: {seller_site}")
                        
                        if seller_site and seller_site.startswith(("http://", "https://")):
                            seller_page = await context.new_page()
                            
                            # Устанавливаем размер viewport для корректного отображения
                            await seller_page.set_viewport_size({"width": 1920, "height": 1080})
                            
                            try:
                                # Устанавливаем обработчик консоли для отладки
                                seller_page.on("console", lambda msg: logger.debug(f"Console: {msg.text}"))
                                
                                await seller_page.goto(seller_site, timeout=SELLER_PAGE_TIMEOUT, wait_until='domcontentloaded')
                                
                                # Проверяем, что страница действительно загружена
                                try:
                                    # Ждем стабилизации страницы
                                    await asyncio.sleep(2)
                                    
                                    # Проверяем, что контекст не уничтожен
                                    page_url = seller_page.url
                                    if page_url and not seller_page.is_closed():
                                        logger.info(f"Страница стабильна: {page_url}")
                                    else:
                                        raise Exception("Page context is destroyed or closed")
                                        
                                except Exception as stability_error:
                                    logger.warning(f"Проблема стабильности страницы {seller_site}: {stability_error}")
                                    # Пробуем перезагрузить страницу
                                    try:
                                        await seller_page.reload(timeout=10000, wait_until='domcontentloaded')
                                        await asyncio.sleep(2)
                                        logger.info(f"Страница перезагружена: {seller_site}")
                                    except Exception as reload_error:
                                        logger.error(f"Не удалось перезагрузить страницу: {reload_error}")
                                        raise reload_error
                                        
                            except Exception as goto_error:
                                logger.error(f"Ошибка загрузки страницы {seller_site}: {goto_error}")
                                seller_page = None
                            
                            if seller_page and not seller_page.is_closed():
                                logger.info(f"Извлечение текста страницы")
                                try:
                                    page_text = await seller_page.evaluate("() => document.body.textContent")
                                    description = characteristics.get('Описание', '') if characteristics else ''
                                except Exception as text_error:
                                    logger.error(f"Ошибка извлечения текста со страницы продавца: {text_error}")
                                    page_text = ""
                                    description = characteristics.get('Описание', '') if characteristics else ''
                            else:
                                logger.warning(f"Страница не загружена, используем данные с основной страницы")
                                page_text = ""
                                description = characteristics.get('Описание', '') if characteristics else ''
                            
                            company_data = await extract_company_data(
                                page_text=page_text,
                                extracted_address=extracted_address,
                                target_unit=query.weight,
                                product_url=seller_site,
                                phone_number=phone_number,
                                company_name=company_name,
                                material_name=material_name,
                                price_info=price_info,
                                kg=query.name,
                                characteristics=characteristics,
                                description=description,
                                client=client
                            )

                            # Создание PDF
                            try:
                                top_path = f"{out_dir}/top_screen_{idx+1}.png"
                                bottom_path = f"{out_dir}/bottom_screen_{idx+1}.png"

                                if seller_page and not seller_page.is_closed():
                                    # Дополнительное ожидание для стабилизации страницы
                                    await asyncio.sleep(3)
                                    
                                    try:
                                        # Проверка готовности страницы для скриншота
                                        page_title = await seller_page.title()
                                        page_url = seller_page.url
                                        
                                        # Проверяем viewport
                                        viewport = seller_page.viewport_size
                                        logger.info(f"Viewport: {viewport}")
                                        
                                        # Проверяем, что страница полностью загружена
                                        ready_state = await seller_page.evaluate("() => document.readyState")
                                        if ready_state != "complete":
                                            logger.warning(f"Страница еще загружается: readyState = {ready_state}")
                                            await seller_page.wait_for_load_state("load", timeout=5000)
                                        
                                        # Проверяем наличие видимого контента на странице
                                        body_height = await seller_page.evaluate("() => document.body.scrollHeight")
                                        visible_elements = await seller_page.evaluate("""() => {
                                            const visibleElements = [];
                                            const elements = document.querySelectorAll('*');
                                            for (let i = 0; i < Math.min(elements.length, 10); i++) {
                                                const el = elements[i];
                                                const rect = el.getBoundingClientRect();
                                                if (rect.width > 0 && rect.height > 0) {
                                                    visibleElements.push({
                                                        tag: el.tagName,
                                                        width: rect.width,
                                                        height: rect.height,
                                                        text: el.textContent?.substring(0, 50)
                                                    });
                                                }
                                            }
                                            return visibleElements;
                                        }""")
                                        
                                        logger.info(f"Готов к скриншоту. Title: '{page_title}', URL: {page_url}, readyState: {ready_state}")
                                        logger.info(f"Body height: {body_height}, Visible elements: {len(visible_elements)}")
                                        
                                        # Если нет видимых элементов, ждем их появления
                                        if len(visible_elements) < 3 or body_height < 100:
                                            logger.warning("Мало видимых элементов или маленькая страница, ждем загрузки контента...")
                                            try:
                                                # Ждем появления основного контента
                                                await seller_page.wait_for_selector("body", timeout=3000)
                                                await asyncio.sleep(2)
                                                
                                                # Пытаемся принудительно прокрутить страницу для активации ленивой загрузки
                                                await seller_page.evaluate("""() => {
                                                    window.scrollTo(0, 100);
                                                    window.scrollTo(0, 0);
                                                }""")
                                                await asyncio.sleep(1)
                                                
                                                # Проверяем снова
                                                new_body_height = await seller_page.evaluate("() => document.body.scrollHeight")
                                                logger.info(f"После активации: высота страницы {new_body_height}")
                                                
                                            except Exception as wait_error:
                                                logger.warning(f"Видимые элементы не появились: {wait_error}, продолжаем со скриншотом")
                                        
                                        # Прокручиваем вверх перед скриншотом
                                        await seller_page.evaluate("() => window.scrollTo(0, 0)")
                                        await asyncio.sleep(2)
                                        
                                        logger.info("Скриншот верхней части экрана через Playwright")
                                        
                                        # Если страница пустая, используем full_page=True
                                        final_body_height = await seller_page.evaluate("() => document.body.scrollHeight")
                                        if final_body_height < 200:
                                            logger.warning("Страница очень короткая, используем полный скриншот")
                                            await seller_page.screenshot(path=top_path, full_page=True, timeout=10000)
                                        else:
                                            # Обычный скриншот с заданной областью
                                            await seller_page.screenshot(
                                                path=top_path, 
                                                full_page=False,
                                                clip={"x": 0, "y": 0, "width": 1920, "height": 600},
                                                timeout=10000
                                            )
                                        
                                    except Exception as screenshot_error:
                                        logger.error(f"Ошибка создания скриншота страницы продавца: {screenshot_error}")
                                        logger.warning("Используем скриншот основной страницы вместо страницы продавца")
                                        await product_page.evaluate("() => window.scrollTo(0, 0)")
                                        await asyncio.sleep(1)
                                        await product_page.screenshot(path=top_path, full_page=False)
                                else:
                                    logger.warning("Страница продавца недоступна, используем скриншот основной страницы")
                                    await product_page.evaluate("() => window.scrollTo(0, 0)")
                                    await asyncio.sleep(1)
                                    await product_page.screenshot(path=top_path, full_page=False)
                                logger.info(f"Проверка {top_path}: {os.path.exists(top_path)}, размер: {os.path.getsize(top_path) if os.path.exists(top_path) else 0}")
                                
                                # Проверяем, не пустой ли скриншот (8511 байт = типичный размер пустого скриншота)
                                if os.path.exists(top_path) and os.path.getsize(top_path) <= 10000:
                                    logger.warning(f"Верхний скриншот пустой или слишком маленький ({os.path.getsize(top_path)} байт), используем fallback")
                                    try:
                                        # Удаляем пустой скриншот
                                        os.remove(top_path)
                                        # Создаем скриншот основной страницы
                                        await product_page.evaluate("() => window.scrollTo(0, 0)")
                                        await asyncio.sleep(1)
                                        await product_page.screenshot(path=top_path, full_page=False)
                                        logger.info(f"Fallback скриншот создан, размер: {os.path.getsize(top_path)} байт")
                                    except Exception as fallback_error:
                                        logger.error(f"Ошибка создания fallback скриншота: {fallback_error}")

                                time.sleep(2)

                                if seller_page and not seller_page.is_closed():
                                    try:
                                        logger.info("Прокрутка страницы до низа")
                                        page_height = await seller_page.evaluate("() => document.body.scrollHeight")
                                        viewport_height = 600
                                        
                                        if page_height > viewport_height:
                                            # Прокручиваем к концу страницы
                                            await seller_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                            await asyncio.sleep(2)
                                            
                                            logger.info("Скриншот нижней части экрана через Playwright")
                                            await seller_page.screenshot(
                                                path=bottom_path, 
                                                full_page=False,
                                                clip={"x": 0, "y": max(0, page_height - viewport_height), "width": 1920, "height": viewport_height},
                                                timeout=10000
                                            )
                                        else:
                                            # Страница короткая, делаем скриншот с середины
                                            logger.warning("Страница короткая, скриншот с середины")
                                            await seller_page.evaluate("window.scrollTo(0, 0)")
                                            await asyncio.sleep(1)
                                            await seller_page.screenshot(path=bottom_path, full_page=True, timeout=10000)
                                        
                                    except Exception as bottom_screenshot_error:
                                        logger.error(f"Ошибка создания нижнего скриншота страницы продавца: {bottom_screenshot_error}")
                                        logger.warning("Используем нижний скриншот основной страницы")
                                        await product_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                        await asyncio.sleep(2)
                                        await product_page.screenshot(path=bottom_path, full_page=False)
                                else:
                                    logger.warning("Страница продавца недоступна, используем скриншот основной страницы (низ)")
                                    await product_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                    await asyncio.sleep(2)
                                    await product_page.screenshot(path=bottom_path, full_page=False)
                                logger.info(f"Проверка {bottom_path}: {os.path.exists(bottom_path)}, размер: {os.path.getsize(bottom_path) if os.path.exists(bottom_path) else 0}")
                                
                                # Проверяем, не пустой ли нижний скриншот
                                if os.path.exists(bottom_path) and os.path.getsize(bottom_path) <= 10000:
                                    logger.warning(f"Нижний скриншот пустой или слишком маленький ({os.path.getsize(bottom_path)} байт), используем fallback")
                                    try:
                                        # Удаляем пустой скриншот
                                        os.remove(bottom_path)
                                        # Создаем скриншот основной страницы (нижняя часть)
                                        await product_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                        await asyncio.sleep(2)
                                        await product_page.screenshot(path=bottom_path, full_page=False)
                                        logger.info(f"Fallback нижний скриншот создан, размер: {os.path.getsize(bottom_path)} байт")
                                    except Exception as fallback_error:
                                        logger.error(f"Ошибка создания fallback нижнего скриншота: {fallback_error}")

                                logger.info(f"Генерация PDF для карточки {idx+1}")
                                pdf_filename = f"{code}_{idx+1}_{current_year}_{current_quarter}.pdf"
                                pdf_path = os.path.join(out_dir, pdf_filename)
                                
                                create_pdf_with_fpdf(
                                    top_path=top_path,
                                    bottom_path=bottom_path,
                                    output_path=pdf_path,
                                    seller_site=seller_site,
                                    company_name=company_name,
                                    material_name=material_name,
                                    company_data=company_data,
                                    query=query,
                                    price_info=price_info,
                                    phone_number=phone_number,
                                    date=date,
                                    delivery_method=delivery_method,
                                    extracted_address=extracted_address,
                                    monitor=query.monitor
                                )
                                logger.info(f"PDF сохранён: {pdf_path}")
                                
                                # OCR + GPT обработка
                                try:
                                    top_text = extract_text_from_image(top_path)
                                    bottom_text = extract_text_from_image(bottom_path)
                                    full_text = top_text + '\n' + bottom_text
                                    
                                    if full_text.strip():
                                        gpt_result_json = await gpt_extract_data_from_screenshot(full_text)
                                        gpt_data = json.loads(gpt_result_json)
                                        if not company_name or company_name == "не указано":
                                            company_name = gpt_data.get('company', company_name)
                                        if (not phone_number or phone_number == "Номер на сайте отсутствует") and gpt_data.get('phone') and gpt_data.get('phone') != "Номер на сайте отсутствует":
                                            phone_number = gpt_data.get('phone', phone_number)
                                        if not price or price == "":
                                            price = gpt_data.get('price', price)
                                        if not extracted_address or extracted_address == "не найдено":
                                            extracted_address = gpt_data.get('address', extracted_address)
                                except Exception as e:
                                    logger.error(f"Ошибка OCR/GPT обработки: {e}")
                                
                                # Удаление скриншотов
                                finally:
                                    for file_path in [top_path, bottom_path]:
                                        try:
                                            if os.path.exists(file_path):
                                                os.remove(file_path)
                                                logger.info(f"Удален файл: {file_path}")
                                        except Exception as e:
                                            logger.warning(f"Не удалось удалить файл {file_path}: {e}")

                            except Exception as e:
                                logger.exception(f"Ошибка обработки страницы {seller_site}: {e}")
                                pdf_filename = "ошибка обработки"
                            finally:
                                if seller_page and not seller_page.is_closed():
                                    await seller_page.close()
                                logger.info(f"PDF сохранён: {pdf_filename}")

                        # Создание записи результата
                        results.append({
                            "Электронная почта поставщика/производителя": company_data['email'],
                            "ИНН поставщика/ производителя": company_data['inn'],
                            "КПП": company_data['kpp'],
                            "Формула": company_data['formula'],
                            "url": link,
                            "Наименование поставщика/ производителя": company_data['company_n'],
                            "Наименование ресурса по прейскуранту": material_name.strip() if isinstance(material_name, str) else material_name,
                            "Ценовое предложение, с НДС, руб.": f"{price_info['price']} {price_info['currency']}",
                            "Телефон поставщика/производителя": phone_number,
                            "delivery_method": delivery_method if delivery_method else "Самовызов",
                            "Адрес поставщика/производителя/склада (место отгрузки)": company_data['address'],
                            "Адрес сайта в информационно-телекоммуникационной сети «Интернет» поставщика/производителя": seller_site,
                            "Цена зафиксирована на дату": date,
                            "Прейскурант": f"{code}_{idx+1}_{current_year}_{current_quarter}.pdf",
                            "Индекс": str(int_number + idx),
                            "note": "Данные частично или полностью отсутствуют" if any([
                                not company_name,
                                not material_name,
                                not price_info['price']
                            ]) else "OK"
                        })

                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error processing {link}: {error_msg}")
                        
                        # Проверяем тип ошибки - если это ошибка соединения, не создаем скриншот
                        if any(err in error_msg for err in [
                            "ERR_CONNECTION_REFUSED", "ERR_NAME_NOT_RESOLVED", 
                            "ERR_SSL_PROTOCOL_ERROR", "ERR_NETWORK_CHANGED",
                            "ERR_INTERNET_DISCONNECTED", "ERR_CONNECTION_TIMED_OUT"
                        ]):
                            logger.warning(f"[SKIP] Пропускаем товар {idx+1} из-за недоступности сайта: {link}")
                            results.append({"url": link, "error": error_msg, "skipped": True})
                        else:
                            # Только для других ошибок создаем скриншот
                            try:
                                await product_page.screenshot(path=f"{out_dir}/error_{idx+1}.png")
                                logger.info(f"[DEBUG] Создан скриншот ошибки: error_{idx+1}.png")
                            except:
                                logger.warning(f"[DEBUG] Не удалось создать скриншот для error_{idx+1}")
                            results.append({"url": link, "error": error_msg})
                    finally:
                        try:
                            if 'product_page' in locals() and not product_page.is_closed():
                                await product_page.close()
                            if 'seller_page' in locals() and not seller_page.is_closed():
                                await seller_page.close()
                        except Exception as e:
                            logger.error(f"Ошибка при закрытии страниц: {e}")
                    
                    # Задержка между обработкой товаров
                    if idx < len(yes_links) - 1:
                        await asyncio.sleep(2)
                        logger.info(f"[PROCESSING] Пауза перед следующим товаром")

                # Запись результатов в JSON
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"json/results_{timestamp}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

                # Возврат результатов
                logger.info(f"[FINAL] Обработано товаров: {len(results)}")
                return {"results": results}

            except Exception as e:
                logger.error(f"Error in main processing: {str(e)}")
                raise
            finally:
                # Финализация
                try:
                    if 'page' in locals() and not page.is_closed():
                        await page.close()
                    if 'context' in locals():
                        await context.close()
                    if 'browser' in locals():
                        await browser.close()
                except Exception as e:
                    logger.error(f"Ошибка при закрытии ресурсов: {e}")
    
    except Exception as e:
        logger.error(f"Error in collect_offers: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Запуск Pulscen Parser API сервера")
    print("=" * 50)
    
    # Запускаем автоматический скриншот в отдельном потоке
    print("📸 Запускаю автоматический скриншот всего экрана...")
    screenshot_thread = threading.Thread(target=auto_screenshot_system, daemon=True)
    screenshot_thread.start()
    
    print("🌐 Запускаю веб-сервер на http://localhost:8000")
    print("📱 Сайт автоматически откроется в браузере")
    print("📸 Скриншот всего экрана будет создан автоматически")
    print("⏰ Время будет отображаться в консоли")
    print("=" * 50)
    
    # Запускаем сервер
    uvicorn.run(app, host="0.0.0.0", port=8000) 