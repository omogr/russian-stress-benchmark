"""
adapters/silero_stress.py

Адаптер для библиотеки silero-stress.
https://github.com/snakers4/silero-stress
"""

from silero_stress import load_accentor


class Accentuator:
    def __init__(self):
        self.accentor = load_accentor()

    def accentuate(self, text: str) -> str:
        return self.accentor(text)

    def description(self) -> str:
        return "Silero stress placement"
