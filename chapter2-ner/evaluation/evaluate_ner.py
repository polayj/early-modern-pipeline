"""
Evaluate NER model outputs against gold standard annotations
Calculates precision, recall, and F1 scores
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter


class NERMetrics:
    def __init__(self):
        self.tp = 0  # True positives
        self.fp = 0  # False positives
        self.fn = 0  # False negatives

    def update(self, tp, fp, fn):
        self.tp += tp
        self.fp += fp
        self.fn += fn

    def precision(self):
        if self.tp + self.fp == 0:
            return 0.0
        return self.tp / (self.tp + self.fp)

    def recall(self):
        if self.tp + self.fn == 0:
            return 0.0
        return self.tp / (self.tp + self.fn)

    def f1(self):
        p = self.precision()
        r = self.recall()
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)

    def __repr__(self):
        return f"P: {self.precision():.3f}, R: {self.recall():.3f}, F1: {self.f1():.3f}"


def load_gold_standards(gold_dir):
    """Load all gold standard annotations"""
    gold_dir = Path(gold_dir)
    gold_data = {}

    for file_path in gold_dir.glob('*.json'):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Normalize doc_id (remove .xml extension if present)
        doc_id = data['doc_id'].replace('.xml', '')
        gold_data[doc_id] = data

    return gold_data


def load_predictions(pred_file):
    """Load model predictions"""
    with open(pred_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Create dict keyed by doc_id
    pred_data = {}
    for doc in data:
        doc_id = doc['doc_id']
        pred_data[doc_id] = doc

    return pred_data


def exact_match(gold_entity, pred_entity):
    """Check if entities match exactly (same boundaries and label)"""
    return (gold_entity['start'] == pred_entity['start'] and
            gold_entity['end'] == pred_entity['end'] and
            gold_entity['label'] == pred_entity['label'])


def partial_match(gold_entity, pred_entity):
    """Check if entities overlap and have same label"""
    if gold_entity['label'] != pred_entity['label']:
        return False

    # Check for overlap
    return not (gold_entity['end'] <= pred_entity['start'] or
                gold_entity['start'] >= pred_entity['end'])


def calculate_metrics_for_doc(gold_entities, pred_entities, match_type='exact'):
    """Calculate TP, FP, FN for a single document"""
    match_fn = exact_match if match_type == 'exact' else partial_match

    matched_gold = set()
    matched_pred = set()

    # Find matches
    for i, gold_ent in enumerate(gold_entities):
        for j, pred_ent in enumerate(pred_entities):
            if match_fn(gold_ent, pred_ent):
                matched_gold.add(i)
                matched_pred.add(j)

    tp = len(matched_gold)  # Gold entities that were found
    fp = len(pred_entities) - len(matched_pred)  # Predicted but not in gold
    fn = len(gold_entities) - len(matched_gold)  # In gold but not predicted

    return tp, fp, fn


def evaluate_model(gold_data, pred_data, model_name, match_type='exact'):
    """Evaluate a model's predictions against gold standard"""
    print(f"\n{'='*70}")
    print(f"Evaluating: {model_name} ({match_type} match)")
    print(f"{'='*70}")

    # Overall metrics
    overall = NERMetrics()

    # Per-label metrics
    label_metrics = defaultdict(NERMetrics)

    # Find matching documents
    gold_ids = set(gold_data.keys())
    pred_ids = set(pred_data.keys())
    common_ids = gold_ids & pred_ids

    print(f"Gold documents: {len(gold_ids)}")
    print(f"Predicted documents: {len(pred_ids)}")
    print(f"Common documents: {len(common_ids)}")

    if not common_ids:
        print("ERROR: No matching documents found!")
        return None

    # Track errors
    false_positives = []
    false_negatives = []

    # Evaluate each document
    for doc_id in sorted(common_ids):
        gold_doc = gold_data[doc_id]
        pred_doc = pred_data[doc_id]

        gold_entities = gold_doc.get('entities', [])
        pred_entities = pred_doc.get('entities', [])

        # Overall metrics
        tp, fp, fn = calculate_metrics_for_doc(gold_entities, pred_entities, match_type)
        overall.update(tp, fp, fn)

        # Per-label metrics
        for label in ['COMMODITY', 'TOPONYM']:
            gold_label = [e for e in gold_entities if e['label'] == label]
            pred_label = [e for e in pred_entities if e['label'] == label]

            tp, fp, fn = calculate_metrics_for_doc(gold_label, pred_label, match_type)
            label_metrics[label].update(tp, fp, fn)

            # Track specific errors for first few docs
            if len(false_positives) < 20:
                for pred_ent in pred_label:
                    if not any(exact_match(pred_ent, g) for g in gold_label):
                        false_positives.append({
                            'doc_id': doc_id,
                            'entity': pred_ent
                        })

            if len(false_negatives) < 20:
                for gold_ent in gold_label:
                    if not any(exact_match(gold_ent, p) for p in pred_label):
                        false_negatives.append({
                            'doc_id': doc_id,
                            'entity': gold_ent
                        })

    # Print results
    print(f"\nOverall Metrics:")
    print(f"  Precision: {overall.precision():.3f}")
    print(f"  Recall:    {overall.recall():.3f}")
    print(f"  F1 Score:  {overall.f1():.3f}")
    print(f"  TP: {overall.tp}, FP: {overall.fp}, FN: {overall.fn}")

    print(f"\nPer-Label Metrics:")
    for label in ['COMMODITY', 'TOPONYM']:
        metrics = label_metrics[label]
        print(f"  {label}:")
        print(f"    Precision: {metrics.precision():.3f}")
        print(f"    Recall:    {metrics.recall():.3f}")
        print(f"    F1 Score:  {metrics.f1():.3f}")
        print(f"    TP: {metrics.tp}, FP: {metrics.fp}, FN: {metrics.fn}")

    # Sample errors
    if false_positives:
        print(f"\nSample False Positives (predicted but not in gold):")
        for i, fp in enumerate(false_positives[:5], 1):
            print(f"  {i}. {fp['entity']['text']:30} ({fp['entity']['label']})")

    if false_negatives:
        print(f"\nSample False Negatives (in gold but not predicted):")
        for i, fn in enumerate(false_negatives[:5], 1):
            print(f"  {i}. {fn['entity']['text']:30} ({fn['entity']['label']})")

    return {
        'model': model_name,
        'match_type': match_type,
        'overall': {
            'precision': overall.precision(),
            'recall': overall.recall(),
            'f1': overall.f1(),
            'tp': overall.tp,
            'fp': overall.fp,
            'fn': overall.fn
        },
        'per_label': {
            label: {
                'precision': metrics.precision(),
                'recall': metrics.recall(),
                'f1': metrics.f1(),
                'tp': metrics.tp,
                'fp': metrics.fp,
                'fn': metrics.fn
            }
            for label, metrics in label_metrics.items()
        }
    }


