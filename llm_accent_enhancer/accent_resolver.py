#!/usr/bin/env python3
"""
accent_resolver.py

Улучшенный модуль для разрешения неоднозначностей в расстановке ударений
с помощью локальной LLM.

Основные оптимизации:
- Данные из JSONL индексируются в памяти один раз (O(1) поиск).
- Промпт содержит только необходимую информацию (glosses — только при
  семантической неоднозначности с одинаковой морфологией).
- Результаты LLM кэшируются.
- Генерация ограничена 5 токенами, температура 0.1.

Использование с model_loader.py:
    from model_loader import model_loader
    resolver = AccentResolver(
        data_store=store,
        model=model_loader.generator_model,
        tokenizer=model_loader.generator_tokenizer
    )
"""

import json
import logging
import re
import sys
import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# -----------------------------------------------------------------------------
# Настройка логирования
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# -----------------------------------------------------------------------------
# Результат разрешения
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ResolutionResult:
    """Результат разрешения неоднозначности ударения."""

    resolved: bool
    group_id: Optional[int] = None
    accented_form: Optional[str] = None
    reason: Optional[str] = None

    @classmethod
    def not_found(cls) -> "ResolutionResult":
        return cls(resolved=False, reason="not_in_dictionary")

    @classmethod
    def ambiguous(cls) -> "ResolutionResult":
        return cls(resolved=False, reason="ambiguous")

    @classmethod
    def success(cls, group_id: int, accented_form: str) -> "ResolutionResult":
        return cls(resolved=True, group_id=group_id, accented_form=accented_form)


# -----------------------------------------------------------------------------
# Хранилище данных
# -----------------------------------------------------------------------------
class AccentDataStore:
    """Хранилище словоформ с неоднозначным ударением из JSONL."""

    def __init__(self, jsonl_path: Union[str, Path]):
        self._data: Dict[str, Tuple[Any, Any, List[Dict]]] = {}
        self._load(Path(jsonl_path))
        logger.info(f"AccentDataStore: загружено {len(self._data)} записей")

    # -------------------------------------------------------------------------
    def _load(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, list) or len(entry) < 3:
                        logger.warning(f"Пропуск строки {lineno}: неверная структура")
                        continue
                    form = entry[0]
                    self._data[self._normalize(form)] = entry
                except json.JSONDecodeError as exc:
                    logger.warning(f"Ошибка JSON в строке {lineno}: {exc}")

    # -------------------------------------------------------------------------
    @staticmethod
    def _normalize(word: str) -> str:
        """Ключ для поиска: нижний регистр, ё → е."""
        return word.casefold().replace("ё", "е")

    # -------------------------------------------------------------------------
    def lookup(self, word: str) -> Optional[Tuple[Any, Any, List[Dict]]]:
        """Вернуть запись [form, accent_options, groups] или None."""
        return self._data.get(self._normalize(word))

    # -------------------------------------------------------------------------
    def __contains__(self, word: str) -> bool:
        return self._normalize(word) in self._data


# -----------------------------------------------------------------------------
# Вспомогательные функции
# -----------------------------------------------------------------------------
def _flatten_tags(tags: List[Any]) -> List[str]:
    """Рекурсивно выравнивает вложенные списки тегов и убирает дубли."""
    out: List[str] = []
    for t in tags:
        if isinstance(t, list):
            out.extend(_flatten_tags(t))
        else:
            out.append(str(t))
    return list(dict.fromkeys(out))


def _lemma_signature(lemma_info: Dict) -> Tuple[str, Tuple[str, ...]]:
    """Сигнатура леммы для сравнения групп: (pos, теги)."""
    pos = lemma_info.get("pos", "")
    tags = tuple(_flatten_tags(lemma_info.get("tags", [])))
    return pos, tags


# -----------------------------------------------------------------------------
# Построитель промптов
# -----------------------------------------------------------------------------

# (названия как в ruwiktionary — на русском языке)
TARGET_TRANSLATION_LANGS = [
    "Английский", "Испанский", "Итальянский", "Немецкий", "Французский",
    "Китайский", "Корейский", "Португальский", "Японский", "Арабский"
]


