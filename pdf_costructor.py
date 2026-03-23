#!/usr/bin/env python3
"""
PDF Constructor API для генерации документов Intesa Sanpaolo
Поддерживает: contratto, garanzia, carta, compensazione, garanzia1of1
"""

from io import BytesIO
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def format_money(amount: float) -> str:
    """Форматирование суммы БЕЗ знака € (он уже есть в HTML)
    Формат: 10 000,00 (пробел для тысяч, запятая для десятичных)
    """
    # Используем точку как разделитель тысяч, затем заменяем на пробел
    # и точку на запятую для десятичных
    formatted = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
    return formatted


def format_date() -> str:
    """Получение текущей даты в итальянском формате"""
    return datetime.now().strftime("%d/%m/%Y")


def monthly_payment(amount: float, months: int, annual_rate: float) -> float:
    """Аннуитетный расчёт ежемесячного платежа"""
    r = (annual_rate / 100) / 12
    if r == 0:
        return round(amount / months, 2)
    num = amount * r * (1 + r) ** months
    den = (1 + r) ** months - 1
    return round(num / den, 2)


def generate_payment_schedule_table(amount: float, months: int, annual_rate: float, monthly_payment: float) -> str:
    """
    Генерирует HTML таблицу графика платежей (амортизационную таблицу)

    Args:
        amount: Сумма кредита
        months: Срок в месяцах
        annual_rate: Годовая процентная ставка (TAN)
        monthly_payment: Ежемесячный платёж

    Returns:
        str: HTML код таблицы
    """
    monthly_rate = (annual_rate / 100) / 12

    # Заголовки таблицы на испанском/итальянском
    table_html = '''
<table class="c18" style="width: 100%; border-collapse: collapse; margin: 10pt 0;">
<tr class="c4" style="background-color: #b7b7b7;">
<td class="c5" style="border: 1pt solid #666666; padding: 5pt; text-align: center; font-weight: 700;"><span class="c3">Mese</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 5pt; text-align: center; font-weight: 700;"><span class="c3">Pagamento</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 5pt; text-align: center; font-weight: 700;"><span class="c3">Interessi</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 5pt; text-align: center; font-weight: 700;"><span class="c3">Importo del prestito</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 5pt; text-align: center; font-weight: 700;"><span class="c3">Saldo residuo</span></td>
</tr>
'''

    # Рассчитываем график платежей
    remaining_balance = float(amount)

    for month in range(1, months + 1):
        # Проценты за месяц
        interest = remaining_balance * monthly_rate

        # Тело кредита (основной долг)
        principal = monthly_payment - interest

        # Последний платёж - корректируем чтобы остаток был точно 0
        if month == months:
            principal = remaining_balance
            interest = monthly_payment - principal
            remaining_balance = 0.0
        else:
            # Остаток долга после платежа
            remaining_balance = remaining_balance - principal

        # Округляем до 2 знаков после запятой
        interest = round(interest, 2)
        principal = round(principal, 2)
        remaining_balance = round(remaining_balance, 2)

        # Форматируем значения
        payment_str = format_money(monthly_payment)
        interest_str = format_money(interest)
        principal_str = format_money(principal)
        balance_str = format_money(remaining_balance) if remaining_balance > 0 else "0,00"

        # Добавляем строку таблицы
        table_html += f'''
<tr class="c7">
<td class="c5" style="border: 1pt solid #666666; padding: 3pt; text-align: center;"><span class="c3">{month}</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 3pt; text-align: right;"><span class="c9 c8">&euro; {payment_str}</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 3pt; text-align: right;"><span class="c9 c8">&euro; {interest_str}</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 3pt; text-align: right;"><span class="c9 c8">&euro; {principal_str}</span></td>
<td class="c5" style="border: 1pt solid #666666; padding: 3pt; text-align: right;"><span class="c9 c8">&euro; {balance_str}</span></td>
</tr>
'''

    table_html += '</table>'
    return table_html


def generate_signatures_table() -> str:
    """
    Генерирует две наложенные друг на друга таблицы:
    1. Таблица с подписями (по рядам)
    2. Таблица с печатью (смещена на 3 клетки вправо и вниз)
    Изображения встраиваются как base64 для гарантированной загрузки
    """
    import os
    import base64

    # Получаем абсолютные пути к изображениям
    base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()

    def image_to_base64(filename):
        """Конвертирует изображение в base64 data URI"""
        img_path = os.path.join(base_dir, filename)
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                # Определяем MIME тип по расширению
                mime_type = 'image/png' if filename.endswith('.png') else 'image/jpeg'
                return f"data:{mime_type};base64,{img_base64}"
        return None

    # Конвертируем изображения в base64
    sing_2_data = image_to_base64('sing_2.png')
    sing_1_data = image_to_base64('sing_1.png')
    seal_data = image_to_base64('seal.png')

    # Проверяем, что все изображения загружены
    if not all([sing_2_data, sing_1_data, seal_data]):
        print("⚠️  Не все изображения найдены для таблицы подписей!")
        return ''

    # Размер одной клетки (примерно 8.4mm ширина, 8.49mm высота для сетки 25x35)
    cell_width = 8.4  # mm
    cell_height = 8.49  # mm
    offset_x = 3 * cell_width  # 3 клетки вправо
    offset_y = 3 * cell_height  # 3 клетки вниз

    # Таблица с подписями (базовая, по рядам)
    # Увеличиваем первую подпись на 50%
    # Сдвигаем таблицу на 3 клетки вправо (3 * 8.4mm = 25.2mm)
    signatures_table = f'''
<table class="signatures-table-base" style="width: 100%; border-collapse: collapse; margin-left: 25.2mm;">
<tr>
<td style="width: 33.33%; vertical-align: bottom;">
<img src="{sing_1_data}" alt="Подпись 1" style="display: block; width: auto; height: auto; max-width: 150mm; max-height: 60mm; margin: 0 auto;" />
</td>
<td style="width: 33.33%; vertical-align: bottom;">
<img src="{sing_2_data}" alt="Подпись 2" style="display: block; width: auto; height: auto; max-width: 100mm; max-height: 40mm; margin: 0 auto;" />
</td>
<td style="width: 33.33%;">
</td>
</tr>
</table>
'''

    # Таблица с печатью (наложенная поверх подписей)
    # Также сдвигаем на 3 клетки вправо для совпадения
    seal_table = f'''
<table class="signatures-table-overlay" style="position: absolute; top: 0; left: 25.2mm; width: 100%; border-collapse: collapse;">
<tr>
<td style="width: 33.33%; vertical-align: bottom;">
<img src="{seal_data}" alt="Печать" style="display: block; width: auto; height: auto; max-width: 150mm; max-height: 65mm; margin: 0 auto;" />
</td>
<td style="width: 33.33%;">
</td>
<td style="width: 33.33%;">
</td>
</tr>
</table>
'''

    # Обертка для наложения таблиц с CSS позиционированием
    table_html = f'''
<div class="signatures-tables-wrapper" style="position: relative; width: 100%;">
{signatures_table}
{seal_table}
</div>
'''
    print("✅ Две наложенные таблицы созданы (подписи и печать)")
    return table_html


def generate_contratto_pdf(data: dict) -> BytesIO:
    """
    API функция для генерации PDF договора
    
    Args:
        data (dict): Словарь с данными {
            'name': str - ФИО клиента,
            'amount': float - Сумма кредита,
            'duration': int - Срок в месяцах, 
            'tan': float - TAN процентная ставка,
            'taeg': float - TAEG эффективная ставка,
            'payment': float - Ежемесячный платеж (опционально, будет рассчитан)
        }
    
    Returns:
        BytesIO: PDF файл в памяти
    """
    # Рассчитываем платеж если не задан
    if 'payment' not in data:
        data['payment'] = monthly_payment(data['amount'], data['duration'], data['tan'])
    
    html = fix_html_layout('contratto')
    return _generate_pdf_with_images(html, 'contratto', data)


def generate_garanzia_pdf(name: str) -> BytesIO:
    """
    API функция для генерации PDF гарантийного письма
    
    Args:
        name (str): ФИО клиента
        
    Returns:
        BytesIO: PDF файл в памяти
    """
    html = fix_html_layout('garanzia')
    return _generate_pdf_with_images(html, 'garanzia', {'name': name})


def generate_carta_pdf(data: dict) -> BytesIO:
    """
    API функция для генерации PDF письма о карте
    
    Args:
        data (dict): Словарь с данными {
            'name': str - ФИО клиента,
            'amount': float - Сумма кредита,
            'duration': int - Срок в месяцах,
            'tan': float - TAN процентная ставка,
            'payment': float - Ежемесячный платеж (опционально, будет рассчитан)
        }
    
    Returns:
        BytesIO: PDF файл в памяти
    """
    # Рассчитываем платеж если не задан
    if 'payment' not in data:
        data['payment'] = monthly_payment(data['amount'], data['duration'], data['tan'])
    
    html = fix_html_layout('carta')
    return _generate_pdf_with_images(html, 'carta', data)


def generate_compensazione_pdf(data: dict) -> BytesIO:
    html = fix_html_layout('compensazione')
    return _generate_pdf_with_images(html, 'compensazione', data)


def generate_garanzia1of1_pdf(data: dict) -> BytesIO:
    html = fix_html_layout('garanzia1of1')
    return _generate_pdf_with_images(html, 'garanzia1of1', data)


def generate_approvazione_pdf(data: dict) -> BytesIO:
    """
    API функция для генерации PDF письма об одобрении (approvazione)
    
    Args:
        data (dict): Словарь с данными {
            'name': str - ФИО клиента,
            'amount': float - Сумма кредита,
            'duration': int - Срок в месяцах,
            'tan': float - TAN процентная ставка
        }
    
    Returns:
        BytesIO: PDF файл в памяти
    """
    html = fix_html_layout('approvazione')
    return _generate_pdf_with_images(html, 'approvazione', data)


