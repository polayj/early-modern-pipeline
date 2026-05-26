#!/bin/bash
#
# process_ocr.sh — OCR processing worker for Nibi
#
# Called by submit_ocr.slurm after the venv is activated.
# Handles both corpus layouts:
#   archive_org/  — each doc in its own subdirectory with one PDF
#   EEBO/         — flat directory of PDFs
#
# Output naming:
#   archive_org__<sanitized_doc_id>.md
#   EEBO__<basename>.md
#
# Resume-safe: skips PDFs that already have a non-empty .md output file.
# Processes in batches so the model is loaded once per BATCH_SIZE PDFs.
#
# Environment variables (all have defaults):
#   PROJECT_DIR   — repo root on Nibi
#   INPUT_DIR     — path to ocr_docs/unprocessed/
#   OUTPUT_DIR    — path to output/ocr_md/
#   BATCH_SIZE    — PDFs per olmocr.pipeline call (default: 50)
#   OCR_MODEL     — HuggingFace model ID

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/projects/def-jic823/Jacob-Projects/emgraphrag}"
INPUT_DIR="${INPUT_DIR:-$PROJECT_DIR/ocr_docs/unprocessed}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/output/ocr_md}"
WORKSPACE="${SCRATCH:-/tmp}/emgraphrag_ocr_workspace_$$"
BATCH_SIZE="${BATCH_SIZE:-50}"
OCR_MODEL="${OCR_MODEL:-allenai/olmOCR-2-7B-1025}"

mkdir -p "$OUTPUT_DIR" "$WORKSPACE"

echo "================================================"
echo "emgraphrag OCR Processing — Nibi"
echo "================================================"
echo "Input:      $INPUT_DIR"
echo "Output:     $OUTPUT_DIR"
echo "Workspace:  $WORKSPACE"
echo "Batch size: $BATCH_SIZE"
echo "Model:      $OCR_MODEL"
echo "HF_HOME:    ${HF_HOME:-<not set>}"
echo ""

# ── Collect unprocessed PDFs ──────────────────────────────────────────────────
echo "Scanning for PDFs..."

declare -a pdf_files=()
declare -a output_names=()

# archive_org: subdirectory per doc
archive_dir="$INPUT_DIR/archive_org"
if [ -d "$archive_dir" ]; then
    while IFS= read -r -d '' subdir; do
        doc_title="$(basename "$subdir")"
        # Find the PDF in this subdir
        pdf_path=""
        while IFS= read -r -d '' f; do
            pdf_path="$f"
            break
        done < <(find "$subdir" -maxdepth 1 -name "*.pdf" -print0 2>/dev/null)

        [ -z "$pdf_path" ] && continue

        # Sanitize output name
        safe_id="${doc_title//[^a-zA-Z0-9_\-.]/_}"
        out_name="archive_org__${safe_id}"
        out_path="$OUTPUT_DIR/${out_name}.md"

        if [ -f "$out_path" ] && [ -s "$out_path" ]; then
            continue  # already done
        fi

        pdf_files+=("$pdf_path")
        output_names+=("$out_name")
    done < <(find "$archive_dir" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null | sort -z)
fi

# EEBO: flat directory
eebo_dir="$INPUT_DIR/EEBO"
if [ -d "$eebo_dir" ]; then
    while IFS= read -r -d '' pdf_path; do
        basename_noext="$(basename "${pdf_path%.pdf}")"
        basename_noext="${basename_noext%.PDF}"
        safe_base="${basename_noext//[^a-zA-Z0-9_\-.]/_}"
        out_name="EEBO__${safe_base}"
        out_path="$OUTPUT_DIR/${out_name}.md"

        if [ -f "$out_path" ] && [ -s "$out_path" ]; then
            continue
        fi

        pdf_files+=("$pdf_path")
        output_names+=("$out_name")
    done < <(find "$eebo_dir" -maxdepth 1 \( -name "*.pdf" -o -name "*.PDF" \) -print0 2>/dev/null | sort -z)
fi

total=${#pdf_files[@]}
echo "  PDFs to process: $total"

if [ "$total" -eq 0 ]; then
    echo "Nothing to do — all PDFs already processed."
    exit 0
fi

# ── Process in batches ────────────────────────────────────────────────────────
batch_num=0
processed=0
failed=0

for (( i=0; i<total; i+=BATCH_SIZE )); do
    batch_num=$(( batch_num + 1 ))
    end=$(( i + BATCH_SIZE ))
    [ "$end" -gt "$total" ] && end=$total
    count=$(( end - i ))

    echo ""
    echo "Batch $batch_num: PDFs $((i+1))–$end of $total..."

    batch_pdfs=("${pdf_files[@]:$i:$count}")
    batch_names=("${output_names[@]:$i:$count}")

    batch_workspace="$WORKSPACE/batch_${batch_num}"
    mkdir -p "$batch_workspace"

    # Run olmOCR pipeline
    python -m olmocr.pipeline "$batch_workspace" \
        --markdown \
        --max_model_len 32768 \
        --model "$OCR_MODEL" \
        --pdfs "${batch_pdfs[@]}" \
        2>&1 | tail -5 || true

    # Extract results from JSONL → correctly named .md files
    if ls "$batch_workspace"/results/*.jsonl &>/dev/null 2>&1; then
        for jsonl_file in "$batch_workspace"/results/*.jsonl; do
            python3 - <<PYEOF "$jsonl_file" "$OUTPUT_DIR" "${batch_pdfs[@]}"
import json, sys, os, re

jsonl_path = sys.argv[1]
out_dir    = sys.argv[2]
pdf_paths  = sys.argv[3:]

# Build map: pdf_basename → full_pdf_path
pdf_map = {}
for p in pdf_paths:
    pdf_map[os.path.basename(p)] = p

for line in open(jsonl_path, encoding='utf-8', errors='replace'):
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except Exception:
        continue
    text   = data.get('text', '')
    source = data.get('metadata', {}).get('Source-File', '')
    if not text or not source:
        continue

    src_basename = os.path.basename(source)
    src_pdf_path = pdf_map.get(src_basename, source)

    # Reconstruct the output name from the original path
    if '/archive_org/' in src_pdf_path:
        doc_title = os.path.basename(os.path.dirname(src_pdf_path))
        safe_id = re.sub(r'[^\w\-.]', '_', doc_title)
        out_name = f'archive_org__{safe_id}'
    else:
        stem = os.path.splitext(src_basename)[0]
        safe_base = re.sub(r'[^\w\-.]', '_', stem)
        out_name = f'EEBO__{safe_base}'

    out_path = os.path.join(out_dir, out_name + '.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'  OK: {out_name}')
PYEOF
        done
    fi

    # Clean up batch workspace to save disk space
    rm -rf "$batch_workspace"

    processed=$(( processed + count ))
    echo "  Batch $batch_num done. Running total: $processed / $total"
done

# ── Summary ───────────────────────────────────────────────────────────────────
md_count=$(find "$OUTPUT_DIR" -name "*.md" -type f 2>/dev/null | wc -l)

echo ""
echo "================================================"
echo "OCR complete!"
echo "  Total .md files in output: $md_count"
echo "  Output: $OUTPUT_DIR"
echo "================================================"

# Clean up scratch workspace
rm -rf "$WORKSPACE"
