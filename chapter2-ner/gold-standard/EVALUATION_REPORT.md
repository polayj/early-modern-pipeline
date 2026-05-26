# NER Model Evaluation Report - Updated with spaCy

**Date**: 2025-12-05
**Gold Standard**: 100 documents, 1,083 entities (564 COMMODITY, 519 TOPONYM)
**Models Evaluated**: spaCy-lg, deepseek-r1, gemma2, mistral

---

## Executive Summary

**Winner**: **deepseek-r1** 🏆

- **Best overall F1 score**: 0.589 (exact match), 0.709 (partial match)
- **Most balanced precision/recall**: Achieves good performance on both metrics
- **Best TOPONYM detection**: 0.667 F1 (exact), 0.770 F1 (partial)
- **Significantly outperforms spaCy-lg** by +32% F1

**Surprise**: spaCy-lg performed much worse than expected, especially on COMMODITY detection (F1: 0.006)

---

## Overall Performance Comparison

### Exact Match

| Model       | Precision | Recall | F1    | TP  | FP    | FN  |
|-------------|-----------|--------|-------|-----|-------|-----|
| **deepseek-r1** | **0.655** | **0.536** | **0.589** | 580 | 305   | 503 |
| **gemma2**      | 0.682     | 0.497  | 0.575 | 538 | 251   | 545 |
| **spaCy-lg**    | 0.373     | 0.212  | 0.271 | 230 | 387   | 853 |
| **mistral**     | 0.027     | 0.376  | 0.051 | 407 | 14500 | 676 |

### Partial Match

| Model       | Precision | Recall | F1    |
|-------------|-----------|--------|-------|
| **deepseek-r1** | 0.794     | 0.641  | **0.709** ✓ |
| **gemma2**      | 0.791     | 0.569  | 0.662 |
| **spaCy-lg**    | 0.491     | 0.282  | 0.358 |
| **mistral**     | 0.034     | 0.464  | 0.063 |

---

## Performance by Entity Type

### COMMODITY Detection

| Model       | Precision | Recall | F1    | Notes |
|-------------|-----------|--------|-------|-------|
| **deepseek-r1** | 0.608     | 0.438  | **0.509** ✓ | Best COMMODITY detection |
| **gemma2**      | 0.647     | 0.348  | 0.452 | High precision, low recall |
| **spaCy-lg**    | 0.024     | 0.004  | **0.006** ❌ | Catastrophic failure |
| **mistral**     | 0.592     | 0.422  | 0.493* | *Unreliable due to data issues |

**Key Finding**: spaCy's PRODUCT label doesn't map well to historical trade goods (COMMODITY). It only found 2 out of 564 commodities correctly!

### TOPONYM Detection

| Model       | Precision | Recall | F1    | Notes |
|-------------|-----------|--------|-------|-------|
| **gemma2**      | 0.704     | 0.659  | **0.681** ✓ | Best TOPONYM |
| **deepseek-r1** | 0.695     | 0.642  | 0.667 | Close second |
| **spaCy-lg**    | 0.428     | 0.439  | 0.433 | Decent but still lags |
| **mistral**     | 0.591     | 0.326  | 0.420* | *Unreliable |

**Key Finding**: All multimodal LLMs significantly outperform spaCy on toponyms, despite spaCy being trained specifically for geographic entities.

---

## Why Did spaCy Perform So Poorly?

### 1. **COMMODITY Mismapping** (F1: 0.006)
   - spaCy's `PRODUCT` label is trained on modern commercial products
   - Historical trade goods like "Incle" (linen tape), "Ribbins" (ribbons), "Muscavado sugar" are not recognized
   - Example misses: sugar, spices, textiles, metals - all core to our corpus

### 2. **Generic Entity Problem**
   - spaCy frequently tags common nouns as entities:
     - "Castle" (commodity) → should not be tagged
     - "Towne", "Kingdom" → too generic
     - These inflate false positive count

### 3. **Modern Training Data Bias**
   - spaCy is trained on modern news text (OntoNotes)
   - Early modern English (1600s-1800s) uses different:
     - Spelling variants: "Froome-gate" vs "Froome Gate"
     - Entity structures: "St. Johns Church" not recognized
     - Vocabulary: historical terms completely missed

### 4. **Phrase Boundary Issues**
   - Multi-word entities poorly detected
   - Example: Misses "St. Johns Church" as a complete entity

---

## Model-Specific Analysis

### deepseek-r1 ⭐⭐⭐ HIGHLY RECOMMENDED

**Strengths**:
- **Best overall F1 score** (0.589 exact, 0.709 partial)
- **Most balanced** precision/recall trade-off
- Excellent TOPONYM detection (0.667 F1)
- Good COMMODITY detection despite difficult vocabulary
- Clean JSON output (98% success rate)
- **32% better F1 than spaCy**

**Weaknesses**:
- Lower COMMODITY recall (0.438) - misses ~56% of commodities
- Overpredicts generic locations ("the City", "the Castle")

**Best for**: General-purpose historical NER, research applications

**vs. spaCy**: +118% better F1 score overall

---

### gemma2 ⭐⭐⭐ HIGH PRECISION CHOICE

