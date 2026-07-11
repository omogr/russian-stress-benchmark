"""
Wiktionary Accent Enhancer — пост-обработка ударений через Wiktionary (kaikki.org)
и Natasha NewsMorphTagger.

Пакет работает поверх accent_engine и не требует изменений в её ядре
(достаточно добавить одну строку `WIKTIONARY = auto()` в StressMethod для красоты).
"""

from .wiktionary_enhancer import WiktionaryAccentEnhancer

# Re-export для удобства: пользователь может делать
#   from wiktionary_enhancer import WiktionaryStressFinder
# вместо отдельного импорта из morph_stress_finder.
try:
    from .morph_stress_finder import WiktionaryStressFinder
except ImportError:
    # fallback: модуль может лежать рядом, но не внутри пакета
    try:
        from morph_stress_finder import WiktionaryStressFinder
    except ImportError:
        WiktionaryStressFinder = None  # type: ignore[misc]

__all__ = [
    "WiktionaryAccentEnhancer",
    "WiktionaryStressFinder",
]