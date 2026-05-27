# Chapter 3 Evaluation Results — Blind Grading

Final results of the blind, criterion-based evaluation of eight retrieval
systems over a 30-question historical benchmark. These files are the data
behind Figures 3.6–3.11.

> The `preliminary_` filename prefix is **legacy script naming only** — the
> contents here are the **final** results of record for the thesis.

## Evaluation design

- **30 questions** across five difficulty tiers:
  | Tier | Theme | Questions |
  |---|---|---|
  | T1 | Factual | Q1–Q4 |
  | T2 | Temporal | Q5–Q10 |
  | T3 | Relational | Q11–Q18 |
  | T4 | Analytical | Q19–Q26 |
  | T5 | Interpretive | Q27–Q30 |

  The exact question text is in `../queries/eval-questions.json`.
- **Five scoring criteria**, each on a 1–5 scale (max total 25): Groundedness,
  Completeness, Accuracy, Synthesis, Usefulness.
- **Blind grading**: system identities were hidden behind randomized labels
  during grading; `grading_key.json` is the (post-rerandomize) map from blind
  label back to system. The grader saw only the labels.

## Systems compared (overall mean, n)

| System | Mean / 25 | n |
|---|---|---|
| `improved_scratchpad` | **17.78** | 23 |
| `self_rag_rag` | 15.40 | 30 |
| `graphrag_kg_vector` | 14.73 | 30 |
| `self_rag_graphrag` | 14.57 | 30 |
| `graphrag_plus_kg` | 14.40 | 30 |
| `true_graphrag` | 12.90 | 30 |
| `rag_only` | 12.10 | 30 |
| `kg_plus_rag` | 11.37 | 30 |

> **Note on `improved_scratchpad` (n=23).** The Improved Scratchpad system was
> added to the evaluation after Q1–Q7 had already been graded, so it only ever
> produced answers for **Q8–Q30** (23 questions). Because all four T1-Factual
> questions are Q1–Q4, `improved_scratchpad` has no T1 scores. This is the
> intended final state, not partial grading.

## File inventory

| File | Description |
|---|---|
| `blind_grading_complete.xlsx` | Raw blind-grading workbook (final, complete) — preserved for provenance |
| `grading_key.json` | Blind-label → system map matching the complete workbook |
| `preliminary_grading_summary.csv` | Per-system overall mean, stdev, and per-criterion means |
| `preliminary_grading_per_tier.csv` | Per-system mean score broken down by tier (T1–T5) |
| `extended_answer_stats.csv` | Answer length / structure statistics |
| `extended_coverage.csv` | Corpus-coverage statistics |
| `extended_discrimination.csv` | Per-question (Q1–Q30) mean / stdev / min / max |
| `extended_latency.csv` | Per-system latency |
| `extended_pairwise.csv` | Pairwise comparison statistics |
| `retrieval_diversity_intersection.csv` | Unique documents/chunks surfaced per system |

The full per-system answer logs (`*_results.json`) and the raw grading
documents are larger and are included in the Zenodo knowledge-graph deposit
rather than committed here.

License: CC-BY-4.0 (see `../../LICENSE-DATA`).
