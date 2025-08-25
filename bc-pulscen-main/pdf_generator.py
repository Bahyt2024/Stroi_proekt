import os
import logging
import textwrap
from PIL import Image
from fpdf import FPDF
from config import BROWSER_VIEWPORT

logger = logging.getLogger(__name__)

def create_pdf_with_fpdf(
    top_path, bottom_path, output_path, scale=1.1,
    seller_site="", company_name="", material_name="", company_data=None,
    query=None, price_info=None, phone_number="", date="", delivery_method="", extracted_address="", monitor="", kg=""
):
    """Создает PDF с двумя страницами"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("create_pdf_with_fpdf")
    scale = float(scale)

    company_data = company_data or {}
    price_info = price_info or {}

    def get_value(obj, key):
        if isinstance(obj, dict):
            return obj.get(key, '')
        else:
            return getattr(obj, key, '')

    if isinstance(query, dict):
        code = query.get('code', '')
    else:
        code = getattr(query, 'code', '') if query is not None else ''

    try:
        A4_WIDTH = 842
        A4_HEIGHT = 595

        pdf = FPDF(orientation="L", unit="pt", format="A4")
        
        # Проверяем наличие шрифта
        font_path = 'dejavu-fonts-ttf-2.37/ttf/DejaVuSans.ttf'
        if os.path.exists(font_path):
            pdf.add_font('DejaVu', '', font_path, uni=True)
            pdf.set_font('DejaVu', '', 7)
        else:
            logger.warning(f"Шрифт {font_path} не найден, используем стандартный")
            pdf.set_font('Arial', '', 7)
            
        pdf.set_auto_page_break(False)

        # ----- Первая страница -----
        pdf.add_page()

        # --- HEADER ---
        header_top = 10
        header_line_height = 15
        header_left_width = A4_WIDTH * 0.30
        header_center_width = A4_WIDTH * 0.45
        header_right_width = A4_WIDTH * 0.25 - 20

        # ЛЕВАЯ КОЛОНКА (seller_site, переносим по словам)
        seller_site_lines = textwrap.wrap(seller_site, width=45)
        max_header_lines = max(len(seller_site_lines), 2)
        for idx, line in enumerate(seller_site_lines[:3]):
            pdf.set_xy(10, header_top + idx * header_line_height)
            pdf.cell(header_left_width, header_line_height, line, border=0, align='L')

        # ЦЕНТР (company_name и material_name, аккуратно по строкам)
        pdf.set_xy(header_left_width, header_top)
        company_display = f'Поставщик: {company_data["company_n"]}'
        logger.info(f"[DEBUG_PDF] Company display string for multi_cell: '{company_display}'")
        pdf.multi_cell(header_center_width, header_line_height, company_display, border=0, align='C')
        pdf.set_xy(header_left_width, header_top + header_line_height)
        pdf.multi_cell(header_center_width, header_line_height, query.name, border=0, align='C')

        # ПРАВО (ИНН, КПП по одной на строку)
        inn = f"ИНН: {str(get_value(company_data, 'inn'))}"
        kpp = f"КПП: {str(get_value(company_data, 'kpp'))}"
        pdf.set_xy(header_left_width + header_center_width + 10, header_top)
        pdf.cell(header_right_width, header_line_height, inn, border=0, align='R')
        pdf.set_xy(header_left_width + header_center_width + 10, header_top + header_line_height)
        pdf.cell(header_right_width, header_line_height, kpp, border=0, align='R')

        # Линия под header
        header_block_height = header_top + max(3, 2) * header_line_height
        pdf.set_xy(0, header_block_height)
        pdf.set_draw_color(200, 200, 200)
        pdf.cell(A4_WIDTH, 0, '', ln=2, border='T')

        # --- Вставка изображения ---
        img_margin_top = 28
        y = header_block_height + img_margin_top

        img = Image.open(top_path)
        orig_w, orig_h = img.size
        max_width = A4_WIDTH * scale
        max_height = (A4_HEIGHT - 270) * scale
        ratio = min(max_width / orig_w, max_height / orig_h)
        new_w = orig_w * ratio
        new_h = orig_h * ratio
        x = (A4_WIDTH - new_w) / 2
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            temp_path = f"temp_converted_{os.path.basename(top_path)}.jpg"
            img.save(temp_path)
            pdf.image(temp_path, x=x, y=y, w=new_w, h=new_h)
            os.remove(temp_path)
        else:
            pdf.image(top_path, x=x, y=y, w=new_w, h=new_h)

        # --- FOOTER ---
        footer_line_height = 16
        footer_bottom_padding = 32
        footer_left = (
            f"Формула: {str(get_value(company_data, 'formula'))}\n"
            f"КСР: {str(code)} - {query.name}\n"
            f"Цена: {str(price_info.get('price', ''))} {price_info.get('currency', '')}\n"
            f"Телефон: {phone_number}\n"
            f"Дата формирования: {date}\n"
            f"Способ получения: Самовызов\n"
            f"Адрес склада: {company_data['address']}"
        )
        footer_right = f"Мониторинг проводил специалист:\n{monitor}"

        # Считаем высоту футера по количеству строк в самом длинном столбце
        footer_left_lines = footer_left.count('\n') + 1
        footer_right_lines = footer_right.count('\n') + 1
        footer_lines = max(footer_left_lines, footer_right_lines)
        footer_height = footer_lines * footer_line_height
        footer_y = A4_HEIGHT - footer_bottom_padding - footer_height

        # Линия над футером
        pdf.set_xy(0, footer_y - 4)
        pdf.set_draw_color(200, 200, 200)
        pdf.cell(A4_WIDTH, 0, '', ln=2, border='T')

        # Левый столбец
        col_width_left = (A4_WIDTH - 30) * 0.45
        col_width_right = (A4_WIDTH - 30) * 0.55
        pdf.set_xy(10, footer_y)
        pdf.multi_cell(col_width_left, footer_line_height, footer_left, border=0, align="L")

        # ПРАВЫЙ столбец
        pdf.set_xy(A4_WIDTH - 10 - col_width_right, footer_y)
        pdf.multi_cell(col_width_right, footer_line_height, footer_right, border=0, align="R")

        # ----- Вторая страница -----
        pdf.add_page()
        img = Image.open(bottom_path)
        orig_w, orig_h = img.size
        ratio = min(max_width / orig_w, max_height / orig_h)
        new_w = orig_w * ratio
        new_h = orig_h * ratio
        x = (A4_WIDTH - new_w) / 2
        y = (A4_HEIGHT - new_h) / 2
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            temp_path = f"temp_converted_{os.path.basename(bottom_path)}.jpg"
            img.save(temp_path)
            pdf.image(temp_path, x=x, y=y, w=new_w, h=new_h)
            os.remove(temp_path)
        else:
            pdf.image(bottom_path, x=x, y=y, w=new_w, h=new_h)

        pdf.output(output_path)
        logger.info(f"PDF успешно создан: {output_path}")

    except Exception as e:
        logger.exception(f"ОШИБКА ПРИ СОЗДАНИИ PDF: {e}")
        raise 