# Добавление PDF-документа в бот (паттерн на примере «Компенсационное письмо»)

Документ описывает **какие операции выполнялись** при добавлении документа `compensazione` и **как устроен итоговый код**. Следующие одностраничные письма в этом и других ботах можно делать **по той же схеме**: тот же каркас (`HTML` → `fix_html_layout` → WeasyPrint → ReportLab overlay), меняются **язык**, **текст** и **набор полей** / **порядок `XXX`**.

---

## 1. Где лежит проект

- Каталог бота: `TELEGRAM-BOTS/1capital-main/` (рядом с другими папками в `LIFE Cachy OS`, не обязательно внутри `Progects`).
- Ключевые файлы:
  - `telegram_document_bot.py` — диалог Telegram, команды, вызов генерации PDF.
  - `pdf_costructor.py` — HTML → PDF (WeasyPrint), подстановка данных, наложение `company.png` / `logo.png` / печать / подпись.
  - `compensazione.html` — шаблон письма (плейсхолдеры `XXX`).
  - Рядом: `carta.html`, `garanzia.html`, … как эталоны одностраничных писем.
  - Зависимости: `requirements.txt` (в т.ч. `weasyprint`, `reportlab`, `PyPDF2`, Pillow).

---

## 2. Хронология операций (что делалось по шагам)

1. **Найти папку бота** в `TELEGRAM-BOTS/1capital-main`.
2. **Добавить HTML** `compensazione.html` по образцу одностраничного `carta.html`: таблица, `body` с классом `c9 doc-content`, в тексте — последовательные **`XXX`** (по одному на каждое подставляемое значение).
3. **`pdf_costructor.py`**
   - Функция **`generate_compensazione_pdf(data)`** → `fix_html_layout('compensazione')` → **`_generate_pdf_with_images(html, 'compensazione', data)`**.
   - В **`_generate_pdf_with_images`**: ветка **`elif template_name == 'compensazione'`** с **`replacements`**: цепочка `('XXX', значение)` с **`replace(..., 1)`** — порядок **строго как в HTML**.
   - Шаблон **`compensazione`** добавлен в общий список шаблонов, где выполняется замена `XXX`.
   - **`_add_images_to_pdf`**: для **`carta` и `compensazione` один и тот же блок** (логотипы и печать/подпись в тех же «клетках», что у карты).
   - **`fix_html_layout`**:
     - Общие стили для **`('carta', 'compensazione')`** — одна страница, рамка `@page`, компактная вёрстка как у `carta`.
     - **Дополнительно только для `compensazione`**: после общего блока **`css_fixes += ...`** — отступ сверху под логотипы, Courier, отступы абзацев, классы `comp-bullet`, `comp-quote`, и т.д.
     - Очистка HTML от встроенных картинок — **общая ветка** `('carta', 'compensazione')`.
     - Сетка 25×35 для позиционирования overlay — **`compensazione` в том же списке, что `carta`**.
   - В **`main()`** / тестах — ветка для аргумента **`compensazione`** и файл **`test_compensazione.pdf`**.
4. **`telegram_document_bot.py`**
   - Импорт **`generate_compensazione_pdf`**, обёртка **`build_compensazione(data)`**.
   - Новые состояния: **`ASK_COMP_COMMISSION`**, **`ASK_COMP_INDEMNITY`** (расширен `range(8)`).
   - В **`choose_doc` / `ask_name`**: при выборе **`/компенсация`** или **`/compensazione`** — после имени запрашиваются **комиссия** и **компенсация**, без суммы кредита/TAN как у карты.
   - Хендлеры **`ask_comp_commission`**, **`ask_comp_indemnity`** → **`build_compensazione`** → отправка **`Compensazione_<имя>.pdf`**.
   - Клавиатура и **`Regex`** для новых команд.
5. **Окружение**: на Arch/Cachy системный **`pip` заблокирован (PEP 668)** — зависимости в **`.venv`**; при подмене `python` в PATH на Cursor удобно запускать **`./.venv/bin/python`** или **`env -i PATH="$PWD/.venv/bin:/usr/bin:/bin"`**.
6. **Итерации по макету** (по желанию): отступ сверху, шрифт, жирность заголовков статей, маркеры `•`, без жёлтого фона — всё это **только в `compensazione.html` и в блоке `css_fixes +=` для `compensazione`**.

