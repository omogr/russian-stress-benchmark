#!/usr/bin/env python3
"""
extract_gold_accentuation.py

Извлекает "золотую" разметку ударений из входного JSON-файла,
где ударения уже проставлены знаками '+' или U+0301,
и сохраняет результат в формате accent_engine_results.json.

Usage:
    python extract_gold_accentuation.py input.json -o results/
    python extract_gold_accentuation.py --verify
"""

import argparse
import json
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import copy

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

VOWELS = frozenset('аеёиоуыэюяАЕЁИОУЫЭЮЯ')

# Try to import TextParser from accent_engine; if unavailable, fail with a clear message
try:
    from accent_engine.parser import TextParser
    _PARSER = TextParser()
except ImportError as exc:
    raise ImportError(
        "Не удалось импортировать TextParser из accent_engine. "
        "Убедитесь, что библиотека accent_engine установлена или доступна в PYTHONPATH."
    ) from exc


# -----------------------------------------------------------------------------
# Accent extraction
# -----------------------------------------------------------------------------

def remove_accents_and_extract(text: str) -> Tuple[str, List[int]]:
    """
    Удаляет знаки ударения из текста и возвращает:
      - clean_text: текст без знаков ударения
      - stress_positions: список позиций (0-based в clean_text) ударных гласных
    """
    clean_chars: List[str] = []
    stress_positions: List[int] = []

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        # Формат 1: '+' непосредственно перед гласной
        if ch == '+' and i + 1 < n and text[i + 1] in VOWELS:
            clean_chars.append(text[i + 1])
            stress_positions.append(len(clean_chars) - 1)
            i += 2
            continue

        # Формат 2: combining acute accent U+0301 после гласной
        if i + 1 < n and text[i + 1] == '\u0301' and ch in VOWELS:
            clean_chars.append(ch)
            stress_positions.append(len(clean_chars) - 1)
            i += 2
            continue

        # Формат 3: combining grave accent U+0300 (на всякий случай)
        if i + 1 < n and text[i + 1] == '\u0300' and ch in VOWELS:
            clean_chars.append(ch)
            stress_positions.append(len(clean_chars) - 1)
            i += 2
            continue

        # Обычный символ
        if ch not in '+\u0300\u0301':
            clean_chars.append(ch)
        i += 1

    return ''.join(clean_chars), stress_positions


def build_accented_text(clean_text: str, stress_positions: List[int]) -> str:
    """Строит текст с разметкой '+' перед ударной гласной."""
    chars = list(clean_text)
    # Вставляем справа налево, чтобы индексы не сдвигались
    for pos in sorted(stress_positions, reverse=True):
        chars.insert(pos, '+')
    return ''.join(chars)


# -----------------------------------------------------------------------------
# Word parsing (compatible with accent_engine)
# -----------------------------------------------------------------------------

def get_words(clean_text: str):
    """
    Разбивает предложение на слова с помощью accent_engine.TextParser.
    Возвращает список объектов WordInfo (или совместимых по интерфейсу).
    """
    doc = _PARSER.parse(clean_text)
    if not doc.sentences:
        return []
    return doc.sentences[0].words


def build_word_info(words, stress_positions: List[int], library_name: str) -> List[dict]:
    """
    Сопоставляет позиции ударений со словами и формирует список
    в формате accentuator_output_format.txt.
    """
    # word_id -> list of stress dicts
    stress_map: dict = {}

    for pos in stress_positions:
        for w in words:
            if w.start <= pos < w.end:
                char_idx = pos - w.start
                # Вычисляем 0-based индекс среди гласных
                vowel_idx = 0
                found = False
                for j, c in enumerate(w.text):
                    if c in VOWELS:
                        if j == char_idx:
                            found = True
                            break
                        vowel_idx += 1
                if not found:
                    # Ударение не на гласной — пропускаем (ошибка разметки)
                    break
                stress_map.setdefault(id(w), []).append({
                    'stress_char_index': char_idx,
                    'stress_vowel_index': vowel_idx,
                })
                break

    result: List[dict] = []
    for w in words:
        stresses = stress_map.get(id(w), [])
        if stresses:
            s = stresses[0]  # берём первое ударение
            result.append({
                'text': w.text,
                'start': w.start,
                'end': w.end,
                'method': library_name,
                'stress_vowel_index': s['stress_vowel_index'],
                'stress_char_index': s['stress_char_index'],
            })
        else:
            result.append({
                'text': w.text,
                'start': w.start,
                'end': w.end,
                'method': None,
                'stress_vowel_index': None,
                'stress_char_index': None,
            })

    return result


# -----------------------------------------------------------------------------
# Main processing
# -----------------------------------------------------------------------------

