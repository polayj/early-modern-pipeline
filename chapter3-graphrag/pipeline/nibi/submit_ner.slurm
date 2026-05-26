#!/bin/bash
#SBATCH --job-name=emgraphrag_ner
#SBATCH --account=def-jic823
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --gpus-per-node=h100:1
#SBATCH --output=emgraphrag_ner_%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

# submit_ner.slurm — EarlyModernNER job for Nibi (H100, x86_64)
#
# Runs NER over all markdown files in output/ocr_md/.
# Resume-safe: already-processed docs are skipped.
# Submit from the project root:
#   cd ~/projects/def-jic823/Jacob-Projects/emgraphrag
#   sbatch pipeline/nibi/submit_ner.slurm
# Or as a dependency (see submit_pipeline.sh):
#   sbatch --dependency=afterok:<ocr_job_id> pipeline/nibi/submit_ner.slurm

set -euo pipefail

PROJECT_DIR=~/projects/def-jic823/Jacob-Projects/emgraphrag
VENV_PATH="$PROJECT_DIR/venv"

echo "======================================================"
echo "emgraphrag NER — Nibi SLURM job"
echo "Job ID:     $SLURM_JOB_ID"
echo "Node:       $SLURMD_NODENAME"
echo "Start time: $(date)"
echo "======================================================"

# ── Load modules ─────────────────────────────────────────────────────────────
module load python/3.11

# ── Activate venv ─────────────────────────────────────────────────────────────
source "$VENV_PATH/bin/activate"
echo "Python: $(python --version)"
echo "Venv:   $VIRTUAL_ENV"
echo ""

# ── Run NER ───────────────────────────────────────────────────────────────────
cd "$PROJECT_DIR"

python pipeline/03_ner/run_ner.py \
    --input  output/ocr_md \
    --output output/ner_output

echo ""
echo "======================================================"
echo "NER job complete: $(date)"
echo "======================================================"