---

## 3. Итоговая логика данных (compensazione)

| Источник | Поле в `data` | Как попадает в PDF |
|----------|----------------|---------------------|
| Авто | — | **`format_date()`** → первая замена `XXX` (дата в итальянском формате). |
| Бот | имя | **`name`**, к отображению добавляется **`,`** в конце, если пользователь не ввёл. |
| Бот | сумма комиссии | **`commission`** → **`format_money(...)`**. |
| Бот | сумма компенсации | **`indemnity`** → **`format_money(...)`**. |

В коде замены (фрагмент логики):

```python
elif template_name == 'compensazione':
    nm = data['name'].strip()
    name_display = nm if nm.endswith(',') else nm + ','
    replacements = [
        ('XXX', format_date()),
        ('XXX', name_display),
        ('XXX', format_money(data['commission'])),
        ('XXX', format_money(data['indemnity'])),
    ]
```

В HTML должно быть **ровно четыре** вхождения `XXX` **в этом порядке**: дата, Gentile, сумма комиссии, сумма компенсации.

---

## 4. Структура кода: что куда смотреть

### 4.1. `compensazione.html`

- Один файл, разметка как у «карты»: таблица, ячейка с текстом.
- Плейсхолдеры **`XXX`** — только такие строки подставляет **`pdf_costructor`** (последовательная замена).
- Семантика классов (для стилей из `fix_html_layout`): например **`comp-bullet`** (пункты со `•`), **`comp-quote`** (цитата), **`comp-line-data`**, **`comp-line-gentile`**, **`comp-saluti`**; жирное — **`span.c4`**, обычный текст — **`span.c5`**.

### 4.2. `pdf_costructor.py` (точки расширения)

| Место | Назначение |
|-------|------------|
| `generate_compensazione_pdf` | Точка входа API: загрузка шаблона по имени файла **`compensazione.html`**. |
| `_generate_pdf_with_images` → `compensazione` | Подстановка **`XXX`**, затем WeasyPrint. |
| `_add_images_to_pdf` → `('carta', 'compensazione')` | Один сценарий наложения картинок. |
| `fix_html_layout` → ветка `carta` + `compensazione` | Общая база стилей; **`if template_name == 'compensazione': css_fixes += ...`** — только для этого документа. |

### 4.3. `telegram_document_bot.py`

| Место | Назначение |
|-------|------------|
| Состояния `ASK_COMP_*` | Отдельная ветка сценария после выбора документа. |
| `ask_name` | Ветка **`/компенсация` / `/compensazione`** → сохранить имя → спросить комиссию. |
| `ask_comp_commission` / `ask_comp_indemnity` | Парсинг сумм, вызов **`build_compensazione`**, отправка PDF. |

### 4.4. Имена: технический slug в коде vs имя PDF в Telegram

В одном проекте используются **два уровня имён** — их нельзя смешивать в документации.

