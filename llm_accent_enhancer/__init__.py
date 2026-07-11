"""
LLM Accent Enhancer — пост-обработка ударений через LLM.

Пакет работает поверх accent_engine и не требует изменений в её ядре
(достаточно добавить одну строку `LLM = auto()` в StressMethod для красоты).
"""
from .accent_resolver import AccentDataStore, AccentResolver, ResolutionResult
from .enhancer import LLMAccentEnhancer

__all__ = [
    "AccentDataStore",
    "AccentResolver",
    "ResolutionResult",
    "LLMAccentEnhancer",
]