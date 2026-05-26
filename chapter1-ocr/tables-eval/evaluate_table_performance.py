#!/usr/bin/env python3
"""
Table-Specific OCR Evaluation

Evaluates how each OCR system performed on table documents by comparing
standardized table outputs against gold standard transcriptions.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from difflib import SequenceMatcher
from collections import defaultdict
import json
from datetime import datetime


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def calculate_cer(reference: str, hypothesis: str) -> Tuple[float, int, int, int, int]:
    """Calculate Character Error Rate and error breakdown"""
    from Levenshtein import editops

    ops = editops(reference, hypothesis)

    insertions = sum(1 for op in ops if op[0] == 'insert')
    deletions = sum(1 for op in ops if op[0] == 'delete')
    substitutions = sum(1 for op in ops if op[0] == 'replace')

    total_errors = insertions + deletions + substitutions
    ref_length = len(reference)

    cer = total_errors / ref_length if ref_length > 0 else 0.0

    return cer, insertions, deletions, substitutions


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate"""
    from Levenshtein import distance

    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if len(ref_words) == 0:
        return 0.0

    errors = distance(ref_words, hyp_words)
    wer = errors / len(ref_words)

    return wer


def calculate_bleu(reference: str, hypothesis: str) -> float:
    """Calculate BLEU score"""
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if not ref_words or not hyp_words:
        return 0.0

    smoothing = SmoothingFunction().method1
    score = sentence_bleu([ref_words], hyp_words, smoothing_function=smoothing)

    return score


def calculate_accuracy_metrics(reference: str, hypothesis: str) -> Dict[str, float]:
    """Calculate character and word accuracy"""
    # Character accuracy
    cer, _, _, _ = calculate_cer(reference, hypothesis)
    char_accuracy = max(0.0, 1.0 - cer)

    # Word accuracy
    wer = calculate_wer(reference, hypothesis)
    word_accuracy = max(0.0, 1.0 - wer)

    return {
        'char_accuracy': char_accuracy,
        'word_accuracy': word_accuracy
    }


def find_matching_file(ocr_dir: Path, doc_name: str) -> Path:
    """Find the matching OCR file for a gold standard document"""
    # Try exact match first
    exact_match = ocr_dir / f"{doc_name}.md"
    if exact_match.exists():
        return exact_match

    # Try with _page_001 suffix (used by some OCR systems)
    page_match = ocr_dir / f"{doc_name}_page_001.md"
    if page_match.exists():
        return page_match

    # Try fuzzy match
    md_files = list(ocr_dir.glob("*.md"))
    for md_file in md_files:
        if doc_name in md_file.stem:
            return md_file

    raise FileNotFoundError(f"No matching file found for {doc_name} in {ocr_dir}")


def evaluate_document(gold_text: str, ocr_text: str, doc_name: str, system_name: str) -> Dict:
    """Evaluate a single document"""
    # Normalize texts
    gold_norm = normalize_text(gold_text)
    ocr_norm = normalize_text(ocr_text)

    # Calculate metrics
    cer, insertions, deletions, substitutions = calculate_cer(gold_norm, ocr_norm)
    wer = calculate_wer(gold_norm, ocr_norm)
    bleu = calculate_bleu(gold_norm, ocr_norm)
    accuracy_metrics = calculate_accuracy_metrics(gold_norm, ocr_norm)

    # Calculate hallucination rate (words in OCR but not in reference)
    ocr_words = set(ocr_norm.lower().split())
    gold_words = set(gold_norm.lower().split())
    hallucinated_words = ocr_words - gold_words
    hallucination_rate = len(hallucinated_words) / len(ocr_words) if ocr_words else 0.0

    return {
        'document': doc_name,
        'system': system_name,
        'cer': cer,
        'wer': wer,
        'bleu': bleu,
        'char_accuracy': accuracy_metrics['char_accuracy'],
        'word_accuracy': accuracy_metrics['word_accuracy'],
        'hallucination_rate': hallucination_rate,
        'char_insertions': insertions,
        'char_deletions': deletions,
        'char_substitutions': substitutions,
        'total_char_errors': insertions + deletions + substitutions,
        'gold_char_count': len(gold_norm),
        'gold_word_count': len(gold_norm.split()),
        'ocr_char_count': len(ocr_norm),
        'ocr_word_count': len(ocr_norm.split())
    }


