#!/usr/bin/env python3
"""
Comprehensive OCR Error Analysis

Categorizes ALL OCR errors into the categories discussed in the paper:
1. Artifact-related: phantom letters, duplicated strokes, spurious punctuation
2. Long s errors: ſ confused with f or l
3. Character substitutions (non-long-s)
4. Character deletions
5. Character insertions (non-artifact)
6. Partial word errors (truncation)

This allows us to say "X% of all OCR errors were [category]" with confidence.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter, defaultdict
import difflib

# Paths
GOLD_STANDARD_DIR = r"/mnt/z/Corpus/Corpus_Gold/page"
STANDARDIZED_DIR = r"/mnt/z/OCR Evaluation/standardized"

OCR_SYSTEMS = {
    "OlmOCRv2": f"{STANDARDIZED_DIR}/OlmOCRv2",
    "OlmOCRv1": f"{STANDARDIZED_DIR}/OlmOCRv1",
    "Tesseract": f"{STANDARDIZED_DIR}/Tesseract",
    "EasyOCR": f"{STANDARDIZED_DIR}/EasyOCR",
    "Kraken": f"{STANDARDIZED_DIR}/Kraken",
    "MinerU": f"{STANDARDIZED_DIR}/MinerU",
    "DeepSeek": f"{STANDARDIZED_DIR}/DeepSeek",
    "Gemini": f"{STANDARDIZED_DIR}/Gemini",
    "Transkribus": f"{STANDARDIZED_DIR}/Transkribus",
    "Chandra-Home": f"{STANDARDIZED_DIR}/Chandra-Home",
}

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
        return ""


def extract_text_from_markdown(md_path):
    """Extract text from markdown file (already standardized)."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Handle standardized files (everything on one line)
        # Remove markdown header at start
        if content.startswith('#'):
            if ' { ' in content:
                # Pattern: "# Title { actual content"
                content = content.split(' { ', 1)[-1]
            elif '\n' in content:
                # Multi-line: remove first line if it's a header
                lines = content.split('\n')
                lines = [line for line in lines if not line.strip().startswith('#')]
                content = ' '.join(lines)
            else:
                # Single line: "# filename content" - find where filename ends
                # Look for _page_NNN pattern as end of filename, then take content after
                import re
                match = re.search(r'_page_\d+\s+(.+)', content)
                if match:
                    content = match.group(1)
                else:
                    # Fallback: try to find .md pattern or just remove header
                    match2 = re.search(r'\.md\s+(.+)', content)
                    if match2:
                        content = match2.group(1)
                    else:
                        # Last resort: remove "# filename " pattern
                        content = re.sub(r'^#[^#]*?\s{2,}', '', content)

        text = content.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text
    except Exception as e:
        return ""


def normalize_text(text):
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_opcodes(ref, hyp):
    """Get edit operations between reference and hypothesis."""
    matcher = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    return matcher.get_opcodes()


