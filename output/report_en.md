# Report on Stress Placement Library Comparison

> Automatically generated report based on comparing library outputs against manual annotations.

## General Information

| Parameter | Value |
|-----------|-------|
| Test date | `2026-07-19T13:55:18.263975` |
| Test set (sentences) | **272** |
| Gold standard file | `GOLD_results.json` |
| Number of libraries compared | **3** |

### Compared Libraries

1. `accent_engine`
2. `silero_stress`
3. `udarenie`

## Performance

Comparison of loading time, processing time, and stability of the libraries.

| Library | Load (sec) | Process (sec) | Exceptions |
|---------|------------|---------------|------------|
| `accent_engine` | 8.3454 | 5.3898 | 0 ✅ |
| `silero_stress` | 1.9638 | 5.9613 | 0 ✅ |
| `udarenie` | 9.9203 | 6.4472 | 0 ✅ |

**Total:** load — 20.2295 sec, process — 17.7983 sec, exceptions — 0

## Errors in Library Outputs

Comparison of stress placement quality and word matching against the gold standard.

| Library | Stress Errors | Missing Stress | Word Count Mismatch | Word Text Mismatch | Sentences with Mismatches |
|---------|---------------|----------------|---------------------|--------------------|---------------------------|
| `accent_engine` | 33 | 0 | 0 | 0 | 0 |
| `silero_stress` | 52 | 6 | 0 | 0 | 0 |
| `udarenie` | 30 | 0 | 0 | 0 | 0 |

**Total across all libraries:** stress errors — 115, missing — 6, count mismatch — 0, text mismatch — 0, sentences with mismatches — 0

## Comparison on Common Words

Words that were successfully annotated by **all** compared libraries. This allows for quality comparison on equal terms.

| Library | Total Common Words | Stress Errors | Accuracy |
|---------|--------------------|---------------|----------|
| `accent_engine` | 8 630 | 33 | 99.62% |
| `silero_stress` | 8 630 | 52 | 99.40% |
| `udarenie` | 8 630 | 30 | 99.65% |

✅ Total number of words annotated by all libraries: **8 630** (matches across all libraries).

## Detailed Summary by Library

### `accent_engine`

- **Sentences processed:** 272
- **Words matched with gold standard:** 13 420
- **Words with stress in gold standard:** 8 636
- **Load time:** 8.3454 sec
- **Process time:** 5.3898 sec
- **Exceptions:** 0

**Errors:**
- Incorrectly placed stress: **33**
- Missing stress: **0**
- Word count mismatch: **0**
- Word text mismatch: **0**
- Sentences with mismatches: **0**

**Common words:** 8 630 words, errors: 33, accuracy: **99.62%**

### `silero_stress`

- **Sentences processed:** 272
- **Words matched with gold standard:** 13 420
- **Words with stress in gold standard:** 8 636
- **Load time:** 1.9638 sec
- **Process time:** 5.9613 sec
- **Exceptions:** 0

**Errors:**
- Incorrectly placed stress: **52**
- Missing stress: **6**
- Word count mismatch: **0**
- Word text mismatch: **0**
- Sentences with mismatches: **0**

**Common words:** 8 630 words, errors: 52, accuracy: **99.40%**

### `udarenie`

- **Sentences processed:** 272
- **Words matched with gold standard:** 13 420
- **Words with stress in gold standard:** 8 636
- **Load time:** 9.9203 sec
- **Process time:** 6.4472 sec
- **Exceptions:** 0

**Errors:**
- Incorrectly placed stress: **30**
- Missing stress: **0**
- Word count mismatch: **0**
- Word text mismatch: **0**
- Sentences with mismatches: **0**

**Common words:** 8 630 words, errors: 30, accuracy: **99.65%**

---

*Report generated: 2026-07-19T13:55:18.469730*
