import json
from collections import defaultdict
from natasha import Segmenter, MorphVocab, NewsEmbedding, NewsMorphTagger, Doc


class WiktionaryStressFinder:
    """
    Находит ударения в русском тексте, сопоставляя морфологические атрибуты
    Natasha NewsMorphTagger с данными Wiktionary (kaikki.org).

    Алгоритм:
    1. При загрузке kaikki: для каждой словоформы с ударением строим индекс
       нормализованная_форма → список (pos, morph_tags, stressed_form).
    2. При обработке текста: для каждого токена ищем его в индексе,
       фильтруем наборы по совместимости с Natasha-атрибутами.
    3. Возвращаем все допустимые варианты ударений или пустой список.
    """

    # --- Сопоставление POS Natasha → Wiktionary ---
    POS_MAP = {
        'ADJ':   'adjective',
        'ADV':   'adverb',
        'NOUN':  'noun',
        'VERB':  'verb',
        'PRON':  'pronoun',
        'ADP':   'preposition',
        'SCONJ': 'conjunction',
        'CCONJ': 'conjunction',
        'PART':  'particle',
        'INTJ':  'intj',
        'NUM':   'numeral',
        'DET':   'det',
        'PROPN': 'name',
    }

    # --- Сопоставление feats Natasha → Wiktionary ---
    FEAT_MAP = {
        'Number': {
            'Sing': 'singular',
            'Plur': 'plural',
        },
        'Gender': {
            'Masc': 'masculine',
            'Fem':  'feminine',
            'Neut': 'neuter',
        },
        'Case': {
            'Nom': 'nominative',
            'Acc': 'accusative',
            'Gen': 'genitive',
            'Dat': 'dative',
            'Ins': 'instrumental',
            'Loc': {'prepositional', 'locative'},
            'Voc': 'vocative',
            'Par': 'partitive',
        },
        'Tense': {
            'Past': 'past',
            'Pres': 'present',
            'Fut':  'future',
        },
        'Aspect': {
            'Perf': 'perfective',
            'Imp':  'imperfective',
        },
        'Mood': {
            'Imp': 'imperative',
        },
        'VerbForm': {
            'Inf':  'infinitive',
            'Part': 'participle',
            'Conv': 'adverbial',
        },
        'Voice': {
            'Act': 'active',
            'Pass': 'passive',
            'Mid':  'reflexive',
        },
        'Person': {
            '1': 'first-person',
            '2': 'second-person',
            '3': 'third-person',
        },
        'Animacy': {
            'Anim': 'animate',
            'Inan': 'inanimate',
        },
        'Degree': {
            'Cmp': 'comparative',
            'Sup': 'superlative',
        },
        'Variant': {
            'Short': 'short-form',
        },
    }

    # --- Теги Wiktionary, которые НЕ относятся к морфологическим атрибутам ---
    NON_MORPH_TAGS = {
        'canonical', 'romanization', 'inflection-template', 'table-tags', 'class',
        'alternative', 'error-unrecognized-form', 'error-unknown-tag',
        'dated', 'rare', 'colloquial', 'poetic', 'obsolete', 'uncommon',
        'proscribed', 'archaic', 'dialectal', 'nonstandard', 'endearing',
        'clipping', 'literary', 'sometimes', 'demonym', 'common-gender',
        'standard', 'stressed', 'unstressed', 'Internet', 'pronunciation-spelling',
        'usually', 'also', 'Middle', 'Russian', 'no-perfect', 'no-short-form',
        'no-table-tags', 'abstract-noun', 'diminutive', 'augmentative', 'pejorative',
        'relational', 'adjective', 'adverb', 'noun-from-verb', 'emphatic', 'collective',
        'count-form', 'semelfactive', 'paucal', 'abbreviation', 'regional', 'Pskov',
        'by-personal-gender', 'common',
    }

    # --- Категории для проверки конфликтов ---
    _CATEGORIES = {
        'number':   {'singular', 'plural'},
        'gender':   {'masculine', 'feminine', 'neuter'},
        'case':     {'nominative', 'accusative', 'genitive', 'dative',
                     'instrumental', 'prepositional', 'locative', 'vocative', 'partitive'},
        'tense':    {'past', 'present', 'future'},
        'aspect':   {'perfective', 'imperfective'},
        'person':   {'first-person', 'second-person', 'third-person'},
        'animacy':  {'animate', 'inanimate'},
        'voice':    {'active', 'passive', 'reflexive'},
        'verbform': {'infinitive', 'participle', 'adverbial', 'imperative', 'short-form'},
        'degree':   {'comparative', 'superlative'},
    }

    def __init__(self, kaikki_path: str):
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)

        # Индекс: нормализованная_форма → [Record(pos, morph_tags, stressed_form)]
        self.index = defaultdict(list)
        self._load_kaikki(kaikki_path)

    # --------------------------------------------------------------------- #
    #  Внутренние утилиты
    # --------------------------------------------------------------------- #
    @staticmethod
    def _normalize(text: str) -> str:
        """Lower-case, без ударений, ё→е."""
        if not text:
            return ''
        return (text.lower()
                .replace('\u0301', '')
                .replace('\u0300', '')
                .replace('ё', 'е')
                .replace('Ё', 'Е'))

    @classmethod
    def _is_morph_tag(cls, tag: str) -> bool:
        return tag not in cls.NON_MORPH_TAGS

    @staticmethod
    def _has_stress(form: str) -> bool:
        """Проверяет наличие знака ударения U+0301."""
        return '\u0301' in form

    def _natasha_feats_to_wiktionary(self, feats: dict) -> set:
        """Преобразует Natasha feats → множество тегов Wiktionary."""
        wikt_tags = set()
        for feat, value in (feats or {}).items():
            mapping = self.FEAT_MAP.get(feat)
            if not mapping:
                continue
            mapped = mapping.get(value)
            if not mapped:
                continue
            if isinstance(mapped, set):
                wikt_tags.update(mapped)
            else:
                wikt_tags.add(mapped)
        return wikt_tags

    def _is_compatible(self, token_tags: set, form_tags: set) -> bool:
        """
        Проверяет совместимость двух наборов тегов.
        Возвращает False, если есть конфликт внутри одной категории.
        """
        for cat_vals in self._CATEGORIES.values():
            tok = token_tags & cat_vals
            frm = form_tags & cat_vals
            if tok and frm and not (tok & frm):
                return False
        return True

    # --------------------------------------------------------------------- #
    #  Загрузка kaikki
    # --------------------------------------------------------------------- #
    def _load_kaikki(self, path: str):
        """
        Загружает kaikki jsonl и строит индекс по нормализованным словоформам.
        Для каждой формы с ударением сохраняем: (pos, morph_tags, stressed_form).
        """
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                norm, value = entry
                self.index[norm] = [{
                            'pos': tv['pos'],
                            'morph_tags': set(tv['morph_tags']),
                            'stressed_form': tv['stressed_form'],
                        } for tv in value]

    # --------------------------------------------------------------------- #
    #  Публичный API
    # --------------------------------------------------------------------- #
    def find_stress(self, text: str) -> list[dict]:
        """
        Анализирует текст и возвращает список токенов с вариантами ударений.

        Каждый элемент — словарь:
            text          : исходное слово
            pos           : POS из Natasha
            feats         : feats из Natasha (dict)
            stress_options: список строк (форм с ударением из Wiktionary)
        """
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)

        results = []

        for token in doc.tokens:
            result = result = {
                'text': token.text,
                'start': token.start,
                'end': token.stop,
                'pos': token.pos,
                'feats': dict(token.feats) if token.feats else {},
                'stress_options': [],
            }

            '''{
                'text': token.text,
                'pos': token.pos,
                'feats': dict(token.feats) if token.feats else {},
                'stress_options': [],
            }'''

            # Пропускаем не-слова
            if token.pos in ('PUNCT', 'SYM', 'X'):
                results.append(result)
                continue

            # Преобразуем POS Natasha → Wiktionary
            wikt_pos = self.POS_MAP.get(token.pos, token.pos.lower())

            # Преобразуем feats
            token_tags = self._natasha_feats_to_wiktionary(
                dict(token.feats) if token.feats else {}
            )

            # Ищем словоформу в индексе
            norm_token = self._normalize(token.text)
            records = self.index.get(norm_token, [])

            # Фильтруем по совместимости
            seen = set()
            for rec in records:
                # Проверяем POS
                if rec['pos'] != wikt_pos:
                    continue

                # Проверяем совместимость морфологических атрибутов
                if not self._is_compatible(token_tags, rec['morph_tags']):
                    continue
                    
                stressed = rec['stressed_form']
                if stressed not in seen:
                    result['stress_options'].append(stressed)
                    seen.add(stressed)

            results.append(result)

        return results


