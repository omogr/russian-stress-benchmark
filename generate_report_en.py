#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for generating a report comparing stress placement libraries.

Reads a JSON file with comparison results and generates a Markdown report,
grouping data by parameters for easy library comparison.

Usage:
    python generate_report_en.py input_results.json [output_report.md]

If the output file is not specified, the report is saved as report.md
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List


def load_json(filepath: str) -> Dict[str, Any]:
    """Loads a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_number(value: Any) -> str:
    """Formats a number for display in a table."""
    if isinstance(value, float):
        # For time — 4 decimal places, for percentages — 2
        return f"{value:.4f}"
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return str(value)


def format_percent(numerator: int, denominator: int) -> str:
    """Computes and formats a percentage."""
    if denominator == 0:
        return "—"
    return f"{numerator / denominator * 100:.2f}%"


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Generates a Markdown report from comparison data."""

    metadata = data.get("metadata", {})
    library_results = data.get("library_results", {})
    libraries = metadata.get("libraries_compared", [])

    lines = []

    # ─── Header ───
    lines.append("# Report on Stress Placement Library Comparison")
    lines.append("")
    lines.append("> Automatically generated report based on comparing library outputs against manual annotations.")
    lines.append("")

    # ─── General Information ───
    lines.append("## General Information")
    lines.append("")

    timestamp = metadata.get("timestamp", "not specified")
    total_sentences = metadata.get("total_sentences", 0)
    gold_file = metadata.get("gold_file", "not specified")

    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    lines.append(f"| Test date | `{timestamp}` |")
    lines.append(f"| Test set (sentences) | **{format_number(total_sentences)}** |")
    lines.append(f"| Gold standard file | `{gold_file}` |")
    lines.append(f"| Number of libraries compared | **{len(libraries)}** |")
    lines.append("")

    lines.append("### Compared Libraries")
    lines.append("")
    for i, lib in enumerate(libraries, 1):
        lines.append(f"{i}. `{lib}`")
    lines.append("")

    # ─── Performance ───
    lines.append("## Performance")
    lines.append("")
    lines.append("Comparison of loading time, processing time, and stability of the libraries.")
    lines.append("")

    lines.append("| Library | Load (sec) | Process (sec) | Exceptions |")
    lines.append("|---------|------------|---------------|------------|")

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

    # Add summary statistics for performance
    if perf_data:
        total_load = sum(d["load_time"] for d in perf_data)
        total_process = sum(d["process_time"] for d in perf_data)
        total_exceptions = sum(d["exceptions"] for d in perf_data)
        lines.append(f"**Total:** load — {format_number(total_load)} sec, process — {format_number(total_process)} sec, exceptions — {total_exceptions}")
        lines.append("")

    # ─── Errors in Results ───
    lines.append("## Errors in Library Outputs")
    lines.append("")
    lines.append("Comparison of stress placement quality and word matching against the gold standard.")
    lines.append("")

    lines.append("| Library | Stress Errors | Missing Stress | Word Count Mismatch | Word Text Mismatch | Sentences with Mismatches |")
    lines.append("|---------|---------------|----------------|---------------------|--------------------|---------------------------|")

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

    # Add error totals
    if error_data:
        total_stress_err = sum(d["stress_errors"] for d in error_data)
        total_missing = sum(d["missing_stress"] for d in error_data)
        total_unmatched_c = sum(d["unmatched_count"] for d in error_data)
        total_unmatched_t = sum(d["unmatched_text"] for d in error_data)
        total_sent_unm = sum(d["sentences_unmatched"] for d in error_data)
        lines.append(f"**Total across all libraries:** stress errors — {format_number(total_stress_err)}, missing — {format_number(total_missing)}, count mismatch — {format_number(total_unmatched_c)}, text mismatch — {format_number(total_unmatched_t)}, sentences with mismatches — {format_number(total_sent_unm)}")
        lines.append("")

    # ─── Common Words ───
    lines.append("## Comparison on Common Words")
    lines.append("")
    lines.append("Words that were successfully annotated by **all** compared libraries. This allows for quality comparison on equal terms.")
    lines.append("")

    lines.append("| Library | Total Common Words | Stress Errors | Accuracy |")
    lines.append("|---------|--------------------|---------------|----------|")

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

    # Check: total_common_words_with_stress should be the same across libraries
    common_totals = set(d["total_common"] for d in common_data)
    if len(common_totals) == 1:
        lines.append(f"✅ Total number of words annotated by all libraries: **{format_number(list(common_totals)[0])}** (matches across all libraries).")
    else:
        lines.append(f"⚠️ Warning: total number of words differs between libraries: {', '.join(str(c) for c in sorted(common_totals))}")
    lines.append("")

    # ─── Detailed Summary per Library ───
    lines.append("## Detailed Summary by Library")
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
        lines.append(f"- **Sentences processed:** {format_number(meta.get('total_sentences_processed', 0))}")
        lines.append(f"- **Words matched with gold standard:** {format_number(total_words)}")
        lines.append(f"- **Words with stress in gold standard:** {format_number(gold_words)}")
        lines.append(f"- **Load time:** {format_number(perf.get('load_time_seconds', 0))} sec")
        lines.append(f"- **Process time:** {format_number(perf.get('total_process_time_seconds', 0))} sec")
        lines.append(f"- **Exceptions:** {perf.get('exception_count', 0)}")
        lines.append("")
        lines.append("**Errors:**")
        lines.append(f"- Incorrectly placed stress: **{format_number(result.get('total_stress_errors', 0))}**")
        lines.append(f"- Missing stress: **{format_number(result.get('total_missing_stress', 0))}**")
        lines.append(f"- Word count mismatch: **{format_number(result.get('total_unmatched_words_different_count', 0))}**")
        lines.append(f"- Word text mismatch: **{format_number(result.get('total_unmatched_words_same_count_diff_text', 0))}**")
        lines.append(f"- Sentences with mismatches: **{format_number(result.get('sentences_with_unmatched_words', 0))}**")
        lines.append("")

        total_common = common.get("total_common_words_with_stress", 0)
        stress_err = common.get("stress_errors_on_common_words", 0)
        if total_common > 0:
            acc = (total_common - stress_err) / total_common * 100
            lines.append(f"**Common words:** {format_number(total_common)} words, errors: {format_number(stress_err)}, accuracy: **{acc:.2f}%**")
        lines.append("")

    # ─── Footer ───
    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated: {datetime.now().isoformat()}*")
    lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_report_en.py <input.json> [output.md]")
        print("  input.json  — file with comparison results")
        print("  output.md   — output file for the report (default: report.md)")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "report.md"

    if not os.path.exists(input_file):
        print(f"Error: file not found: {input_file}")
        sys.exit(1)

    print(f"Loading data from: {input_file}")
    data = load_json(input_file)

    print("Generating report...")
    report = generate_markdown_report(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"Report saved to: {output_file}")
    print(f"Size: {len(report)} characters")


if __name__ == "__main__":
    main()