# Reproduction Guide

How to re-run the work in this repository, end to end. For chapter-specific instructions, see each chapter's own `README.md`.

## TL;DR — what you can run right now

| Task | Where | Needs |
|---|---|---|
| Reproduce OCR-system comparison | `chapter1-ocr/evaluation/` | CPU only; pip install reqs |
| Reproduce NER comparison (without retraining) | `chapter2-ner/evaluation/` | CPU for classical models; GPU for LLM-based |
| Re-train EarlyModernNER | `chapter2-ner/training-recipes/` | GPU (24GB+); Zenodo training corpus |
| Run EarlyModernNER inference | `chapter2-ner/earlymodernner/` | GPU; Zenodo adapter weights |
| Run GraphRAG pipeline | `chapter3-graphrag/` | Phase B Zenodo deposits + Neo4j + ChromaDB |

## Software prerequisites

- Python 3.11+
- For GPU work: CUDA 12.1+ and a GPU with ≥24GB VRAM (the EarlyModernNER adapters were trained on RTX 4090; inference works on smaller cards)
- For Chapter 3: Docker (for Neo4j and ChromaDB) and Ollama (for local LLM serving in the LightRAG path)

## Step 1 — Clone

```bash
git clone https://github.com/polayj/early-modern-pipeline.git
cd early-modern-pipeline
```

## Step 2 — Pick what you want to reproduce

### Chapter 1: OCR evaluation

```bash
cd chapter1-ocr/evaluation/
pip install -r requirements.txt
python evaluate_all_ocr_systems.py \
    --gold ../gold-standard/transcriptions/ \
    --systems ../gold-standard/per-system-outputs/ \
    --out ../results/my-run.csv
```

Expected: a CSV matching `results/ocr_evaluation_summary.csv` within rounding tolerance (the per-system outputs are pre-computed and standardized, so the metrics are deterministic).

### Chapter 2: NER comparison

```bash
cd chapter2-ner/evaluation/
pip install -r ../earlymodernner/requirements.txt
python compare_all_models.py \
    --gold ../gold-standard/reviewed/ \
    --out ../results/my-comparison.json
```

To include EarlyModernNER in the comparison, you'll need the adapter weights from Zenodo (link in top-level README under "Zenodo deposits").

### Chapter 2: Re-train EarlyModernNER

```bash
cd chapter2-ner/training-recipes/
# Download training corpus from Zenodo first
python prepare_training_data.py --source <zenodo-extracted-path> --out ./data
python train_lora.py --config config/ensemble_person_augmented.yaml
# Repeat for commodity, organization, toponym
```

Each adapter takes ~6–12 hours on an RTX 4090. The thesis training run took ~3 days end to end.

### Chapter 3: GraphRAG pipeline

This requires Phase B Zenodo deposits and is the most involved reproduction.

```bash
cd chapter3-graphrag/
pip install -r requirements.txt

# 1. Bring up databases
docker compose -f docker/unraid/neo4j.compose.yml up -d
docker compose -f docker/unraid/chromadb.compose.yml up -d

# 2. Option A: load the prebuilt knowledge graph (fast)
unzip <zenodo-knowledge-graph.zip> -d /tmp/kg
# (see Zenodo deposit README for cypher-shell load command)

# 2. Option B: rebuild from OCR + NER outputs (slow, GPU required)
bash pipeline/run_pipeline.sh

# 3. Query
python pipeline/06_query/query.py "What were the main commodities exported from Jamaica in the 1730s?"
```

For just verifying the pipeline works without the full corpus, use the 10-document smoke test in `chapter3-graphrag/smoke-test/` (added in Phase B).

## Common issues

- **"Out of memory" during NER inference**: reduce `batch_size` in the EarlyModernNER config; the cascading architecture loads one adapter at a time but each adapter still needs ~16GB for inference.
- **OCR evaluation gives slightly different numbers than the thesis**: the thesis numbers are from a specific run captured in `chapter1-ocr/results/ocr_evaluation_summary.csv`. Re-runs should match within ~0.001 WER; if you see larger drift, check that you're using the same `standardize_text.py` post-processing.
- **Neo4j won't start**: the compose file expects ports 7474 and 7687; check for conflicts.
- **EEBO OCR outputs are missing from the Zenodo deposit**: this is intentional — they're held back pending copyright review. Internet Archive sources are present.

## Hardware used in the thesis

- OCR runs: mix of RTX 4090 (local) and U of S `nibi` cluster (SLURM scripts in `chapter3-graphrag/pipeline/nibi/`)
- EarlyModernNER training: RTX 4090
- GraphRAG building: RTX 4090 + 64GB RAM machine; Neo4j and ChromaDB on Unraid
- LLM serving: Ollama running Qwen3.5-35B-A3B quantized

Lower-spec setups will work but slower. Don't try to OCR the full 20K corpus on CPU — the thesis estimate was ~3 weeks of GPU-time even on the fastest systems.