| Уровень | Компенсационное письмо (GARANZIA) | Кредитный договор (пример) |
|--------|-----------------------------------|----------------------------|
| **Файл шаблона в репозитории** | **`compensazione.html`** — латиница, как **`generate_compensazione_pdf`**. | **`contratto.html`**, **`generate_contratto_pdf`**. |
| **Имя PDF в диалоге бота (`1capital-main`)** | **`Compensazione_<safe>.pdf`** — итальянское имя типа (**`Compensazione`**), подчёркивание, затем имя клиента. **`safe`** = имя из диалога: **`/`** и **`\`** заменяются на **`_`**, обрезка **80** символов. | **`Contratto_<имя>.pdf`** — тот же стиль: тип документа по-итальянски + **`_`** + имя. |
| **Локальный тест после сборки** | **`test_compensazione.pdf`** — префикс **`test_`** + **slug** шаблона (**`main()`** в `pdf_costructor.py`). | **`test_contratto.pdf`** и т.д. |

**Стандарт для этого бота:** в Telegram имя вложения = **`ИтальянскоеИмяТипа_<имя_клиента>.pdf`** (как **`Compensazione_`**, **`Contratto_`**, **`Carta_`**, **`Approvazione_`**, **`Garanzia_`** в коде). Смысл «компенсационное письмо» — в тексте команды и интерфейса (**`/компенсация`**, описание в комментариях), а **не** в имени файла: файл остаётся **`Compensazione_*`**.

**Правило для новых документов:** в репозитории — **латинский slug** (`<slug>.html`, `generate_<slug>_pdf`, `test_<slug>.pdf`). В **`reply_document`** — **одно слово типа** на итальянском (как у соседних документов) + **`_`** + безопасное имя: **`Tipo_<safe>.pdf`**.

Проверка в коде: **`ask_comp_indemnity`** → **`InputFile(..., f"Compensazione_{safe}.pdf")`**; контракт — **`Contratto_{d['name']}.pdf`**.

### 4.5. Боты `RFM-main` и `TC_Finanzholding-main` (проверка соответствия §4.4 и §5)

Оба бота — **не** копия `1capital-main`: префиксы в Telegram — **одно слово типа на языке текста PDF** + **`_`** + **`safe`** (как **`Compensazione_<safe>.pdf`** в §4.4, но не итальянское слово «вслепую»). Для немецких писем: **`Vertrag_`**, **`Bankkarte_`**, **`Genehmigung_`**, **`Verpflichtung_`** и т.п. В **`RFM-main`** два «гарантийных» письма с разными префиксами, чтобы не дублировать одно и то же имя: итальянское — **`Garanzia_<safe>.pdf`** (шаблон **`garanzia.html`**), немецкое RFM — **`Buergschaft_<safe>.pdf`** (латиница без умлаута; шаблон **`buergschaft_rfm.html`**). **Нельзя** вшивать в имя файла бренд/суффиксы вроде **`Garantie_RFM_`** — это ломает правило «язык префикса = язык документа».

| Требование | `TC_Finanzholding-main` | `RFM-main` |
|------------|---------------------------|------------|
| Схема **`Тип_<safe>.pdf`** | Да | Да |
| Санитизация **`safe`**: **`/`** и **`\`** → **`_`**, **≤ 80** символов | **`_safe_filename_part`** | То же; **`/garanzia`** → **`Garanzia_<safe>.pdf`**; для **`buergschaft_rfm`** поле **Von** → **`Buergschaft_<safe>.pdf`** (текст шаблона **DE**) |
| Генерация через **`generate_*_pdf`** | Да (`pdf_costructor.py`) | Да |

**Пример:** `RFM-main` / **`buergschaft_rfm.html`** — тело письма по **немецки** → имя вложения **`Buergschaft_<safe>.pdf`**, а не **`Compensazione_`** (итальянский) и не **`Garantie_RFM_`**.

---

## 5. Как повторять для «следующих документов»

Структура **та же**, меняется содержимое:

1. **Новый файл** `<slug>.html` — тот же тип вёрстки, что `compensazione` / `carta`, свой текст и язык, свой **порядок `XXX`**.
2. **`generate_<slug>_pdf`** и ветки в **`_generate_pdf_with_images`**, **`fix_html_layout`**, при необходимости **`_add_images_to_pdf`** (часто копия **`carta`** или **`compensazione`**).
3. **Бот**: либо те же поля и шаги, либо новые состояния и вопросы — по списку полей для `XXX`; в **`reply_document`** — **`Тип_<safe>.pdf`** по **§4.4**. **Обязательно:** слово **`Тип`** — на **том же языке, что основной текст PDF** (итальянский: **`Compensazione_`**, **`Contratto_`**, **`Garanzia_`** …; немецкий: **`Verpflichtung_`**, **`Buergschaft_`** …). Не добавлять в префикс аббревиатуры бренда (**`…_RFM_`**) и не смешивать языки.
4. Проверка: **`./.venv/bin/python -c "from pdf_costructor import generate_<slug>_pdf; ..."`** и файл **`test_<slug>.pdf`**.

Если документ **логически совпадает** с compensazione (одна страница, те же картинки, тот же тип полей), достаточно **скопировать ветки `compensazione`**, переименовать шаблон и подправить **`replacements`** и диалог. Если меняется только **язык и формулировки** — чаще всего правится **только HTML** и при необходимости порядок **`XXX`** в Python.

---

## 6. Зависимости и сборка PDF локально

```bash
cd TELEGRAM-BOTS/1capital-main
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Пример проверки (после активации venv или с полным путём к `python`):

