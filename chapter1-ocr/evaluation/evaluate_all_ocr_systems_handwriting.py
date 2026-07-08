#!/usr/bin/env python3
"""
Batch OCR Evaluation - Handwriting Documents

Runs ocr_evaluation.py against the handwriting gold standard (.md files in
the handwriting-eval directory) for all OCR systems that have already been
run on those documents.

NOTE: The handwriting evaluation data was not archived in this repository.
To re-run this evaluation, place the gold standard .md files in
chapter1-ocr/gold-standard/handwriting-eval/ and the OCR outputs in
chapter1-ocr/gold-standard/handwriting-eval/ocr_outputs/<SystemName>/md/
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Repo-relative defaults: chapter1-ocr/ is the parent of this script's directory
REPO_CH1 = Path(__file__).resolve().parents[1]

# Placeholder: the handwriting evaluation data was NOT archived in this repo.
# Place the handwriting gold-standard .md files (and per-system OCR outputs
# under ocr_outputs/<SystemName>/) here to re-run this evaluation.
HANDWRITING_DIR = REPO_CH1 / "gold-standard" / "handwriting-eval"

# Gold standard: .md files alongside the handwriting PDFs
GOLD_STANDARD_DIR = str(HANDWRITING_DIR)

# Where timestamped results will be saved
OUTPUT_DIR = str(REPO_CH1 / "results" / "handwriting")

# Gold standard files are .md (not .xml)
GOLD_FORMAT = "md"

# Not using a standardized directory for handwriting (use raw outputs directly)
USE_STANDARDIZED = False

# Strip markdown headers from OCR outputs if some systems include them
STRIP_MARKDOWN_HEADERS = False

# ============================================================================
# OCR SYSTEMS CONFIGURATION
# Each entry: (display_name, path_to_md_files)
# Comment out systems whose outputs don't exist yet.
# ============================================================================

# Handwriting OCR outputs were not archived in this repo; these are the
# expected locations if the data is restored (see note above).
OCR_OUTPUTS_DIR = HANDWRITING_DIR / "ocr_outputs"

OCR_SYSTEMS = [
    ("Tesseract",        str(OCR_OUTPUTS_DIR / "Tesseract" / "md")),
    ("Tesseract-Legacy", str(OCR_OUTPUTS_DIR / "Tesseract-Legacy" / "md")),
    ("EasyOCR",          str(OCR_OUTPUTS_DIR / "EasyOCR" / "md")),
    ("Kraken",           str(OCR_OUTPUTS_DIR / "Kraken" / "md")),
    ("Gemini",           str(OCR_OUTPUTS_DIR / "Gemini")),
    ("MinerU",           str(OCR_OUTPUTS_DIR / "MinerU" / "md")),
    ("OlmOCRv1",         str(OCR_OUTPUTS_DIR / "OlmOCRv1" / "md")),
    ("OlmOCRv2",         str(OCR_OUTPUTS_DIR / "OlmOCRv2" / "md")),
    ("Transkribus",      str(OCR_OUTPUTS_DIR / "Transkribus")),
    ("DeepSeek",         str(OCR_OUTPUTS_DIR / "DeepSeek" / "md")),
    ("Chandra-1",        str(OCR_OUTPUTS_DIR / "Chandra-1" / "md")),
    ("LightOn",          str(OCR_OUTPUTS_DIR / "LightOn" / "md")),
    ("Chandra-2",        str(OCR_OUTPUTS_DIR / "Chandra-2" / "md")),

    # Add new systems below:
    # ("NewSystem", str(OCR_OUTPUTS_DIR / "NewSystem" / "md")),
]

# ============================================================================
# END CONFIGURATION
# ============================================================================


def check_directory_exists(path):
    return Path(path).exists()


def main():
    print("=" * 80)
    print("BATCH OCR EVALUATION - HANDWRITING")
    print("=" * 80)
    print()

    if not check_directory_exists(GOLD_STANDARD_DIR):
        print(f"ERROR: Gold standard directory not found: {GOLD_STANDARD_DIR}")
        print("The handwriting evaluation data was not archived in this repository.")
        print("Place the handwriting gold-standard .md files there to re-run.")
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(OUTPUT_DIR) / f"evaluation_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Gold Standard : {GOLD_STANDARD_DIR}  (format: {GOLD_FORMAT.upper()})")
    print(f"Output        : {output_path}")
    print()

    available_systems = []
    unavailable_systems = []

    for name, md_dir in OCR_SYSTEMS:
        if check_directory_exists(md_dir):
            md_files = list(Path(md_dir).glob('*.md'))
            if md_files:
                available_systems.append((name, md_dir))
                print(f"[OK]   {name:15} - {len(md_files)} .md files found")
            else:
                unavailable_systems.append((name, md_dir))
                print(f"[SKIP] {name:15} - Directory exists but no .md files")
        else:
            unavailable_systems.append((name, md_dir))
            print(f"[SKIP] {name:15} - Directory not found")

    print()
    print(f"Available: {len(available_systems)}   Skipped: {len(unavailable_systems)}")
    print()

    if not available_systems:
        print("ERROR: No OCR output directories with .md files found.")
        print(f"Expected OCR outputs under: {OCR_OUTPUTS_DIR}")
        sys.exit(1)

    try:
        response = input(f"Evaluate {len(available_systems)} OCR systems? (y/n, default=y): ").strip().lower()
        if response and response != 'y':
            print("Cancelled.")
            sys.exit(0)
    except EOFError:
        print("y")

    print()
    print("=" * 80)
    print("RUNNING EVALUATION")
    print("=" * 80)
    print()

    cmd = [
        sys.executable,
        "ocr_evaluation.py",
        "-g", GOLD_STANDARD_DIR,
        "--output-dir", str(output_path),
        "--similarity-threshold", "0.6",
        "--gold-format", GOLD_FORMAT,
    ]

    if STRIP_MARKDOWN_HEADERS:
        cmd.append("--strip-markdown-headers")

    for name, md_dir in available_systems:
        cmd.extend(["-o", md_dir, "-n", name])

    print("Command:")
    print(" ".join(cmd))
    print()

    try:
        subprocess.run(
            cmd,
            check=True,
            cwd=Path(__file__).parent,
            text=True
        )

        print()
        print("=" * 80)
        print("EVALUATION COMPLETE!")
        print("=" * 80)
        print()
        print(f"Results saved to: {output_path}")
        print(f"  - {output_path / 'ocr_evaluation_detailed_*.csv'}")
        print(f"  - {output_path / 'ocr_evaluation_summary_*.csv'}")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 80)
        print("ERROR DURING EVALUATION")
        print("=" * 80)
        print(f"Exit code: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
