#!/usr/bin/env python3
"""Quick script to standardize only Tesseract v3.02 outputs."""

import re
import sys
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

# Repo-relative defaults: chapter1-ocr/ is the parent of this script's directory
REPO_CH1 = Path(__file__).resolve().parents[1]

# Source and output directories
# NOTE: Tesseract v3.02 raw outputs were not archived in this repo; place them
# in this placeholder directory to re-run this script.
SOURCE_DIR = REPO_CH1 / "gold-standard" / "per-system-outputs" / "Tesseract-v3.02"
OUTPUT_DIR = REPO_CH1 / "results" / "standardized" / "Tesseract-v3.02"

if not SOURCE_DIR.exists():
    sys.exit(f"ERROR: Source directory not found: {SOURCE_DIR}\n"
             "Tesseract v3.02 outputs were not archived in this repository.")

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
