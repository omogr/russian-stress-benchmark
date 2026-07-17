#!/usr/bin/env python3
"""
extract_gold_accentuation.py

Извлекает "золотую" разметку ударений из входного JSON-файла,
где ударения уже проставлены знаками '+' или U+0301,
и сохраняет результат в формате text_parser_results.json.

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
from typing import Any #, Callable


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
    def __init__(self):
        self.dubious = {}
        self.num_of_dubious = 0
    def load(self, vocab_path):
        with open(vocab_path, 'r', encoding="utf-8") as finp:
            for entry in finp:
                parts = entry.split('\t')
                if len(parts) == 2:
                    self.dubious[parts[0].strip()] = parts[1]
    def is_dubious(self, word):
        key = word.casefold()
        if key in self.dubious:
            self.num_of_dubious += 1
            return True
        if '-' in key:
            return True
        return False
      
dubious = DubiousStressPos()


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
    
    #for ch in ['+', '\u0300', '\u0301']:
    #    rep2 = f"{ch}{ch}"
    #    while rep2 in text:
    #        text = text.replace(rep2, ch)
   
    n = len(text)
    while i < n:
        ch = text[i]
        
        # Формат 1: '+' непосредственно перед гласной
        if ch == '+' and i + 1 < n and text[i + 1] in VOWELS:
            #if text[i + 1] not in '+\u0300\u0301':
            clean_chars.append(text[i + 1])
            stress_positions.append(len(clean_chars) - 1)
            i += 2
            continue

        # Формат 2: combining acute accent U+0301 после гласной
        if i + 1 < n and text[i + 1] == '\u0301' and ch in VOWELS:
            #if ch not in '+\u0300\u0301':
            clean_chars.append(ch)
            stress_positions.append(len(clean_chars) - 1)
            i += 2
            continue

        # Формат 3: combining grave accent U+0300 (на всякий случай)
        if i + 1 < n and text[i + 1] == '\u0300' and ch in VOWELS:
            #if ch not in '+\u0300\u0301':
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
# Word parsing (compatible with text_parser)
# -----------------------------------------------------------------------------

def extract_word_info(doc_result: Any) -> list[dict]:
    """Извлекает пословную информацию из DocumentResult."""
    words = []
    for sentence in doc_result.sentences:
        for word in sentence.words:
            if dubious.is_dubious(word.text):
                word.stress = None
            words.append(word)
            '''
            {
                'text': word.text,
                'start': word.start,
                'end': word.end,
                'method': word.method.name if word.method else None,
                'stress_vowel_index': word.stress.vowel_index if word.stress else None,
                'stress_char_index': word.stress.char_index if word.stress else None,
            })'''
    return words


def get_words(clean_text: str):
    """
    Разбивает предложение на слова с помощью text_parser.TextParser.
    Возвращает список объектов WordInfo (или совместимых по интерфейсу).
    """
    doc_result = _PARSER.parse(clean_text)
    if not doc_result.sentences:
        return []
    return extract_word_info(doc_result)


def build_word_info(words, stress_positions: List[int]) -> List[dict]:
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
                'method': 'GOLD',
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
    start_time = time.perf_counter()

    sentence_results = []
    for item in sentences_data:
        original = item['text']
        clean_text, stress_positions = remove_accents_and_extract(original)
        words = get_words(clean_text)
        word_infos = build_word_info(words, stress_positions)
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

    print(f"Saved: {output_path}")


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

        print("\n✅ VERIFICATION PASSED: tokenization matches text_parser exactly.")
        print("\n--- Sample output (first sentence) ---")
        print(json.dumps(gold['sentences'][0], ensure_ascii=False, indent=2))
        return 0

def run_verify2() -> int:
    """
    Создаёт тестовый JSON с размеченными ударениями, прогоняет через скрипт,
    а затем сравнивает разбиение на слова с text_parser.TextParser.
    """

    input_path = Path("results") / "text_parser_results.json"
    gold_path = Path("results") / "GOLD_results.json"

    with open(gold_path, 'r', encoding='utf-8') as f:
        gold = json.load(f)
    with open(input_path, 'r', encoding='utf-8') as f:
        engine_result = json.load(f)

    gold_sentences = gold['sentences']
    engine_sentences = engine_result['sentences']
    assert len(gold_sentences) == len(engine_sentences)
    mismatches = []
    for gold_sentence, engine_sentence in zip(gold_sentences, engine_sentences):

        engine_words = engine_sentence['words']
        gold_words = gold_sentence['words']
        
        #engine_sentence_text = '|'.join([gw['text'] for gw in engine_words])
        #gold_sentence_text = '|'.join([gw['text'] for gw in gold_words])
        #engine_sentence_text = engine_sentence["original_text"]
        engine_sentence_text = '|'.join([gw['text'] for gw in gold_words])
        gold_sentence_text = 'Приподня́вшись одни́м ту́ловищем, опира́ясь на́ руки, Гара́́ська посмотре́л вни́з, — пото́м упа́л лицо́м на зе́млю и завы́л, как ба́бы в́оют по поко́йнике.'
        
        # gold_sentence["original_text"]
        
        codes1 = '~'.join([f"{char}{ord(char)}" for char in engine_sentence_text])
        codes2 = '~'.join([f"{char}{ord(char)}" for char in gold_sentence_text])

        #sentence_text = f"\n{gold_sentence_text}\n{engine_sentence_text}\n{codes1}\n{codes1}\n"
        sentence_text = f"\n{gold_sentence_text}\n{engine_sentence_text}\n{codes2}\n{codes1}\n"
        #sentence_text = f"\n{codes1[:150]}\n{codes1[:150]}\n"

        if len(gold_words) != len(engine_words):
            mismatches.append(
                f"Word count mismatch for '{sentence_text}\n...': "
                f"gold={len(gold_words)}, engine={len(engine_words)}"
            )
            continue

        for i, (gw, ew) in enumerate(zip(gold_words, engine_words)):
            if gw['text'] != ew['text']:
                mismatches.append(
                    f"Text mismatch at word {i} in '{sentence_text}...': "
                    f"gold='{gw['text']}', engine='{ew['text']}'"
                )
            '''
            if gw['start'] != ew['start']:
                mismatches.append(
                    f"Start mismatch for '{gw['text']}' in '{sentence_text}...': "
                    f"gold={gw['start']}, engine={ew['start']}"
                )
            if gw['end'] != ew['end']:
                mismatches.append(
                    f"End mismatch for '{gw['text']}' in '{sentence_text}...': "
                    f"gold={gw['end']}, engine={ew['end']}"
                )
            '''

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
        help='Запустить проверочный тест и сравнить токенизацию с text_parser',
    )
    parser.add_argument(
        '-d', '--dubious',
        default=None,
        help='Путь к словарю со словами с варьирующимся ударением',
    )

    args = parser.parse_args()

    if args.verify:
        return run_verify2()

    if not args.input_file:
        parser.print_help()
        return 1

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    
    if args.dubious is not None:
        dubious.load(args.dubious)
        
    process_file(input_path, output_path)
    print('dubious', dubious.num_of_dubious, len(dubious.dubious))
    return 0


if __name__ == '__main__':
    sys.exit(main())