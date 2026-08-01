# russian-stress-benchmark

[Russian README](https://github.com/omogr/russian-stress-benchmark/blob/main/README.md)

A set of scripts for comparing stress placement libraries against a manually annotated gold standard.

## What it does

This repository provides a pipeline for automatically testing and comparing various libraries that place stress marks in Russian texts. The output of each library is compared against a manually annotated gold standard, and a detailed report is generated.

Each library under test must accept a text string as input and return a string with stress marks added to the same text. Typically, the `+` sign is placed before the stressed vowel. In some cases, the stress marks U+0301 and U+0300 after the stressed vowel are also allowed.

The benchmark measures:

- number of stress placement errors
- processing time
- data loading time into RAM
- number of exceptions thrown by libraries
- differences between the returned text and the original input

## Libraries compared

| Library | Description |
|---------|-------------|
| `silero_stress` | [silero-stress](https://github.com/snakers4/silero-stress) |
| `udarenie` | Model and dictionaries from [omogre](https://github.com/omogr/omogre) + morphological analyzer Natasha NewsMorphTagger + stress from Wiktionary. Returns word‑by‑word markup. |
| `accent_engine` | The udarenie library with morphology disabled. Faster, but slightly more errors. |

## Important limitations

- The library must not change the original text, only add stress marks. If words appear/disappear, only the unchanged words from the beginning and end of the sentence are taken into account. All others are considered unmatched.
- Errors are counted only on words that were marked by **all** libraries – this allows accuracy comparison without distortion from text changes.
- The **real gold standard** (`gold/pattern.txt`) is not included in the repository – a placeholder is provided. Use your own annotated text.
- There is a dictionary of words with multiple allowed stress positions – such words are ignored.
- Words with hyphens are **not tested**.
- The code is raw and has been lightly tested. Results are preliminary.

## Requirements

- Python 3.x
- Dependencies from `requirements.txt`

## Quick start

```bash
# 1. Initialize configuration
python benchmark.py init

# 2. Run the full benchmark
python benchmark.py run --gold gold/pattern.txt
```

## Management via `benchmark.py`

`benchmark.py` is a single orchestrator. It controls the pipeline:
`split → extract_gold → [run_adapter] × N → compare → report`

### Commands

| Command | Description |
|---------|-------------|
| `init` | Create `benchmark_config.json` |
| `run` | Run the benchmark |
| `status` | Show cache status |
| `clean` | Clear cache |
| `list-adapters` | Show available adapters |

### Examples

```bash
# Full run
python benchmark.py run --gold gold/pattern.txt

# Only specified libraries
python benchmark.py run --gold gold/pattern.txt --libs silero_stress,udarenie

# Re-run a specific library
python benchmark.py run --gold gold/pattern.txt --libs accent_engine --force

# Status
python benchmark.py status --gold gold/pattern.txt

# List adapters
python benchmark.py list-adapters

# Clear cache
python benchmark.py clean --all
```

### Configuration (`benchmark_config.json`)

```json
{
  "libraries": [
    {
      "name": "silero_stress",
      "description": "Silero stress placement"
    },
    {
      "name": "udarenie",
      "description": "Udarenie with morphology"
    }
  ],
  "output_dir": "output",
  "cache_dir": ".benchmark_cache",
  "adapters_dir": "adapters",
  "dubious_file": "gold/dubious.txt",
  "reports": "both"
}
```

| Field | Description |
|-------|-------------|
| `name` | Library name (matches the adapter filename without `.py`) |
| `description` | Description used in reports |
| `output_dir` | Directory for results |
| `cache_dir` | Directory for cache |
| `adapters_dir` | Directory containing adapters |
| `dubious_file` | Dictionary of words with variable stress |
| `reports` | `"ru"`, `"en"`, or `"both"` |

## Adding new libraries

To add a new library, you only need **two steps**:

### Step 1: Create an adapter

```bash
cp adapters/_template.py adapters/my_library.py
```

Edit the `Accentuator` class:

```python
class Accentuator:
    def __init__(self):
        """Load model / data."""
        from my_library import StressPlacer
        self.placer = StressPlacer.load("path/to/model")

    def accentuate(self, text: str) -> str:
        """Place stress in a single sentence."""
        return self.placer.place_stress(text)

    def description(self) -> str:
        """Description for reports."""
        return "My awesome stress library"
```

### Step 2: Add to config

```json
{
  "libraries": [
    ...
    {"name": "my_library", "description": "My awesome stress library"}
  ]
}
```

Done:

```bash
python benchmark.py run --gold gold/pattern.txt --libs my_library
```

For more details, see [ADDING_LIBRARIES.md](ADDING_LIBRARIES.md).

## Manual adapter testing

```bash
# Prepare test input
echo '{"sentences":[{"original_text":"В л+есу род+илась ёлочка."}]}' > test_input.json

# Run the runner
python adapters/runner.py adapters.my_library test_input.json test_output.json

# Check result
cat test_output.json | python -m json.tool
```

## Architecture

```
russian-stress-benchmark/
├── benchmark.py              # Single orchestrator
├── benchmark_config.json     # Configuration
├── README.md
├── requirements.txt
│
├── adapters/                 # Library adapters
│   ├── runner.py             # Unified runner (common logic)
│   ├── _template.py          # Template for new adapters
│   ├── silero_stress.py
│   ├── udarenie.py
│   └── accent_engine.py
│
├── core/                     # Pipeline steps
│   ├── split_text_by_lines.py
│   ├── extract_accentuation.py
│   ├── compare_accentuators.py
│   ├── generate_report.py
│   └── generate_report_en.py
│
├── gold/
│   └── pattern.txt           # Gold standard (placeholder)
│
└── output/                   # Results (created automatically)
    ├── raw/
    ├── lib/
    ├── comparison.json
    ├── report.md
    └── report_en.md
```

**Adapter** – a minimal module that knows only about its library.  
**Runner** (`adapters/runner.py`) – common logic: timing, normalisation, saving.  
**Orchestrator** (`benchmark.py`) – manages the pipeline, cache, and reports.

## Script descriptions

### `benchmark.py`
Single orchestrator. Manages the pipeline: `split → extract_gold → [run_adapter] × N → compare → report`. Supports caching, incremental runs, and status checking.

### `adapters/runner.py`
Unified runner for all adapters. Takes a module name, dynamically imports `Accentuator`, measures loading and processing times, normalises stress marks, and saves results.

### `core/split_text_by_lines.py`
Splits the input text into sentences (by lines) and saves as JSON. Supports automatic encoding detection.

### `core/extract_accentuation.py`
Extracts word‑by‑word stress markup. Modes:
- `--mode gold` – gold standard markup
- `--mode lib` – library results

### `core/compare_accentuators.py`
Compares library results against the gold standard. Counts errors, omissions, unmatched words, and metrics on common words.

### `core/generate_report.py` / `core/generate_report_en.py`
Generate Markdown reports in Russian and English.

## Overall pipeline scheme

```
gold/pattern.txt
       │
       ▼
core/split_text_by_lines.py
       │
       ▼
output/pattern.json
       │
       ├──► core/extract_accentuation.py --mode gold
       │           │
       │           ▼
       │    output/lib/GOLD_results.json
       │
       ├──► adapters/runner.py adapters.<lib1>
       │           │
       │           ▼
       │    output/raw/<lib1>_results.json
       │           │
       │           ▼
       │    core/extract_accentuation.py --mode lib
       │           │
       │           ▼
       │    output/lib/<lib1>_results.json
       │
       ├──► adapters/runner.py adapters.<lib2> ──► ...
       │
       ▼
core/compare_accentuators.py ──► output/comparison.json
                                       │
                                       ├──► core/generate_report.py ──► output/report.md
                                       │
                                       └──► core/generate_report_en.py ──► output/report_en.md
```

## Results

After the pipeline completes, the `output/` directory contains:
- `pattern.json` – the gold standard split into sentences
- `lib/GOLD_results.json` – word‑by‑word markup of the gold standard
- `raw/` – raw adapter results
- `lib/` – results with word‑by‑word markup
- `comparison.json` – comparison data
- **`report.md`** – final report in Russian
- **`report_en.md`** – final report in English

## Warning

This project is the result of vibe coding. The code is raw, has been lightly tested, and results should be considered preliminary. Use at your own risk.

---

*Repository: [github.com/omogr/russian-stress-benchmark](https://github.com/omogr/russian-stress-benchmark)*