```python
from pdf_costructor import generate_compensazione_pdf
buf = generate_compensazione_pdf({
    "name": "Mario Rossi",
    "commission": 220.0,
    "indemnity": 150.5,
})
open("test_compensazione.pdf", "wb").write(buf.read())
```

Системные библиотеки для WeasyPrint на Linux (при ошибках Pango/Cairo): см. дистрибутив; в Docker используется логика из `install_deps.sh` (пакеты под Debian/Ubuntu).

### 6.1. Перегенерация тестового PDF при каждой правке (обязательно для ассистента)

После **любых** изменений в `*.html`, `fix_html_layout`, `replacements`, overlay или боте, связанных с PDF, нужно **в том же запросе** пересобрать соответствующий **`test_<slug>.pdf`**, открыть в просмотрщике и убедиться, что макет и подстановки верны. Не закрывать задачу только на «правках в коде» без актуального артефакта.

**Как (пример для `TC_Finanzholding-main` и шаблона `verpflichtung`):**

```bash
cd TELEGRAM-BOTS/TC_Finanzholding-main
# venv лучше создавать системным Python, без подмены Cursor в PATH:
env -i PATH=/usr/bin:/bin HOME="$HOME" /usr/bin/python3.11 -m venv .venv
env -i PATH="$PWD/.venv/bin:/usr/bin:/bin" HOME="$HOME" python -m pip install -r requirements.txt
env -i PATH="$PWD/.venv/bin:/usr/bin:/bin" HOME="$HOME" python pdf_costructor.py verpflichtung
# → test_verpflichtung.pdf в каталоге бота
```

Для **`1capital-main`** замените каталог и аргумент `main()` (например `python pdf_costructor.py compensazione` или тот сценарий, который добавлен в `if __name__ == '__main__'`).

Если в терминале в Cursor **`python` указывает на AppImage** и `venv` получается с битым интерпретатором, используйте **`env -i PATH=/usr/bin:/bin …`** при создании venv и при запуске команд (как выше), либо явный **`/usr/bin/python3.11`**.

### 6.2. Эталонная генерация PDF (для ассистента и для ручного запуска)

**Почему не только `python pdf_costructor.py <шаблон>`:** в `1capital-main/pdf_costructor.py` исторически может быть **два блока `if __name__ == '__main__'`** — при запуске файла отрабатывают оба, лог дублируется, итоговый файл всё равно перезаписывается `main()`, но надёжнее вызывать **`generate_<slug>_pdf` из кода** (как в `main()`), без лишнего первого блока.

**Оболочка для любой команды ниже** (выполнять **из каталога бота**, подставив свой путь к проекту при необходимости):

```bash
cd TELEGRAM-BOTS/1capital-main   # или TC_Finanzholding-main
export BOTDIR="$PWD"
env -i PATH="$BOTDIR/.venv/bin:/usr/bin:/bin" HOME="$HOME" SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt python3.11 …
```

Если нет **`python3.11`**, используйте ту версию Python, с которой создан `.venv` (см. `.venv/pyvenv.cfg` → `version`).

#### Один новый документ (минимальный эталон)

После добавления **`generate_<slug>_pdf`** и тестовых данных в `main()` замените `<slug>`, словарь `data` и имя файла:

```bash
cd TELEGRAM-BOTS/1capital-main
env -i PATH="$PWD/.venv/bin:/usr/bin:/bin" HOME="$HOME" SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
  python3.11 -c "
import os
os.chdir('$PWD')
from pdf_costructor import generate_<slug>_pdf
buf = generate_<slug>_pdf({'name': '...', 'commission': 0.0, 'indemnity': 0.0})
open('test_<slug>.pdf', 'wb').write(buf.read())
print('test_<slug>.pdf OK')
"
```

Подставьте реальный `<slug>`, импорт и поля словаря — как в **`generate_<slug>_pdf`** и в боте.

#### Полная пересборка **всех** тестовых PDF бота (обязательно в конце правок по общему коду)

После изменений в **`fix_html_layout`**, общих стилях ветки `carta`, **`_add_images_to_pdf`**, универсальном анализаторе HTML или других местах, которые затрагивают **несколько шаблонов**, нужно пересобрать **все** существующие `test_*.pdf` этого репозитория и просмотреть выборочно или все — иначе регрессия по «чужому» документу останется незамеченной.

