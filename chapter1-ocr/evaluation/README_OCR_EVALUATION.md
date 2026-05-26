# OCR Evaluation Tool

This tool evaluates OCR (Optical Character Recognition) output quality by comparing it against manually transcribed "gold standard" text. It calculates **Character Error Rate (CER)**, **Word Error Rate (WER)**, and provides detailed error analysis with breakdown by error type.

## What is CER and WER?

### Character Error Rate (CER)
CER measures the accuracy at the character level:
```
CER = (Substitutions + Deletions + Insertions) / Total Characters
```
- Lower values are better
- 0.0 = perfect match
- Typical values: 0.05-0.30 for good OCR, 0.30+ indicates poor quality

### Word Error Rate (WER)
WER measures the accuracy at the word level:
```
WER = (Substitutions + Deletions + Insertions) / Total Words
```
- Lower values are better
- 0.0 = perfect match
- Typical values: 0.10-0.50 for good OCR, 0.50+ indicates poor quality

## Features

- **Flexible Directory Selection**: Specify directories via command-line arguments
- **Multiple OCR System Support**: Evaluate multiple OCR systems in a single run
- **Multiple Format Support**: Auto-detects and handles Transkribus PAGE XML, hOCR, and markdown
- **Fuzzy Filename Matching**: Automatically matches files even when names differ slightly
- **Comprehensive Metrics**: CER, WER, accuracy percentages, and error type breakdowns
- **Best/Worst File Ranking**: Identify top 5 best and worst performing documents
- **Detailed Error Analysis**: See breakdown of insertions, deletions, and substitutions
- **CSV Export**: Both detailed per-file results and aggregate summary statistics
- **Match Diagnostics**: Shows similarity scores and suggests closest matches for unmatched files

## Files

- `ocr_evaluation.py` - Main evaluation script
- `evaluate_all_ocr_systems.py` - Batch evaluation script for multiple OCR systems
- `requirements.txt` - Python dependencies
- `ocr_evaluation_detailed_YYYYMMDD_HHMMSS.csv` - Per-file results (generated after running, timestamped)
- `ocr_evaluation_summary_YYYYMMDD_HHMMSS.csv` - Summary statistics per OCR system (generated after running, timestamped)
- `ocr_evaluation_age_grouped_YYYYMMDD_HHMMSS.csv` - Age-grouped statistics (generated after running, timestamped)

## Directory Requirements

The script is flexible and works with any directory structure. You need:
- **Gold standard directory**: Contains `.xml` files with reference transcriptions (Transkribus PAGE XML format)
- **OCR output directory**: Contains OCR results in one of these formats:
  - `.xml` files (Transkribus PAGE XML or hOCR format - auto-detected)
  - `.md` files (markdown)

Example structure:
```
.
├── ocr_evaluation.py
├── Corpus/
│   └── page/                          # Gold standard XML files
│       ├── document1.xml
│       ├── document2.xml
│       └── ...
├── EasyOCR/
│   └── md/                            # EasyOCR output (markdown)
│       ├── document1_page_001.md
│       ├── document2_page_001.md
│       └── ...
├── Tesseract/
│   └── xml/                           # Tesseract output (XML)
│       ├── document1.xml
│       ├── document2.xml
│       └── ...
└── Transkribus/
    └── xml/                           # Transkribus output (XML)
        ├── document1.xml
        ├── document2.xml
        └── ...
```

## Installation

1. Install Python 3.7 or higher
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The tool uses command-line arguments for flexibility. Use `-g` for gold standard directory, `-o` for OCR directories, and `-n` for OCR system names.

### Basic Usage - Single OCR System

```bash
python ocr_evaluation.py -g "Corpus/page" -o "EasyOCR/md" -n "EasyOCR"
```

### Evaluate Multiple OCR Systems

```bash
python ocr_evaluation.py -g "Corpus/page" \
  -o "EasyOCR/md" -n "EasyOCR" \
  -o "Tesseract/md" -n "Tesseract"
```

### Specify Output Directory

```bash
python ocr_evaluation.py -g "Corpus/page" -o "EasyOCR/md" -n "EasyOCR" --output-dir "results"
```

### Get Help

```bash
python ocr_evaluation.py --help
```

### Command-Line Options

- `-g, --gold-standard`: Path to gold standard directory (required)
- `-o, --ocr-dir`: Path to OCR output directory (required, can be used multiple times)
- `-n, --ocr-name`: Name for the OCR system (required, must match order of `-o` flags)
- `--output-dir`: Directory to save CSV files (optional, defaults to current directory)
- `--similarity-threshold`: Minimum similarity score (0.0-1.0) for filename matching (optional, default: 0.6)
- `--verbose`: Show detailed text extraction information for first file of each OCR system (optional, useful for debugging)

