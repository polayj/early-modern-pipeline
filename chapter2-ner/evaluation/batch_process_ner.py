"""
Batch process 100 transcribed texts with both NER models

This script processes multiple text files (TXT or XML) and compares the performance of:
1. dell-research-harvard/historical_newspaper_ner
2. dslim/bert-base-NER

Supports PAGE XML format from Transkribus and plain text files.

Output structure:
- output/historical_newspaper_ner/ - Results from model 1
- output/bert_base_ner/ - Results from model 2
- output/comparison/ - Side-by-side comparisons and statistics

Usage:
    python batch_process_ner.py --input_dir "Z:/Corpus/Corpus_Gold/page" --file_ext .xml
"""

import os
import json
import argparse
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import warnings
warnings.filterwarnings('ignore')
from datetime import datetime
from collections import defaultdict
import xml.etree.ElementTree as ET

def load_models():
    """Load both NER models"""
    print("Loading models... (this may take a minute)\n")

    # Model 1: Historical newspaper NER
    print("1. Loading dell-research-harvard/historical_newspaper_ner...")
    tokenizer1 = AutoTokenizer.from_pretrained("dell-research-harvard/historical_newspaper_ner")
    model1 = AutoModelForTokenClassification.from_pretrained("dell-research-harvard/historical_newspaper_ner")
    ner_pipeline1 = pipeline("ner", model=model1, tokenizer=tokenizer1, aggregation_strategy="simple", device="cpu")

    # Model 2: Standard BERT NER
    print("2. Loading dslim/bert-base-NER...")
    ner_pipeline2 = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple", device="cpu")

    print("\nModels loaded successfully!\n")
    return ner_pipeline1, ner_pipeline2


def extract_text_from_page_xml(filepath):
    """Extract text from PAGE XML format (Transkribus)"""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Define namespace
        ns = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}

        # Find all Unicode elements within TextLine elements
        text_lines = []
        for text_line in root.findall('.//page:TextLine', ns):
            unicode_elem = text_line.find('.//page:Unicode', ns)
            if unicode_elem is not None and unicode_elem.text:
                text_lines.append(unicode_elem.text.strip())

        # Join all text lines with spaces
        return ' '.join(text_lines)

    except ET.ParseError as e:
        print(f"  Warning: XML parse error in {filepath}: {e}")
        return ""


def read_text_file(filepath):
    """Read text file with fallback encoding, supports TXT and PAGE XML"""
    # Check if it's XML
    if str(filepath).lower().endswith('.xml'):
        return extract_text_from_page_xml(filepath)

    # Otherwise, read as plain text
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # If all fail, read as binary and decode with errors='replace'
    with open(filepath, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')


def process_file(filepath, ner1, ner2, output_dir1, output_dir2):
    """Process a single file with both models"""
    filename = Path(filepath).stem

    # Read text
    text = read_text_file(filepath)

    # Skip empty files
    if not text.strip():
        print(f"  Warning: No text extracted from {filepath.name}")
        return None, None, filename

    # Run both models
    entities1 = ner1(text)
    entities2 = ner2(text)

    # Prepare results
    result1 = {
        'filename': filename,
        'text': text,
        'entities': [
            {
                'word': e['word'],
                'entity_group': e['entity_group'],
                'score': float(e['score']),
                'start': int(e['start']),
                'end': int(e['end'])
            }
            for e in entities1
        ],
        'entity_count': len(entities1)
    }

    result2 = {
        'filename': filename,
        'text': text,
        'entities': [
            {
                'word': e['word'],
                'entity_group': e['entity_group'],
                'score': float(e['score']),
                'start': int(e['start']),
                'end': int(e['end'])
            }
            for e in entities2
        ],
        'entity_count': len(entities2)
    }

    # Save individual results
    with open(os.path.join(output_dir1, f"{filename}.json"), 'w', encoding='utf-8') as f:
        json.dump(result1, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_dir2, f"{filename}.json"), 'w', encoding='utf-8') as f:
        json.dump(result2, f, indent=2, ensure_ascii=False)

    return result1, result2, filename


