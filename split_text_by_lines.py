#!/usr/bin/env python3
"""
split_text_by_lines.py

Читает входной текстовый файл, разбивает его на предложения и сохраняет в JSON-файл.

Использование:
    python split_text_by_lines.py input.txt -o sentences.json
"""

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Console encoding fix for Windows
# ---------------------------------------------------------------------------

def _fix_windows_console():
    """
    На Windows консоль по умолчанию использует cp866 (или cp1251).
    Python 3.6+ пишет в stdout как utf-8, что приводит к кракозябрам или
    UnicodeEncodeError при выводе русского текста.

    Эта функция:
    1. Пытается переключить консоль в UTF-8 (chcp 65001)
    2. Перенастраивает stdout/stderr на utf-8
    3. Если не получится — переключает stdout в режим "replace",
       чтобы программа не падала, а кракозябры заменялись на ?
    """
    if sys.platform != 'win32':
        return

    try:
        # Пробуем переключить консоль Windows в UTF-8
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # SetConsoleOutputCP(65001) = UTF-8
        kernel32.SetConsoleOutputCP(65001)
        # SetConsoleCP(65001) = UTF-8 для ввода
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass  # Если не получилось — не страшно, попробуем дальше

    try:
        # Python 3.7+: перенастраиваем stdout/stderr
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


# Вызываем сразу при импорте, до любых print
_fix_windows_console()


# ---------------------------------------------------------------------------
# Logging helper — пишем ВСЕГДА в файл, в консоль только если получится
# ---------------------------------------------------------------------------

class SafeLogger:
    """
    Безопасный логгер: всегда пишет в файл (UTF-8),
    в консоль пишет только если кодировка совместима.
    """
    def __init__(self, log_file: Path = None):
        self.log_file = log_file
        self._file_handle = None
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(log_file, 'a', encoding='utf-8')
            self._file_handle.write(f"\n--- Log started at {datetime.now().isoformat()} ---\n")

    def _write(self, level: str, msg: str):
        line = f"[{level}] {msg}"
        # 1. Всегда пишем в файл
        if self._file_handle:
            self._file_handle.write(line + "\n")
            self._file_handle.flush()
        # 2. Пробуем писать в консоль
        try:
            print(line)
        except UnicodeEncodeError:
            # Если консоль не принимает UTF-8 — пишем ASCII fallback
            safe = line.encode('ascii', 'replace').decode('ascii')
            print(safe)

    def info(self, msg: str):
        self._write("INFO", msg)

    def error(self, msg: str):
        self._write("ERROR", msg)

    def close(self):
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Разбиение текста по строкам'
    )
    parser.add_argument('input_file', help='Входной текстовый файл')
    parser.add_argument(
        '-o', '--output',
        default='sentences.json',
        help='Выходной JSON-файл (default: sentences.json)'
    )
    parser.add_argument(
        '--log',
        default=None,
        help='Файл для логов (если не указан — логи только в консоль)'
    )
    args = parser.parse_args()

    log_file = Path(args.log) if args.log else None
    logger = SafeLogger(log_file)

    try:
        input_path = Path(args.input_file)
        if not input_path.exists():
            logger.error(f"Файл не найден: {input_path}")
            return 1

        output_path = Path(args.output)
        logger.info(f"Разбиение текста: {input_path} -> {output_path}")

        # --- Чтение файла с автоопределением кодировки ---
        # Если файл не в UTF-8, пробуем cp1251, затем cp866
        text = None
        encodings = ['utf-8', 'cp1251', 'cp866', 'koi8-r', 'iso-8859-5']
        for enc in encodings:
            try:
                with open(input_path, 'r', encoding=enc) as f:
                    text = f.read()
                logger.info(f"Файл прочитан в кодировке {enc}")
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            logger.error(f"Не удалось прочитать файл ни в одной из кодировок: {encodings}")
            return 1

        sentences = []
        for raw_text in text.splitlines():
            entry = raw_text.strip()
            if entry:
                sentences.append({'text': entry})

        result = {
            'metadata': {
                'source_file': str(input_path),
                'sentence_count': len(sentences),
                'timestamp': datetime.now().isoformat(),
            },
            'sentences': sentences,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"Сохранено {len(sentences)} предложений в {output_path}")
        return 0

    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        traceback_str = traceback.format_exc()
        logger.error(traceback_str)
        return 1
    finally:
        logger.close()


if __name__ == '__main__':
    exit(main())