**`1capital-main`** — эталонный скрипт (те же вызовы, что и при пакетной проверке; данные согласованы с `main()`):

```bash
cd TELEGRAM-BOTS/1capital-main
env -i PATH="$PWD/.venv/bin:/usr/bin:/bin" HOME="$HOME" SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt python3.11 <<'PY'
# Рабочий каталог — каталог бота (команда cd выше)
from pdf_costructor import (
    generate_contratto_pdf,
    generate_garanzia_pdf,
    generate_carta_pdf,
    generate_compensazione_pdf,
    generate_approvazione_pdf,
    monthly_payment,
)
td = {
    "name": "Mario Rossi",
    "amount": 15000.0,
    "tan": 7.86,
    "taeg": 8.30,
    "duration": 36,
    "payment": monthly_payment(15000.0, 36, 7.86),
}
def save(name, buf):
    with open(name, "wb") as f:
        f.write(buf.read())
save("test_contratto.pdf", generate_contratto_pdf(td))
save("test_garanzia.pdf", generate_garanzia_pdf(td["name"]))
save("test_carta.pdf", generate_carta_pdf(td))
save("test_compensazione.pdf", generate_compensazione_pdf({
    "name": td["name"],
    "commission": 180.0,
    "indemnity": 250.0,
}))
save("test_approvazione.pdf", generate_approvazione_pdf(td))
print("1capital-main: все test_*.pdf пересобраны")
PY
```

**`TC_Finanzholding-main`** — полный набор шаблонов этого бота (`verpflichtung`: комиссия/инденнита как в `main()`):

```bash
cd TELEGRAM-BOTS/TC_Finanzholding-main
env -i PATH="$PWD/.venv/bin:/usr/bin:/bin" HOME="$HOME" SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt python3.11 <<'PY'
# Рабочий каталог — каталог бота (команда cd выше)
from pdf_costructor import (
    generate_contratto_pdf,
    generate_garanzia_pdf,
    generate_carta_pdf,
    generate_approvazione_pdf,
    generate_verpflichtung_pdf,
    monthly_payment,
)
base = {"name": "Mario Rossi", "amount": 15000.0, "taeg": 8.10, "duration": 36}
td = {**base, "tan": 7.24, "payment": monthly_payment(15000.0, 36, 7.24)}
td_app = {**base, "tan": 7.15, "payment": monthly_payment(15000.0, 36, 7.15)}
def save(name, buf):
    with open(name, "wb") as f:
        f.write(buf.read())
save("test_contratto.pdf", generate_contratto_pdf(td))
save("test_garanzia.pdf", generate_garanzia_pdf(td["name"]))
save("test_carta.pdf", generate_carta_pdf(td))
save("test_approvazione.pdf", generate_approvazione_pdf(td_app))
save("test_verpflichtung.pdf", generate_verpflichtung_pdf({
    "name": base["name"],
    "commission": 310.0,
    "indemnity": 150.0,
}))
print("TC_Finanzholding-main: все test_*.pdf пересобраны")
PY
```

**Правило для ассистента:** после добавления нового `<slug>` — в такие скрипты нужно **добавить ещё один вызов** `generate_<slug>_pdf` и строку `save("test_<slug>.pdf", …)`, чтобы следующая «полная проверка» снова покрывала весь набор.

---

## 7. Типичные неточности: шрифт, отступ под логотипы, «мусор» на странице

Чтобы следующие документы и итерации по макету шли быстрее, полезно понимать **откуда берётся вид PDF**, а не только HTML.

### 7.1. Почему шрифт «не как в Word» или «странный»

