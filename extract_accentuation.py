#!/usr/bin/env python3
"""
extract_accentuation.py

Универсальный модуль для извлечения пословной разметки ударений.
Работает как с эталонной (GOLD) разметкой, так и с результатами библиотек.

Usage:
    # Для GOLD-разметки (вход: JSON с полем 'text' в каждом предложении)
    python extract_accentuation.py input.json -o output.json --mode gold

    # Для результатов библиотек (вход: JSON с полем 'accented_text')
    python extract_accentuation.py input.json -o output.json --mode lib

    # Проверка токенизации
    python extract_accentuation.py --verify
"""

import argparse
import json
import sys
import time
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from typing import Any

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

VOWELS = frozenset('аеёиоуыэюяАЕЁИОУЫЭЮЯ')

# Try to import TextParser from text_parser; if unavailable, fail with a clear message
try:
    from text_parser.parser import TextParser
    _PARSER = TextParser()
except ImportError as exc:
    raise ImportError(
        "Не удалось импортировать TextParser из text_parser. "
        "Убедитесь, что библиотека text_parser установлена или доступна в PYTHONPATH."
    ) from exc


class DubiousStressPos:
    """Словарь слов с варьирующимся ударением (исключаются из тестирования)."""
    def __init__(self):
        self.dubious = {}
        self.num_of_dubious = 0

    def load(self, vocab_path: Path):
        with open(vocab_path, 'r', encoding="utf-8") as finp:
            for entry in finp:
                parts = entry.split('\t')
                if len(parts) == 2:
                    self.dubious[parts[0].strip()] = parts[1]

    def is_dubious(self, word: str) -> bool:
        key = word.casefold()
        if key in self.dubious:
            self.num_of_dubious += 1
            return True
        if '-' in key:
            return True
        return False


# Global dubious checker (loaded on demand)
_dubious_checker: Optional[DubiousStressPos] = None


def get_dubious_checker(vocab_path: Optional[Path] = None) -> DubiousStressPos:
    global _dubious_checker
    if _dubious_checker is None:
        _dubious_checker = DubiousStressPos()
        if vocab_path is not None:
            _dubious_checker.load(vocab_path)
    return _dubious_checker


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

        # Обычный символ (пропускаем сами знаки ударения)
        if ch not in '+\u0300\u0301':
            clean_chars.append(ch)
        i += 1

    return ''.join(clean_chars), stress_positions


def build_accented_text(clean_text: str, stress_positions: List[int]) -> str:
    """Строит текст с разметкой '+' перед ударной гласной."""
    chars = list(clean_text)
    for pos in sorted(stress_positions, reverse=True):
        chars.insert(pos, '+')
    return ''.join(chars)


# -----------------------------------------------------------------------------
# Word parsing (compatible with text_parser)
# -----------------------------------------------------------------------------

def extract_word_info(doc_result: Any, library_name: str = 'GOLD',
                       dubious_path: Optional[Path] = None) -> list[dict]:
    """Извлекает пословную информацию из DocumentResult."""
    dubious_checker = get_dubious_checker(dubious_path)
    words = []
    for sentence in doc_result.sentences:
        for word in sentence.words:
            if dubious_checker.is_dubious(word.text):
                word.stress = None
            words.append(word)
    return words


def get_words(clean_text: str, library_name: str = 'GOLD',
              dubious_path: Optional[Path] = None):
    """
    Разбивает предложение на слова с помощью text_parser.TextParser.
    Возвращает список объектов WordInfo.
    """
    doc_result = _PARSER.parse(clean_text)
    if not doc_result.sentences:
        return []
    return extract_word_info(doc_result, library_name, dubious_path)


def build_word_info(words, stress_positions: List[int], library_name: str) -> List[dict]:
    """
    Сопоставляет позиции ударений со словами и формирует список
    в формате accentuator_output_format.txt.
    """
    stress_map: dict = {}

    for pos in stress_positions:
        for w in words:
            if w.start <= pos < w.end:
                char_idx = pos - w.start
                vowel_idx = 0
                found = False
                for j, c in enumerate(w.text):
                    if c in VOWELS:
                        if j == char_idx:
                            found = True
                            break
                        vowel_idx += 1
                if not found:
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
            s = stresses[0]
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
# Processing modes
# -----------------------------------------------------------------------------