def _generate_pdf_with_images(html: str, template_name: str, data: dict) -> BytesIO:
    """Внутренняя функция для генерации PDF с изображениями"""
    try:
        from weasyprint import HTML
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from PyPDF2 import PdfReader, PdfWriter
        from PIL import Image
        
        # Заменяем XXX на реальные данные для contratto, carta, garanzia, compensazione, garanzia1of1 и approvazione
        if template_name in ['contratto', 'carta', 'garanzia', 'compensazione', 'garanzia1of1', 'approvazione']:
            replacements = []
            if template_name == 'contratto':
                replacements = [
                    ('XXX', data['name']),  # имя клиента (первое)
                    ('XXX', format_money(data['amount'])),  # сумма кредита (БЕЗ %)
                    ('XXX', f"{data['tan']:.2f}%"),  # TAN (С %)
                    ('XXX', f"{data['taeg']:.2f}%"),  # TAEG (С %)
                    ('XXX', f"{data['duration']} mesi"),  # срок (с "mesi", БЕЗ %)
                    ('XXX', format_money(data['payment'])),  # платеж (БЕЗ %)
                    ('11/06/2025', format_date()),  # дата
                    ('XXX', data['name']),  # имя в подписи
                ]

                # Рассчитываем данные для графика платежей (по формулам Google Sheets)
                # B7 = B4/12/100  (Месячная ставка)
                # B8 = -PMT(B7; B5; B3)  (Ежемесячный платёж) - уже рассчитан в data['payment']
                # B9 = B8*B5  (Общая сумма выплат)
                # B10 = B9-B3  (Сумма переплаты)
                monthly_rate = (data['tan'] / 100) / 12
                total_payments = data['payment'] * data['duration']
                overpayment = total_payments - data['amount']

                # Заменяем плейсхолдеры графика платежей
                html = html.replace('PAYMENT_SCHEDULE_MONTHLY_RATE', f"{monthly_rate:.12f}")
                html = html.replace('PAYMENT_SCHEDULE_MONTHLY_PAYMENT', f"&euro; {format_money(data['payment'])}")
                html = html.replace('PAYMENT_SCHEDULE_TOTAL_PAYMENTS', f"&euro; {format_money(total_payments)}")
                html = html.replace('PAYMENT_SCHEDULE_OVERPAYMENT', f"&euro; {format_money(overpayment)}")

                # Отладочный вывод
                print(f"📊 Подстановка данных графика платежей:")
                print(f"   Месячная ставка: {monthly_rate:.12f}")
                print(f"   Ежемесячный платёж: €{format_money(data['payment'])}")
                print(f"   Общая сумма выплат: €{format_money(total_payments)}")
                print(f"   Сумма переплаты: €{format_money(overpayment)}")

                # Проверяем, что замена произошла
                if 'PAYMENT_SCHEDULE_MONTHLY_RATE' in html:
                    print("⚠️  ВНИМАНИЕ: Плейсхолдер PAYMENT_SCHEDULE_MONTHLY_RATE не был заменен!")
                else:
                    print("✅ Все плейсхолдеры успешно заменены")

                # Генерируем и вставляем таблицу графика платежей
                payment_schedule_table = generate_payment_schedule_table(
                    data['amount'],
                    data['duration'],
                    data['tan'],
                    data['payment']
                )
                html = html.replace('<!-- PAYMENT_SCHEDULE_TABLE_PLACEHOLDER -->', payment_schedule_table)

                # Генерируем и вставляем таблицу с подписями и печатью (перед нижней линией)
                signatures_table = generate_signatures_table()
                html = html.replace('<!-- SIGNATURES_TABLE_PLACEHOLDER -->', signatures_table)
                print("✅ Таблица с подписями и печатью добавлена перед нижней линией")

                # Добавляем класс к разделу 7 для принудительного разрыва страницы
                import re
                # Ищем параграф с "7. Firme" и добавляем класс
                html = re.sub(
                    r'(<p class="c3">\s*<span class="c7 c10">\s*7\. Firme</span>\s*</p>)',
                    r'<p class="c3 section-7-firme"><span class="c7 c10">7. Firme</span></p>',
                    html
                )
                print("✅ Раздел 7 'Firme' будет начинаться с новой страницы")
            elif template_name == 'carta':
                replacements = [
                    ('XXX', data['name']),  # имя клиента
                    ('XXX', format_money(data['amount'])),  # сумма кредита
                    ('XXX', f"{data['tan']:.2f}%"),  # TAN
                    ('XXX', f"{data['duration']} mesi"),  # срок
                    ('XXX', format_money(data['payment'])),  # платеж
                ]
            elif template_name == 'garanzia':
                replacements = [
                    ('XXX', data['name']),  # имя клиента
                ]
            elif template_name == 'approvazione':
                replacements = [
                    ('XXX', data['name']),  # имя клиента в Oggetto
                    ('XXX', data['name']),  # имя клиента в тексте
                    ('XXX', format_money(data['amount'])),  # сумма кредита
                    ('XXX', f"{data['tan']:.2f}%"),  # TAN
                    ('XXX', str(data['duration'])),  # срок в месяцах
                ]
            elif template_name in ('compensazione', 'garanzia1of1'):
                nm = data['name'].strip()
                name_display = nm if nm.endswith(',') else nm + ','
                replacements = [
                    ('XXX', format_date()),
                    ('XXX', name_display),
                    ('XXX', format_money(data['commission'])),
                    ('XXX', format_money(data['indemnity'])),
                ]
            
            for old, new in replacements:
                html = html.replace(old, new, 1)  # заменяем по одному
        
        # Конвертируем HTML в PDF
        pdf_bytes = HTML(string=html).write_pdf()
        
        # НАКЛАДЫВАЕМ ИЗОБРАЖЕНИЯ ЧЕРЕЗ REPORTLAB
        return _add_images_to_pdf(pdf_bytes, template_name)
            
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        raise

