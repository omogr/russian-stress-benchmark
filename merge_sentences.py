#!/usr/bin/env python3
"""
merge_sentences.py

Читает входной текстовый файл, объединяет подряд идущие непустые строки
в чанки не больше заданного размера и сохраняет в JSON-файл.

Использование:
    python merge_sentences.py input.txt -o sentences.json -m 500
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Объединение строк в чанки заданного размера'
    )
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument(
        '-o', '--output',
        default='sentences.json',
        help='Выходной JSON-файл (default: sentences.json)'
    )
    parser.add_argument(
        '-m', '--max-chunk-size',
        type=int,
        default=500,
        help='Максимальный размер чанка в символах (default: 500)'
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] Файл не найден: {input_path}")
        return 1

    # Читаем все непустые строки
    lines = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for raw_text in f:
            entry = raw_text.strip()
            if entry:
                lines.append(entry)

    # Объединяем подряд идущие строки в чанки
    sentences = []
    current_chunk = ""
    for line in lines:
        if not current_chunk:
            current_chunk = line
        elif len(current_chunk) + 1 + len(line) <= args.max_chunk_size:
            current_chunk += " " + line
        else:
            sentences.append({'text': current_chunk})
            current_chunk = line

    if current_chunk:
        sentences.append({'text': current_chunk})

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

    print(f"Сохранено {len(sentences)} чанков в {output_path}")
    return 0


if __name__ == '__main__':
    exit(main())