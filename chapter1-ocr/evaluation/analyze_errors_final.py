#!/usr/bin/env python3
"""
Final comprehensive OCR error analysis.
Categorizes ALL errors to support valid percentage claims.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
import difflib
from collections import defaultdict

GOLD_DIR = Path("/mnt/z/Corpus/Corpus_Gold/page")
STANDARDIZED_DIR = Path("/mnt/z/OCR Evaluation/standardized")
TARGET_WORDS = 5000

OCR_SYSTEMS = [
    "OlmOCRv2", "OlmOCRv1", "Tesseract", "EasyOCR", "Kraken",
    "MinerU", "DeepSeek", "Gemini", "Transkribus", "Chandra-Home"
]


def extract_xml(path):
    """Extract text from gold standard XML."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        ns = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
        texts = []
        for tl in root.findall('.//page:TextLine', ns):
            u = tl.find('.//page:Unicode', ns)
            if u is not None and u.text:
                texts.append(u.text)
        return ' '.join(texts)
    except:
        return ""


def extract_md(path):
    """Extract text from standardized markdown."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Handle various header formats
        if content.startswith('#'):
            if ' { ' in content:
                content = content.split(' { ', 1)[-1]
            elif '\n' in content:
                lines = content.split('\n')
                lines = [l for l in lines if not l.strip().startswith('#')]
                content = ' '.join(lines)
            else:
                # Look for _page_NNN pattern
                match = re.search(r'_page_\d+\s+(.+)', content)
                if match:
                    content = match.group(1)
                else:
                    # Try .md pattern
                    match2 = re.search(r'\.md\s+(.+)', content)
                    if match2:
                        content = match2.group(1)

        return re.sub(r'\s+', ' ', content.strip())
    except:
        return ""


def find_ocr_file(gold_name, ocr_dir):
    """Find matching OCR file."""
    base = gold_name.replace('.xml', '')

    # Try exact match first
    exact = ocr_dir / f"{base}.md"
    if exact.exists():
        return exact

    exact2 = ocr_dir / f"{base}_page_001.md"
    if exact2.exists():
        return exact2

    # Fuzzy match
    for f in ocr_dir.glob("*.md"):
        fname = f.name.replace('.md', '').replace('_page_001', '').replace('.xml', '')
        if base[:50] in f.name or fname[:50] in base[:50]:
            return f

    return None


def normalize(text):
    """Normalize text for comparison."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def classify_errors(ref, hyp):
    """Classify all character-level errors."""
    errors = {
        'long_s_to_f': 0,
        'long_s_to_l': 0,
        'artifact_phantom': 0,
        'artifact_duplicate': 0,
        'artifact_punctuation': 0,
        'other_insertions': 0,
        'deletions': 0,
        'substitutions_other': 0,
        'total': 0,
    }

    punct = set('.,;:!?\'"-()[]{}@#$%^&*+=<>/\\|`~""''')

    matcher = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            continue

        if op == 'replace':
            ref_chars = ref[i1:i2]
            hyp_chars = hyp[j1:j2]

            for k in range(max(len(ref_chars), len(hyp_chars))):
                rc = ref_chars[k] if k < len(ref_chars) else ''
                hc = hyp_chars[k] if k < len(hyp_chars) else ''

                if rc and hc:
                    errors['total'] += 1
                    if rc == 's' and hc == 'f':
                        errors['long_s_to_f'] += 1
                    elif rc == 's' and hc == 'l':
                        errors['long_s_to_l'] += 1
                    else:
                        errors['substitutions_other'] += 1
                elif rc and not hc:
                    errors['deletions'] += 1
                    errors['total'] += 1
                elif hc and not rc:
                    errors['total'] += 1
                    if hc in punct:
                        errors['artifact_punctuation'] += 1
                    elif hc.isalpha():
                        ctx = ref[max(0,i1-2):min(len(ref),i2+2)]
                        if hc.lower() in ctx.lower():
                            errors['artifact_duplicate'] += 1
                        else:
                            errors['artifact_phantom'] += 1
                    else:
                        errors['other_insertions'] += 1

        elif op == 'insert':
            for hc in hyp[j1:j2]:
                errors['total'] += 1
                if hc in punct:
                    errors['artifact_punctuation'] += 1
                elif hc.isalpha():
                    ctx = ref[max(0,i1-3):min(len(ref),i1+3)]
                    if hc.lower() in ctx.lower():
                        errors['artifact_duplicate'] += 1
                    else:
                        errors['artifact_phantom'] += 1
                else:
                    errors['other_insertions'] += 1

        elif op == 'delete':
            n = i2 - i1
            errors['deletions'] += n
            errors['total'] += n

    return errors