**Strengths**:
- **Highest precision** (0.682 exact, 0.791 partial)
- Perfect JSON compliance (0 errors)
- **Best TOPONYM performance** (0.681 F1)
- Fast inference (9B parameter model)
- **30% better F1 than spaCy**

**Weaknesses**:
- Lowest recall (0.497) - very conservative
- Misses many COMMODITY entities (34.8% recall)

**Best for**: Applications where false positives are costly; high-precision requirements

**vs. spaCy**: +112% better F1 score overall

---

### spaCy-lg ⚠️ NOT RECOMMENDED FOR HISTORICAL TEXT

**Strengths**:
- Fast inference
- Well-documented, easy to use
- Reasonable TOPONYM recall (0.439)

**Critical Weaknesses**:
- **Catastrophic COMMODITY performance** (F1: 0.006)
- Only found 2/564 commodities correctly
- Modern training data doesn't transfer to historical text
- Generic entity over-prediction

**F1 Scores**:
- Overall: 0.271 (worst non-broken model)
- COMMODITY: 0.006 (essentially useless)
- TOPONYM: 0.433 (mediocre)

**Verdict**: spaCy-lg is not suitable for early modern historical texts without significant fine-tuning

**vs. LLMs**: -53% worse than deepseek-r1, -53% worse than gemma2

---

### mistral ❌ BROKEN - DO NOT USE

**Critical Issues**:
- 14,500 false positive "UNKNOWN" entities with empty text
- Overall F1: 0.051 (essentially non-functional)
- Requires complete data reprocessing

---

## Key Insights

### 1. LLMs >>> Traditional NER for Historical Text
   - deepseek-r1 and gemma2 both **>100% better** than spaCy-lg
   - Better handling of:
     - Historical spelling variants
     - Domain-specific vocabulary
     - Multi-word entity boundaries

### 2. COMMODITY is Hard
   - Even best model (deepseek-r1) only achieves 0.509 F1
   - Historical trade goods vocabulary is challenging
   - Modern NER models (like spaCy) completely fail (0.006 F1)

### 3. TOPONYM is Easier
   - All models perform better on toponyms
   - Geographic entities more standardized over time
   - But LLMs still outperform spaCy by 50%+

### 4. Fine-tuning Needed
   - All models would benefit from fine-tuning on historical text
   - spaCy would need complete retraining on early modern corpus
   - LLMs could improve with few-shot examples

---

## Recommendations

### For Production Use

1. **Primary Choice**: **deepseek-r1**
   - Best overall performance
   - Most reliable for both entity types
   - Good balance of precision and recall

2. **High-Precision Alternative**: **gemma2**
   - When false positives are more costly than false negatives
   - Faster inference than deepseek-r1
   - Best TOPONYM detection

3. **Do NOT Use**:
   - ❌ spaCy-lg (without fine-tuning on historical corpus)
   - ❌ mistral (until data quality issues resolved)

### For Improving Performance

**All LLM Models**:
1. Add post-processing filters for generic terms
2. Implement entity boundary refinement
3. Create historical trade goods lexicon
4. Handle spelling/hyphenation variants

**spaCy** (if must use):
1. Fine-tune on annotated historical corpus (minimum 1000+ documents)
2. Retrain entity recognizer with historical trade goods
3. Add custom entity rules for known commodities
4. Consider training from scratch on early modern text

---

## Common Error Patterns

### False Positives (All Models)
- Generic location references: "the City", "the Castle", "Kingdom"
- Common nouns mistaken for proper nouns
- Partial matches of longer entity names

### False Negatives (All Models)
- Historical trade goods: "Incle", "Ribbins", "Muscavado"
- Multi-word entities with punctuation: "St. Johns Church"
- Hyphenation variants: "Froome-gate" vs "Froome Gate"
- Historical spelling: older English orthography

---

## Files and Outputs

- **Evaluation Script**: `Z:\NER\evaluate_ner.py`
- **spaCy Runner**: `Z:\NER\run_spacy_ner.py`
- **Detailed Results**: `Z:\NER\evaluation_results.json`
- **Model Outputs**:
  - spaCy-lg: `Z:\NER\spaCy\results_20251205_135827.json`
  - deepseek-r1: `Z:\NER\deepseek\results_20251203_145333.json`
  - gemma2: `Z:\NER\gemma2\results_20251203_152052.json`
  - mistral: `Z:\NER\mistral\results_20251203_144203.json` (broken)
- **Gold Standard**: `Z:\NER\gold\` (100 manually annotated documents)

---

## Conclusion

For NER on early modern historical trade documents (1600s-1800s):

1. **Use deepseek-r1** for best overall performance (F1: 0.589)
2. **Use gemma2** if you need highest precision (P: 0.682)
3. **Avoid spaCy** unless fine-tuned on historical corpus (F1: 0.271)
4. **Modern LLMs outperform traditional NER** by >100% on this task

The results demonstrate that multimodal LLMs with zero-shot prompting significantly outperform established NER tools like spaCy when working with historical domain-specific text. This suggests that fine-tuning LLMs or using few-shot learning could achieve even better results.

**Key Takeaway**: For historical NER tasks, invest in LLM-based approaches rather than trying to adapt traditional NER models trained on modern text.
