"""
adapters/udarenie.py

Адаптер для библиотеки udarenie (с морфологией).
https://github.com/omogr/omogre
"""

from pathlib import Path
from udarenie import load_accentor


class Accentuator:
    def __init__(self):
        self.accentor = load_accentor(data_dir=Path("data_plus"))

    def accentuate(self, text: str) -> str:
        doc = self.accentor.accentuate(text)
        return doc.to_annotated_text()

    def description(self) -> str:
        return "Udarenie with morphology"
