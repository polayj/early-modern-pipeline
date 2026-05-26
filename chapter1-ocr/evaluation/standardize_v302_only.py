#!/usr/bin/env python3
"""Quick script to standardize only Tesseract v3.02 outputs."""

import re
from pathlib import Path

def fully_standardize(text):
    """Fully standardize text: lowercase, single spaces, strip."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def extract_text_from_md(md_path):
    """Extract text from markdown file."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove markdown headers
        if content.startswith('#'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('#')]
            content = ' '.join(lines)

        return content
    except Exception as e:
        print(f"  Error reading {md_path.name}: {e}")
        return ""

# Source and output directories
SOURCE_DIR = Path("Z:/Tesseract/tesseract_v3.02/output/md")
OUTPUT_DIR = Path("Z:/standardized/Tesseract-v3.02")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("Processing Tesseract-v3.02...")
md_files = list(SOURCE_DIR.glob("*.md"))
success = 0

for md_file in md_files:
    text = extract_text_from_md(md_file)
    if text:
        standardized = fully_standardize(text)
        output_file = OUTPUT_DIR / md_file.name
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(standardized)
        success += 1

print(f"Processed {success}/{len(md_files)} files")
print(f"Output: {OUTPUT_DIR}")
