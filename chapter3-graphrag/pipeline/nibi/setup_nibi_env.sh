#!/bin/bash
#
# setup_nibi_env.sh — One-time environment setup for emgraphrag on Nibi
#
# Run this ONCE on the Nibi login node before submitting any jobs.
# It creates the Python venv, installs all dependencies using the
# Alliance wheelhouse where possible, and pre-downloads the olmOCR model.
#
# Usage:
#   ssh nibi
#   cd ~/projects/def-jic823/Jacob-Projects/emgraphrag
#   bash pipeline/nibi/setup_nibi_env.sh

set -euo pipefail

PROJECT_DIR=~/projects/def-jic823/Jacob-Projects/emgraphrag
VENV_PATH="$PROJECT_DIR/venv"
HF_HOME="$PROJECT_DIR/.cache/huggingface"
OCR_MODEL="allenai/olmOCR-7B-0225-preview"

echo "========================================================"
echo "emgraphrag environment setup — Nibi"
echo "========================================================"
echo "Project dir: $PROJECT_DIR"
echo "Venv:        $VENV_PATH"
echo "HF cache:    $HF_HOME"
echo ""

mkdir -p "$HF_HOME"

# ── Load modules ──────────────────────────────────────────────────────────────
echo "Loading modules..."
module load gcc python/3.11 opencv
echo "  Python: $(python --version)"

# ── Create venv ───────────────────────────────────────────────────────────────
if [ -d "$VENV_PATH" ]; then
    echo ""
    echo "Venv already exists — activating."
    source "$VENV_PATH/bin/activate"
else
    echo ""
    echo "Creating virtualenv (Alliance --no-download)..."
    virtualenv --no-download "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
fi

# ── pip + wheelhouse dependencies ────────────────────────────────────────────
echo ""
echo "Upgrading pip..."
pip install --no-index --upgrade pip

echo ""
echo "Installing PyTorch from Alliance wheelhouse..."
pip install --no-index torch torchvision

echo ""
echo "Installing other wheelhouse packages..."
pip install --no-index pillow numpy scipy transformers accelerate tokenizers safetensors 2>/dev/null || true
pip install --no-index tqdm 2>/dev/null || pip install tqdm
pip install --no-index pandas 2>/dev/null || pip install pandas
pip install --no-index openpyxl 2>/dev/null || pip install openpyxl

# ── Install packages from PyPI (wheelhouse deps already satisfied) ────────────
echo ""
echo "Installing hf_xet (required for HuggingFace Xet storage downloads)..."
# Pin to 1.2.0 — the 1.3.x Alliance wheelhouse build removes PyXetDownloadInfo
# which the current huggingface_hub expects. 1.2.0 is confirmed working on Nibi.
pip install "hf_xet==1.2.0"

echo ""
echo "Installing vllm (olmOCR inference backend)..."
pip install vllm

echo ""
echo "Installing olmocr from PyPI..."
pip install olmocr

echo ""
echo "Installing earlymodernner from PyPI..."
pip install earlymodernner

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
echo "Verifying installation..."
python -c "import torch; print(f'  PyTorch: {torch.__version__}')"
python -c "import olmocr; print('  olmOCR: OK')"
python -c "import earlymodernner; print('  EarlyModernNER: OK')"
python -c "import tqdm; print('  tqdm: OK')"

# ── Pre-download olmOCR model ─────────────────────────────────────────────────
# Must be done on the login node (internet access).
# SLURM compute nodes run with HF_HUB_OFFLINE=1 to use this cache.
echo ""
echo "========================================================"
echo "Pre-downloading olmOCR model: $OCR_MODEL"
echo "  (This may take 10-20 minutes — ~15GB download)"
echo "  Cache: $HF_HOME"
echo "========================================================"

export HF_HOME="$HF_HOME"

if [ -z "${HF_TOKEN:-}" ]; then
    echo ""
    echo "ERROR: HF_TOKEN is not set."
    echo "  allenai/olmOCR-7B-0225-preview is a gated model."
    echo "  1. Accept the license at: https://huggingface.co/allenai/olmOCR-7B-0225-preview"
    echo "  2. Create a token at:     https://huggingface.co/settings/tokens"
    echo "  3. Re-run with:           HF_TOKEN=hf_xxxx bash pipeline/nibi/setup_nibi_env.sh"
    exit 1
fi

python -c "
from huggingface_hub import snapshot_download
import os
print('Downloading model weights...')
snapshot_download('$OCR_MODEL', cache_dir='$HF_HOME', token='${HF_TOKEN}')
print('Model download complete.')
"

echo ""
echo "========================================================"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Upload PDFs to Nibi (see copy_to_nibi.sh from WSL2)"
echo "  2. sbatch pipeline/nibi/submit_ocr.slurm"
echo "  3. After OCR finishes: sbatch pipeline/nibi/submit_ner.slurm"
echo "  4. Download results (see copy_to_nibi.sh)"
echo "========================================================"
