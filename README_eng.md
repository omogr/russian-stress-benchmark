# russian-stress-benchmark

[Russian README](https://github.com/omogr/russian-stress-benchmark/blob/main/README.md)

A set of scripts for comparing stress-marking libraries against a manually annotated gold standard.

## What it does

This repository contains a pipeline for automatically testing and comparing various libraries that mark stress (accent) in Russian texts. The output of each library is compared against a manually annotated sample (gold standard), and a detailed report is generated.

## Libraries compared

| Library | Description |
|---------|-------------|
| `silero_stress` | [silero-stress](https://github.com/snakers4/silero-stress) |
| `udarenie` | A refactoring of the library from [omogre](https://github.com/omogr/omogre) + morphological analyzer Natasha NewsMorphTagger + stress marks from Wiktionary. |
| `accent_engine` | udarenie with load_accentor(use_morph=False) |

## Important limitations

- It is assumed that the stress-marking library must not change the original text, only add stress marks. If any words appear or disappear in the resulting text after stress marking, no complex word-alignment algorithms are used; only unchanged words from the beginning and end of the sentence are matched. The remaining words are considered unmatchable.

- Among other metrics, the test results also count errors on words that were marked by all libraries. This allows comparing the accuracy of a library without taking into account distortions it introduces to the original text.

- **The actual gold standard** (`gold/pattern.txt`) is **not** included in the repository — a placeholder is provided instead. For testing, use your own annotated text.

- **ruaccent** has many exceptional cases; after fixing them, testing will need to be repeated.

- There is a dictionary of words that allow multiple stress variants — such words are ignored.
- Words with hyphens are **not tested** (for simplicity).
- The code is a result of vibe coding, is raw, and has received little testing. The results should be considered preliminary.
- Performance (loading and processing time) is affected by computer configuration and caching. Performance measurements may vary across different computers or, for example, across multiple sequential runs of the same library on the same machine. Performance was measured on a laptop (Intel i7-12650H 2.30 GHz, DDR4 RAM, NVIDIA GeForce RTX 4060 Laptop GPU).

## Requirements

- Python 3.x
- Dependencies from `requirements.txt`

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
   The `requirements.txt` file lists the package versions used during testing. However, the testing scripts do nothing complex — they only run libraries and count errors. So they will likely work with other package versions as well.

3. **Prepare the gold standard:**
   - Replace the placeholder `gold/pattern.txt` with your own stress-annotated file.
   - Format: use `+` before the stressed vowel, **one sentence per line**.
   - Example:
     ```
     В л+есу род+илась ёлочка.
     ```

4. **Run the test:**
   ```bash
   ./run.sh
   ```

## Results

After running `run.sh` (or `run.bat`), the following files are created in the `output/` directory:
- `output/pattern.json` — the gold standard split into sentences
- `output/lib/GOLD_results.json` — word‑by‑word markup of the gold standard
- `output/raw/` — raw results from libraries (without word‑by‑word markup)
- `output/lib/` — results with word‑by‑word markup
- `output/comparison.json` — comparison data
- **`output/report.md`** — the final Markdown report

## [Sample report](https://github.com/omogr/russian-stress-benchmark/blob/main/reports/2026-07-10.pdf)

The report contains:
- General information (date, number of sentences, number of libraries)
- Performance (loading and processing time, exceptions)
- Error summary (incorrect stress, missed stress, mismatches in word count/text)
- Comparison on common words (accuracy on the intersection of words marked by all libraries)
- Detailed statistics per library

## Adding new libraries

Adding new libraries and re‑testing with other data is not particularly difficult. To add a new library, create a new accentuator in `run_accentuator.py` and add calls to `run.sh` following the pattern used for `silero_stress`.

## Repository structure

```
russian-stress-benchmark/
├── gold/
│   └── pattern.txt          # Gold standard (placeholder)
├── output/                  # Test results (created automatically)
├── run.sh                   # Main launch script
├── split_text_by_lines.py
├── extract_gold_accentuation.py
├── run_accentuator.py
├── extract_word_accentuation.py
├── compare_accentuators.py
├── generate_report.py
└── ...
```

## Disclaimer

This project is a result of vibe coding. The code is raw, has received little testing, and the results should be considered preliminary. Use at your own risk.

---

*Repository: [github.com/omogr/russian-stress-benchmark](https://github.com/omogr/russian-stress-benchmark)*
