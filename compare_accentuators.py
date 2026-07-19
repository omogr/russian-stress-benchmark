#!/usr/bin/env python3
"""
Скрипт сравнения результатов работы библиотек расстановки ударений
с ручной разметкой (GOLD).

Использование:
    python compare_accentuators.py <input_dir> [-o output.json]

В <input_dir> должны находиться:
    - GOLD_results.json          — эталонная ручная разметка
    - <library>_results.json     — результаты работы библиотек

Результат сохраняется в JSON-файл (по умолчанию comparison_results.json).
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_vowels(word: str) -> list[str]:
    """Возвращает список гласных букв слова в порядке следования."""
    return [ch for ch in word if ch in VOWELS]

def compare_strings(str1, str2):
    # Приводим к нижнему регистру и заменяем 'ё' на 'е'
    normalized1 = str1.lower().replace('ё', 'е')
    normalized2 = str2.lower().replace('ё', 'е')
    
    return normalized1 == normalized2

def should_have_stress(word: str) -> bool:
    """
    Определяет, обязано ли слово иметь проставленное ударение.
    Ударение не требуется, если:
      • в слове меньше двух гласных;
      • в слове присутствует буква «ё» / «Ё».
    """
    vowels = get_vowels(word)
    if len(vowels) < 2:
        return False
    if "ё" in word or "Ё" in word:
        return False
    return True


def should_have_stress_info(word_info: dict) -> bool:
    """
    Определяет, обязано ли слово иметь проставленное ударение.
    Ударение не требуется, если:
      • в слове меньше двух гласных;
      • в слове присутствует буква «ё» / «Ё».
    """
    word = word_info["text"]
    vowels = get_vowels(word)
    if len(vowels) < 2:
        return False
    if "ё" in word or "Ё" in word:
        return False
        
    if "-" in word:
        return False
        
    if word_info.get("start") is None:
        return False
        
    if word_info.get("stress_char_index") is None:
        return False
    return True


# ---------------------------------------------------------------------------
# Сопоставление слов
# ---------------------------------------------------------------------------
'''
def match_words(
    gold_words: list[dict],
    lib_words: list[dict],
) -> tuple[list[tuple[int, int]], int, int, bool]:
    """
    Сопоставляет слова из GOLD и библиотеки.

    Возвращает кортеж:
      1. matched_pairs — список (gold_idx, lib_idx) для сопоставленных слов;
      2. unmatched_diff_count — число несопоставленных слов в предложениях,
         где количество слов НЕ совпало с GOLD;
      3. unmatched_same_count_diff_text — число несопоставленных слов
         в предложениях, где количество слов совпало, но тексты не совпали;
      4. has_unmatched — True, если в предложении есть несопоставленные слова.
    """
    # Если у одной из сторон нет разбиения на слова — всё несопоставлено
    if not gold_words or not lib_words:
        total = (len(gold_words) if gold_words else 0) + (len(lib_words) if lib_words else 0)
        return [], total, 0, total > 0

    # Полное совпадение по длине и текстам
    if len(gold_words) == len(lib_words):
        all_match = all(compare_strings(gw["text"], lw["text"]) for gw, lw in zip(gold_words, lib_words))
        if all_match:
            pairs = [(i, i) for i in range(len(gold_words))]
            return pairs, 0, 0, False

    # Частичное совпадение: префикс + суффикс
    g_len, l_len = len(gold_words), len(lib_words)

    prefix = 0
    for i in range(min(g_len, l_len)):
        if compare_strings(gold_words[i]["text"], lib_words[i]["text"]):
            prefix += 1
        else:
            break

    suffix = 0
    max_suffix = min(g_len - prefix, l_len - prefix)
    for i in range(1, max_suffix + 1):
        if compare_strings(gold_words[-i]["text"], lib_words[-i]["text"]):
            suffix += 1
        else:
            break

# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_vowels(word: str) -> list[str]:
    """Возвращает список гласных букв слова в порядке следования."""
    return [ch for ch in word if ch in VOWELS]


def should_have_stress(word: str) -> bool:
    """
    Определяет, обязано ли слово иметь проставленное ударение.
    Ударение не требуется, если:
      • в слове меньше двух гласных;
      • в слове присутствует буква «ё» / «Ё».
    """
    vowels = get_vowels(word)
    if len(vowels) < 2:
        return False
    if "ё" in word or "Ё" in word:
        return False
    return True


def should_have_stress_info(word_info: dict) -> bool:
    """
    Определяет, обязано ли слово иметь проставленное ударение.
    Ударение не требуется, если:
      • в слове меньше двух гласных;
      • в слове присутствует буква «ё» / «Ё».
    """
    word = word_info["text"]
    vowels = get_vowels(word)
    if len(vowels) < 2:
        return False
    if "ё" in word or "Ё" in word:
        return False
        
    if "-" in word:
        return False
        
    if word_info.get("start") is None:
        return False
        
    if word_info.get("stress_char_index") is None:
        return False
    return True

'''

# ---------------------------------------------------------------------------
# Сопоставление слов
# ---------------------------------------------------------------------------

def match_words(
    gold_words: list[dict],
    lib_words: list[dict],
) -> tuple[list[tuple[int, int]], int, int, bool]:
    """
    Сопоставляет слова из GOLD и библиотеки.

    Возвращает кортеж:
      1. matched_pairs — список (gold_idx, lib_idx) для сопоставленных слов;
      2. unmatched_diff_count — число несопоставленных слов в предложениях,
         где количество слов НЕ совпало с GOLD;
      3. unmatched_same_count_diff_text — число несопоставленных слов
         в предложениях, где количество слов совпало, но тексты не совпали;
      4. has_unmatched — True, если в предложении есть несопоставленные слова.
    """
    # Если у одной из сторон нет разбиения на слова — всё несопоставлено
    if not gold_words or not lib_words:
        total = (len(gold_words) if gold_words else 0) + (len(lib_words) if lib_words else 0)
        return [], total, 0, total > 0

    # Полное совпадение по длине и текстам
    if len(gold_words) == len(lib_words):
        all_match = all(compare_strings(gw["text"], lw["text"]) for gw, lw in zip(gold_words, lib_words))
        if all_match:
            pairs = [(i, i) for i in range(len(gold_words))]
            return pairs, 0, 0, False

    # Частичное совпадение: префикс + суффикс
    g_len, l_len = len(gold_words), len(lib_words)

    prefix = 0
    for i in range(min(g_len, l_len)):
        if compare_strings(gold_words[i]["text"], lib_words[i]["text"]):
            prefix += 1
        else:
            break

    suffix = 0
    max_suffix = min(g_len - prefix, l_len - prefix)
    for i in range(1, max_suffix + 1):
        if compare_strings(gold_words[-i]["text"], lib_words[-i]["text"]):
            suffix += 1
        else:
            break

    # Формируем пары, избегая пересечения префикса и суффикса
    pairs = []
    seen_gold = set()
    for i in range(prefix):
        pairs.append((i, i))
        seen_gold.add(i)
    for i in range(1, suffix + 1):
        g_idx = g_len - i
        if g_idx not in seen_gold:
            pairs.append((g_idx, l_len - i))
            seen_gold.add(g_idx)

    matched_gold = {g for g, _ in pairs}
    matched_lib = {l for _, l in pairs}

    unmatched_gold = [i for i in range(g_len) if i not in matched_gold]
    unmatched_lib = [i for i in range(l_len) if i not in matched_lib]
    total_unmatched = len(unmatched_gold) + len(unmatched_lib)

    if g_len != l_len:
        return pairs, total_unmatched, 0, total_unmatched > 0
    else:
        return pairs, 0, total_unmatched, total_unmatched > 0


def get_stress_pos(word_info: dict) -> int:
    if "stress_char_index" not in word_info:
        return None
    stress_char_index = word_info.get("stress_char_index")
    if stress_char_index is None:
        return None
    #start_index = word_info.get("start")
    #if start_index is None:
    #    return None
    return stress_char_index # - start_index


# ---------------------------------------------------------------------------
# Сравнение одного предложения
# ---------------------------------------------------------------------------

def compare_sentence(
    gold_sent: dict,
    lib_sent: dict,
) -> dict:
    """
    Сравнивает одно предложение из GOLD и библиотеки.
    Возвращает словарь с детальной информацией по предложению.
    """
    result = {
        "sentence_index": None,
        "original_text": gold_sent.get("original_text"),
        "gold_word_count": 0,
        "lib_word_count": 0,
        "matched_word_pairs": 0,
        "unmatched_words_different_count": 0,
        "unmatched_words_same_count_diff_text": 0,
        "has_unmatched_words": False,
        "stress_errors": 0,
        "missing_stress": 0,
        "gold_words_with_stress": 0,
        "lib_error": False,
        "gold_error": False,
        "matched_pairs": [],
        "checked_pairs": [],
        "error_pairs": [],
        "missing_pairs": [],
    }

    gold_words = gold_sent.get("words") or []
    lib_words = lib_sent.get("words") or []

    result["gold_word_count"] = len(gold_words)
    result["lib_word_count"] = len(lib_words)

    if gold_sent.get("errors"):
        result["gold_error"] = True
    if lib_sent.get("errors"):
        result["lib_error"] = True

    # При ошибке в предложении сопоставление слов невозможно
    if result["gold_error"] or result["lib_error"]:
        return result

    pairs, un_diff, un_same, has_unm = match_words(gold_words, lib_words)
    result["matched_pairs"] = pairs
    result["matched_word_pairs"] = len(pairs)
    result["unmatched_words_different_count"] = un_diff
    result["unmatched_words_same_count_diff_text"] = un_same
    result["has_unmatched_words"] = has_unm

    # Сравниваем ударения только для сопоставленных слов
    for g_idx, l_idx in pairs:
        gw = gold_words[g_idx]
        lw = lib_words[l_idx]

        gold_stress = get_stress_pos(gw)
        lib_stress = get_stress_pos(lw)
        


        #if should_have_stress(gw["text"]):
        if should_have_stress_info(gw):
            result["gold_words_with_stress"] += 1

            if gold_stress is not None and lib_stress is None:
                # Библиотека не проставила ударение, хотя должна была
                result["missing_stress"] += 1

                result["missing_pairs"].append(
                    {
                        "gold": gw,
                        "lib": lw,
                    }
                )
            else:
                result["checked_pairs"].append((g_idx, l_idx))
                if gold_stress != lib_stress:
                    # Ударение проставлено, но на другую позицию
                    result["stress_errors"] += 1
                    result["error_pairs"].append(
                        {
                            "gold": gw,
                            "lib": lw,
                        }
                    )
            # else: ударения совпадают — ошибки нет

    return result


# ---------------------------------------------------------------------------
# Главная логика
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Сравнение результатов расстановки ударений с GOLD-разметкой"
    )
    parser.add_argument("input_dir", help="Директория с JSON-файлами результатов")
    parser.add_argument(
        "-o", "--output", default="comparison_results.json",
        help="Имя выходного JSON-файла (по умолчанию: comparison_results.json)"
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"Ошибка: {input_dir} не является директорией", file=sys.stderr)
        sys.exit(1)

    # --- Загрузка GOLD ------------------------------------------------------
    gold_path = input_dir / "GOLD_results.json"
    if not gold_path.exists():
        print(f"Ошибка: не найден эталонный файл {gold_path}", file=sys.stderr)
        sys.exit(1)

    gold_data = load_json(gold_path)
    gold_sentences = gold_data.get("sentences", [])

    # --- Загрузка библиотек -------------------------------------------------
    result_files = sorted(input_dir.glob("*_results.json"))
    library_files = [f for f in result_files if f.name != "GOLD_results.json"]

    if not library_files:
        print("Ошибка: не найдено файлов результатов библиотек", file=sys.stderr)
        sys.exit(1)
        
    performance = {}

    libraries: dict[str, list[dict]] = {}
    for lib_path in library_files:
        lib_data = load_json(lib_path)
        lib_name = lib_data["metadata"]["library_name"]
        libraries[lib_name] = lib_data.get("sentences", [])
        
        performance[lib_name] = {
            "load_time_seconds": lib_data.get("metadata", {}).get("load_time_seconds", 0.0),
            "total_process_time_seconds": lib_data.get("metadata", {}).get(
                "total_process_time_seconds", 0.0
            ),
            "exception_count": sum(
                1 for sent in libraries[lib_name] if sent.get("errors")
            ),
        }

    # --- Попарное сравнение каждой библиотеки с GOLD ------------------------
    all_per_sentence: dict[str, list[dict]] = {}
    all_matched_pairs: dict[str, list[list[tuple[int, int]]]] = {}

    for lib_name, lib_sentences in libraries.items():
        per_sentence = []
        sent_matched_pairs = []

        max_sent = max(len(gold_sentences), len(lib_sentences))
        for sent_idx in range(max_sent):
            gold_sent = gold_sentences[sent_idx] if sent_idx < len(gold_sentences) else None
            lib_sent = lib_sentences[sent_idx] if sent_idx < len(lib_sentences) else None

            if gold_sent is None or lib_sent is None:
                # Несовпадение по числу предложений
                sent_result = {
                    "sentence_index": sent_idx,
                    "original_text": gold_sent.get("original_text") if gold_sent else None,
                    "gold_word_count": len(gold_sent.get("words") or []) if gold_sent else 0,
                    "lib_word_count": len(lib_sent.get("words") or []) if lib_sent else 0,
                    "matched_word_pairs": 0,
                    "unmatched_words_different_count": 0,
                    "unmatched_words_same_count_diff_text": 0,
                    "has_unmatched_words": True,
                    "stress_errors": 0,
                    "missing_stress": 0,
                    "gold_words_with_stress": 0,
                    "lib_error": lib_sent is None or bool(lib_sent.get("errors")) if lib_sent else True,
                    "gold_error": gold_sent is None or bool(gold_sent.get("errors")) if gold_sent else True,
                    "matched_pairs": [],
                }
                # Все слова считаем несопоставленными из-за разного количества
                if gold_sent is None:
                    sent_result["unmatched_words_different_count"] = sent_result["lib_word_count"]
                elif lib_sent is None:
                    sent_result["unmatched_words_different_count"] = sent_result["gold_word_count"]
                else:
                    sent_result["unmatched_words_different_count"] = (
                        sent_result["gold_word_count"] + sent_result["lib_word_count"]
                    )
                per_sentence.append(sent_result)
                sent_matched_pairs.append([])
            else:
                sent_result = compare_sentence(gold_sent, lib_sent)
                sent_result["sentence_index"] = sent_idx
                per_sentence.append(sent_result)
                sent_matched_pairs.append(sent_result["checked_pairs"]) # sent_result["matched_pairs"])

        all_per_sentence[lib_name] = per_sentence
        all_matched_pairs[lib_name] = sent_matched_pairs

    # --- Поиск слов, сопоставленных во ВСЕХ библиотеках --------------------
    common_words: Optional[set[tuple[int, int]]] = None

    for lib_name, sent_matched in all_matched_pairs.items():
        lib_matched = set()
        for sent_idx, pairs in enumerate(sent_matched):
            for g_idx, _ in pairs:
                lib_matched.add((sent_idx, g_idx))
        if common_words is None:
            common_words = lib_matched
        else:
            common_words &= lib_matched

    if common_words is None:
        common_words = set()

    # --- Формирование итоговой статистики -----------------------------------
    output = {
        "metadata": {
            "gold_file": str(gold_path.name),
            "libraries_compared": sorted(libraries.keys()),
            "total_sentences": len(gold_sentences),
            "timestamp": datetime.now().isoformat(),
        },
        "library_results": {},
    }
    
    #sentence_errors = {}

    for lib_name in sorted(libraries.keys()):
        lib_comparison = all_per_sentence[lib_name]
        lib_sentences = libraries[lib_name]

        total_stress_errors = 0
        total_missing_stress = 0
        total_unmatched_diff = 0
        total_unmatched_same = 0
        sentences_with_unmatched = 0
        total_matched_pairs = 0
        total_gold_words_with_stress = 0

        # Метрики только по общим (всеми размеченным) словам
        common_stress_errors = 0
        common_missing_stress = 0
        common_gold_words_with_stress = 0
        
        #sum_all_errors = []

        for sent_idx, sent_result in enumerate(lib_comparison):
            total_stress_errors += sent_result["stress_errors"]
            total_missing_stress += sent_result["missing_stress"]
            total_unmatched_diff += sent_result["unmatched_words_different_count"]
            total_unmatched_same += sent_result["unmatched_words_same_count_diff_text"]
            if sent_result["has_unmatched_words"]:
                sentences_with_unmatched += 1
            total_matched_pairs += sent_result["matched_word_pairs"]
            total_gold_words_with_stress += sent_result["gold_words_with_stress"]
            
            #error_pairs = sent_result.get("error_pairs")
            #if error_pairs:
            #    sum_all_errors.extend(error_pairs)
            #    if sent_idx not in sentence_errors:
            #        sentence_errors[sent_idx] = {}
            #    if lib_name not in sentence_errors[sent_idx]:
            #        sentence_errors[sent_idx][lib_name] = error_pairs

            # Подсчёт по общим словам
            for g_idx, l_idx in sent_result.get("matched_pairs", []):
                if (sent_idx, g_idx) not in common_words:
                    continue

                gw = gold_sentences[sent_idx]["words"][g_idx]
                lw = lib_sentences[sent_idx]["words"][l_idx]

                if should_have_stress_info(gw):
                    common_gold_words_with_stress += 1
                    gold_stress = get_stress_pos(gw)
                    lib_stress = get_stress_pos(lw)

                    if gold_stress is not None and lib_stress is None:
                        common_missing_stress += 1
                    elif gold_stress != lib_stress:
                        # Ударение проставлено, но на другую позицию
                        common_stress_errors += 1

        output["library_results"][lib_name] = {
            "metadata": {
                "library_name": lib_name,
                "total_sentences_processed": len(lib_comparison),
                "total_matched_word_pairs": total_matched_pairs,
                "total_gold_words_with_stress": total_gold_words_with_stress,
                "performance": performance.get(lib_name, {})
            },
            "total_stress_errors": total_stress_errors,
            "total_missing_stress": total_missing_stress,
            "total_unmatched_words_different_count": total_unmatched_diff,
            "total_unmatched_words_same_count_diff_text": total_unmatched_same,
            "sentences_with_unmatched_words": sentences_with_unmatched,
            "common_words": {
                "total_common_words_with_stress": common_gold_words_with_stress,
                "stress_errors_on_common_words": common_stress_errors,
                "missing_stress_on_common_words": common_missing_stress,
            },
            "per_sentence": lib_comparison,
        }
        
        #print('sum_all_errors', lib_name, len(sum_all_errors))
        #with open(f"{lib_name}_errors.json", "w", encoding="utf-8") as f:
        #    json.dump(sum_all_errors, f, ensure_ascii=False, indent=2)

    for lib_name in sorted(libraries.keys()):
        lib_comparison = output["library_results"].get(lib_name, {}).get("per_sentence", {})
        
        for ts in lib_comparison:
            if "matched_pairs" in ts:
                ts["matched_pairs"] = len(ts["matched_pairs"])
            if "checked_pairs" in ts:
                ts["checked_pairs"] = len(ts["checked_pairs"])

    # --- Сохранение --------------------------------------------------------
    output_path = args.output # input_dir / 
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Результаты сохранены в {output_path}")
    '''
    common_errors = {}
    for sent_idx, value in sentence_errors.items():
        for lib_name, word_list in value.items():
            for tw in word_list:
                word_text = tw["gold"]["text"]
                key = (sent_idx, word_text)
                if sent_idx not in common_errors:
                    common_errors[sent_idx] = {}
                if word_text not in common_errors[sent_idx]:
                    common_errors[sent_idx][word_text] = {}
                common_errors[sent_idx][word_text][lib_name] = (tw["gold"]["start"], tw["gold"]["stress_char_index"])
    
    error_sentences = []
    for sent_idx, ts in enumerate(gold_data.get("sentences", [])):
        if sent_idx not in common_errors:
            continue
            
        err_words = []
        for word_text in common_errors[sent_idx]:
            if "ruaccent_turbo" not in common_errors[sent_idx][word_text]:
                continue
            if "wiki_enhancer" not in common_errors[sent_idx][word_text]:
                continue
            err_words.append(word_text)

        ts["words"] = []
        if err_words:
            error_sentences.append((sent_idx, err_words, ts["accented_text"]))

    output_path = "errors.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(error_sentences, f, ensure_ascii=False, indent=2)
    '''

if __name__ == "__main__":
    main()