def generate_comparison_report(all_results, output_dir):
    """Generate comparison statistics and report"""

    stats1 = defaultdict(int)
    stats2 = defaultdict(int)

    total_entities1 = 0
    total_entities2 = 0
    total_files = len(all_results)
    valid_files = 0

    comparison_details = []

    for result1, result2, filename in all_results:
        if result1 is None or result2 is None:
            continue

        valid_files += 1

        # Count entity types
        for entity in result1['entities']:
            stats1[entity['entity_group']] += 1
            total_entities1 += 1

        for entity in result2['entities']:
            stats2[entity['entity_group']] += 1
            total_entities2 += 1

        # Per-file comparison
        comparison_details.append({
            'filename': filename,
            'model1_entity_count': result1['entity_count'],
            'model2_entity_count': result2['entity_count'],
            'difference': result1['entity_count'] - result2['entity_count']
        })

    # Generate summary report
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_files_processed': valid_files,
        'model1_name': 'dell-research-harvard/historical_newspaper_ner',
        'model2_name': 'dslim/bert-base-NER',
        'summary': {
            'model1': {
                'total_entities': total_entities1,
                'avg_entities_per_doc': total_entities1 / valid_files if valid_files > 0 else 0,
                'entity_type_counts': dict(stats1)
            },
            'model2': {
                'total_entities': total_entities2,
                'avg_entities_per_doc': total_entities2 / valid_files if valid_files > 0 else 0,
                'entity_type_counts': dict(stats2)
            }
        },
        'per_file_comparison': comparison_details
    }

    # Save JSON report
    with open(os.path.join(output_dir, 'comparison_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Generate human-readable report
    with open(os.path.join(output_dir, 'comparison_report.txt'), 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("NER MODEL COMPARISON REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total files processed: {valid_files}\n\n")

        f.write("-" * 80 + "\n")
        f.write("MODEL 1: dell-research-harvard/historical_newspaper_ner\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total entities found: {total_entities1}\n")
        f.write(f"Average entities per document: {total_entities1 / valid_files:.2f}\n")
        f.write("\nEntity type breakdown:\n")
        for entity_type, count in sorted(stats1.items()):
            f.write(f"  {entity_type}: {count} ({count/total_entities1*100:.1f}%)\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("MODEL 2: dslim/bert-base-NER\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total entities found: {total_entities2}\n")
        f.write(f"Average entities per document: {total_entities2 / valid_files:.2f}\n")
        f.write("\nEntity type breakdown:\n")
        for entity_type, count in sorted(stats2.items()):
            f.write(f"  {entity_type}: {count} ({count/total_entities2*100:.1f}%)\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("COMPARISON SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total difference: {total_entities1 - total_entities2} entities\n")
        f.write(f"Model 1 found {abs(total_entities1 - total_entities2)} ")
        f.write("more entities\n" if total_entities1 > total_entities2 else "fewer entities\n")

        # Files with biggest differences
        f.write("\n" + "-" * 80 + "\n")
        f.write("Top 10 files with biggest differences:\n")
        f.write("-" * 80 + "\n")
        sorted_details = sorted(comparison_details, key=lambda x: abs(x['difference']), reverse=True)[:10]
        for detail in sorted_details:
            f.write(f"\n{detail['filename']}:\n")
            f.write(f"  Model 1: {detail['model1_entity_count']} entities\n")
            f.write(f"  Model 2: {detail['model2_entity_count']} entities\n")
            f.write(f"  Difference: {detail['difference']}\n")

    return report


def main():
    parser = argparse.ArgumentParser(description='Batch process texts with NER models')
    parser.add_argument('--input_dir', type=str, required=True, help='Directory containing text files')
    parser.add_argument('--file_ext', type=str, default='.txt', help='File extension (default: .txt)')

    args = parser.parse_args()

    # Setup paths
    input_dir = Path(args.input_dir)
    output_dir1 = Path('output/historical_newspaper_ner')
    output_dir2 = Path('output/bert_base_ner')
    comparison_dir = Path('output/comparison')

    # Create output directories
    output_dir1.mkdir(parents=True, exist_ok=True)
    output_dir2.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    # Load models
    ner1, ner2 = load_models()

    # Get all text files
    text_files = list(input_dir.glob(f'*{args.file_ext}'))

    if not text_files:
        print(f"No files with extension '{args.file_ext}' found in {input_dir}")
        return

    print(f"Found {len(text_files)} files to process\n")
    print("=" * 80)
    print("Processing files...")
    print("=" * 80 + "\n")

    # Process all files
    all_results = []

    for i, filepath in enumerate(text_files, 1):
        print(f"[{i}/{len(text_files)}] Processing: {filepath.name}")
        result1, result2, filename = process_file(filepath, ner1, ner2, output_dir1, output_dir2)
        all_results.append((result1, result2, filename))

    print("\n" + "=" * 80)
    print("Generating comparison report...")
    print("=" * 80 + "\n")

    # Generate comparison report
    report = generate_comparison_report(all_results, comparison_dir)

    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"\nResults saved to:")
    print(f"  - Model 1 results: {output_dir1}")
    print(f"  - Model 2 results: {output_dir2}")
    print(f"  - Comparison report: {comparison_dir}/comparison_report.txt")
    print(f"  - Detailed JSON: {comparison_dir}/comparison_report.json")
    print(f"\nTotal files processed: {report['total_files_processed']}")
    print(f"Total entities found:")
    print(f"  - Model 1: {report['summary']['model1']['total_entities']}")
    print(f"  - Model 2: {report['summary']['model2']['total_entities']}")
    print()


if __name__ == "__main__":
    main()
