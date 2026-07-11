#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для формирования отчёта о сравнении библиотек расстановки ударений.

Читает JSON-файл с результатами сравнения и генерирует Markdown-отчёт,
группируя данные по параметрам для удобного сравнения библиотек.

Использование:
    python generate_report.py input_results.json [output_report.md]

Если выходной файл не указан, отчёт сохраняется как report.md
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List


def load_json(filepath: str) -> Dict[str, Any]:
    """Загружает JSON-файл."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_number(value: Any) -> str:
    """Форматирует число для вывода в таблицу."""
    if isinstance(value, float):
        # Для времени — 4 знака после запятой, для процентов — 2
        return f"{value:.4f}"
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return str(value)


def format_percent(numerator: int, denominator: int) -> str:
    """Вычисляет и форматирует процент."""
    if denominator == 0:
        return "—"
    return f"{numerator / denominator * 100:.2f}%"


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Генерирует Markdown-отчёт из данных сравнения."""

    metadata = data.get("metadata", {})
    library_results = data.get("library_results", {})
    libraries = metadata.get("libraries_compared", [])

    lines = []

    # ─── Заголовок ───
    lines.append("# Отчёт о сравнении библиотек расстановки ударений")
    lines.append("")
    lines.append("> Автоматически сгенерированный отчёт на основе сравнения результатов работы библиотек с ручной разметкой.")
    lines.append("")

    # ─── Общая информация ───
    lines.append("## Общая информация")
    lines.append("")

    timestamp = metadata.get("timestamp", "не указана")
    total_sentences = metadata.get("total_sentences", 0)
    gold_file = metadata.get("gold_file", "не указан")

    lines.append(f"| Параметр | Значение |")
    lines.append(f"|----------|----------|")
    lines.append(f"| Дата тестирования | `{timestamp}` |")
    lines.append(f"| Тестовый набор (предложений) | **{format_number(total_sentences)}** |")
    lines.append(f"| Эталонный файл (gold) | `{gold_file}` |")
    lines.append(f"| Число сравниваемых библиотек | **{len(libraries)}** |")
    lines.append("")

    lines.append("### Сравниваемые библиотеки")
    lines.append("")
    for i, lib in enumerate(libraries, 1):
        lines.append(f"{i}. `{lib}`")
    lines.append("")

    # ─── Performance ───
    lines.append("## Производительность")
    lines.append("")
    lines.append("Сравнение времени загрузки, обработки и стабильности работы библиотек.")
    lines.append("")

    lines.append("| Библиотека | Загрузка (сек) | Обработка (сек) | Исключения |")
    lines.append("|------------|---------------|-----------------|------------|")

    perf_data = []
    for lib in libraries:
        result = library_results.get(lib, {})
        meta = result.get("metadata", {})
        perf = meta.get("performance", {})

        load_time = perf.get("load_time_seconds", 0)
        process_time = perf.get("total_process_time_seconds", 0)
        exceptions = perf.get("exception_count", 0)

        perf_data.append({
            "library": lib,
            "load_time": load_time,
            "process_time": process_time,
            "exceptions": exceptions
        })

        exc_str = f"**{exceptions}** ❌" if exceptions > 0 else f"{exceptions} ✅"
        lines.append(f"| `{lib}` | {format_number(load_time)} | {format_number(process_time)} | {exc_str} |")

    lines.append("")

    # Добавим суммарную статистику по performance
    if perf_data:
        total_load = sum(d["load_time"] for d in perf_data)
        total_process = sum(d["process_time"] for d in perf_data)
        total_exceptions = sum(d["exceptions"] for d in perf_data)
        lines.append(f"**Итого:** загрузка — {format_number(total_load)} сек, обработка — {format_number(total_process)} сек, исключений — {total_exceptions}")
        lines.append("")

    # ─── Ошибки в результатах ───
    lines.append("## Ошибки в результатах работы библиотек")
    lines.append("")
    lines.append("Сравнение качества расстановки ударений и сопоставления слов с эталоном.")
    lines.append("")

    lines.append("| Библиотека | Ошибки ударений | Пропущенные ударения | Несовпадение по кол-ву слов | Несовпадение по тексту слов | Предложения с несовпадениями |")
    lines.append("|------------|-----------------|----------------------|-----------------------------|----------------------------|------------------------------|")

    error_data = []
    for lib in libraries:
        result = library_results.get(lib, {})

        stress_errors = result.get("total_stress_errors", 0)
        missing_stress = result.get("total_missing_stress", 0)
        unmatched_count = result.get("total_unmatched_words_different_count", 0)
        unmatched_text = result.get("total_unmatched_words_same_count_diff_text", 0)
        sentences_unmatched = result.get("sentences_with_unmatched_words", 0)

        error_data.append({
            "library": lib,
            "stress_errors": stress_errors,
            "missing_stress": missing_stress,
            "unmatched_count": unmatched_count,
            "unmatched_text": unmatched_text,
            "sentences_unmatched": sentences_unmatched
        })

        lines.append(
            f"| `{lib}` | {format_number(stress_errors)} | {format_number(missing_stress)} | "
            f"{format_number(unmatched_count)} | {format_number(unmatched_text)} | {format_number(sentences_unmatched)} |"
        )

    lines.append("")

    # Добавим итоги по ошибкам
    if error_data:
        total_stress_err = sum(d["stress_errors"] for d in error_data)
        total_missing = sum(d["missing_stress"] for d in error_data)
        total_unmatched_c = sum(d["unmatched_count"] for d in error_data)
        total_unmatched_t = sum(d["unmatched_text"] for d in error_data)
        total_sent_unm = sum(d["sentences_unmatched"] for d in error_data)
        lines.append(f"**Итого по всем библиотекам:** ошибки ударений — {format_number(total_stress_err)}, пропущенные — {format_number(total_missing)}, несовпадение по кол-ву — {format_number(total_unmatched_c)}, несовпадение по тексту — {format_number(total_unmatched_t)}, предложения с несовпадениями — {format_number(total_sent_unm)}")
        lines.append("")

    # ─── Common Words ───
    lines.append("## Сравнение по общим словам (common words)")
    lines.append("")
    lines.append("Слова, которые были успешно размечены **всеми** сравниваемыми библиотеками. Это позволяет сравнивать качество на равных условиях.")
    lines.append("")

    lines.append("| Библиотека | Всего общих слов | Ошибки ударений | Точность (accuracy) |")
    lines.append("|------------|------------------|-----------------|---------------------|")

    common_data = []
    for lib in libraries:
        result = library_results.get(lib, {})
        common = result.get("common_words", {})

        total_common = common.get("total_common_words_with_stress", 0)
        stress_err_common = common.get("stress_errors_on_common_words", 0)
        accuracy = format_percent(total_common - stress_err_common, total_common) if total_common > 0 else "—"

        common_data.append({
            "library": lib,
            "total_common": total_common,
            "stress_err": stress_err_common,
            "accuracy": accuracy
        })

        lines.append(f"| `{lib}` | {format_number(total_common)} | {format_number(stress_err_common)} | {accuracy} |")

    lines.append("")

    # Проверка: total_common_words_with_stress должен быть одинаковым
    common_totals = set(d["total_common"] for d in common_data)
    if len(common_totals) == 1:
        lines.append(f"✅ Общее число слов, размеченных всеми библиотеками: **{format_number(list(common_totals)[0])}** (совпадает у всех библиотек).")
    else:
        lines.append(f"⚠️ Внимание: общее число слов различается между библиотеками: {', '.join(str(c) for c in sorted(common_totals))}")
    lines.append("")

    # ─── Детальная сводка по каждой библиотеке ───
    lines.append("## Детальная сводка по библиотекам")
    lines.append("")

    for lib in libraries:
        result = library_results.get(lib, {})
        meta = result.get("metadata", {})
        perf = meta.get("performance", {})
        common = result.get("common_words", {})

        total_words = meta.get("total_matched_word_pairs", 0)
        gold_words = meta.get("total_gold_words_with_stress", 0)

        lines.append(f"### `{lib}`")
        lines.append("")
        lines.append(f"- **Обработано предложений:** {format_number(meta.get('total_sentences_processed', 0))}")
        lines.append(f"- **Сопоставлено слов с эталоном:** {format_number(total_words)}")
        lines.append(f"- **Слов с ударением в эталоне:** {format_number(gold_words)}")
        lines.append(f"- **Время загрузки:** {format_number(perf.get('load_time_seconds', 0))} сек")
        lines.append(f"- **Время обработки:** {format_number(perf.get('total_process_time_seconds', 0))} сек")
        lines.append(f"- **Исключений:** {perf.get('exception_count', 0)}")
        lines.append("")
        lines.append("**Ошибки:**")
        lines.append(f"- Неправильно расставленные ударения: **{format_number(result.get('total_stress_errors', 0))}**")
        lines.append(f"- Пропущенные ударения: **{format_number(result.get('total_missing_stress', 0))}**")
        lines.append(f"- Несовпадение по количеству слов: **{format_number(result.get('total_unmatched_words_different_count', 0))}**")
        lines.append(f"- Несовпадение по тексту слов: **{format_number(result.get('total_unmatched_words_same_count_diff_text', 0))}**")
        lines.append(f"- Предложения с несовпадениями: **{format_number(result.get('sentences_with_unmatched_words', 0))}**")
        lines.append("")

        total_common = common.get("total_common_words_with_stress", 0)
        stress_err = common.get("stress_errors_on_common_words", 0)
        if total_common > 0:
            acc = (total_common - stress_err) / total_common * 100
            lines.append(f"**Common words:** {format_number(total_common)} слов, ошибок: {format_number(stress_err)}, точность: **{acc:.2f}%**")
        lines.append("")

    # ─── Футер ───
    lines.append("---")
    lines.append("")
    lines.append(f"*Отчёт сгенерирован: {datetime.now().isoformat()}*")
    lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Использование: python generate_report.py <input.json> [output.md]")
        print("  input.json  — файл с результатами сравнения")
        print("  output.md   — файл для сохранения отчёта (по умолчанию: report.md)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "report.md"

    if not os.path.exists(input_file):
        print(f"Ошибка: файл не найден: {input_file}")
        sys.exit(1)

    print(f"Загрузка данных из: {input_file}")
    data = load_json(input_file)

    print("Генерация отчёта...")
    report = generate_markdown_report(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Отчёт сохранён в: {output_file}")
    print(f"Размер: {len(report)} символов")


if __name__ == "__main__":
    main()