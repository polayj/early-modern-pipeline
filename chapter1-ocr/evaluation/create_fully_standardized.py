#!/usr/bin/env python3
"""
Create fully standardized versions of all OCR outputs and gold standard.

Standardization:
- Remove all extra whitespace (single space between words)
- Convert to lowercase
- Strip leading/trailing whitespace

Output: /mnt/z/standardized/
  - Gold_Standard/
  - OlmOCRv2/
  - OlmOCRv1/
  - Tesseract/
  - EasyOCR/
  - Kraken/
  - MinerU/
  - DeepSeek/
  - Gemini/
  - Transkribus/
  - Chandra-Home/
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

# Source directories
GOLD_STANDARD_DIR = Path("Z:/Corpus/Corpus_Gold/page")
EXISTING_STANDARDIZED_DIR = Path("Z:/OCR Evaluation/standardized")

# Output directory
OUTPUT_DIR = Path("Z:/standardized")

OCR_SYSTEMS = [
    "OlmOCRv2", "OlmOCRv1", "Tesseract", "Tesseract-Legacy", "Tesseract-v3.02",
    "EasyOCR", "Kraken", "MinerU", "DeepSeek", "Gemini", "Transkribus", "Chandra-Home",
    "LightOn", "Chandra-2"
]


def fully_standardize(text):
    """
    Fully standardize text:
    - Lowercase
    - Single spaces only
    - Strip whitespace
    """
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def extract_text_from_xml(xml_path):
    """Extract text from gold standard PAGE XML."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
        texts = []
        for textline in root.findall('.//page:TextLine', ns):
            unicode_elem = textline.find('.//page:Unicode', ns)
            if unicode_elem is not None and unicode_elem.text:
                texts.append(unicode_elem.text)
        return ' '.join(texts)
    except Exception as e:
        print(f"  Error reading XML {xml_path.name}: {e}")
        return ""


def extract_text_from_md(md_path):
    """Extract text from markdown file (already partially standardized)."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Handle various header formats from previous standardization
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
                    match2 = re.search(r'\.md\s+(.+)', content)
                    if match2:
                        content = match2.group(1)

        return content
    except Exception as e:
        print(f"  Error reading MD {md_path.name}: {e}")
        return ""


def process_gold_standard():
    """Process and standardize gold standard files."""
    print("\nProcessing Gold Standard...")

    output_dir = OUTPUT_DIR / "Gold_Standard"
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_files = list(GOLD_STANDARD_DIR.glob("*.xml"))
    success = 0

    for xml_file in xml_files:
        text = extract_text_from_xml(xml_file)
        if text:
            standardized = fully_standardize(text)

            # Save as .md file with same base name
            output_file = output_dir / (xml_file.stem + ".md")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(standardized)
            success += 1

    print(f"  Processed {success}/{len(xml_files)} files")
    return success


def process_ocr_system(system_name):
    """Process and standardize one OCR system."""
    print(f"\nProcessing {system_name}...")

    source_dir = EXISTING_STANDARDIZED_DIR / system_name
    if not source_dir.exists():
        print(f"  Source directory not found: {source_dir}")
        return 0

    output_dir = OUTPUT_DIR / system_name
    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(source_dir.glob("*.md"))
    success = 0

    for md_file in md_files:
        text = extract_text_from_md(md_file)
        if text:
            standardized = fully_standardize(text)

            # Save as .md file, normalizing the filename
            # Remove _page_001 suffix if present for consistency
            stem = md_file.stem.replace('_page_001', '')
            output_file = output_dir / (stem + ".md")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(standardized)
            success += 1

    print(f"  Processed {success}/{len(md_files)} files")
    return success


def main():
    print("=" * 70)
    print("CREATING FULLY STANDARDIZED CORPUS")
    print("=" * 70)
    print(f"\nOutput directory: {OUTPUT_DIR}")
    print("\nStandardization applied:")
    print("  - Convert to lowercase")
    print("  - Single space between words")
    print("  - Strip leading/trailing whitespace")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process gold standard
    gold_count = process_gold_standard()

    # Process each OCR system
    ocr_counts = {}
    for system in OCR_SYSTEMS:
        ocr_counts[system] = process_ocr_system(system)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nGold Standard: {gold_count} files")
    for system, count in ocr_counts.items():
        print(f"{system}: {count} files")

    print(f"\nAll files saved to: {OUTPUT_DIR}")
    print("\nFolder structure:")
    print("  Z:/standardized/")
    print("    Gold_Standard/")
    for system in OCR_SYSTEMS:
        print(f"    {system}/")


if __name__ == "__main__":
    main()
