import os
import re
import logging
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from config import COMPANIES_FILE, FORMULA_FILE

logger = logging.getLogger(__name__)

def read_formula_table():
    """Читает таблицу формул"""
    try:
        with open(FORMULA_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Файл {FORMULA_FILE} не найден!")
        return ""

def read_comp_table():
    """Читает таблицу компаний"""
    if os.path.exists(COMPANIES_FILE):
        with open(COMPANIES_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

async def is_url_valid(url):
    """Проверяет валидность URL"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.head(url, follow_redirects=True)
            return response.status_code == 200
    except Exception:
        return False

async def extract_phone_number(page):
    """Извлекает номер телефона со страницы"""
    phone_number = "Номер на сайте отсутствует"

    try:
        # Пытаемся найти блок с адресом и телефоном
        address_block = await page.query_selector('div.footer-bottom__address')
        if address_block:
            text = await address_block.inner_text()
            matches = re.findall(r'(?:\+7|8|7)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2}', text)
            if matches:
                raw = matches[0]
                cleaned = re.sub(r'[^\d+]', '', raw)
                if len(cleaned) == 11 and cleaned.startswith('8'):
                    phone_number = f"+7{cleaned[1:]}"
                elif len(cleaned) == 12 and cleaned.startswith('+7'):
                    phone_number = cleaned
                else:
                    phone_number = cleaned
                return phone_number

        # Если не нашли в footer, ищем в header
        header_phone = await page.query_selector('div.header-phone__number')
        if header_phone:
            text = await header_phone.inner_text()
            matches = re.findall(r'(?:\+7|8|7)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2}', text)
            if matches:
                raw = matches[0]
                cleaned = re.sub(r'[^\d+]', '', raw)
                if len(cleaned) == 11 and cleaned.startswith('8'):
                    phone_number = f"+7{cleaned[1:]}"
                elif len(cleaned) == 12 and cleaned.startswith('+7'):
                    phone_number = cleaned
                else:
                    phone_number = cleaned
                return phone_number

        # Если не нашли в конкретных блоках, ищем по всей странице
        page_text = await page.content()
        matches = re.findall(r'(?:\+7|8|7)[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{3}[\s\-\(\)]*\d{2}[\s\-\(\)]*\d{2}', page_text)
        if matches:
            raw = matches[0]
            cleaned = re.sub(r'[^\d+]', '', raw)
            if len(cleaned) == 11 and cleaned.startswith('8'):
                phone_number = f"+7{cleaned[1:]}"
            elif len(cleaned) == 12 and cleaned.startswith('+7'):
                phone_number = cleaned
            else:
                phone_number = cleaned

    except Exception as e:
        logger.warning(f"Ошибка извлечения номера: {str(e)}")

    return phone_number

async def extract_dates_from_main_page(page):
    """Извлекает даты с главной страницы"""
    try:
        date_elements = await page.query_selector_all("time")
        return [await el.get_attribute("datetime") for el in date_elements]
    except Exception as e:
        logger.error(f"Error extracting dates: {str(e)}")
        return []

def get_current_date():
    """Получает текущую дату в московском времени"""
    return datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")

def get_current_year_quarter():
    """Получает текущий год и квартал"""
    today = datetime.today()
    current_year = today.year
    current_quarter = (today.month - 1) // 3 + 1
    return current_year, current_quarter 