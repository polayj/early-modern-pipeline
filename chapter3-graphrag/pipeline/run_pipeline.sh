#!/bin/bash
#
# run_pipeline.sh — Run OCR and NER concurrently
#
# OCR processes PDFs in batches and writes .md files to output/ocr_md/.
# NER watches that directory and processes each .md as soon as it appears,
# so both steps overlap instead of running sequentially.
#
# When OCR finishes it writes a sentinel file; NER drains any remaining
# files and then exits cleanly.
#
# GPU note: Both models run on GPU. olmOCR (7.5B) + EarlyModernNER (4B) total
# ~23GB at fp16 — well within the GB10's 128GB unified memory. The workload
# naturally staggers (NER catches up on the previous batch while OCR processes
# the next), so GPU compute contention is minimal in practice.
#
# Usage:
#   bash pipeline/run_pipeline.sh
#
# Environment variables (all optional):
#   PROJECT_DIR      — repo root (default: directory of this script)
#   MODEL            — olmOCR model (default: allenai/olmOCR-7B-0825-preview)
#   BATCH_SIZE       — PDFs per OCR invocation (default: 50)
#   POLL_INTERVAL    — seconds between NER polls (default: 30)
#   CHUNK_SIZE       — NER text chunk size in chars (default: 2000)
#   VENV_DIR         — path to venv (default: $PROJECT_DIR/.venv)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
SENTINEL="$PROJECT_DIR/output/ocr_complete.sentinel"
POLL_INTERVAL="${POLL_INTERVAL:-30}"
CHUNK_SIZE="${CHUNK_SIZE:-2000}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"

# ── Activate venv ─────────────────────────────────────────────────────────────
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "WARNING: venv not found at $VENV_DIR — using system Python"
fi

# ── Pre-flight ────────────────────────────────────────────────────────────────
echo "================================================"
echo "emgraphrag Parallel Pipeline (OCR + NER)"
echo "Project:       $PROJECT_DIR"
echo "Sentinel:      $SENTINEL"
echo "NER poll:      every ${POLL_INTERVAL}s"
echo "NER device:    GPU (shared with OCR — both fit in 128GB unified memory)"
echo "================================================"

if ! python3 -c "import olmocr" &>/dev/null; then
    echo "ERROR: olmOCR not installed. Run: pip install olmocr"
    exit 1
fi
if ! python3 -c "import earlymodernner" &>/dev/null; then
    echo "ERROR: earlymodernner not installed. Run: pip install earlymodernner"
    exit 1
fi

# Remove any stale sentinel from a previous run
rm -f "$SENTINEL"
mkdir -p "$PROJECT_DIR/output"

# ── Trap: write sentinel and clean up on exit ─────────────────────────────────
NER_PID=""
cleanup() {
    echo ""
    echo "Interrupted — writing sentinel so NER can finish draining..."
    touch "$SENTINEL"
    if [ -n "$NER_PID" ] && kill -0 "$NER_PID" 2>/dev/null; then
        wait "$NER_PID" || true
    fi
}
trap cleanup INT TERM

# ── Start NER in watch mode (background) ─────────────────────────────────────
echo ""
echo "Starting NER in watch mode (GPU)..."
python3 "$PROJECT_DIR/pipeline/03_ner/run_ner.py" \
    --watch \
    --done-sentinel "$SENTINEL" \
    --poll-interval "$POLL_INTERVAL" \
    --chunk-size "$CHUNK_SIZE" \
    >> "$PROJECT_DIR/output/ner_pipeline.log" 2>&1 &
NER_PID=$!
echo "  NER PID: $NER_PID (logging to output/ner_pipeline.log)"

# ── Run OCR (foreground — holds the GPU) ─────────────────────────────────────
echo "Starting OCR (GPU)..."
echo ""
bash "$PROJECT_DIR/pipeline/02_ocr/run_ocr.sh"

# ── OCR done: write sentinel so NER knows to stop after draining ──────────────
echo ""
echo "OCR complete — writing sentinel: $SENTINEL"
touch "$SENTINEL"

# ── Wait for NER to drain remaining files ─────────────────────────────────────
echo "Waiting for NER to finish remaining files..."
wait "$NER_PID" || true
NER_PID=""

echo ""
echo "================================================"
echo "Pipeline complete!"
echo "  OCR output:  $PROJECT_DIR/output/ocr_md/"
echo "  NER output:  $PROJECT_DIR/output/ner_output/"
echo "  NER log:     $PROJECT_DIR/output/ner_pipeline.log"
echo "================================================"
echo ""
echo "Next steps:"
echo "  python pipeline/04_graph/import_records_to_docs.py"
echo "  python pipeline/04_graph/build_graph.py"
echo "  python pipeline/05_lightrag/ingest.py"
