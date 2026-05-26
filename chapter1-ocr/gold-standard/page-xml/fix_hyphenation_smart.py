#!/usr/bin/env python3
"""
Intelligently fix end-of-line hyphenation in PAGE XML files using dictionary validation.
Handles both hyphenated (Im- porter) and non-hyphenated (sur prise) splits.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Set
import argparse

# Register namespaces
NS = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
ET.register_namespace('', NS['page'])
ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')


def load_dictionary() -> Set[str]:
    """
    Load a dictionary of valid English words.
    Tries multiple sources in order of preference.
    """
    words = set()

    # Try 1: Use enchant (PyEnchant) if available
    try:
        import enchant
        d = enchant.Dict("en_US")
        # Get words from a standard word list
        print("Using PyEnchant dictionary")
        # We'll check words dynamically with d.check()
        return {'__enchant__': d}  # Special marker
    except (ImportError, Exception):
        pass

    # Try 2: Use NLTK words corpus
    try:
        import nltk
        from nltk.corpus import words as nltk_words
        try:
            word_list = set(w.lower() for w in nltk_words.words())
            print(f"Using NLTK dictionary ({len(word_list)} words)")
            return word_list
        except LookupError:
            print("NLTK words corpus not found. Downloading...")
            nltk.download('words', quiet=True)
            word_list = set(w.lower() for w in nltk_words.words())
            print(f"Using NLTK dictionary ({len(word_list)} words)")
            return word_list
    except ImportError:
        pass

    # Try 3: Use system dictionary file
    dict_paths = [
        '/usr/share/dict/words',
        '/usr/dict/words',
        'C:\\Program Files\\Git\\usr\\share\\dict\\words',
    ]

    for dict_path in dict_paths:
        try:
            with open(dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                words = set(line.strip().lower() for line in f if line.strip())
            print(f"Using system dictionary from {dict_path} ({len(words)} words)")
            return words
        except FileNotFoundError:
            continue

    # Fallback: Empty set with warning
    print("WARNING: No dictionary found. Install PyEnchant (pip install pyenchant) or NLTK (pip install nltk)")
    print("Proceeding without dictionary validation - all merges will be applied!")
    return set()


def is_valid_word(word: str, dictionary: Set[str]) -> bool:
    """Check if a word is valid according to the dictionary."""
    if not dictionary:
        return True  # No dictionary = accept all

    # Strip common punctuation from the word before checking
    word_clean = word.strip('.,;:!?\'\"()-')

    # Special case for enchant
    if '__enchant__' in dictionary:
        d = dictionary['__enchant__']
        return d.check(word_clean) or d.check(word_clean.lower()) or d.check(word_clean.capitalize())

    # Regular dictionary lookup (case-insensitive)
    word_lower = word_clean.lower()
    return word_lower in dictionary


def fix_hyphenation_in_file(xml_path: Path, dictionary: Set[str], dry_run: bool = False) -> Tuple[int, List[dict]]:
    """
    Fix hyphenation in a single PAGE XML file.

    Returns:
        Tuple of (number of fixes made, list of fix details)
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    fixes_made = 0
    fix_details = []

    # Find all TextRegion elements
    for text_region in root.findall('.//page:TextRegion', NS):
        text_lines = text_region.findall('.//page:TextLine', NS)

        # Process consecutive pairs of lines
        for i in range(len(text_lines) - 1):
            current_line = text_lines[i]
            next_line = text_lines[i + 1]

            current_unicode = current_line.find('.//page:Unicode', NS)
            next_unicode = next_line.find('.//page:Unicode', NS)

            if current_unicode is None or next_unicode is None:
                continue

            current_text = current_unicode.text or ''
            next_text = next_unicode.text or ''

            # Case 1: Hyphenated split (e.g., "Im- porter" or "Im-" + "porter")
            if match := re.search(r'(\S+)-\s*$', current_text):
                word_fragment = match.group(1)

                if next_match := re.match(r'^(\S+)', next_text):
                    continuation = next_match.group(1)
                    merged_word = word_fragment + continuation

                    # Validate with dictionary
                    if is_valid_word(merged_word, dictionary):
                        new_current = re.sub(r'(\S+)-\s*$', merged_word, current_text)
                        new_next = re.sub(r'^\S+\s*', '', next_text, count=1)

                        if not dry_run:
                            current_unicode.text = new_current
                            next_unicode.text = new_next

                        fixes_made += 1
                        fix_details.append({
                            'type': 'hyphenated',
                            'original': f"{word_fragment}- {continuation}",
                            'merged': merged_word,
                            'line1': current_text[:50] + '...' if len(current_text) > 50 else current_text,
                            'line2': next_text[:50] + '...' if len(next_text) > 50 else next_text
                        })
                        continue

            # Case 2: Non-hyphenated split (e.g., "sur prise")
            # Only check if last word of current line + first word of next line forms valid word
            if match := re.search(r'(\S+)\s*$', current_text):
                word_fragment = match.group(1)

                # Skip if it already looks like a complete word (heuristic: > 3 chars and common ending)
                if len(word_fragment) > 3 and not word_fragment.endswith(('ing', 'ed', 'er', 'ly', 'tion')):
                    if next_match := re.match(r'^(\S+)', next_text):
                        continuation = next_match.group(1)
                        merged_word = word_fragment + continuation

                        # Only merge if:
                        # 1. The merged word is valid
                        # 2. The continuation is NOT a valid word by itself (or is very short)
                        # 3. The fragment is likely incomplete (short or doesn't look complete)
                        if (is_valid_word(merged_word, dictionary) and
                            (len(continuation) < 4 or not is_valid_word(continuation, dictionary)) and
                            len(word_fragment) < 8):

                            new_current = re.sub(r'(\S+)\s*$', merged_word, current_text)
                            new_next = re.sub(r'^\S+\s*', '', next_text, count=1)

                            if not dry_run:
                                current_unicode.text = new_current
                                next_unicode.text = new_next

                            fixes_made += 1
                            fix_details.append({
                                'type': 'non-hyphenated',
                                'original': f"{word_fragment} {continuation}",
                                'merged': merged_word,
                                'line1': current_text[:50] + '...' if len(current_text) > 50 else current_text,
                                'line2': next_text[:50] + '...' if len(next_text) > 50 else next_text
                            })

    # Save the modified XML
    if fixes_made > 0 and not dry_run:
        try:
            tree.write(str(xml_path), encoding='UTF-8', xml_declaration=True, method='xml')
        except Exception as e:
            print(f"WARNING: Failed to save {xml_path}: {e}")
            # Try alternative method
            xml_string = ET.tostring(root, encoding='unicode')
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
                f.write(xml_string)

    return fixes_made, fix_details


