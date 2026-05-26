"""
Extended NER Evaluation Metrics (Text-Based Matching)

Uses text-based matching with normalization (following earlymodernner/dev/evaluate.py)
instead of span-based matching. Entities are deduplicated per document into sets
of (normalized_text, label) before matching.

Metrics:
1. Strict F1 and Partial F1 (with per-label breakdown)
2. Confusion matrix (gold_label x pred_label)
3. Slot Error Rate (SER)
4. Entity diversity metrics

Uses gold_reviewed/ as gold standard (4 entity types).
"""

import json
import re
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable
from collections import defaultdict, Counter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LABELS = ['COMMODITY', 'TOPONYM', 'PERSON', 'ORGANIZATION']


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_gold_standards(gold_dir: str) -> Dict[str, dict]:
    """Load gold standard annotations from gold_reviewed/."""
    gold_dir = Path(gold_dir)
    gold_data = {}

    for file_path in sorted(gold_dir.glob('*.json')):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc_id = data['doc_id'].replace('.xml', '')
        gold_data[doc_id] = data

    return gold_data


def load_predictions(pred_file: str) -> Dict[str, dict]:
    """Load model predictions (list of docs -> dict keyed by doc_id)."""
    with open(pred_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    pred_data = {}
    for doc in data:
        doc_id = doc['doc_id'].replace('.xml', '')
        pred_data[doc_id] = doc
    return pred_data


# ---------------------------------------------------------------------------
# Text normalization (from earlymodernner/dev/evaluate.py)
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalize entity text for comparison.

    Handles common variations in historical texts:
    - Case differences
    - Hyphen vs space (east-india vs east india)
    - Leading articles (the East India Company vs East India Company)
    - Multiple spaces
    """
    t = text.lower().strip()
    # Remove leading "the "
    if t.startswith("the "):
        t = t[4:]
    # Normalize hyphens to spaces
    t = t.replace("-", " ")
    # Collapse multiple spaces
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


# ---------------------------------------------------------------------------
# Text-based matching
# ---------------------------------------------------------------------------

def _deduplicate_entities(entities: List[dict]) -> set:
    """Deduplicate entities into a set of (normalized_text, label) tuples."""
    result = set()
    for e in entities:
        label = e.get('label', e.get('type', ''))
        norm = normalize_text(e.get('text', ''))
        if norm:
            result.add((norm, label))
    return result


def _match_entities_text(gold_set: set, pred_set: set) -> List[dict]:
    """Produce an alignment between gold and predicted entity sets.

    Both inputs are sets of (normalized_text, label) tuples (deduplicated per doc).

    Matching in 5 passes:
    1. Strict same-label: exact normalized text + same label
    2. Partial same-label: substring match (either direction) + same label
    3. Strict wrong-label: exact normalized text + different label (substitution)
    4. Partial wrong-label: substring match + different label (substitution)
    5. Remaining: unmatched gold -> missing, unmatched pred -> spurious
    """
    gold_remaining = set(gold_set)
    pred_remaining = set(pred_set)
    pairs = []

    # --- Pass 1: Strict same-label (exact text + same label) ---
    strict_matches = gold_remaining & pred_remaining
    for item in strict_matches:
        pairs.append({
            'category': 'strict',
            'gold': {'text': item[0], 'label': item[1]},
            'pred': {'text': item[0], 'label': item[1]},
        })
    gold_remaining -= strict_matches
    pred_remaining -= strict_matches

    # --- Pass 2: Partial same-label (substring + same label) ---
    matched_gold = set()
    matched_pred = set()
    for g_text, g_label in sorted(gold_remaining):
        if (g_text, g_label) in matched_gold:
            continue
        for p_text, p_label in sorted(pred_remaining):
            if (p_text, p_label) in matched_pred:
                continue
            if g_label == p_label and (g_text in p_text or p_text in g_text):
                pairs.append({
                    'category': 'partial',
                    'gold': {'text': g_text, 'label': g_label},
                    'pred': {'text': p_text, 'label': p_label},
                })
                matched_gold.add((g_text, g_label))
                matched_pred.add((p_text, p_label))
                break
    gold_remaining -= matched_gold
    pred_remaining -= matched_pred

    # --- Pass 3: Strict wrong-label (exact text, different label) ---
    matched_gold = set()
    matched_pred = set()
    for g_text, g_label in sorted(gold_remaining):
        if (g_text, g_label) in matched_gold:
            continue
        for p_text, p_label in sorted(pred_remaining):
            if (p_text, p_label) in matched_pred:
                continue
            if g_text == p_text and g_label != p_label:
                pairs.append({
                    'category': 'substitution',
                    'gold': {'text': g_text, 'label': g_label},
                    'pred': {'text': p_text, 'label': p_label},
                })
                matched_gold.add((g_text, g_label))
                matched_pred.add((p_text, p_label))
                break
    gold_remaining -= matched_gold
    pred_remaining -= matched_pred

    # --- Pass 4: Partial wrong-label (substring, different label) ---
    matched_gold = set()
    matched_pred = set()
    for g_text, g_label in sorted(gold_remaining):
        if (g_text, g_label) in matched_gold:
            continue
        for p_text, p_label in sorted(pred_remaining):
            if (p_text, p_label) in matched_pred:
                continue
            if g_label != p_label and (g_text in p_text or p_text in g_text):
                pairs.append({
                    'category': 'substitution',
                    'gold': {'text': g_text, 'label': g_label},
                    'pred': {'text': p_text, 'label': p_label},
                })
                matched_gold.add((g_text, g_label))
                matched_pred.add((p_text, p_label))
                break
    gold_remaining -= matched_gold
    pred_remaining -= matched_pred

    # --- Pass 5: Unmatched ---
    for item in sorted(gold_remaining):
        pairs.append({
            'category': 'missing',
            'gold': {'text': item[0], 'label': item[1]},
            'pred': None,
        })

    for item in sorted(pred_remaining):
        pairs.append({
            'category': 'spurious',
            'gold': None,
            'pred': {'text': item[0], 'label': item[1]},
        })

    return pairs


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------

def _prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {'precision': round(p, 4), 'recall': round(r, 4),
            'f1': round(f1, 4), 'tp': tp, 'fp': fp, 'fn': fn}


# ---------------------------------------------------------------------------
# 1. Strict & Partial F1
# ---------------------------------------------------------------------------

def compute_semeval_metrics(all_pairs: List[dict],
                            total_gold: int,
                            total_pred: int,
                            gold_flat: List[dict],
                            pred_flat: List[dict]) -> Dict[str, Any]:
    """Compute Strict F1 and Partial F1.

    - Strict F1: only 'strict' matches count as TP
    - Partial F1: 'strict' + 'partial' matches count as TP
    """
    cat_counts = Counter(p['category'] for p in all_pairs)
    n_strict = cat_counts.get('strict', 0)
    n_partial = cat_counts.get('partial', 0)

    results = {}

    # Strict: exact normalized text + correct label
    tp_s = n_strict
    results['strict'] = _prf(tp_s, total_pred - tp_s, total_gold - tp_s)

    # Partial: strict + substring matches (same label)
    tp_p = n_strict + n_partial
    results['partial'] = _prf(tp_p, total_pred - tp_p, total_gold - tp_p)

    # Per-label breakdown
    per_label = {}
    for label in LABELS:
        label_gold = set()
        label_pred = set()
        for e in gold_flat:
            lbl = e.get('label', e.get('type', ''))
            if lbl == label:
                label_gold.add((normalize_text(e.get('text', '')), lbl))
        for e in pred_flat:
            lbl = e.get('label', e.get('type', ''))
            if lbl == label:
                label_pred.add((normalize_text(e.get('text', '')), lbl))

        label_pairs = _match_entities_text(label_gold, label_pred)
        lc = Counter(p['category'] for p in label_pairs)
        n_g = len(label_gold)
        n_p = len(label_pred)

        tp_strict = lc.get('strict', 0)
        tp_partial_label = lc.get('strict', 0) + lc.get('partial', 0)

        per_label[label] = {
            'strict': _prf(tp_strict, n_p - tp_strict, n_g - tp_strict),
            'partial': _prf(tp_partial_label, n_p - tp_partial_label, n_g - tp_partial_label),
            'gold_count': n_g,
            'pred_count': n_p,
        }

    results['per_label'] = per_label
    return results


# ---------------------------------------------------------------------------
# 2. Confusion Matrix
# ---------------------------------------------------------------------------

def compute_confusion_matrix(all_pairs: List[dict]) -> Dict[str, Dict[str, int]]:
    """Build gold_label x pred_label confusion matrix.

    Rows = gold labels (+ 'O' for spurious predictions).
    Columns = pred labels (+ 'O' for missed gold entities).
    """
    all_labels_seen = set(LABELS)
    for pair in all_pairs:
        if pair['gold']:
            all_labels_seen.add(pair['gold']['label'])
        if pair['pred']:
            all_labels_seen.add(pair['pred']['label'])

    labels_plus_o = sorted(all_labels_seen) + ['O']
    matrix = {g: {p: 0 for p in labels_plus_o} for g in labels_plus_o}

    for pair in all_pairs:
        cat = pair['category']
        if cat == 'missing':
            gold_label = pair['gold']['label']
            matrix[gold_label]['O'] += 1
        elif cat == 'spurious':
            pred_label = pair['pred']['label']
            matrix['O'][pred_label] += 1
        else:
            gold_label = pair['gold']['label']
            pred_label = pair['pred']['label']
            matrix[gold_label][pred_label] += 1

    return matrix


# ---------------------------------------------------------------------------
# 3. Slot Error Rate
# ---------------------------------------------------------------------------

def compute_ser(all_pairs: List[dict],
                total_gold: int) -> Dict[str, Any]:
    """Compute Slot Error Rate.

    SER = (S + D + I) / N_gold
    S = substitutions (matched but wrong label)
    D = deletions (missed gold entities)
    I = insertions (spurious predictions)
    """
    substitutions = 0
    deletions = 0
    insertions = 0

    for pair in all_pairs:
        cat = pair['category']
        if cat == 'missing':
            deletions += 1
        elif cat == 'spurious':
            insertions += 1
        elif cat == 'substitution':
            substitutions += 1
        # strict and partial are correct matches

    ser = (substitutions + deletions + insertions) / total_gold if total_gold else 0.0

    return {
        'substitutions': substitutions,
        'deletions': deletions,
        'insertions': insertions,
        'correct': total_gold - substitutions - deletions,
        'total_gold': total_gold,
        'ser': round(ser, 4),
    }


# ---------------------------------------------------------------------------
# 4. Entity Diversity
# ---------------------------------------------------------------------------

def compute_entity_diversity(gold_entities: List[dict],
                             pred_entities: List[dict]) -> Dict[str, Any]:
    """Compute entity diversity / vocabulary coverage metrics."""
    gold_texts = [normalize_text(e['text']) for e in gold_entities]
    pred_texts = [normalize_text(e['text']) for e in pred_entities]

    gold_unique = set(gold_texts)
    pred_unique = set(pred_texts)

    coverage = len(pred_unique & gold_unique) / len(gold_unique) if gold_unique else 0.0

    # Frequency distributions
    gold_freq = Counter(gold_texts)
    pred_freq = Counter(pred_texts)

    gold_hapax = sum(1 for v in gold_freq.values() if v == 1)
    pred_hapax = sum(1 for v in pred_freq.values() if v == 1)

    # Per-label breakdown
    per_label = {}
    for label in LABELS:
        g_texts = [normalize_text(e['text']) for e in gold_entities if e['label'] == label]
        p_texts = [normalize_text(e['text']) for e in pred_entities
                   if e.get('label', e.get('type', '')) == label]
        g_unique = set(g_texts)
        p_unique = set(p_texts)

        g_freq = Counter(g_texts)
        p_freq = Counter(p_texts)

        per_label[label] = {
            'gold_unique': len(g_unique),
            'pred_unique': len(p_unique),
            'overlap': len(g_unique & p_unique),
            'coverage': round(len(g_unique & p_unique) / len(g_unique), 4) if g_unique else 0.0,
            'gold_top5': g_freq.most_common(5),
            'pred_top5': p_freq.most_common(5),
        }

    return {
        'gold_unique': len(gold_unique),
        'pred_unique': len(pred_unique),
        'overlap_unique': len(gold_unique & pred_unique),
        'coverage_ratio': round(coverage, 4),
        'gold_hapax_legomena': gold_hapax,
        'pred_hapax_legomena': pred_hapax,
        'per_label': per_label,
    }


# ---------------------------------------------------------------------------
# 5. Throughput / Latency Utility
# ---------------------------------------------------------------------------

def time_model_run(model_fn: Callable[[str], List[dict]],
                   documents: List[dict],
                   label: str = 'model') -> Dict[str, Any]:
    """Time a model's NER predictions across a set of documents."""
    latencies = []
    total_chars = 0

    tracemalloc.start()

    for doc in documents:
        text = doc['text']
        total_chars += len(text)

        t0 = time.perf_counter()
        _ = model_fn(text)
        t1 = time.perf_counter()

        latencies.append(t1 - t0)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    latencies.sort()
    n = len(latencies)
    total_time = sum(latencies)

    return {
        'model': label,
        'num_documents': n,
        'total_chars': total_chars,
        'total_time_s': round(total_time, 3),
        'mean_latency_s': round(total_time / n, 4) if n else 0,
        'median_latency_s': round(latencies[n // 2], 4) if n else 0,
        'p95_latency_s': round(latencies[int(n * 0.95)], 4) if n else 0,
        'throughput_chars_per_s': round(total_chars / total_time, 1) if total_time else 0,
        'peak_memory_mb': round(peak / 1024 / 1024, 2),
    }


# ---------------------------------------------------------------------------
# Main evaluation pipeline
# ---------------------------------------------------------------------------

def evaluate_model_extended(gold_data: Dict[str, dict],
                            pred_data: Dict[str, dict],
                            model_name: str) -> Dict[str, Any]:
    """Run all extended metrics for one model against gold standard."""

    common_ids = set(gold_data.keys()) & set(pred_data.keys())
    if not common_ids:
        print(f"  ERROR: No matching documents for {model_name}")
        return {}

    # Collect all pairs across documents, deduplicated per doc
    all_pairs: List[dict] = []
    gold_flat: List[dict] = []
    pred_flat: List[dict] = []
    total_gold_dedup = 0
    total_pred_dedup = 0

    for doc_id in sorted(common_ids):
        g_ents = gold_data[doc_id].get('entities', [])
        p_ents = pred_data[doc_id].get('entities', [])

        # Deduplicate into sets of (normalized_text, label) per document
        gold_set = _deduplicate_entities(g_ents)
        pred_set = _deduplicate_entities(p_ents)

        total_gold_dedup += len(gold_set)
        total_pred_dedup += len(pred_set)

        # Keep flat lists for diversity metrics (pre-dedup)
        gold_flat.extend(g_ents)
        pred_flat.extend(p_ents)

        # Match within this document
        doc_pairs = _match_entities_text(gold_set, pred_set)
        all_pairs.extend(doc_pairs)

    # 1. Strict & Partial F1
    semeval = compute_semeval_metrics(all_pairs, total_gold_dedup, total_pred_dedup,
                                      gold_flat, pred_flat)

    # 2. Confusion matrix
    confusion = compute_confusion_matrix(all_pairs)

    # 3. Slot Error Rate
    ser = compute_ser(all_pairs, total_gold_dedup)

    # 4. Entity diversity
    diversity = compute_entity_diversity(gold_flat, pred_flat)

    return {
        'model': model_name,
        'documents_evaluated': len(common_ids),
        'total_gold_entities': total_gold_dedup,
        'total_pred_entities': total_pred_dedup,
        'semeval_metrics': semeval,
        'confusion_matrix': confusion,
        'slot_error_rate': ser,
        'entity_diversity': diversity,
        'throughput': None,
    }


# ---------------------------------------------------------------------------
# Pretty-printing
# ---------------------------------------------------------------------------

def print_results(results: Dict[str, Any]) -> None:
    """Print a human-readable summary of extended metrics."""
    model = results['model']
    print(f"\n{'=' * 72}")
    print(f"  Extended Evaluation: {model}")
    print(f"{'=' * 72}")
    print(f"  Documents: {results['documents_evaluated']}")
    print(f"  Gold entities (dedup): {results['total_gold_entities']}")
    print(f"  Pred entities (dedup): {results['total_pred_entities']}")

    # F1 metrics
    sem = results['semeval_metrics']
    print(f"\n  Matching Metrics:")
    print(f"  {'Schema':<10} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print(f"  {'-' * 42}")
    for schema in ('strict', 'partial'):
        s = sem[schema]
        print(f"  {schema:<10} {s['precision']:>10.4f} {s['recall']:>10.4f} {s['f1']:>10.4f}")

    # Per-label
    print(f"\n  Per-Label Breakdown:")
    print(f"  {'Label':<16} {'Strict F1':>10} {'Partial F1':>10} {'Gold':>6} {'Pred':>6}")
    print(f"  {'-' * 54}")
    for label in LABELS:
        if label in sem['per_label']:
            lbl = sem['per_label'][label]
            print(f"  {label:<16} {lbl['strict']['f1']:>10.4f} "
                  f"{lbl['partial']['f1']:>10.4f} "
                  f"{lbl['gold_count']:>6} {lbl['pred_count']:>6}")

    # Confusion matrix
    cm = results['confusion_matrix']
    labels_display = sorted(k for k in cm.keys() if k != 'O') + ['O']
    print(f"\n  Confusion Matrix (rows=gold, cols=pred):")
    header = f"  {'':>14}" + ''.join(f'{l:>8}' for l in labels_display)
    print(header)
    for g_label in labels_display:
        row = f"  {g_label:>14}"
        for p_label in labels_display:
            row += f"{cm.get(g_label, {}).get(p_label, 0):>8}"
        print(row)

    # SER
    ser = results['slot_error_rate']
    print(f"\n  Slot Error Rate:")
    print(f"    Correct:       {ser['correct']}")
    print(f"    Substitutions: {ser['substitutions']}")
    print(f"    Deletions:     {ser['deletions']}")
    print(f"    Insertions:    {ser['insertions']}")
    print(f"    SER:           {ser['ser']:.4f}")

    # Diversity
    div = results['entity_diversity']
    print(f"\n  Entity Diversity:")
    print(f"    Gold unique forms:  {div['gold_unique']}")
    print(f"    Pred unique forms:  {div['pred_unique']}")
    print(f"    Overlap:            {div['overlap_unique']}")
    print(f"    Coverage ratio:     {div['coverage_ratio']:.4f}")
    for label in LABELS:
        if label in div['per_label']:
            ld = div['per_label'][label]
            print(f"    {label}: gold={ld['gold_unique']}, "
                  f"pred={ld['pred_unique']}, "
                  f"coverage={ld['coverage']:.4f}")

    print()


def print_comparison_table(all_results: List[Dict[str, Any]]) -> None:
    """Print a summary comparison table across models."""
    print(f"\n{'=' * 90}")
    print("  COMPARISON SUMMARY")
    print(f"{'=' * 90}")

    print(f"\n  {'Model':<20} {'Strict F1':>10} {'Partial F1':>12} "
          f"{'SER':>8} {'Coverage':>10}")
    print(f"  {'-' * 62}")
    for r in sorted(all_results,
                    key=lambda x: x['semeval_metrics']['strict']['f1'],
                    reverse=True):
        sem = r['semeval_metrics']
        print(f"  {r['model']:<20} "
              f"{sem['strict']['f1']:>10.4f} "
              f"{sem['partial']['f1']:>12.4f} "
              f"{r['slot_error_rate']['ser']:>8.4f} "
              f"{r['entity_diversity']['coverage_ratio']:>10.4f}")


# ---------------------------------------------------------------------------
# JSON serialisation helper
# ---------------------------------------------------------------------------

def _serialise_for_json(obj):
    """Convert tuples (from Counter.most_common) to lists for JSON."""
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, dict):
        return {k: _serialise_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialise_for_json(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    GOLD_DIR = r'/mnt/z/NER/gold_reviewed'

    # ------------------------------------------------------------------
    # Auto-discover latest result files from run_all_ner.py output dirs
    # ------------------------------------------------------------------
    def _latest_result(directory: str, pattern: str = "results_4cat_*.json") -> Optional[str]:
        """Find the most recently modified result file in a directory."""
        d = Path(directory)
        if not d.exists():
            return None
        files = sorted(d.glob(pattern), key=lambda p: p.stat().st_mtime)
        return str(files[-1]) if files else None

    # Static / legacy results (original 2-category runs)
    MODEL_FILES_LEGACY = {
        'spaCy-lg (2cat)':     r'/mnt/z/NER/spaCy/results_20251205_135827.json',
        'deepseek-r1 (2cat)':  r'/mnt/z/NER/deepseek/results_20251208_190219.json',
        'gemma2 (2cat)':       r'/mnt/z/NER/gemma2/results_20251203_152052.json',
        'mistral (2cat)':      r'/mnt/z/NER/mistral/results_20251203_144203.json',
        'GLiNER (2cat)':       r'/mnt/z/NER/gliNER/results_20251208_143935.json',
    }

    # MacBERTh -- existing fine-tuned results (already has all 4 categories)
    MODEL_FILES_STATIC = {
        'MacBERTh':     r'/mnt/z/NER/macberth_gold_eval/macberth_gold_results_20251210_170140_fixed.json',
    }

    # New 4-category single-pass results (auto-discovered)
    MODEL_DIRS_4CAT = {
        'spaCy-lg':       '/mnt/z/NER/spaCy_4cat',
        'GLiNER':         '/mnt/z/NER/gliNER_4cat',
        'gemma2':         '/mnt/z/NER/gemma2_4cat',
        'mistral':        '/mnt/z/NER/mistral_4cat',
        'deepseek-r1':    '/mnt/z/NER/deepseek_4cat',
        'Stanford NER':   '/mnt/z/NER/stanford_4cat',
        'GATE ANNIE':     '/mnt/z/NER/gate_4cat',
        'Flair NLP':      '/mnt/z/NER/flair_4cat',
        'BERT-large':     '/mnt/z/NER/deberta_4cat',
        'mBERT':          '/mnt/z/NER/mbert_4cat',
        'GoLLIE':         '/mnt/z/NER/gollie_4cat',
        'earlymodernner': '/mnt/z/NER/earlymodernner_4cat',
        'Gemini Pro':     '/mnt/z/NER/gemini_pro_4cat',
        'Qwen3-4B':      '/mnt/z/NER/qwen3_4cat',
        'hmBERT':         '/mnt/z/NER/hmbert_4cat',
    }

    # Ensemble results (auto-discovered)
    MODEL_DIRS_ENSEMBLE = {
        'gemma2 (ens)':     '/mnt/z/NER/gemma2_4cat_ensemble',
        'mistral (ens)':    '/mnt/z/NER/mistral_4cat_ensemble',
        'deepseek-r1 (ens)':'/mnt/z/NER/deepseek_4cat_ensemble',
        'GoLLIE (ens)':     '/mnt/z/NER/gollie_4cat_ensemble',
        'Gemini Pro (ens)': '/mnt/z/NER/gemini_pro_4cat_ensemble',
        'Qwen3-4B (ens)':   '/mnt/z/NER/qwen3_4cat_ensemble',
    }

    # Build MODEL_FILES from all sources
    MODEL_FILES = dict(MODEL_FILES_STATIC)

    for name, directory in MODEL_DIRS_4CAT.items():
        path = _latest_result(directory)
        if path:
            MODEL_FILES[name] = path

    for name, directory in MODEL_DIRS_ENSEMBLE.items():
        path = _latest_result(directory)
        if path:
            MODEL_FILES[name] = path

    if not MODEL_FILES:
        print("  [ERROR] No model result files found!")
        print("  Run: python run_all_ner.py --models spacy gliner flair deberta mbert")
        sys.exit(1)

    print(f"\n  Found {len(MODEL_FILES)} model result files:")
    for name, path in sorted(MODEL_FILES.items()):
        print(f"    {name}: {path}")

    print('=' * 72)
    print('  EXTENDED NER EVALUATION (Text-Based Matching)')
    print('=' * 72)

    # Load gold standard
    gold_data = load_gold_standards(GOLD_DIR)
    print(f"\n  Loaded {len(gold_data)} gold standard documents")

    # Count gold entities
    total_gold = sum(len(d.get('entities', [])) for d in gold_data.values())
    for label in LABELS:
        cnt = sum(1 for d in gold_data.values()
                  for e in d.get('entities', []) if e['label'] == label)
        print(f"  {label}: {cnt}")
    print(f"  Total: {total_gold}")

    # Evaluate each model
    all_results = []
    for model_name, pred_file in MODEL_FILES.items():
        pred_data = load_predictions(pred_file)
        result = evaluate_model_extended(gold_data, pred_data, model_name)
        if result:
            print_results(result)
            all_results.append(result)

    # Comparison table
    if all_results:
        print_comparison_table(all_results)

    # Save JSON
    output_file = Path(GOLD_DIR).parent / 'extended_evaluation_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(_serialise_for_json(all_results), f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to: {output_file}")