def group_kaikki_forms(src_path: str, dst_path: str):
    """
    Загружает kaikki jsonl и строит индекс по нормализованным словоформам.
    Для каждой формы с ударением сохраняем: (pos, morph_tags, stressed_form).
    """
    index = defaultdict(list)
    with open(src_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            pos = entry.get('pos', '')
            if not pos:
                continue

            for form_entry in entry.get('forms', []):
                form_text = form_entry.get('form', '')
                if not form_text or not WiktionaryStressFinder._has_stress(form_text):
                    continue
                    
                if form_text == "дабы́":
                    continue

                morph_tags = {t for t in form_entry.get('tags', []) if WiktionaryStressFinder._is_morph_tag(t)}

                norm = WiktionaryStressFinder._normalize(form_text)
                if norm:
                    index[norm].append({
                        'pos': pos,
                        'morph_tags': list(morph_tags),
                        'stressed_form': form_text,
                    })

    with open(dst_path, 'w', encoding='utf-8') as fout:
        for norm, value in index.items():
            print(json.dumps((norm, value), ensure_ascii=False), file=fout)


# =====================================================================
#  Пример использования
# =====================================================================
if __name__ == '__main__':
    #KAIKKI_PATH = 'kaikki-filt.jsonl'
    KAIKKI_SRC_PATH = 'kaikki.jsonl'
    KAIKKI_PATH = 'kaikki-forms.jsonl'
    
    group_kaikki_forms(KAIKKI_SRC_PATH, KAIKKI_PATH)
    print("=" * 60)
    finder = WiktionaryStressFinder(KAIKKI_PATH)
    print("=" * 60)    

    text = ('На другой день Алексей, твёрдый в своём намерении, '
            'рано утром поехал к Муромскому, дабы откровенно с ним объясниться.')

    print("=" * 60)
    print("Результат (без лемматизации):")
    print("=" * 60)
    for token in finder.find_stress(text):
        stress = ', '.join(token['stress_options']) if token['stress_options'] else '-'
        print(f"{token['text']:15} | {token['pos']:8} | {stress}")

