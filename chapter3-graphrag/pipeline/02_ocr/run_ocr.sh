#!/bin/bash
#
# run_ocr.sh — olmOCR batch processing for emgraphrag corpus
#
# Requires olmOCR installed natively in the active Python environment:
#   pip install olmocr
#
# Handles two corpus layouts:
#   archive_org/  — each document in its own subdirectory containing one PDF
#   EEBO/         — flat directory of PDFs
#
# Outputs .md files to output/ocr_md/ with prefixed names:
#   archive_org__<sanitized_doc_id>.md
#   EEBO__<sanitized_basename>.md
#
# Resume-safe: skips any doc whose output .md already exists and is non-empty.
#
# Environment variables (all optional):
#   PROJECT_DIR   - path to emgraphrag repo root (default: two levels above this script)
#   MODEL         - HuggingFace model name (default: allenai/olmOCR-7B-0825-preview)
#   OUTPUT_TAG    - label for workspace subdir (default: emgraphrag_ocr)
#   BATCH_SIZE    - PDFs per olmOCR invocation (default: 50, tune for GPU memory)
#
# Usage:
#   bash pipeline/02_ocr/run_ocr.sh
#   MODEL=allenai/olmOCR-7B-0825-preview BATCH_SIZE=100 bash pipeline/02_ocr/run_ocr.sh

set -euo pipefail

# ── Resolve paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

INPUT_ARCHIVE="$PROJECT_DIR/ocr_docs/unprocessed/archive_org"
INPUT_EEBO="$PROJECT_DIR/ocr_docs/unprocessed/EEBO"
MD_DIR="$PROJECT_DIR/output/ocr_md"

OUTPUT_TAG="${OUTPUT_TAG:-emgraphrag_ocr}"
WORKSPACE="$PROJECT_DIR/output/ocr_workspace/$OUTPUT_TAG"
MODEL="${MODEL:-allenai/olmOCR-7B-0825-preview}"
BATCH_SIZE="${BATCH_SIZE:-50}"

# ── Validate environment ───────────────────────────────────────────────────────
if ! python3 -c "import olmocr" &>/dev/null; then
    echo "ERROR: olmOCR not found in current Python environment."
    echo "  Install with: pip install olmocr"
    echo "  Or from source: git clone https://github.com/allenai/olmocr && pip install -e olmocr/"
    exit 1
fi

if ! nvidia-smi &>/dev/null; then
    echo "WARNING: nvidia-smi not available — GPU may not be accessible."
    echo "  olmOCR will fall back to CPU (very slow)."
fi

mkdir -p "$MD_DIR" "$WORKSPACE/results"

echo "================================================"
echo "emgraphrag olmOCR Processing"
echo "Project:    $PROJECT_DIR"
echo "Model:      $MODEL"
echo "Output tag: $OUTPUT_TAG"
echo "MD output:  $MD_DIR"
echo "Workspace:  $WORKSPACE"
echo "Batch size: $BATCH_SIZE"
echo "================================================"

# ── Discover PDFs ──────────────────────────────────────────────────────────────
declare -A pdf_to_output_key   # pdf_path -> output_key (used for naming)
declare -A pdf_to_prefix       # pdf_path -> prefix (archive_org or EEBO)

skipped=0
queued=0

