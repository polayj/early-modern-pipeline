# Batch OCR Evaluation Guide

This guide explains how to evaluate all your OCR systems at once using the batch evaluation scripts.

## Quick Start

### Option 1: Double-Click (Windows)
Simply double-click `evaluate_all_ocr_systems.bat`

### Option 2: Command Line
```bash
cd "Z:\OCR Evaluation"
python evaluate_all_ocr_systems.py
```

## What It Does

1. **Checks which OCR systems have markdown files ready**
   - Shows you which systems are available
   - Counts how many .md files each has

2. **Runs comprehensive evaluation**
   - Character Error Rate (CER)
   - Word Error Rate (WER)
   - Significant Word Accuracy (content words)
   - Capitalized Word Accuracy (proper nouns)
   - Number Group Accuracy (dates, currency)
   - Error breakdowns by type

3. **Saves timestamped results**
   - All CSV files include timestamps to prevent overwriting
   - Detailed CSV: Per-file metrics for every document
   - Summary CSV: Aggregate statistics for each OCR system
   - Age-grouped CSV: Performance statistics by document age
   - Results organized by date/time in `results/` folder

## Directory Structure Expected

```
Z:\
├── Corpus\
│   └── Corpus_Gold\
│       └── page\               ← Your gold standard XML files
│           ├── file1.xml
│           ├── file2.xml
│           └── ... (100 files)
│
├── Tesseract\
│   └── completed\
│       └── md\                 ← Tesseract markdown outputs
│           ├── file1.md
│           └── ... (100 files)
│
├── EasyOCR\
│   └── completed\
│       └── md\                 ← EasyOCR markdown outputs
│
├── Kraken\
│   └── completed\
│       └── md\                 ← Kraken markdown outputs
│
... (and so on for all 8 OCR systems)
```

## Configured OCR Systems

The script looks for markdown files in these locations:

1. **Tesseract**: `Z:\Tesseract\completed\md`
2. **EasyOCR**: `Z:\EasyOCR\completed\md`
3. **Kraken**: `Z:\Kraken\completed\md`
4. **Gemini**: `Z:\Gemini\completed\md`
5. **MinerU**: `Z:\MinerU\completed\md`
6. **OlmOCR**: `Z:\OlmOCR\completed\md`
7. **Transkribus**: `Z:\Transkribus\completed\md`
8. **DeepSeek**: `Z:\DeepSeek\completed\md`

## Adding/Removing OCR Systems

### Quick Instructions

1. Open `evaluate_all_ocr_systems.py` in any text editor
2. Find the `OCR_SYSTEMS` configuration section (clearly marked with comment blocks)
3. To **add a new system**: Add a new line following the format:
   ```python
   ("SystemName", r"Z:\Path\To\System\completed\md"),
   ```
4. To **disable a system temporarily**: Add `#` at the start of the line:
   ```python
   # ("Kraken", r"Z:\Kraken\completed\md"),
   ```
5. To **remove a system permanently**: Delete the entire line
6. Save the file

### Example Configuration

```python
OCR_SYSTEMS = [
    # Active OCR Systems
    ("Tesseract", r"Z:\Tesseract\completed\md"),
    ("EasyOCR", r"Z:\EasyOCR\completed\md"),
    # ("Kraken", r"Z:\Kraken\completed\md"),  # Temporarily disabled

    # Add new systems below:
    # ("MyNewOCR", r"Z:\MyNewOCR\completed\md"),
]
```

**The configuration section has detailed comments** explaining each step. No Python knowledge required!

## Output Files

