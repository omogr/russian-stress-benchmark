#!/usr/bin/env python3
"""
run_accentuator.py

Запускает одну библиотеку расстановки ударений, замеряет время загрузки
данных в память и время обработки текста, сохраняет результаты в JSON.

Для accent_engine, wiki_enhancer и llm_enhancer сохраняется пословная
информация (координаты слов и StressMethod).

Использование:
    python run_accentuator.py accent_engine sentences.json -o results/
    python run_accentuator.py wiki_enhancer sentences.json -o results/
    python run_accentuator.py llm_enhancer sentences.json -o results/
    python run_accentuator.py ruaccent_turbo sentences.json -o results/
    python run_accentuator.py silero_stress sentences.json -o results/
"""

import argparse
import json
import re
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from ensure_data import ensure_data


VOWELS = 'аеёиоуыэюяАЕЁИОУЫЭЮЯ'


def remove_accent_marks(text: str) -> str:
    """Удаляет знаки ударения U+0301 и U+0300 из текста."""
    return text.replace('\u0301', '').replace('\u0300', '').replace('+', '')


def normalize_accent_to_plus(text: str) -> str:
    """Приводит любую разметку ударений к формату '+' перед ударной гласной."""
    if not text:
        return text

    # Шаг 1: заменяем combining acute/grave на '+' перед гласной
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

    # Шаг 2: если '+' оказался после гласной, переносим вперёд
    def _repl(m):
        return '+' + m.group(1) + m.group(3)

    text = re.sub(r'([' + VOWELS + r'])(\+)([^' + VOWELS + r']|$)', _repl, text)
    return text


@dataclass
class LibraryConfig:
    name: str
    accentuate_fn: Callable[[str], Any]
    returns_document: bool = False


def extract_word_info(doc_result: Any) -> list[dict]:
    """Извлекает пословную информацию из DocumentResult."""
    words = []
    for sentence in doc_result.sentences:
        for word in sentence.words:
            words.append({
                'text': word.text,
                'start': word.start,
                'end': word.end,
                'method': word.method.name if word.method else None,
                'stress_vowel_index': word.stress.vowel_index if word.stress else None,
                'stress_char_index': word.stress.char_index if word.stress else None,
            })
    return words


def load_library(library_name: str, args: argparse.Namespace) -> LibraryConfig:
    """Загружает указанную библиотеку и возвращает её конфигурацию."""

    if library_name == 'accent_engine':
        from accent_engine import AccentEngine, AccentConfig
        config = AccentConfig(data_path=Path(args.data_path))
        engine = AccentEngine(config)

        def accentuate(text: str):
            return engine.accentuate(text)

        return LibraryConfig(
            name=library_name,
            accentuate_fn=accentuate,
            returns_document=True,
        )

    elif library_name == 'wiki_enhancer':
        from accent_engine import AccentEngine, AccentConfig
        from wiktionary_enhancer import WiktionaryAccentEnhancer, WiktionaryStressFinder

        engine = AccentEngine(AccentConfig(data_path=Path(args.data_path)))
        finder = WiktionaryStressFinder(args.wiki_path)
        enhancer = WiktionaryAccentEnhancer(engine, finder)

        def accentuate(text: str):
            return enhancer.accentuate(text)

        return LibraryConfig(
            name=library_name,
            accentuate_fn=accentuate,
            returns_document=True,
        )

    elif library_name == 'llm_enhancer':
        from accent_engine import AccentEngine, AccentConfig
        from llm_accent_enhancer import AccentDataStore, AccentResolver, LLMAccentEnhancer

        engine = AccentEngine(AccentConfig(data_path=Path(args.data_path)))
        store = AccentDataStore(args.ambiguity_path)
        resolver = AccentResolver(
            data_store=store,
        )
        resolver._load_model()
        enhancer = LLMAccentEnhancer(engine, resolver, only_ambiguous=True)

        def accentuate(text: str):
            return enhancer.accentuate(text)

        return LibraryConfig(
            name=library_name,
            accentuate_fn=accentuate,
            returns_document=True,
        )

    elif library_name.startswith('ruaccent_'):
        from ruaccent import RUAccent
        model_size = library_name.split('_', 1)[1]
        accentizer = RUAccent()
        accentizer.load(omograph_model_size=model_size, use_dictionary=True)

        def accentuate(text: str):
            return accentizer.process_all(text)

        return LibraryConfig(
            name=library_name,
            accentuate_fn=accentuate,
            returns_document=False,
        )

    elif library_name == 'omogre_accentuator':
        from omogre import Accentuator
        accentuator = Accentuator(data_path=args.data_path)

        def accentuate(text: str):
            result = accentuator(text)
            if isinstance(result, list):
                return ' '.join(result)
            return result

        return LibraryConfig(
            name=library_name,
            accentuate_fn=accentuate,
            returns_document=False,
        )
    elif library_name == 'silero_stress':
        from silero_stress import load_accentor
        accentor = load_accentor()
 
        def accentuate(text: str):
            return accentor(text)
 
        return LibraryConfig(
            name=library_name,
            accentuate_fn=accentuate,
            returns_document=False,
        )
    else:
        raise ValueError(f"Неизвестная библиотека: {library_name}")


