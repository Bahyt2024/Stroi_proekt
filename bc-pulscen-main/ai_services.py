import json
import re
import logging
import httpx
import requests
import asyncio
from openai import AsyncOpenAI
from config import PERPLEXITY_API_KEY, OPENAI_API_KEY, DADATA_HEADERS, COMPANIES_FILE, REQUEST_DELAY

logger = logging.getLogger(__name__)

# Инициализация OpenAI клиента
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def perplexity_raw_search(material_name: str, count=3, attempt=1, exclude_urls=None) -> str:
    """Поиск товаров через Perplexity API"""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    # Варьируем запрос в зависимости от номера попытки (поддержка до 10 попыток)
    search_variations = {
        1: f"ЭТАП 1: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА для запроса «{material_name}» — ищи в крупных российских строительных интернет-магазинах.",
        2: f"ЭТАП 2: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — поищи в других источниках, НЕ на тех же сайтах что раньше.",
        3: f"ЭТАП 3: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — проверь региональные поставщики и производителей.",
        4: f"ЭТАП 4: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — ищи в специализированных химических компаниях и дистрибьюторах.",
        5: f"ЭТАП 5: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — проверь промышленные поставщики в разных регионах России.",
        6: f"ЭТАП 6: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — ищи у заводов-производителей и их официальных представителей.",
        7: f"ЭТАП 7: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — проверь оптовых поставщиков и торговые компании.",
        8: f"ЭТАП 8: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — ищи в менее популярных, но качественных источниках.",
        9: f"ЭТАП 9: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — проверь новые и альтернативные торговые площадки.",
        10: f"ЭТАП 10: НАЙДИ СТРОГО {count} КАРТОЧКИ ТОВАРА «{material_name}» — финальный поиск в любых доступных источниках, которые еще не проверяли."
    }
    
    prompt = (
        search_variations.get(attempt, search_variations[1]) +
        "ИСКЛЮЧИ:"
        "- Каталоги, подборки, списки, фильтры, разделы (любой URL с /catalog/, /category/, /section/, /filter/, /list/, /produktsiya/, /product-category/, /products/, /goods/, если ссылка не содержит уникального ID или slug товара)."
        "- Сайты с не-российскими доменами."
        "- Маркетплейсы (Avito, Wildberries, Ozon, Яндекс-Маркет)."
        "- Сайты 400meshkov.ru, capitolina.ru."
        "Для примера: "
        "- ПРАВИЛЬНО: https://eldako.ru/produktsiya/mel-molotyy/mel-prirodnyy-tekhnicheskiy-dispersnyy-mtd-2-meshok-30-kg/ (есть slug, ID или .html)"
        "- НЕПРАВИЛЬНО: https://eldako.ru/produktsiya/mel-molotyy/ (это каталог, не карточка товара)"
        "- НЕПРАВИЛЬНО: https://petrostm.ru/mel-prirodnyi.html (если это просто каталог/описание товара без кнопки 'Купить' и конкретной цены — не принимать)"
        "КРИТЕРИИ ВЫБОРА КАРТОЧКИ:"
        "- В URL обязательно должен быть slug или ID товара, или заканчиваться на .html/.php/.aspx и вести на отдельную страницу."
        "- На странице обязательно есть:"
        "  • Точное название товара (в заголовке или h1)"
        "  • Точное название компании т.к. его нужно пробивать в базу данных (в заголовке или h1). Перед тем как выдать ее, посмотри о ней информацию и проверь действительно ли она существует"
        "  • Конкретная цена с единицей  т.е. если даже в штуках то в штуке сколько чего может 30 кг может 25 кг, в названии товара укажи (руб., руб./шт., руб./т, и т.д. — не 'цена по запросу', именно то, что указана на сайте действительная цена без запроса, чтобы я мог понимать сколько она стоит. Если не нашел то ищи другой сайт!)"
        "  • Активная кнопка 'Купить', 'В корзину', 'Заказать'"
        "  • Таблица/список характеристик товара (ГОСТ, вес, размеры)"
        "  • Явный телефон продавца в шапке или футере (+7..., 8...) или в разделе контакты, все должно совпадать как будто открыл перешел к карточке товара и сразу видишь тот же номер телефона, что и у тебя должен быть. НЕ ОШИБИСЬ НОМЕРОМ Т.К. БУДУ ТУДА ЗВОНИТЬ и если ты ошбишься, то я не смогу купить товар!"
        "- Если хотя бы ОДНОГО признака нет — ОТБРАСЫВАЙ ссылку."
        "ДЛЯ КАЖДОЙ ВЫДАННОЙ ССЫЛКИ:"
        "• Объясни, почему это карточка товара, а не каталог (например: 'В URL есть slug и страница содержит кнопку Купить, конкретную цену и характеристики, телефон продавца найден в футере')."
        "ФОРМАТ ВЫВОДА (строго без JSON):"
        "Компания, продающая товар: [полное название]"
        "Товар: [название с сайта]"
        "Цена: [число] руб./[единица]"
        "Адрес: [полный адрес]"
        "Телефон: [номер]"
        "Ссылка: [URL карточки]"
        "Пояснение: [кратко аргументируй, почему именно карточка товара]"

        f"Если что-то отсутствует, ИЩИ ДРУГОЙ САЙТ. Проверь ссылку, цену и телефон на актуальность!"
        f"КРИТИЧЕСКИ ВАЖНО: НАЙДИ СТРОГО {count} РАЗНЫХ ТОВАРА от РАЗНЫХ компаний. Если находишь меньше — продолжи поиск!"
        f"РАЗНООБРАЗИЕ ИСТОЧНИКОВ: Ищи товары на РАЗНЫХ доменах и сайтах! НЕ используй один и тот же сайт или домен дважды. Примеры разных источников:"
        f"- Специализированные газовые компании (газснаб, техгазы, промгазы)"
        f"- Региональные строительные поставщики"
        f"- Промышленные дистрибьюторы"
        f"- Заводы-производители"
        f"ИСКЛЮЧИ ПОВТОРЫ: Если уже нашел товар на сайте example.com - НЕ ищи больше на этом домене!"
        f"ОБЯЗАТЕЛЬНАЯ ПРОВЕРКА САЙТОВ: Каждую ссылку проверь на доступность! Если сайт не открывается, SSL ошибки или домен не существует — НЕ ВКЛЮЧАЙ его в результат!"
        f"Ищи только РАБОЧИЕ сайты с активными страницами товаров. Убедись что можешь открыть каждую ссылку перед выдачей результата."
    )
    
    # Добавляем исключения недоступных URL если они есть
    if exclude_urls and len(exclude_urls) > 0:
        excluded_domains = list(set([url.split('/')[2] if url.startswith('http') else url for url in exclude_urls]))
        
        prompt += f"\n\nВАЖНО: НЕ используй эти недоступные домены из предыдущих попыток:\n"
        prompt += f"Исключить домены: {', '.join(excluded_domains[:10])}\n"  # Показываем первые 10
        prompt += f"Ищи товары на ДРУГИХ сайтах, которых нет в списке исключений!"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Ты помощник по поиску товаров в интернете."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000
    }
    async with httpx.AsyncClient(timeout=60) as client_httpx:
        response = await client_httpx.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

