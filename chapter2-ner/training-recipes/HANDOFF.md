# Handoff Instructions — Extended NER Evaluation (4-Category, 12 Models)

## What Was Done

### Phase 1: Original Evaluation
1. **Created `evaluate_ner_extended.py`** — multi-metric evaluation script with:
   - Text-based matching with normalization (lowercase, strip "the ", hyphens→spaces, collapse whitespace)
   - Set-deduplicated per document (1 "Sugar" per doc regardless of occurrences)
   - Strict F1 (exact normalized text + same label) and Partial F1 (+ substring matches)
   - Confusion matrix, Slot Error Rate, Entity diversity
   - Auto-discovery of result files from `run_all_ner.py` output directories

2. **Created `METRICS_EXPLAINED.md`** — explains all metrics in plain language.

### Phase 2: Full 4-Category Re-run (Feb 2026)
3. **Created `run_all_ner.py`** — unified NER runner for all models:
   - Reads gold_reviewed/ JSON files as input (100 documents)
   - Uses earlymodernner prompts (`earlymodernner/constants.py`) for all LLMs
   - Supports single-pass and ensemble modes for Ollama LLMs
   - Tracks timing metadata (total time, avg per doc, throughput)
   - Outputs standardized JSON with entities, tokens, IOB tags

4. **Installed dependencies:** spacy, gliner, flair, Stanford NER (Java)

5. **Ran all models with 4 entity categories:**

#### Phase A — Fast Models (completed)
| Model | Time (100 docs) | Entities | COMM | TOPO | PER | ORG |
|-------|-----------------|----------|------|------|-----|-----|
| spaCy-lg | 57s | 3273 | 128 | 881 | 842 | 1422 |
| GLiNER | 181s | 1322 | 245 | 375 | 519 | 183 |
| Flair NLP | 82s | 2140 | 0 | 820 | 974 | 346 |
| BERT-large | 9s | 1240 | 0 | 659 | 413 | 168 |
| mBERT | 3s | 1778 | 0 | 756 | 475 | 547 |
| Stanford NER | 162s | 1539 | 0 | 642 | 600 | 297 |
| GATE ANNIE | ~120s | 1869 | 0 | 602 | 1083 | 184 |

#### Phase B — LLM Single-Pass (via Ollama)
| Model | Time (100 docs) | Entities | COMM | TOPO | PER | ORG |
|-------|-----------------|----------|------|------|-----|-----|
| gemma2:9b | 25,524s (~7h) | 1314 | 556 | 444 | 192 | 122 |
| deepseek-r1 | KILLED at 5/100 (needs restart) | - | - | - | - | - |
| mistral | SKIPPED (too slow) | - | - | - | - | - |
| GoLLIE | FAILED (inference errors, 0 entities) | - | - | - | - | - |

#### earlymodernner (existing results)
| Model | Entities | COMM | TOPO | PER | ORG |
|-------|----------|------|------|-----|-----|
| earlymodernner | 816 | 393 | 280 | 115 | 28 |
- Results converted from `earlymodernner/_archive/testresults.jsonl`
- Conversion script: `convert_earlymodernner.py`

#### Phase C — LLM Ensemble (PENDING)
Run with `python run_all_ner.py --models gemma2 deepseek --ensemble`

## Results (11 models, text-based matching with normalization)

Evaluation uses text-based matching: entities are normalized (lowercase, strip "the ", hyphens→spaces, collapse whitespace), deduplicated per document, and matched by text+label. Partial F1 additionally credits substring matches (e.g. "Lords of Trade" ≈ "Lords of Trade and Plantations").

