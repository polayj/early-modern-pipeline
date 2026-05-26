#!/bin/bash
#
# submit_pipeline.sh — Submit the full OCR→NER chain to Nibi's SLURM scheduler.
#
# Run this from the project root on the Nibi LOGIN NODE:
#   cd ~/projects/def-jic823/Jacob-Projects/emgraphrag
#   bash pipeline/nibi/submit_pipeline.sh
#
# What it does:
#   Submits 3 rounds of OCR → NER as a dependency chain.
#   Each OCR job runs for up to 48 h, processing ~7,000 PDFs.
#   Each NER job runs after the preceding OCR job finishes successfully.
#   All steps are resume-safe — already-processed files are skipped.
#
#   ocr1 → ner1 → ocr2 → ner2 → ocr3 → ner3
#
# After all 6 jobs complete, download results:
#   rsync -av nibi:~/projects/def-jic823/Jacob-Projects/emgraphrag/output/ocr_md/ output/ocr_md/
#   rsync -av nibi:~/projects/def-jic823/Jacob-Projects/emgraphrag/output/ner_output/ output/ner_output/
# Then run steps 4–5 on the school computer.

set -euo pipefail

SLURM_DIR="$(cd "$(dirname "$0")" && pwd)"
OCR_SLURM="$SLURM_DIR/submit_ocr.slurm"
NER_SLURM="$SLURM_DIR/submit_ner.slurm"

echo "========================================================"
echo "emgraphrag — Submitting OCR→NER pipeline chain"
echo "========================================================"
echo ""

# ── Round 1 ───────────────────────────────────────────────────────────────────
ocr1=$(sbatch --parsable "$OCR_SLURM")
echo "OCR round 1 submitted: job $ocr1"

ner1=$(sbatch --parsable --dependency=afterok:$ocr1 "$NER_SLURM")
echo "NER round 1 submitted: job $ner1  (depends on $ocr1)"

# ── Round 2 ───────────────────────────────────────────────────────────────────
ocr2=$(sbatch --parsable --dependency=afterok:$ner1 "$OCR_SLURM")
echo "OCR round 2 submitted: job $ocr2  (depends on $ner1)"

ner2=$(sbatch --parsable --dependency=afterok:$ocr2 "$NER_SLURM")
echo "NER round 2 submitted: job $ner2  (depends on $ocr2)"

# ── Round 3 ───────────────────────────────────────────────────────────────────
ocr3=$(sbatch --parsable --dependency=afterok:$ner2 "$OCR_SLURM")
echo "OCR round 3 submitted: job $ocr3  (depends on $ner2)"

ner3=$(sbatch --parsable --dependency=afterok:$ocr3 "$NER_SLURM")
echo "NER round 3 submitted: job $ner3  (depends on $ocr3)"

echo ""
echo "========================================================"
echo "All 6 jobs submitted."
echo ""
echo "Job summary:"
printf "  %-20s %s\n" "OCR round 1:" "$ocr1"
printf "  %-20s %s\n" "NER round 1:" "$ner1"
printf "  %-20s %s\n" "OCR round 2:" "$ocr2"
printf "  %-20s %s\n" "NER round 2:" "$ner2"
printf "  %-20s %s\n" "OCR round 3:" "$ocr3"
printf "  %-20s %s\n" "NER round 3:" "$ner3"
echo ""
echo "Monitor with:"
echo "  squeue -u \$USER"
echo "  squeue -j $ocr1,$ner1,$ocr2,$ner2,$ocr3,$ner3"
echo ""
echo "Watch live log (replace JOBID with the current running job ID):"
echo "  tail -f emgraphrag_ocr_JOBID.out"
echo "  tail -f emgraphrag_ner_JOBID.out"
echo ""
echo "Cancel all jobs if needed:"
echo "  scancel $ocr1 $ner1 $ocr2 $ner2 $ocr3 $ner3"
echo "========================================================"