def classify_all_errors(ref_text, hyp_text):
    """
    Classify ALL character-level errors into categories.

    Returns a dict with counts for each category:
    - long_s_errors: ſ/s confused with f or l
    - artifact_phantom: inserted letters (not duplicates)
    - artifact_duplicate: duplicated strokes (char appears near same char in ref)
    - artifact_punctuation: spurious punctuation inserted
    - other_insertions: other inserted characters
    - deletions: deleted characters
    - substitutions_other: substitutions not involving long s
    """

    errors = {
        'long_s_to_f': 0,           # s → f (long s error)
        'long_s_to_l': 0,           # s → l (long s error)
        'long_s_total': 0,          # Total long s errors
        'artifact_phantom': 0,       # Phantom letters (insertions)
        'artifact_duplicate': 0,     # Duplicated strokes
        'artifact_punctuation': 0,   # Spurious punctuation
        'other_insertions': 0,       # Other insertions
        'deletions': 0,              # Deleted characters
        'substitutions_other': 0,    # Other substitutions
        'total_errors': 0,
    }

    # Track specific examples
    long_s_examples = []

    punctuation_chars = set('.,;:!?\'"-()[]{}@#$%^&*+=<>/\\|`~""''')

    opcodes = get_opcodes(ref_text, hyp_text)

    for op, i1, i2, j1, j2 in opcodes:
        if op == 'equal':
            continue

        elif op == 'replace':
            # Character substitutions
            ref_chars = ref_text[i1:i2]
            hyp_chars = hyp_text[j1:j2]

            # Align characters for comparison
            for k in range(max(len(ref_chars), len(hyp_chars))):
                ref_char = ref_chars[k] if k < len(ref_chars) else ''
                hyp_char = hyp_chars[k] if k < len(hyp_chars) else ''

                if ref_char and hyp_char:
                    # This is a substitution
                    errors['total_errors'] += 1

                    # Check for long s error: s → f or s → l
                    if ref_char == 's' and hyp_char == 'f':
                        errors['long_s_to_f'] += 1
                        errors['long_s_total'] += 1
                        # Get context for example
                        ctx_start = max(0, i1 - 5)
                        ctx_end = min(len(ref_text), i2 + 5)
                        long_s_examples.append(ref_text[ctx_start:ctx_end])
                    elif ref_char == 's' and hyp_char == 'l':
                        errors['long_s_to_l'] += 1
                        errors['long_s_total'] += 1
                    else:
                        errors['substitutions_other'] += 1

                elif ref_char and not hyp_char:
                    # Deletion within replacement block
                    errors['deletions'] += 1
                    errors['total_errors'] += 1
                elif hyp_char and not ref_char:
                    # Insertion within replacement block
                    errors['total_errors'] += 1
                    if hyp_char in punctuation_chars:
                        errors['artifact_punctuation'] += 1
                    elif hyp_char.isalpha():
                        # Check if it's a duplicate of nearby character
                        context = ref_text[max(0,i1-2):min(len(ref_text),i2+2)]
                        if hyp_char.lower() in context.lower():
                            errors['artifact_duplicate'] += 1
                        else:
                            errors['artifact_phantom'] += 1
                    else:
                        errors['other_insertions'] += 1

        elif op == 'insert':
            # Characters in hypothesis not in reference
            inserted = hyp_text[j1:j2]
            for char in inserted:
                errors['total_errors'] += 1
                if char in punctuation_chars:
                    errors['artifact_punctuation'] += 1
                elif char.isalpha():
                    # Check for duplication
                    # Look at what's around this position in the reference
                    context_start = max(0, i1 - 3)
                    context_end = min(len(ref_text), i1 + 3)
                    context = ref_text[context_start:context_end]
                    if char.lower() in context.lower():
                        errors['artifact_duplicate'] += 1
                    else:
                        errors['artifact_phantom'] += 1
                else:
                    errors['other_insertions'] += 1

        elif op == 'delete':
            # Characters in reference not in hypothesis
            deleted_count = i2 - i1
            errors['deletions'] += deleted_count
            errors['total_errors'] += deleted_count

    return errors, long_s_examples[:10]  # Return up to 10 examples


def find_matching_ocr_file(gold_filename, ocr_dir):
    """Find matching OCR file for a gold standard file."""
    base_name = gold_filename.replace('.xml', '')
    ocr_path = Path(ocr_dir)

    # Try exact patterns first
    patterns = [
        f"{base_name}.md",
        f"{base_name}_page_001.md",
    ]

    for pattern in patterns:
        candidate = ocr_path / pattern
        if candidate.exists():
            return candidate

    # Fuzzy match - look for files that start with similar prefix
    # Handle cases where gold is "file.xml" but OCR is "file_page_001.md"
    for md_file in ocr_path.glob("*.md"):
        md_base = md_file.name.replace('_page_001.md', '').replace('.md', '')
        if md_base == base_name or base_name.startswith(md_base) or md_base.startswith(base_name):
            return md_file
        # Also check if first 50 chars match
        if base_name[:50] in md_file.name or md_file.name[:50] in base_name:
            return md_file

    return None