def main():
    """Run table-specific OCR evaluation"""
    print("=" * 80)
    print("TABLE-SPECIFIC OCR EVALUATION")
    print("=" * 80)
    print()

    # Setup paths
    tables_dir = Path(r"Z:\Tables")
    gold_dir = tables_dir / "goldstandard"
    output_dir = tables_dir / "results"
    output_dir.mkdir(exist_ok=True)

    # OCR systems to evaluate (excluding Chandra which has no .md files)
    ocr_systems = {
        'Deepseek': tables_dir / 'Deepseek',
        'EasyOCR': tables_dir / 'EasyOCR',
        'Gemini': tables_dir / 'Gemini',
        'Kraken': tables_dir / 'Kraken',
        'MinerU': tables_dir / 'MinerU',
        'OlmOCRv1': tables_dir / 'olmv1',
        'OlmOCRv2': tables_dir / 'olmv2',
        'Tesseract': tables_dir / 'Tesseract',
        'Transkribus': tables_dir / 'transkribus',
        'Chandra': tables_dir / 'Chandra'
    }

    # Load gold standard documents
    gold_files = list(gold_dir.glob("*.md"))
    print(f"Found {len(gold_files)} gold standard table documents:")
    for gf in gold_files:
        print(f"  - {gf.name}")
    print()

    # Check which systems are available
    available_systems = {}
    print("Checking OCR systems:")
    for name, path in ocr_systems.items():
        if path.exists():
            md_files = list(path.glob("*.md"))
            if md_files:
                available_systems[name] = path
                print(f"  [OK] {name:15} - {len(md_files)} files")
            else:
                print(f"  [SKIP] {name:15} - No .md files")
        else:
            print(f"  [SKIP] {name:15} - Directory not found")
    print()

    print(f"Evaluating {len(available_systems)} OCR systems on {len(gold_files)} documents")
    print()

    # Evaluate all documents
    results = []

    for gold_file in gold_files:
        doc_name = gold_file.stem
        gold_text = gold_file.read_text(encoding='utf-8')

        print(f"Evaluating: {doc_name}")

        for system_name, system_dir in available_systems.items():
            try:
                # Find matching OCR file
                ocr_file = find_matching_file(system_dir, doc_name)
                ocr_text = ocr_file.read_text(encoding='utf-8')

                # Evaluate
                result = evaluate_document(gold_text, ocr_text, doc_name, system_name)
                results.append(result)

                print(f"  {system_name:15} - CER: {result['cer']:.4f}, WER: {result['wer']:.4f}, BLEU: {result['bleu']:.4f}")

            except FileNotFoundError as e:
                print(f"  {system_name:15} - ERROR: {e}")
            except Exception as e:
                print(f"  {system_name:15} - ERROR: {e}")

        print()

    # Create detailed results DataFrame
    detailed_df = pd.DataFrame(results)

    # Check if we have any results
    if len(results) == 0:
        print("ERROR: No successful evaluations completed!")
        print("Please check that all dependencies are installed.")
        return

    # Create summary by system
    summary_data = []
    for system in available_systems.keys():
        system_results = detailed_df[detailed_df['system'] == system]

        if len(system_results) == 0:
            continue

        summary_data.append({
            'OCR System': system,
            'Documents Evaluated': len(system_results),
            'Mean CER': system_results['cer'].mean(),
            'Mean WER': system_results['wer'].mean(),
            'Mean BLEU Score': system_results['bleu'].mean(),
            'Mean Hallucination Rate': system_results['hallucination_rate'].mean(),
            'Char Accuracy': system_results['char_accuracy'].mean(),
            'Word Accuracy': system_results['word_accuracy'].mean(),
            'Total Char Errors': system_results['total_char_errors'].sum(),
            'Char Ins %': (system_results['char_insertions'].sum() / system_results['total_char_errors'].sum() * 100) if system_results['total_char_errors'].sum() > 0 else 0,
            'Char Del %': (system_results['char_deletions'].sum() / system_results['total_char_errors'].sum() * 100) if system_results['total_char_errors'].sum() > 0 else 0,
            'Char Sub %': (system_results['char_substitutions'].sum() / system_results['total_char_errors'].sum() * 100) if system_results['total_char_errors'].sum() > 0 else 0
        })

    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('Mean CER')

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    detailed_file = output_dir / f"table_evaluation_detailed_{timestamp}.csv"
    summary_file = output_dir / f"table_evaluation_summary_{timestamp}.csv"

    detailed_df.to_csv(detailed_file, index=False)
    summary_df.to_csv(summary_file, index=False)

    # Print summary
    print("=" * 80)
    print("EVALUATION SUMMARY - TABLE PERFORMANCE")
    print("=" * 80)
    print()
    print(summary_df.to_string(index=False))
    print()

    # Print rankings
    print("=" * 80)
    print("RANKINGS BY METRIC")
    print("=" * 80)
    print()

    print("Best CER (Lower is Better):")
    for idx, row in summary_df.nsmallest(3, 'Mean CER').iterrows():
        print(f"  {row['OCR System']:15} - {row['Mean CER']:.4f}")
    print()

    print("Best WER (Lower is Better):")
    for idx, row in summary_df.nsmallest(3, 'Mean WER').iterrows():
        print(f"  {row['OCR System']:15} - {row['Mean WER']:.4f}")
    print()

    print("Best BLEU Score (Higher is Better):")
    for idx, row in summary_df.nlargest(3, 'Mean BLEU Score').iterrows():
        print(f"  {row['OCR System']:15} - {row['Mean BLEU Score']:.4f}")
    print()

    print("=" * 80)
    print("RESULTS SAVED")
    print("=" * 80)
    print(f"Detailed results: {detailed_file}")
    print(f"Summary results: {summary_file}")
    print()


if __name__ == "__main__":
    main()
