#!/usr/bin/env python3
"""
OCR Evaluation Tool - Calculate Character Error Rate (CER) and Word Error Rate (WER)
Compares OCR output from EasyOCR, Tesseract, and Transkribus against gold standard transcriptions.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import csv
from dataclasses import dataclass
import numpy as np
import argparse
from collections import defaultdict
from datetime import datetime
try:
    from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
    from nltk.corpus import words as nltk_words
    import nltk
    BLEU_AVAILABLE = True
    NLTK_AVAILABLE = True

    # Download words corpus if not already present
    try:
        nltk_words.words()
    except LookupError:
        print("[INFO] Downloading NLTK words corpus...")
        nltk.download('words', quiet=True)

except ImportError:
    BLEU_AVAILABLE = False
    NLTK_AVAILABLE = False
    print("[WARNING] NLTK not available. BLEU scores and hallucination detection will not be calculated.")


# Stop word list for significant word filtering (based on research article)
# Common function words excluded from "significant word" accuracy calculation
STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but',
    'by', 'can', 'cannot', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each',
    'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here',
    'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it',
    'its', 'itself', 'just', 'me', 'might', 'more', 'most', 'must', 'my', 'myself', 'no',
    'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours',
    'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than',
    'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they',
    'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we',
    'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with',
    'would', 'you', 'your', 'yours', 'yourself', 'yourselves',
    # Additional common words often excluded
    'also', 'though', 'although', 'however', 'therefore', 'thus', 'hence', 'yet', 'still',
    'may', 'shall', 'ought', 'need', 'dare', 'used', 'say', 'said', 'says', 'saying',
    'one', 'two', 'three', 'first', 'second', 'third', 'another', 'every', 'much', 'many'
}


def calculate_bleu_score(reference: str, hypothesis: str) -> float:
    """
    Calculate BLEU score between reference and hypothesis text.
    BLEU measures n-gram overlap and is useful for semantic similarity.

    Args:
        reference: Gold standard text
        hypothesis: OCR output text

    Returns:
        BLEU score (0.0-1.0), or 0.0 if NLTK not available
    """
    if not BLEU_AVAILABLE:
        return 0.0

    # Tokenize into words
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if not ref_words or not hyp_words:
        return 0.0

    # Use smoothing to handle zero counts (Method 1: add epsilon)
    smoothing = SmoothingFunction().method1

    try:
        # Calculate sentence-level BLEU with up to 4-grams
        score = sentence_bleu([ref_words], hyp_words, smoothing_function=smoothing)
        return score
    except Exception as e:
        print(f"[WARNING] BLEU calculation failed: {e}")
        return 0.0


# Global variable to cache the English word set for performance
_ENGLISH_WORDS_CACHE = None


def get_english_words() -> set:
    """
    Get set of valid English words from NLTK corpus (cached for performance).

    Returns:
        Set of lowercase English words
    """
    global _ENGLISH_WORDS_CACHE

    if _ENGLISH_WORDS_CACHE is None:
        if NLTK_AVAILABLE:
            # NLTK words corpus contains ~236k English words
            _ENGLISH_WORDS_CACHE = set(w.lower() for w in nltk_words.words())
        else:
            _ENGLISH_WORDS_CACHE = set()

    return _ENGLISH_WORDS_CACHE


def calculate_hallucination_rate(reference: str, hypothesis: str) -> Tuple[float, int, int]:
    """
    Calculate hallucination rate: percentage of OCR words that are real English words
    but do not appear anywhere in the reference text.

    This detects cases where the language model "guessed" plausible words instead of
    transcribing the actual text. High hallucination rates indicate the OCR system
    is making up content rather than accurately reading characters.

    Args:
        reference: Gold standard text (normalized to lowercase)
        hypothesis: OCR output text (normalized to lowercase)

    Returns:
        Tuple of (hallucination_rate, total_hallucinated_words, unique_hallucinated_words)
        - hallucination_rate: Proportion of hypothesis words that are hallucinations (0.0-1.0)
        - total_hallucinated_words: Total count of hallucinated word tokens
        - unique_hallucinated_words: Count of unique hallucinated word types

    Examples:
        Reference: "the quick brown fox"
        Hypothesis: "the swift brown fox"
        - "swift" is a real English word not in reference -> hallucination

        Reference: "hello world"
        Hypothesis: "hel1o w0rld"
        - "hel1o" and "w0rld" are NOT real words -> NOT hallucinations (just OCR errors)
    """
    if not NLTK_AVAILABLE:
        return 0.0, 0, 0

    # Tokenize into words
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    if not hyp_words:
        return 0.0, 0, 0

    # Create set of reference words for fast lookup
    ref_word_set = set(ref_words)

    # Get English dictionary
    english_words = get_english_words()

    # Find words in hypothesis that:
    # 1. Do NOT appear in reference text
    # 2. ARE valid English words (hallucinations)
    hallucinated_words = []

    for word in hyp_words:
        # Skip if word is in reference (not a hallucination)
        if word in ref_word_set:
            continue

        # Remove punctuation for dictionary check
        word_cleaned = ''.join(c for c in word if c.isalnum())

        # Check if it's a real English word
        # We check both the word itself and cleaned version
        if word_cleaned and (word.lower() in english_words or word_cleaned.lower() in english_words):
            hallucinated_words.append(word)

    total_hallucinated = len(hallucinated_words)
    unique_hallucinated = len(set(hallucinated_words))

    # Calculate rate as proportion of all hypothesis words
    hallucination_rate = total_hallucinated / len(hyp_words) if hyp_words else 0.0

    return hallucination_rate, total_hallucinated, unique_hallucinated


def extract_document_year(filename: str) -> Optional[int]:
    """
    Extract year from filename following format: 'Author - YYYY - Title.xml'
    Example: 'Anonymous - 1675 - Every woman her own midwife.xml'

    Args:
        filename: Document filename

    Returns:
        Year as integer, or None if not found or invalid
    """
    # Pattern to match "- YYYY -" where YYYY is a 4-digit year
    match = re.search(r'- (\d{4}) -', filename)

    if match:
        year = int(match.group(1))
        # Validate reasonable range for historical documents (1600-1900)
        if 1600 <= year <= 1900:
            return year
        else:
            # If year is outside expected range, still return it but warn
            if year < 1600 or year > 2100:
                print(f"[WARNING] Year {year} from {filename} is outside expected range")
            return year

    return None


def get_age_group(year: Optional[int]) -> Optional[str]:
    """
    Group year into 25-year period.
    Examples: 1675 → "1650-1674", 1700 → "1700-1724"

    Args:
        year: Document year

    Returns:
        Age group string (e.g., "1650-1674"), or None if year is None
    """
    if year is None:
        return None

    # Calculate start of 25-year period
    group_start = (year // 25) * 25
    group_end = group_start + 24

    return f"{group_start}-{group_end}"


@dataclass
class EvaluationResult:
    """Store evaluation results for a single document"""
    filename: str
    ocr_system: str
    cer: float
    wer: float
    char_insertions: int
    char_deletions: int
    char_substitutions: int
    word_insertions: int
    word_deletions: int
    word_substitutions: int
    total_chars: int
    total_words: int
    # New metrics from article
    significant_word_accuracy: float
    total_significant_words: int
    significant_word_errors: int
    capitalized_word_accuracy: float
    total_capitalized_words: int
    capitalized_word_errors: int
    number_group_accuracy: float
    total_number_groups: int
    number_group_errors: int
    # BLEU score and document age
    bleu_score: float
    document_year: Optional[int]
    age_group: Optional[str]
    # Hallucination detection metrics
    hallucination_rate: float
    total_hallucinated_words: int
    unique_hallucinated_words: int


def levenshtein_distance_detailed(s1: str, s2: str) -> Tuple[int, int, int, int]:
    """
    Calculate Levenshtein distance with detailed counts of operations.

    Args:
        s1: Reference string (gold standard)
        s2: Hypothesis string (OCR output)

    Returns:
        Tuple of (total_distance, insertions, deletions, substitutions)
    """
    len1, len2 = len(s1), len(s2)

    # Create DP table
    dp = np.zeros((len1 + 1, len2 + 1), dtype=int)

    # Initialize base cases
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    # Fill DP table
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(
                    dp[i-1][j],    # deletion
                    dp[i][j-1],    # insertion
                    dp[i-1][j-1]   # substitution
                )

    # Backtrack to count operations
    insertions = 0
    deletions = 0
    substitutions = 0

    i, j = len1, len2
    while i > 0 or j > 0:
        if i == 0:
            insertions += j
            break
        elif j == 0:
            deletions += i
            break
        elif s1[i-1] == s2[j-1]:
            i -= 1
            j -= 1
        else:
            current = dp[i][j]
            if current == dp[i-1][j-1] + 1:  # substitution
                substitutions += 1
                i -= 1
                j -= 1
            elif current == dp[i-1][j] + 1:  # deletion
                deletions += 1
                i -= 1
            else:  # insertion
                insertions += 1
                j -= 1

    total_distance = dp[len1][len2]
    return total_distance, insertions, deletions, substitutions


def calculate_cer(reference: str, hypothesis: str) -> Tuple[float, int, int, int, int]:
    """
    Calculate Character Error Rate (CER).

    CER = (S + D + I) / N
    where S = substitutions, D = deletions, I = insertions, N = total characters in reference

    Args:
        reference: Gold standard text
        hypothesis: OCR output text

    Returns:
        Tuple of (cer, insertions, deletions, substitutions, total_chars)
    """
    distance, insertions, deletions, substitutions = levenshtein_distance_detailed(
        reference, hypothesis
    )

    total_chars = len(reference)

    if total_chars == 0:
        return 0.0, insertions, deletions, substitutions, total_chars

    cer = distance / total_chars
    return cer, insertions, deletions, substitutions, total_chars


def calculate_wer(reference: str, hypothesis: str) -> Tuple[float, int, int, int, int]:
    """
    Calculate Word Error Rate (WER).

    WER = (S + D + I) / N
    where S = substitutions, D = deletions, I = insertions, N = total words in reference

    Args:
        reference: Gold standard text
        hypothesis: OCR output text

    Returns:
        Tuple of (wer, insertions, deletions, substitutions, total_words)
    """
    # Tokenize into words
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    distance, insertions, deletions, substitutions = levenshtein_distance_detailed(
        ref_words, hyp_words
    )

    total_words = len(ref_words)

    if total_words == 0:
        return 0.0, insertions, deletions, substitutions, total_words

    wer = distance / total_words
    return wer, insertions, deletions, substitutions, total_words


def calculate_significant_word_accuracy(reference: str, hypothesis: str) -> Tuple[float, int, int]:
    """
    Calculate accuracy for significant words (content words excluding stop words).

    Based on research article: "The number of occurrences of content words for which users
    might be interested in searching, excluding stop-listed words."

    Args:
        reference: Gold standard text (normalized to lowercase)
        hypothesis: OCR output text (normalized to lowercase)

    Returns:
        Tuple of (accuracy, total_significant_words, errors)
    """
    # Tokenize into words
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    # Filter out stop words and punctuation-only tokens
    ref_significant = [w for w in ref_words if w not in STOP_WORDS and any(c.isalnum() for c in w)]
    hyp_significant = [w for w in hyp_words if w not in STOP_WORDS and any(c.isalnum() for c in w)]

    # Calculate distance for significant words only
    if not ref_significant:
        return 1.0, 0, 0

    distance, _, _, _ = levenshtein_distance_detailed(ref_significant, hyp_significant)
    total_significant = len(ref_significant)

    accuracy = 1.0 - (distance / total_significant) if total_significant > 0 else 1.0

    return accuracy, total_significant, distance


def calculate_capitalized_word_accuracy(reference_original: str, hypothesis_original: str) -> Tuple[float, int, int]:
    """
    Calculate accuracy for words starting with capital letters (proper nouns, named entities).

    Based on research article: "Significant word occurrences that have a capital letter start
    (i.e., proper nouns)."

    Note: This function works on ORIGINAL (non-normalized) text to preserve capitalization.

    Args:
        reference_original: Gold standard text (original case)
        hypothesis_original: OCR output text (original case)

    Returns:
        Tuple of (accuracy, total_capitalized_words, errors)
    """
    # Tokenize into words (preserving case)
    ref_words = reference_original.split()
    hyp_words = hypothesis_original.split()

    # Extract capitalized words (starting with uppercase letter)
    # Filter out stop words even if capitalized (e.g., "The" at start of sentence)
    ref_capitalized = [w for w in ref_words if w and w[0].isupper() and w.lower() not in STOP_WORDS]

    # For hypothesis, we need to match positions or use normalized comparison
    # We'll normalize to lowercase for comparison
    ref_cap_lower = [w.lower() for w in ref_capitalized]
    hyp_cap_lower = []

    # Extract capitalized words from hypothesis at same positions or by matching
    for word in hyp_words:
        if word and word[0].isupper() and word.lower() not in STOP_WORDS:
            hyp_cap_lower.append(word.lower())

    if not ref_capitalized:
        return 1.0, 0, 0

    # Calculate distance for capitalized words
    distance, _, _, _ = levenshtein_distance_detailed(ref_cap_lower, hyp_cap_lower)
    total_capitalized = len(ref_capitalized)

    accuracy = 1.0 - (distance / total_capitalized) if total_capitalized > 0 else 1.0

    return accuracy, total_capitalized, distance


def calculate_number_group_accuracy(reference: str, hypothesis: str) -> Tuple[float, int, int]:
    """
    Calculate accuracy for number groups.

    Based on research article: "The number of occurrences of a number group" where groups
    contain "at least one number and may include" currency symbols ($, £, €), slashes,
    commas, periods, and percentage signs.

    Args:
        reference: Gold standard text
        hypothesis: OCR output text

    Returns:
        Tuple of (accuracy, total_number_groups, errors)
    """
    # Pattern to match number groups:
    # - Must contain at least one digit
    # - May include: currency symbols, commas, periods, slashes, percentage signs, hyphens
    # - Examples: "$1,234.56", "12/31/2023", "45.6%", "£100", "1-800-555-0123"
    number_group_pattern = r'[$£€]?\d+(?:[.,/\-:]\d+)*[%]?|[$£€]\d+'

    # Extract number groups from reference and hypothesis
    ref_numbers = re.findall(number_group_pattern, reference)
    hyp_numbers = re.findall(number_group_pattern, hypothesis)

    if not ref_numbers:
        return 1.0, 0, 0

    # Calculate distance for number groups
    distance, _, _, _ = levenshtein_distance_detailed(ref_numbers, hyp_numbers)
    total_numbers = len(ref_numbers)

    accuracy = 1.0 - (distance / total_numbers) if total_numbers > 0 else 1.0

    return accuracy, total_numbers, distance


def extract_text_from_hocr_xml(xml_path: str, verbose: bool = False) -> str:
    """
    Extract text content from hOCR (HTML-based OCR) format.

    Args:
        xml_path: Path to the hOCR XML file
        verbose: If True, print detailed extraction information

    Returns:
        Extracted text content
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        if verbose:
            print(f"    XML format: hOCR (HTML-based OCR)")

        # Define XHTML namespace
        ns = {'xhtml': 'http://www.w3.org/1999/xhtml'}

        # Extract all text from span elements (where OCR text is stored)
        text_parts = []

        # Look for elements with OCR classes (ocr_line, ocrx_word, etc.)
        for elem in root.findall('.//xhtml:span', ns):
            if elem.text and elem.text.strip():
                text_parts.append(elem.text.strip())

        # Join with spaces
        result = ' '.join(text_parts)

        if verbose:
            print(f"    Extracted {len(text_parts)} text elements, {len(result)} characters total")
            if result:
                print(f"    First 100 chars: {result[:100]}...")

        return result

    except Exception as e:
        print(f"Error parsing hOCR XML {xml_path}: {e}")
        return ""


