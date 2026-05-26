# Chapter 2 — Named Entity Recognition

Materials accompanying Chapter 2 of *Loud Yet Invisible: A Humanist-Designed Pipeline for Unlocking the Early Modern Archive*. This chapter benchmarks 15 NER systems on early modern text and introduces **EarlyModernNER**, a cascading entity-type-specialized model trained on top of Qwen3-4B-Instruct.

## What's in here

```
chapter2-ner/
├── README.md
├── earlymodernner/            # Source of the EarlyModernNER package (code only)
│   ├── README.md / LICENSE / pyproject.toml / requirements.txt
│   ├── docs/                  # Architecture and usage docs
│   └── earlymodernner/        # Python package
│       ├── __init__.py, __main__.py, version.py
│       ├── constants.py, normalization.py, metrics.py, pipeline.py
│       └── adapters/          # ! Weights NOT included — see Zenodo (link in data/)
├── gold-standard/
│   ├── annotations/           # 100 fully annotated documents (JSON)
│   ├── reviewed/              # Reviewer-corrected versions of the same set
│   ├── ENTITY_GUIDELINES.md   # What counts as a person, place, organization, commodity
│   ├── DOMAIN_ANALYSIS_REPORT.md
│   ├── EVALUATION_REPORT.md
│   ├── METRICS_EXPLAINED.md
│   └── PROJECT_CONTEXT.md
├── evaluation/                # Cross-model evaluation harness
│   ├── batch_process_ner.py
│   ├── evaluate_ner.py / evaluate_ner_extended.py
│   ├── compare_ner_models.py / compare_gliner_models.py / compare_all_models.py
│   ├── final_ner_comparison.py
│   └── *_results.json         # Cached evaluation runs
├── training-recipes/
│   ├── train_lora.py          # LoRA / DoRA fine-tuning script
│   ├── prepare_training_data.py
│   ├── generate_synthetic_training.py
│   ├── evaluate.py            # In-package evaluation script
│   ├── training.md            # Training notes and lessons learned
│   ├── config/                # Per-entity-type YAML configs
│   │   ├── ensemble_commodity_augmented.yaml
│   │   ├── ensemble_organization_augmented.yaml
│   │   ├── ensemble_person_augmented.yaml
│   │   ├── ensemble_toponym_silver.yaml
│   │   └── template.yaml
│   └── HANDOFF.md / PROGRESS.json
├── results/                   # Aggregate JSON results
└── figures/                   # Chapter 2 figures (2.1–2.8)
```

## Systems tested

The thesis compares 15 systems organized into three families:

- **Statistical / classical**: spaCy, Stanford NER, Flair, GATE ANNIE
- **Domain-pretrained transformers**: MacBERTh, hmBERT
- **General LLMs (prompted)**: Gemini 3 Pro, gemma2, Mistral 7B, Qwen3 (base + DoRA), DeepSeek
- **Zero-shot**: GLiNER (multiple variants)

The full per-system comparison lives in `evaluation/final_ner_comparison.json` and `extended_evaluation_results.json`. The thesis reports **EarlyModernNER F1 = 0.823**, outperforming Gemini 3 Pro (0.665) and the best zero-shot GLiNER variant.

## EarlyModernNER — the contribution

`earlymodernner/` is the standalone package implementing the cascading architecture:

1. A base Qwen3-4B-Instruct model
2. Four per-entity-type adapters (Commodity, Organization, Person, Toponym) trained via DoRA + augmented data
3. A pipeline orchestrator that runs each adapter in turn, normalizes outputs, and resolves conflicts

The package has its own `README.md`, `LICENSE`, and `pyproject.toml` and can be installed independently:

```bash
cd earlymodernner/
pip install -e .
earlymodernner --help
```

**Important**: the trained adapter weights (~20 GB) are **not** in this repo — see `earlymodernner/earlymodernner/adapters/README.md` for the Zenodo link (to be minted after the thesis defense).

## Gold-standard corpus

- **Size**: 100 documents, hand-annotated
- **Source**: drawn from the same Internet-Archive corpus as Chapter 1
- **Format**: JSON; one file per document; spans for Person, Place (Toponym), Organization, Commodity
- **Provenance**: see `gold-standard/PROJECT_CONTEXT.md` for the document selection rationale
- **License**: CC-BY-4.0 (the annotations are the author's work)

The `annotations/` and `reviewed/` directories are two passes over the same set — `reviewed/` is the final version used for the thesis numbers.

## Reproducing the evaluation

```bash
cd evaluation/
pip install -r ../earlymodernner/requirements.txt

# Compare all systems against the gold standard
python compare_all_models.py \
  --gold ../gold-standard/reviewed/ \
  --out ../results/run-$(date +%Y%m%d).json

# EarlyModernNER alone (requires downloading adapter weights from Zenodo first)
python evaluate_ner.py \
  --model ../earlymodernner/ \
  --gold ../gold-standard/reviewed/
```

## Training recipes

`training-recipes/` contains everything you'd need to retrain EarlyModernNER:

- The fine-tuning script (`train_lora.py`)
- The data prep pipeline (`prepare_training_data.py`)
- The synthetic-data generator (`generate_synthetic_training.py`)
- Per-entity-type configs (`config/*.yaml`)
- Training notes (`training.md`)

You'll need to supply your own training corpus or use the EarlyModernNER training data deposit on Zenodo (link to be minted post-defense).

## Citation

If you use EarlyModernNER or the gold-standard annotations, please cite the thesis (see top-level `CITATION.cff`).