class PromptBuilder:
    """
    Формирует промпт, где каждая уникальная лемма — отдельный вариант.
    После выбора леммы AccentResolver пересчитывает её в group_id.
    """

    SYSTEM_PROMPT0 = (
        "Ты — эксперт по русской орфоэпии. Определи правильное ударение в слове по контексту.\n"
        "Каждый вариант — это отдельная словарная статья (лемма) с её значением и грамматикой.\n"
        "Правила:\n"
        "1. Выбери вариант, который подходит по смыслу и грамматике контекста.\n"
        "2. Ответь ТОЛЬКО номером выбранного варианта.\n"
        "3. Если ни один вариант не подходит, контекст неясен или варианты неразличимы — ответь 0.\n"
        "4. Не угадывай. Лучше отказаться, чем ошибиться."
    )
    
    SYSTEM_PROMPT = (
        "Определи номер варианта, к которому можно отнести данное слово слово в контексте данного предложения.\n"
        "Каждый вариант — это отдельная словарная статья (лемма) с её значением и грамматикой.\n"
        "Правила:\n"
        "1. Выбери вариант, который подходит по смыслу и грамматике контекста.\n"
        "2. Ответь ТОЛЬКО номером выбранного варианта.\n"
        "3. Если информации недостаточно - ответь 0.\n"
        "4. Отвечай только если полностью уверен. Лучше отказаться, чем ошибиться."
    )

    def __init__(self, context_radius: int = 200):
        self.context_radius = context_radius

    # -------------------------------------------------------------------------
    def build(
        self,
        text: str,
        word: str,
        start: int,
        end: int,
        entry: Tuple[Any, Any, List[Dict]],
    ) -> Tuple[Optional[str], Optional[str], Union[Dict[int, int], Dict[str, int]]]:
        """
        Возвращает (system_prompt, user_prompt, lemma_to_group).
        Если все леммы из одной группы — возвращает (None, None, {"single_group": id}).
        Если леммы неразличимы — возвращает (None, None, {}).
        """
        _, accent_options, groups = entry

        # 1. Собираем плоский список уникальных лемм с group_id
        lemmas = self._collect_lemmas(groups)

        # 2. Если осталась только одна группа — ударение однозначно
        group_ids = {lm["group_id"] for lm in lemmas}
        if len(group_ids) == 1:
            return None, None, {"single_group": group_ids.pop()}

        # 3. Ранний отказ: если после дедупликации профили лемм идентичны
        if not self._can_distinguish(lemmas):
            return None, None, {}

        # 4. Формируем варианты для LLM
        variants = self._build_variants(lemmas)

        context = self._extract_context(text, start, end)
        user_data = {
            "context": context,
            "word": word,
            "variants": variants,
        }
        user_prompt = json.dumps(user_data, ensure_ascii=False, indent=2)

        # 5. Маппинг: номер варианта (1-based) -> group_id
        lemma_to_group = {i + 1: lm["group_id"] for i, lm in enumerate(lemmas)}

        return self.SYSTEM_PROMPT, user_prompt, lemma_to_group

    # -------------------------------------------------------------------------
    def _collect_lemmas(self, groups: List[Dict]) -> List[Dict]:
        """Собирает плоский список уникальных лемм с group_id."""
        lemmas: List[Dict] = []
        seen: set = set()
        for g in groups:
            gid = g["group ID"]
            for lm in g.get("lemmas", []):
                # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: включаем group_id в ключ,
                # чтобы леммы из разных групп не схлопывались
                key = (
                    gid,
                    lm.get("lemma", ""),
                    lm.get("pos", ""),
                    tuple(_flatten_tags(lm.get("tags", []))),
                )
                if key in seen:
                    continue
                seen.add(key)
                # translations — словарь {язык: перевод}, нормализуем в список строк
                raw_trans = lm.get("translations", {})
                if isinstance(raw_trans, dict):
                    translations = self._format_translations(raw_trans)
                else:
                    translations = []
                lemmas.append({
                    "group_id": gid,
                    "lemma": lm.get("lemma", ""),
                    "pos": lm.get("pos", ""),
                    "tags": _flatten_tags(lm.get("tags", [])),
                    "glosses": lm.get("glosses", []),
                    "translations": translations,
                })
        return lemmas

    # -------------------------------------------------------------------------
    @staticmethod
    def _format_translations(translations_dict: Dict[str, str]) -> List[str]:
        """
        Формирует список строк вида 'Язык: перевод'.
        Сначала идут языки из TARGET_TRANSLATION_LANGS (в заданном порядке),
        затем — остальные языки из словаря.
        """
        result: List[str] = []
        # Приоритетные языки
        for lang in TARGET_TRANSLATION_LANGS:
            if lang in translations_dict:
                result.append(f"{lang}: {translations_dict[lang]}")
        # Остальные языки (детерминированный порядок — сортировка по ключу)
        for lang in sorted(translations_dict.keys()):
            if lang not in TARGET_TRANSLATION_LANGS:
                result.append(f"{lang}: {translations_dict[lang]}")
        return result

    # -------------------------------------------------------------------------
    def _can_distinguish(self, lemmas: List[Dict]) -> bool:
        """True, если между леммами есть хотя бы одно реальное различие."""
        if len(lemmas) < 2:
            return False
        profiles: set = set()
        for lm in lemmas:
            profile = (
                lm["lemma"],
                lm["pos"],
                tuple(lm["tags"]),
                tuple(sorted(lm["glosses"])),
                tuple(sorted(lm["translations"])),
            )
            profiles.add(profile)
        return len(profiles) > 1

    # -------------------------------------------------------------------------
    def _build_variants(self, lemmas: List[Dict]) -> List[Dict]:
        """Строит JSON-варианты для LLM."""
        variants: List[Dict] = []
        for i, lm in enumerate(lemmas):
            variant: Dict[str, Any] = {"id": i + 1}
            if lm["lemma"]:
                variant["lemma"] = lm["lemma"]
            if lm["pos"]:
                variant["pos"] = lm["pos"]
            if lm["tags"]:
                variant["tags"] = lm["tags"]
            if lm["glosses"]:
                variant["glosses"] = lm["glosses"][:2]
            # translations уже отформатированы как список строк
            if lm["translations"]:
                variant["translations"] = lm["translations"][:2]
            variants.append(variant)
        return variants

    # -------------------------------------------------------------------------
    def _extract_context(self, text: str, start: int, end: int) -> str:
        """Извлекает окно текста с выделенным словом `` `word` ``."""
        ctx_start = max(0, start - self.context_radius)
        ctx_end = min(len(text), end + self.context_radius)

        while ctx_start > 0 and text[ctx_start - 1] not in " \n\t":
            ctx_start -= 1
        while ctx_end < len(text) and text[ctx_end] not in " \n\t":
            ctx_end += 1

        ctx = text[ctx_start:ctx_end]
        rel_s = start - ctx_start
        rel_e = end - ctx_start

        return f"{ctx[:rel_s]}\u0060{ctx[rel_s:rel_e]}\u0060{ctx[rel_e:]}"