def detect_and_extract_xml(xml_path: str, verbose: bool = False) -> str:
    """
    Detect XML format and extract text using the appropriate method.
    Falls back to plain text reading if XML parsing fails.

    Args:
        xml_path: Path to the XML file
        verbose: If True, print detailed extraction information

    Returns:
        Extracted text content
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Detect format based on root tag
        if 'html' in root.tag.lower():
            # hOCR format (XHTML)
            return extract_text_from_hocr_xml(xml_path, verbose)
        elif 'PcGts' in root.tag or 'PAGE' in root.tag:
            # Transkribus PAGE XML format
            return extract_text_from_transkribus_xml(xml_path, verbose)
        else:
            if verbose:
                print(f"    [WARNING] Unknown XML format, root tag: {root.tag}")
                print(f"    Attempting generic text extraction...")
            # Fall back to generic extraction
            return extract_text_from_transkribus_xml(xml_path, verbose)

    except ET.ParseError as e:
        # XML parsing failed - file might be plain text with .xml extension
        if verbose:
            print(f"    [WARNING] XML parsing failed: {e}")
            print(f"    Attempting to read as plain text file...")
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if verbose:
                print(f"    Successfully read as plain text, {len(content)} characters")
                if content:
                    print(f"    First 100 chars: {content[:100]}...")
            return content
        except Exception as text_error:
            print(f"Error reading {xml_path} as plain text: {text_error}")
            return ""
    except Exception as e:
        print(f"Error detecting XML format {xml_path}: {e}")
        return ""


def extract_text_from_transkribus_xml(xml_path: str, verbose: bool = False) -> str:
    """
    Extract text content from Transkribus PAGE XML format.

    Args:
        xml_path: Path to the XML file
        verbose: If True, print detailed extraction information

    Returns:
        Extracted text content
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        if verbose:
            print(f"    XML format: Transkribus PAGE XML")
            print(f"    XML root tag: {root.tag}")

        # Define namespace
        ns = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}

        # Extract all Unicode text elements in reading order
        text_lines = []

        # Get all TextLine elements
        for textline in root.findall('.//page:TextLine', ns):
            # Get Unicode element within TextEquiv
            unicode_elem = textline.find('.//page:Unicode', ns)
            if unicode_elem is not None and unicode_elem.text:
                text_lines.append(unicode_elem.text)

        if verbose and len(text_lines) == 0:
            print(f"    [WARNING] No text found using Transkribus PAGE XML format")
            print(f"    Trying to find any text elements...")
            # Try to find any text in the XML
            all_text = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    all_text.append(f"{elem.tag}: {elem.text[:50]}...")
            if all_text:
                print(f"    Found {len(all_text)} elements with text:")
                for t in all_text[:5]:  # Show first 5
                    print(f"      {t}")

        # Join with spaces to form complete text
        result = ' '.join(text_lines)

        if verbose:
            print(f"    Extracted {len(text_lines)} text lines, {len(result)} characters total")
            if result:
                print(f"    First 100 chars: {result[:100]}...")

        return result

    except Exception as e:
        print(f"Error parsing XML {xml_path}: {e}")
        return ""


