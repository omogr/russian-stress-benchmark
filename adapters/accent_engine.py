"""
adapters/accent_engine.py

Адаптер для библиотеки accent_engine (без морфологии).
https://github.com/omogr/omogre
"""

from pathlib import Path
from udarenie import load_accentor


class Accentuator:
    def __init__(self):
        self.accentor = load_accentor(data_dir=Path("data_plus"), use_morph=False)

    def accentuate(self, text: str) -> str:
        doc = self.accentor.accentuate(text)
        return doc.to_annotated_text()

    def description(self) -> str:
        return "Accent engine without morphology"
