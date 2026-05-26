#!/usr/bin/env python3
"""
Text Standardization Tool for OCR Outputs

This script standardizes text formatting across different OCR systems by:
- Copying .md files from original OCR system directories to a standardized folder
- Normalizing all whitespace (spaces, tabs, newlines) to single spaces
- Preserving all punctuation
- Maintaining word boundaries

This ensures fair comparison between OCR systems regardless of their
formatting choices (single-line vs multi-line, multiple spaces, etc.)
"""

import argparse
import re
import sys
import shutil
from pathlib import Path
from typing import List, Tuple

# Import OCR systems configuration from evaluate_all_ocr_systems.py
try:
    from evaluate_all_ocr_systems import OCR_SYSTEMS
except ImportError:
    OCR_SYSTEMS = []

# Default output directory for standardized files
STANDARDIZED_DIR = Path(__file__).parent / "standardized"


def standardize_text(text: str) -> str:
    """
    Standardize text by normalizing all whitespace to single spaces.

    Args:
        text: Input text with potentially irregular whitespace

    Returns:
        Standardized text with single-space separators
    """
    # Replace all sequences of whitespace (spaces, tabs, newlines) with a single space
    # \s matches any whitespace character (space, tab, newline, etc.)
    # + means one or more occurrences
    standardized = re.sub(r'\s+', ' ', text)

    # Strip leading and trailing whitespace
    standardized = standardized.strip()

    return standardized


def copy_and_standardize_file(source_path: Path, dest_path: Path) -> Tuple[bool, str]:
    """
    Copy a file to a new location and standardize its text.

    Args:
        source_path: Path to the source file
        dest_path: Path to the destination file

    Returns:
        Tuple of (success, message)
    """
    try:
        # Read the original content
        with open(source_path, 'r', encoding='utf-8') as f:
            original_text = f.read()

        # Standardize the text
        standardized_text = standardize_text(original_text)

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Write standardized text to destination
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(standardized_text)

        return True, f"Processed: {source_path.name}"

    except Exception as e:
        return False, f"Error processing {source_path.name}: {str(e)}"


def process_ocr_system(system_name: str, source_dir: Path, output_base_dir: Path,
                        pattern: str = "*.md") -> Tuple[int, int]:
    """
    Copy and standardize all files from an OCR system directory.

    Args:
        system_name: Name of the OCR system (e.g., "Tesseract")
        source_dir: Source directory with original files
        output_base_dir: Base output directory (e.g., "Z:\OCR Evaluation\standardized")
        pattern: File pattern to match (e.g., "*.md")

    Returns:
        Tuple of (success_count, failure_count)
    """
    if not source_dir.exists():
        print(f"  ✗ Source directory not found: {source_dir}")
        return 0, 0

    files = list(source_dir.glob(pattern))

    if not files:
        print(f"  ⚠ No {pattern} files found in {source_dir}")
        return 0, 0

    # Create output directory for this OCR system
    dest_dir = output_base_dir / system_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0

    for source_file in files:
        dest_file = dest_dir / source_file.name
        success, message = copy_and_standardize_file(source_file, dest_file)
        if success:
            success_count += 1
            print(f"  ✓ {message}")
        else:
            failure_count += 1
            print(f"  ✗ {message}")

    return success_count, failure_count


def main():
    """Main entry point for the text standardization tool"""
    parser = argparse.ArgumentParser(
        description="Copy OCR outputs to standardized folder and normalize whitespace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all OCR systems (from configuration)
  python standardize_text.py

  # Specify custom output directory
  python standardize_text.py --output "Z:\\OCR Evaluation\\standardized_v2"

  # Use different file pattern
  python standardize_text.py --pattern "*.txt"
        """
    )

    # Processing options
    parser.add_argument('--output', type=str, default=str(STANDARDIZED_DIR),
                       help=f'Output directory for standardized files (default: {STANDARDIZED_DIR})')
    parser.add_argument('--pattern', type=str, default='*.md',
                       help='File pattern to match (default: *.md)')

    args = parser.parse_args()

    output_dir = Path(args.output)

    print("=" * 80)
    print("TEXT STANDARDIZATION TOOL")
    print("=" * 80)
    print()
    print("This tool will:")
    print("  1. Copy .md files from each OCR system to a standardized folder")
    print("  2. Normalize all whitespace to single spaces")
    print("  3. Preserve all punctuation and word boundaries")
    print()
    print("Settings:")
    print(f"  Output directory: {output_dir}")
    print(f"  File pattern: {args.pattern}")
    print()

    # Check if we can load OCR systems configuration
    if not OCR_SYSTEMS:
        print("ERROR: Could not load OCR_SYSTEMS configuration.")
        print("Make sure evaluate_all_ocr_systems.py is in the same directory.")
        sys.exit(1)

    # Check if output directory already exists
    if output_dir.exists():
        print(f"WARNING: Output directory already exists: {output_dir}")
        response = input("Delete and recreate? (y/n, default=n): ").strip().lower()
        if response == 'y':
            shutil.rmtree(output_dir)
            print("Deleted existing directory.")
        else:
            print("Will merge with existing directory.")
        print()

    print(f"Processing {len(OCR_SYSTEMS)} OCR systems...")
    print()

    total_success = 0
    total_failure = 0

    for name, source_directory in OCR_SYSTEMS:
        print(f"{name}:")
        source_path = Path(source_directory)
        success, failure = process_ocr_system(name, source_path, output_dir, args.pattern)
        total_success += success
        total_failure += failure
        print()

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Successfully processed: {total_success} files")
    print(f"Failures: {total_failure} files")
    print()
    print(f"Standardized files saved to: {output_dir}")
    print()
    print("Next step: Update evaluate_all_ocr_systems.py to use these standardized folders")
    print()

    if total_failure > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