1. **Цепочка рендера:** `HTML` → **WeasyPrint** (Pango/Cairo) → PDF, затем **ReportLab** накладывает логотипы, печать и подпись **поверх** первой страницы. Это не тот же движок, что Word/Google Docs.
2. **Общий CSS в `fix_html_layout`:** для одностраничных шаблонов в духе `carta` в `TC_Finanzholding-main` на `body` часто задаётся **`"Roboto Mono", monospace`** — моноширинный шрифт, похож на код/технический текст и **не похож на банковский пропорциональный** (Arial, Helvetica и т.п.). Если в HTML шаблоне тоже прописан Roboto Mono, визуал усиливается.
3. **Подстановка шрифтов:** если запрошенный шрифт не найден или глифы подставляются из другого файла, возможны **обрезанные нижние выносные** (у `g`, `y`, `q`) и «ломаная» окантовка букв — это не «битый» текст, а сочетание шрифта, `overflow: hidden` в компактных стилях и рендера Pango.
4. **Что делать в новом документе:** явно задать в HTML и/или в **`css_fixes +=`** для шаблона стек вроде `Arial, Helvetica, "Liberation Sans", sans-serif` с `!important`, если нужен «офисный» вид; при необходимости — отдельный класс на `<body>` (как `tpl-verpflichtung`), чтобы не ломать соседние шаблоны с тем же `c6`.

### 7.2. Отступ текста ниже логотипов

Логотипы **не в HTML**, а в **overlay** — отступ сверху у текста задаётся **`padding-top` на `body`** (или на обёртке) в `css_fixes +=` для конкретного шаблона, в единицах **`em`** подбирается под высоту картинок. Если «мало воздуха» — увеличить `padding-top` (например с `6em` до `8em`), пересобрать тестовый PDF и сравнить с макетом.

### 7.3. Сетка 25×35 и редкие артефакты

Для позиционирования overlay в HTML вставляется **невидимая сетка** с номерами ячеек. Обычно цифры не видны (`opacity: 0`, `display: none` на ячейках). В отдельных версиях WeasyPrint/шрифта возможны **случайные пиксели текста** — для шаблона можно **полностью скрыть** `.grid-overlay` в CSS (координаты для ReportLab в коде не от этого блока).

### 7.4. Согласование с эталоном

- Сверять **порядок и количество `XXX`** в HTML с массивом `replacements` в Python — иначе подставятся не те поля.
- После правок **всегда** открывать итоговый PDF: превью в редакторе и печать в PDF — разные вещи.

### 7.5. `compensazione` (GARANZIA) и общая ветка `carta`

Шаблон **`compensazione`** идёт через ту же ветку **`fix_html_layout`**, что и **`carta`**: на `body` навешивается **`Roboto Mono`**, плюс глобально **`* { overflow: hidden !important }`**, что может «резать» выносные букв и маскировать жирность. В **`compensazione.html`** в классах `.c4`/`.c5` раньше тоже был Roboto — визуал не совпадал с эталоном (**заголовок GARANZIA — Arial жирный, основной текст — Courier / Courier New**). Исправление: в HTML — **Courier** для текста, класс **`.comp-title`** для «GARANZIA»; в **`css_fixes +=` только для `compensazione`** — переопределение шрифтов с `!important`, **`overflow: visible`** для ячейки, **висячий отступ** у `p.comp-bullet` (`padding-left` + отрицательный `text-indent`), отступ цитаты у `p.comp-quote`.

**`TC_Finanzholding-main` / `verpflichtung`:** чтобы типографика совпадала с **`compensazione.html`**, разметка приведена к тем же классам (**`body.c9.doc-content`**, **`c1`**, **`c4`/`c5`**, **`comp-line-data`**, **`comp-line-gentile`**, **`comp-bullet`**, **`comp-saluti`**), в **`pdf_costructor.py`** для `verpflichtung` используется тот же набор правил, что и у `compensazione` в `1capital-main` (Courier New, жирное через `.c4`, отступ под логотипы, висячий отступ у пунктов).

---

## 8. Ошибки, которые уже случались — зафиксировать эталон и не повторять

Ниже — то, что **уже ломало макет** или вызывало итерации «шрифт не тот / нет жирного / нет отступов». Перед новым документом или переносом шаблона в другой бот — **пройти чеклист**.

### 8.1. Сначала зафиксировать, *какой* эталон

- **Эталон `compensazione.html` (GARANZIA):** основной текст — **Courier New** (`span.c5` / обычный, `span.c4` / жирный), заголовок «GARANZIA» — **Arial** (класс **`comp-title`**). Это **не** «всё Arial как в Word» и **не** Roboto Mono из ветки `carta`.
- Путаница возникала, когда для немецкого письма подставляли **Arial целиком** или **Roboto Mono** из общего CSS, а затем просили **«как в compensazione»** — это **другая** типографика. Правило: если пользователь ссылается на **`compensazione.html`**, копируются **и HTML-классы (`c9`, `c1`, `c4`/`c5`, `comp-*`)**, и **блок `css_fixes +=`** в том же духе, что в `1capital-main` для `compensazione`, с переопределением шрифтов через **`!important`** и **`overflow: visible`** у ячейки с текстом.