def _add_images_to_pdf(pdf_bytes: bytes, template_name: str) -> BytesIO:
    """Добавляет изображения на PDF через ReportLab"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from PyPDF2 import PdfReader, PdfWriter
        from PIL import Image
        
        # Создаем overlay с изображениями
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=A4)
        
        # Размер ячейки для расчета сдвигов
        cell_width_mm = 210/25  # 8.4mm
        cell_height_mm = 297/35  # 8.49mm
        
        if template_name == 'garanzia':
            # Добавляем company.png в центр 27-й клетки с уменьшением в 1.92 раза + сдвиг вправо на 5 клеток
            company_img = Image.open("company.png")
            company_width_mm = company_img.width * 0.264583  # пиксели в мм (96 DPI)
            company_height_mm = company_img.height * 0.264583

            # Уменьшаем в 1.6 раза (было 1.92, увеличиваем на 20%)
            company_scaled_width = company_width_mm / 1.6
            company_scaled_height = company_height_mm / 1.6

            # Клетка 27 = строка 1, колонка 1 + сдвиг на 5 клеток вправо
            row_27 = (27 - 1) // 25  # строка 1
            col_27 = (27 - 1) % 25   # колонка 1

            # Центр клетки 27 + смещение на 5 клеток вправо + 1.25 клетки правее
            x_27_center = (col_27 + 5 + 0.5 + 1.25) * cell_width_mm * mm
            y_27_center = (297 - (row_27 + 0.5) * cell_height_mm) * mm

            # Смещаем на половину размера изображения для центрирования
            x_27 = x_27_center - (company_scaled_width * mm / 2)
            y_27 = y_27_center - (company_scaled_height * mm / 2)

            # Рисуем company.png
            overlay_canvas.drawImage("company.png", x_27, y_27,
                                   width=company_scaled_width*mm, height=company_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            # Добавляем logo.png (как в contratto)
            logo_img = Image.open("logo.png")
            logo_width_mm = logo_img.width * 0.264583
            logo_height_mm = logo_img.height * 0.264583

            logo_scaled_width = logo_width_mm / 9
            logo_scaled_height = logo_height_mm / 9

            row_71 = (71 - 1) // 25
            col_71 = (71 - 1) % 25

            x_71 = (col_71 - 2 + 4) * cell_width_mm * mm
            y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm) * mm  # поднимаем на 1 клетку

            overlay_canvas.drawImage("logo.png", x_71, y_71,
                                       width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            # Добавляем seal.png в центр 590-й клетки с уменьшением в 5 раз
            seal_img = Image.open("seal.png")
            seal_width_mm = seal_img.width * 0.264583
            seal_height_mm = seal_img.height * 0.264583

            seal_scaled_width = seal_width_mm / 5
            seal_scaled_height = seal_height_mm / 5

            row_590 = (590 - 1) // 25  # строка 23
            col_590 = (590 - 1) % 25   # колонка 14

            x_590_center = (col_590 + 0.5) * cell_width_mm * mm
            y_590_center = (297 - (row_590 + 0.5) * cell_height_mm) * mm

            x_590 = x_590_center - (seal_scaled_width * mm / 2)
            y_590 = y_590_center - (seal_scaled_height * mm / 2)

            overlay_canvas.drawImage("seal.png", x_590, y_590,
                                   width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            # Добавляем sing_1.png в центр 593-й клетки с уменьшением в 5 раз
            sing1_img = Image.open("sing_1.png")
            sing1_width_mm = sing1_img.width * 0.264583
            sing1_height_mm = sing1_img.height * 0.264583

            sing1_scaled_width = sing1_width_mm / 5
            sing1_scaled_height = sing1_height_mm / 5

            row_593 = (593 - 1) // 25  # строка 23
            col_593 = (593 - 1) % 25   # колонка 17

            x_593_center = (col_593 + 0.5) * cell_width_mm * mm
            y_593_center = (297 - (row_593 + 0.5) * cell_height_mm) * mm

            x_593 = x_593_center - (sing1_scaled_width * mm / 2)
            y_593 = y_593_center - (sing1_scaled_height * mm / 2)

            overlay_canvas.drawImage("sing_1.png", x_593, y_593,
                                   width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            overlay_canvas.save()
            print("🖼️ Добавлены изображения для garanzia через ReportLab API")
        
        elif template_name in ('carta', 'compensazione', 'garanzia1of1'):
            # Страница 1 - добавляем company.png и logo.png ТОЧНО КАК В CONTRATTO (carta / compensazione / garanzia1of1)
            img = Image.open("company.png")
            img_width_mm = img.width * 0.264583
            img_height_mm = img.height * 0.264583

            scaled_width = (img_width_mm / 2) * 1.44  # +44% (было +20%, теперь еще +20%)
            scaled_height = (img_height_mm / 2) * 1.44

            row_52 = (52 - 1) // 25 + 1  # строка 3
            col_52 = (52 - 1) % 25 + 1   # колонка 2

            x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm) * mm
            y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) + 0.5 * cell_height_mm) * mm  # поднимаем на пол клетки

            overlay_canvas.drawImage("company.png", x_52, y_52,
                                       width=scaled_width*mm, height=scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            # Добавляем logo.png
            logo_img = Image.open("logo.png")
            logo_width_mm = logo_img.width * 0.264583
            logo_height_mm = logo_img.height * 0.264583

            logo_scaled_width = logo_width_mm / 9
            logo_scaled_height = logo_height_mm / 9

            row_71 = (71 - 1) // 25
            col_71 = (71 - 1) % 25

            x_71 = (col_71 - 2 + 4) * cell_width_mm * mm
            y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm) * mm  # поднимаем на 1 клетку

            overlay_canvas.drawImage("logo.png", x_71, y_71,
                                       width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            # Добавляем seal.png в центр (590+7 вниз +2 вправо)-й клетки с уменьшением в 5 раз
            seal_img = Image.open("seal.png")
            seal_width_mm = seal_img.width * 0.264583
            seal_height_mm = seal_img.height * 0.264583

            seal_scaled_width = seal_width_mm / 5
            seal_scaled_height = seal_height_mm / 5

            # Исходная клетка 590, смещаем на 7 вниз и 2 вправо
            row_590 = (590 - 1) // 25 + 7  # +7 клеток вниз
            col_590 = (590 - 1) % 25 + 2   # +2 клетки вправо

            x_590_center = (col_590 + 0.5) * cell_width_mm * mm
            y_590_center = (297 - (row_590 + 0.5) * cell_height_mm) * mm

            x_590 = x_590_center - (seal_scaled_width * mm / 2)
            y_590 = y_590_center - (seal_scaled_height * mm / 2)

            overlay_canvas.drawImage("seal.png", x_590, y_590,
                                       width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            # Добавляем sing_1.png в центр (593+7 вниз +2 вправо)-й клетки с уменьшением в 5 раз
            sing1_img = Image.open("sing_1.png")
            sing1_width_mm = sing1_img.width * 0.264583
            sing1_height_mm = sing1_img.height * 0.264583

            sing1_scaled_width = sing1_width_mm / 5
            sing1_scaled_height = sing1_height_mm / 5

            # Исходная клетка 593, смещаем на 7 вниз и 2 вправо
            row_593 = (593 - 1) // 25 + 7  # +7 клеток вниз
            col_593 = (593 - 1) % 25 + 2   # +2 клетки вправо

            x_593_center = (col_593 + 0.5) * cell_width_mm * mm
            y_593_center = (297 - (row_593 + 0.5) * cell_height_mm) * mm

            x_593 = x_593_center - (sing1_scaled_width * mm / 2)
            y_593 = y_593_center - (sing1_scaled_height * mm / 2)

            overlay_canvas.drawImage("sing_1.png", x_593, y_593,
                                       width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            overlay_canvas.save()
            print("🖼️ Добавлены изображения для carta/compensazione/garanzia1of1 через ReportLab API (company.png и logo.png как в contratto, печать и подпись смещены на 7 вниз +2 вправо)")
        
        elif template_name == 'contratto':
            # Страница 1 - добавляем company.png и logo.png
            img = Image.open("company.png")
            img_width_mm = img.width * 0.264583
            img_height_mm = img.height * 0.264583
            
            scaled_width = (img_width_mm / 2) * 1.44  # +44% (было +20%, теперь еще +20%)
            scaled_height = (img_height_mm / 2) * 1.44
            
            row_52 = (52 - 1) // 25 + 1  # строка 3
            col_52 = (52 - 1) % 25 + 1   # колонка 2
            
            x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm) * mm
            y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) + 0.5 * cell_height_mm) * mm  # поднимаем на пол клетки
            
            overlay_canvas.drawImage("company.png", x_52, y_52, 
                                   width=scaled_width*mm, height=scaled_height*mm, 
                                   mask='auto', preserveAspectRatio=True)
            
            # Добавляем logo.png
            logo_img = Image.open("logo.png")
            logo_width_mm = logo_img.width * 0.264583
            logo_height_mm = logo_img.height * 0.264583
            
            logo_scaled_width = logo_width_mm / 9
            logo_scaled_height = logo_height_mm / 9
            
            row_71 = (71 - 1) // 25
            col_71 = (71 - 1) % 25
            
            x_71 = (col_71 - 2 + 4) * cell_width_mm * mm
            y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm) * mm  # поднимаем на 1 клетку
            
            overlay_canvas.drawImage("logo.png", x_71, y_71, 
                                   width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            # Нумерация страницы 1
            row_862_p1 = (862 - 1) // 25
            col_862_p1 = (862 - 1) % 25
            
            x_page_num_p1 = (col_862_p1 + 1 + 0.5) * cell_width_mm * mm
            y_page_num_p1 = (297 - (row_862_p1 * cell_height_mm + cell_height_mm/2) - 0.25 * cell_height_mm) * mm
            
            overlay_canvas.setFillColorRGB(0, 0, 0)
            overlay_canvas.setFont("Helvetica", 10)
            overlay_canvas.drawString(x_page_num_p1-2, y_page_num_p1-2, "1")
            
            overlay_canvas.showPage()
            
            # Страница 2 - убираем принудительное добавление изображений,
            # так как подписи теперь идут в конце документа (секция 7)
            # overlay_canvas.showPage()
            
            overlay_canvas.save()
            print("🖼️ Добавлены изображения для contratto через ReportLab API")
        
        elif template_name == 'approvazione':
            # Для approvazione используем те же изображения что и для contratto
            # Страница 1 - добавляем company.png и logo.png
            img = Image.open("company.png")
            img_width_mm = img.width * 0.264583
            img_height_mm = img.height * 0.264583
            
            scaled_width = (img_width_mm / 2) * 1.44
            scaled_height = (img_height_mm / 2) * 1.44
            
            row_52 = (52 - 1) // 25 + 1
            col_52 = (52 - 1) % 25 + 1
            
            x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm) * mm
            y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) + 0.5 * cell_height_mm) * mm
            
            overlay_canvas.drawImage("company.png", x_52, y_52,
                                   width=scaled_width*mm, height=scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)

            # Добавляем logo.png (как в contratto)
            logo_img = Image.open("logo.png")
            logo_width_mm = logo_img.width * 0.264583
            logo_height_mm = logo_img.height * 0.264583

            logo_scaled_width = logo_width_mm / 9
            logo_scaled_height = logo_height_mm / 9

            row_71 = (71 - 1) // 25
            col_71 = (71 - 1) % 25

            x_71 = (col_71 - 2 + 4) * cell_width_mm * mm
            y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 0.25 * cell_height_mm) * mm  # поднимаем на 1 клетку

            overlay_canvas.drawImage("logo.png", x_71, y_71,
                                       width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                       mask='auto', preserveAspectRatio=True)

            # Нумерация страницы 1
            row_862_p1 = (862 - 1) // 25
            col_862_p1 = (862 - 1) % 25
            
            x_page_num_p1 = (col_862_p1 + 1 + 0.5) * cell_width_mm * mm
            y_page_num_p1 = (297 - (row_862_p1 * cell_height_mm + cell_height_mm/2) - 0.25 * cell_height_mm) * mm
            
            overlay_canvas.setFillColorRGB(0, 0, 0)
            overlay_canvas.setFont("Helvetica", 10)
            overlay_canvas.drawString(x_page_num_p1-2, y_page_num_p1-2, "1")
            
            overlay_canvas.showPage()
            
            # Страница 2 - sing_1.png, seal.png
            # sing_1.png
            sing1_img = Image.open("sing_1.png")
            sing1_width_mm = sing1_img.width * 0.264583
            sing1_height_mm = sing1_img.height * 0.264583
            
            # +30% к текущему размеру (было /6 * 1.1)
            sing1_scaled_width = (sing1_width_mm / 6) * 1.1 * 1.3
            sing1_scaled_height = (sing1_height_mm / 6) * 1.1 * 1.3
            
            row_628 = (628 - 1) // 25
            col_628 = (628 - 1) % 25
            
            x_628 = col_628 * cell_width_mm * mm
            y_628 = (297 - (row_628 * cell_height_mm + cell_height_mm) - 2 * cell_height_mm) * mm
            
            overlay_canvas.drawImage("sing_1.png", x_628, y_628, 
                                   width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            # seal.png
            seal_img = Image.open("seal.png")
            seal_width_mm = seal_img.width * 0.264583
            seal_height_mm = seal_img.height * 0.264583
            
            # +30% к текущему размеру (было /7)
            seal_scaled_width = (seal_width_mm / 7) * 1.3
            seal_scaled_height = (seal_height_mm / 7) * 1.3
            
            row_682 = (682 - 1) // 25
            col_682 = (682 - 1) % 25
            
            x_682 = col_682 * cell_width_mm * mm
            y_682 = (297 - (row_682 * cell_height_mm + cell_height_mm)) * mm
            
            overlay_canvas.drawImage("seal.png", x_682, y_682, 
                                   width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                   mask='auto', preserveAspectRatio=True)
            
            # Нумерация страницы 2
            row_862 = (862 - 1) // 25
            col_862 = (862 - 1) % 25
            
            x_page_num = (col_862 + 1 + 0.5) * cell_width_mm * mm
            y_page_num = (297 - (row_862 * cell_height_mm + cell_height_mm/2) - 0.25 * cell_height_mm) * mm
            
            overlay_canvas.setFillColorRGB(0, 0, 0)
            overlay_canvas.setFont("Helvetica", 10)
            overlay_canvas.drawString(x_page_num-2, y_page_num-2, "2")
            
            overlay_canvas.save()
            print("🖼️ Добавлены изображения для approvazione через ReportLab API")
        
        # Объединяем PDF с overlay
        overlay_buffer.seek(0)
        base_pdf = PdfReader(BytesIO(pdf_bytes))
        overlay_pdf = PdfReader(overlay_buffer)
        
        writer = PdfWriter()
        
        # Накладываем изображения на каждую страницу
        for i, page in enumerate(base_pdf.pages):
            if i < len(overlay_pdf.pages):
                page.merge_page(overlay_pdf.pages[i])
            writer.add_page(page)
        
        # Создаем финальный PDF с изображениями
        final_buffer = BytesIO()
        writer.write(final_buffer)
        final_buffer.seek(0)
        
        print(f"✅ PDF с изображениями создан через API! Размер: {len(final_buffer.getvalue())} байт")
        return final_buffer
        
    except Exception as e:
        print(f"❌ Ошибка наложения изображений через API: {e}")
        # Возвращаем обычный PDF без изображений
        buf = BytesIO(pdf_bytes)
        buf.seek(0)
        return buf


def fix_html_layout(template_name='contratto'):
    """Исправляем HTML для корректного отображения"""
    
    # Читаем оригинальный HTML
    html_file = f'{template_name}.html'
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Добавляем CSS для правильной разметки
    if template_name == 'garanzia':
        # Для garanzia - СТРОГО 1 СТРАНИЦА с рамкой ближе к краям
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 3mm;  /* Минимальный отступ - рамка ближе к краям */
        border: 3pt solid #f17321;  /* Оранжевая рамка */
        padding: 5mm;  /* Отступ от рамки до контента */
    }
    
    body {
        font-family: "Roboto Mono", monospace;
        font-size: 11pt;  /* Увеличиваем размер шрифта */
        line-height: 1.2;  /* Увеличиваем межстрочный интервал */
        margin: 0;
        padding: 0;
    }
    
    /* СТРОГИЙ КОНТРОЛЬ: ТОЛЬКО 1 СТРАНИЦА для garanzia */
    * {
        page-break-after: avoid !important;
        page-break-inside: avoid !important;
        page-break-before: avoid !important;
    }
    
    /* Запрещаем создание страниц после 1-й */
    @page:nth(2) {
        display: none !important;
    }
    
    /* Убираем рамки из элементов, оставляем только @page */
    .c9 {
        border: none !important;
        padding: 8pt !important;
        margin: 0 !important;
        width: 100% !important;  /* Занимаем всю ширину */
    }
    
    /* Компактная таблица на всю ширину */
    .c8 {
        margin: 0 !important;
        width: 100% !important;
        margin-left: 0 !important;  /* Убираем отступ слева */
    }
    
    /* Основной контейнер документа */
    .c12 {
        max-width: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
    }
    
    /* Параграфы с нормальными отступами */
    .c6 {
        margin: 8pt 0 !important;  /* Возвращаем отступы между абзацами */
        text-align: left !important;
        width: 100% !important;
    }
    
    /* Заголовки */
    .c2 {
        margin: 12pt 0 8pt 0 !important;  /* Отступы для заголовков */
        text-align: left !important;
    }
    
    /* Списки */
    .c0 {
        margin: 4pt 0 4pt 36pt !important;  /* Отступы для списков */
        text-align: left !important;
    }
    
    /* Убираем красное выделение */
    .c15 {
        background-color: transparent !important;
        background: none !important;
    }
    
    </style>
    """
    elif template_name in ('carta', 'compensazione', 'garanzia1of1'):
        # Для carta, compensazione и garanzia1of1 - СТРОГО 1 СТРАНИЦА с компактной версткой
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 3mm;  /* Минимальный отступ - рамка ближе к краям */
        border: 2pt solid #f17321;  /* Оранжевая рамка тоньше на 1pt */
        padding: 5mm;  /* Отступ от рамки до контента */
    }
    
    body {
        font-family: "Roboto Mono", monospace;
        font-size: 9pt;  /* Уменьшаем размер шрифта для компактности */
        line-height: 1.0;  /* Компактная высота строки */
        margin: 0;
        padding: 0;
        overflow: hidden;  /* Предотвращаем выход за границы */
    }
    
    /* СТРОГИЙ КОНТРОЛЬ: ТОЛЬКО 1 СТРАНИЦА для carta */
    * {
        page-break-after: avoid !important;
        page-break-inside: avoid !important;
        page-break-before: avoid !important;
        overflow: hidden !important;  /* Обрезаем контент если он не помещается */
    }
    
    /* Запрещаем создание страниц после 1-й */
    @page:nth(2) {
        display: none !important;
    }
    
    /* УБИРАЕМ ВСЕ рамки элементов - используем только @page рамку КАК В ДРУГИХ ШАБЛОНАХ */
    .c12, .c9, .c20, .c22, .c8 {
        border: none !important;
        padding: 2pt !important;
        margin: 0 !important;
        width: 100% !important;
        max-width: none !important;
    }
    
    /* Основной контейнер документа - компактный */
    .c12 {
        max-width: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        height: auto !important;
        overflow: hidden !important;
        border: none !important;  /* Убираем только лишние рамки, НЕ .c8 */
    }
    
    /* Параграфы с минимальными отступами */
    .c6, .c0, .c2, .c3 {
        margin: 1pt 0 !important;  /* Минимальные отступы */
        padding: 0 !important;
        text-align: left !important;
        width: 100% !important;
        line-height: 1.0 !important;
        overflow: hidden !important;
    }
    
    /* Таблицы компактные */
    table {
        margin: 1pt 0 !important;
        padding: 0 !important;
        width: 100% !important;
        font-size: 9pt !important;
        border-collapse: collapse !important;
    }
    
    td, th {
        padding: 1pt !important;
        margin: 0 !important;
        font-size: 9pt !important;
        line-height: 1.0 !important;
    }
    
    /* Убираем красное выделение и фоны */
    .c15, .c1, .c16, .c6 {
        background-color: transparent !important;
        background: none !important;
    }
    
    /* Списки компактные */
    ul, ol, li {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.0 !important;
    }
    
    /* Заголовки компактные */
    h1, h2, h3, h4, h5, h6 {
        margin: 2pt 0 !important;
        padding: 0 !important;
        font-size: 10pt !important;
        line-height: 1.0 !important;
    }
    
    /* СЕТКА ДЛЯ ПОЗИЦИОНИРОВАНИЯ ИЗОБРАЖЕНИЙ 25x35 - КАК В ДРУГИХ ШАБЛОНАХ */
    .grid-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 210mm;  /* Полная ширина A4 */
        height: 297mm; /* Полная высота A4 */
        pointer-events: none;
        z-index: 1000;
        opacity: 0; /* 0% прозрачности - невидимая */
    }
    
    .grid-cell {
        position: absolute;
        border: none;
        background-color: transparent;
        display: none;
        font-size: 6pt;
        font-weight: bold;
        color: transparent;
        font-family: Arial, sans-serif;
        box-sizing: border-box;
    }
    
    </style>
    """
        if template_name in ('compensazione', 'garanzia1of1'):
            # compensazione / garanzia1of1: эталон GARANZIA — заголовок Arial, тело Courier; жирность c4; висячий отступ у •
            # База carta задаёт body Roboto Mono и * { overflow:hidden } — ниже переопределяем под эталон.
            css_fixes += """
    <style>
    body.c9.doc-content {
        padding-top: 7em !important;
        font-family: "Courier New", Courier, monospace !important;
        font-size: 11pt !important;
        line-height: 1.15 !important;
    }
    body.c9.doc-content td.c8 {
        overflow: visible !important;
    }
    body.c9.doc-content td.c8 p,
    body.c9.doc-content td.c8 span {
        overflow: visible !important;
    }
    body.c9.doc-content td.c8 span.comp-title {
        font-family: Arial, Helvetica, sans-serif !important;
        font-weight: 700 !important;
        font-size: 13pt !important;
    }
    body.c9.doc-content td.c8 span:not(.comp-title) {
        font-family: "Courier New", Courier, monospace !important;
        font-size: 11pt !important;
        line-height: 1.15 !important;
    }
    body.c9.doc-content span.c4 {
        font-weight: 700 !important;
    }
    body.c9.doc-content span.c5 {
        font-weight: 400 !important;
    }
    body.c9.doc-content p.comp-bullet {
        margin: 6pt 0 8pt 0 !important;
        padding-left: 1.35em !important;
        text-indent: -1.35em !important;
    }
    body.c9.doc-content p.comp-quote {
        margin: 0 0 10pt 0 !important;
        padding-left: 2em !important;
        text-indent: 0 !important;
    }
    body.c9.doc-content p.comp-line-data {
        margin-bottom: 3pt !important;
    }
    body.c9.doc-content p.comp-line-gentile {
        margin-bottom: 6pt !important;
    }
    body.c9.doc-content p.comp-saluti {
        margin-top: 12pt !important;
    }
    </style>
    """
    elif template_name == 'approvazione':
        # Для approvazione — 2 страницы как у contratto, но с увеличенным интерлиньяжем 1.25
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 6mm;  /* Отступ как в contratto */
        border: 3pt solid #f17321;  /* Оранжевая рамка на каждой странице */
        padding: 3mm;  /* Отступ от рамки до контента */
    }
    
    body {
        font-family: "Roboto Mono", monospace;
        font-size: 10pt;
        line-height: 1.25;  /* Увеличенный интервал */
        margin: 0;
        padding: 0;
    }
    
    /* Убираем рамки из внутренних контейнеров, оставляем только @page */
    .c20 {
        border: none !important;
        padding: 3mm !important;
        margin: 0 !important;
    }
    
    /* Контроль разрывов — максимум 2 страницы */
    * {
        page-break-after: avoid !important;
        page-break-inside: avoid !important;
    }
    
    .page-break {
        page-break-before: always !important;
        page-break-after: avoid !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Базовые текстовые блоки с интервалом 1.25 */
    p, .c3, .c24, li, td, th {
        line-height: 1.25 !important;
    }

    /* Пункты-"буллеты" (строки, начинающиеся с символа •) — интервал 1.5 */
    .bullet {
        line-height: 1.5 !important;
        margin: 4pt 0 !important; /* доп. расстояние между пунктами */
    }
    
    /* Нормальные отступы как в contratto */
    p {
        margin: 2pt 0 !important;
        padding: 0 !important;
    }
    
    table {
        margin: 3pt 0 !important;
        font-size: 10pt !important;
        border-collapse: collapse !important;
    }
    
    /* Убираем Google Docs стили */
    .c22 {
        max-width: none !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }
    
    .c14, .c25 {
        margin-left: 0 !important;
    }
    
    /* Заголовки — тоже немного выше, если встретятся */
    .c15, .c10, h1, h2, h3, h4, h5, h6 {
        line-height: 1.25 !important;
    }
    
    /* Убираем красное выделение */
    .c1, .c16 {
        background-color: transparent !important;
        background: none !important;
    }
    
    /* Сетка позиционирования 25x35 */
    .grid-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 210mm;
        height: 297mm;
        pointer-events: none;
        z-index: 1000;
        opacity: 0;
    }
    .grid-cell {
        position: absolute;
        border: none;
        background-color: transparent;
        display: none;
        font-size: 6pt;
        font-weight: bold;
        color: transparent;
        font-family: Arial, sans-serif;
        box-sizing: border-box;
    }
    </style>
    """
    else:
        # Для contratto и carta - 2 СТРАНИЦЫ
        css_fixes = """
    <style>
    @page {
        size: A4;
        margin: 6mm;  /* Уменьшенный отступ для экономии места */
        border: 3pt solid #f17321;  /* Оранжевая рамка на каждой странице */
        padding: 3mm;  /* Отступ от рамки до контента */
    }
    
    body {
        font-family: "Roboto Mono", monospace;
        font-size: 10pt;  /* Возвращаем нормальный размер шрифта */
        line-height: 1.0;  /* Нормальная высота строки */
        margin: 0;
        padding: 0;
    }
    
    /* КРИТИЧНО: Убираем фиксированные высоты из таблиц, которые создают огромные пробелы */
    .c13, .c19 {
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
    }
    
    /* Убираем рамки из элементов, оставляем только @page */
    .c20 {
        border: none !important;
        padding: 3mm !important;  /* Нормальные отступы */
        margin: 0 !important;
    }
    
    /* СТРОГИЙ КОНТРОЛЬ: МАКСИМУМ 2 СТРАНИЦЫ */
    * {
        page-break-after: avoid !important;
        page-break-inside: avoid !important;
    }
    
    .page-break {
        page-break-before: always !important;
        page-break-after: avoid !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* ВОССТАНАВЛИВАЕМ НОРМАЛЬНЫЕ ОТСТУПЫ В ТЕКСТЕ */
    p {
        margin: 2pt 0 !important;  /* Нормальные отступы между параграфами */
        padding: 0 !important;
        line-height: 1.0 !important;
    }
    
    div {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    table {
        margin: 3pt 0 !important;  /* Нормальные отступы для таблиц */
        font-size: 10pt !important;  /* Нормальный размер шрифта */
    }
    
    /* Убираем Google Docs стили */
    .c22 {
        max-width: none !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }
    
    .c14, .c25 {
        margin-left: 0 !important;
    }
    
    /* НОРМАЛЬНЫЕ ЗАГОЛОВКИ С ОТСТУПАМИ */
    .c15 {
        font-size: 14pt !important;  /* Возвращаем нормальный размер */
        margin: 4pt 0 !important;    /* Нормальные отступы */
        font-weight: 700 !important;
    }
    
    .c10 {
        font-size: 12pt !important;  /* Возвращаем нормальный размер */
        margin: 3pt 0 !important;    /* Нормальные отступы */
        font-weight: 700 !important;
    }
    
    /* ТОЛЬКО пустые элементы делаем невидимыми - НЕ ТРОГАЕМ текстовые! */
    .c6:empty {
        height: 0pt !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Нормальные отступы для списков */
    .c3 {
        margin: 1pt 0 !important;
    }
    
    /* Запрещаем создание страниц после 2-й */
    @page:nth(3) {
        display: none !important;
    }
    
    /* УБИРАЕМ КРАСНОЕ ВЫДЕЛЕНИЕ ТЕКСТА */
    .c1, .c16 {
        background-color: transparent !important;
        background: none !important;
    }
    
    /* СЕТКА ДЛЯ ПОЗИЦИОНИРОВАНИЯ ИЗОБРАЖЕНИЙ 25x35 - НА КАЖДОЙ СТРАНИЦЕ */
    .grid-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 210mm;  /* Полная ширина A4 */
        height: 297mm; /* Полная высота A4 */
        pointer-events: none;
        z-index: 1000;
        opacity: 0; /* 0% прозрачности - невидимая */
    }
    
    /* Сетка для каждой страницы отдельно */
    .page-grid {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100vh;
        pointer-events: none;
        z-index: 1000;
        opacity: 0.3;
    }
    
    .grid-cell {
        position: absolute;
        border: none;
        background-color: transparent;
        display: none;
        font-size: 6pt;
        font-weight: bold;
        color: transparent;
        font-family: Arial, sans-serif;
        box-sizing: border-box;
    }
    
    /* Позиционирование относительно сетки */
    .positioned-image {
        position: absolute;
        z-index: 500;
    }
    
    </style>
    """
    
    # Вставляем CSS после тега <head>
    html = html.replace('<head>', f'<head>{css_fixes}')
    
    # НЕ НУЖНО - используем @page рамку как в других шаблонах
    
    # КРИТИЧНО: СНАЧАЛА убираем старые изображения, ПОТОМ добавляем новые!
    import re
    
    # Очистка HTML в зависимости от шаблона
    if template_name == 'contratto':
        # 1. ПОЛНОСТЬЮ убираем блок с 3 изображениями между разделами
        # Новая регулярка для гибкого поиска
        middle_images_pattern = r'<p class="c3"><span[^>]*><img[^>]*images/image1\.png[^>]*>.*?<\/p>'
        html = re.sub(middle_images_pattern, '', html, flags=re.DOTALL)
        
        # Также убираем пустые параграфы, которые могли быть вокруг этого блока
        html = re.sub(r'(<p class="c3 c6"><span class="c7 c12"></span></p>\s*)+', '', html)
        html = re.sub(r'(<p class="c24 c6"><span class="c7 c12"></span></p>\s*)+', '', html)
        
        # Убираем все изображения, которые не image3.png (image3 - это маленькая полоска разделителя)
        # image1, image2, image4, image5 - это большие логотипы и подписи, которые создают проблемы
        html = re.sub(r'<span[^>]*><img[^>]*images/image1\.png[^>]*>.*?</span>', '', html, flags=re.DOTALL)
        html = re.sub(r'<span[^>]*><img[^>]*images/image2\.png[^>]*>.*?</span>', '', html, flags=re.DOTALL)
        html = re.sub(r'<span[^>]*><img[^>]*images/image4\.png[^>]*>.*?</span>', '', html, flags=re.DOTALL)
        html = re.sub(r'<span[^>]*><img[^>]*images/image5\.png[^>]*>.*?</span>', '', html, flags=re.DOTALL)
        
        # И убираем пустые контейнеры span, которые могли остаться
        html = re.sub(r'<span[^>]*style="[^"]*width:\s*[\d\.]+px;\s*height:\s*[\d\.]+px[^"]*"[^>]*>\s*</span>', '', html)

        # Принудительно убираем высоты у таблиц
        html = html.replace('class="c13"', 'class="c13" style="height: auto !important; min-height: 0 !important;"')
        html = html.replace('class="c19"', 'class="c19" style="height: auto !important; min-height: 0 !important;"')
        html = html.replace('class="c20"', 'class="c20" style="height: auto !important; min-height: 0 !important;"')
        
        # КРИТИЧНО: Заменяем фиксированные высоты в CSS стилях напрямую
        html = re.sub(r'\.c13\{[^}]*height:\s*[\d\.]+pt[^}]*\}', '.c13{height: auto !important;}', html)
        html = re.sub(r'\.c19\{[^}]*height:\s*[\d\.]+pt[^}]*\}', '.c19{height: auto !important;}', html)
        html = re.sub(r'\.c13\{height:\s*[\d\.]+pt\}', '.c13{height: auto !important;}', html)
        html = re.sub(r'\.c19\{height:\s*[\d\.]+pt\}', '.c19{height: auto !important;}', html)
    
        # 2. Убираем ВСЕ пустые div и параграфы в конце
        html = re.sub(r'<div><p class="c6 c18"><span class="c7 c23"></span></p></div>$', '', html)
        html = re.sub(r'<p class="c3 c6"><span class="c7 c12"></span></p>$', '', html)
        html = re.sub(r'<p class="c6 c24"><span class="c7 c12"></span></p>$', '', html)
        
        # 3. Убираем избыточные пустые строки между разделами (НЕ в тексте!)
        html = re.sub(r'(<p class="c3 c6"><span class="c7 c12"></span></p>\s*){2,}', '<p class="c3 c6"><span class="c7 c12"></span></p>', html)
        html = re.sub(r'(<p class="c24 c6"><span class="c7 c12"></span></p>\s*)+', '', html)
        
        # 4. Убираем лишние высоты из таблиц
        html = html.replace('class="c13"', 'class="c13" style="height: auto !important;"')
        html = html.replace('class="c19"', 'class="c19" style="height: auto !important;"')
        
        # 5. Принудительно разбиваем на 2 страницы: после раздела 2 (Agevolazioni)
        agevolazioni_end = html.find('• Bonifici SEPA e SDD gratuiti, senza spese aggiuntive')
        if agevolazioni_end != -1:
            # Находим конец этого раздела
            next_section_start = html.find('</td></tr></table>', agevolazioni_end)
            if next_section_start != -1:
                # Вставляем разрыв страницы
                html = html[:next_section_start] + '</td></tr></table><div class="page-break"></div>' + html[next_section_start+len('</td></tr></table>'):]
    
    elif template_name == 'garanzia':
        # Убираем ВСЕ изображения из garanzia - они создают лишние страницы
        # Убираем логотип в начале
        logo_pattern = r'<p class="c6"><span style="overflow: hidden[^>]*><img alt="" src="images/image2\.png"[^>]*></span></p>'
        html = re.sub(logo_pattern, '', html)
        
        # Убираем изображения в конце (печать и подпись)
        seal_pattern = r'<p class="c6"><span style="overflow: hidden[^>]*><img alt="" src="images/image1\.png"[^>]*></span></p>'
        html = re.sub(seal_pattern, '', html)
        
        signature_pattern = r'<span style="overflow: hidden[^>]*><img alt="" src="images/image3\.png"[^>]*></span>'
        html = re.sub(signature_pattern, '', html)
        
        print("🗑️ Удалены все изображения из garanzia для предотвращения лишних страниц")
    elif template_name in ('carta', 'compensazione', 'garanzia1of1'):
        # Убираем ВСЕ изображения из carta/compensazione/garanzia1of1 - они создают лишние страницы
        # Убираем логотип в начале
        logo_pattern = r'<p class="c12"><span style="overflow: hidden[^>]*><img alt="" src="images/image1\.png"[^>]*></span></p>'
        html = re.sub(logo_pattern, '', html)
        
        # Убираем изображения в тексте (печать и подпись)
        seal_pattern = r'<span style="overflow: hidden[^>]*><img alt="" src="images/image2\.png"[^>]*></span>'
        html = re.sub(seal_pattern, '', html)
        
        signature_pattern = r'<span style="overflow: hidden[^>]*><img alt="" src="images/image3\.png"[^>]*></span>'
        html = re.sub(signature_pattern, '', html)
        
        # Убираем ВСЕ пустые div и параграфы которые создают лишние страницы
        html = re.sub(r'<div><p class="c6 c18"><span class="c7 c23"></span></p></div>', '', html)
        html = re.sub(r'<p class="c3 c6"><span class="c7 c12"></span></p>', '', html)
        html = re.sub(r'<p class="c6 c24"><span class="c7 c12"></span></p>', '', html)
        html = re.sub(r'<p class="c6"><span class="c7"></span></p>', '', html)
        
        # Убираем избыточные пустые строки между разделами
        html = re.sub(r'(<p class="c3 c6"><span class="c7 c12"></span></p>\s*){2,}', '', html)
        html = re.sub(r'(<p class="c24 c6"><span class="c7 c12"></span></p>\s*)+', '', html)
        
        # Убираем лишние высоты из таблиц - принудительно делаем auto
        html = html.replace('class="c13"', 'class="c13" style="height: auto !important;"')
        html = html.replace('class="c19"', 'class="c19" style="height: auto !important;"')
        html = html.replace('class="c5"', 'class="c5" style="height: auto !important;"')
        html = html.replace('class="c9"', 'class="c9" style="height: auto !important;"')
        
        # КРИТИЧНО: Убираем всё что может создать вторую страницу в конце документа
        # Ищем закрывающий тег body и убираем всё лишнее перед ним
        body_end = html.rfind('</body>')
        if body_end != -1:
            # Находим последний значимый контент перед </body>
            content_before_body = html[:body_end].rstrip()
            # Убираем trailing пустые параграфы и divs
            content_before_body = re.sub(r'(<p[^>]*><span[^>]*></span></p>\s*)+$', '', content_before_body)
            content_before_body = re.sub(r'(<div[^>]*></div>\s*)+$', '', content_before_body)
            html = content_before_body + '\n</body></html>'
        
        print("🗑️ Удалены все изображения из carta/compensazione/garanzia1of1 для предотвращения лишних страниц")
        print("🗑️ Убраны пустые элементы в конце документа для строгого контроля 1 страницы")
        
    elif template_name == 'approvazione':
        # Для approvazione используем те же правила что и для contratto
        # 1. ПОЛНОСТЬЮ убираем блок с 3 изображениями в конце
        middle_images_pattern = r'<p class="c3"><span style="overflow: hidden[^>]*><img alt="" src="images/image1\.png"[^>]*></span><span style="overflow: hidden[^>]*><img alt="" src="images/image2\.png"[^>]*></span><span style="overflow: hidden[^>]*><img alt="" src="images/image4\.png"[^>]*></span></p>'
        html = re.sub(middle_images_pattern, '', html)
    
        # 2. Убираем ВСЕ пустые div и параграфы
        html = re.sub(r'<p class="c3 c6"><span class="c7 c26"></span></p>', '', html)
        html = re.sub(r'<p class="c24 c6"><span class="c7 c26"></span></p>', '', html)
        
        # 3. Убираем лишние высоты из таблиц
        html = html.replace('class="c13"', 'class="c13" style="height: auto !important;"')

        # 4. Помечаем все абзацы, начинающиеся с символа •, как .bullet для интерлиньяжa 1.5
        bullet_pattern = r'<p class="c3">(\s*)<span class="c7 c4">\s*•'
        html = re.sub(bullet_pattern, r'<p class="c3 bullet">\1<span class="c7 c4"> •', html)
        
        print("🗑️ Удалены изображения из approvazione")

    
    # Общая очистка для всех шаблонов
    # Убираем лишние высоты из таблиц
    html = html.replace('class="c5"', 'class="c5" style="height: auto !important;"')
    html = html.replace('class="c9"', 'class="c9" style="height: auto !important;"')
    
    print("🗑️ Удалены: блок изображений между разделами, пустые div, лишние параграфы")
    print("📄 Установлен принудительный разрыв после раздела 'Agevolazioni'")
    
    # ГЕНЕРИРУЕМ СЕТКУ 25x35 ДЛЯ ПОЗИЦИОНИРОВАНИЯ
    def generate_grid():
        """Генерирует HTML сетку 25x35 с нумерацией для A4"""
        grid_html = '<div class="grid-overlay">\n'
        
        # Размеры страницы A4 в миллиметрах
        page_width_mm = 210  # A4 ширина
        page_height_mm = 297  # A4 высота
        
        cell_width_mm = page_width_mm / 25  # 8.4mm на ячейку
        cell_height_mm = page_height_mm / 35  # 8.49mm на ячейку
        
        cell_number = 1
        
        for row in range(35):
            for col in range(25):
                x_mm = col * cell_width_mm
                y_mm = row * cell_height_mm
                
                grid_html += f'''    <div class="grid-cell" style="
                    left: {x_mm:.1f}mm; 
                    top: {y_mm:.1f}mm; 
                    width: {cell_width_mm:.1f}mm; 
                    height: {cell_height_mm:.1f}mm;">
                    {cell_number}
                </div>\n'''
                
                cell_number += 1
        
        grid_html += '</div>\n'
        return grid_html
    
    
    # Функция для размещения изображения по номеру квадрата
    def place_image_at_cell(cell_number, image_path):
        """Размещает изображение с левой гранью в указанном квадрате"""
        page_width_mm = 210
        page_height_mm = 297
        cell_width_mm = page_width_mm / 25  # 8.4mm
        cell_height_mm = page_height_mm / 35  # 8.49mm
        
        row = (cell_number - 1) // 25
        col = (cell_number - 1) % 25
        x = col * cell_width_mm  # Левая грань квадрата
        y = row * cell_height_mm  # Верхняя грань квадрата
        
        return f'''<img src="{image_path}" style="
            position: absolute;
            left: {x:.1f}mm;
            top: {y:.1f}mm;
            z-index: 600;
        " />\n'''
    
    # Добавляем сетку в body (для contratto, carta, compensazione, garanzia1of1 и approvazione)
    if template_name in ['contratto', 'carta', 'compensazione', 'garanzia1of1', 'approvazione']:
        grid_overlay = generate_grid()
        if template_name in ['contratto', 'approvazione']:
            html = html.replace('<body class="c22 doc-content">', f'<body class="c22 doc-content">\n{grid_overlay}')
        elif template_name in ('carta', 'compensazione', 'garanzia1of1'):
            # Для carta / compensazione / garanzia1of1 — body c9
            html = html.replace('<body class="c9 doc-content">', f'<body class="c9 doc-content">\n{grid_overlay}')
        print("🔢 Добавлена сетка позиционирования 25x35")
        print("📋 Изображения будут добавлены через ReportLab поверх PDF")
    else:
        print("📋 Простой PDF без сетки и изображений")
    
    # НЕ СОХРАНЯЕМ исправленный HTML - не нужен
    
    print(f"✅ HTML обработан в памяти (файл не сохраняется)")
    print("🔧 Рамка зафиксирована через @page - будет на каждой странице!")
    print("📄 Удалены изображения между разделами - главная причина лишних страниц")
    
    # Тестовые данные удалены - используем только данные из API
    
    return html

