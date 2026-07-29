# russian-stress-benchmark

[English README](https://github.com/omogr/russian-stress-benchmark/blob/main/README_eng.md)

Набор скриптов для сравнения библиотек расстановки ударений с эталонной ручной разметкой.

## Что делает

Репозиторий содержит пайплайн для автоматического тестирования и сравнения различных библиотек, которые расставляют ударения в текстах на русском языке. Результаты работы каждой библиотеки сравниваются с размеченным вручную образцом (gold standard) и формируется детальный отчёт.

Каждая тестируемая библиотека должна уметь получать на вход текстовую строку с текстом и возвращать строку с этим же текстом, в который добавлены знаки ударения. Чаще всего для указания ударения используется знак `+` перед ударной гласной. В некоторых случаях допускается использование знаков ударения U+0301 и U+0300 после ударной гласной.

Тестирование заключается в том, что результаты работы каждой из библиотек сравниваются с размеченным вручную образцом и измеряются:
- число ошибок расстановки ударений
- время работы
- время загрузки данных в оперативную память
- число исключительных ситуаций в библиотеках (если такие были)
- отличия возвращаемого текста от исходного

## Сравниваемые библиотеки

| Библиотека | Описание |
|------------|----------|
| `silero_stress` | [silero-stress](https://github.com/snakers4/silero-stress) |
| `udarenie` | Модель и словари из [omogre](https://github.com/omogr/omogre) + морфологический анализатор Natasha NewsMorphTagger + ударения из Wiktionary. Возвращает не только текст с ударениями, но и дополнительную информацию (пословную разметку). |
| `accent_engine` | Библиотека udarenie с выключенной морфологией. Работает быстрее, но ошибок немного больше. Возвращает не только текст с ударениями, но и дополнительную информацию (пословную разметку). |

## Важные ограничения

- Предполагается, что библиотека расстановки ударений не должна менять исходный текст, а только должна добавлять знаки ударений. Если в результате разметки ударений в результирующем тексте появились или исчезли какие-то слова, то никаких сложных алгоритмов выравнивания слов в предложениях не используется, учитываются только неизменившиеся слова от начала и от конца предложения. Остальные слова считаются несопоставившимися.

- В результатах тестирования, среди прочего, считаются и ошибки на тех словах, которые были размечены всеми библиотеками. Это позволяет сравнивать точность библиотеки без учета тех искажений, которые они вносят в исходный текст.

- **Реальный эталонный образец** (`gold/pattern.txt`) в репозитории не выложен — вместо него присутствует заглушка. Для тестирования используйте собственный размеченный текст.

- **ruaccent** имеет много исключительных ситуаций; после их исправления тестирование потребуется повторить.

- Есть словарь слов, для которых допустимы несколько вариантов ударений — такие слова не учитываются.
- Слова с дефисами **не тестируются** (для простоты).
- Код является результатом вайб-кодинга, сырой и мало тестировался. Результаты следует считать предварительными.
- На быстродействие (время загрузки и обработки) влияют конфигурация компьютера и кэширование. Результаты измерения быстродействия могут быть разными на разных компьютерах или, например, при нескольких последовательных запусках одной и той же библиотеки на одном компьютере. Производительность измерялась на ноутбуке (процессор Intel i7-12650H 2.30 GHz, память DDR4, видеокарта NVIDIA GeForce RTX 4060 Laptop GPU).

## Требования

- Python 3.x
- Зависимости из `requirements.txt`

## Быстрый старт

### Способ 1: Через `benchmark.py` (рекомендуется)

```bash
# 1. Инициализация конфигурации
python benchmark.py init

# 2. Запуск полного бенчмарка
python benchmark.py run --gold gold/pattern.txt
```

### Способ 2: По шагам (через отдельные скрипты)

1. **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/omogr/russian-stress-benchmark.git
   cd russian-stress-benchmark
   ```

2. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
   В requirements.txt указаны те версии пакетов, с которыми проводилось тестирование. Но, по сути, тестирующие скрипты не делают ничего сложного, только запускают библиотеки и считают ошибки. Так что, скорей всего, они будут работать и с другими версиями пакетов.

3. **Подготовьте эталонный образец:**
   - Замените заглушку `gold/pattern.txt` на свой файл с размеченными ударениями.
   - Формат: знак `+` перед ударной гласной. Для удобства анализа результатов желательно разбивать текст на предложения или небольшие абзацы, **по одному предложению или абзацу на строку**.
   - Пример:
     ```
     В л+есу род+илась ёлочка.
     ```

4. **Запустите пошаговое тестирование:**
   ```bash
   # Разбиение текста на предложения
   python split_text_by_lines.py gold/pattern.txt -o output/pattern.json

   # Извлечение эталонной разметки (GOLD)
   python extract_accentuation.py output/pattern.json -o output/lib/GOLD_results.json --mode gold

   # Запуск тестируемых библиотек (пример для silero_stress)
   python run_accentuator.py silero_stress output/lib/GOLD_results.json -o output/raw/

   # Извлечение пословной разметки из результатов библиотеки
   python extract_accentuation.py output/raw/silero_stress_results.json -o output/lib/silero_stress_results.json --mode lib --lib-name silero_stress

   # Сравнение результатов всех библиотек
   python compare_accentuators.py output/lib/ -o output/comparison.json

   # Генерация отчётов
   python generate_report.py output/comparison.json output/report.md
   python generate_report_en.py output/comparison.json output/report_en.md
   ```

## Управление через `benchmark.py`

`benchmark.py` — единый оркестратор, который управляет полным пайплайном тестирования: `split → extract_gold → [run_lib] × N → compare → report`. Поддерживает кэширование результатов и инкрементальный запуск.

### Команды

| Команда | Описание |
|---------|----------|
| `init` | Создать `benchmark_config.json` с настройками по умолчанию |
| `run` | Запустить полный бенчмарк |
| `status` | Показать статус кэша — что посчитано, что нужно пересчитать |
| `clean` | Очистить кэш |

### Примеры использования

```bash
# Полный прогон всех библиотек
python benchmark.py run --gold gold/pattern.txt --config benchmark_config.json

# Перезапуск конкретной библиотеки (остальные из кэша)
python benchmark.py run --gold gold/pattern.txt --libs silero_stress --force

# Показать статус
python benchmark.py status --gold gold/pattern.txt --config benchmark_config.json

# Очистить кэш конкретной библиотеки
python benchmark.py clean --lib silero_stress

# Очистить весь кэш
python benchmark.py clean --all
```

### Конфигурация (`benchmark_config.json`)

```json
{
  "libraries": [
    {
      "name": "silero_stress",
      "accentuator_args": ["silero_stress"],
      "extra_args": {},
      "returns_document": false,
      "description": "Silero stress placement"
    },
    {
      "name": "udarenie",
      "accentuator_args": ["udarenie"],
      "extra_args": {"--data-path": "data_plus"},
      "returns_document": true,
      "description": "Udarenie with morphology"
    }
  ],
  "output_dir": "output",
  "cache_dir": ".benchmark_cache",
  "dubious_file": "dubious/dubious.txt",
  "reports": "both"
}
```

| Поле | Описание |
|------|----------|
| `name` | Имя библиотеки (должно совпадать с именем в `run_accentuator.py`) |
| `accentuator_args` | Аргументы для `run_accentuator.py` |
| `extra_args` | Дополнительные флаги (например, `--data-path`) |
| `returns_document` | `true` — библиотека возвращает DocumentResult с пословной разметкой. Для таких библиотек (например, `udarenie` и `accent_engine`) шаг `extract_accentuation.py` можно пропустить, так как пословное соответствие с исходным текстом можно получить из дополнительной информации. |
| `description` | Описание для отчётов |
| `output_dir` | Директория для результатов |
| `cache_dir` | Директория для кэша состояний |
| `dubious_file` | Путь к словарю сомнительных слов (слов с варьирующимся ударением) |
| `reports` | `"ru"`, `"en"` или `"both"` — какие отчёты генерировать |

## Описание скриптов

### `benchmark.py`
Единый оркестратор для сравнения библиотек расстановки ударений. Заменяет `run.sh` / `run.bat`. Управляет полным пайплайном: `split → extract_gold → [run_lib] × N → compare → report`. Поддерживает кэширование результатов, инкрементальный запуск, проверку статуса и очистку кэша.

### `split_text_by_lines.py`
Читает входной текстовый файл с размеченными ударениями, разбивает его на предложения (по строкам) и сохраняет в JSON-формате. Поддерживает автоопределение кодировки (UTF-8, cp1251, cp866, koi8-r, iso-8859-5). На Windows автоматически переключает консоль в UTF-8.

**Использование:**
```bash
python split_text_by_lines.py gold/pattern.txt -o output/pattern.json
```

### `run_accentuator.py`
Запускает одну библиотеку расстановки ударений, замеряет время загрузки данных в память и время обработки текста, сохраняет результаты в JSON. Поддерживает библиотеки: `accent_engine`, `udarenie`, `llm_enhancer`, `ruaccent_*`, `omogre_accentuator`, `silero_stress`.

**Использование:**
```bash
python run_accentuator.py silero_stress output/pattern.json -o output/raw/
python run_accentuator.py udarenie output/pattern.json -o output/raw/ --data-path data_plus
```

### `extract_accentuation.py`
Универсальный модуль для извлечения пословной разметки ударений. Работает в двух режимах:
- `--mode gold` — обрабатывает эталонную разметку (входной JSON с полем `text`)
- `--mode lib` — обрабатывает результаты библиотек (входной JSON с полем `accented_text`)

Удаляет знаки ударения из текста, определяет позиции ударных гласных, разбивает на слова с помощью `text_parser.TextParser` и формирует пословную разметку.

**Использование:**
```bash
# Для GOLD-разметки
python extract_accentuation.py output/pattern.json -o output/lib/GOLD_results.json --mode gold

# Для результатов библиотеки
python extract_accentuation.py output/raw/silero_stress_results.json -o output/lib/silero_stress_results.json --mode lib --lib-name silero_stress

# Проверка токенизации
python extract_accentuation.py --verify
```

### `compare_accentuators.py`
Сравнивает результаты работы библиотек с эталонной ручной разметкой (GOLD). Считает количество ошибок ударений, пропущенных ударений, несопоставленных слов. Также вычисляет метрики по "общим словам" — словам, которые были успешно размечены всеми библиотеками.

**Использование:**
```bash
python compare_accentuators.py output/lib/ -o output/comparison.json
```

### `generate_report.py`
Генерирует текстовый отчёт в формате Markdown на русском языке на основе данных сравнения. Включает таблицы производительности, ошибок, сравнение по общим словам и детальную сводку по каждой библиотеке.

**Использование:**
```bash
python generate_report.py output/comparison.json output/report.md
```

### `generate_report_en.py`
Генерирует текстовый отчёт в формате Markdown на английском языке. Функциональность аналогична `generate_report.py`.

**Использование:**
```bash
python generate_report_en.py output/comparison.json output/report_en.md
```

## Общая схема пайплайна

```
gold/pattern.txt
       │
       ▼
split_text_by_lines.py
       │
       ▼
output/pattern.json  (список предложений)
       │
       ├──► extract_accentuation.py --mode gold
       │           │
       │           ▼
       │    output/lib/GOLD_results.json  (пословная разметка эталона)
       │
       ├──► run_accentuator.py <lib1>
       │           │
       │           ▼
       │    output/raw/<lib1>_results.json  (сырые результаты)
       │           │
       │           ▼
       │    extract_accentuation.py --mode lib
       │           │
       │           ▼
       │    output/lib/<lib1>_results.json  (пословная разметка)
       │
       ├──► run_accentuator.py <lib2> ──► ... (аналогично)
       │
       ▼
compare_accentuators.py output/lib/ ──► output/comparison.json
                                              │
                                              ├──► generate_report.py ──► output/report.md
                                              │
                                              └──► generate_report_en.py ──► output/report_en.md
```

**Примечание:** Для библиотек `udarenie` и `accent_engine`, которые возвращают `DocumentResult` с пословной разметкой, шаг `extract_accentuation.py --mode lib` можно пропустить, так как пословное соответствие с исходным текстом уже содержится в дополнительной информации.

## Результаты

После выполнения пайплайна в директории `output/` создаются:
- `output/pattern.json` — разбитый на предложения эталон
- `output/lib/GOLD_results.json` — пословная разметка эталона
- `output/raw/` — сырые результаты библиотек (без пословной разметки)
- `output/lib/` — результаты с пословной разметкой
- `output/comparison.json` — данные сравнения
- **`output/report.md`** — итоговый отчёт на русском (Markdown)
- **`output/report_en.md`** — итоговый отчёт на английском (Markdown)

## [Пример отчёта](https://github.com/omogr/russian-stress-benchmark/blob/main/reports/2026-07-18.pdf)

Отчёт содержит:
- Общую информацию (дата, число предложений, количество библиотек)
- Производительность (время загрузки и обработки, исключения)
- Сводку ошибок (неправильные ударения, пропуски, несовпадения по количеству/тексту слов)
- Сравнение по общим словам (accuracy на пересечении размеченных всеми библиотеками слов)
- Детальную статистику по каждой библиотеке

## Добавление новых библиотек

### Через `benchmark.py` (рекомендуется)

Просто добавьте запись в `benchmark_config.json`:

```json
{
  "name": "my_new_lib",
  "accentuator_args": ["my_new_lib"],
  "extra_args": {"--data-path": "path/to/data"},
  "returns_document": false,
  "description": "My new stress library"
}
```

И запустите:
```bash
python benchmark.py run --gold gold/pattern.txt --libs my_new_lib
```

### Вручную (через отдельные скрипты)

Для добавления новой библиотеки надо:
1. Создать новый акцентуатор в `run_accentuator.py` (добавить ветку в `load_library()`)
2. Запустить пошагово, как описано в разделе "Быстрый старт → Способ 2"

## Структура репозитория

```
russian-stress-benchmark/
├── gold/
│   └── pattern.txt              # Эталонный образец (заглушка)
├── output/                      # Результаты тестирования (создаётся автоматически)
│   ├── pattern.json             # Разбитый на предложения эталон
│   ├── raw/                     # Сырые результаты библиотек
│   ├── lib/                     # Результаты с пословной разметкой
│   ├── comparison.json          # Данные сравнения
│   ├── report.md                # Отчёт на русском
│   └── report_en.md             # Отчёт на английском
├── benchmark.py                 # Единый оркестратор (рекомендуется)
├── benchmark_config.json        # Конфигурация бенчмарка (создаётся через init)
├── split_text_by_lines.py       # Разбиение текста на предложения
├── extract_accentuation.py      # Извлечение пословной разметки ударений
├── run_accentuator.py           # Запуск одной библиотеки
├── compare_accentuators.py      # Сравнение результатов с GOLD
├── generate_report.py           # Генерация отчёта (русский)
├── generate_report_en.py        # Генерация отчёта (английский)
├── requirements.txt             # Зависимости Python
├── run.sh                       # Старый скрипт запуска (bash)
└── run.bat                      # Старый скрипт запуска (Windows)
```

## Предупреждение

Этот проект — результат вайб-кодинга. Код сырой, мало тестировался, а результаты следует считать предварительными. Используйте на свой страх и риск.

---

*Репозиторий: [github.com/omogr/russian-stress-benchmark](https://github.com/omogr/russian-stress-benchmark)*
