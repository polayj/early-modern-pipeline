#!/usr/bin/env python3
"""
Analyze artifact-related OCR errors (phantom letters, duplicated strokes, spurious punctuation)

This script analyzes a subset of the corpus to identify errors likely caused by scan artifacts
rather than character misrecognition.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
import difflib

# Paths - adjust as needed
GOLD_STANDARD_DIR = r"/mnt/z/Corpus/Corpus_Gold/page"

# Use standardized versions (no Chandra available in standardized)
USE_STANDARDIZED = True
STANDARDIZED_DIR = r"/mnt/z/OCR Evaluation/standardized"

OCR_DIRS = {
    "OlmOCRv2": r"/mnt/z/OlmOCR/complete_v2/md",
    "OlmOCRv1": r"/mnt/z/OlmOCR/complete/md",
    "Tesseract": r"/mnt/z/Tesseract/completed/md",
    "EasyOCR": r"/mnt/z/EasyOCR/completed/md",
    "Kraken": r"/mnt/z/Kraken/completed/md",
    "MinerU": r"/mnt/z/MinerU/md",
    "DeepSeek": r"/mnt/z/DeepSeek/DeepSeek-OCR/complete/md",
    "Gemini": r"/mnt/z/Gemini/completed",
}

# Standardized paths (used if USE_STANDARDIZED=True)
OCR_DIRS_STANDARDIZED = {
    "OlmOCRv2": f"{STANDARDIZED_DIR}/OlmOCRv2",
    "OlmOCRv1": f"{STANDARDIZED_DIR}/OlmOCRv1",
    "Tesseract": f"{STANDARDIZED_DIR}/Tesseract",
    "EasyOCR": f"{STANDARDIZED_DIR}/EasyOCR",
    "Kraken": f"{STANDARDIZED_DIR}/Kraken",
    "MinerU": f"{STANDARDIZED_DIR}/MinerU",
    "DeepSeek": f"{STANDARDIZED_DIR}/DeepSeek",
    "Gemini": f"{STANDARDIZED_DIR}/Gemini",
    "Transkribus": f"{STANDARDIZED_DIR}/Transkribus",
}

# Target word count for subset analysis
TARGET_WORDS = 5000


def extract_text_from_xml(xml_path):
    """Extract text from Transkribus PAGE XML format."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
        text_lines = []
        for textline in root.findall('.//page:TextLine', ns):
            unicode_elem = textline.find('.//page:Unicode', ns)
            if unicode_elem is not None and unicode_elem.text:
                text_lines.append(unicode_elem.text)
        return ' '.join(text_lines)
    except Exception as e:
        print(f"Error parsing XML {xml_path}: {e}")
        return ""


