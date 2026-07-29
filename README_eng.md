# russian-stress-benchmark
[Russian README](https://github.com/omogr/russian-stress-benchmark/blob/main/README.md)

A set of scripts for comparing stress placement libraries against a gold standard manual annotation.

## What it does
The repository contains a pipeline for automated testing and comparison of various libraries that place stress marks in Russian texts. The results of each library are compared against a manually annotated gold standard, and a detailed report is generated.

Each tested library must be able to take a text string as input and return a string with the same text but with stress marks added. Most commonly, the `+` sign is used before the stressed vowel. In some cases, the combining acute accent (U+0301) and combining grave accent (U+0300) after the vowel are allowed.

Testing involves comparing the results of each library against the manually annotated gold standard and measuring:
* number of stress placement errors
* execution time
* data loading time into RAM
* number of exceptions in the libraries (if any)
* differences between the returned text and the original text

## Compared libraries
| Library | Description |
| --- | --- |
| silero_stress | [silero-stress](https://github.com/snakers4/silero-stress) |
| udarenie | Model and dictionaries from [omogre](https://github.com/omogr/omogre) + morphological analyzer Natasha NewsMorphTagger + stresses from Wiktionary. Returns not only the text with stresses but also additional information (word-by-word annotation). |
| accent_engine | The `udarenie` library with morphology disabled. Works faster, but has slightly more errors. Returns not only the text with stresses but also additional information (word-by-word annotation). |

## Important limitations
* It is assumed that the stress placement library should not change the original text, but only add stress marks. If words appear or disappear in the resulting text, no complex word alignment algorithms are used; only unchanged words from the beginning and end of the sentence are considered. The rest are considered unmatched.
* The testing results also count errors on words that were successfully annotated by all libraries. This allows comparing the accuracy of the library without taking into account the distortions they introduce into the original text.
* The real gold standard (`gold/pattern.txt`) is not uploaded to the repository — a placeholder is provided instead. Use your own annotated text for testing.
* `ruaccent` has many exceptions; after fixing them, testing will need to be repeated.
* There is a dictionary of words that allow multiple stress variants — such words are not counted.
* Hyphenated words are not tested (for simplicity).
* The code is the result of "vibe-coding", it is raw and poorly tested. Results should be considered preliminary.
* Performance (loading and processing time) is affected by computer configuration and caching. Performance measurement results may vary across different computers or, for example, across multiple consecutive runs of the same library on the same computer. Performance was measured on a laptop (Intel i7-12650H 2.30 GHz processor, DDR4 RAM, NVIDIA GeForce RTX 4060 Laptop GPU).

## Requirements
* Python 3.x
* Dependencies from `requirements.txt`

## Quick Start

### Method 1: Via `benchmark.py` (recommended)
```bash
# 1. Initialize configuration
python benchmark.py init

# 2. Run the full benchmark
python benchmark.py run --gold gold/pattern.txt
```

### Method 2: Step-by-step (via separate scripts)
Clone the repository:
```bash
git clone https://github.com/omogr/russian-stress-benchmark.git
cd russian-stress-benchmark
```

Install dependencies:
```bash
pip install -r requirements.txt
```
*The `requirements.txt` specifies the package versions used for testing. However, the testing scripts don't do anything complex, they just run the libraries and count errors. So they will most likely work with other package versions too.*

Prepare the gold standard:
Replace the placeholder `gold/pattern.txt` with your own file with annotated stresses.
Format: `+` sign before the stressed vowel. For convenient analysis, it is desirable to split the text into sentences or short paragraphs, one sentence or paragraph per line.
Example:
```text
В л+есу род+илась ёлочка.
```

Run step-by-step testing:
```bash
# Splitting text into sentences
python split_text_by_lines.py gold/pattern.txt -o output/pattern.json

# Extracting gold standard annotation (GOLD)
python extract_accentuation.py output/pattern.json -o output/lib/GOLD_results.json --mode gold

# Running tested libraries (example for silero_stress)
python run_accentuator.py silero_stress output/lib/GOLD_results.json -o output/raw/

# Extracting word-by-word annotation from library results
python extract_accentuation.py output/raw/silero_stress_results.json -o output/lib/silero_stress_results.json --mode lib --lib-name silero_stress

# Comparing results of all libraries
python compare_accentuators.py output/lib/ -o output/comparison.json

# Generating reports
python generate_report.py output/comparison.json output/report.md
python generate_report_en.py output/comparison.json output/report_en.md
```

## Managing via `benchmark.py`
`benchmark.py` is a single orchestrator that manages the full testing pipeline: `split → extract_gold → [run_lib] × N → compare → report`. It supports result caching and incremental execution.

### Commands
| Command | Description |
| --- | --- |
| init | Create `benchmark_config.json` with default settings |
| run | Run the full benchmark |
| status | Show cache status — what is calculated, what needs recalculation |
| clean | Clear the cache |

### Usage examples
```bash
# Full run of all libraries
python benchmark.py run --gold gold/pattern.txt --config benchmark_config.json

# Rerun a specific library (others from cache)
python benchmark.py run --gold gold/pattern.txt --libs silero_stress --force

# Show status
python benchmark.py status --gold gold/pattern.txt --config benchmark_config.json

# Clear cache for a specific library
python benchmark.py clean --lib silero_stress

# Clear all cache
python benchmark.py clean --all
```

## Configuration (`benchmark_config.json`)
```json
{
   "libraries": [
     {
       "name": "silero_stress",
       "accentuator_args": ["silero_stress"],
       "extra_args": {},
       "returns_document": false,
       "description": "Silero stress placement"
     },
     {
       "name": "udarenie",
       "accentuator_args": ["udarenie"],
       "extra_args": {"--data-path": "data_plus"},
       "returns_document": true,
       "description": "Udarenie with morphology"
     }
   ],
   "output_dir": "output",
   "cache_dir": ".benchmark_cache",
   "dubious_file": "dubious/dubious.txt",
   "reports": "both"
 }
```

| Field | Description |
| --- | --- |
| name | Library name (must match the name in `run_accentuator.py`) |
| accentuator_args | Arguments for `run_accentuator.py` |
| extra_args | Additional flags (e.g., `--data-path`) |
| returns_document | `true` — the library returns a `DocumentResult` with word-by-word annotation. For such libraries (e.g., `udarenie` and `accent_engine`), the `extract_accentuation.py` step can be skipped, as the word-by-word correspondence with the original text can be obtained from the additional information. |
| description | Description for reports |
| output_dir | Directory for results |
| cache_dir | Directory for state cache |
| dubious_file | Path to the dictionary of dubious words (words with varying stress) |
| reports | `"ru"`, `"en"`, or `"both"` — which reports to generate |

## Script descriptions

**`benchmark.py`**
Single orchestrator for comparing stress placement libraries. Replaces `run.sh` / `run.bat`. Manages the full pipeline: `split → extract_gold → [run_lib] × N → compare → report`. Supports result caching, incremental execution, status checking, and cache clearing.

**`split_text_by_lines.py`**
Reads an input text file with annotated stresses, splits it into sentences (by lines), and saves it in JSON format. Supports auto-detection of encoding (UTF-8, cp1251, cp866, koi8-r, iso-8859-5). On Windows, automatically switches the console to UTF-8.
Usage:
```bash
python split_text_by_lines.py gold/pattern.txt -o output/pattern.json
```

**`run_accentuator.py`**
Runs a single stress placement library, measures data loading time into memory and text processing time, and saves results to JSON. Supports libraries: `accent_engine`, `udarenie`, `llm_enhancer`, `ruaccent_*`, `omogre_accentuator`, `silero_stress`.
Usage:
```bash
python run_accentuator.py silero_stress output/pattern.json -o output/raw/
python run_accentuator.py udarenie output/pattern.json -o output/raw/ --data-path data_plus
```

**`extract_accentuation.py`**
Universal module for extracting word-by-word stress annotation. Works in two modes:
* `--mode gold` — processes the gold standard annotation (input JSON with a `text` field)
* `--mode lib` — processes library results (input JSON with an `accented_text` field)

Removes stress marks from the text, determines the positions of stressed vowels, splits into words using `text_parser.TextParser`, and forms word-by-word annotation.
Usage:
```bash
# For GOLD annotation
python extract_accentuation.py output/pattern.json -o output/lib/GOLD_results.json --mode gold

# For library results
python extract_accentuation.py output/raw/silero_stress_results.json -o output/lib/silero_stress_results.json --mode lib --lib-name silero_stress

# Verify tokenization
python extract_accentuation.py --verify
```

**`compare_accentuators.py`**
Compares library results against the gold standard manual annotation (GOLD). Counts the number of stress errors, missed stresses, and unmatched words. Also calculates metrics for "common words" — words that were successfully annotated by all libraries.
Usage:
```bash
python compare_accentuators.py output/lib/ -o output/comparison.json
```

**`generate_report.py`**
Generates a text report in Markdown in Russian based on the comparison data. Includes performance tables, error counts, comparison by common words, and a detailed summary for each library.
Usage:
```bash
python generate_report.py output/comparison.json output/report.md
```

**`generate_report_en.py`**
Generates a text report in Markdown in English. Functionality is similar to `generate_report.py`.
Usage:
```bash
python generate_report_en.py output/comparison.json output/report_en.md
```

## General pipeline scheme
```text
gold/pattern.txt
        │
        ▼
 split_text_by_lines.py
        │
        ▼
 output/pattern.json  (list of sentences)
        │
        ├──► extract_accentuation.py --mode gold
        │           │
        │           ▼
        │    output/lib/GOLD_results.json  (gold standard word-by-word annotation)
        │
        ├──► run_accentuator.py <lib1>
        │           │
        │           ▼
        │    output/raw/<lib1>_results.json  (raw results)
        │           │
        │           ▼
        │    extract_accentuation.py --mode lib
        │           │
        │           ▼
        │    output/lib/<lib1>_results.json  (word-by-word annotation)
        │
        ├──► run_accentuator.py <lib2> ──► ... (similarly)
        │
        ▼
 compare_accentuators.py output/lib/ ──► output/comparison.json
                                               │
                                               ├──► generate_report.py ──► output/report.md
                                               │
                                               └──► generate_report_en.py ──► output/report_en.md
```
*Note: For libraries `udarenie` and `accent_engine`, which return `DocumentResult` with word-by-word annotation, the `extract_accentuation.py --mode lib` step can be skipped, as the word-by-word correspondence with the original text is already contained in the additional information.*

## Results
After executing the pipeline, the following are created in the `output/` directory:
* `output/pattern.json` — gold standard split into sentences
* `output/lib/GOLD_results.json` — gold standard word-by-word annotation
* `output/raw/` — raw library results (without word-by-word annotation)
* `output/lib/` — results with word-by-word annotation
* `output/comparison.json` — comparison data
* `output/report.md` — final report in Russian (Markdown)
* `output/report_en.md` — final report in English (Markdown)

[Example report](https://github.com/omogr/russian-stress-benchmark/blob/main/reports/2026-07-18.pdf)

The report contains:
* General information (date, number of sentences, number of libraries)
* Performance (loading and processing time, exceptions)
* Error summary (incorrect stresses, misses, mismatches in word count/text)
* Comparison by common words (accuracy on the intersection of words annotated by all libraries)
* Detailed statistics for each library

## Adding new libraries

### Via `benchmark.py` (recommended)
Simply add an entry to `benchmark_config.json`:
```json
{
  "name": "my_new_lib",
  "accentuator_args": ["my_new_lib"],
  "extra_args": {"--data-path": "path/to/data"},
  "returns_document": false,
  "description": "My new stress library"
}
```
And run:
```bash
python benchmark.py run --gold gold/pattern.txt --libs my_new_lib
```

### Manually (via separate scripts)
To add a new library you need to:
1. Create a new accentuator in `run_accentuator.py` (add a branch in `load_library()`)
2. Run step-by-step as described in "Quick Start → Method 2"

## Repository structure
```text
russian-stress-benchmark/
 ├── gold/
 │   └── pattern.txt              # Gold standard (placeholder)
 ├── output/                      # Testing results (created automatically)
 │   ├── pattern.json             # Gold standard split into sentences
 │   ├── raw/                     # Raw library results
 │   ├── lib/                     # Results with word-by-word annotation
 │   ├── comparison.json          # Comparison data
 │   ├── report.md                # Report in Russian
 │   └── report_en.md             # Report in English
 ├── benchmark.py                 # Single orchestrator (recommended)
 ├── benchmark_config.json        # Benchmark configuration (created via init)
 ├── split_text_by_lines.py       # Splitting text into sentences
 ├── extract_accentuation.py      # Extracting word-by-word stress annotation
 ├── run_accentuator.py           # Running a single library
 ├── compare_accentuators.py      # Comparing results with GOLD
 ├── generate_report.py           # Generating report (Russian)
 ├── generate_report_en.py        # Generating report (English)
 ├── requirements.txt             # Python dependencies
 ├── run.sh                       # Old launch script (bash)
 └── run.bat                      # Old launch script (Windows)
```

## Disclaimer
This project is the result of "vibe-coding". The code is raw, poorly tested, and the results should be considered preliminary. Use at your own risk.

Repository: [github.com/omogr/russian-stress-benchmark](https://github.com/omogr/russian-stress-benchmark)