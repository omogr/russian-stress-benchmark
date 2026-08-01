"""
adapters/my_library.py

Шаблон адаптера для подключения новой библиотеки расстановки ударений.

Как использовать:
1. Скопируйте этот файл в adapters/<имя_вашей_библиотеки>.py
2. Замените код в методах __init__ и accentuate на реальный
3. Добавьте имя библиотеки в benchmark_config.json
4. Запустите: python benchmark.py run --gold gold/pattern.txt --libs <имя>

Проверка вручную:
    python adapters/runner.py <имя_модуля> input.json output.json
    (модуль должен быть доступен для импорта из текущей директории)
"""

# TODO: замените на реальный импорт вашей библиотеки
# from my_library import StressPlacer


class Accentuator:
    def __init__(self):
        """Загружает и инициализирует библиотеку."""
        # TODO: замените на реальную инициализацию
        # self.placer = StressPlacer.load("path/to/model")
        pass

    def accentuate(self, text: str) -> str:
        """Расставляет ударения в тексте."""
        # TODO: замените на реальный вызов
        # return self.placer.place_stress(text)
        return text  # заглушка

    def description(self) -> str:
        """Описание библиотеки для отчётов."""
        return "My library description"