async def openai_to_json(raw_text: str, count: int = 3) -> list:
    """Конвертирует текст в JSON через OpenAI"""
    json_schema = '''
    [
      {
        "company": "",
        "url": "",
        "name": "",
        "price": "",
        "address": "",
        "phone": ""
      }
    ]
    '''
    prompt = (
        f"В этом тексте приведены блоки описания товаров из интернет-магазинов. Также определи номер телефона через адрес сайта и перепроверь название компании, он находится либо в footer, либо в header.\n"
        f"Тебе нужно извлечь не более {count} карточек товаров и оформить их строго по этой структуре (array of JSON):\n"
        f"{json_schema}\n\n"
        "company — настоящее официальное название компании/магазина (брать только явно с сайта, а не из ссылки/email/домена) либо тебе надо по ссылке узнать что именно за компания представлена, можешь поискать в своих источниках т.к. ошибаться категорически нельзя;\n"
        "url — ссылка на карточку товара;\n"
        "name — точное название товара;\n"
        "price — цена с единицей измерения. Цена ДОЛЖНА быть ЧИСЛОМ. Единица измерения должна быть ЧЕТКОЙ (например, 'руб./шт.', 'руб./м2', 'руб./кг'). Если цена не содержит числа или единица измерения неясна, используй пустую строку для цены и 'руб.' для валюты.;\n"
        "address — адрес магазина;\n"
        "phone — телефон магазина, в header footer он 100% должен быть. Если он такого формата +7 (960) 991-ХХ-ХХ, то есть когда ХХ-ХХ то лучше бери, что тебе выдали в схеме номер телефона либо поищи в источниках\n"
        "Верни только JSON массив. Если какого-то поля нет — оставь его пустым.\n"
        "Текст:\n"
        f"{raw_text}"
    )
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=2048,
    )
    content = response.choices[0].message.content.strip()
    try:
        data = json.loads(content)
    except Exception:
        json_matches = re.findall(r'\[.*\]', content, re.DOTALL)
        if json_matches:
            data = json.loads(json_matches[0])
        else:
            raise RuntimeError(f"OpenAI не вернул валидный JSON. Ответ: {content}")
    return data