def extract_text_from_markdown(md_path, strip_headers=True):
    """Extract text from markdown file."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        if strip_headers:
            lines = [line for line in lines if not line.strip().startswith('#')]
        text = '\n'.join(lines).strip()
        text = re.sub(r' +', ' ', text)
        return text
    except Exception as e:
        print(f"Error reading markdown {md_path}: {e}")
        return ""


def normalize_text(text):
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_detailed_edits(ref, hyp):
    """
    Get detailed character-level edits between reference and hypothesis.
    Returns list of (operation, ref_char, hyp_char, position) tuples.
    """
    edits = []
    matcher = difflib.SequenceMatcher(None, ref, hyp)

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            continue
        elif op == 'replace':
            for k in range(max(i2 - i1, j2 - j1)):
                ref_char = ref[i1 + k] if i1 + k < i2 else ''
                hyp_char = hyp[j1 + k] if j1 + k < j2 else ''
                edits.append(('substitute', ref_char, hyp_char, i1 + k))
        elif op == 'insert':
            for k in range(j2 - j1):
                edits.append(('insert', '', hyp[j1 + k], i1))
        elif op == 'delete':
            for k in range(i2 - i1):
                edits.append(('delete', ref[i1 + k], '', i1 + k))

    return edits


def classify_artifact_errors(edits, ref_text, hyp_text):
    """
    Classify errors into artifact-related categories:
    - phantom_letters: Inserted characters (especially at word boundaries or creating nonsense)
    - duplicated_strokes: Repeated characters that shouldn't be repeated
    - spurious_punctuation: Inserted punctuation marks
    - other: Regular OCR errors (misrecognition, etc.)

    Returns dict with counts and examples.
    """
    artifact_errors = {
        'phantom_letters': [],
        'duplicated_strokes': [],
        'spurious_punctuation': [],
        'other_insertions': [],
        'deletions': [],
        'substitutions': []
    }

    punctuation_chars = set('.,;:!?\'"-()[]{}@#$%^&*+=<>/\\|`~')

    for op, ref_char, hyp_char, pos in edits:
        if op == 'insert':
            if hyp_char in punctuation_chars:
                artifact_errors['spurious_punctuation'].append((pos, hyp_char))
            else:
                # Check if this is a duplicated stroke (repeated character)
                # Look at surrounding context
                context_start = max(0, pos - 2)
                context_end = min(len(ref_text), pos + 2)
                context = ref_text[context_start:context_end]

                if hyp_char.isalpha():
                    # Check if character appears nearby (potential duplicate)
                    if hyp_char.lower() in context.lower():
                        artifact_errors['duplicated_strokes'].append((pos, hyp_char, context))
                    else:
                        artifact_errors['phantom_letters'].append((pos, hyp_char))
                else:
                    artifact_errors['other_insertions'].append((pos, hyp_char))
        elif op == 'delete':
            artifact_errors['deletions'].append((pos, ref_char))
        elif op == 'substitute':
            artifact_errors['substitutions'].append((pos, ref_char, hyp_char))

    return artifact_errors


def analyze_document(gold_path, ocr_path):
    """Analyze a single document pair for artifact errors."""
    gold_text = extract_text_from_xml(str(gold_path))
    ocr_text = extract_text_from_markdown(str(ocr_path))

    if not gold_text or not ocr_text:
        return None

    gold_norm = normalize_text(gold_text)
    ocr_norm = normalize_text(ocr_text)

    word_count = len(gold_norm.split())

    edits = get_detailed_edits(gold_norm, ocr_norm)
    artifact_errors = classify_artifact_errors(edits, gold_norm, ocr_norm)

    return {
        'word_count': word_count,
        'char_count': len(gold_norm),
        'total_edits': len(edits),
        'artifact_errors': artifact_errors
    }


def find_matching_ocr_file(gold_filename, ocr_dir):
    """Find matching OCR file for a gold standard file."""
    base_name = gold_filename.replace('.xml', '')
    ocr_path = Path(ocr_dir)

    # Try various patterns
    patterns = [
        f"{base_name}.md",
        f"{base_name}_page_001.md",
    ]

    for pattern in patterns:
        candidate = ocr_path / pattern
        if candidate.exists():
            return candidate

    # Try fuzzy matching
    for md_file in ocr_path.glob("*.md"):
        if base_name[:50] in md_file.name:
            return md_file

    return None


def analyze_corpus_subset(target_words=5000):
    """Analyze a subset of the corpus up to target_words."""
    gold_path = Path(GOLD_STANDARD_DIR)
    gold_files = sorted(gold_path.glob("*.xml"))

    results_by_system = {}

    for ocr_system, ocr_dir in OCR_DIRS.items():
        print(f"\nAnalyzing {ocr_system}...")

        total_words = 0
        total_chars = 0
        all_artifact_errors = {
            'phantom_letters': 0,
            'duplicated_strokes': 0,
            'spurious_punctuation': 0,
            'other_insertions': 0,
            'deletions': 0,
            'substitutions': 0
        }
        all_errors_total = 0
        docs_analyzed = 0

        for gold_file in gold_files:
            if total_words >= target_words:
                break

            ocr_file = find_matching_ocr_file(gold_file.name, ocr_dir)
            if not ocr_file:
                continue

            result = analyze_document(gold_file, ocr_file)
            if not result:
                continue

            docs_analyzed += 1
            total_words += result['word_count']
            total_chars += result['char_count']
            all_errors_total += result['total_edits']

            for error_type, errors in result['artifact_errors'].items():
                all_artifact_errors[error_type] += len(errors)

        # Calculate artifact-related percentage
        artifact_count = (all_artifact_errors['phantom_letters'] +
                         all_artifact_errors['duplicated_strokes'] +
                         all_artifact_errors['spurious_punctuation'])

        total_errors = all_errors_total
        artifact_pct = (artifact_count / total_errors * 100) if total_errors > 0 else 0

        results_by_system[ocr_system] = {
            'docs_analyzed': docs_analyzed,
            'total_words': total_words,
            'total_chars': total_chars,
            'total_errors': total_errors,
            'artifact_errors': all_artifact_errors,
            'artifact_count': artifact_count,
            'artifact_percentage': artifact_pct
        }

        print(f"  Documents analyzed: {docs_analyzed}")
        print(f"  Total words: {total_words}")
        print(f"  Total characters: {total_chars}")
        print(f"  Total errors: {total_errors}")
        print(f"  Artifact-related errors: {artifact_count}")
        print(f"    - Phantom letters: {all_artifact_errors['phantom_letters']}")
        print(f"    - Duplicated strokes: {all_artifact_errors['duplicated_strokes']}")
        print(f"    - Spurious punctuation: {all_artifact_errors['spurious_punctuation']}")
        print(f"  Artifact percentage of all errors: {artifact_pct:.1f}%")

    return results_by_system


if __name__ == "__main__":
    print("=" * 70)
    print("ARTIFACT ERROR ANALYSIS")
    print("=" * 70)

    results = analyze_corpus_subset(TARGET_WORDS)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for system, data in results.items():
        print(f"\n{system}:")
        print(f"  Words analyzed: {data['total_words']}")
        print(f"  Artifact errors: {data['artifact_count']} / {data['total_errors']} total errors")
        print(f"  Artifact percentage: {data['artifact_percentage']:.1f}%")
