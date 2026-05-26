"""
Compare all NER models including MacBERTh
"""

import sys
sys.path.append(r"Z:\NER")

from evaluate_ner import compare_models

if __name__ == "__main__":
    GOLD_DIR = r"Z:\NER\gold"

    MODEL_FILES = {
        "MacBERTh-470docs": r"Z:\NER\macberth_gold_eval\macberth_gold_results_20251210_170140_fixed.json",
        "spaCy-lg": r"Z:\NER\spaCy\results_20251205_135827.json",
        "deepseek-r1": r"Z:\NER\deepseek\results_20251203_145333.json",
        "gemma2": r"Z:\NER\gemma2\results_20251203_152052.json",
        "mistral": r"Z:\NER\mistral\results_20251203_144203.json",
        "GLiNER": r"Z:\NER\gliNER\results_20251208_143935.json"
    }

    print("="*80)
    print("COMPARING ALL NER MODELS INCLUDING MACBERTH")
    print("="*80)
    print()

    results = compare_models(GOLD_DIR, MODEL_FILES)
