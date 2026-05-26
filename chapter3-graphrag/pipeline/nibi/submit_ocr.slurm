#!/bin/bash
#SBATCH --job-name=emgraphrag_ocr
#SBATCH --account=def-jic823
#SBATCH --time=8:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4
#SBATCH --gpus-per-node=h100:1
#SBATCH --output=emgraphrag_ocr_%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

# submit_ocr.slurm — OCR job for Nibi (H100, x86_64)
#
# Submits a 48-hour OCR job. Resume-safe: already-processed PDFs are skipped.
# Submit from the project root:
#   cd ~/projects/def-jic823/Jacob-Projects/emgraphrag
#   sbatch pipeline/nibi/submit_ocr.slurm

set -euo pipefail

PROJECT_DIR=~/projects/def-jic823/Jacob-Projects/emgraphrag
VENV_PATH="$PROJECT_DIR/venv"

echo "======================================================"
echo "emgraphrag OCR — Nibi SLURM job"
echo "Job ID:     $SLURM_JOB_ID"
echo "Node:       $SLURMD_NODENAME"
echo "Start time: $(date)"
echo "======================================================"

# ── Load modules ─────────────────────────────────────────────────────────────
module load gcc python/3.11 opencv

# ── Activate venv ─────────────────────────────────────────────────────────────
source "$VENV_PATH/bin/activate"
echo "Python: $(python --version)"
echo "Venv:   $VIRTUAL_ENV"

# ── Offline mode (model was pre-downloaded on login node) ────────────────────
export HF_HOME="$PROJECT_DIR/.cache/huggingface"
# setup_nibi_env.sh passed cache_dir=HF_HOME to snapshot_download, so the model
# lives at $HF_HOME/models--... rather than the default $HF_HOME/hub/models--...
# Point HF_HUB_CACHE to the same location so olmocr finds it.
export HF_HUB_CACHE="$PROJECT_DIR/.cache/huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo "HF_HOME:     $HF_HOME"
echo "HF_HUB_CACHE: $HF_HUB_CACHE"
echo ""

# ── Run OCR ───────────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"
bash pipeline/nibi/process_ocr.sh

echo ""
echo "======================================================"
echo "OCR job complete: $(date)"
echo "======================================================"