| Model | Strict F1 | Partial F1 | SER | Coverage |
|-------|-----------|------------|-----|----------|
| earlymodernner | 0.7754 | 0.8233 | 0.33 | 0.7287 |
| gemma2 | 0.5696 | 0.5982 | 0.73 | 0.5630 |
| GLiNER | 0.4048 | 0.4590 | 0.94 | 0.3578 |
| MacBERTh | 0.3659 | 0.5998 | 0.80 | 0.3050 |
| Flair NLP | 0.3410 | 0.4567 | 1.07 | 0.4047 |
| Stanford NER | 0.2907 | 0.3926 | 1.07 | 0.3739 |
| BERT-large | 0.2884 | 0.4211 | 0.89 | 0.1994 |
| mBERT | 0.2357 | 0.3639 | 1.04 | 0.1994 |
| GATE ANNIE | 0.2073 | 0.2735 | 1.36 | 0.2287 |
| spaCy-lg | 0.1980 | 0.2719 | 1.94 | 0.5191 |
| GoLLIE | 0.0000 | 0.0000 | 1.00 | 0.0000 |

### Key Observations
- **earlymodernner leads** across all metrics (0.78 Strict F1, 0.33 SER, 0.73 coverage)
- **earlymodernner has highest precision** (0.83) with very few false positives (94 insertions)
- **gemma2 is the best single LLM** at 0.57 Strict F1
- **Only earlymodernner, gemma2, GLiNER, and MacBERTh extract COMMODITY** — all other models lack commodity detection
- **GLiNER is the best zero-shot model** at 0.40 Strict F1
- **MacBERTh benefits most from partial matching** (0.37→0.60 F1) — many substring matches
- **spaCy has aggressive over-prediction** (1931 pred vs 938 gold dedup) tanking precision
- **Traditional NER models** (Stanford, Flair, BERT, mBERT, GATE) cannot detect COMMODITY entities — they only have LOC/PER/ORG label sets
- **GoLLIE** produced 0 entities (inference errors) — only 2 docs matched

### Per-Label Best Performers (Strict F1)
| Label | Best Model | F1 |
|-------|-----------|-----|
| COMMODITY | earlymodernner | 0.7407 |
| TOPONYM | earlymodernner | 0.8241 |
| PERSON | earlymodernner | 0.7594 |
| ORGANIZATION | earlymodernner | 0.5294 |

## Pending Work
1. **Re-run DeepSeek** — killed at 5/100 docs, needs full 100-doc run
2. **Fix or skip GoLLIE** — inference errors ('NoneType' has no attribute 'shape'), 0 entities produced
3. **Run ensemble mode** for gemma2 and deepseek (once deepseek completes)
4. **Re-run evaluation** after pending models complete

## Gold Standard Details
- Location: `gold_reviewed/` (100 docs)
- Entity counts: COMMODITY: 610, TOPONYM: 496, PERSON: 154, ORGANIZATION: 56 (total 1316)
- Evaluation uses text-based matching (no span offsets needed)
- Entities deduplicated per doc: 938 unique (text, label) pairs across 100 docs

## Model Result Files
Results auto-discovered from these directories:
- `spaCy_4cat/`, `gliNER_4cat/`, `gemma2_4cat/`, `mistral_4cat/`, `deepseek_4cat/`
- `stanford_4cat/`, `gate_4cat/`, `flair_4cat/`, `deberta_4cat/`, `mbert_4cat/`
- `gollie_4cat/` (broken — 0 entities)
- `earlymodernner_4cat/` (converted from JSONL)
- Ensemble: `*_4cat_ensemble/` directories
- MacBERTh: `macberth_gold_eval/macberth_gold_results_20251210_170140_fixed.json`

## How to Run

```bash
# Run fast models
python3 run_all_ner.py --models spacy gliner flair deberta mbert stanford

# Run LLMs (single-pass)
python3 run_all_ner.py --models gemma2 deepseek

# Run LLMs (ensemble mode)
python3 run_all_ner.py --models gemma2 deepseek --ensemble

# Run evaluation
python3 evaluate_ner_extended.py

# Test mode (first 3 docs)
python3 run_all_ner.py --models spacy --test --test-limit 3
```

## Configuration
- **Ollama URL:** `http://Jacobs-Computer.local:11434` (set in `run_all_ner.py`)
- **Prompts:** `earlymodernner/earlymodernner/constants.py` (SYSTEM_PROMPT for single-pass, SYSTEM_PROMPTS for ensemble)
- **Stanford NER:** `/mnt/z/NER/stanford-ner/stanford-ner-2020-11-17/`