def process_file(input_path: Path, output_path: Path) -> None:
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sentences_data = data.get('sentences', [])
    
    library_name = data.get('metadata', {}).get('library_name', "UNKNOWN_LIBRARY")
    start_time = time.perf_counter()

    sentence_results = []
    for item in sentences_data:
        original_text = item.get("original_text")
        accented_text = item.get("accented_text")
        if not original_text:
            original_text = ""
        if not accented_text:
            accented_text = ""
        clean_text, stress_positions = remove_accents_and_extract(accented_text)
        words = get_words(clean_text)
        word_infos = build_word_info(words, stress_positions, library_name)
        # accented_text = build_accented_text(clean_text, stress_positions)
        item_copy = copy.copy(item)
        item_copy['words'] = word_infos

        sentence_results.append(item_copy)
        '''
        {
            'original_text': original_text,
            'accented_text': accented_text,
            'words': word_infos,
            'process_time_seconds': 0.0,
            'errors': [],
        })
        '''

    #total_time = time.perf_counter() - start_time 
    result_data = {
        'metadata': {
            'library_name': library_name,
            'input_file': data.get('metadata', {}).get('input_file', "-"),
            'timestamp': data.get('metadata', {}).get('timestamp', "-"),
            'load_time_seconds': data.get('metadata', {}).get('load_time_seconds', 0.0),
            'total_process_time_seconds': data.get('metadata', {}).get('total_process_time_seconds', 0.0),
            'total_time_seconds': data.get('metadata', {}).get('total_time_seconds', 0.0),
            'sentence_count': len(sentence_results),
        },
        'sentences': sentence_results,
    }
    '''
        result_data = {
            'metadata': {
                'library_name': library_name,
                'input_file': str(input_path),
                'timestamp': datetime.now().isoformat(),
                'load_time_seconds': 0.0,
                'total_process_time_seconds': round(total_time, 4),
                'total_time_seconds': round(total_time, 4),
                'sentence_count': len(sentence_results),
            },
            'sentences': sentence_results,
        }
    '''
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")


# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------

def run_verify() -> int:
    """
    Создаёт тестовый JSON с размеченными ударениями, прогоняет через скрипт,
    а затем сравнивает разбиение на слова с accent_engine.TextParser.
    """
    test_cases = [
        {"text": "М+ама м+ыла р+аму.", "start": 1, "end": 20},
        {"text": "Он приш+ёл дом+ой.", "start": 21, "end": 45},
        {
            "text": "Баргамо́т и Гара́ська\nавтор Леони́д Никола́евич Андре́ев",
            "start": 46,
            "end": 110,
        },
        {"text": "по-насто́ящему", "start": 111, "end": 130},
        {"text": "С+олнце свет+ит я́рко.", "start": 131, "end": 160},
    ]

    test_data = {
        "metadata": {
            "sentence_count": len(test_cases),
            "timestamp": datetime.now().isoformat(),
        },
        "sentences": test_cases,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "test_input.json"
        output_path = Path(tmpdir) / "gold_results.json"

        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)

        process_file(input_path, output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            gold = json.load(f)

        mismatches = []
        for sent_gold in gold['sentences']:
            clean = sent_gold['original_text']
            doc = _PARSER.parse(clean)
            engine_words = doc.sentences[0].words if doc.sentences else []
            gold_words = sent_gold['words']

            if len(gold_words) != len(engine_words):
                mismatches.append(
                    f"Word count mismatch for '{clean[:50]}...': "
                    f"gold={len(gold_words)}, engine={len(engine_words)}"
                )
                continue

            for i, (gw, ew) in enumerate(zip(gold_words, engine_words)):
                if gw['text'] != ew.text:
                    mismatches.append(
                        f"Text mismatch at word {i} in '{clean[:50]}...': "
                        f"gold='{gw['text']}', engine='{ew.text}'"
                    )
                if gw['start'] != ew.start:
                    mismatches.append(
                        f"Start mismatch for '{gw['text']}' in '{clean[:50]}...': "
                        f"gold={gw['start']}, engine={ew.start}"
                    )
                if gw['end'] != ew.end:
                    mismatches.append(
                        f"End mismatch for '{gw['text']}' in '{clean[:50]}...': "
                        f"gold={gw['end']}, engine={ew.end}"
                    )

        if mismatches:
            print("\n❌ VERIFICATION FAILED:")
            for m in mismatches:
                print(f"   {m}")
            return 1

        print("\n✅ VERIFICATION PASSED: tokenization matches accent_engine exactly.")
        print("\n--- Sample output (first sentence) ---")
        print(json.dumps(gold['sentences'][0], ensure_ascii=False, indent=2))
        return 0


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Извлекает золотую разметку ударений из JSON с размеченным текстом'
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Входной JSON-файл с предложениями (формат как у run_accentuator.py)',
    )
    parser.add_argument(
        '-o', '--output',
        default='gold_results.json',
        help='Путь к выходному JSON (default: gold_results.json)',
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Запустить проверочный тест и сравнить токенизацию с accent_engine',
    )

    args = parser.parse_args()

    if args.verify:
        return run_verify()

    if not args.input_file:
        parser.print_help()
        return 1

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    process_file(input_path, output_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())