if __name__ == '__main__':
    import sys
    
    # Определяем какой шаблон обрабатывать
    template = sys.argv[1] if len(sys.argv) > 1 else 'contratto'
    
    print(f"🔧 Исправляем разметку для {template} - 2 страницы с рамками...")
    fixed_html = fix_html_layout(template)
    
    # Тестируем конвертацию
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=fixed_html).write_pdf()
        
        # НАКЛАДЫВАЕМ ИЗОБРАЖЕНИЯ И СЕТКУ ЧЕРЕЗ REPORTLAB
        if template in ['contratto', 'garanzia', 'carta', 'compensazione', 'garanzia1of1']:
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.units import mm
                from PyPDF2 import PdfReader, PdfWriter
                from io import BytesIO
                
                # Создаем overlay с изображениями и/или сеткой
                overlay_buffer = BytesIO()
                overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=A4)
                
                # Размер ячейки для расчета сдвигов
                cell_width_mm = 210/25  # 8.4mm
                cell_height_mm = 297/35  # 8.49mm
                
                if template == 'garanzia':
                    # Для garanzia - сетка НЕВИДИМАЯ (0% прозрачности)
                    # overlay_canvas.setStrokeColorRGB(0.7, 0.7, 0.7)  # Серый цвет для сетки
                    # overlay_canvas.setLineWidth(0.3)
                    
                    # # Рисуем вертикальные линии
                    # for col in range(26):  # 0-25 (26 линий)
                    #     x = col * cell_width_mm * mm
                    #     overlay_canvas.line(x, 0, x, 297*mm)
                    
                    # # Рисуем горизонтальные линии
                    # for row in range(36):  # 0-35 (36 линий)
                    #     y = row * cell_height_mm * mm
                    #     overlay_canvas.line(0, y, 210*mm, y)
                    
                    # # Нумеруем ячейки
                    # overlay_canvas.setFillColorRGB(0.5, 0.5, 0.5)  # Серый цвет для номеров
                    # overlay_canvas.setFont("Helvetica", 6)
                    
                    # cell_number = 1
                    # for row in range(35):
                    #     for col in range(25):
                    #         x = (col + 0.1) * cell_width_mm * mm
                    #         y = (297 - (row + 0.8) * cell_height_mm) * mm  # ReportLab считает от низа
                    #         overlay_canvas.drawString(x, y, str(cell_number))
                    #         cell_number += 1
                    
                    # Добавляем company.png в центр 27-й клетки с уменьшением в 6 раз
                    from PIL import Image
                    company_img = Image.open("company.png")
                    company_width_mm = company_img.width * 0.264583  # пиксели в мм (96 DPI)
                    company_height_mm = company_img.height * 0.264583
                    
                    # Уменьшаем в 1.92 раза (было 2.5, увеличиваем на 30%)
                    company_scaled_width = company_width_mm / 1.92
                    company_scaled_height = company_height_mm / 1.92
                    
                    # Клетка 27 = строка 1, колонка 1 (27-1=26, 26//25=1, 26%25=1)
                    row_27 = (27 - 1) // 25  # строка 1
                    col_27 = (27 - 1) % 25   # колонка 1
                    
                    # Центр клетки 27 + смещение на 5 клеток вправо
                    x_27_center = (col_27 + 5 + 0.5) * cell_width_mm * mm  # центр по X + 5 клеток вправо
                    y_27_center = (297 - (row_27 + 0.5) * cell_height_mm) * mm  # центр по Y (ReportLab от низа)
                    
                    # Смещаем на половину размера изображения для центрирования
                    x_27 = x_27_center - (company_scaled_width * mm / 2)
                    y_27 = y_27_center - (company_scaled_height * mm / 2)
                    
                    # Рисуем company.png в центре 27-й клетки
                    overlay_canvas.drawImage("company.png", x_27, y_27, 
                                           width=company_scaled_width*mm, height=company_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем seal.png в центр 590-й клетки с уменьшением в 5 раз
                    seal_img = Image.open("seal.png")
                    seal_width_mm = seal_img.width * 0.264583  # пиксели в мм (96 DPI)
                    seal_height_mm = seal_img.height * 0.264583
                    
                    # Уменьшаем в 5 раз
                    seal_scaled_width = seal_width_mm / 5
                    seal_scaled_height = seal_height_mm / 5
                    
                    # Клетка 590 = строка 23, колонка 14 (590-1=589, 589//25=23, 589%25=14)
                    row_590 = (590 - 1) // 25  # строка 23
                    col_590 = (590 - 1) % 25   # колонка 14
                    
                    # Центр клетки 590
                    x_590_center = (col_590 + 0.5) * cell_width_mm * mm  # центр по X
                    y_590_center = (297 - (row_590 + 0.5) * cell_height_mm) * mm  # центр по Y (ReportLab от низа)
                    
                    # Смещаем на половину размера изображения для центрирования
                    x_590 = x_590_center - (seal_scaled_width * mm / 2)
                    y_590 = y_590_center - (seal_scaled_height * mm / 2)
                    
                    # Рисуем seal.png в центре 590-й клетки
                    overlay_canvas.drawImage("seal.png", x_590, y_590, 
                                           width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем sing_1.png в центр 593-й клетки с уменьшением в 5 раз
                    sing1_img = Image.open("sing_1.png")
                    sing1_width_mm = sing1_img.width * 0.264583  # пиксели в мм (96 DPI)
                    sing1_height_mm = sing1_img.height * 0.264583
                    
                    # Уменьшаем в 5 раз
                    sing1_scaled_width = sing1_width_mm / 5
                    sing1_scaled_height = sing1_height_mm / 5
                    
                    # Клетка 593 = строка 23, колонка 17 (593-1=592, 592//25=23, 592%25=17)
                    row_593 = (593 - 1) // 25  # строка 23
                    col_593 = (593 - 1) % 25   # колонка 17
                    
                    # Центр клетки 593
                    x_593_center = (col_593 + 0.5) * cell_width_mm * mm  # центр по X
                    y_593_center = (297 - (row_593 + 0.5) * cell_height_mm) * mm  # центр по Y (ReportLab от низа)
                    
                    # Смещаем на половину размера изображения для центрирования
                    x_593 = x_593_center - (sing1_scaled_width * mm / 2)
                    y_593 = y_593_center - (sing1_scaled_height * mm / 2)
                    
                    # Рисуем sing_1.png в центре 593-й клетки
                    overlay_canvas.drawImage("sing_1.png", x_593, y_593, 
                                           width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    print("🔢 Добавлена сетка 25x35 для garanzia через ReportLab")
                    print("🖼️ Добавлено company.png в 27-й клетке + 5 клеток вправо (уменьшено в 1.92 раза)")
                    print("🖼️ Добавлено seal.png в центр 590-й клетки (уменьшено в 5 раз)")
                    print("🖼️ Добавлено sing_1.png в центр 593-й клетки (уменьшено в 5 раз)")
                    overlay_canvas.save()
                
                elif template in ('carta', 'compensazione', 'garanzia1of1'):
                    # ДОБАВЛЯЕМ company.png и logo.png ТОЧНО КАК В CONTRATTO (carta / compensazione / garanzia1of1)
                    from PIL import Image

                    # Получаем размер изображения company.png для масштабирования
                    img = Image.open("company.png")
                    img_width_mm = img.width * 0.264583  # пиксели в мм (96 DPI)
                    img_height_mm = img.height * 0.264583

                    # Увеличиваем на 20% (было уменьшение в 2 раза, теперь увеличиваем)
                    scaled_width = (img_width_mm / 2) * 1.2  # +20% к уменьшенному размеру
                    scaled_height = (img_height_mm / 2) * 1.2

                    # Размер ячейки для расчета сдвигов
                    cell_width_mm = 210/25  # 8.4mm
                    cell_height_mm = 297/35  # 8.49mm

                    # Страница 1: изображение company.png в квадрате 52 + сдвиг (влево на 0.5, вниз на 0.5)
                    # Квадрат 52 = строка 2, колонка 1 (нумерация с 1)
                    row_52 = (52 - 1) // 25 + 1  # строка 2 + 1 = строка 3
                    col_52 = (52 - 1) % 25 + 1   # колонка 1 + 1 = колонка 2

                    # Левая грань квадрата + сдвиги (ReportLab считает от НИЗА страницы!)
                    x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm) * mm  # влево на пол клетки
                    y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) - 0.5 * cell_height_mm) * mm  # вниз на пол клетки

                    # Рисуем с увеличением на 20% и сохранением прозрачности
                    overlay_canvas.drawImage("company.png", x_52, y_52,
                                           width=scaled_width*mm, height=scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)

                    # Добавляем logo.png в квадрат 71 первой страницы с уменьшением в 9 раз и сдвигом влево на 2 клетки, затем вправо на 4
                    # Квадрат 71 = строка 2, колонка 20 (71-1=70, 70//25=2, 70%25=20)
                    row_71 = (71 - 1) // 25  # строка 2
                    col_71 = (71 - 1) % 25   # колонка 20

                    # Получаем размер logo.png для уменьшения в 9 раз
                    logo_img = Image.open("logo.png")
                    logo_width_mm = logo_img.width * 0.264583  # пиксели в мм (96 DPI)
                    logo_height_mm = logo_img.height * 0.264583

                    # Уменьшаем в 9 раз (3 * 3)
                    logo_scaled_width = logo_width_mm / 9  # уменьшение в 9 раз
                    logo_scaled_height = logo_height_mm / 9

                    # Левая грань квадрата 71 + сдвиг вправо на 4 клетки и вниз на 1.25 клетки
                    x_71 = (col_71 - 2 + 4) * cell_width_mm * mm  # было влево на 2, теперь вправо на 4
                    y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 1.25 * cell_height_mm) * mm  # вниз на 1.25 клетки

                    # Рисуем logo.png с уменьшением в 9 раз
                    overlay_canvas.drawImage("logo.png", x_71, y_71,
                                           width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)

                    if template == 'carta':
                        # Добавляем carta_logo.png в 63-ю клетку с увеличением на 20% (уменьшение в 4.17 раз)
                        carta_logo_img = Image.open("carta_logo.png")
                        carta_logo_width_mm = carta_logo_img.width * 0.264583  # пиксели в мм (96 DPI)
                        carta_logo_height_mm = carta_logo_img.height * 0.264583
                        
                        # Уменьшаем в 4.17 раз (было 5, увеличиваем на 20%)
                        carta_logo_scaled_width = (carta_logo_width_mm / 5) * 1.2  # +20%
                        carta_logo_scaled_height = (carta_logo_height_mm / 5) * 1.2
                        
                        # Клетка 63 = строка 2, колонка 12 (63-1=62, 62//25=2, 62%25=12)
                        row_63 = (63 - 1) // 25  # строка 2
                        col_63 = (63 - 1) % 25   # колонка 12
                        
                        # Центр клетки 63 + смещение вверх на 1/3 клетки
                        x_63_center = (col_63 + 0.5) * cell_width_mm * mm  # центр по X
                        y_63_center = (297 - (row_63 + 0.5) * cell_height_mm) * mm + (cell_height_mm * mm / 3)  # центр по Y + 1/3 клетки вверх
                        
                        # Смещаем на половину размера изображения для центрирования
                        x_63 = x_63_center - (carta_logo_scaled_width * mm / 2)
                        y_63 = y_63_center - (carta_logo_scaled_height * mm / 2)
                        
                        # Рисуем carta_logo.png в центре 63-й клетки
                        overlay_canvas.drawImage("carta_logo.png", x_63, y_63, 
                                               width=carta_logo_scaled_width*mm, height=carta_logo_scaled_height*mm,
                                               mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем seal.png в центр 590-й клетки с уменьшением в 5 раз (КАК В GARANZIA)
                    seal_img = Image.open("seal.png")
                    seal_width_mm = seal_img.width * 0.264583  # пиксели в мм (96 DPI)
                    seal_height_mm = seal_img.height * 0.264583
                    
                    # Уменьшаем в 5 раз
                    seal_scaled_width = seal_width_mm / 5
                    seal_scaled_height = seal_height_mm / 5
                    
                    # Клетка 590 = строка 23, колонка 14 (590-1=589, 589//25=23, 589%25=14)
                    row_590 = (590 - 1) // 25  # строка 23
                    col_590 = (590 - 1) % 25   # колонка 14
                    
                    # Центр клетки 590
                    x_590_center = (col_590 + 0.5) * cell_width_mm * mm  # центр по X
                    y_590_center = (297 - (row_590 + 0.5) * cell_height_mm) * mm  # центр по Y (ReportLab от низа)
                    
                    # Смещаем на половину размера изображения для центрирования
                    x_590 = x_590_center - (seal_scaled_width * mm / 2)
                    y_590 = y_590_center - (seal_scaled_height * mm / 2)
                    
                    # Рисуем seal.png в центре 590-й клетки
                    overlay_canvas.drawImage("seal.png", x_590, y_590, 
                                           width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем sing_1.png в центр 593-й клетки с уменьшением в 5 раз (КАК В GARANZIA)
                    sing1_img = Image.open("sing_1.png")
                    sing1_width_mm = sing1_img.width * 0.264583  # пиксели в мм (96 DPI)
                    sing1_height_mm = sing1_img.height * 0.264583
                    
                    # Уменьшаем в 5 раз
                    sing1_scaled_width = sing1_width_mm / 5
                    sing1_scaled_height = sing1_height_mm / 5
                    
                    # Клетка 593 = строка 23, колонка 17 (593-1=592, 592//25=23, 592%25=17)
                    row_593 = (593 - 1) // 25  # строка 23
                    col_593 = (593 - 1) % 25   # колонка 17
                    
                    # Центр клетки 593
                    x_593_center = (col_593 + 0.5) * cell_width_mm * mm  # центр по X
                    y_593_center = (297 - (row_593 + 0.5) * cell_height_mm) * mm  # центр по Y (ReportLab от низа)
                    
                    # Смещаем на половину размера изображения для центрирования
                    x_593 = x_593_center - (sing1_scaled_width * mm / 2)
                    y_593 = y_593_center - (sing1_scaled_height * mm / 2)
                    
                    # Рисуем sing_1.png в центре 593-й клетки
                    overlay_canvas.drawImage("sing_1.png", x_593, y_593, 
                                           width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    overlay_canvas.save()
                    print("🔢 Добавлена сетка 25x35 для carta через ReportLab")
                    print("🖼️ Добавлено company.png в клетку 52 (как в contratto)")
                    print("🖼️ Добавлено logo.png в клетку 71 (как в contratto)")
                    print("🖼️ Добавлено carta_logo.png в центр 63-й клетки (увеличено на 20%)")
                    print("🖼️ Добавлено seal.png в центр 590-й клетки (уменьшено в 5 раз)")
                    print("🖼️ Добавлено sing_1.png в центр 593-й клетки (уменьшено в 5 раз)")
                
                elif template == 'contratto':
                    # Получаем размер изображения для масштабирования
                    from PIL import Image
                    img = Image.open("company.png")
                    img_width_mm = img.width * 0.264583  # пиксели в мм (96 DPI)
                    img_height_mm = img.height * 0.264583
                    
                    # Увеличиваем на 20% (было уменьшение в 2 раза, теперь увеличиваем)
                    scaled_width = (img_width_mm / 2) * 1.2  # +20% к уменьшенному размеру
                    scaled_height = (img_height_mm / 2) * 1.2
                    
                    # Размер ячейки для расчета сдвигов
                    cell_width_mm = 210/25  # 8.4mm
                    cell_height_mm = 297/35  # 8.49mm
                    
                    # Страница 1: изображение в квадрате 52 + сдвиг (влево на 0.5, вниз на 0.5)
                    # Квадрат 52 = строка 2, колонка 1 (нумерация с 1)
                    row_52 = (52 - 1) // 25 + 1  # строка 2 + 1 = строка 3
                    col_52 = (52 - 1) % 25 + 1   # колонка 1 + 1 = колонка 2
                    
                    # Левая грань квадрата + сдвиги (ReportLab считает от НИЗА страницы!)
                    x_52 = (col_52 * cell_width_mm - 0.5 * cell_width_mm) * mm  # влево на пол клетки
                    y_52 = (297 - (row_52 * cell_height_mm + cell_height_mm) - 0.5 * cell_height_mm) * mm  # вниз на пол клетки
                    
                    # Рисуем с увеличением на 20% и сохранением прозрачности
                    overlay_canvas.drawImage("company.png", x_52, y_52, 
                                           width=scaled_width*mm, height=scaled_height*mm, 
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем logo.png в квадрат 71 первой страницы с уменьшением на 20% и сдвигом влево на 2 клетки
                    # Квадрат 71 = строка 2, колонка 20 (71-1=70, 70//25=2, 70%25=20)
                    row_71 = (71 - 1) // 25  # строка 2
                    col_71 = (71 - 1) % 25   # колонка 20
                    
                    # Получаем размер logo.png для уменьшения на 20%
                    logo_img = Image.open("logo.png")
                    logo_width_mm = logo_img.width * 0.264583  # пиксели в мм (96 DPI)
                    logo_height_mm = logo_img.height * 0.264583
                    
                    # Уменьшаем в 9 раз (3 * 3)
                    logo_scaled_width = logo_width_mm / 9  # уменьшение в 9 раз
                    logo_scaled_height = logo_height_mm / 9
                    
                    # Левая грань квадрата 71 + сдвиг вправо на 4 клетки и вниз на 1.25 клетки
                    x_71 = (col_71 - 2 + 4) * cell_width_mm * mm  # было влево на 2, теперь вправо на 4
                    y_71 = (297 - (row_71 * cell_height_mm + cell_height_mm) - 1.25 * cell_height_mm) * mm  # вниз на 1.25 клетки
                    
                    # Рисуем logo.png с уменьшением на 20%
                    overlay_canvas.drawImage("logo.png", x_71, y_71, 
                                           width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем нумерацию страницы 1 между клетками 862 и 863 (аналогично второй странице)
                    # Используем те же координаты что и для второй страницы
                    row_862_p1 = (862 - 1) // 25  # строка 34
                    col_862_p1 = (862 - 1) % 25   # колонка 11
                    
                    # Позиция между клетками 862 и 863 (на границе) + сдвиг на полклетки вправо и на 1/4 клетки вниз
                    x_page_num_p1 = (col_862_p1 + 1 + 0.5) * cell_width_mm * mm  # граница между клетками + полклетки вправо
                    y_page_num_p1 = (297 - (row_862_p1 * cell_height_mm + cell_height_mm/2) - 0.25 * cell_height_mm) * mm  # середина строки + 1/4 клетки вниз
                    
                    # Рисуем цифру 1 размером 10pt
                    overlay_canvas.setFillColorRGB(0, 0, 0)  # Черный цвет
                    overlay_canvas.setFont("Helvetica", 10)
                    overlay_canvas.drawString(x_page_num_p1-2, y_page_num_p1-2, "1")
                    
                    overlay_canvas.showPage()
                    
                    # Страница 2: Добавляем logo.png точь в точь как на первой странице
                    # Сетка убрана - невидимая (0% прозрачности)
                    
                    # Добавляем logo.png на вторую страницу точь в точь как на первой
                    # Используем те же координаты и размеры что и на первой странице
                    overlay_canvas.drawImage("logo.png", x_71, y_71, 
                                           width=logo_scaled_width*mm, height=logo_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем sing_2.png в квадрат 637 второй страницы с уменьшением в 7 раз
                    # Квадрат 637 = строка 25, колонка 12 (637-1=636, 636//25=25, 636%25=11)
                    row_637 = (637 - 1) // 25  # строка 25
                    col_637 = (637 - 1) % 25   # колонка 11
                    
                    # Получаем размер sing_2.png для уменьшения в 7 раз
                    sing_img = Image.open("sing_2.png")
                    sing_width_mm = sing_img.width * 0.264583  # пиксели в мм (96 DPI)
                    sing_height_mm = sing_img.height * 0.264583
                    
                    # Уменьшаем в 7 раз и дополнительно на 10%
                    sing_scaled_width = (sing_width_mm / 7) * 0.9  # -10%
                    sing_scaled_height = (sing_height_mm / 7) * 0.9
                    
                    # Левая грань квадрата 637 + сдвиг влево на 1 клетку и вниз на 0.5 клетки
                    x_637 = (col_637 - 1) * cell_width_mm * mm  # влево на 1 клетку
                    y_637 = (297 - (row_637 * cell_height_mm + cell_height_mm) - 0.5 * cell_height_mm) * mm  # вниз на 0.5 клетки
                    
                    # Рисуем sing_2.png с уменьшением в 7 раз и сохранением прозрачности
                    overlay_canvas.drawImage("sing_2.png", x_637, y_637, 
                                           width=sing_scaled_width*mm, height=sing_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем sing_1.png в квадрат 628 второй страницы с уменьшением в 6 раз
                    # Квадрат 628 = строка 25, колонка 3 (628-1=627, 627//25=25, 627%25=2)
                    row_628 = (628 - 1) // 25  # строка 25
                    col_628 = (628 - 1) % 25   # колонка 2
                    
                    # Получаем размер sing_1.png для уменьшения в 6 раз
                    sing1_img = Image.open("sing_1.png")
                    sing1_width_mm = sing1_img.width * 0.264583  # пиксели в мм (96 DPI)
                    sing1_height_mm = sing1_img.height * 0.264583
                    
                    # Уменьшаем в 6 раз и увеличиваем на 10%
                    sing1_scaled_width = (sing1_width_mm / 6) * 1.1  # +10%
                    sing1_scaled_height = (sing1_height_mm / 6) * 1.1
                    
                    # Левая грань квадрата 628 + сдвиг на 2 клетки вниз
                    x_628 = col_628 * cell_width_mm * mm
                    y_628 = (297 - (row_628 * cell_height_mm + cell_height_mm) - 2 * cell_height_mm) * mm  # вниз на 2 клетки
                    
                    # Рисуем sing_1.png с уменьшением в 6 раз и сохранением прозрачности
                    overlay_canvas.drawImage("sing_1.png", x_628, y_628, 
                                           width=sing1_scaled_width*mm, height=sing1_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем seal.png в квадрат 682 второй страницы с уменьшением в 7 раз
                    # Квадрат 682 = строка 27, колонка 7 (682-1=681, 681//25=27, 681%25=6)
                    row_682 = (682 - 1) // 25  # строка 27
                    col_682 = (682 - 1) % 25   # колонка 6
                    
                    # Получаем размер seal.png для уменьшения в 7 раз
                    seal_img = Image.open("seal.png")
                    seal_width_mm = seal_img.width * 0.264583  # пиксели в мм (96 DPI)
                    seal_height_mm = seal_img.height * 0.264583
                    
                    # Уменьшаем в 7 раз
                    seal_scaled_width = seal_width_mm / 7
                    seal_scaled_height = seal_height_mm / 7
                    
                    # Левая грань квадрата 682
                    x_682 = col_682 * cell_width_mm * mm
                    y_682 = (297 - (row_682 * cell_height_mm + cell_height_mm)) * mm
                    
                    # Рисуем seal.png с уменьшением в 7 раз и сохранением прозрачности
                    overlay_canvas.drawImage("seal.png", x_682, y_682, 
                                           width=seal_scaled_width*mm, height=seal_scaled_height*mm,
                                           mask='auto', preserveAspectRatio=True)
                    
                    # Добавляем нумерацию страницы 2 между клетками 862 и 863
                    # Квадрат 862 = строка 34, колонка 12 (862-1=861, 861//25=34, 861%25=11)
                    # Квадрат 863 = строка 34, колонка 13 (863-1=862, 862//25=34, 862%25=12)
                    row_862 = (862 - 1) // 25  # строка 34
                    col_862 = (862 - 1) % 25   # колонка 11
                    col_863 = (863 - 1) % 25   # колонка 12
                    
                    # Позиция между клетками 862 и 863 (на границе) + сдвиг на полклетки вправо и на 1/4 клетки вниз
                    x_page_num = (col_862 + 1 + 0.5) * cell_width_mm * mm  # граница между клетками + полклетки вправо
                    y_page_num = (297 - (row_862 * cell_height_mm + cell_height_mm/2) - 0.25 * cell_height_mm) * mm  # середина строки + 1/4 клетки вниз
                    
                    # Рисуем цифру 2 размером 10pt
                    overlay_canvas.setFillColorRGB(0, 0, 0)  # Черный цвет
                    overlay_canvas.setFont("Helvetica", 10)
                    overlay_canvas.drawString(x_page_num-2, y_page_num-2, "2")
                    
                    overlay_canvas.save()
                
                # Объединяем PDF с overlay
                overlay_buffer.seek(0)
                base_pdf = PdfReader(BytesIO(pdf_bytes))
                overlay_pdf = PdfReader(overlay_buffer)
                
                writer = PdfWriter()
                
                # Накладываем изображения на каждую страницу
                for i, page in enumerate(base_pdf.pages):
                    if i < len(overlay_pdf.pages):
                        page.merge_page(overlay_pdf.pages[i])
                    writer.add_page(page)
                
                # Сохраняем финальный PDF
                final_buffer = BytesIO()
                writer.write(final_buffer)
                final_pdf_bytes = final_buffer.getvalue()
                
                output_pdf = f'test_{template}.pdf'
                with open(output_pdf, 'wb') as f:
                    f.write(final_pdf_bytes)
                    
                print(f"✅ PDF с изображениями создан! Размер: {len(final_pdf_bytes)} байт")
                print("🖼️ Изображения наложены через ReportLab")
                print(f"📄 Файл сохранен как {output_pdf}")
                
            except ImportError as e:
                print(f"❌ Нужны библиотеки: pip install reportlab PyPDF2")
                print(f"❌ Ошибка импорта: {e}")
                # Сохраняем обычный PDF без изображений
                output_pdf = f'test_{template}.pdf'
                with open(output_pdf, 'wb') as f:
                    f.write(pdf_bytes)
                print(f"✅ Обычный PDF создан! Размер: {len(pdf_bytes)} байт")
        else:
            # Для других шаблонов - простой PDF без изображений
            output_pdf = f'test_{template}_fixed.pdf'
            with open(output_pdf, 'wb') as f:
                f.write(pdf_bytes)
            print(f"✅ PDF создан! Размер: {len(pdf_bytes)} байт")
            print(f"📄 Файл сохранен как {output_pdf}")
        
    except ImportError:
        print("❌ Нужен WeasyPrint для тестирования")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def main():
    """Функция для тестирования PDF конструктора"""
    import sys
    
    # Определяем какой шаблон обрабатывать
    template = sys.argv[1] if len(sys.argv) > 1 else 'contratto'
    
    print(f"🧪 Тестируем PDF конструктор для {template} через API...")
    
    # Тестовые данные
    test_data = {
        'name': 'Mario Rossi',
        'amount': 15000.0,
        'tan': 7.86,
        'taeg': 8.30, 
        'duration': 36,
        'payment': monthly_payment(15000.0, 36, 7.86)
    }
    
    try:
        if template == 'contratto':
            buf = generate_contratto_pdf(test_data)
            filename = f'test_contratto.pdf'
        elif template == 'garanzia':
            buf = generate_garanzia_pdf(test_data['name'])
            filename = f'test_garanzia.pdf'
        elif template == 'carta':
            buf = generate_carta_pdf(test_data)
            filename = f'test_carta.pdf'
        elif template == 'compensazione':
            buf = generate_compensazione_pdf({
                'name': test_data['name'],
                'commission': 180.0,
                'indemnity': 250.0,
            })
            filename = 'test_compensazione.pdf'
        elif template == 'garanzia1of1':
            buf = generate_garanzia1of1_pdf({
                'name': 'Cristian Fasolato,',
                'commission': 890.0,
                'indemnity': 4200.0,
            })
            filename = 'test_garanzia1of1.pdf'
        elif template == 'approvazione':
            buf = generate_approvazione_pdf(test_data)
            filename = f'test_approvazione.pdf'
        else:
            print(f"❌ Неизвестный тип документа: {template}")
            return
        
        # Сохраняем тестовый PDF
        with open(filename, 'wb') as f:
            f.write(buf.read())
            
        print(f"✅ PDF создан через API! Файл сохранен как {filename}")
        print(f"📊 Данные: {test_data}")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")


if __name__ == '__main__':
    main()
