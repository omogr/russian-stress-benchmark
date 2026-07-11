#!/usr/bin/env python3
"""
split_sentences.py

Читает входной текстовый файл, разбивает его на предложения
с помощью razdel.sentenize и сохраняет в JSON-файл.

Использование:
    python split_sentences.py input.txt -o sentences.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from razdel import sentenize


def main():
    parser = argparse.ArgumentParser(
        description='Разбиение текста на предложения с помощью razdel'
    )
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument(
        '-o', '--output',
        default='sentences.json',
        help='Выходной JSON-файл (default: sentences.json)'
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}")
        return 1

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    sentences = []
    for sent in sentenize(raw_text):
        sentences.append({
            'text': sent.text,
            'start': sent.start,
            'end': sent.stop,
        })

    result = {
        'metadata': {
            'source_file': str(input_path),
            'sentence_count': len(sentences),
            'timestamp': datetime.now().isoformat(),
        },
        'sentences': sentences,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Сохранено {len(sentences)} предложений в {output_path}")
    return 0


if __name__ == '__main__':
    exit(main())