def analyze_system(system_name):
    """Analyze one OCR system."""
    ocr_dir = STANDARDIZED_DIR / system_name
    if not ocr_dir.exists():
        return None

    gold_files = sorted(GOLD_DIR.glob("*.xml"))

    total_words = 0
    docs = 0
    combined = defaultdict(int)

    for gf in gold_files:
        if total_words >= TARGET_WORDS:
            break

        ocr_f = find_ocr_file(gf.name, ocr_dir)
        if not ocr_f:
            continue

        gold_text = normalize(extract_xml(str(gf)))
        ocr_text = normalize(extract_md(str(ocr_f)))

        if not gold_text or not ocr_text:
            continue

        words = len(gold_text.split())
        total_words += words
        docs += 1

        errors = classify_errors(gold_text, ocr_text)
        for k, v in errors.items():
            combined[k] += v

    if docs == 0 or combined['total'] == 0:
        return None

    total = combined['total']
    long_s = combined['long_s_to_f'] + combined['long_s_to_l']
    artifact = combined['artifact_phantom'] + combined['artifact_duplicate'] + combined['artifact_punctuation']

    return {
        'docs': docs,
        'words': total_words,
        'total_errors': total,
        'long_s': long_s,
        'long_s_pct': 100 * long_s / total,
        'artifact': artifact,
        'artifact_pct': 100 * artifact / total,
        'deletions': combined['deletions'],
        'deletions_pct': 100 * combined['deletions'] / total,
        'subs_other': combined['substitutions_other'],
        'subs_pct': 100 * combined['substitutions_other'] / total,
        'details': dict(combined),
    }


def main():
    print("=" * 80)
    print("COMPREHENSIVE OCR ERROR ANALYSIS")
    print("=" * 80)

    results = {}

    for system in OCR_SYSTEMS:
        print(f"\nAnalyzing {system}...")
        result = analyze_system(system)

        if result:
            results[system] = result
            print(f"  Documents: {result['docs']}, Words: {result['words']}")
            print(f"  Total errors: {result['total_errors']}")
            print(f"  Long s errors (s→f/l): {result['long_s']} ({result['long_s_pct']:.1f}%)")
            print(f"    - s→f: {result['details']['long_s_to_f']}")
            print(f"    - s→l: {result['details']['long_s_to_l']}")
            print(f"  Artifact errors: {result['artifact']} ({result['artifact_pct']:.1f}%)")
            print(f"    - Phantom: {result['details']['artifact_phantom']}")
            print(f"    - Duplicate: {result['details']['artifact_duplicate']}")
            print(f"    - Punctuation: {result['details']['artifact_punctuation']}")
            print(f"  Deletions: {result['deletions']} ({result['deletions_pct']:.1f}%)")
            print(f"  Other substitutions: {result['subs_other']} ({result['subs_pct']:.1f}%)")
        else:
            print(f"  No results (check file matching)")

    # Summary
    if results:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        long_s_pcts = [r['long_s_pct'] for r in results.values()]
        artifact_pcts = [r['artifact_pct'] for r in results.values()]

        print(f"\nLong s errors (s→f or s→l):")
        print(f"  Average: {sum(long_s_pcts)/len(long_s_pcts):.1f}%")
        print(f"  Range: {min(long_s_pcts):.1f}% - {max(long_s_pcts):.1f}%")

        print(f"\nArtifact-related errors:")
        print(f"  Average: {sum(artifact_pcts)/len(artifact_pcts):.1f}%")
        print(f"  Range: {min(artifact_pcts):.1f}% - {max(artifact_pcts):.1f}%")

        print("\n" + "-" * 80)
        print(f"{'System':<15} {'Long s %':>10} {'Artifact %':>12} {'Deletions %':>12} {'Other Sub %':>12}")
        print("-" * 80)

        for sys, data in sorted(results.items(), key=lambda x: x[1]['long_s_pct'], reverse=True):
            print(f"{sys:<15} {data['long_s_pct']:>9.1f}% {data['artifact_pct']:>11.1f}% "
                  f"{data['deletions_pct']:>11.1f}% {data['subs_pct']:>11.1f}%")


if __name__ == "__main__":
    main()