# -----------------------------------------------------------------------------
# Основной резолвер
# -----------------------------------------------------------------------------

class AccentResolver:
    """
    Разрешает неоднозначность ударения с помощью локальной LLM.
    """

    def __init__(
        self,
        data_store: AccentDataStore,
        model: Optional[Any] = None,
        tokenizer: Optional[Any] = None,

        max_new_tokens: int = 5,
        temperature: float = 0.1,
        top_p: float = 0.9,
        context_radius: int = 200,
        cache_size: int = 2048,
    ):
        """
        Args:
            data_store: Загруженное хранилище JSONL.
            model: Готовая модель (например, model_loader.generator_model).
            tokenizer: Готовый токенизатор.

            max_new_tokens: Максимум генерируемых токенов (достаточно 3-5).
            temperature: 0.0 для жёсткой детерминированности.
            top_p: Параметр nucleus sampling.
            context_radius: Радиус контекста в символах.
            cache_size: Размер LRU-кэша результатов.
        """
        self.data_store = data_store
        self.model = model
        self.tokenizer = tokenizer

        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.prompt_builder = PromptBuilder(context_radius=context_radius)

        # LRU-кэш: OrderedDict с ограничением размера
        self._cache: OrderedDict[str, ResolutionResult] = OrderedDict()
        self._cache_size = cache_size

        if model is not None and tokenizer is not None:
            logger.info("Resolver: используется переданная модель/токенизатор")
        else:
            logger.warning("Resolver: модель не загружена, только режим промптов")

    # -------------------------------------------------------------------------
    def _load_model(self) -> None:
        """Автозагрузка модели через model_loader (локальный импорт)."""
        try:
            from .model_loader import ModelLoader  # локальный импорт
        except ImportError:
            logger.error("model_loader не найден — невозможно загрузить модель")
            return
        model_loader = ModelLoader()
        logger.info("Resolver: загрузка модели...")
        self.tokenizer = model_loader.generator_tokenizer
        self.model = model_loader.generator_model
        self.model.eval()
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        logger.info("Resolver: модель загружена")

    # -------------------------------------------------------------------------
    def _cache_key(
        self, text: str, start: int, end: int, entry: Tuple[Any, Any, List[Dict]]
    ) -> str:
        """Хэш-ключ для кэширования на основе слова, контекста и вариантов."""
        _, accent_options, groups = entry
        payload = {
            "word": text[start:end],
            "ctx": text[max(0, start - 50) : min(len(text), end + 50)],
            "opts": accent_options,
            "groups": groups,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    # -------------------------------------------------------------------------

    def resolve(self, text: str, start: int, end: int) -> ResolutionResult:
        word = text[start:end]
        entry = self.data_store.lookup(word)

        if entry is None:
            logger.debug(f"Словоформа '{word}' отсутствует в словаре")
            return ResolutionResult.not_found()

        # Проверка кэша
        key = self._cache_key(text, start, end, entry)
        if key in self._cache:
            logger.debug(f"Кэш-хит для '{word}'")
            self._cache.move_to_end(key)
            return self._cache[key]

        # Формируем промпт
        system_prompt, user_prompt, lemma_to_group = self.prompt_builder.build(
            text, word, start, end, entry
        )

        # === Однозначный случай: все леммы из одной группы ===
        if isinstance(lemma_to_group, dict) and "single_group" in lemma_to_group:
            group_id = lemma_to_group["single_group"]
            _, accent_options, _ = entry
            accented = accent_options.get(str(group_id))
            if accented is None:
                accented = accent_options.get(group_id, word)
            result = ResolutionResult.success(group_id, accented)
            self._cache[key] = result
            self._cache.move_to_end(key)
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
            return result

        # === Ранний отказ: леммы неразличимы ===
        if system_prompt is None:
            logger.info(f"Отказ для '{word}': варианты неразличимы")
            return ResolutionResult(resolved=False, reason="indistinguishable")

        # Если модели нет — режим только промптов
        if self.model is None or self.tokenizer is None:
            logger.info("Режим только промптов (модель не загружена)")
            return ResolutionResult(resolved=False, reason="model_not_loaded")

        # Вызываем LLM
        result = self._call_llm(system_prompt, user_prompt, entry, lemma_to_group)
        
        # Сохраняем в кэш (LRU)
        self._cache[key] = result
        self._cache.move_to_end(key)
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

        return result

    # -------------------------------------------------------------------------
    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        entry: Tuple[Any, Any, List[Dict]],
        lemma_to_group: Dict[int, int],
    ) -> ResolutionResult:
        """Отправляет запрос в LLM и парсит ответ."""
        _, accent_options, _ = entry
        num_lemmas = len(lemma_to_group)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            prompt_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.tokenizer(prompt_text, return_tensors="pt").to(
                self.model.device
            )

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    do_sample=self.temperature > 0,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    max_length=None
                )

            generated = outputs[0][inputs.input_ids.shape[1] :]
            answer = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
            logger.debug(f"LLM ответ: {answer!r}")

        except Exception as exc:
            logger.error(f"Ошибка при вызове LLM: {exc}")
            return ResolutionResult(resolved=False, reason=f"llm_error: {exc}")

        # Парсим lemma_id (теперь это номер леммы, а не группы)
        lemma_id = self._parse_answer(answer, num_lemmas)
        if lemma_id is None or lemma_id == 0:
            return ResolutionResult.ambiguous()

        # Пересчитываем lemma_id -> group_id
        group_id = lemma_to_group.get(lemma_id)
        if group_id is None:
            return ResolutionResult.ambiguous()

        accented = accent_options.get(str(group_id))
        if accented is None:
            accented = accent_options.get(group_id, "")

        return ResolutionResult.success(group_id, accented)

    # -------------------------------------------------------------------------
    def _parse_answer(self, answer: str, num_lemmas: int) -> Optional[int]:
        """Извлекает номер леммы из ответа LLM."""
        # Ищем первое число в ответе
        match = re.search(r'\d+', answer)
        if not match:
            return None
        try:
            val = int(match.group())
            if 0 <= val <= num_lemmas:
                return val
        except ValueError:
            pass
        return None

    # -------------------------------------------------------------------------
    def get_prompt(self, text: str, start: int, end: int) -> Optional[Tuple[str, str]]:
        """Возвращает сформированный промпт без вызова модели (для отладки)."""
        word = text[start:end]
        entry = self.data_store.lookup(word)
        if entry is None:
            return None
        system_prompt, user_prompt, lemma_to_group = self.prompt_builder.build(
            text, word, start, end, entry
        )
        if system_prompt is None:
            return None
        return system_prompt, user_prompt