Results are saved to `Z:\OCR Evaluation\results\evaluation_YYYYMMDD_HHMMSS\`

**All CSV files are timestamped** (format: `YYYYMMDD_HHMMSS`) to prevent overwriting previous results.

### ocr_evaluation_detailed_YYYYMMDD_HHMMSS.csv
Contains per-file metrics for every document:
- Filename, OCR System
- CER, WER
- Character errors (insertions, deletions, substitutions)
- Word errors (insertions, deletions, substitutions)
- Significant word accuracy
- Capitalized word accuracy
- Number group accuracy
- BLEU score, document year, age group
- Total characters, total words

### ocr_evaluation_summary_YYYYMMDD_HHMMSS.csv
Contains aggregate statistics for each OCR system:
- Number of documents evaluated
- Mean/median/std CER and WER
- Character and word accuracy percentages
- Total errors by type
- Error type percentages
- All word-based accuracy metrics
- BLEU score statistics

### ocr_evaluation_age_grouped_YYYYMMDD_HHMMSS.csv
Contains performance statistics grouped by document age (25-year periods):
- OCR system performance across different historical periods
- Useful for analyzing how document age affects OCR accuracy

### Console Output
The script also prints:
- Summary statistics table for each system
- Best 5 and worst 5 performing files (by CER)
- File matching status

## Understanding the Results

### Character Error Rate (CER)
- **Good**: CER < 0.10 (90%+ accuracy)
- **Moderate**: CER 0.10-0.30 (70-90% accuracy)
- **Poor**: CER > 0.30 (<70% accuracy)

### Word Error Rate (WER)
- **Good**: WER < 0.30 (70%+ accuracy)
- **Moderate**: WER 0.30-0.60 (40-70% accuracy)
- **Poor**: WER > 0.60 (<40% accuracy)

### Significant Word Accuracy
Measures accuracy on content words (excluding "the", "a", "of", etc.)
- Important for searchability and information extraction
- Higher values mean better performance on meaningful words

### Capitalized Word Accuracy
Measures accuracy on proper nouns (names, places)
- Critical for historical documents with person/place names
- Shows how well OCR handles entities

### Number Group Accuracy
Measures accuracy on dates, currency, numbers
- Essential for preserving factual information
- Common error source in historical documents

## Example Workflow

1. **Generate markdown files from one OCR system**
   ```bash
   # Example: You've just finished running EasyOCR
   # Files are in Z:\EasyOCR\completed\md
   ```

2. **Run batch evaluation**
   ```bash
   # Double-click evaluate_all_ocr_systems.bat
   # Or run: python evaluate_all_ocr_systems.py
   ```

3. **Review results**
   - Open the CSV files in Excel or a text editor
   - Compare CER/WER across systems
   - Identify which OCR works best for your documents

4. **Add more OCR systems as you process them**
   - Place new .md files in the appropriate directory
   - Re-run the batch evaluation
   - Results will include all available systems

## Troubleshooting

### "No OCR systems with markdown files found"
- Check that your .md files are in the correct directories
- Verify the paths in `evaluate_all_ocr_systems.py`
- Make sure files have the `.md` extension

### "Gold standard directory not found"
- Check that `Z:\Corpus\Corpus_Gold\page` exists
- Verify it contains your gold standard .xml files

### Filename matching issues
- The script uses fuzzy matching (60% similarity threshold)
- If files aren't matching, you may need to rename them
- Or adjust `--similarity-threshold` in the script (line with 0.6)

### Different number of files in different OCR systems
- This is okay! The script will evaluate whatever is available
- The summary will show how many files were matched for each system

## Customization

### Change similarity threshold for filename matching
Edit line in `evaluate_all_ocr_systems.py`:
```python
"--similarity-threshold", "0.6",  # Change to 0.5 for more lenient matching
```

### Change output directory
Edit at the top of `evaluate_all_ocr_systems.py`:
```python
OUTPUT_DIR = r"Z:\OCR Evaluation\my_custom_results"
```

### Enable verbose mode
Edit the cmd construction in `evaluate_all_ocr_systems.py`:
```python
cmd = [
    sys.executable,
    "ocr_evaluation.py",
    "-g", GOLD_STANDARD_DIR,
    "--output-dir", str(output_path),
    "--verbose",  # Add this line
]
```

## Comparison with OmniDocBench

### Your OCR Evaluation Tool Advantages:
✓ More comprehensive metrics (CER, WER, significant words, etc.)
✓ Designed specifically for OCR text comparison
✓ Handles filename variations automatically
✓ No complex dependencies
✓ Faster execution
✓ Better statistical analysis

### When to Use OmniDocBench:
- You have structured layout detection (titles, footers, headers)
- You have table structure parsing (not just table text)
- You want to evaluate document parsing systems
- You need reading order evaluation with semantic labels

**For comparing OCR text accuracy on historical documents, your custom tool is superior!**

## Tips

1. **Start with a subset**: Test with one or two OCR systems first
2. **Check the detailed CSV**: Identify specific problematic documents
3. **Use "Best/Worst Files" output**: Focus improvement efforts on worst performers
4. **Compare error types**: Different OCR systems have different error patterns
5. **Re-run as needed**: The script is designed for multiple runs as you add systems

## Questions?

Refer to the main `README_OCR_EVALUATION.md` for detailed information about:
- What CER and WER mean
- How the metrics are calculated
- File format requirements
- Advanced usage options