### Adjusting Filename Matching

If filenames between OCR output and gold standard differ slightly, you can adjust the matching threshold:

```bash
# More lenient matching (50% similarity required)
python ocr_evaluation.py -g "Corpus/page" -o "OCR/xml" -n "MyOCR" --similarity-threshold 0.5

# Stricter matching (80% similarity required)
python ocr_evaluation.py -g "Corpus/page" -o "OCR/xml" -n "MyOCR" --similarity-threshold 0.8
```

The tool uses fuzzy matching to pair files even when names differ. For example:
- `document123.xml` (OCR) matches `document123_final.xml` (gold standard)
- `report_page_001.md` (OCR) matches `report.xml` (gold standard)
- `file-2024.xml` (OCR) matches `file-2024-edited.xml` (gold standard)

### What the Script Does

1. Validates all directories exist
2. Matches OCR output files with gold standard transcriptions
3. Calculates CER and WER for each file
4. Generates detailed error breakdowns (insertions, deletions, substitutions)
5. Creates CSV reports with comprehensive metrics
6. Displays summary statistics in the console
7. Shows best and worst performing files for each OCR system

## Output Files

**All output CSV files are timestamped** to prevent overwriting previous results. The timestamp format is `YYYYMMDD_HHMMSS` (e.g., `20250130_143022`).

### ocr_evaluation_detailed_YYYYMMDD_HHMMSS.csv
Contains per-file metrics for every document:
- Filename
- OCR System
- CER and WER values
- Detailed error counts at character level (insertions, deletions, substitutions)
- Detailed error counts at word level (insertions, deletions, substitutions)
- Total character and word counts
- Significant word accuracy, capitalized word accuracy, number group accuracy
- BLEU score, document year, and age group

### ocr_evaluation_summary_YYYYMMDD_HHMMSS.csv
Contains comprehensive aggregate statistics for each OCR system:
- Number of documents evaluated
- Mean, median, standard deviation, min, and max CER
- Mean, median, standard deviation, min, and max WER
- Character accuracy (1 - CER)
- Word accuracy (1 - WER)
- Total characters and words processed
- Total errors by type (insertions, deletions, substitutions)
- Error type percentages (what proportion of errors are insertions vs deletions vs substitutions)
- Word-based accuracy metrics (significant words, capitalized words, number groups)
- BLEU score statistics

### ocr_evaluation_age_grouped_YYYYMMDD_HHMMSS.csv
Contains statistics grouped by document age (25-year periods):
- OCR system performance by historical period
- Useful for analyzing how OCR performs on documents of different ages

### Console Output
The script displays:
- Configuration summary (directories being used, similarity threshold)
- File format detection (XML or markdown)
- Progress updates as each file is processed
- Fuzzy match notifications when files are paired with less than 100% similarity
- Match summary showing successfully matched vs unmatched files
- Comprehensive summary statistics table for each OCR system
- Best 5 and worst 5 performing files by CER for each OCR system

## Understanding the Results

### Error Rates (CER and WER)

**Good OCR Performance**
- CER < 0.10 (less than 10% character errors) → 90%+ character accuracy
- WER < 0.30 (less than 30% word errors) → 70%+ word accuracy

**Moderate OCR Performance**
- CER 0.10-0.30 (70-90% character accuracy)
- WER 0.30-0.60 (40-70% word accuracy)

**Poor OCR Performance**
- CER > 0.30 (less than 70% character accuracy)
- WER > 0.60 (less than 40% word accuracy)

### Error Type Breakdown

The tool shows what types of errors are most common:
- **Insertions**: Extra characters/words added by OCR
- **Deletions**: Characters/words missing from OCR output
- **Substitutions**: Characters/words incorrectly transcribed

Understanding error patterns helps identify:
- High insertions might indicate OCR seeing artifacts or noise
- High deletions might indicate faint or missing text
- High substitutions might indicate character confusion (e.g., 'O' vs '0')

### Best/Worst Files Analysis

The tool identifies the top 5 best and worst performing files for each OCR system. Use this to:
- **Best files**: Understand what document characteristics lead to good OCR results
- **Worst files**: Identify problematic documents that may need manual review or reprocessing
- **Comparison**: See which documents are consistently easy/hard across different OCR systems

## How It Works

1. **File Matching**: Uses intelligent fuzzy matching to pair OCR output with gold standard files
   - Removes common suffixes (e.g., `_page_001.md`, `_page_001.xml`)
   - Tries exact match first
   - Falls back to prefix-based similarity scoring
   - Pairs files if similarity score exceeds threshold (default: 60%)
   - Reports match confidence for non-exact matches