# -----------------------------------------------------------------------------
# Точка входа (демо / CLI)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Accent Resolver")
    parser.add_argument("--data", required=True, help="Путь к JSONL-файлу с данными")

    parser.add_argument("--text", help="Входной текст")
    parser.add_argument("--start", type=int, help="Начальная позиция слова")
    parser.add_argument("--end", type=int, help="Конечная позиция слова")
    parser.add_argument(
        "--prompt-only", action="store_true", help="Только сформировать промпт"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    store = AccentDataStore(args.data)

    # Локальный импорт model_loader только при необходимости
    try:
        from model_loader import model_loader
        resolver = AccentResolver(
            data_store=store,
            model=model_loader.generator_model,
            tokenizer=model_loader.generator_tokenizer
        )
    except ImportError:
        logger.warning("model_loader не найден — resolver работает в режиме промптов")
        resolver = AccentResolver(data_store=store)

    # --- CLI-режим с явными позициями ---
    if args.text and args.start is not None and args.end is not None:
        if args.prompt_only:
            prompt = resolver.get_prompt(args.text, args.start, args.end)
            if prompt:
                print("=== SYSTEM PROMPT ===")
                print(prompt[0])
                print("\n=== USER PROMPT ===")
                print(prompt[1])
            else:
                print("Слово не найдено в словаре")
        else:
            result = resolver.resolve(args.text, args.start, args.end)
            print(result)
        sys.exit(0)

    # --- Демо: показываем промпт для "мука" ---
    demo_text = 'На другой день Алексей, твёрдый в своём намерении, рано утром поехал к Муромскому, дабы откровенно с ним объясниться.'
    # 'Происходящие события - это ужасная мука для меня.'
    
    w = "дабы" # "мука"
    s = demo_text.find(w)
    e = s + len(w)

    prompt = resolver.get_prompt(demo_text, s, e)
    if prompt:
        print("=== ДЕМО ПРОМПТ ===")
        print(prompt[1])

    print("\n=== resolver.resolve ===")
    result = resolver.resolve(demo_text, s, e)
    print(result)