# Chapter 1 — Optical Character Recognition

Materials accompanying Chapter 1 of *Loud Yet Invisible: A Humanist-Designed Pipeline for Unlocking the Early Modern Archive*. This chapter benchmarks 14 OCR systems on a hand-transcribed gold-standard corpus of 100 early modern printed pages.

## What's in here

```
chapter1-ocr/
├── gold-standard/
│   ├── transcriptions/        # 100 hand-corrected reference transcriptions (.md)
│   ├── page-xml/              # PAGE-XML ground truth with region/line geometry
│   ├── per-system-outputs/    # OCR output from each tested system, post-standardization
│   └── manifest.csv           # Mapping from gold-standard filename → source citation
├── evaluation/                # Evaluation pipeline (WER, BLEU, hallucination rate, etc.)
├── results/                   # Aggregate CSVs and per-run evaluation outputs
├── tables-eval/               # Separate evaluation focused on table-OCR performance
└── figures/                   # Chapter 1 figures (1.1–1.8)
```

## Systems tested

| System | Type | Notes |
|---|---|---|
| Tesseract (v5) | Traditional | Baseline; widely used |
| Tesseract-Legacy | Traditional | LSTM-disabled variant |
| Kraken | Traditional/CNN | Trained for historical scripts |
| EasyOCR | Traditional/CNN | |
| Transkribus | Hybrid (commercial) | Subscription required; manually run |
| olmOCR-1 | Vision-language transformer | |
| olmOCR-2 | Vision-language transformer | Best overall WER in the study |
| DeepSeek-OCR | Vision-language transformer | |
| Chandra (v1 + v2) | Vision-language transformer | |
| MinerU 2.6.2 | Vision-language transformer | |
| LightOn | Vision-language transformer | |
| Gemini 2.5 Pro | General-purpose LLM with vision | Run via API |

Two Chandra versions are included because the model received a major update during the evaluation window.

## Gold-standard corpus

- **Source**: 100 page images drawn from publicly accessible scans on the Internet Archive (Caribbean / British Atlantic, 1614–1810). All transcriptions were produced by the author.
- **Format**: plain Markdown (one paragraph per line, normalized whitespace) + PAGE-XML for systems that need geometric ground truth.
- **License**: CC-BY-4.0 (original transcriptions). Source images are linked from `gold-standard/manifest.csv` but not redistributed.
- **EEBO note**: This chapter's gold-standard corpus uses Internet Archive sources only. EEBO-sourced page images are referenced in Chapter 3's citation manifest but their OCR outputs are withheld from this release pending copyright review (see the top-level README).

## Reproducing the evaluation

```bash
cd evaluation/
pip install -r requirements.txt

# Reproduce per-system metrics on the gold standard
python evaluate_all_ocr_systems.py \
  --gold ../gold-standard/transcriptions/ \
  --systems ../gold-standard/per-system-outputs/ \
  --out ../results/run-$(date +%Y%m%d).csv
```

The metrics computed match those in the thesis:
- **WER** (Word Error Rate)
- **swWER** (Significant-Word Word Error Rate — stopwords removed)
- **BLEU**
- **HR** (Hallucination Rate)
- Character-level quality score

## Notes on running the OCR systems themselves

This repository does *not* re-run the OCR systems on the source images — it evaluates their outputs against the gold standard. To regenerate the per-system outputs you would need to install each system separately (see each system's documentation linked in `evaluation/README_OCR_EVALUATION.md`). The transformer-based systems require GPU.

## Tables sub-study

`tables-eval/` contains a smaller benchmark on two pages dominated by tabular data (a 1682 Jamaica letter and the 1807 West-India Common-place Book). Tables stress OCR systems differently than running prose; results are reported separately in Chapter 1.

## Citation

If you use the gold-standard transcriptions or the evaluation methodology, please cite the thesis (see top-level `CITATION.cff`).
