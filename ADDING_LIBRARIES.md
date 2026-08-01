# Добавление новой библиотеки в бенчмарк

## Быстрый старт

Для добавления новой библиотеки нужно сделать **только два шага**:

### Шаг 1: Создать адаптер

Скопируйте шаблон и настройте под свою библиотеку:

```bash
cp adapters/_template.py adapters/my_library.py
```

Отредактируйте три метода в классе `Accentuator`:

```python
class Accentuator:
    def __init__(self):
        """Загружает и инициализирует библиотеку."""
        from my_library import StressPlacer
        self.placer = StressPlacer.load("path/to/model")

    def accentuate(self, text: str) -> str:
        """Расставляет ударения в тексте."""
        return self.placer.place_stress(text)

    def description(self) -> str:
        """Описание для отчётов."""
        return "My awesome stress library"
```

### Шаг 2: Добавить в конфиг

Добавьте запись в `benchmark_config.json`:

```json
{
  "libraries": [
    ...
    {
      "name": "my_library",
      "description": "My awesome stress library"
    }
  ]
}
```

Готово! Запускайте:

```bash
python benchmark.py run --gold gold/pattern.txt --libs my_library
```

---

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  adapters/      │     │  adapters/      │     │  adapters/      │
│  silero_stress  │     │  udarenie.py    │     │  my_library.py  │
│  .py            │     │                 │     │                 │
│                 │     │  class          │     │  class          │
│  class          │     │  Accentuator:   │     │  Accentuator:   │
│  Accentuator:   │     │    __init__()   │     │    __init__()   │
│    __init__()   │     │    accentuate() │     │    accentuate() │
│    accentuate() │     │    description()│     │    description()│
│    description()│     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │   runner.py               │
                    │                           │
                    │  - читает input.json      │
                    │  - импортирует Accentuator│
                    │  - замеряет время         │
                    │  - нормализует ударения   │
                    │  - пишет output.json      │
                    └───────────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      benchmark.py         │
                    │   (оркестратор)           │
                    └───────────────────────────┘
```

**Адаптер** — минимальный модуль, знает только о своей библиотеке.
**Раннер** (`runner.py`) — общая логика, не трогается при добавлении библиотек.
**Оркестратор** (`benchmark.py`) — управляет пайплайном, не трогается при добавлении библиотек.

---

## Протокол адаптера

Каждый адаптер — модуль Python с классом `Accentuator`, содержащим три метода:

### `__init__(self)`

Инициализирует библиотеку. Здесь происходит загрузка моделей, словарей и т.д.
Время выполнения этого метода замеряется отдельно как `load_time`.

### `accentuate(self, text: str) -> str`

Принимает **одно предложение** без знаков ударения, возвращает текст с ударениями.

**Вход:** чистый текст (знаки `+`, `\u0301`, `\u0300` уже удалены).
**Выход:** текст с ударениями. Предпочтительный формат — `+` перед ударной гласной.
Допустимы также `\u0301` / `\u0300` после гласной — раннер нормализует автоматически.

При ошибке метод может бросить исключение — раннер поймает его, запишет в лог
и продолжит работу с остальными предложениями.

### `description(self) -> str`

Возвращает описание библиотеки для отчётов. Необязательный метод — если отсутствует,
используется имя модуля.

---

## Проверка адаптера вручную

Перед подключением к бенчмарку можно проверить адаптер отдельно:

```bash
# 1. Подготовить тестовый вход
echo '{"sentences":[{"original_text":"В л+есу род+илась ёлочка."}]}' > test_input.json

# 2. Запустить раннер
python runner.py my_library test_input.json test_output.json

# 3. Проверить результат
cat test_output.json | python -m json.tool
```

---

## Примеры существующих адаптеров

### silero_stress

```python
from silero_stress import load_accentor

class Accentuator:
    def __init__(self):
        self.accentor = load_accentor()

    def accentuate(self, text: str) -> str:
        return self.accentor(text)

    def description(self) -> str:
        return "Silero stress placement"
```

### udarenie (с морфологией)

```python
from pathlib import Path
from udarenie import load_accentor

class Accentuator:
    def __init__(self):
        self.accentor = load_accentor(data_dir=Path("data_plus"))

    def accentuate(self, text: str) -> str:
        doc = self.accentor.accentuate(text)
        return doc.to_annotated_text()

    def description(self) -> str:
        return "Udarenie with morphology"
```

### accent_engine (без морфологии)

```python
from pathlib import Path
from udarenie import load_accentor

class Accentuator:
    def __init__(self):
        self.accentor = load_accentor(data_dir=Path("data_plus"), use_morph=False)

    def accentuate(self, text: str) -> str:
        doc = self.accentor.accentuate(text)
        return doc.to_annotated_text()

    def description(self) -> str:
        return "Accent engine without morphology"
```

---

## Продвинутые сценарии

### Адаптер без записи в конфиге

Если в `adapters/` лежит файл `my_lib.py`, но его нет в `benchmark_config.json`,
`benchmark.py status` покажет его как "orphan adapter". Чтобы запустить — добавьте в конфиг.

### Нестандартные зависимости

Адаптер может импортировать любые пакеты — раннер запускает его в том же Python-процессе,
где запущен `benchmark.py`. Если библиотеке нужен отдельный venv — создайте адаптер-обёртку,
которая запускает нужный интерпретатор через `subprocess`.

### Адаптер на другом языке

Если библиотека написана не на Python, создайте адаптер-обёртку на Python,
которая вызывает внешний процесс:

```python
import subprocess

class Accentuator:
    def __init__(self):
        # Проверяем, что бинарник доступен
        subprocess.run(["my_stress_tool", "--version"], check=True)

    def accentuate(self, text: str) -> str:
        result = subprocess.run(
            ["my_stress_tool", "--accentuate"],
            input=text, capture_output=True, text=True, encoding='utf-8'
        )
        return result.stdout.strip()

    def description(self) -> str:
        return "My external stress tool"
```