# archive_org: each doc is in its own subdirectory
if [ -d "$INPUT_ARCHIVE" ]; then
    while IFS= read -r -d '' subdir; do
        doc_id="$(basename "$subdir")"
        # Find the PDF inside this subdir (take first match)
        pdf=""
        while IFS= read -r -d '' p; do
            pdf="$p"
            break
        done < <(find "$subdir" -maxdepth 1 \( -name "*.pdf" -o -name "*.PDF" \) -print0 2>/dev/null)

        [ -z "$pdf" ] && continue

        # Sanitize doc_id for filesystem use
        safe_id="$(echo "$doc_id" | tr '/' '_' | tr ' ' '_' | tr -cd '[:alnum:]_\-.')"
        output_key="archive_org__${safe_id}"
        output_md="$MD_DIR/${output_key}.md"

        if [ -f "$output_md" ] && [ -s "$output_md" ]; then
            skipped=$((skipped + 1))
            continue
        fi

        pdf_to_output_key["$pdf"]="$output_key"
        pdf_to_prefix["$pdf"]="archive_org"
        queued=$((queued + 1))
    done < <(find "$INPUT_ARCHIVE" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
fi

# EEBO: flat directory of PDFs
if [ -d "$INPUT_EEBO" ]; then
    while IFS= read -r -d '' pdf; do
        base="$(basename "${pdf%.*}")"
        safe_base="$(echo "$base" | tr '/' '_' | tr ' ' '_' | tr -cd '[:alnum:]_\-.')"
        output_key="EEBO__${safe_base}"
        output_md="$MD_DIR/${output_key}.md"

        if [ -f "$output_md" ] && [ -s "$output_md" ]; then
            skipped=$((skipped + 1))
            continue
        fi

        pdf_to_output_key["$pdf"]="$output_key"
        pdf_to_prefix["$pdf"]="EEBO"
        queued=$((queued + 1))
    done < <(find "$INPUT_EEBO" -maxdepth 1 \( -name "*.pdf" -o -name "*.PDF" \) -print0 2>/dev/null)
fi

echo ""
echo "PDFs to process: $queued"
echo "Already done:    $skipped (skipped)"
echo "================================================"

if [ "$queued" -eq 0 ]; then
    echo "Nothing to process. Exiting."
    exit 0
fi

# ── Build model flag ───────────────────────────────────────────────────────────
MODEL_FLAG=()
if [ -n "$MODEL" ]; then
    MODEL_FLAG=(--model "$MODEL")
fi

# ── Process in batches ─────────────────────────────────────────────────────────
queued_pdfs=()
for pdf in "${!pdf_to_output_key[@]}"; do
    queued_pdfs+=("$pdf")
done

total_batches=$(( (queued + BATCH_SIZE - 1) / BATCH_SIZE ))
batch_num=0
total_processed=0
start_time=$SECONDS

for (( i=0; i<${#queued_pdfs[@]}; i+=BATCH_SIZE )); do
    batch_num=$((batch_num + 1))
    batch=("${queued_pdfs[@]:$i:$BATCH_SIZE}")
    batch_count=${#batch[@]}

    echo ""
    echo "── Batch $batch_num/$total_batches ($batch_count PDFs) ──────────────────────"

    # Clear workspace results for this batch
    rm -f "$WORKSPACE/results"/*.jsonl 2>/dev/null || true

    python3 -m olmocr.pipeline "$WORKSPACE" \
        --markdown \
        --max_model_len 32768 \
        "${MODEL_FLAG[@]}" \
        --pdfs "${batch[@]}" \
        2>&1 | tee -a "$PROJECT_DIR/output/ocr_run.log"

    pipeline_exit=${PIPESTATUS[0]}
    echo "  Pipeline exit code: $pipeline_exit"

    # ── Extract results from JSONL ─────────────────────────────────────────────
    for jsonl_file in "$WORKSPACE/results"/*.jsonl; do
        [ -e "$jsonl_file" ] || continue

        python3 - "$jsonl_file" "$MD_DIR" <<'PYEOF'
import json, os, sys, re

jsonl_file = sys.argv[1]
md_dir = sys.argv[2]

ok = 0
fail = 0

for line in open(jsonl_file, encoding='utf-8', errors='replace'):
    line = line.strip()
    if not line:
        continue
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        continue

    text = data.get('text', '')
    source = data.get('metadata', {}).get('Source-File', '')

    if not source or not text:
        fail += 1
        continue

    # Determine prefix from path
    norm = source.replace('\\', '/')
    if '/archive_org/' in norm:
        parts = norm.split('/')
        try:
            idx = parts.index('archive_org')
            doc_id = parts[idx + 1] if idx + 1 < len(parts) else os.path.splitext(parts[-1])[0]
        except ValueError:
            doc_id = os.path.splitext(os.path.basename(source))[0]
        safe_id = re.sub(r'[^\w\-.]', '_', doc_id)
        output_key = f'archive_org__{safe_id}'
    elif '/EEBO/' in norm:
        base = os.path.splitext(os.path.basename(source))[0]
        safe_base = re.sub(r'[^\w\-.]', '_', base)
        output_key = f'EEBO__{safe_base}'
    else:
        base = os.path.splitext(os.path.basename(source))[0]
        safe_base = re.sub(r'[^\w\-.]', '_', base)
        output_key = safe_base

    md_path = os.path.join(md_dir, output_key + '.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'  OK: {output_key}')
    ok += 1

print(f'  Batch results: {ok} extracted, {fail} failed/empty')
PYEOF

        total_processed=$((total_processed + 1))
    done

done

elapsed=$(( SECONDS - start_time ))
echo ""
echo "================================================"
echo "OCR processing complete!"
echo "  Processed:  $total_processed batches"
echo "  Skipped:    $skipped (already done)"
echo "  MD output:  $MD_DIR"
echo "  Total time: $(( elapsed / 60 ))m $(( elapsed % 60 ))s"
echo "  Log:        $PROJECT_DIR/output/ocr_run.log"
echo "================================================"