def analyze_corpus(target_words=5000):
    """Analyze corpus and categorize all errors."""
    gold_path = Path(GOLD_STANDARD_DIR)
    gold_files = sorted(gold_path.glob("*.xml"))

    all_results = {}

    for ocr_system, ocr_dir in OCR_SYSTEMS.items():
        if not Path(ocr_dir).exists():
            print(f"Skipping {ocr_system} - directory not found")
            continue

        print(f"\nAnalyzing {ocr_system}...")

        total_words = 0
        combined_errors = defaultdict(int)
        all_long_s_examples = []
        docs_analyzed = 0

        for gold_file in gold_files:
            if total_words >= target_words:
                break

            ocr_file = find_matching_ocr_file(gold_file.name, ocr_dir)
            if not ocr_file:
                continue

            gold_text = extract_text_from_xml(str(gold_file))
            ocr_text = extract_text_from_markdown(str(ocr_file))

            if not gold_text or not ocr_text:
                continue

            gold_norm = normalize_text(gold_text)
            ocr_norm = normalize_text(ocr_text)

            word_count = len(gold_norm.split())
            total_words += word_count
            docs_analyzed += 1

            errors, examples = classify_all_errors(gold_norm, ocr_norm)

            for key, value in errors.items():
                combined_errors[key] += value
            all_long_s_examples.extend(examples)

        # Calculate percentages
        total = combined_errors['total_errors']
        if total > 0:
            artifact_total = (combined_errors['artifact_phantom'] +
                            combined_errors['artifact_duplicate'] +
                            combined_errors['artifact_punctuation'])

            results = {
                'docs_analyzed': docs_analyzed,
                'total_words': total_words,
                'total_errors': total,
                'errors': dict(combined_errors),
                'long_s_pct': (combined_errors['long_s_total'] / total) * 100,
                'artifact_pct': (artifact_total / total) * 100,
                'deletion_pct': (combined_errors['deletions'] / total) * 100,
                'substitution_pct': (combined_errors['substitutions_other'] / total) * 100,
                'long_s_examples': all_long_s_examples[:5],
            }

            all_results[ocr_system] = results

            print(f"  Documents: {docs_analyzed}, Words: {total_words}")
            print(f"  Total errors: {total}")
            print(f"  --- Error Breakdown ---")
            print(f"  Long s errors (s→f/l): {combined_errors['long_s_total']} ({results['long_s_pct']:.1f}%)")
            print(f"    - s→f: {combined_errors['long_s_to_f']}")
            print(f"    - s→l: {combined_errors['long_s_to_l']}")
            print(f"  Artifact errors: {artifact_total} ({results['artifact_pct']:.1f}%)")
            print(f"    - Phantom letters: {combined_errors['artifact_phantom']}")
            print(f"    - Duplicated strokes: {combined_errors['artifact_duplicate']}")
            print(f"    - Spurious punctuation: {combined_errors['artifact_punctuation']}")
            print(f"  Deletions: {combined_errors['deletions']} ({results['deletion_pct']:.1f}%)")
            print(f"  Other substitutions: {combined_errors['substitutions_other']} ({results['substitution_pct']:.1f}%)")
            print(f"  Other insertions: {combined_errors['other_insertions']}")

    return all_results


def print_summary(results):
    """Print summary statistics across all systems."""
    print("\n" + "=" * 80)
    print("SUMMARY ACROSS ALL SYSTEMS")
    print("=" * 80)

    # Calculate averages
    long_s_pcts = [r['long_s_pct'] for r in results.values()]
    artifact_pcts = [r['artifact_pct'] for r in results.values()]

    print(f"\nLong s errors (s→f or s→l):")
    print(f"  Average: {sum(long_s_pcts)/len(long_s_pcts):.1f}%")
    print(f"  Range: {min(long_s_pcts):.1f}% - {max(long_s_pcts):.1f}%")

    print(f"\nArtifact-related errors (phantom letters, duplicates, spurious punctuation):")
    print(f"  Average: {sum(artifact_pcts)/len(artifact_pcts):.1f}%")
    print(f"  Range: {min(artifact_pcts):.1f}% - {max(artifact_pcts):.1f}%")

    # Print table
    print("\n" + "-" * 80)
    print(f"{'System':<15} {'Long s %':>10} {'Artifact %':>12} {'Deletions %':>12} {'Other Sub %':>12}")
    print("-" * 80)

    for system, data in sorted(results.items(), key=lambda x: x[1]['long_s_pct'], reverse=True):
        print(f"{system:<15} {data['long_s_pct']:>9.1f}% {data['artifact_pct']:>11.1f}% "
              f"{data['deletion_pct']:>11.1f}% {data['substitution_pct']:>11.1f}%")


if __name__ == "__main__":
    print("=" * 80)
    print("COMPREHENSIVE OCR ERROR ANALYSIS")
    print("Categorizing ALL errors for valid percentage claims")
    print("=" * 80)

    results = analyze_corpus(TARGET_WORDS)
    print_summary(results)