async def perplexity_search_product_cards(material_name: str, count=3, attempt=1, exclude_urls=None):
    """Получает сырые карточки из Perplexity, структурирует в JSON через OpenAI"""
    raw_text = await perplexity_raw_search(material_name, count, attempt, exclude_urls)
    products = await openai_to_json(raw_text, count=count)
    results = []
    for item in products[:count]:
        results.append({
            "company": item.get("company", ""),
            "url": item.get("url", ""),
            "name": item.get("name", ""),
            "price": item.get("price", ""),
            "address": item.get("address", ""),
            "phone": item.get("phone", ""),
        })
    return results

async def gpt_clean_company_name(client, company_name: str) -> str:
    """Очищает название компании от сокращений, географических суффиксов и т.д."""
    prompt = f"""
    Очисти название компании от сокращений, географических суффиксов и лишних слов.
    Оставь только основное название компании.
    
    Примеры:
    - "База Стройка" -> "База Стройка (не сокращай!)"
    - "ООО Строительная компания Велес г. Челябинск" -> "ООО Строительная компания Велес"
    - "СК Велес" -> "Строительная компания Велес"
    - "ИСМА г. Москва" -> "ИСМА"
    - "АО ИСМА" -> "АО ИСМА"
    - или СИСТЕМА МАТЕРИАЛЬНО-ТЕХНИЧЕСКОЙ КОМПЛЕКТАЦИИ -> "СМТК" в общем используй все варианты
    
    Название для очистки: {company_name}
    
    Верни только очищенное название, без пояснений.
    """
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100
    )
    
    cleaned_name = response.choices[0].message.content.strip()
    return cleaned_name

async def gpt_correct_company_name(client, company_name: str) -> str:
    """Корректирует название компании для поиска в DaData"""
    prompt = f"""
    Ты - эксперт по поиску компаний в базе данных DaData.
    Тебе дано название компании, для которого не удалось найти ИНН.
    Твоя задача - предложить альтернативные варианты написания названия, которые могут помочь найти компанию.
    
    Правила:
    1. Сохраняй основное название компании
    2. Добавляй или убирай организационно-правовую форму (ООО, АО, ЗАО)
    3. Исправляй возможные опечатки
    4. Добавляй или убирай кавычки
    5. Исправляй сокращения на полные названия
    
    Примеры:
    - "СК Велес" -> "Строительная компания Велес"
    - "ООО ИСМА" -> "ИСМА"
    - "АО ИСМА" -> "ИСМА"
    - "СК Велес г. Челябинск" -> "Строительная компания Велес"
    - или СИСТЕМА МАТЕРИАЛЬНО-ТЕХНИЧЕСКОЙ КОМПЛЕКТАЦИИ -> "СМТК" в общем используй все варианты
    
    Название для корректировки: {company_name}
    
    Верни только скорректированное название, без пояснений.
    """
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100
    )
    
    corrected_name = response.choices[0].message.content.strip()
    return corrected_name

def find_company_dadata(company_name, count=100, file_path=COMPANIES_FILE, client=None):
    """Поиск по DaData и запись всех результатов в файл без фильтрации"""
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
    data = {"query": company_name, "count": count}
    response = requests.post(url, headers=DADATA_HEADERS, json=data)
    logger.info(f"DaData status: {response.status_code}, response: {response.text[:300]}...")
    response.raise_for_status()
    result = response.json()
    suggestions = result.get("suggestions", [])

    # Если не найдено ни одной компании, пробуем очистить название через GPT и повторить поиск
    if not suggestions and client is not None:
        logger.info(f"[DADATA] Не найдено по '{company_name}', пробуем очистить название через GPT...")
        loop = asyncio.get_event_loop()
        cleaned_name = loop.run_until_complete(gpt_clean_company_name(client, company_name))
        logger.info(f"[DADATA] Очищенное название: '{cleaned_name}'")
        data = {"query": cleaned_name, "count": count}
        response = requests.post(url, headers=DADATA_HEADERS, json=data)
        logger.info(f"DaData (повтор) status: {response.status_code}, response: {response.text[:300]}...")
        response.raise_for_status()
        result = response.json()
        suggestions = result.get("suggestions", [])

    with open(file_path, "a", encoding="utf-8") as f:
        for item in suggestions:
            state = item["data"].get("state", {})
            status = state.get("status", "UNKNOWN")
            f.write(f"Название: {item['value']}\n")
            f.write(f"ИНН: {item['data'].get('inn', '')}\n")
            f.write(f"КПП: {item['data'].get('kpp', '')}\n")
            f.write(f"Адрес: {item['data'].get('address', {}).get('value', '')}\n")
            f.write(f"Статус: {status}\n")
            f.write('-' * 40 + '\n')
    logger.info(f"Записано компаний: {len(suggestions)} в файл {file_path}")
    return suggestions

