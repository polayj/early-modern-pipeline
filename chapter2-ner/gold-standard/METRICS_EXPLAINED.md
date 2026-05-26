# Extended NER Evaluation Metrics

This document explains the metrics computed by `evaluate_ner_extended.py` for evaluating Named Entity Recognition systems on the historical Caribbean trade corpus.

## 1. SemEval 4-Category Matching

Based on the SemEval-2013 Task 9.1 evaluation framework. Every gold-prediction entity pair is classified into one of four categories, each defining a progressively relaxed notion of "correct":

| Schema    | Boundary   | Entity Type | What it measures |
|-----------|-----------|-------------|------------------|
| **Strict**  | Exact match | Must match  | Full correctness: the model found exactly the right span with the right label |
| **Exact**   | Exact match | Ignored     | Boundary detection quality regardless of labelling |
| **Partial** | Any overlap | Must match  | Entity detection with the right label, tolerating boundary errors |
| **Type**    | Any overlap | Ignored     | Any entity detection, tolerating both boundary and label errors |

For each schema, standard Precision, Recall, and F1 are computed.

**How to interpret:** The gap between Strict and Exact F1 reveals type confusion (correct boundaries, wrong label). The gap between Strict and Partial F1 reveals boundary errors (right label, imprecise span). A large gap between Partial and Type indicates the model often detects entities but assigns the wrong label.

**Formulas:**
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * P * R / (P + R)

Where TP is defined differently per schema (strict requires exact boundary + correct type; partial gives half-credit for overlapping boundaries with correct type, etc.).

## 2. Confusion Matrix

A table showing gold label (rows) vs. predicted label (columns), including an "O" class for missed/spurious entities.

| Cell | Meaning |
|------|---------|
| COMMODITY -> COMMODITY | Correctly identified commodities |
| COMMODITY -> TOPONYM | Gold commodity misclassified as toponym |
| COMMODITY -> O | Gold commodity that the model missed entirely |
| O -> TOPONYM | Spurious toponym prediction (no matching gold entity) |

**How to interpret:** Diagonal cells are correct predictions. Off-diagonal cells (excluding O) reveal systematic type confusions. The O column shows what the model misses; the O row shows what it hallucinates. Row sums equal the total gold count per label.

## 3. Slot Error Rate (SER)

A single number summarising overall error rate, analogous to Word Error Rate in speech recognition.

**Formula:** SER = (S + D + I) / N

- **S (Substitutions):** Gold entity matched by boundary overlap but assigned the wrong label
- **D (Deletions):** Gold entity with no matching prediction (false negative)
- **I (Insertions):** Prediction with no matching gold entity (false positive)
- **N:** Total number of gold entities

**How to interpret:**
- SER = 0: Perfect system
- SER < 1: More correct entities than errors
- SER = 1: Errors equal the number of gold entities
- SER > 1: More errors than gold entities (e.g., a model that produces many spurious predictions)

**Complements F1 by:** distinguishing between different error types (substitution vs. deletion vs. insertion) and providing a single intuitive error rate rather than the precision/recall trade-off.

## 4. Boundary Analysis

For entities where the model found the right label and boundaries overlap but are not exact ("partial" matches), this metric analyses the direction and magnitude of boundary errors.

| Metric | Meaning |
|--------|---------|
| Left trimmed | Prediction starts after gold start (model missed the beginning) |
| Left extended | Prediction starts before gold start (model included extra leading text) |
| Right trimmed | Prediction ends before gold end (model missed the ending) |
| Right extended | Prediction ends after gold end (model included extra trailing text) |
| Avg left offset | Mean character offset at the left boundary (negative = extended) |
| Avg right offset | Mean character offset at the right boundary (positive = extended) |

**How to interpret:** A model with many "left extended" errors systematically includes preceding words (e.g., articles like "the"). A model with "right trimmed" errors systematically drops suffixes. The average offsets reveal the typical magnitude: an avg left offset of -5.8 means predictions start ~6 characters too early on average.

## 5. Entity Diversity

Measures how well a model covers the vocabulary of entity surface forms in the gold standard.

| Metric | Meaning |
|--------|---------|
| Gold unique | Number of distinct entity text forms in the gold standard |
| Pred unique | Number of distinct entity text forms predicted by the model |
| Overlap | Number of unique forms that appear in both gold and predictions |
| Coverage ratio | Overlap / Gold unique (what fraction of gold vocabulary was found) |
| Hapax legomena | Forms appearing exactly once (indicates vocabulary breadth) |

**How to interpret:** A high coverage ratio means the model recognises a wide variety of entity forms, not just frequent ones. Low coverage with high F1 suggests the model only detects common entities. Per-label breakdowns reveal if coverage is uneven (e.g., good toponym coverage but poor commodity coverage).

## 6. Throughput and Latency (Optional)

When timing data is collected by re-running models through the `time_model_run()` utility:

| Metric | Meaning |
|--------|---------|
| Mean latency | Average processing time per document |
| Median latency | Typical processing time (less affected by outliers) |
| P95 latency | 95th percentile (worst-case realistic latency) |
| Throughput | Characters processed per second |
| Peak memory | Maximum memory usage during processing |

**How to interpret:** Useful for comparing computational cost alongside accuracy. A model with marginally lower F1 but 10x higher throughput may be preferable for large-scale processing.

## How the Metrics Complement Each Other

- **SemEval F1** gives the headline accuracy numbers at different strictness levels
- **Confusion matrix** explains *where* errors occur (which labels get confused)
- **SER** provides a single error rate that accounts for all error types
- **Boundary analysis** explains *how* boundary errors manifest (systematic patterns)
- **Entity diversity** reveals whether the model generalises across the entity vocabulary or just detects frequent forms

Together, these metrics provide a complete picture: overall performance (SemEval), error decomposition (SER, confusion matrix), error characterisation (boundary analysis), and vocabulary coverage (diversity).