def extract_text_from_markdown(md_path: str, strip_headers: bool = False) -> str:
    """
    Extract text content from markdown file.
    Optionally removes markdown headers.

    Args:
        md_path: Path to the markdown file
        strip_headers: If True, remove all lines starting with # (markdown headers)

    Returns:
        Extracted text content
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        if strip_headers:
            # Remove ALL lines starting with # (any markdown header level)
            lines = [line for line in lines if not line.strip().startswith('#')]

        # Join and clean up
        text = '\n'.join(lines).strip()

        # Remove extra whitespace but preserve line breaks
        text = re.sub(r' +', ' ', text)

        return text

    except Exception as e:
        print(f"Error reading markdown {md_path}: {e}")
        return ""


def extract_text_from_gold_md(md_path: str) -> str:
    """
    Extract text from a gold standard markdown file, stripping YAML frontmatter.

    Gold standard .md files may begin with a YAML frontmatter block delimited by
    '---' lines (e.g. primary_language, is_rotation_valid, etc.).  Everything
    inside that block is metadata and should be excluded from the text comparison.

    Args:
        md_path: Path to the gold standard markdown file

    Returns:
        Text content with YAML frontmatter removed
    """
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        # Strip YAML frontmatter: if the file starts with '---', skip until
        # the closing '---' line.
        if lines and lines[0].strip() == '---':
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i].strip() == '---':
                    end_idx = i
                    break
            if end_idx is not None:
                lines = lines[end_idx + 1:]

        text = '\n'.join(lines).strip()
        text = re.sub(r' +', ' ', text)
        return text

    except Exception as e:
        print(f"Error reading gold standard markdown {md_path}: {e}")
        return ""


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    - Convert to lowercase
    - Normalize whitespace
    - Remove extra spaces

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower()

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def get_matching_filename(ocr_filename: str, gold_standard_files: List[str], threshold: float = 0.6, gold_format: str = 'xml') -> Tuple[str, float]:
    """
    Find the matching gold standard file for an OCR output file using fuzzy matching.

    Args:
        ocr_filename: Filename from OCR output (e.g., "file_page_001.md" or "file.xml")
        gold_standard_files: List of gold standard filenames
        threshold: Minimum similarity score (0.0-1.0) to accept a match
        gold_format: Extension of gold standard files, either 'xml' or 'md'

    Returns:
        Tuple of (matching gold standard filename or None, similarity score)
    """
    gold_ext = f'.{gold_format}'

    # Try different patterns to extract base name
    base_name = ocr_filename

    # Remove common OCR suffixes and extensions
    patterns = [
        '_page_001.md',
        '_page_001.xml',
        '_page_001',
        '.md',
        '.xml'
    ]

    for pattern in patterns:
        if base_name.endswith(pattern):
            base_name = base_name.replace(pattern, '')
            break

    # First try exact match with the gold standard extension
    exact_match = base_name + gold_ext
    if exact_match in gold_standard_files:
        return exact_match, 1.0

    # Try fuzzy matching based on shared prefix and similarity
    best_match = None
    best_score = 0.0

    for gs_file in gold_standard_files:
        if not gs_file.endswith(gold_ext):
            continue

        gs_base = gs_file.replace(gold_ext, '')

        # Calculate similarity score
        # 1. Check if one is a prefix of the other
        if gs_base.startswith(base_name) or base_name.startswith(gs_base):
            # Calculate what percentage of the shorter name matches
            shorter_len = min(len(base_name), len(gs_base))
            longer_len = max(len(base_name), len(gs_base))
            score = shorter_len / longer_len
        else:
            # Calculate longest common prefix
            common_prefix_len = 0
            for i in range(min(len(base_name), len(gs_base))):
                if base_name[i].lower() == gs_base[i].lower():
                    common_prefix_len += 1
                else:
                    break

            # Score based on common prefix length relative to the shorter filename
            shorter_len = min(len(base_name), len(gs_base))
            if shorter_len > 0:
                score = common_prefix_len / shorter_len
            else:
                score = 0.0

        # Update best match if this is better
        if score > best_score:
            best_score = score
            best_match = gs_file

    # Return match if score is above threshold
    if best_score >= threshold:
        return best_match, best_score

    return None, 0.0


def evaluate_ocr_system(
    ocr_dir: str,
    gold_standard_dir: str,
    ocr_system_name: str,
    similarity_threshold: float = 0.6,
    verbose: bool = False,
    strip_markdown_headers: bool = False,
    gold_format: str = 'xml'
) -> List[EvaluationResult]:
    """
    Evaluate all files from one OCR system against gold standard.

    Args:
        ocr_dir: Directory containing OCR output files (XML or markdown)
        gold_standard_dir: Directory containing gold standard files
        ocr_system_name: Name of the OCR system (e.g., "EasyOCR", "Tesseract")
        similarity_threshold: Minimum similarity score for filename matching
        verbose: Enable verbose output for debugging
        strip_markdown_headers: If True, remove all lines starting with # from markdown files
        gold_format: Format of gold standard files, either 'xml' or 'md'

    Returns:
        List of EvaluationResult objects
    """
    results = []

    # Get list of gold standard files
    gold_standard_path = Path(gold_standard_dir)
    gold_ext = f'.{gold_format}'
    gold_standard_files = [f.name for f in gold_standard_path.iterdir() if f.suffix == gold_ext]

    # Get list of OCR output files (check for both .xml and .md)
    ocr_path = Path(ocr_dir)
    ocr_files_md = sorted([f for f in ocr_path.iterdir() if f.suffix == '.md'])
    ocr_files_xml = sorted([f for f in ocr_path.iterdir() if f.suffix == '.xml'])

    # Use whichever format is found
    if ocr_files_xml:
        ocr_files = ocr_files_xml
        file_format = 'xml'
    elif ocr_files_md:
        ocr_files = ocr_files_md
        file_format = 'md'
    else:
        print(f"  [ERROR] No .xml or .md files found in {ocr_dir}")
        return results

    print(f"\nEvaluating {ocr_system_name}...")
    print(f"Found {len(ocr_files)} OCR output files (.{file_format} format)")
    if strip_markdown_headers and file_format == 'md':
        print(f"  [INFO] Markdown headers (lines starting with #) will be stripped")

    unmatched_files = []
    first_file = True  # Track first file for verbose output

    for ocr_file in ocr_files:
        # Find matching gold standard file
        gs_filename, similarity = get_matching_filename(ocr_file.name, gold_standard_files, similarity_threshold, gold_format)

        if gs_filename is None:
            # Find closest matches for diagnostic purposes
            closest_matches = []
            ocr_base = ocr_file.name.replace('_page_001.md', '').replace('_page_001.xml', '').replace('.md', '').replace('.xml', '')

            for gs_file in gold_standard_files[:10]:  # Check up to 10 files
                gs_base = gs_file.replace('.xml', '')
                # Calculate prefix similarity
                common_len = 0
                for i in range(min(len(ocr_base), len(gs_base))):
                    if ocr_base[i].lower() == gs_base[i].lower():
                        common_len += 1
                    else:
                        break
                if common_len > 3:  # At least 4 characters in common
                    closest_matches.append((gs_file, common_len))

            closest_matches.sort(key=lambda x: x[1], reverse=True)

            warning_msg = f"  [WARNING] No gold standard found for {ocr_file.name}"
            if closest_matches:
                warning_msg += f" (closest: {closest_matches[0][0]})"
            print(warning_msg)
            unmatched_files.append(ocr_file.name)
            continue

        gs_file = gold_standard_path / gs_filename

        # Show match confidence if not exact match
        if similarity < 1.0:
            print(f"  [MATCHED] {ocr_file.name} -> {gs_filename} (similarity: {similarity:.1%})")

        # Enable verbose output for first file if requested
        show_verbose = verbose and first_file
        if show_verbose:
            print(f"\n  [VERBOSE] Extracting text from first file: {ocr_file.name}")

        # Extract text based on file format
        if file_format == 'xml':
            ocr_text = detect_and_extract_xml(str(ocr_file), verbose=show_verbose)
        else:
            ocr_text = extract_text_from_markdown(str(ocr_file), strip_headers=strip_markdown_headers)

        if show_verbose:
            print(f"  [VERBOSE] Extracting text from gold standard: {gs_filename}")

        if gold_format == 'md':
            gold_text = extract_text_from_gold_md(str(gs_file))
        else:
            gold_text = detect_and_extract_xml(str(gs_file), verbose=show_verbose)

        first_file = False  # Only show verbose for first file

        # Check if extraction succeeded
        if not ocr_text or not ocr_text.strip():
            print(f"  [ERROR] No text extracted from {ocr_file.name} - file may be empty or wrong format")
            continue

        if not gold_text or not gold_text.strip():
            print(f"  [ERROR] No text extracted from gold standard {gs_filename}")
            continue

        # Normalize text
        ocr_text_norm = normalize_text(ocr_text)
        gold_text_norm = normalize_text(gold_text)

        # Additional check after normalization
        if not ocr_text_norm:
            print(f"  [ERROR] {ocr_file.name} is empty after normalization")
            continue

        if not gold_text_norm:
            print(f"  [ERROR] Gold standard {gs_filename} is empty after normalization")
            continue

        # Calculate metrics
        cer, c_ins, c_del, c_sub, total_chars = calculate_cer(gold_text_norm, ocr_text_norm)
        wer, w_ins, w_del, w_sub, total_words = calculate_wer(gold_text_norm, ocr_text_norm)

        # Calculate new word-based accuracy metrics from research article
        sig_word_acc, total_sig_words, sig_word_errors = calculate_significant_word_accuracy(
            gold_text_norm, ocr_text_norm
        )
        cap_word_acc, total_cap_words, cap_word_errors = calculate_capitalized_word_accuracy(
            gold_text, ocr_text  # Use original text to preserve capitalization
        )
        num_group_acc, total_num_groups, num_group_errors = calculate_number_group_accuracy(
            gold_text_norm, ocr_text_norm
        )

        # Calculate BLEU score
        bleu = calculate_bleu_score(gold_text_norm, ocr_text_norm)

        # Calculate hallucination rate
        halluc_rate, total_halluc, unique_halluc = calculate_hallucination_rate(
            gold_text_norm, ocr_text_norm
        )

        # Extract document year from gold standard filename
        doc_year = extract_document_year(gs_filename)
        doc_age_group = get_age_group(doc_year)

        result = EvaluationResult(
            filename=ocr_file.name,
            ocr_system=ocr_system_name,
            cer=cer,
            wer=wer,
            char_insertions=c_ins,
            char_deletions=c_del,
            char_substitutions=c_sub,
            word_insertions=w_ins,
            word_deletions=w_del,
            word_substitutions=w_sub,
            total_chars=total_chars,
            total_words=total_words,
            significant_word_accuracy=sig_word_acc,
            total_significant_words=total_sig_words,
            significant_word_errors=sig_word_errors,
            capitalized_word_accuracy=cap_word_acc,
            total_capitalized_words=total_cap_words,
            capitalized_word_errors=cap_word_errors,
            number_group_accuracy=num_group_acc,
            total_number_groups=total_num_groups,
            number_group_errors=num_group_errors,
            bleu_score=bleu,
            document_year=doc_year,
            age_group=doc_age_group,
            hallucination_rate=halluc_rate,
            total_hallucinated_words=total_halluc,
            unique_hallucinated_words=unique_halluc
        )

        results.append(result)

        print(f"  [OK] {ocr_file.name}: CER={cer:.4f}, WER={wer:.4f}")

    # Print summary of matching
    print(f"\n  Summary: {len(results)}/{len(ocr_files)} files successfully matched and evaluated")
    if unmatched_files:
        print(f"  Unmatched files: {len(unmatched_files)}")
        if len(unmatched_files) <= 5:
            for uf in unmatched_files:
                print(f"    - {uf}")
        else:
            print(f"    (showing first 5 of {len(unmatched_files)})")
            for uf in unmatched_files[:5]:
                print(f"    - {uf}")

    return results


def generate_summary_statistics(results: List[EvaluationResult]) -> Dict:
    """
    Generate summary statistics for evaluation results.

    Args:
        results: List of EvaluationResult objects

    Returns:
        Dictionary containing summary statistics
    """
    if not results:
        return {}

    cers = [r.cer for r in results]
    wers = [r.wer for r in results]

    # Calculate total errors by type
    total_char_ins = sum(r.char_insertions for r in results)
    total_char_del = sum(r.char_deletions for r in results)
    total_char_sub = sum(r.char_substitutions for r in results)
    total_char_errors = total_char_ins + total_char_del + total_char_sub

    total_word_ins = sum(r.word_insertions for r in results)
    total_word_del = sum(r.word_deletions for r in results)
    total_word_sub = sum(r.word_substitutions for r in results)
    total_word_errors = total_word_ins + total_word_del + total_word_sub

    total_chars = sum(r.total_chars for r in results)
    total_words = sum(r.total_words for r in results)

    # Calculate accuracy (inverse of error rate)
    mean_char_accuracy = 1 - np.mean(cers)
    mean_word_accuracy = 1 - np.mean(wers)

    # Calculate error type percentages
    char_ins_pct = (total_char_ins / total_char_errors * 100) if total_char_errors > 0 else 0
    char_del_pct = (total_char_del / total_char_errors * 100) if total_char_errors > 0 else 0
    char_sub_pct = (total_char_sub / total_char_errors * 100) if total_char_errors > 0 else 0

    word_ins_pct = (total_word_ins / total_word_errors * 100) if total_word_errors > 0 else 0
    word_del_pct = (total_word_del / total_word_errors * 100) if total_word_errors > 0 else 0
    word_sub_pct = (total_word_sub / total_word_errors * 100) if total_word_errors > 0 else 0

    # Calculate new word-based accuracy metrics
    sig_word_accs = [r.significant_word_accuracy for r in results]
    cap_word_accs = [r.capitalized_word_accuracy for r in results]
    num_group_accs = [r.number_group_accuracy for r in results]

    total_sig_words = sum(r.total_significant_words for r in results)
    total_cap_words = sum(r.total_capitalized_words for r in results)
    total_num_groups = sum(r.total_number_groups for r in results)

    total_sig_word_errors = sum(r.significant_word_errors for r in results)
    total_cap_word_errors = sum(r.capitalized_word_errors for r in results)
    total_num_group_errors = sum(r.number_group_errors for r in results)

    # Calculate BLEU statistics
    bleu_scores = [r.bleu_score for r in results]

    # Calculate hallucination statistics
    halluc_rates = [r.hallucination_rate for r in results]
    total_hallucinated = sum(r.total_hallucinated_words for r in results)
    total_unique_hallucinated = sum(r.unique_hallucinated_words for r in results)

    return {
        'ocr_system': results[0].ocr_system,
        'num_documents': len(results),
        'mean_cer': np.mean(cers),
        'median_cer': np.median(cers),
        'std_cer': np.std(cers),
        'min_cer': np.min(cers),
        'max_cer': np.max(cers),
        'mean_wer': np.mean(wers),
        'median_wer': np.median(wers),
        'std_wer': np.std(wers),
        'min_wer': np.min(wers),
        'max_wer': np.max(wers),
        'mean_char_accuracy': mean_char_accuracy,
        'mean_word_accuracy': mean_word_accuracy,
        'total_chars': total_chars,
        'total_words': total_words,
        'total_char_errors': total_char_errors,
        'total_word_errors': total_word_errors,
        'total_char_insertions': total_char_ins,
        'total_char_deletions': total_char_del,
        'total_char_substitutions': total_char_sub,
        'total_word_insertions': total_word_ins,
        'total_word_deletions': total_word_del,
        'total_word_substitutions': total_word_sub,
        'char_ins_pct': char_ins_pct,
        'char_del_pct': char_del_pct,
        'char_sub_pct': char_sub_pct,
        'word_ins_pct': word_ins_pct,
        'word_del_pct': word_del_pct,
        'word_sub_pct': word_sub_pct,
        # New word-based accuracy metrics
        'mean_significant_word_accuracy': np.mean(sig_word_accs),
        'median_significant_word_accuracy': np.median(sig_word_accs),
        'std_significant_word_accuracy': np.std(sig_word_accs),
        'total_significant_words': total_sig_words,
        'total_significant_word_errors': total_sig_word_errors,
        'mean_capitalized_word_accuracy': np.mean(cap_word_accs),
        'median_capitalized_word_accuracy': np.median(cap_word_accs),
        'std_capitalized_word_accuracy': np.std(cap_word_accs),
        'total_capitalized_words': total_cap_words,
        'total_capitalized_word_errors': total_cap_word_errors,
        'mean_number_group_accuracy': np.mean(num_group_accs),
        'median_number_group_accuracy': np.median(num_group_accs),
        'std_number_group_accuracy': np.std(num_group_accs),
        'total_number_groups': total_num_groups,
        'total_number_group_errors': total_num_group_errors,
        # BLEU score statistics
        'mean_bleu_score': np.mean(bleu_scores),
        'median_bleu_score': np.median(bleu_scores),
        'std_bleu_score': np.std(bleu_scores),
        'min_bleu_score': np.min(bleu_scores),
        'max_bleu_score': np.max(bleu_scores),
        # Hallucination statistics
        'mean_hallucination_rate': np.mean(halluc_rates),
        'median_hallucination_rate': np.median(halluc_rates),
        'std_hallucination_rate': np.std(halluc_rates),
        'min_hallucination_rate': np.min(halluc_rates),
        'max_hallucination_rate': np.max(halluc_rates),
        'total_hallucinated_words': total_hallucinated,
        'total_unique_hallucinated_words': total_unique_hallucinated
    }


def save_detailed_results(results: List[EvaluationResult], output_file: str):
    """
    Save detailed results to CSV file.

    Args:
        results: List of EvaluationResult objects
        output_file: Path to output CSV file
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'Filename', 'OCR System', 'CER', 'WER',
            'Char Insertions', 'Char Deletions', 'Char Substitutions',
            'Word Insertions', 'Word Deletions', 'Word Substitutions',
            'Total Chars', 'Total Words',
            'Significant Word Accuracy', 'Total Significant Words', 'Significant Word Errors',
            'Capitalized Word Accuracy', 'Total Capitalized Words', 'Capitalized Word Errors',
            'Number Group Accuracy', 'Total Number Groups', 'Number Group Errors',
            'BLEU Score', 'Hallucination Rate', 'Total Hallucinated Words', 'Unique Hallucinated Words',
            'Document Year', 'Age Group'
        ])

        # Write data
        for r in results:
            writer.writerow([
                r.filename, r.ocr_system, f'{r.cer:.6f}', f'{r.wer:.6f}',
                r.char_insertions, r.char_deletions, r.char_substitutions,
                r.word_insertions, r.word_deletions, r.word_substitutions,
                r.total_chars, r.total_words,
                f'{r.significant_word_accuracy:.6f}', r.total_significant_words, r.significant_word_errors,
                f'{r.capitalized_word_accuracy:.6f}', r.total_capitalized_words, r.capitalized_word_errors,
                f'{r.number_group_accuracy:.6f}', r.total_number_groups, r.number_group_errors,
                f'{r.bleu_score:.6f}', f'{r.hallucination_rate:.6f}', r.total_hallucinated_words, r.unique_hallucinated_words,
                r.document_year if r.document_year else '', r.age_group if r.age_group else ''
            ])

    print(f"\n[OK] Detailed results saved to {output_file}")


