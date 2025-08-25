import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# API ключи
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DADATA_API_KEY = '656d444b45d6f010afdeb08de8f4ffedd542c265'

# Заголовки для API
DADATA_HEADERS = {
    "Authorization": f"Token {DADATA_API_KEY}",
    "Content-Type": "application/json"
}

# Файлы
COMPANIES_FILE = "companies.txt"
FORMULA_FILE = "формула.txt"

# Настройки
REQUEST_DELAY = 7
MAX_PAGE_TEXT_LENGTH = 3500

# Настройки браузера
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
BROWSER_VIEWPORT = {"width": 1920, "height": 1080}
BROWSER_ARGS = ['--no-sandbox', '--disable-dev-shm-usage']

# Таймауты
PAGE_TIMEOUT = 90000
SELLER_PAGE_TIMEOUT = 15000
PRODUCT_PAGE_TIMEOUT = 60000

# Настройки поиска
MAX_PAGES = 1 