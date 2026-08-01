#!/usr/bin/env python3
"""
runner.py

Единый раннер для всех адаптеров библиотек расстановки ударений.

Принимает на вход имя модуля с классом Accentuator, запускает тестирование
и сохраняет результаты в стандартном формате.

Usage:
    python runner.py <module_name> <input.json> <output.json>

Примеры:
    python runner.py silero_stress input.json output.json
    python runner.py udarenie input.json output.json

Каждый модуль-адаптер должен содержать класс Accentuator с методами:
    - __init__(self)        — инициализация, загрузка модели
    - accentuate(self, text: str) -> str  — расстановка ударений
    - description(self) -> str  — описание для отчётов
"""

import argparse
import importlib
import json
import re
import sys
import time
import traceback
from pathlib import Path
from tqdm import tqdm

VOWELS = 'аеёиоуыэюяАЕЁИОУЫЭЮЯ'


def remove_accent_marks(text: str) -> str:
    """Удаляет знаки ударения U+0301, U+0300 и '+' из текста."""
    return text.replace('\u0301', '').replace('\u0300', '').replace('+', '')


def normalize_accent_to_plus(text: str) -> str:
    """Приводит любую разметку ударений к формату '+' перед ударной гласной."""
    if not text:
        return text

    result = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i + 1] in '\u0301\u0300':
            if text[i] in VOWELS:
                result.append('+')
                result.append(text[i])
                i += 2
                continue
            else:
                result.append(text[i])
                i += 2
                continue
        result.append(text[i])
        i += 1
    text = ''.join(result)

    def _repl(m):
        return '+' + m.group(1) + m.group(3)

    text = re.sub(r'([' + VOWELS + r'])(\+)([^' + VOWELS + r']|$)', _repl, text)
    return text


def load_accentuator(module_name: str):
    """Динамически импортирует модуль и возвращает экземпляр Accentuator."""
    
    print('load_accentuator', module_name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(f"Не удалось импортировать модуль '{module_name}': {e}")

    if not hasattr(module, 'Accentuator'):
        raise AttributeError(
            f"Модуль '{module_name}' не содержит класса 'Accentuator'. "
            f"Доступные имена: {dir(module)}"
        )

    AccentuatorClass = module.Accentuator
    return AccentuatorClass()


def run(module_name: str, input_path: Path, output_path: Path) -> int:
    """Основная логика раннера."""

    # --- Чтение входного файла ---
    with open(input_path, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    sentences_data = input_data.get('sentences', [])
    if not sentences_data:
        print(f"[WARNING] В файле {input_path} не найдено предложений")
        return 1

    print(f"Найдено предложений: {len(sentences_data)}")

    # --- Загрузка библиотеки (с замером времени) ---
    script_start = time.perf_counter()
    print(f"Загрузка библиотеки '{module_name}'...")
    try:
        accentuator = load_accentuator(module_name)
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить библиотеку: {e}")
        traceback.print_exc()
        return 1
    load_time = time.perf_counter() - script_start
    print(f"  Загрузка завершена за {load_time:.2f}s")

    description = accentuator.description() if hasattr(accentuator, 'description') else module_name

    # --- Обработка предложений ---
    sentence_results = []
    total_process_time = 0.0
    total_errors = 0

    for idx, sent_item in enumerate(tqdm(sentences_data, desc="  Accentuating", unit="sent"), start=1):
        # for idx, sent_item in enumerate(sentences_data, start=1):
        original_sentence = sent_item.get("original_text", "")
        clean_sentence = remove_accent_marks(original_sentence)

        sent_start = time.perf_counter()
        errors = []
        accented_text = None

        try:
            result = accentuator.accentuate(clean_sentence)
            accented_text = normalize_accent_to_plus(result)
        except Exception as e:
            errors.append({
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc(),
            })
            total_errors += 1
            print(f"[ERROR] Предложение {idx}: {e}")
            accented_text = clean_sentence

        sent_process_time = time.perf_counter() - sent_start
        total_process_time += sent_process_time

        sentence_results.append({
            'original_text': clean_sentence,
            'accented_text': accented_text,
            'process_time_seconds': round(sent_process_time, 6),
            'errors': errors,
        })

        #if idx % 100 == 0 or idx == len(sentences_data):
        #    print(f"  Обработано {idx}/{len(sentences_data)} предложений...")

    total_time = time.perf_counter() - script_start

    print(f"\nОбработка завершена. Общее время: {total_time:.2f}s")
    if total_errors > 0:
        print(f"  Ошибок: {total_errors}")

    # --- Сохранение результата ---
    result_data = {
        'metadata': {
            'library_name': module_name,
            'library_description': description,
            'input_file': str(input_path),
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'load_time_seconds': round(load_time, 4),
            'total_process_time_seconds': round(total_process_time, 4),
            'total_time_seconds': round(total_time, 4),
            'sentence_count': len(sentence_results),
            'errors_count': total_errors,
        },
        'sentences': sentence_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"Результаты сохранены: {output_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Единый раннер для адаптеров библиотек расстановки ударений'
    )
    parser.add_argument('module_name', help='Имя модуля с классом Accentuator')
    parser.add_argument('input_file', help='Входной JSON с предложениями')
    parser.add_argument('output_file', help='Выходной JSON с результатами')
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}")
        return 1

    return run(args.module_name, input_path, output_path)


if __name__ == '__main__':
    sys.exit(main())