def save_summary_results(summaries: List[Dict], output_file: str):
    """
    Save summary statistics to CSV file.

    Args:
        summaries: List of summary dictionaries
        output_file: Path to output CSV file
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'OCR System', 'Num Documents',
            'Mean CER', 'Median CER', 'Std CER', 'Min CER', 'Max CER',
            'Mean WER', 'Median WER', 'Std WER', 'Min WER', 'Max WER',
            'Char Accuracy', 'Word Accuracy',
            'Total Chars', 'Total Words', 'Total Char Errors', 'Total Word Errors',
            'Char Insertions', 'Char Deletions', 'Char Substitutions',
            'Word Insertions', 'Word Deletions', 'Word Substitutions',
            'Char Ins %', 'Char Del %', 'Char Sub %',
            'Word Ins %', 'Word Del %', 'Word Sub %',
            'Mean Significant Word Accuracy', 'Median Significant Word Accuracy', 'Std Significant Word Accuracy',
            'Total Significant Words', 'Total Significant Word Errors',
            'Mean Capitalized Word Accuracy', 'Median Capitalized Word Accuracy', 'Std Capitalized Word Accuracy',
            'Total Capitalized Words', 'Total Capitalized Word Errors',
            'Mean Number Group Accuracy', 'Median Number Group Accuracy', 'Std Number Group Accuracy',
            'Total Number Groups', 'Total Number Group Errors',
            'Mean BLEU Score', 'Median BLEU Score', 'Std BLEU Score', 'Min BLEU Score', 'Max BLEU Score',
            'Mean Hallucination Rate', 'Median Hallucination Rate', 'Std Hallucination Rate',
            'Min Hallucination Rate', 'Max Hallucination Rate',
            'Total Hallucinated Words', 'Total Unique Hallucinated Words'
        ])

        # Write data
        for s in summaries:
            if s:  # Check if summary is not empty
                writer.writerow([
                    s['ocr_system'], s['num_documents'],
                    f"{s['mean_cer']:.6f}", f"{s['median_cer']:.6f}", f"{s['std_cer']:.6f}",
                    f"{s['min_cer']:.6f}", f"{s['max_cer']:.6f}",
                    f"{s['mean_wer']:.6f}", f"{s['median_wer']:.6f}", f"{s['std_wer']:.6f}",
                    f"{s['min_wer']:.6f}", f"{s['max_wer']:.6f}",
                    f"{s['mean_char_accuracy']:.6f}", f"{s['mean_word_accuracy']:.6f}",
                    s['total_chars'], s['total_words'],
                    s['total_char_errors'], s['total_word_errors'],
                    s['total_char_insertions'], s['total_char_deletions'], s['total_char_substitutions'],
                    s['total_word_insertions'], s['total_word_deletions'], s['total_word_substitutions'],
                    f"{s['char_ins_pct']:.2f}", f"{s['char_del_pct']:.2f}", f"{s['char_sub_pct']:.2f}",
                    f"{s['word_ins_pct']:.2f}", f"{s['word_del_pct']:.2f}", f"{s['word_sub_pct']:.2f}",
                    f"{s['mean_significant_word_accuracy']:.6f}", f"{s['median_significant_word_accuracy']:.6f}",
                    f"{s['std_significant_word_accuracy']:.6f}", s['total_significant_words'], s['total_significant_word_errors'],
                    f"{s['mean_capitalized_word_accuracy']:.6f}", f"{s['median_capitalized_word_accuracy']:.6f}",
                    f"{s['std_capitalized_word_accuracy']:.6f}", s['total_capitalized_words'], s['total_capitalized_word_errors'],
                    f"{s['mean_number_group_accuracy']:.6f}", f"{s['median_number_group_accuracy']:.6f}",
                    f"{s['std_number_group_accuracy']:.6f}", s['total_number_groups'], s['total_number_group_errors'],
                    f"{s['mean_bleu_score']:.6f}", f"{s['median_bleu_score']:.6f}", f"{s['std_bleu_score']:.6f}",
                    f"{s['min_bleu_score']:.6f}", f"{s['max_bleu_score']:.6f}",
                    f"{s['mean_hallucination_rate']:.6f}", f"{s['median_hallucination_rate']:.6f}",
                    f"{s['std_hallucination_rate']:.6f}", f"{s['min_hallucination_rate']:.6f}",
                    f"{s['max_hallucination_rate']:.6f}",
                    s['total_hallucinated_words'], s['total_unique_hallucinated_words']
                ])

    print(f"[OK] Summary results saved to {output_file}")


def print_best_worst_files(results: List[EvaluationResult], top_n: int = 3):
    """
    Print the best and worst performing files by CER.

    Args:
        results: List of EvaluationResult objects
        top_n: Number of best/worst files to display
    """
    if not results:
        return

    print("\n" + "="*80)
    print("BEST AND WORST PERFORMING FILES")
    print("="*80)

    # Group by OCR system
    systems = {}
    for r in results:
        if r.ocr_system not in systems:
            systems[r.ocr_system] = []
        systems[r.ocr_system].append(r)

    for ocr_system, sys_results in systems.items():
        print(f"\n{ocr_system}")
        print("-" * 40)

        # Sort by CER
        sorted_results = sorted(sys_results, key=lambda x: x.cer)

        # Best performing
        print(f"\n  Best Performing (Top {min(top_n, len(sorted_results))}):")
        for i, r in enumerate(sorted_results[:top_n], 1):
            print(f"    {i}. {r.filename}")
            print(f"       CER: {r.cer:.4f} ({r.cer*100:.2f}%), WER: {r.wer:.4f} ({r.wer*100:.2f}%)")

        # Worst performing
        print(f"\n  Worst Performing (Bottom {min(top_n, len(sorted_results))}):")
        for i, r in enumerate(sorted_results[-top_n:][::-1], 1):
            print(f"    {i}. {r.filename}")
            print(f"       CER: {r.cer:.4f} ({r.cer*100:.2f}%), WER: {r.wer:.4f} ({r.wer*100:.2f}%)")

    print("\n" + "="*80)


def print_summary_table(summaries: List[Dict]):
    """
    Print a formatted summary table to console.

    Args:
        summaries: List of summary dictionaries
    """
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    for s in summaries:
        if not s:
            continue

        print(f"\n{s['ocr_system']}")
        print("-" * 40)
        print(f"  Documents Evaluated: {s['num_documents']}")
        print(f"  Total Characters:    {s['total_chars']:,}")
        print(f"  Total Words:         {s['total_words']:,}")

        print(f"\n  Character Error Rate (CER):")
        print(f"    Mean:   {s['mean_cer']:.4f} ({s['mean_cer']*100:.2f}%)")
        print(f"    Median: {s['median_cer']:.4f} ({s['median_cer']*100:.2f}%)")
        print(f"    Std:    {s['std_cer']:.4f}")
        print(f"    Range:  {s['min_cer']:.4f} - {s['max_cer']:.4f}")

        print(f"\n  Character Accuracy: {s['mean_char_accuracy']:.4f} ({s['mean_char_accuracy']*100:.2f}%)")

        print(f"\n  Word Error Rate (WER):")
        print(f"    Mean:   {s['mean_wer']:.4f} ({s['mean_wer']*100:.2f}%)")
        print(f"    Median: {s['median_wer']:.4f} ({s['median_wer']*100:.2f}%)")
        print(f"    Std:    {s['std_wer']:.4f}")
        print(f"    Range:  {s['min_wer']:.4f} - {s['max_wer']:.4f}")

        print(f"\n  Word Accuracy: {s['mean_word_accuracy']:.4f} ({s['mean_word_accuracy']*100:.2f}%)")

        print(f"\n  Error Breakdown (Character Level):")
        print(f"    Total Errors: {s['total_char_errors']:,}")
        print(f"    Insertions:   {s['total_char_insertions']:,} ({s['char_ins_pct']:.1f}%)")
        print(f"    Deletions:    {s['total_char_deletions']:,} ({s['char_del_pct']:.1f}%)")
        print(f"    Substitutions: {s['total_char_substitutions']:,} ({s['char_sub_pct']:.1f}%)")

        print(f"\n  Error Breakdown (Word Level):")
        print(f"    Total Errors: {s['total_word_errors']:,}")
        print(f"    Insertions:   {s['total_word_insertions']:,} ({s['word_ins_pct']:.1f}%)")
        print(f"    Deletions:    {s['total_word_deletions']:,} ({s['word_del_pct']:.1f}%)")
        print(f"    Substitutions: {s['total_word_substitutions']:,} ({s['word_sub_pct']:.1f}%)")

        # New word-based accuracy metrics from research article
        print(f"\n  Significant Word Accuracy (Content Words, Stop Words Excluded):")
        print(f"    Mean:   {s['mean_significant_word_accuracy']:.4f} ({s['mean_significant_word_accuracy']*100:.2f}%)")
        print(f"    Median: {s['median_significant_word_accuracy']:.4f} ({s['median_significant_word_accuracy']*100:.2f}%)")
        print(f"    Std:    {s['std_significant_word_accuracy']:.4f}")
        print(f"    Total Significant Words: {s['total_significant_words']:,}")
        print(f"    Total Errors: {s['total_significant_word_errors']:,}")

        print(f"\n  Capitalized Word Accuracy (Proper Nouns):")
        print(f"    Mean:   {s['mean_capitalized_word_accuracy']:.4f} ({s['mean_capitalized_word_accuracy']*100:.2f}%)")
        print(f"    Median: {s['median_capitalized_word_accuracy']:.4f} ({s['median_capitalized_word_accuracy']*100:.2f}%)")
        print(f"    Std:    {s['std_capitalized_word_accuracy']:.4f}")
        print(f"    Total Capitalized Words: {s['total_capitalized_words']:,}")
        print(f"    Total Errors: {s['total_capitalized_word_errors']:,}")

        print(f"\n  Number Group Accuracy (Dates, Currency, etc.):")
        print(f"    Mean:   {s['mean_number_group_accuracy']:.4f} ({s['mean_number_group_accuracy']*100:.2f}%)")
        print(f"    Median: {s['median_number_group_accuracy']:.4f} ({s['median_number_group_accuracy']*100:.2f}%)")
        print(f"    Std:    {s['std_number_group_accuracy']:.4f}")
        print(f"    Total Number Groups: {s['total_number_groups']:,}")
        print(f"    Total Errors: {s['total_number_group_errors']:,}")

        print(f"\n  BLEU Score (Semantic Similarity):")
        print(f"    Mean:   {s['mean_bleu_score']:.4f} ({s['mean_bleu_score']*100:.2f}%)")
        print(f"    Median: {s['median_bleu_score']:.4f} ({s['median_bleu_score']*100:.2f}%)")
        print(f"    Std:    {s['std_bleu_score']:.4f}")
        print(f"    Range:  {s['min_bleu_score']:.4f} - {s['max_bleu_score']:.4f}")

        print(f"\n  Hallucination Rate (Real words not in reference):")
        print(f"    Mean:   {s['mean_hallucination_rate']:.4f} ({s['mean_hallucination_rate']*100:.2f}%)")
        print(f"    Median: {s['median_hallucination_rate']:.4f} ({s['median_hallucination_rate']*100:.2f}%)")
        print(f"    Std:    {s['std_hallucination_rate']:.4f}")
        print(f"    Range:  {s['min_hallucination_rate']:.4f} - {s['max_hallucination_rate']:.4f}")
        print(f"    Total Hallucinated Words: {s['total_hallucinated_words']:,}")
        print(f"    Unique Hallucinated Words: {s['total_unique_hallucinated_words']:,}")

    print("\n" + "="*80)


def generate_age_grouped_statistics(results: List[EvaluationResult]) -> Dict[str, Dict]:
    """
    Generate statistics grouped by document age (25-year periods).

    Args:
        results: List of EvaluationResult objects

    Returns:
        Dictionary mapping OCR system -> age group -> statistics
    """
    # Group results by OCR system and age group
    grouped = defaultdict(lambda: defaultdict(list))

    for r in results:
        if r.age_group:  # Only include results with valid age groups
            grouped[r.ocr_system][r.age_group].append(r)

    # Calculate statistics for each group
    age_stats = {}

    for ocr_system, age_groups in grouped.items():
        age_stats[ocr_system] = {}

        for age_group, group_results in age_groups.items():
            if not group_results:
                continue

            cers = [r.cer for r in group_results]
            wers = [r.wer for r in group_results]
            bleu_scores = [r.bleu_score for r in group_results]
            halluc_rates = [r.hallucination_rate for r in group_results]

            age_stats[ocr_system][age_group] = {
                'num_documents': len(group_results),
                'mean_cer': np.mean(cers),
                'median_cer': np.median(cers),
                'std_cer': np.std(cers),
                'mean_wer': np.mean(wers),
                'median_wer': np.median(wers),
                'std_wer': np.std(wers),
                'mean_bleu': np.mean(bleu_scores),
                'median_bleu': np.median(bleu_scores),
                'std_bleu': np.std(bleu_scores),
                'mean_hallucination': np.mean(halluc_rates),
                'median_hallucination': np.median(halluc_rates),
                'std_hallucination': np.std(halluc_rates)
            }

    return age_stats


def save_age_grouped_results(age_stats: Dict[str, Dict], output_file: str):
    """
    Save age-grouped statistics to CSV file.

    Args:
        age_stats: Dictionary from generate_age_grouped_statistics()
        output_file: Path to output CSV file
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            'OCR System', 'Age Group', 'Num Documents',
            'Mean CER', 'Median CER', 'Std CER',
            'Mean WER', 'Median WER', 'Std WER',
            'Mean BLEU Score', 'Median BLEU Score', 'Std BLEU Score',
            'Mean Hallucination Rate', 'Median Hallucination Rate', 'Std Hallucination Rate'
        ])

        # Write data sorted by OCR system and age group
        for ocr_system in sorted(age_stats.keys()):
            for age_group in sorted(age_stats[ocr_system].keys()):
                stats = age_stats[ocr_system][age_group]
                writer.writerow([
                    ocr_system, age_group, stats['num_documents'],
                    f"{stats['mean_cer']:.6f}", f"{stats['median_cer']:.6f}", f"{stats['std_cer']:.6f}",
                    f"{stats['mean_wer']:.6f}", f"{stats['median_wer']:.6f}", f"{stats['std_wer']:.6f}",
                    f"{stats['mean_bleu']:.6f}", f"{stats['median_bleu']:.6f}", f"{stats['std_bleu']:.6f}",
                    f"{stats['mean_hallucination']:.6f}", f"{stats['median_hallucination']:.6f}", f"{stats['std_hallucination']:.6f}"
                ])

    print(f"[OK] Age-grouped results saved to {output_file}")


