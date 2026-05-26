#!/usr/bin/env python3
"""
Batch OCR Evaluation - Evaluate all OCR systems at once

This script runs ocr_evaluation.py on all available OCR systems.
Comment out systems you don't have markdown files for yet.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION - Edit this section to customize your evaluation
# ============================================================================

# Path to your gold standard XML files
GOLD_STANDARD_DIR = r"Z:\Corpus\Corpus_Gold\page"

# Directory where timestamped results will be saved
# Results will be saved to: OUTPUT_DIR/evaluation_YYYYMMDD_HHMMSS/
OUTPUT_DIR = r"Z:\OCR Evaluation\results"

# Strip markdown headers (lines starting with #) from OCR outputs
# Set to True if some OCR systems include titles while others don't
STRIP_MARKDOWN_HEADERS = False

# Use standardized (whitespace-normalized) versions of OCR outputs
# Set to True to use files from "standardized" folder (created by standardize_text.py)
# Set to False to use original OCR output files
USE_STANDARDIZED = True

# Path to standardized files (only used if USE_STANDARDIZED = True)
STANDARDIZED_DIR = r"Z:\standardized"

# ============================================================================
# OCR SYSTEMS CONFIGURATION
# ============================================================================
# Add or remove OCR systems here. Each entry is a tuple: (name, path_to_md_files)
#
# To add a new OCR system:
#   1. Add a new line: ("SystemName", r"Z:\Path\To\System\md"),
#
# To temporarily disable an OCR system:
#   - Add # at the start of the line to comment it out
#   - Example: # ("Tesseract", r"Z:\Tesseract\completed\md"),
#
# To permanently remove an OCR system:
#   - Delete the entire line
# ============================================================================

OCR_SYSTEMS = [
    # Active OCR Systems (edit paths as needed for your setup)
    ("Tesseract", r"Z:\Tesseract\completed\md"),
    ("Tesseract-Legacy", r"Z:\Tesseract\output_legacy\md"),
    #("Tesseract-v3.02", r"Z:\Tesseract\tesseract_v3.02\output\md"),
    ("EasyOCR", r"Z:\EasyOCR\completed\md"),
    ("Kraken", r"Z:\Kraken\completed\md"),
    ("Gemini", r"Z:\Gemini\completed"),
    ("MinerU", r"Z:\MinerU\md"),
    ("OlmOCRv1", r"Z:\OlmOCR\complete\md"),
    ("OlmOCRv2", r"Z:\OlmOCR\complete_v2\md"),
    #("OlmOCR-Ensemble", r"Z:\OlmOCR\ensemble\md"),
    ("Transkribus", r"Z:\Transkribus Raw\Print"),
    ("DeepSeek", r"Z:\DeepSeek\DeepSeek-OCR\complete\md"),
    ("Chandra-1", r"Z:\Chandra\complete\md"),
    ("LightOn", r"Z:\LightOn\outputs\md"),
    ("Chandra-2", r"Z:\Chandra\complete_chandra2\md"),

    # Add new OCR systems below this line:
    # ("NewSystem", r"Z:\NewSystem\completed\md"),
]

# ============================================================================
# END CONFIGURATION
# ============================================================================

def check_directory_exists(path):
    """Check if a directory exists"""
    return Path(path).exists()

def main():
    """Run OCR evaluation on all configured systems"""
    print("=" * 80)
    print("BATCH OCR EVALUATION")
    print("=" * 80)
    print()

    # Verify gold standard directory exists
    if not check_directory_exists(GOLD_STANDARD_DIR):
        print(f"ERROR: Gold standard directory not found: {GOLD_STANDARD_DIR}")
        print("Please check the path and try again.")
        sys.exit(1)

    # Create output directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(OUTPUT_DIR) / f"evaluation_{timestamp}"
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Gold Standard: {GOLD_STANDARD_DIR}")
    print(f"Output Directory: {output_path}")
    print()

    # Determine which directories to use
    if USE_STANDARDIZED:
        print(f"Using STANDARDIZED files from: {STANDARDIZED_DIR}")
        print()
    else:
        print("Using ORIGINAL OCR output files")
        print()

    # Check which OCR systems are available
    available_systems = []
    unavailable_systems = []

    for name, md_dir in OCR_SYSTEMS:
        # Use standardized directory if enabled
        if USE_STANDARDIZED:
            md_dir = str(Path(STANDARDIZED_DIR) / name)

        if check_directory_exists(md_dir):
            # Check if directory has .md files
            md_files = list(Path(md_dir).glob('*.md'))
            if md_files:
                available_systems.append((name, md_dir))
                print(f"[OK] {name:15} - {len(md_files)} .md files found")
            else:
                unavailable_systems.append((name, md_dir))
                print(f"[SKIP] {name:15} - Directory exists but no .md files found")
        else:
            unavailable_systems.append((name, md_dir))
            print(f"[SKIP] {name:15} - Directory not found")

    print()
    print(f"Available systems: {len(available_systems)}")
    print(f"Unavailable systems: {len(unavailable_systems)}")
    print()

    if not available_systems:
        print("ERROR: No OCR systems with markdown files found!")
        print()
        print("Make sure you have .md files in at least one of these directories:")
        for name, md_dir in OCR_SYSTEMS:
            print(f"  {name}: {md_dir}")
        sys.exit(1)

    # Ask for confirmation (skip if running non-interactively)
    try:
        response = input(f"Evaluate {len(available_systems)} OCR systems? (y/n, default=y): ").strip().lower()
        if response and response != 'y':
            print("Cancelled.")
            sys.exit(0)
    except EOFError:
        # Running non-interactively, proceed with default (yes)
        print("y")
        pass

    print()
    print("=" * 80)
    print("RUNNING EVALUATION")
    print("=" * 80)
    print()

    # Build command for ocr_evaluation.py
    cmd = [
        sys.executable,  # Use same Python interpreter
        "ocr_evaluation.py",
        "-g", GOLD_STANDARD_DIR,
        "--output-dir", str(output_path),
        "--similarity-threshold", "0.6",  # Adjust if needed
    ]

    # Add markdown header stripping flag if enabled
    if STRIP_MARKDOWN_HEADERS:
        cmd.append("--strip-markdown-headers")

    # Add all available OCR systems
    for name, md_dir in available_systems:
        cmd.extend(["-o", md_dir, "-n", name])

    # Run the evaluation
    print("Command:")
    print(" ".join(cmd))
    print()

    try:
        result = subprocess.run(
            cmd,
            check=True,
            cwd=Path(__file__).parent,  # Run in OCR Evaluation directory
            text=True
        )

        print()
        print("=" * 80)
        print("EVALUATION COMPLETE!")
        print("=" * 80)
        print()
        print(f"Results saved to: {output_path}")
        print(f"  - {output_path / 'ocr_evaluation_detailed.csv'}")
        print(f"  - {output_path / 'ocr_evaluation_summary.csv'}")
        print()

    except subprocess.CalledProcessError as e:
        print()
        print("=" * 80)
        print("ERROR DURING EVALUATION")
        print("=" * 80)
        print(f"Exit code: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        print("Evaluation cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