def main():
    parser = argparse.ArgumentParser(
        description='Запуск одной библиотеки расстановки ударений с замером времени'
    )
    parser.add_argument(
        'library',
        help='Имя библиотеки: accent_engine, wiki_enhancer, llm_enhancer, ruaccent_turbo, omogre_accentuator, silero_stress, ...'
    )
    parser.add_argument(
        'input_file',
        help='Входной JSON-файл с текстом, разбитым на предложения (см. split_sentences.py)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        default='accent_results',
        help='Директория для сохранения результатов (default: accent_results)'
    )
    parser.add_argument(
        '--data-path',
        default='data/accent_engine',
        help='Путь к данным accent_engine / omogre (default: data/accent_engine)'
    )
    parser.add_argument(
        '--wiki-path',
        default='./data/wiktionary_enhancer/kaikki-forms.jsonl',
        help='Путь к данным викисловаря (default: ./data/wiktionary_enhancer/kaikki-forms.jsonl)'
    )
    parser.add_argument(
        '--ambiguity-path',
        default='./data/wiktionary_enhancer/ambiguity.jsonl',
        help='Путь к файлу неоднозначностей для llm_enhancer (default: ./data/wiktionary_enhancer/ambiguity.jsonl)'
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}")
        return 1
        
    ensure_data()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # === Загрузка библиотеки (с замером времени) ===
    script_start = time.perf_counter()
    print(f"Загрузка библиотеки '{args.library}'...")
    try:
        library = load_library(args.library, args)
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить библиотеку: {e}")
        traceback.print_exc()
        return 1
    load_time = time.perf_counter() - script_start
    print(f"  Загрузка завершена за {load_time:.2f}s")

    # === Чтение входного JSON с предложениями ===
    with open(input_path, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    sentences_data = input_data.get('sentences', [])
    if not sentences_data:
        print(f"[WARNING] В файле {input_path} не найдено предложений")
        return 1

    print(f"Найдено предложений: {len(sentences_data)}")

    # === Обработка по предложениям ===
    sentence_results = []
    total_process_time = 0.0

    for idx, sent_item in enumerate(sentences_data, start=1):
        original_sentence = sent_item["original_text"]
        clean_sentence = remove_accent_marks(original_sentence)

        sent_start = time.perf_counter()
        errors = []
        words = None
        accented_text = None

        try:
            result = library.accentuate_fn(clean_sentence)
            if library.returns_document:
                doc_result = result
                accented_text = normalize_accent_to_plus(doc_result.to_annotated_text())
                words = extract_word_info(doc_result)
            else:
                accented_text = normalize_accent_to_plus(result)
        except Exception as e:
            errors.append({
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc(),
            })
            print(f"[ERROR] Предложение {idx}: {e}")

        sent_process_time = time.perf_counter() - sent_start
        total_process_time += sent_process_time

        sentence_results.append({
            'original_text': clean_sentence,
            'accented_text': accented_text,
            'words': words,
            'process_time_seconds': round(sent_process_time, 6),
            'errors': errors,
        })

        if idx % 100 == 0 or idx == len(sentences_data):
            print(f"  Обработано {idx}/{len(sentences_data)} предложений...")

    total_time = time.perf_counter() - script_start

    print(f"Обработка завершена. Общее время: {total_time:.2f}s")

    # === Сохранение результата ===
    result_data = {
        'metadata': {
            'library_name': library.name,
            'input_file': str(input_path),
            'timestamp': datetime.now().isoformat(),
            'load_time_seconds': round(load_time, 4),
            'total_process_time_seconds': round(total_process_time, 4),
            'total_time_seconds': round(total_time, 4),
            'sentence_count': len(sentence_results),
        },
        'sentences': sentence_results,
    }

    output_path = output_dir / f"{library.name}_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"Результаты сохранены: {output_path}")
    return 0


if __name__ == '__main__':
    exit(main())