2. **Text Extraction**:
   - Gold standard: Extracts Unicode text from Transkribus PAGE XML
   - OCR output: Auto-detects format and extracts accordingly:
     - **Transkribus PAGE XML**: Extracts from `<Unicode>` elements
     - **hOCR (HTML-based OCR)**: Extracts from `<span>` elements
     - **Markdown**: Extracts plain text with markdown headers removed
3. **Text Normalization**: Converts to lowercase, normalizes whitespace
4. **Error Calculation**: Uses Levenshtein distance (edit distance) algorithm
5. **Statistical Analysis**: Computes mean, median, std dev, min, max

## Technical Details

- **Algorithm**: Dynamic programming implementation of Levenshtein distance
- **Complexity**: O(n*m) where n and m are text lengths
- **Normalization**: Case-insensitive comparison with whitespace normalization

## Adding New OCR Systems

### Method 1: Using the Batch Script (Recommended)

The easiest way to add a new OCR system is to edit `evaluate_all_ocr_systems.py`:

1. Open `evaluate_all_ocr_systems.py` in a text editor
2. Find the `OCR_SYSTEMS` configuration section (clearly marked with comments)
3. Add a new line with your OCR system:
   ```python
   ("MyNewOCR", r"Z:\Path\To\MyNewOCR\completed\md"),
   ```
4. Save the file and run the batch script

The configuration section has detailed comments explaining how to add, disable, or remove OCR systems.

### Method 2: Using Command-Line Arguments

You can also evaluate a new OCR system directly via command line:

```bash
python ocr_evaluation.py -g "Corpus/page" \
  -o "EasyOCR/md" -n "EasyOCR" \
  -o "Tesseract/md" -n "Tesseract" \
  -o "MyNewOCR/md" -n "MyNewOCR"
```

### Requirements for OCR Output

Just ensure your OCR output:
- Is in either `.xml` (Transkribus PAGE XML or hOCR) or `.md` (markdown) format
- Has filenames that share a common prefix with gold standard files

The fuzzy matching handles various naming patterns:
- Exact match: `document.xml` (OCR) ↔ `document.xml` (gold standard)
- With suffix: `document_page_001.md` (OCR) ↔ `document.xml` (gold standard)
- Different suffixes: `document_final.xml` (OCR) ↔ `document_original.xml` (gold standard)
- Software modifications: `file123.xml` (OCR) ↔ `file123_processed_2024.xml` (gold standard)

## Troubleshooting

### "Error: Gold standard directory not found"
- Double-check the path you provided with `-g` flag
- Use quotes around paths with spaces: `-g "My Folder/page"`
- Paths can be absolute or relative

### "Error: OCR directory not found"
- Verify the path you provided with `-o` flag
- Ensure the directory exists before running the script
- The script will show a warning and skip that OCR system

### "Error: Number of --ocr-dir and --ocr-name arguments must match"
- Each `-o` flag must have a corresponding `-n` flag
- Example: `-o "dir1" -n "Name1" -o "dir2" -n "Name2"`

### "ERROR: No .xml or .md files found"
- The OCR directory doesn't contain any `.xml` or `.md` files
- Check that you're pointing to the correct directory
- Ensure your OCR output files have the correct extension

### "ERROR: No text extracted from [file] - file may be empty or wrong format"
- The tool couldn't extract text from an XML file
- Possible causes:
  - The XML format is not recognized (not Transkribus PAGE XML or hOCR)
  - The file is actually empty
  - The file is corrupted
- Solution: Run with `--verbose` flag to see detailed format information for the first file
- The tool auto-detects these XML formats:
  - **Transkribus PAGE XML**: Root tag contains `PcGts` or `PAGE`
  - **hOCR**: Root tag is `html` with XHTML namespace

### "No gold standard found" warnings
- The OCR output filename doesn't match any gold standard file above the similarity threshold
- The warning will suggest the closest potential match if found
- Solutions:
  - Lower the `--similarity-threshold` (e.g., from 0.6 to 0.5) for more lenient matching
  - Check that filenames share a common prefix
  - Rename files to have more similar names
- Example warning: `[WARNING] No gold standard found for file123.xml (closest: file123_edited.xml)`

### Slow processing
- Processing 100 files takes several minutes due to edit distance calculations
- This is normal for large documents
- Consider evaluating a smaller subset first to test

### Unicode errors on Windows
- The script uses `[OK]` and `[WARNING]` prefixes instead of Unicode symbols for Windows compatibility

## References

- Levenshtein Distance: https://en.wikipedia.org/wiki/Levenshtein_distance
- PAGE XML Format: https://github.com/PRImA-Research-Lab/PAGE-XML
- Transkribus: https://readcoop.eu/transkribus/

## License

This tool is provided as-is for research and evaluation purposes.
