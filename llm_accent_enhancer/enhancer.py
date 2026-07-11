"""
LLM Accent Enhancer — пост-обработка результатов AccentEngine с помощью LLM.

Использование:
    from accent_engine import AccentEngine, AccentConfig
    from llm_accent_enhancer import AccentDataStore, AccentResolver, LLMAccentEnhancer

    engine = AccentEngine(AccentConfig(data_path=Path("...")))
    store  = AccentDataStore("ambiguity.jsonl")
    resolver = AccentResolver(data_store=store, model=..., tokenizer=...)
    enhancer = LLMAccentEnhancer(engine, resolver)

    result = enhancer.accentuate("Ключик от навесного замка")
    print(result.to_annotated_text())
"""
from __future__ import annotations

import logging
from typing import Optional

from accent_engine import (
    AccentEngine,
    DocumentResult,
    WordInfo,
    StressPosition,
    StressMethod,
)

from .accent_resolver import AccentResolver

logger = logging.getLogger(__name__)

RUSSIAN_VOWELS_LOWER = frozenset("аеёиоуыэюя")

stress_sign = "́"

def _vowel_positions(text: str) -> list[int]:
    """Возвращает индексы всех гласных в тексте."""
    return [i for i, ch in enumerate(text) if ch in RUSSIAN_VOWELS_LOWER]


class LLMAccentEnhancer:
    """
    Обёртка над AccentEngine, которая уточняет неоднозначные ударения через LLM.

    Работает в два этапа:
      1. Быстрая акцентуация через AccentEngine (BERT + словарь + эвристики).
      2. Пост-обработка: для слов, присутствующих в словаре LLM-неоднозначностей,
         вызывается AccentResolver, который анализирует контекст и выбирает
         правильный вариант ударения.
    """

    def __init__(
        self,
        accent_engine: AccentEngine,
        accent_resolver: AccentResolver,
        *,
        only_ambiguous: bool = True,
    ):
        """
        Args:
            accent_engine:   Экземпляр AccentEngine.
            accent_resolver: Экземпляр AccentResolver (с загруженной LLM).
            only_ambiguous:  Если True, LLM вызывается только для слов,
                             которые AccentEngine пометил как DICT_MULTI / BERT
                             или оставил UNKNOWN. Если False — для любого слова,
                             есть оно в LLM-словаре.
        """
        self.accent_engine = accent_engine
        self.resolver = accent_resolver
        self.only_ambiguous = only_ambiguous

        # Попробуем использовать StressMethod.LLM, если пользователь добавил его
        # в core.py. Иначе fallback на HEURISTIC.
        try:
            self._llm_method = StressMethod.LLM
        except AttributeError:
            self._llm_method = StressMethod.HEURISTIC
            logger.debug(
                "StressMethod.LLM не найден — используем HEURISTIC как placeholder"
            )

    # ------------------------------------------------------------------
    def accentuate(self, text: str) -> DocumentResult:
        """
        Акцентуирует текст с помощью AccentEngine, затем уточняет
        неоднозначные слова через LLM.
        """
        doc = self.accent_engine.accentuate(text)
        self._enhance(doc)
        return doc

    # ------------------------------------------------------------------
    def _enhance(self, doc: DocumentResult) -> None:
        """Пост-обработка: уточнение неоднозначных слов."""
        for sentence in doc.sentences:
            for word in sentence.words:
                if not word.is_russian_word:
                    continue
                    
                # print('word.text', word.text, word.method)

                # Фильтр: если only_ambiguous=True, пропускаем однозначные
                if self.only_ambiguous and word.method not in (
                    StressMethod.DICT_MULTI,
                    StressMethod.BERT,
                    StressMethod.UNKNOWN,
                    StressMethod.HEURISTIC,
                ):
                    continue
                    
                # Проверяем, есть ли слово в словаре LLM-неоднозначностей
                if not self.resolver.data_store.lookup(word.text):
                    continue

                try:
                    result = self.resolver.resolve(
                        doc.original_text, word.start, word.end
                    )
                except Exception as exc:
                    logger.warning(f"LLM resolver failed for \'{word.text}\': {exc}")
                    continue
                    
                if not result.resolved or not result.accented_form:
                    continue

                stress = self._parse_accented_form(word, result.accented_form)
                if stress is not None:
                    word.stress = stress
                    word.method = self._llm_method
                    logger.debug(f"LLM refined \'{word.text}\' → {stress}")

    # ------------------------------------------------------------------
    def _parse_accented_form(
        self, word: WordInfo, accented_form: str
    ) -> Optional[StressPosition]:
        """
        Преобразует словарную форму вида 'з+амка' в StressPosition
        для оригинального слова (с учётом регистра и ё/е).
        """
        # plus_pos = accented_form.find("+")
        plus_pos = accented_form.find(stress_sign) - 1
        if plus_pos < 0:
            return None

        clean_form = accented_form.replace("+", "").replace(stress_sign, "")
        word_lower = word.text.casefold().replace("ё", "е")

        if clean_form == word_lower:
            # Прямое совпадение — позиция '+' совпадает с позицией в оригинале
            char_index = plus_pos
        else:
            # Непрямое совпадение: маппим по индексу гласной
            form_vowels = _vowel_positions(clean_form)
            word_vowels = _vowel_positions(word_lower)

            if len(form_vowels) != len(word_vowels):
                logger.warning(
                    f"Vowel count mismatch for \'{word.text}\' vs \'{accented_form}\'"
                )
                return None

            # Какая по счёту гласная ударная в форме словаря?
            stressed_vowel_idx = sum(1 for v in form_vowels if v < plus_pos)
            if stressed_vowel_idx >= len(word_vowels):
                return None

            char_index = word_vowels[stressed_vowel_idx]

        # Проверяем, что индекс валиден для оригинального слова
        if char_index >= len(word.text):
            return None

        # Считаем vowel_index (порядковый номер гласной)
        word_vowels = _vowel_positions(word.text.casefold())
        try:
            vowel_index = word_vowels.index(char_index)
        except ValueError:
            return None

        return StressPosition(vowel_index=vowel_index, char_index=char_index)