def main():
    parser = argparse.ArgumentParser(description='Fix hyphenation in PAGE XML files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--verbose', action='store_true', help='Show detailed information for each fix')
    parser.add_argument('--limit', type=int, help='Limit number of files to process (for testing)')
    args = parser.parse_args()

    print("Loading dictionary...")
    dictionary = load_dictionary()
    print()

    current_dir = Path('.')
    xml_files = list(current_dir.glob('*.xml'))

    if args.limit:
        xml_files = xml_files[:args.limit]

    print(f"Found {len(xml_files)} XML files")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
    print("=" * 80)

    total_fixes = 0
    files_with_fixes = 0
    all_fix_details = []

    for xml_file in xml_files:
        try:
            fixes, details = fix_hyphenation_in_file(xml_file, dictionary, args.dry_run)
            if fixes > 0:
                files_with_fixes += 1
                total_fixes += fixes
                all_fix_details.extend(details)

                print(f"\n{xml_file.name}")
                print(f"  Fixes: {fixes}")

                if args.verbose and details:
                    for detail in details[:5]:  # Show first 5
                        print(f"    [{detail['type']}] {detail['original']} -> {detail['merged']}")
                    if len(details) > 5:
                        print(f"    ... and {len(details) - 5} more")

        except Exception as e:
            print(f"\nError processing {xml_file.name}: {e}")

    print("\n" + "=" * 80)
    print(f"Summary:")
    print(f"  Files processed: {len(xml_files)}")
    print(f"  Files with fixes: {files_with_fixes}")
    print(f"  Total fixes: {total_fixes}")

    if all_fix_details:
        hyphenated = sum(1 for d in all_fix_details if d['type'] == 'hyphenated')
        non_hyphenated = sum(1 for d in all_fix_details if d['type'] == 'non-hyphenated')
        print(f"    - Hyphenated: {hyphenated}")
        print(f"    - Non-hyphenated: {non_hyphenated}")

    if args.dry_run:
        print("\nThis was a dry run. Use without --dry-run to apply changes.")


if __name__ == '__main__':
    main()