### 8.2. Наследование ветки `carta` в `fix_html_layout`

- Для пар **`(carta, compensazione)`** или **`(carta, approvazione, verpflichtung)`** в `TC_Finanzholding-main` в базе задаётся **`body { font-family: "Roboto Mono" … }`** и **` * { overflow: hidden !important }`**. Без отдельного **`css_fixes +=` для конкретного `template_name`** шрифт останется «чужим», выносные букв могут визуально «ломаться», жирность — теряться.
- **Ошибка:** править только `*.html` и ждать, что в PDF будет как в эталоне. **Нужно:** дублировать в Python те же переопределения, что и у эталонного шаблона (или вынести общий фрагмент CSS, но не полагаться на дефолт ветки `carta`).

### 8.3. Жирность и маркированный список

- **Ошибка:** весь абзац одним `span` или только классы без разделения — в PDF неотличимо от обычного текста или жирное «ломается» каскадом.
- **Нужно:** как в **`compensazione`**: подписи к полям и юридические ссылки в списке — **`span.c4`**, остальной текст строки — **`span.c5`**; пункт — абзац с классом **`comp-bullet`**, внутри **`•`** отдельным `span`, затем ссылка **`c4`**, затем продолжение **`c5`**.
- В **`css_fixes +=`** для шаблона явно: **`span.c4 { font-weight: 700 !important; }`**, **`span.c5 { font-weight: 400 !important; }`**, для **`p.comp-bullet`** — **висячий отступ** (`padding-left` + отрицательный **`text-indent`**, как у `compensazione`).

### 8.4. Отступ текста ниже логотипов (overlay)

- Логотипы — **ReportLab поверх PDF**, не из HTML. «Мало воздуха» сверху исправляется только **`padding-top` на `body`** (часто **`6em`–`8em`**) в **`css_fixes +=`** для этого шаблона, затем пересборка **`test_<slug>.pdf`**.

### 8.5. Другой бот / копирование шаблона

- **Ошибка:** скопировать только **`verpflichtung.html`** в `TC_Finanzholding-main`, не обновив **`fix_html_layout`**, **`_add_images_to_pdf`**, вставку сетки под **`body`**, **`replacements`** и бота.
- Нужны **все** точки из разделов **2–4** для этого репозитория; класс **`body`** должен совпадать с тем, что ожидают **`replace`** для сетки (например **`c9 doc-content tpl-verpflichtung`** — отдельная ветка вставки `grid_overlay`, чтобы не перепутать с обычной `carta`).

### 8.6. Сетка 25×35

- Редко на PDF проявлялись **артефакты** от номеров ячеек. Для проблемного шаблона **`display: none` на `.grid-overlay`** в CSS шаблона (координаты overlay в ReportLab от HTML-сетки не зависят).

### 8.7. Подстановка `XXX`

- Несовпадение **порядка** `XXX` в HTML и **`replacements` в Python** давало другие даты, имена и суммы в готовом файле — визуально «документ не тот». После правок — сверка **количества** и **порядка** плейсхолдеров.

### 8.8. Окружение и проверка

- **PEP 668**, **venv**; в Cursor **`python` может указывать на AppImage** — venv с «битым» интерпретатором; использовать **`env -i PATH=/usr/bin:/bin`** и **`/usr/bin/python3.11 -m venv`** (см. §6.1).
- После изменений по PDF — **обязательно пересобрать `test_<slug>.pdf` в том же запросе** (§6.1), иначе повторяются ошибки, которые уже исправлены в коде, но не проверены в артефакте.

### 8.9. Технический долг в `1capital-main/pdf_costructor.py`

- В файле могут оказаться **два блока `if __name__ == '__main__'`** — при запуске скрипта **дважды** отрабатывает логика теста/сборки. Имеет смысл оставить **один** вход в `main()`.

---

*Документ отражает результат работ по добавлению `compensazione` в `1capital-main` и служит шаблоном для аналогичных документов в этом и других ботах.*