def process_gold(input_path: Path, output_path: Path,
                 dubious_path: Optional[Path] = None) -> None:
    """
    Обрабатывает GOLD-разметку.
    Входной JSON содержит поле 'text' в каждом предложении.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sentences_data = data.get('sentences', [])
    start_time = time.perf_counter()

    sentence_results = []
    for item in sentences_data:
        original = item['text']
        clean_text, stress_positions = remove_accents_and_extract(original)
        words = get_words(clean_text, 'GOLD', dubious_path)
        word_infos = build_word_info(words, stress_positions, 'GOLD')
        accented_text = build_accented_text(clean_text, stress_positions)

        sentence_results.append({
            'original_text': clean_text,
            'accented_text': accented_text,
            'words': word_infos,
            'process_time_seconds': 0.0,
            'errors': [],
        })

    total_time = time.perf_counter() - start_time

    result_data = {
        'metadata': {
            'library_name': 'GOLD',
            'input_file': str(input_path),
            'timestamp': datetime.now().isoformat(),
            'load_time_seconds': 0.0,
            'total_process_time_seconds': round(total_time, 4),
            'total_time_seconds': round(total_time, 4),
            'sentence_count': len(sentence_results),
        },
        'sentences': sentence_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"Saved GOLD results: {output_path}")


def process_lib(input_path: Path, output_path: Path,
                library_name: Optional[str] = None,
                dubious_path: Optional[Path] = None) -> None:
    """
    Обрабатывает результаты библиотеки.
    Входной JSON содержит поле 'accented_text' в каждом предложении.
    Также копирует метаданные из входного файла.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sentences_data = data.get('sentences', [])
    metadata = data.get('metadata', {})

    # Auto-detect library name from metadata if not provided
    if library_name is None:
        library_name = metadata.get('library_name', 'UNKNOWN_LIBRARY')

    start_time = time.perf_counter()

    sentence_results = []
    for item in sentences_data:
        original_text = item.get("original_text", "")
        accented_text = item.get("accented_text", "")

        if not original_text and accented_text:
            # Fallback: extract clean text from accented_text
            clean_text, stress_positions = remove_accents_and_extract(accented_text)
        else:
            clean_text, stress_positions = remove_accents_and_extract(accented_text)

        words = get_words(clean_text, library_name, dubious_path)
        word_infos = build_word_info(words, stress_positions, library_name)

        item_copy = {
            'original_text': original_text or clean_text,
            'accented_text': accented_text,
            'words': word_infos,
            'process_time_seconds': item.get('process_time_seconds', 0.0),
            'errors': item.get('errors', []),
        }
        sentence_results.append(item_copy)

    total_time = time.perf_counter() - start_time

    # Preserve original metadata, just update what we computed
    result_metadata = dict(metadata)
    result_metadata['sentence_count'] = len(sentence_results)

    result_data = {
        'metadata': result_metadata,
        'sentences': sentence_results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"Saved library results: {output_path}")


# -----------------------------------------------------------------------------
# Verification
# -----------------------------------------------------------------------------

def run_verify() -> int:
    """
    Создаёт тестовый JSON с размеченными ударениями, прогоняет через скрипт,
    а затем сравнивает разбиение на слова с text_parser.TextParser.
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

        process_gold(input_path, output_path)

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

        print("\n✅ VERIFICATION PASSED: tokenization matches text_parser exactly.")
        print("\n--- Sample output (first sentence) ---")
        print(json.dumps(gold['sentences'][0], ensure_ascii=False, indent=2))
        return 0


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Извлекает пословную разметку ударений из JSON'
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Входной JSON-файл',
    )
    parser.add_argument(
        '-o', '--output',
        default='results.json',
        help='Путь к выходному JSON (default: results.json)',
    )
    parser.add_argument(
        '--mode',
        choices=['gold', 'lib'],
        default='gold',
        help='Режим: gold — эталонная разметка (поле text), '
             'lib — результаты библиотеки (поле accented_text) (default: gold)',
    )
    parser.add_argument(
        '--lib-name',
        default=None,
        help='Имя библиотеки (для mode=lib; если не указано, берётся из metadata)',
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Запустить проверочный тест и сравнить токенизацию с text_parser',
    )
    parser.add_argument(
        '-d', '--dubious',
        default=None,
        help='Путь к словарю со словами с варьирующимся ударением',
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
    dubious_path = Path(args.dubious) if args.dubious else None

    if args.mode == 'gold':
        process_gold(input_path, output_path, dubious_path)
    else:
        process_lib(input_path, output_path, args.lib_name, dubious_path)

    return 0


if __name__ == '__main__':
    sys.exit(main())