def compare_models(gold_dir, model_files):
    """Compare multiple models"""
    print("="*70)
    print("NER MODEL EVALUATION")
    print("="*70)

    # Load gold standard
    gold_data = load_gold_standards(gold_dir)
    print(f"\nLoaded {len(gold_data)} gold standard documents")

    # Count entities in gold
    total_entities = sum(len(doc.get('entities', [])) for doc in gold_data.values())
    commodity_count = sum(len([e for e in doc.get('entities', []) if e['label'] == 'COMMODITY'])
                         for doc in gold_data.values())
    toponym_count = sum(len([e for e in doc.get('entities', []) if e['label'] == 'TOPONYM'])
                       for doc in gold_data.values())

    print(f"Gold standard contains:")
    print(f"  Total entities: {total_entities}")
    print(f"  COMMODITY: {commodity_count}")
    print(f"  TOPONYM: {toponym_count}")

    # Evaluate each model
    results = []

    for model_name, model_file in model_files.items():
        pred_data = load_predictions(model_file)

        # Evaluate with exact match
        result_exact = evaluate_model(gold_data, pred_data, model_name, 'exact')
        if result_exact:
            results.append(result_exact)

        # Evaluate with partial match
        result_partial = evaluate_model(gold_data, pred_data, model_name, 'partial')
        if result_partial:
            results.append(result_partial)

    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON (Exact Match)")
    print(f"{'='*70}")
    print(f"{'Model':<20} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("-"*70)

    exact_results = [r for r in results if r['match_type'] == 'exact']
    exact_results.sort(key=lambda x: x['overall']['f1'], reverse=True)

    for result in exact_results:
        print(f"{result['model']:<20} "
              f"{result['overall']['precision']:>10.3f} "
              f"{result['overall']['recall']:>10.3f} "
              f"{result['overall']['f1']:>10.3f}")

    # Save results
    output_file = Path(gold_dir).parent / "evaluation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    return results


if __name__ == "__main__":
    GOLD_DIR = r"Z:\NER\gold"

    MODEL_FILES = {
        "spaCy-lg": r"Z:\NER\spaCy\results_20251205_135827.json",
        "deepseek-r1": r"Z:\NER\deepseek\results_20251203_145333.json",
        "gemma2": r"Z:\NER\gemma2\results_20251203_152052.json",
        "mistral": r"Z:\NER\mistral\results_20251203_144203.json",
        "GLiNER": r"Z:\NER\gliNER\results_20251208_143935.json"
    }

    results = compare_models(GOLD_DIR, MODEL_FILES)
