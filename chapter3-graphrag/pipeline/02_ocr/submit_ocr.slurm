#!/bin/bash
#SBATCH --job-name=emgraphrag_ocr
#SBATCH --account=${SLURM_ACCOUNT:-def-jic823}
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --gpus-per-node=1
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
#
# SLURM job script for emgraphrag olmOCR processing.
# Uses native olmOCR install (no Apptainer container needed).
#
# Submit from emgraphrag project root:
#   sbatch pipeline/02_ocr/submit_ocr.slurm
#
# Optional overrides via environment before sbatch:
#   MODEL=allenai/olmOCR-7B-0825-preview BATCH_SIZE=100 sbatch pipeline/02_ocr/submit_ocr.slurm

echo "Job started at: $(date)"
echo "Running on node: $(hostname)"
echo "Job ID: $SLURM_JOB_ID"
echo "Working dir: $(pwd)"
echo "================================================"

export MODEL="${MODEL:-allenai/olmOCR-7B-0825-preview}"
export OUTPUT_TAG="${OUTPUT_TAG:-emgraphrag_ocr}"
export BATCH_SIZE="${BATCH_SIZE:-50}"
export PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
export VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"

# ── Activate venv ─────────────────────────────────────────────────────────────
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    echo "Activated venv: $VENV_DIR"
else
    echo "WARNING: venv not found at $VENV_DIR — using system Python"
    echo "  Create it with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt olmocr"
fi

# ── Pre-flight checks ─────────────────────────────────────────────────────────
echo ""
echo "Pre-flight checks..."

if ! python3 -c "import olmocr" &>/dev/null; then
    echo "FATAL: olmOCR not installed. Run: pip install olmocr"
    exit 1
fi
echo "  olmOCR: OK"

if ! nvidia-smi &>/dev/null; then
    echo "FATAL: nvidia-smi not available — no GPU allocated"
    exit 1
fi
echo "  GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
echo "  Model: $MODEL"
echo ""
echo "All pre-flight checks passed."
echo "================================================"

# ── Run OCR ───────────────────────────────────────────────────────────────────
echo ""
echo "Starting olmOCR processing..."
bash "$PROJECT_DIR/pipeline/02_ocr/run_ocr.sh"

echo "================================================"
echo "Job completed at: $(date)"
