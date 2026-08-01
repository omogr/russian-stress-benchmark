# russian-stress-benchmark

[English README](https://github.com/omogr/russian-stress-benchmark/blob/main/README_eng.md)

Набор скриптов для сравнения библиотек расстановки ударений с эталонной ручной разметкой.

## Что делает

Репозиторий содержит пайплайн для автоматического тестирования и сравнения различных библиотек, которые расставляют ударения в текстах на русском языке. Результаты работы каждой библиотеки сравниваются с размеченным вручную образцом (gold standard) и формируется детальный отчёт.

Каждая тестируемая библиотека должна уметь получать на вход текстовую строку с текстом и возвращать строку с этим же текстом, в который добавлены знаки ударения. Чаще всего для указания ударения используется знак `+` перед ударной гласной. В некоторых случаях допускается использование знаков ударения U+0301 и U+0300 после ударной гласной.

Тестирование измеряет:
- число ошибок расстановки ударений
- время работы
- время загрузки данных в оперативную память
- число исключительных ситуаций в библиотеках
- отличия возвращаемого текста от исходного

## Сравниваемые библиотеки

| Библиотека | Описание |
|------------|----------|
| `silero_stress` | [silero-stress](https://github.com/snakers4/silero-stress) |
| `udarenie` | Модель и словари из [omogre](https://github.com/omogr/omogre) + морфологический анализатор Natasha NewsMorphTagger + ударения из Wiktionary. Возвращает пословную разметку. |
| `accent_engine` | Библиотека udarenie с выключенной морфологией. Работает быстрее, но ошибок немного больше. |

## Важные ограничения

- Библиотека не должна менять исходный текст, а только добавлять знаки ударений. Если слова появились/исчезли, учитываются только неизменившиеся слова от начала и от конца предложения. Остальные считаются несопоставившимися.
- Считаются ошибки на тех словах, которые были размечены **всеми** библиотеками — это позволяет сравнивать точность без учёта искажений текста.
- **Реальный эталон** (`gold/pattern.txt`) в репозитории не выложен — присутствует заглушка. Используйте собственный размеченный текст.
- Есть словарь слов с допустимыми вариантами ударений — такие слова не учитываются.
- Слова с дефисами **не тестируются**.
- Код сырой, мало тестировался. Результаты предварительные.

## Требования

- Python 3.x
- Зависимости из `requirements.txt`

## Быстрый старт

```bash
# 1. Инициализация конфигурации
python benchmark.py init

# 2. Запуск полного бенчмарка
python benchmark.py run --gold gold/pattern.txt
```

## Управление через `benchmark.py`

`benchmark.py` — единый оркестратор. Управляет пайплайном:
`split → extract_gold → [run_adapter] × N → compare → report`

### Команды

| Команда | Описание |
|---------|----------|
| `init` | Создать `benchmark_config.json` |
| `run` | Запустить бенчмарк |
| `status` | Показать статус кэша |
| `clean` | Очистить кэш |
| `list-adapters` | Показать доступные адаптеры |

### Примеры

```bash
# Полный прогон
python benchmark.py run --gold gold/pattern.txt

# Только указанные библиотеки
python benchmark.py run --gold gold/pattern.txt --libs silero_stress,udarenie

# Перезапуск конкретной библиотеки
python benchmark.py run --gold gold/pattern.txt --libs accent_engine --force

# Статус
python benchmark.py status --gold gold/pattern.txt

# Список адаптеров
python benchmark.py list-adapters

# Очистить кэш
python benchmark.py clean --all
```

### Конфигурация (`benchmark_config.json`)

```json
{
  "libraries": [
    {
      "name": "silero_stress",
      "description": "Silero stress placement"
    },
    {
      "name": "udarenie",
      "description": "Udarenie with morphology"
    }
  ],
  "output_dir": "output",
  "cache_dir": ".benchmark_cache",
  "adapters_dir": "adapters",
  "dubious_file": "gold/dubious.txt",
  "reports": "both"
}
```

| Поле | Описание |
|------|----------|
| `name` | Имя библиотеки (совпадает с именем файла адаптера без `.py`) |
| `description` | Описание для отчётов |
| `output_dir` | Директория для результатов |
| `cache_dir` | Директория для кэша |
| `adapters_dir` | Директория с адаптерами |
| `dubious_file` | Словарь слов с варьирующимся ударением |
| `reports` | `"ru"`, `"en"` или `"both"` |

## Добавление новых библиотек

Для добавления новой библиотеки нужно сделать **только два шага**:

### Шаг 1: Создать адаптер

```bash
cp adapters/_template.py adapters/my_library.py
```

Отредактируйте класс `Accentuator`:

```python
class Accentuator:
    def __init__(self):
        """Загрузка модели / данных."""
        from my_library import StressPlacer
        self.placer = StressPlacer.load("path/to/model")

    def accentuate(self, text: str) -> str:
        """Расстановка ударений в одном предложении."""
        return self.placer.place_stress(text)

    def description(self) -> str:
        """Описание для отчётов."""
        return "My awesome stress library"
```

### Шаг 2: Добавить в конфиг

```json
{
  "libraries": [
    ...
    {"name": "my_library", "description": "My awesome stress library"}
  ]
}
```

Готово:

```bash
python benchmark.py run --gold gold/pattern.txt --libs my_library
```

Подробнее см. [ADDING_LIBRARIES.md](ADDING_LIBRARIES.md).

## Проверка адаптера вручную

```bash
# Подготовить тестовый вход
echo '{"sentences":[{"original_text":"В л+есу род+илась ёлочка."}]}' > test_input.json

# Запустить раннер
python adapters/runner.py adapters.my_library test_input.json test_output.json

# Проверить результат
cat test_output.json | python -m json.tool
```

## Архитектура

```
russian-stress-benchmark/
├── benchmark.py              # Единый оркестратор
├── benchmark_config.json     # Конфигурация
├── README.md
├── requirements.txt
│
├── adapters/                 # Адаптеры библиотек
│   ├── runner.py             # Единый раннер (общая логика)
│   ├── _template.py          # Шаблон для новых адаптеров
│   ├── silero_stress.py
│   ├── udarenie.py
│   └── accent_engine.py
│
├── core/                     # Шаги пайплайна
│   ├── split_text_by_lines.py
│   ├── extract_accentuation.py
│   ├── compare_accentuators.py
│   ├── generate_report.py
│   └── generate_report_en.py
│
├── gold/
│   └── pattern.txt           # Эталон (заглушка)
│
└── output/                   # Результаты (создаётся автоматически)
    ├── raw/
    ├── lib/
    ├── comparison.json
    ├── report.md
    └── report_en.md
```

**Адаптер** — минимальный модуль, знает только о своей библиотеке.  
**Раннер** (`adapters/runner.py`) — общая логика: замер времени, нормализация, сохранение.  
**Оркестратор** (`benchmark.py`) — управляет пайплайном, кэшем, отчётами.

## Описание скриптов

### `benchmark.py`
Единый оркестратор. Управляет пайплайном: `split → extract_gold → [run_adapter] × N → compare → report`. Поддерживает кэширование, инкрементальный запуск, проверку статуса.

### `adapters/runner.py`
Единый раннер для всех адаптеров. Получает имя модуля, динамически импортирует `Accentuator`, замеряет время загрузки и обработки, нормализует ударения, сохраняет результаты.

### `core/split_text_by_lines.py`
Разбивает входной текст на предложения (по строкам) и сохраняет в JSON. Поддерживает автоопределение кодировки.

### `core/extract_accentuation.py`
Извлекает пословную разметку ударений. Режимы:
- `--mode gold` — эталонная разметка
- `--mode lib` — результаты библиотеки

### `core/compare_accentuators.py`
Сравнивает результаты библиотек с GOLD. Считает ошибки, пропуски, несопоставленные слова, метрики по общим словам.

### `core/generate_report.py` / `core/generate_report_en.py`
Генерируют отчёты в Markdown на русском и английском.

## Общая схема пайплайна

```
gold/pattern.txt
       │
       ▼
core/split_text_by_lines.py
       │
       ▼
output/pattern.json
       │
       ├──► core/extract_accentuation.py --mode gold
       │           │
       │           ▼
       │    output/lib/GOLD_results.json
       │
       ├──► adapters/runner.py adapters.<lib1>
       │           │
       │           ▼
       │    output/raw/<lib1>_results.json
       │           │
       │           ▼
       │    core/extract_accentuation.py --mode lib
       │           │
       │           ▼
       │    output/lib/<lib1>_results.json
       │
       ├──► adapters/runner.py adapters.<lib2> ──► ...
       │
       ▼
core/compare_accentuators.py ──► output/comparison.json
                                       │
                                       ├──► core/generate_report.py ──► output/report.md
                                       │
                                       └──► core/generate_report_en.py ──► output/report_en.md
```

## Результаты

После выполнения пайплайна в `output/`:
- `pattern.json` — разбитый на предложения эталон
- `lib/GOLD_results.json` — пословная разметка эталона
- `raw/` — сырые результаты адаптеров
- `lib/` — результаты с пословной разметкой
- `comparison.json` — данные сравнения
- **`report.md`** — итоговый отчёт на русском
- **`report_en.md`** — итоговый отчёт на английском

## Предупреждение

Этот проект — результат вайб-кодинга. Код сырой, мало тестировался, а результаты следует считать предварительными. Используйте на свой страх и риск.

---

*Репозиторий: [github.com/omogr/russian-stress-benchmark](https://github.com/omogr/russian-stress-benchmark)*
