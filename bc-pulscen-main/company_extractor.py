import json
import logging
import asyncio
from ai_services import gpt_clean_company_name, gpt_correct_company_name, find_company_dadata
from utils import read_formula_table, read_comp_table
from config import REQUEST_DELAY, COMPANIES_FILE

logger = logging.getLogger(__name__)

async def extract_company_data(
    page_text: str, extracted_address: str, target_unit: str, product_url: str,
    phone_number: str, company_name: str, material_name: str, price_info: str, kg: str,
    characteristics: dict = None, description: str = None, client=None
) -> dict:
    """Извлекает данные о компании с помощью AI"""
    logger.info("extract_company_data ВЫЗВАНА!!!")
    try:
        if not client or not client.api_key:
            logger.error("OPENAI_API_KEY не установлен!")
            raise ValueError("Отсутствует OPENAI_API_KEY")

        await asyncio.sleep(REQUEST_DELAY)

        # Очищаем название компании перед поиском
        cleaned_company_name = await gpt_clean_company_name(client, company_name)
        logger.info(f"[COMPANY] Оригинальное название: {company_name}")
        logger.info(f"[COMPANY] Очищенное название: {cleaned_company_name}")

        # Поиск по DaData с очищенным названием
        suggestions = find_company_dadata(cleaned_company_name, count=100, client=client)
        
        # Если не нашли по очищенному названию, пробуем оригинальное
        if not suggestions:
            logger.info("[COMPANY] Не найдено по очищенному названию, пробуем оригинальное")
            suggestions = find_company_dadata(company_name, count=100, client=client)

        # Если нашли компании, берем первую с полным названием
        company_n = "не найдено"
        inn = "не найдено"
        kpp = "не найдено"
        if suggestions:
            for suggestion in suggestions:
                value = suggestion.get("value", "")
                data = suggestion.get("data", {})
                if value and not value.startswith(("ООО", "АО", "ЗАО", "ОАО")):
                    company_n = value
                    inn = data.get("inn", "не найдено")
                    kpp = data.get("kpp", "не найдено")
                    break
            if company_n == "не найдено":
                company_n = suggestions[0].get("value", "не найдено")
                inn = suggestions[0].get("data", {}).get("inn", "не найдено")
                kpp = suggestions[0].get("data", {}).get("kpp", "не найдено")

        # Если ИНН не найден, пробуем еще раз с GPT-скорректированным названием
        if inn == "не найдено":
            logger.info("[COMPANY] ИНН не найден, пробуем скорректировать название через GPT")
            corrected_name = await gpt_correct_company_name(client, company_name)
            logger.info(f"[COMPANY] Скорректированное название: {corrected_name}")
            
            # Пробуем поиск с новым названием
            new_suggestions = find_company_dadata(corrected_name, count=100, client=client)
            if new_suggestions:
                for suggestion in new_suggestions:
                    value = suggestion.get("value", "")
                    data = suggestion.get("data", {})
                    if value and data.get("inn"):
                        company_n = value
                        inn = data.get("inn", "не найдено")
                        kpp = data.get("kpp", "не найдено")
                        logger.info(f"[COMPANY] Найдено по скорректированному названию: {company_n} (ИНН: {inn})")
                        break

        formula_table = read_formula_table()
        comp = read_comp_table()

        # Промпт для расчёта формулы
        formula_prompt = f'''
Ты — калькулятор строительных цен.
Шаги:

1. Определи исходную и целевую единицу измерения. {material_name} {price_info} в {target_unit}. Если указан диапазон цен, бери минимальное только.
о товаре {characteristics}. {description}
2. Выбери правило из таблицы правил (см. ниже).
3. Найди коэффициент:
   • Если он присутствует в описании (длина, площадь, масса) — используй его.
   • Для газов используй фикс.: He 0.74 м³/л, O₂ 0.84, C₃H₈ 0.51, CH₄ 0.71.
4. Запиши формулу ровно в формате:
   ƒ = <SRC> в <DST> = ( <PRICE><операция><FACTOR> ) = <ITOG>
   — никаких пояснений.
5. Если данных нет → «не найдено», формулу не выводи.

Таблица правил:
{formula_table}
• КГ → Т: *1000
• Т → КГ: /1000
• ШТ → М² (лист/рулон/картон/паронит): /<S, м²>
• ШТ → М³ (лист по толщине): /(S * h)
• ШТ → КГ (канистра N кг): *N
• ШТ → м (пог.м): /<L, м>
• УПАК → КГ: /<масса, кг>
• УПАК → Т: *<масса, кг> /1000
• Л → М³ (жидкости): /1000
• Л → КГ (жидкости): *<ρ, кг/л>
• КГ → Л (жидкости): /<ρ>
• Л → М³ (ГАЗЫ, БАЛЛОНЫ чистые): *k  
  k: He 0.74  O₂ 0.84  CH₄ 0.71  C₃H₈ 0.51
• Баллон V м³ → М³: /V
• КГ → М² (мастики, битумная гидроизоляция): /(q, кг/м²)
• Т → М³ (битум / эмульсия): /(ρ, т/м³)
• Если название плитка 1000х1500х3000 мм 240 руб и нужно в м3 -> 240 / (1 * 1.5 * 3) = 53.33 руб./м³. Если указан объем например 0.38 м³, то цена будет 240 / 0.38 = 631.58 руб./м3

• Если цена указана за мешок (N кг), чтобы получить цену за тонну, умножь цену за мешок на (1000 / N).
  Пример: 260 руб./мешок 30 кг → 260 * (1000 / 30) = 8 666 руб./т

Правила МЕТА  
1) Нет коэффициента — «не найдено».  
2) Услуга — «не найдено».  
3) Итог строго «… руб./<цел-ед.>».
'''

        prompt = f"""
{formula_prompt}

Вот содержимое страницы товара:

Ссылка: {product_url}

Задание:
• Найди и укажи ТОЛЬКО ТО, что явно подтверждено в поиске и на странице!
• Извлеки:
    - Название компании: {company_n} (используй это название, оно уже проверено через DaData)
    — Email компании (если явно указан)
    — ИНН и КПП у {company_name}, ищи в документе {comp}, сравнивай его с адресом {extracted_address}. Если не найдешь такой же адрес или он не найден то бери первый результат и вставь ИНН/КПП с его адресом, чтобы он был там. Пример: если стоит "kpp":"123","kpp_largest":null то тебе нужно извлекать kpp а не kpp_largest т.е. где есть данные
    — Адрес компании: {extracted_address} (или бери из ИНН/КПП адрес документа comp, если не нашел)
    — Телефон компании: {phone_number} (или в документе comp указан, если не нашел)
    — Цена: {price_info}
    — Целевая единица измерения: {target_unit}
    — Название материала: {material_name} и {kg}

Верни только JSON:
{{
    "company_n": "{company_n}",
    "email": "...",
    "inn": "{inn}",
    "kpp": "{kpp}",
    "address": "...",
    "phone": "...",
    "formula": "..."
}}
"""
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        if hasattr(response, "usage"):
            logger.info(f"Токенов prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens}, total: {response.usage.total_tokens}")

        result = json.loads(response.choices[0].message.content)
        for field in ["company_n", "email", "inn", "kpp", "phone", "address", "formula"]:
            value = result.get(field, "не указан")
            if value == "не найдено":
                logger.info(f"[{field}] — искал, не нашёл.")
            elif value == "не указан":
                logger.warning(f"[{field}] — не было попытки поиска или ошибка получения поля!")
            else:
                logger.info(f"[{field}] — найдено: {value}")

        # Если company_n не найден, но DaData вернула хотя бы одну компанию, подставить её название
        if (result.get("company_n", "не найдено") in ["не найдено", "не указан"]) and suggestions:
            result["company_n"] = suggestions[0]["value"]

        return {
            "company_n": result.get("company_n", "не указан"),
            "email": result.get("email", "не указан"),
            "inn": result.get("inn", "не указан"),
            "kpp": result.get("kpp", "не указан"),
            "phone": result.get("phone", "не указан"),
            "address": result.get("address", "не указан"),
            "formula": result.get("formula", "не указан"),
            "characteristics": characteristics or {},
            "description": description or ""
        }

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        return default_response()
    finally:
        # Очистить файл comp после использования
        with open(COMPANIES_FILE, "w", encoding="utf-8") as f:
            f.truncate(0)

def default_response():
    """Возвращает ответ по умолчанию"""
    return {
        "company_n": "не указан",
        "email": "не указан",
        "inn": "не указан",
        "kpp": "не указан",
        "phone": "не указан",
        "address": "не указан",
        "formula": "не указан"
    } 