#!/bin/bash
#
# copy_to_nibi.sh — Sync pipeline scripts and small data files to Nibi.
#
# Run this from WSL2 (or any machine with rsync + SSH access to Nibi):
#   bash pipeline/nibi/copy_to_nibi.sh
#
# What it copies automatically:
#   - pipeline/          → all scripts
#   - requirements.txt   → Python deps list
#   - CLAUDE.md          → project context
#   - output/import_records_parsed/  → pre-parsed import records (~50 MB)
#
# What you must copy manually (too large for automated transfer):
#   ocr_docs/            → ~100 GB PDF corpus
#   (see the rsync command printed at the end)

set -euo pipefail

NIBI_HOST="nibi"
NIBI_USER="jacobpol"
NIBI_PROJECT_DIR="/home/$NIBI_USER/projects/def-jic823/Jacob-Projects/emgraphrag"
LOCAL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "========================================================"
echo "copy_to_nibi.sh — Syncing emgraphrag to Nibi"
echo "========================================================"
echo "Local root:  $LOCAL_ROOT"
echo "Remote:      $NIBI_HOST:$NIBI_PROJECT_DIR"
echo ""

# ── Create remote directory structure ────────────────────────────────────────
echo "Creating remote directory structure..."
ssh "$NIBI_HOST" "mkdir -p \
    $NIBI_PROJECT_DIR/pipeline/nibi \
    $NIBI_PROJECT_DIR/output/ocr_md \
    $NIBI_PROJECT_DIR/output/ner_output \
    $NIBI_PROJECT_DIR/output/import_records_parsed \
    $NIBI_PROJECT_DIR/ocr_docs/unprocessed/archive_org \
    $NIBI_PROJECT_DIR/ocr_docs/unprocessed/EEBO"
echo "  Remote dirs created."
echo ""

# ── Sync pipeline scripts ─────────────────────────────────────────────────────
echo "Syncing pipeline/ scripts..."
rsync -av --progress \
    "$LOCAL_ROOT/pipeline/" \
    "$NIBI_HOST:$NIBI_PROJECT_DIR/pipeline/"
echo ""

# ── Sync root config files ────────────────────────────────────────────────────
echo "Syncing root config files (requirements.txt, CLAUDE.md)..."
rsync -av --progress \
    "$LOCAL_ROOT/requirements.txt" \
    "$LOCAL_ROOT/CLAUDE.md" \
    "$NIBI_HOST:$NIBI_PROJECT_DIR/"
echo ""

# ── Sync pre-parsed import records ───────────────────────────────────────────
IMPORT_RECORDS_LOCAL="$LOCAL_ROOT/output/import_records_parsed"
if [ -d "$IMPORT_RECORDS_LOCAL" ]; then
    echo "Syncing output/import_records_parsed/ (~50 MB)..."
    rsync -av --progress \
        "$IMPORT_RECORDS_LOCAL/" \
        "$NIBI_HOST:$NIBI_PROJECT_DIR/output/import_records_parsed/"
    echo ""
else
    echo "WARNING: $IMPORT_RECORDS_LOCAL not found — skipping."
    echo "  Run pipeline/01_parse_import_records.py first, then re-run this script."
    echo ""
fi

echo "========================================================"
echo "Script-managed files synced successfully."
echo ""
echo "NEXT STEP — Copy the PDF corpus (run this separately, ~100 GB):"
echo ""
echo "  rsync -av --progress \\"
echo "    $LOCAL_ROOT/ocr_docs/unprocessed/ \\"
echo "    $NIBI_HOST:$NIBI_PROJECT_DIR/ocr_docs/unprocessed/"
echo ""
echo "This will take a long time over the network. Consider:"
echo "  - Running it in a screen/tmux session so it survives disconnects:"
echo "      screen -S rsync_pdfs"
echo "      rsync -av --progress --partial \\"
echo "        $LOCAL_ROOT/ocr_docs/unprocessed/ \\"
echo "        $NIBI_HOST:$NIBI_PROJECT_DIR/ocr_docs/unprocessed/"
echo "      # Ctrl-A D to detach; screen -r rsync_pdfs to reattach"
echo ""
echo "  - Or use Globus for large transfers (available on Nibi via the Alliance)."
echo ""
echo "After PDFs are uploaded, on the Nibi login node run:"
echo "  cd $NIBI_PROJECT_DIR"
echo "  bash pipeline/nibi/setup_nibi_env.sh    # one-time setup"
echo "  bash pipeline/nibi/submit_pipeline.sh   # submit the job chain"
echo "========================================================"
