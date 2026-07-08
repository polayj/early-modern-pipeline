"""
Compare all NER models including MacBERTh
"""

import sys
from pathlib import Path

# Make evaluate_ner importable regardless of the current working directory
sys.path.append(str(Path(__file__).resolve().parent))

from evaluate_ner import compare_models

# Chapter root (chapter2-ner/)
REPO_CH2 = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    # Gold standard annotations with span offsets (archived in this repository).
    GOLD_DIR = REPO_CH2 / "gold-standard" / "annotations"

    # NOTE: the per-model prediction files below were NOT archived in this
    # repository. To re-run the comparison, place your prediction files at
    # these paths (or edit the mapping). Missing files are skipped with a
    # warning rather than evaluated.
    PREDICTIONS_DIR = REPO_CH2 / "results" / "predictions"
    MODEL_FILES = {
        "MacBERTh-470docs": PREDICTIONS_DIR / "macberth_gold_eval" / "macberth_gold_results_20251210_170140_fixed.json",  # unarchived
        "spaCy-lg": PREDICTIONS_DIR / "spaCy" / "results_20251205_135827.json",       # unarchived
        "deepseek-r1": PREDICTIONS_DIR / "deepseek" / "results_20251203_145333.json", # unarchived
        "gemma2": PREDICTIONS_DIR / "gemma2" / "results_20251203_152052.json",        # unarchived
        "mistral": PREDICTIONS_DIR / "mistral" / "results_20251203_144203.json",      # unarchived
        "GLiNER": PREDICTIONS_DIR / "gliNER" / "results_20251208_143935.json"         # unarchived
    }

    print("="*80)
    print("COMPARING ALL NER MODELS INCLUDING MACBERTH")
    print("="*80)
    print()

    results = compare_models(GOLD_DIR, MODEL_FILES)