async def gpt_check_product_match(query_name, product_name, company_name, found_companies, client):
    """Проверяет соответствие товара запросу через GPT"""
    prompt = ("Ты — эксперт по сравнению строительных материалов. "
    "Твоя задача — отсеять карточки, которые НЕ являются нужным товаром.\n\n"
    "⚠️ Пропускай всё, где есть слова: \"услуга\", \"аренда\", \"освидетельствование\", "
    "\"проверка\", \"диагностика\", \"монтаж\", \"доставка\".\n"
    "⚠️ Пропускай товары без указания цены ИЛИ с диапазоном без числа.\n\n"
    "Считай совпадением «да», если:\n"
    "• материал, толщина, вид обработки совпадают,\n"
    "• название отражает именно продукт, а не работу/услугу.\n\n"
    "Правила сравнения:\n"
    "Если название компании на сайте уже есть в списке найденных компаний, всегда отвечай 'нет'.\n"
    "1. Считай товары одинаковыми, если:\n"
    "   - Основной материал совпадает (например, 'хризотилцементный' = 'асбестоцементный')\n"
    "   - Тип изделия совпадает (например, 'лист' = 'шифер')\n"
    "   - Толщина совпадает (например, '8 мм' = '8мм')\n"
    "   - Способ изготовления совпадает (например, 'прессованный' = 'прессованный')\n"
    "2. Игнорируй различия в:\n"
    "   - Размерах (если не указаны в запросе)\n"
    "   - ГОСТах (если не указаны в запросе)\n"
    "   - Форматировании текста\n"
    "   - Порядке слов\n"
    "   - Сокращениях (например, 'х/ц' = 'хризотилцементный')\n\n"
    "Примеры 'да':\n"
    "- 'Лист хризотилцементный плоский прессованный 8 мм' = 'Лист плоски прессованный х/ц 8 мм'\n"
    "- 'Листы хризотилцементные плоские прессованные, толщина 8 мм' = 'Лист хризотилцементный плоский прессованный ЛПП 8х1200х3000 мм'\n"
    "- 'Газ сварочный (смесь аргона и углекислого газа)' = 'Газовые смеси для сварочных работ (арг/угл 80/20) 40 литров в баллоне'\n"
    "- 'Шифер плоский прессованный 8 мм' = 'Лист хризотилцементный плоский прессованный 8 мм'\n\n"
    "Примеры 'нет':\n"
    "- 'Газ сварочный (смесь аргона и углекислого газа)' ≠ 'Регулятор расхода газа аргон Ар 40-2'\n"
    "- 'Газ сварочный (смесь аргона и углекислого газа)' ≠ 'Метан-аргоновая смесь (10% метан 90% аргон) 40 л'\n"
    "- 'Лист хризотилцементный плоский прессованный 8 мм' ≠ 'Лист хризотилцементный волнистый 8 мм'\n"
    "- 'Лист хризотилцементный плоский прессованный 8 мм' ≠ 'Лист хризотилцементный плоский непрессованный 8 мм'\n"
    "- 'Лист хризотилцементный плоский прессованный 8 мм' ≠ 'Лист хризотилцементный плоский прессованный 10 мм'\n\n"
    f'Название из запроса: "{query_name}"\n'
    f'Название на сайте: "{product_name}"\n'
    f'Название компании на сайте: "{company_name}"\n'
    f'Уже найденные компании: {found_companies}\n'
    'Ответь строго одним словом: да или нет.'
    )
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=3,
        temperature=0
    )
    return response.choices[0].message.content.strip().lower()

def extract_text_from_image(image_path):
    """Извлекает текст из изображения с помощью OCR"""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(image_path), lang='rus+eng')
    except Exception as e:
        logger.error(f"Ошибка OCR для {image_path}: {e}")
        return ""

async def gpt_extract_data_from_screenshot(text):
    """Извлекает данные из скриншота с помощью GPT"""
    prompt = (
        "В этом тексте содержится информация со скриншота страницы интернет-магазина. "
        "Тебе нужно извлечь и вернуть в JSON-формате:\n"
        "- company: название компании\n"
        "- phone: номер телефона\n"
        "- price: цена с единицей измерения (например, 1000 руб./т)\n"
        "- address: адрес компании\n\n"
        "Если какое-то поле не найдено, оставь его пустым.\n"
        "Текст скриншота:\n"
        f"{text}\n\n"
        "Верни только JSON:"
    )
    response = await openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content.strip() 