def print_age_grouped_table(age_stats: Dict[str, Dict]):
    """
    Print age-grouped statistics table to console.

    Args:
        age_stats: Dictionary from generate_age_grouped_statistics()
    """
    print("\n" + "="*80)
    print("AGE-GROUPED STATISTICS (25-year periods)")
    print("="*80)

    for ocr_system in sorted(age_stats.keys()):
        print(f"\n{ocr_system}")
        print("-" * 100)
        print(f"{'Age Group':<15} {'Docs':<6} {'CER':<12} {'WER':<12} {'BLEU':<12} {'Hallucination':<15}")
        print("-" * 100)

        for age_group in sorted(age_stats[ocr_system].keys()):
            stats = age_stats[ocr_system][age_group]
            print(
                f"{age_group:<15} "
                f"{stats['num_documents']:<6} "
                f"{stats['mean_cer']:.4f} ({stats['mean_cer']*100:.1f}%)  "
                f"{stats['mean_wer']:.4f} ({stats['mean_wer']*100:.1f}%)  "
                f"{stats['mean_bleu']:.4f} ({stats['mean_bleu']*100:.1f}%)  "
                f"{stats['mean_hallucination']:.4f} ({stats['mean_hallucination']*100:.1f}%)"
            )

    print("\n" + "="*80)


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='OCR Evaluation Tool - Compare OCR outputs against gold standard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate single OCR system
  python ocr_evaluation.py -g "Corpus/page" -o "EasyOCR/md" -n "EasyOCR"

  # Evaluate multiple OCR systems
  python ocr_evaluation.py -g "Corpus/page" \\
    -o "EasyOCR/md" -n "EasyOCR" \\
    -o "Tesseract/md" -n "Tesseract"

  # Specify output directory
  python ocr_evaluation.py -g "Corpus/page" -o "OCR/md" -n "MyOCR" --output-dir "results"
        """
    )

    parser.add_argument(
        '-g', '--gold-standard',
        required=True,
        help='Path to gold standard directory (containing .xml files)'
    )

    parser.add_argument(
        '-o', '--ocr-dir',
        action='append',
        required=True,
        help='Path to OCR output directory (containing .md files). Can be specified multiple times.'
    )

    parser.add_argument(
        '-n', '--ocr-name',
        action='append',
        required=True,
        help='Name for the OCR system. Must match order of --ocr-dir arguments.'
    )

    parser.add_argument(
        '--output-dir',
        default='.',
        help='Directory to save output CSV files (default: current directory)'
    )

    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.6,
        help='Minimum similarity score (0.0-1.0) for fuzzy filename matching (default: 0.6)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output showing text extraction details for first file'
    )

    parser.add_argument(
        '--strip-markdown-headers',
        action='store_true',
        help='Strip all lines starting with # (markdown headers) from OCR markdown files. '
             'Useful when some OCR systems include document titles while others do not.'
    )

    parser.add_argument(
        '--gold-format',
        choices=['xml', 'md'],
        default='xml',
        help='Format of gold standard files: "xml" (default, PAGE XML or hOCR) or '
             '"md" (markdown with optional YAML frontmatter, e.g. handwriting gold standards)'
    )

    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_arguments()

    # Validate arguments
    if len(args.ocr_dir) != len(args.ocr_name):
        print("Error: Number of --ocr-dir and --ocr-name arguments must match")
        return

    # Convert paths to Path objects
    gold_standard_dir = Path(args.gold_standard)
    output_dir = Path(args.output_dir)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify gold standard path exists
    if not gold_standard_dir.exists():
        print(f"Error: Gold standard directory not found: {gold_standard_dir}")
        return

    # Build OCR systems list
    ocr_systems = []
    for ocr_name, ocr_path_str in zip(args.ocr_name, args.ocr_dir):
        ocr_path = Path(ocr_path_str)
        if not ocr_path.exists():
            print(f"Warning: OCR directory not found: {ocr_path}")
            continue
        ocr_systems.append((ocr_name, ocr_path))

    if not ocr_systems:
        print("Error: No valid OCR directories found")
        return

    print("="*80)
    print("OCR EVALUATION TOOL")
    print("="*80)
    print(f"Gold Standard: {gold_standard_dir}")
    print(f"OCR Systems to evaluate: {len(ocr_systems)}")
    for name, path in ocr_systems:
        print(f"  - {name}: {path}")
    print(f"Output Directory: {output_dir}")
    print(f"Similarity Threshold: {args.similarity_threshold:.2f} ({args.similarity_threshold*100:.0f}%)")
    if args.strip_markdown_headers:
        print(f"Strip Markdown Headers: Yes")
    print(f"Gold Standard Format: {args.gold_format.upper()}")
    print("="*80)

    all_results = []
    all_summaries = []

    # Evaluate each OCR system
    for ocr_name, ocr_dir in ocr_systems:
        results = evaluate_ocr_system(
            str(ocr_dir),
            str(gold_standard_dir),
            ocr_name,
            args.similarity_threshold,
            args.verbose,
            args.strip_markdown_headers,
            args.gold_format
        )

        all_results.extend(results)

        summary = generate_summary_statistics(results)
        all_summaries.append(summary)

    # Generate timestamp for output files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save results
    if all_results:
        detailed_output = output_dir / f"ocr_evaluation_detailed_{timestamp}.csv"
        save_detailed_results(all_results, str(detailed_output))

    if all_summaries:
        summary_output = output_dir / f"ocr_evaluation_summary_{timestamp}.csv"
        save_summary_results(all_summaries, str(summary_output))
        print_summary_table(all_summaries)

    # Print best/worst performing files
    if all_results:
        print_best_worst_files(all_results, top_n=5)

    # Generate and save age-grouped statistics
    if all_results:
        age_stats = generate_age_grouped_statistics(all_results)
        if age_stats:  # Only save if there are age-grouped results
            age_grouped_output = output_dir / f"ocr_evaluation_age_grouped_{timestamp}.csv"
            save_age_grouped_results(age_stats, str(age_grouped_output))
            print_age_grouped_table(age_stats)

    print("\n[OK] Evaluation complete!")


if __name__ == "__main__":
    main()
