# russian-stress-benchmark

A set of scripts for comparing Russian stress placement libraries against a manually annotated gold standard.

## What it does

This repository contains a pipeline for automated testing and comparison of various libraries that place stress marks in Russian-language texts. The results of each library are compared against a manually annotated sample (gold standard), and a detailed report is generated.

## Compared libraries

| Library | Description |
|---------|-------------|
| `accent_engine` | A refactored version of the library from [omogre](https://github.com/omogr/omogre). Data and algorithms remain unchanged. |
| `wiki_enhancer` | Experimental module: `accent_engine` + Natasha NewsMorphTagger morphological analyzer + stress data from Wiktionary. |
| `silero_stress` | [silero-stress](https://github.com/snakers4/silero-stress) |
| `ruaccent_turbo` | [ruaccent](https://github.com/Den4ikAI/ruaccent) |
| `llm_enhancer` | Experimental module: `accent_engine` + sense disambiguation based on LLM. |

## Important limitations

- **accent_engine**, **wiki_enhancer**, and **llm_enhancer** are designed to process text in small chunks. When the input exceeds 512 tokens, quality degrades. **It is recommended to process text sentence by sentence.**
- The **real gold standard** (`gold/pattern.txt`) is not included in the repository — a placeholder is provided instead. Use your own annotated text for testing.
- **ruaccent_turbo** has many edge cases; after they are fixed, testing will need to be repeated.
- **llm_enhancer** uses a heavy local model, works reasonably well, but in the current version does not improve upon `accent_engine` and is excluded from the standard report.
- A significant portion of errors comes from words that have multiple valid stress variants — a dictionary of such cases may be required.
- Hyphenated words are **not tested** (for simplicity).
- The code is the result of vibe coding, raw and barely tested. Results should be considered preliminary.

## Requirements

- Python 3.x
- Dependencies from `requirements.txt`
- For `llm_enhancer` — a local LLM (not included in the standard run)

## Quick start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/omogr/russian-stress-benchmark.git
   cd russian-stress-benchmark
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare the gold standard:**
   - Replace the placeholder `gold/pattern.txt` with your own file containing annotated stress marks.
   - Format: a `+` sign before the stressed vowel, **one sentence per line**.
   - Example:
     ```
     В л+есу род+илась ёлочка.
     ```

4. **Run the benchmark:**
   ```bash
   ./run.sh
   ```

## Results

After the script completes, the following files are created in the `output/` directory:
- `output/pattern.json` — the gold standard split into sentences
- `output/lib/GOLD_results.json` — word-level annotation of the gold standard
- `output/raw/` — raw library outputs
- `output/lib/` — word-level annotation results
- `output/comparison.json` — comparison data
- **`output/report.md`** — final Markdown report

## Sample report

The report contains:
- General information (date, number of sentences, number of libraries)
- Performance (load and processing time, exceptions)
- Error summary (incorrect stress, omissions, word count/text mismatches)
- Comparison on common words (accuracy on the intersection of words annotated by all libraries)
- Detailed statistics for each library

## Adding new libraries

Adding new libraries and re-testing with different data is straightforward. Create a new accentuator in `run_accentuator.py` and add its invocation to `run.sh`.

## Repository structure

```
russian-stress-benchmark/
├── gold/
│   └── pattern.txt          # Gold standard (placeholder)
├── output/                  # Test results (created automatically)
├── run.sh                   # Main launch script
├── split_sentences_by_lines.py
├── extract_gold_accentuation.py
├── run_accentuator.py
├── extract_word_accentuation.py
├── compare_accentuators.py
├── generate_report.py
└── ...
```

## Disclaimer

This project is the result of vibe coding. The code is raw, barely tested, and the results should be considered preliminary. Use at your own risk.

---

*Repository: [github.com/omogr/russian-stress-benchmark](https://github.com/omogr/russian-stress-benchmark)*